# PlanAI Editor Python Backend
This Python backend serves as the server component for the PlanAI Editor application. It provides the following functionality:

1. **Code Generation**: Converts visual graph representations (nodes and edges) from the frontend into executable PlanAI Python code.
2. **Module Loading**: Dynamically loads and validates the generated Python modules to ensure they are syntactically correct.
3. **WebSocket Communication**: Uses Flask-SocketIO to establish real-time communication with the frontend for sending graph data and receiving generated code.

## Key Components

- **Flask Application**: Serves as the main web server
- **SocketIO**: Handles real-time bidirectional communication with the frontend
- **Code Generation**: Transforms visual graph data into Python code with proper imports, task definitions, worker definitions, and graph setup
- **Black Formatter**: Ensures generated code follows consistent formatting standards

## API Endpoints

The backend primarily communicates through WebSocket events:
- `connect`: Handles client connections
- `disconnect`: Handles client disconnections
- `export_graph`: Receives graph data from the frontend, generates Python code, and attempts to load it
- `export_result`: Sends the result of the code generation and loading process back to the frontend

## Running the Backend

The server runs on port 5001 by default, separate from the SvelteKit frontend development server.
