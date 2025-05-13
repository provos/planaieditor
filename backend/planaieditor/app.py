# Try to import and monkey patch eventlet FIRST
try:
    import eventlet

    eventlet.monkey_patch()
    print("Eventlet monkey patch applied successfully.")
except ImportError:
    print("Eventlet not found. Proceeding without monkey patching.")
    # Optionally, you could force a non-eventlet server if needed
    pass

import json
import os
import re
import subprocess
import sys
import tempfile
import traceback
from argparse import ArgumentParser
from pathlib import Path
from textwrap import indent
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from planaieditor.filesystem import setup_filesystem
from planaieditor.llm_interface_utils import list_models_for_provider
from planaieditor.lsp_handler import lsp_handler_instance as lsp_handler
from planaieditor.patch import get_definitions_from_file
from planaieditor.python import (
    add_to_task_import_state,
    create_task_class,
    create_worker_class,
    format_python_code,
    generate_python_module,
)
from planaieditor.socket_server import SocketServer
from planaieditor.utils import parse_traceback
from planaieditor.venv import discover_python_environments

# Determine mode and configure paths/CORS
FLASK_ENV = os.environ.get("FLASK_ENV", "production")  # Default to production
is_development = FLASK_ENV == "development"

# Define the build directory *within the package* for production
# This path is relative to app.py's location
package_static_dir = os.path.join(os.path.dirname(__file__), "static_frontend")

# Initialize Flask differently based on mode
if is_development:
    print("Running in DEVELOPMENT mode. Enabling CORS for *")
    app = Flask(__name__)
    # Allow requests from frontend dev server origin
    CORS(app, resources={r"/*": {"origins": "*"}})
    socketio = SocketIO(app, cors_allowed_origins="*")
else:
    # Production mode: Serve static files from the packaged directory
    print(
        f"Running in PRODUCTION mode. Serving static files from: {package_static_dir}"
    )
    # Ensure the static folder exists, otherwise Flask might error or serve incorrectly
    if not os.path.exists(package_static_dir):
        print(
            f"WARNING: Static file directory not found at {package_static_dir}. Frontend might not load."
        )
        # Initialize without static serving if dir is missing, API might still work
        app = Flask(__name__)
    else:
        app = Flask(__name__, static_folder=package_static_dir, static_url_path="/")
    socketio = SocketIO(app)  # No CORS needed when served from same origin

app.config["SECRET_KEY"] = "secret!"  # Change this in production!
app.config["SELECTED_VENV_PATH"] = (
    sys.executable  # Will store the selected Python interpreter path
)


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
def validate_code_in_venv(module_name, code_string, inject_debug_events=False):
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
    process = None  # Initialize process reference

    # Set up debug infrastructure if requested
    if inject_debug_events:
        # this assumes that the call came from a socketio connection
        sid = request.sid

        # Define the debug event handler
        def handle_debug_event(event):
            """Handle debug events received from the subprocess"""
            event_type = event.get("type", "unknown")
            event_data = event.get("data", {})

            print(f"Received debug event: {event_type} - {event_data}")

            # Emit the event to the frontend through SocketIO
            # Include current socket ID to ensure it goes to the right client
            socketio.emit(
                "planai_debug_event",
                {"type": event_type, "data": event_data},
                room=sid,
            )

        try:
            # Use the SocketServer as a context manager
            with SocketServer(callback=handle_debug_event) as server:
                # Create a named temporary file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".py", delete=False, encoding="utf-8"
                ) as tmp_file:
                    # Inject debug monitor import at the top of the code
                    debug_monitor_path = os.path.join(
                        os.path.dirname(__file__),
                        "codesnippets",
                        "debug_monitor.py",
                    )
                    debug_import = f"""
# Debug monitoring - injected by PlanAI Editor
import os, sys
os.environ['DEBUG_PORT'] = '{server.port}'

{Path(debug_monitor_path).read_text()}

# End of debug monitoring injection
"""
                    tmp_file.write(debug_import + code_string)
                    module_path = tmp_file.name  # Get the path of the temporary file

                print(f"Starting execution with debug server on port {server.port}")

                # Execute the script using the venv's Python interpreter
                process = subprocess.run(
                    [python_executable, module_path],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=60,
                )

                # Process the results (this is the same for both paths)
                return process_execution_results(process, module_name)

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
    else:
        # Simpler path when not injecting debug events
        try:
            # Create a temporary file for the code without debug injection
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(code_string)
                module_path = tmp_file.name

            # Execute the script using the venv's Python interpreter
            process = subprocess.run(
                [python_executable, module_path],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )

            # Process the results
            return process_execution_results(process, module_name)

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


# Helper function to process execution results - extracted from validate_code_in_venv to avoid code duplication
def process_execution_results(process, module_name):
    """Processes the results of a subprocess execution, parsing output for structured JSON or errors."""
    print(f"Execution in venv completed with exit code: {process.returncode}")
    if process.stdout:
        # Print label and output separately
        print("stdout:")
        print(process.stdout)
    if process.stderr:
        # Print label and output separately
        print("stderr:")
        print(process.stderr)

    # Combine stdout and stderr for parsing
    combined_output = process.stdout + "\n" + process.stderr

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

    # Try to parse special errors from planai logs in output
    error_match = re.search(
        r"ERROR:root:Worker (\w+) on Task (\w+) failed with exception: (.*)",
        process.stderr,
    )
    if error_match:
        error_data = {
            "success": False,
            "error": {
                "message": f"Worker {error_match.group(1)} on Task {error_match.group(2)} failed with exception: {error_match.group(3)}",
                "nodeName": error_match.group(1),
                "fullTraceback": process.stderr,
            },
        }
        return error_data

    traceback_data = parse_traceback(process.stderr)
    if traceback_data:
        return traceback_data

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

    if process.returncode == 0:
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
            f"Script failed with exit code {process.returncode} before printing JSON markers."
        )
        error_output = process.stderr or process.stdout or "Unknown execution error"
        lines = error_output.strip().split("\n")
        core_error_message = lines[-1] if lines else "Unknown execution error line."

        # Use the simpler regex fallback for node name from raw output
        name_regex = r"\b([A-Za-z_][A-Za-z0-9_]*?)(?:Task|Worker)\d+\b(?:\s*=|\s*\()"
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


@socketio.on("connect")
def handle_connect():
    print("Client connected:", request.sid)

    # Initialize debug sessions storage if not exists
    if not hasattr(app, "debug_sessions"):
        app.debug_sessions = {}


@socketio.on("disconnect")
def handle_disconnect():
    sid = request.sid
    print("Client disconnected:", sid)

    # Clean up any debug session data
    if hasattr(app, "debug_sessions") and sid in app.debug_sessions:
        del app.debug_sessions[sid]


@socketio.on("register_for_debug_events")
def handle_register_for_debug(data):
    """Register client to receive PlanAI debug events."""
    print(f"Client {request.sid} registered for debug events")

    # Store debug session data
    if not hasattr(app, "debug_sessions"):
        app.debug_sessions = {}

    # Store any client preferences
    app.debug_sessions[request.sid] = {
        "registered": True,
        "preferences": data.get("preferences", {}),
    }

    # Acknowledge registration
    emit(
        "debug_registration_status",
        {"success": True, "message": "Successfully registered for PlanAI debug events"},
        room=request.sid,
    )


@socketio.on("start_lsp")
def handle_start_lsp():
    """Handles request from client to start the LSP server process."""
    sid = request.sid
    print(f"[{sid}] Received start_lsp request.")

    # Use the currently selected Python executable or fallback to the system one
    python_executable = app.config.get("SELECTED_VENV_PATH", sys.executable)

    # XXX - we need to restart the LSP process if the venv changes
    success = lsp_handler.start_lsp_process(python_executable, sid, socketio.emit)

    if success:
        print(f"[{sid}] LSP process started successfully.")
    else:
        print(f"[{sid}] Failed to start LSP process.")


@socketio.on("lsp_message")
def handle_lsp_message(message):
    """Handles LSP messages forwarded from the client."""
    sid = request.sid
    # Basic validation
    if not isinstance(message, dict):
        print(f"[{sid}] Received invalid LSP message (not a dict): {message}")
        return

    # Forward the message to the handler with the emit function
    lsp_handler.send_lsp_message(message)


@socketio.on("stop_lsp")
def handle_stop_lsp():
    """Handles request from client to explicitly stop the LSP server process."""
    sid = request.sid
    print(f"[{sid}] Received stop_lsp request.")
    lsp_handler.stop_lsp_process()
    emit("lsp_stopped", room=sid)  # Confirm stop


@socketio.on("export_graph")
def handle_export_graph(data):
    """Receives graph data, generates Python module, validates it, and returns structured result."""
    print(f"Received export_graph event from {request.sid}")
    # You might want to add validation for the 'data' structure here

    python_code, module_name, error_json = generate_python_module(
        data, debug_print=is_development
    )
    if error_json:
        emit("export_result", error_json, room=request.sid)
        return

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

    if data.get("mode") == "export":
        emit(
            "export_result",
            {
                "success": True,
                "mode": "export",
                "python_code": python_code,
            },
            room=request.sid,
        )
        return

    # Attempt to validate the generated module in the specified venv
    validation_result = validate_code_in_venv(
        module_name, python_code, inject_debug_events=True
    )

    # Construct the final response
    response_data = {
        "success": validation_result.get("success", False),
        "mode": "execute",
        "python_code": python_code,
        "validation_result": validation_result,  # Include the validation details
    }
    # Add error details to the main level if validation failed
    if not response_data["success"]:
        response_data["error"] = validation_result.get("error", "Validation failed.")
    else:
        response_data["message"] = "Execution successful!"

    emit("export_result", response_data, room=request.sid)


@app.route("/api/import-python", methods=["POST"])
def import_python_module():
    """Receives Python code content, parses it for Task definitions, and returns them."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    data = request.get_json()
    python_code = data.get("python_code")

    if not python_code:
        return (
            jsonify(
                {"success": False, "error": "Missing 'python_code' in request body"}
            ),
            400,
        )

    # We need a temporary file to pass to the existing patch function
    # Alternatively, modify patch.py to accept code as a string directly
    # For now, using a temporary file is simpler to integrate.
    tmp_file = None
    try:
        # Create a named temporary file to store the code
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as tmp_file:
            tmp_file.write(python_code)
            temp_filename = tmp_file.name

        # Call the function from patch.py using the temporary file path
        definitions = get_definitions_from_file(temp_filename)

        # TODO: Add parsing for Worker definitions and graph structure later

        # Return the full dictionary with tasks and workers
        return jsonify({"success": True, **definitions})

    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Error during Python import processing: {e}\n{tb_str}")
        # Return a generic error to the client
        return (
            jsonify({"success": False, "error": f"Failed to parse Python code: {e}"}),
            500,
        )
    finally:
        # Clean up the temporary file
        if tmp_file and os.path.exists(tmp_file.name):
            try:
                os.remove(tmp_file.name)
            except OSError as e:
                print(f"Error removing temporary file {tmp_file.name}: {e}")


# --- New Endpoint for LLM Model Listing ---
@app.route("/api/llm/list-models", methods=["GET"])
def get_llm_models():
    provider = request.args.get("provider")
    if not provider:
        return (
            jsonify({"success": False, "error": "Missing 'provider' query parameter"}),
            400,
        )

    # Note: Ideally, this should run within the selected venv context.
    # For simplicity now, it runs in the backend env. This requires PlanAI & keys there.
    # A more robust solution would use a helper script + run_inspection_script.
    print(
        f"Attempting to list models for provider: {provider} (using backend environment)"
    )

    try:
        # Ensure PlanAI is available (checked within the function)
        models = list_models_for_provider(provider)
        print(f"Successfully listed models for {provider}: {models}")
        return jsonify({"success": True, "models": models})
    except ValueError as e:  # Catch errors like missing keys or invalid provider
        print(f"ValueError listing models for {provider}: {e}")
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        tb_str = traceback.format_exc()
        print(f"Internal server error listing models for {provider}: {e}\n{tb_str}")
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Internal server error listing models: {e}",
                }
            ),
            500,
        )


# --- Helper function to run the inspection script --- #
def run_inspection_script(
    module_path: str,
    action: str,
    class_name: Optional[str] = None,
    debug_print: bool = False,
) -> dict:
    """Runs the inspect_module.py script in the selected venv and returns parsed JSON output."""
    if debug_print:
        dprint = print
    else:

        def dprint(*args, **kwargs):
            pass

    python_executable = app.config.get("SELECTED_VENV_PATH")
    if not python_executable:
        return {"success": False, "error": "No Python interpreter selected."}
    if not os.path.exists(python_executable):
        return {
            "success": False,
            "error": f"Selected Python interpreter not found: {python_executable}",
        }

    script_path = Path(__file__).parent / "codesnippets" / "inspect_module.py"
    if not script_path.exists():
        return {
            "success": False,
            "error": "Internal error: inspect_module.py not found.",
        }

    command = [python_executable, str(script_path), module_path, action]
    if class_name:
        command.append(class_name)

    try:
        # Use the directory of the module path as cwd? Or workspace root?
        # This might need adjustment depending on how modules are typically structured/imported
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Check return code manually
            timeout=30,  # Timeout for inspection
            # cwd= # Consider setting cwd if relative imports are an issue
        )

        # Debugging output
        dprint("--- Inspect Script Start ---")
        dprint(f"Command: {' '.join(command)}")
        dprint(f"Return Code: {process.returncode}")
        if process.stdout:
            dprint(f"stdout:\n{process.stdout.strip()}")
        if process.stderr:
            dprint(f"stderr:\n{process.stderr.strip()}")
        dprint("--- Inspect Script End ---")

        # Attempt to parse JSON from stdout first (expected output)
        try:
            result_json = json.loads(process.stdout)
            return result_json
        except json.JSONDecodeError:
            # If stdout is not JSON, return an error with stderr content
            error_message = "Script execution failed or produced invalid output."
            if process.stderr:
                error_message += f" Error details: {process.stderr.strip()}"
            elif process.stdout:
                # Maybe stdout has a plain error message?
                error_message += f" Output: {process.stdout.strip()}"
            return {"success": False, "error": error_message}

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Module inspection timed out for '{module_path}'.",
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to run inspection script: {e}"}


@app.route("/api/import-task-classes", methods=["POST"])
def import_task_classes():
    """Imports a module in the venv and lists PlanAI Task classes."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    data = request.get_json()
    module_path = data.get("module_path")
    if not module_path:
        return (
            jsonify({"success": False, "error": "Missing 'module_path' in request"}),
            400,
        )

    result = run_inspection_script(
        module_path, action="list_classes", debug_print=is_development
    )
    status_code = 200 if result.get("success") else 400  # Or 500 for internal errors?
    return jsonify(result), status_code


@app.route("/api/get-task-fields", methods=["POST"])
def get_task_fields():
    """Gets Pydantic fields for a specific PlanAI Task class in a module."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    data = request.get_json()
    module_path = data.get("module_path")
    class_name = data.get("class_name")
    if not module_path or not class_name:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Missing 'module_path' or 'class_name' in request",
                }
            ),
            400,
        )

    result = run_inspection_script(
        module_path,
        action="get_fields",
        class_name=class_name,
        debug_print=is_development,
    )
    status_code = 200 if result.get("success") else 400  # Or 500?
    return jsonify(result), status_code


@app.route("/api/validate-module-imports", methods=["POST"])
def validate_module_imports():
    """Validates Python import statements in the selected venv."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    data = request.get_json()
    import_code = indent(data.get("import_code"), "    ")

    if import_code is None:  # Allow empty string, but not missing key
        return (
            jsonify({"success": False, "error": "Missing 'import_code' in request"}),
            400,
        )

    # Handle empty input gracefully - technically valid Python
    if not import_code.strip():
        return jsonify({"success": True, "message": "No imports to validate."}), 200

    python_executable = app.config.get("SELECTED_VENV_PATH")
    if not python_executable:
        return (
            jsonify({"success": False, "error": "No Python interpreter selected."}),
            400,
        )
    if not os.path.exists(python_executable):
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Selected Python interpreter not found: {python_executable}",
                }
            ),
            400,
        )

    # Create a validation script with proper JSON output markers
    validation_script = f"""
import sys
import json
import traceback

try:
    # --- User's import code ---
{import_code}
    # --- End of user's import code ---

    # If imports succeed, output success JSON
    success_output = {{"success": True, "message": "Imports validated successfully"}}
    print("##SUCCESS_JSON_START##")
    print(json.dumps(success_output))
    print("##SUCCESS_JSON_END##")

except Exception as e:
    # Error case - format any validation errors as JSON
    error_message = str(e)
    error_traceback = traceback.format_exc()

    # Create a structured error response
    error_output = {{
        "success": False,
        "error": {{
            # Use a specific message for import errors
            "message": f"Import validation failed: {{error_message}}",
            "nodeName": None, # No specific node context here
            "fullTraceback": error_traceback
        }}
    }}

    print("##ERROR_JSON_START##")
    print(json.dumps(error_output))
    print("##ERROR_JSON_END##")
    sys.exit(1) # Indicate failure
"""

    # Execute the validation script in the selected Python environment
    result = validate_code_in_venv("module_import_validation", validation_script)

    # Process the result for the frontend
    status_code = 200
    if not result.get("success"):
        # Extract the core error message if possible
        error_details = result.get("error", {})
        result["error"] = error_details.get("message", "Import validation failed.")

    return jsonify(result), status_code


@app.route("/api/validate-pydantic-data", methods=["POST"])
def validate_pydantic_data():
    """Validates JSON data against a Pydantic model."""
    data = request.get_json()
    node = data.get("node")
    json_data = data.get("jsonData")

    if not node or not json_data:
        return (
            jsonify(
                {"success": False, "error": "Missing 'node' or 'jsonData' in request"}
            ),
            400,
        )

    className = node.get("data", {}).get("className")
    if not className:
        return (
            jsonify({"success": False, "error": "Missing 'className' in request"}),
            400,
        )

    python_executable = app.config.get("SELECTED_VENV_PATH")
    if not python_executable:
        return {"success": False, "error": "No Python interpreter selected."}
    if not os.path.exists(python_executable):
        return {
            "success": False,
            "error": f"Selected Python interpreter not found: {python_executable}",
        }

    task_import_state = {}
    node_type = node.get("type")
    task_class = ""
    import_code = ""
    match node_type:
        case "task":
            task_class = create_task_class(node)
        case "taskimport":
            add_to_task_import_state(node, task_import_state)
            import_code = ""
            for module_path, classes in task_import_state.items():
                import_code += f"from {module_path} import {', '.join(classes)}\n"
        case _:
            return (jsonify({"success": False, "error": "Invalid node type"}), 400)

    # Create a validation script with proper JSON output markers
    validation_script = f"""
import sys
import json
import traceback
from planai import Task
from pydantic import Field
{import_code}
{task_class}

try:
    # Parse and validate the JSON data against the model
    validated_data = {className}.model_validate({json_data})

    # Success case - output formatted JSON for the validation function to parse
    success_output = {{
        "success": True,
        "message": "Data successfully validated against {className}"
    }}
    print("##SUCCESS_JSON_START##")
    print(json.dumps(success_output))
    print("##SUCCESS_JSON_END##")

except Exception as e:
    # Error case - format any validation errors as JSON
    error_message = str(e)
    error_traceback = traceback.format_exc()

    # Create a structured error response
    error_output = {{
        "success": False,
        "error": {{
            "message": error_message,
            "nodeName": "{className}",
            "fullTraceback": error_traceback
        }}
    }}

    print("##ERROR_JSON_START##")
    print(json.dumps(error_output))
    print("##ERROR_JSON_END##")
    sys.exit(1)
"""

    # Execute the validation script in the selected Python environment
    result = validate_code_in_venv("pydantic_validation", validation_script)

    if not result.get("success"):
        # convert the error output to a string
        error_output = result.get("error")
        result["error"] = error_output.get("message")

    # Return the validation result directly to the frontend
    status_code = 200
    return jsonify(result), status_code


@app.route("/api/get-node-code", methods=["POST"])
def get_node_code():
    """Receives a node data, and returns the code of the node."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    node_data = request.get_json()

    module_level_import = node_data.get("moduleLevelImport")

    worker = node_data.get("worker")
    preamble = """
from planai import Task, TaskWorker, CachedTaskWorker, JoinedTaskWorker
from planai import LLMTaskWorker, CachedLLMTaskWorker
from typing import Optional, List, Dict, Any, Type

"""

    if module_level_import:
        module_level_import_code = module_level_import.get("data", {}).get("code", "")
        # strip all comments from the code
        module_level_import_code = re.sub(r"^\s*#.*", "", module_level_import_code)
        if module_level_import_code:
            preamble += module_level_import_code + "\n"

    preamble += "\n# Please, make changes to your worker class below. The code above is just for auto-completion purposes.\n"

    python_code = create_worker_class(worker, add_comment=False)
    formatted_code = format_python_code(preamble + python_code)

    return (
        jsonify({"success": True, "code": formatted_code}),
        200,
    )


@app.route("/api/code-to-node", methods=["POST"])
def code_to_node():
    """Receives code and returns a node."""
    if not request.is_json:
        return jsonify({"success": False, "error": "Request must be JSON"}), 400

    data = request.get_json()
    code = data.get("code")

    if not code:
        return jsonify({"success": False, "error": "Missing 'code' in request"}), 400

    definitions = get_definitions_from_file(code_string=code)
    print(definitions)

    workers = definitions.get("workers", [])
    if len(workers) != 1:
        return jsonify({"success": False, "error": "Expected exactly one worker"}), 200

    worker = workers[0]

    return jsonify({"success": True, "worker": worker}), 200


if is_development:

    @app.route("/api/export-transformed", methods=["POST"])
    def export_transformed_graph():
        """
        Accepts pre-transformed graph data (nodes with className, edges with names)
        and generates/validates the Python code. Intended for E2E testing.
        """
        if not request.is_json:
            return jsonify({"success": False, "error": "Request must be JSON"}), 400

        graph_data = request.get_json()
        if not graph_data or "nodes" not in graph_data or "edges" not in graph_data:
            return (
                jsonify({"success": False, "error": "Invalid graph data format"}),
                400,
            )

        # Directly generate code from the pre-transformed data
        python_code, module_name, error_json = generate_python_module(
            graph_data, debug_print=is_development
        )

        if error_json:
            # Generation itself failed, return the error JSON from generate_python_module
            return jsonify(error_json), 400  # Or 500?

        if python_code is None or module_name is None:
            # Should ideally be caught by error_json, but as a fallback
            return (
                jsonify(
                    {"success": False, "error": "Code generation failed silently."}
                ),
                500,
            )

        # --- Validation is NOT needed for this E2E test endpoint ---
        # validation_result = validate_code_in_venv(module_name, python_code)

        # Construct the final response - just return the code
        response_data = {
            "success": True,
            "python_code": python_code,
            # "validation_result": validation_result # Removed
        }

        return jsonify(response_data), 200  # Always 200 if generation succeeds


# Serve Svelte static files - ONLY add this route if NOT in development
if not is_development:

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve(path):
        # Use app.static_folder which is now package_static_dir
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            # Serve the specific file if it exists (e.g., CSS, JS, images)
            return send_from_directory(app.static_folder, path)
        # Check if the path looks like a file extension, if not, serve index.html
        elif "." not in path:
            # Serve index.html for SPA routing (handles page reloads and paths like /about)
            return send_from_directory(app.static_folder, "index.html")
        else:
            # Serve index.html for SPA routing (handles page reloads)
            return send_from_directory(app.static_folder, "index.html")


# Main execution block - Refactored to be callable by entry point
def main():
    parser = ArgumentParser()
    parser.add_argument("--root-path", type=Path, default=None)
    args = parser.parse_args()
    if args.root_path:
        setup_filesystem(app, args.root_path)
    else:
        setup_filesystem(app, Path.cwd())

    print(f"Starting Flask-SocketIO server in {FLASK_ENV} mode...")
    # Use different settings for development vs production
    run_config = {
        "app": app,
        "host": "localhost",  # Listen only on localhost because of dangerous exposed interfaces
        "port": 5001,
    }
    if is_development:
        run_config["debug"] = True
        run_config["use_reloader"] = True  # Development reloader
    else:
        run_config["debug"] = False
        # use_reloader should generally be False in production when using eventlet/gunicorn
        # run_config["use_reloader"] = False
        print(
            f"Serving application on http://{run_config['host']}:{run_config['port']}"
        )

    # Use eventlet for better performance if available
    try:
        # Verify if eventlet was successfully imported and patched earlier
        import eventlet  # Re-import shouldn't hurt, just checks if it's available  # noqa: F401

        print("Using eventlet WSGI server for socketio.run().")
        if is_development:
            # Eventlet doesn't directly use use_reloader, but Flask's debug mode implies it
            pass  # Debug=True handles this sufficiently with eventlet? Check docs.
        # else: run_config.pop("use_reloader", None) # Not needed when debug=False

        # Eventlet doesn't need debug/reloader passed here when monkey-patched? Test this.
        # socketio.run(app, host=run_config['host'], port=run_config['port']) # Simpler call?
        socketio.run(**run_config)

    except ImportError:
        print(
            "Eventlet not found, using Flask's default development server for socketio.run()."
        )
        # Add back use_reloader=False explicitly for production if not using eventlet
        if not is_development:
            run_config["use_reloader"] = False
        socketio.run(**run_config)


if __name__ == "__main__":
    main()
