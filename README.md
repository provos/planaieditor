# PlanAI Editor

[![Status](https://img.shields.io/badge/status-pre--release-orange)](https://shields.io/) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

A graphical user interface (GUI) for visually building and managing AI workflows using the [PlanAI](https://github.com/provos/planai) framework.

## Overview

This application provides a node-based interface, built with Svelte 5 and svelte-flow, allowing users to:

*   Visually construct PlanAI graphs by creating and connecting Task, TaskWorker, LLMTaskWorker, and JoinedTaskWorker nodes.
*   Configure the properties of each node.
*   Export the designed graph into a Python module compatible with PlanAI.
*   Import existing PlanAI Python modules into the visual editor for modification.

The backend is powered by Python using Flask and Flask-SocketIO to handle graph processing and communication with the PlanAI framework.

## Features

*   **Visual Graph Creation:** Drag and drop interface to build PlanAI workflows.
*   **Python Export:** Generate runnable Python code from your visual graph.
*   **Python Import:** Load existing PlanAI Python files into the editor for visualization and modification. (Backend uses `ast` module for parsing and patching).

## Technologies Used

*   **Frontend:** Svelte 5, SvelteKit, svelte-flow, TypeScript
*   **Backend:** Python 3.10+, Flask, Flask-SocketIO
*   **Core AI Framework:** PlanAI

## Getting Started (Preliminary)

**Prerequisites:**

*   Python 3.10+
*   Node.js and npm

**Installation:**

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd planaieditor
    ```
2.  **Backend Setup:**
    ```bash
    cd backend
    poetry install
    cd ..
    ```
3.  **Frontend Setup:**
    ```bash
    cd frontend
    npm install
    cd ..
    ```

## Usage (Preliminary)

1.  **Run the Backend:**
    ```bash
    cd backend
    poetru run python app.py
    ```
2.  **Run the Frontend:**
    ```bash
    cd frontend
    npm run dev -- --open
    ```

Navigate to the URL provided by the SvelteKit development server (usually `http://localhost:5173`).

## Disclaimer

**This project is currently in a pre-release state.** It is intended for development and testing purposes only and is not officially supported. Features may change, and bugs are expected.

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests. (Optional: Add contribution guidelines if you have them).

## License

Apache 2.0
