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
    ChatTaskWorker,
    llm_from_config,
)
from pydantic import ConfigDict, Field, PrivateAttr  # noqa: F401

# {import_statements}

# Task Definitions

# {task_definitions}

# Worker Definitions

# {worker_definitions}

# End Worker Definitions (used for error handling)

# --- Graph Setup ---


def execute_graph():
    graph = Graph(name="GeneratedPlan")

    # --- LLM Configs ---

    # {llm_configs}

    # --- Worker Instantiation with Error Handling ---

    # {worker_instantiation}

    # {dependency_setup}

    print("Graph setup complete.")

    initial_tasks = []

    # {initial_tasks}

    # Run the graph
    if initial_tasks:
        print("Running graph with initial tasks...")
        graph.run(initial_tasks=initial_tasks, display_terminal=False)

        # Get the output from the graph
        output = graph.get_output_tasks()

        # Print the output
        print(output)
    else:
        print("No initial tasks provided.")


if __name__ == "__main__":
    print("Setting up and running the generated PlanAI graph...")
    try:
        # Pass notify=None for now, can be configured later
        execute_graph()
        # If setup completes without error (no sys.exit), print success JSON
        success_info = {"success": True, "message": "Graph setup successful."}
        print("##SUCCESS_JSON_START##", flush=True)
        print(json.dumps(success_info), flush=True)
        print("##SUCCESS_JSON_END##", flush=True)

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
