import os
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
    """Attempts to execute Python code in a separate virtual environment using a temporary file."""
    # Define the path to the virtual environment's Python executable
    # TODO: Make this configurable
    venv_path = (
        "/Users/provos/src/deepsearch/.venv"  # Hardcoded path to the venv directory
    )
    python_executable = os.path.join(
        venv_path, "bin", "python"
    )  # Assumes Linux/macOS structure

    if not os.path.exists(python_executable):
        error_message = f"Python executable not found at {python_executable}. Please ensure the venv exists and is correctly structured."
        print(error_message)
        return False, error_message

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
            timeout=30,
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
            return True, None
        else:
            error_output = result.stderr or result.stdout or "Unknown execution error"
            print(f"Error validating module '{module_name}' in venv: {error_output}")
            # Construct the error message without complex f-string interpolation
            error_message = (
                "Execution failed with code "
                + str(result.returncode)
                + ":\n"
                + error_output
            )
            return False, error_message

    except subprocess.TimeoutExpired:
        error_message = f"Execution of '{module_name}' timed out."
        print(error_message)
        return False, error_message
    except Exception as e:
        # Format traceback separately before including in the error message
        tb_str = traceback.format_exc()
        error_details = f"Error during validation process for '{module_name}': {e}"
        print(f"{error_details}\n{tb_str}")
        # Combine the message for return
        error_message = f"{error_details}\n{tb_str}"
        return False, error_message
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
    """Receives graph data, generates Python module, attempts to validate it in a separate venv."""
    print(f"Received export_graph event from {request.sid}")
    # You might want to add validation for the 'data' structure here

    python_code, module_name = generate_python_module(data)

    if python_code is None or module_name is None:
        emit(
            "export_result",
            {"success": False, "error": "Failed to generate Python code from graph."},
            room=request.sid,
        )
        return

    # Attempt to validate the generated module in the specified venv
    is_valid, error = validate_code_in_venv(module_name, python_code)

    if not is_valid:
        # Construct error message separately to avoid issues with newlines in f-string
        error_message = f"Generated code failed validation:\n{error}"
        emit(
            "export_result",
            {"success": False, "error": error_message},
            room=request.sid,
        )
    else:
        emit(
            "export_result",
            {
                "success": True,
                "message": f"Successfully generated and validated module '{module_name}' in designated environment.",
            },
            room=request.sid,
        )


if __name__ == "__main__":
    print("Starting Flask-SocketIO server...")
    # Use eventlet for better performance if available
    socketio.run(
        app, debug=True, port=5001, use_reloader=True
    )  # Use a different port than SvelteKit dev server
