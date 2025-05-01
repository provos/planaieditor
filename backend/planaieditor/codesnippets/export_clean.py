# Auto-generated PlanAI module
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
    execute_graph()
    print("Script execution finished.")
