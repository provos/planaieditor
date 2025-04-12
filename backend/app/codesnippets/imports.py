# Auto-generated PlanAI module
# prevent black from formatting this file
# fmt: off
import json
import sys
import traceback
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple, Type

from planai import (
    Graph,
    JoinedTaskWorker,
    LLMInterface,
    LLMTaskWorker,
    Task,
    TaskWorker,
    llm_from_config,
)
from pydantic import ConfigDict, Field

# Add any other necessary imports based on worker code (e.g., planai.patterns)

# Task Definitions

{task_definitions}

# Worker Definitions

{worker_definitions}

# --- Graph Setup ---


def create_graph(
    *, llm_fast: LLMInterface, llm_code: LLMInterface, llm_writing: LLMInterface
) -> Tuple[Graph, Dict[str, TaskWorker]]:
    graph = Graph(name="GeneratedPlan")

    # --- Worker Instantiation with Error Handling ---
    workers_dict: Dict[str, TaskWorker] = {{}}
    # Keep track of mapping from generated instance name back to original frontend node ID
    instance_to_node_id: Dict[str, str] = {{}}

    {worker_instantiation}

    # Add graph workers *after* instantiation block
    all_worker_instances = list(workers_dict.values())
    if all_worker_instances:  # Only add if any were successful
        graph.add_workers(*all_worker_instances)
    else:
        raise ValueError("No worker instances were successfully created.")

    {dependency_setup}

    return graph, workers_dict


def setup_graph(
    notify: Optional[Callable[Dict[str, Any], None]] = None,
) -> Tuple[Graph, Dict[str, TaskWorker]]:
    # TODO: Replace with your actual LLM configuration using llm_from_config
    print("Warning: Using dummy LLM configurations. Replace with llm_from_config.")
    # Example: llm_config = {{"provider": "openai", "model": "gpt-3.5-turbo"}}
    # llm_fast = llm_from_config(llm_config)
    llm_fast = llm_code = llm_writing = LLMInterface()  # Placeholder

    graph = None  # Initialize
    workers = None
    try:
        graph, workers = create_graph(
            llm_fast=llm_fast, llm_code=llm_code, llm_writing=llm_writing
        )
    except (
        Exception
    ) as e:  # Catch errors during create_graph itself (e.g., invalid class name, edge setup)
        error_info_dict = {{
                "success": False,
                "error": {{
                    "message": f"Error during graph creation/setup: {{repr(str(e))}}",
                    "nodeName": None,
                    "fullTraceback": traceback.format_exc(),
                }},
            }}

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
        error_info_dict = {{
                "success": False,
                "error":
                    {{
                        "message": "Graph creation failed internally.",
                        "nodeName": None,
                        "fullTraceback": "",
                    }}
            }}
        print("##ERROR_JSON_START##", flush=True)
        print(json.dumps(error_info_dict), flush=True)
        print("##ERROR_JSON_END##", flush=True)
        sys.exit(1)

    return graph, workers


if __name__ == "__main__":
    print("Setting up and running the generated PlanAI graph...")
    graph = None
    workers = None
    try:
        # Pass notify=None for now, can be configured later
        graph, workers = setup_graph(notify=None)
        # If setup completes without error (no sys.exit), print success JSON
        success_info = {{"success": True, "message": "Graph setup successful."}}
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
        error_info_dict = {{
            "success": False,
            "error": {{
                "message": f"Unexpected error in main execution block: {{repr(str(e))}}",
                "nodeName": None,
                "fullTraceback": traceback.format_exc(),
            }},
        }}
        print("##ERROR_JSON_START##", flush=True)
        print(json.dumps(error_info_dict), flush=True)
        print("##ERROR_JSON_END##", flush=True)
    finally:
        print("Script execution finished.")
