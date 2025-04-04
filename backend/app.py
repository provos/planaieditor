from flask import Flask, request
from flask_socketio import SocketIO, emit
import importlib.util
import sys
import os
import traceback

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!' # Change this in production!
socketio = SocketIO(app, cors_allowed_origins="*") # Allow requests from frontend dev server

# Placeholder function - replace with your actual graph to Python conversion logic
def generate_python_module(graph_data):
    """
    Converts the graph data (nodes, edges) into executable Python code.

    Args:
        graph_data (dict): Dictionary containing 'nodes' and 'edges'.

    Returns:
        tuple: (python_code_string, suggested_module_name)
               Returns (None, None) if conversion fails.
    """
    print("Generating Python module for graph:")
    # print(graph_data) # Uncomment to see the received data

    # --- Replace this with your actual conversion logic ---
    # Example: Create a simple module based on node names
    nodes = graph_data.get('nodes', [])
    module_name = "generated_plan"
    python_code = f"# Auto-generated PlanAI module\n\n"
    python_code += "print('Hello from the generated module!')\n\n"
    python_code += "class GeneratedPlan:\n"
    if not nodes:
        python_code += "    pass\n"
    else:
        for node in nodes:
            node_id = node.get('id', 'unknown_node')
            python_code += f"    def task_{node_id.replace('-', '_')}(self):\n"
            python_code += f"        print('Executing task {node_id}')\n"
            python_code += f"        pass\n"
    # --- End of replacement section ---
    
    print(f"Generated code for module: {module_name}")
    print(python_code)
    # print(python_code) # Uncomment to see the generated code
    return python_code, module_name

# Function to safely load the generated code as a module
def load_module_from_string(module_name, code_string):
    """Attempts to load Python code as a module."""
    module_path = f"{module_name}.py"
    try:
        # Write the code to a temporary file
        with open(module_path, 'w') as f:
            f.write(code_string)

        # Dynamically import the module
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not create module spec for {module_name}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module # Add to sys.modules before execution
        spec.loader.exec_module(module)
        print(f"Successfully loaded module '{module_name}'")
        return module, None # Return module and no error
    except Exception as e:
        print(f"Error loading module '{module_name}': {e}")
        print(traceback.format_exc())
        # Ensure the failed module is removed from sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]
        return None, traceback.format_exc() # Return no module and the error traceback
    finally:
        # Clean up the temporary file
        if os.path.exists(module_path):
            os.remove(module_path)


@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('export_graph')
def handle_export_graph(data):
    """Receives graph data, generates Python module, attempts to load it."""
    print(f"Received export_graph event from {request.sid}")
    # You might want to add validation for the 'data' structure here

    python_code, module_name = generate_python_module(data)

    if python_code is None or module_name is None:
        emit('export_result', {'success': False, 'error': 'Failed to generate Python code from graph.'})
        return

    # Attempt to load the generated module
    _, error = load_module_from_string(module_name, python_code)

    if error:
        emit('export_result', {'success': False, 'error': f"Failed to load generated module:\n{error}"})
    else:
        emit('export_result', {'success': True, 'message': f"Successfully generated and loaded module '{module_name}'."})


if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Use eventlet for better performance if available
    socketio.run(app, debug=True, port=5001, use_reloader=True) # Use a different port than SvelteKit dev server 