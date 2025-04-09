# Auto-generated PlanAI module
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
