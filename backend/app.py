import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Union

from app.python import generate_python_module
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"  # Change this in production!
app.config["SELECTED_VENV_PATH"] = (
    None  # Will store the selected Python interpreter path
)
# Enable CORS for the Flask app
CORS(app, resources={r"/api/*": {"origins": "*"}})
socketio = SocketIO(
    app, cors_allowed_origins="*"
)  # Allow requests from frontend dev server


# Function to discover Python environments
def discover_python_environments() -> List[Dict[str, str]]:
    """
    Discover Python interpreters available on the system.
    Returns a list of dictionaries with 'path' and 'name' keys.
    """
    environments = []

    # Current directory venvs
    base_dir = Path(os.path.abspath(__file__)).parent.parent.parent
    potential_dirs = base_dir.glob("*/.venv")
    common_venv_paths = [
        dir / "bin" / "python" for dir in potential_dirs if dir.is_dir()
    ]

    # Add macOS/Linux specific paths
    if sys.platform != "win32":
        # Check home directory for virtual environments
        home_dir = os.path.expanduser("~")
        for env_dir in [".virtualenvs", "venvs", "Envs"]:
            venvs_dir = os.path.join(home_dir, env_dir)
            if os.path.isdir(venvs_dir):
                for venv in os.listdir(venvs_dir):
                    venv_path = os.path.join(venvs_dir, venv, "bin", "python")
                    if os.path.isfile(venv_path) and os.access(venv_path, os.X_OK):
                        environments.append(
                            {
                                "path": venv_path,
                                "name": f"~/{env_dir}/{venv}/bin/python",
                            }
                        )

    # Add common venv paths
    for venv_path in common_venv_paths:
        if os.path.isfile(venv_path) and os.access(venv_path, os.X_OK):
            environments.append(
                {
                    "path": str(venv_path),
                    "name": f"Python ({venv_path.parent.parent.parent.name})",
                }
            )

    # Filter out all duplicate paths
    unique_environments = []
    seen = set()
    for env in environments:
        env_path = env["path"]
        if env_path not in seen:
            unique_environments.append(env)
            seen.add(env_path)

    return unique_environments


# API endpoints for Python interpreter selection
@app.route("/api/venvs", methods=["GET"])
def get_venvs():
    """Get available Python environments."""
    try:
        environments = discover_python_environments()
        return jsonify({"success": True, "environments": environments})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/current-venv", methods=["GET"])
def get_current_venv():
    """Get the currently selected Python environment."""
    return jsonify({"success": True, "path": app.config["SELECTED_VENV_PATH"]})


@app.route("/api/set-venv", methods=["POST"])
def set_venv():
    """Set the Python environment to use for validation."""
    try:
        data = request.json
        if not data or "path" not in data:
            return jsonify({"success": False, "error": "Missing path parameter"}), 400

        path = data["path"]
        if not os.path.isfile(path) or not os.access(path, os.X_OK):
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Invalid Python executable path: {path}",
                    }
                ),
                400,
            )

        # Verify it's a Python interpreter
        try:
            result = subprocess.run(
                [path, "--version"], capture_output=True, text=True, check=True
            )
            if not result.stdout.strip().startswith("Python "):
                return (
                    jsonify(
                        {"success": False, "error": f"Not a Python interpreter: {path}"}
                    ),
                    400,
                )
        except subprocess.SubprocessError as e:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": f"Failed to verify Python interpreter: {str(e)}",
                    }
                ),
                400,
            )

        # Store the selected path
        app.config["SELECTED_VENV_PATH"] = path
        return jsonify({"success": True, "path": path})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Function to validate the generated code by running it in a specific venv
def validate_code_in_venv(module_name, code_string):
    """Executes Python code in a venv, parses structured JSON output, and returns the result."""
    # Get the selected Python executable path
    python_executable = app.config.get("SELECTED_VENV_PATH")

    # If no path is selected, return an error
    if not python_executable:
        return {
            "success": False,
            "error": {
                "message": "No Python interpreter selected. Please select a Python interpreter in the settings.",
                "nodeName": None,
                "fullTraceback": None,
            },
        }

    # Verify the path still exists
    if not os.path.exists(python_executable):
        error_message = f"Python executable not found at {python_executable}. Please select another interpreter."
        print(error_message)
        # Return structured error
        return {
            "success": False,
            "error": {
                "message": error_message,
                "nodeName": None,
                "fullTraceback": None,
            },
        }

    # Use a temporary file for the generated code
    # delete=False is needed on Windows to allow the subprocess to open the file.
    # The file is explicitly closed and removed in the finally block.
    tmp_file = None  # Initialize outside try
    try:
        # Create a named temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(code_string)
            module_path = tmp_file.name  # Get the path of the temporary file

        # Execute the script using the venv's Python interpreter
        result = subprocess.run(
            [python_executable, module_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,  # Increased timeout slightly
        )

        print(f"Execution in venv completed with exit code: {result.returncode}")
        if result.stdout:
            # Print label and output separately
            print("stdout:")
            print(result.stdout)
        if result.stderr:
            # Print label and output separately
            print("stderr:")
            print(result.stderr)

        # Combine stdout and stderr for parsing
        combined_output = result.stdout + "\n" + result.stderr

        # Try to parse structured JSON error output first
        error_match = re.search(
            r"##ERROR_JSON_START##\s*(.*?)\s*##ERROR_JSON_END##",
            combined_output,
            re.DOTALL,
        )
        if error_match:
            json_str = error_match.group(1)
            try:
                error_data = json.loads(json_str)
                print(f"Parsed error JSON from script output: {error_data}")
                return error_data  # Return the structured error from the script
            except json.JSONDecodeError as e:
                print(
                    f"Error decoding JSON from script error output: {e}\nJSON string: {json_str}"
                )
                # Fallback to generic error if JSON parsing fails
                return {
                    "success": False,
                    "error": {
                        "message": "Script failed with undecipherable JSON error output.",
                        "nodeName": None,
                        "fullTraceback": combined_output,
                    },
                }

        # Try to parse structured JSON success output
        success_match = re.search(
            r"##SUCCESS_JSON_START##\s*(.*?)\s*##SUCCESS_JSON_END##",
            combined_output,
            re.DOTALL,
        )
        if success_match:
            json_str = success_match.group(1)
            try:
                success_data = json.loads(json_str)
                print(f"Parsed success JSON from script output: {success_data}")
                return success_data  # Return the structured success info
            except json.JSONDecodeError as e:
                print(
                    f"Error decoding JSON from script success output: {e}\nJSON string: {json_str}"
                )
                # Fallback, but assume success if marker was present
                return {
                    "success": True,
                    "message": "Script indicated success, but JSON output was malformed.",
                }

        # --- Fallback Logic (if no JSON markers found) ---
        print(
            "No structured JSON markers found in script output. Falling back to exit code check."
        )

        if result.returncode == 0:
            # Script finished with exit code 0 but didn't print success JSON
            print(
                f"Script '{module_name}' completed with exit code 0 but no success JSON marker."
            )
            return {
                "success": True,
                "message": "Script validation finished without explicit success confirmation.",
            }  # Assume success?
        else:
            # Script failed before printing JSON markers (e.g., syntax error)
            print(
                f"Script failed with exit code {result.returncode} before printing JSON markers."
            )
            error_output = result.stderr or result.stdout or "Unknown execution error"
            lines = error_output.strip().split("\n")
            core_error_message = lines[-1] if lines else "Unknown execution error line."

            # Use the simpler regex fallback for node name from raw output
            name_regex = (
                r"\b([A-Za-z_][A-Za-z0-9_]*?)(?:Task|Worker)\d+\b(?:\s*=|\s*\()"
            )
            found_node_name = None
            matches = re.findall(name_regex, error_output)
            if matches:
                found_node_name = matches[0]
                if (
                    found_node_name.startswith("l")
                    and len(found_node_name) > 1
                    and found_node_name[1].isupper()
                ):
                    found_node_name = found_node_name[1:]

            print(
                f"Fallback Error: Node found: {found_node_name}, Error: {core_error_message}"
            )
            return {
                "success": False,
                "error": {
                    "message": core_error_message,
                    "nodeName": found_node_name,
                    "fullTraceback": error_output,  # Provide the raw output as traceback
                },
            }

    except subprocess.TimeoutExpired:
        error_message = f"Execution of '{module_name}' timed out after 60 seconds."
        print(error_message)
        # Return structured error
        return {
            "success": False,
            "error": {
                "message": error_message,
                "nodeName": None,
                "fullTraceback": None,
            },
        }
    except Exception as e:
        tb_str = traceback.format_exc()
        error_details = f"Error during validation process for '{module_name}': {e}"
        print(f"{error_details}\n{tb_str}")
        # Return structured error
        return {
            "success": False,
            "error": {
                "message": f"Internal validation error: {e}",
                "nodeName": None,
                "fullTraceback": tb_str,
            },
        }
    finally:
        # Clean up the temporary file explicitly if it was created
        if tmp_file and os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)


@socketio.on("connect")
def handle_connect():
    print("Client connected:", request.sid)


@socketio.on("disconnect")
def handle_disconnect():
    print("Client disconnected:", request.sid)


@socketio.on("export_graph")
def handle_export_graph(data):
    """Receives graph data, generates Python module, validates it, and returns structured result."""
    print(f"Received export_graph event from {request.sid}")
    # You might want to add validation for the 'data' structure here

    python_code, module_name = generate_python_module(data)

    if python_code is None or module_name is None:
        emit(
            "export_result",
            {
                "success": False,
                "error": {
                    "message": "Failed to generate Python code from graph.",
                    "nodeName": None,
                    "fullTraceback": None,
                },
            },
            room=request.sid,
        )
        return

    # Attempt to validate the generated module in the specified venv
    validation_result = validate_code_in_venv(module_name, python_code)

    # Emit the entire result structure (which includes success status and error details if any)
    emit("export_result", validation_result, room=request.sid)


if __name__ == "__main__":
    print("Starting Flask-SocketIO server...")
    # Use eventlet for better performance if available
    socketio.run(
        app, debug=True, port=5001, use_reloader=True
    )  # Use a different port than SvelteKit dev server
