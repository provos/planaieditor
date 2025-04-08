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
    """Attempts to execute Python code in a separate venv and returns structured error info."""
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

        # Check if the execution was successful (exit code 0)
        if result.returncode == 0:
            print(f"Successfully validated '{module_name}' in venv '{venv_path}'")
            return {"success": True}  # Return success structure
        else:
            # Parse stderr for node name and error message
            error_output = result.stderr or result.stdout or "Unknown execution error"
            lines = error_output.strip().split("\n")
            core_error_message = lines[-1] if lines else "Unknown execution error line."

            # Regex to find potential class/worker names (e.g., Task1, LLMTaskWorker3)
            # Looks for assignments like 'workerName =' or class instantiations 'workerName(...)'
            name_regex = (
                r"\b([A-Za-z_][A-Za-z0-9_]*?)(?:Task|Worker)\d+\b(?:\s*=|\s*\()"
            )
            found_node_name = None
            matches = re.findall(name_regex, error_output)
            if matches:
                # Use the first match found in the traceback as the likely source
                # This assumes the error happens during instantiation or use of the generated class
                found_node_name = matches[0]  # Get the first captured group
                # Simple heuristic: remove common prefixes if they exist for cleaner matching
                if (
                    found_node_name.startswith("l")
                    and len(found_node_name) > 1
                    and found_node_name[1].isupper()
                ):
                    found_node_name = found_node_name[
                        1:
                    ]  # Crude way to handle 'lLMTaskWorker1' -> 'LMTaskWorker1'

            print(
                f"Error validating module '{module_name}' in venv. Node found: {found_node_name}, Error: {core_error_message}"
            )
            # Return structured error
            return {
                "success": False,
                "error": {
                    "message": core_error_message,
                    "nodeName": found_node_name,
                    "fullTraceback": error_output,
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
