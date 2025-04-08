import json
import os
import re
import subprocess
import tempfile
import traceback

from app.python import generate_python_module
from flask import Flask, request
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config["SECRET_KEY"] = "secret!"  # Change this in production!
socketio = SocketIO(
    app, cors_allowed_origins="*"
)  # Allow requests from frontend dev server


# Function to validate the generated code by running it in a specific venv
def validate_code_in_venv(module_name, code_string):
    """Executes Python code in a venv, parses structured JSON output, and returns the result."""
    # Define the path to the virtual environment's Python executable
    # TODO: Make this configurable
    venv_path = (
        "/Users/provos/src/deepsearch/.venv"  # Hardcoded path to the venv directory
    )
    python_executable = os.path.join(
        venv_path, "bin", "python"
    )  # Assumes Linux/macOS structure

    if not os.path.exists(python_executable):
        error_message = f"Python executable not found at {python_executable}. Please ensure the venv exists."
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
