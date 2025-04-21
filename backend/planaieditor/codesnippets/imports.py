# Auto-generated PlanAI module
import json
import sys
import traceback
from typing import (  # noqa: F401
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
)

from planai import (  # noqa: F401
    CachedLLMTaskWorker,
    CachedTaskWorker,
    Graph,
    InitialTaskWorker,
    JoinedTaskWorker,
    LLMInterface,
    LLMTaskWorker,
    Task,
    TaskWorker,
    llm_from_config,
)
from pydantic import ConfigDict, Field, PrivateAttr  # noqa: F401

# Add any other necessary imports based on worker code (e.g., planai.patterns)

# {import_statements}

# Task Definitions

# {task_definitions}

# Worker Definitions

# {worker_definitions}

# --- Graph Setup ---


def create_graph() -> Graph:
    graph = Graph(name="GeneratedPlan")

    # --- Worker Instantiation with Error Handling ---

    # {worker_instantiation}

    # {dependency_setup}

    return graph


def setup_graph() -> Tuple[Graph, Dict[str, TaskWorker]]:
    # TODO: Replace with your actual LLM configuration using llm_from_config
    print("Warning: Using dummy LLM configurations. Replace with llm_from_config.")

    graph = None  # Initialize
    try:
        graph = create_graph()
    except (
        Exception
    ) as e:  # Catch errors during create_graph itself (e.g., invalid class name, edge setup)
        error_info_dict = {
            "success": False,
            "error": {
                "message": f"Error during graph creation/setup: {repr(str(e))}",
                "nodeName": None,
                "fullTraceback": traceback.format_exc(),
            },
        }

        print("##ERROR_JSON_START##", flush=True)
        print(json.dumps(error_info_dict), flush=True)
        print("##ERROR_JSON_END##", flush=True)
        sys.exit(1)

    # TODO: Configure sinks if needed, e.g.:
    # response_publisher = workers.get('responsePublisher')
    # if response_publisher and notify:
    #     response_publisher.add_sink(notify)

    if graph is None:
        # Handle case where create_graph failed internally and exited
        # This path might not be strictly necessary if create_graph always sys.exits
        error_info_dict = {
            "success": False,
            "error": {
                "message": "Graph creation failed internally.",
                "nodeName": None,
                "fullTraceback": "",
            },
        }
        print("##ERROR_JSON_START##", flush=True)
        print(json.dumps(error_info_dict), flush=True)
        print("##ERROR_JSON_END##", flush=True)
        sys.exit(1)

    return graph


if __name__ == "__main__":
    print("Setting up and running the generated PlanAI graph...")
    graph = None
    try:
        # Pass notify=None for now, can be configured later
        workers = setup_graph()
        # If setup completes without error (no sys.exit), print success JSON
        success_info = {"success": True, "message": "Graph setup successful."}
        print("##SUCCESS_JSON_START##", flush=True)
        print(json.dumps(success_info), flush=True)
        print("##SUCCESS_JSON_END##", flush=True)

        # Optional: Add code here to run the graph if needed for testing
        # print("Graph setup complete. Running graph...")
        # graph.run() # Example run call

    except SystemExit:  # Don't catch sys.exit(1) from inner blocks
        # Errors should have already been printed with JSON markers
        print("Exiting due to error during setup.", file=sys.stderr)
        pass  # Allow the script to terminate
    except Exception as e:  # Catch unexpected errors during the setup_graph call itself
        error_info_dict = {
            "success": False,
            "error": {
                "message": f"Unexpected error in main execution block: {repr(str(e))}",
                "nodeName": None,
                "fullTraceback": traceback.format_exc(),
            },
        }
        print("##ERROR_JSON_START##", flush=True)
        print(json.dumps(error_info_dict), flush=True)
        print("##ERROR_JSON_END##", flush=True)
    finally:
        print("Script execution finished.")
