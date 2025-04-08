# Updated function to generate PlanAI Python code from graph data
from textwrap import dedent, indent

import black

from app.utils import is_valid_python_class_name


def generate_python_module(graph_data):
    """
    Converts the graph data (nodes, edges) into executable PlanAI Python code.

    Args:
        graph_data (dict): Dictionary containing 'nodes' and 'edges'.

    Returns:
        tuple: (python_code_string, suggested_module_name)
               Returns (None, None) if conversion fails.
    """
    print("Generating PlanAI Python module from graph data...")
    module_name = "generated_plan"
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    print("--------------------------------")
    print(graph_data)

    # --- Code Generation Start ---
    code = []

    # 1. Imports
    code.append(
        dedent(
            """
        # Auto-generated PlanAI module
        import sys
        from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple, Type
        from planai import Graph, LLMInterface, Task, TaskWorker, LLMTaskWorker, JoinedTaskWorker, llm_from_config
        from pydantic import Field, ConfigDict
        # Add any other necessary imports based on worker code (e.g., planai.patterns)
    """
        )
    )

    # 2. Task Definitions (from 'task' nodes)
    code.append("\n# --- Task Definitions ---")
    task_nodes = [n for n in nodes if n.get("type") == "task"]
    task_class_names = {}  # Map node ID to generated Task class name
    if not task_nodes:
        code.append("# No Task nodes defined in the graph.")
    else:
        for node in task_nodes:
            node_id = node["id"]
            data = node.get("data", {})
            class_name = data.get("className", f"Task_{node_id}")
            if not is_valid_python_class_name(class_name):
                raise ValueError(f"Invalid class name: {class_name}")
            task_class_names[node_id] = class_name
            code.append(f"\nclass {class_name}(Task):")
            fields = data.get("fields", [])
            if not fields:
                code.append("    pass # No fields defined")
            else:
                # Add ConfigDict for arbitrary_types_allowed if needed later
                # code.append("    model_config = ConfigDict(arbitrary_types_allowed=True)")
                for field in fields:
                    field_name = field.get("name", "unnamed_field")
                    field_type = field.get("type", "Any")  # Default to Any
                    description = field.get("description", "No description")
                    # Basic type mapping (can be expanded)
                    match field_type.lower():
                        case "string":
                            py_type = "str"
                        case "integer":
                            py_type = "int"
                        case "float":
                            py_type = "float"
                        case "boolean":
                            py_type = "bool"
                        case _:
                            py_type = "Any"

                    if field.get("isList", False):
                        py_type = f"List[{py_type}]"

                    code.append(
                        f'    {field_name}: {py_type} = Field(..., description="{description}")'
                    )

    # Helper to map frontend type names (like 'TaskA') to generated Task class names
    def get_task_class_name(type_name: str) -> str:
        # Find the task node whose className matches type_name
        print("--------------------------------")
        print(task_class_names)
        for node_id, task_name in task_class_names.items():
            if task_name == type_name:
                return task_name
        raise ValueError(f"Could not find Task definition for type '{type_name}'")

    # 3. Worker Definitions (from worker nodes)
    code.append("\n# --- Worker Definitions ---")
    worker_nodes = [
        n
        for n in nodes
        if n.get("type") in ("taskworker", "llmtaskworker", "joinedtaskworker")
    ]
    worker_instances = {}  # Map node ID to worker instance variable name
    if not worker_nodes:
        code.append("# No Worker nodes defined in the graph.")
    else:
        for node in worker_nodes:
            node_id = node["id"]
            node_type = node["type"]
            data = node.get("data", {})
            worker_name = data.get("workerName", f"Worker_{node_id}")
            if not is_valid_python_class_name(worker_name):
                raise ValueError(f"Invalid worker name: {worker_name}")
            instance_name = (
                worker_name[0].lower() + worker_name[1:]
            )  # e.g., basicTaskWorker
            worker_instances[node_id] = instance_name

            base_class = "TaskWorker"
            extra_args = ""
            if node_type == "llmtaskworker":
                base_class = "LLMTaskWorker"
                # TODO: Map llm_input_type, llm_output_type if specified in data
                # extra_args = ", llm_input_type=..., llm_output_type=..."
            elif node_type == "joinedtaskworker":
                base_class = "JoinedTaskWorker"
                # TODO: Add join_method if specified
                # join_method = data.get('joinMethod', 'merge')

            code.append(f"\nclass {worker_name}({base_class}):")

            # Input/Output Types
            if len(data.get("inputTypes", [])) > 1 and node_type != "mergedtaskworker":
                raise ValueError(
                    f'Only MergedTaskWorker can have multiple input types. Got {len(data.get("inputTypes", []))} for {worker_name}.'
                )
            output_types_str = ", ".join(
                get_task_class_name(t) for t in data.get("outputTypes", [])
            )
            code.append(f"    output_types: List[Type[Task]] = [{output_types_str}]")

            # LLM Specifics
            print("--------------------------------")
            print(data)
            print(data.get("inputTypes", ["Task"]))
            input_type = get_task_class_name(data.get("inputTypes", ["Task"])[0])
            if node_type == "llmtaskworker":
                code.append(f"    llm_input_type: Type[Task] = {input_type}")
                system_prompt = data.get("systemPrompt", "You are a helpful assistant.")
                prompt = data.get("prompt", "# Define your prompt here")
                code.append(f'    system_prompt: str = """{dedent(system_prompt)}"""')
                code.append(f'    prompt: str = """{dedent(prompt)}"""')
                # TODO: Add llm_input_type/llm_output_type mapping
                # llm_input = data.get('llmInputType')
                # llm_output = data.get('llmOutputType')
                # if llm_input: code.append(f"    llm_input_type: Type[Task] = {get_task_class_name(llm_input)}")
                # if llm_output: code.append(f"    llm_output_type: Type[Task] = {get_task_class_name(llm_output)}")

            # Consume Work Method
            consume_work_code = data.get("consumeWork", None)
            if consume_work_code:
                indented_consume_work = indent(dedent(consume_work_code), "        ")
                code.append(f"\n    def consume_work(self, task: {input_type}):")
                code.append(indented_consume_work)
                code.append("\n")

    # 4. Graph Creation Function
    code.append("\n# --- Graph Setup ---")
    code.append(
        "\ndef create_graph(*, llm_fast: LLMInterface, llm_code: LLMInterface, llm_writing: LLMInterface) -> Tuple[Graph, Dict[str, TaskWorker]]:"
    )
    code.append('    graph = Graph(name="GeneratedPlan")')

    code.append("\n    # Worker Instances")
    if not worker_instances:
        code.append("    # No workers to instantiate")
    else:
        for node_id, instance_name in worker_instances.items():
            worker_node = next((n for n in worker_nodes if n["id"] == node_id), None)
            if worker_node:
                worker_class_name = worker_node.get("data", {}).get(
                    "workerName", f"Worker_{node_id}"
                )
                if not is_valid_python_class_name(worker_class_name):
                    raise ValueError(f"Invalid worker name: {worker_class_name}")
                # Basic LLM assignment - needs refinement based on node config/needs
                llm_arg = ""
                if worker_node["type"] == "llmtaskworker":
                    llm_arg = "llm=llm_code"  # Default to code llm for LLM workers
                elif worker_node["type"] == "joinedtaskworker":
                    pass  # Joined workers don't take LLM directly
                else:  # Basic taskworker might sometimes need an LLM? Defaulting to none.
                    pass
                code.append(f"    {instance_name} = {worker_class_name}({llm_arg})")

    code.append(f"\n    all_workers = [{', '.join(worker_instances.values())}]")
    code.append("    graph.add_workers(*all_workers)")

    code.append("\n    # Dependencies (Edges)")
    if not edges:
        code.append("    # No edges defined to set dependencies.")
    else:
        edge_chains = {}  # Store chains like {source_id: [target1_id, target2_id]}
        processed_edges = set()
        for edge in edges:
            source_id = edge.get("source")
            target_id = edge.get("target")
            edge_id = edge.get("id")

            if not source_id or not target_id or edge_id in processed_edges:
                continue

            if source_id not in worker_instances or target_id not in worker_instances:
                print(
                    f"Warning: Edge '{edge_id}' connects non-worker nodes or unknown nodes ({source_id} -> {target_id}). Skipping."
                )
                continue

            source_instance = worker_instances[source_id]
            target_instance = worker_instances[target_id]

            # Build chains: graph.set_dependency(src, tgt1).next(tgt2)...
            if source_id not in edge_chains:
                edge_chains[source_id] = []
            edge_chains[source_id].append(target_instance)
            processed_edges.add(edge_id)

        # Generate the set_dependency calls
        for source_id, targets in edge_chains.items():
            source_instance = worker_instances[source_id]
            dep_str = f"    graph.set_dependency({source_instance}, {targets[0]})"
            if len(targets) > 1:
                dep_str += "".join([f".next({tgt})" for tgt in targets[1:]])
            code.append(dep_str)

    # Determine entry point(s) - nodes with no incoming edges
    target_node_ids = {edge.get("target") for edge in edges if edge.get("target")}
    entry_nodes = [
        node_id
        for node_id, instance in worker_instances.items()
        if node_id not in target_node_ids
    ]

    if not entry_nodes:
        code.append(
            "    # Warning: Could not determine entry point (no worker node without incoming edges)."
        )
        code.append("    entry_worker = None # Set manually if needed")

    elif len(entry_nodes) > 1:
        code.append(
            f"    # Warning: Multiple potential entry points found: {entry_nodes}. Using the first one."
        )
        entry_worker_instance = worker_instances[entry_nodes[0]]
        code.append(f"    graph.set_entry({entry_worker_instance})")
    else:
        entry_worker_instance = worker_instances[entry_nodes[0]]
        code.append(f"    graph.set_entry({entry_worker_instance})")

    code.append(
        "\n    # Return graph and a dictionary mapping instance names to workers for potential use"
    )
    code.append("    workers_dict = {")
    for node_id, instance_name in worker_instances.items():
        code.append(f"        '{instance_name}': {instance_name},")
    code.append("    }")
    code.append("    return graph, workers_dict")

    # 5. Setup Graph Function (Simplified LLM config)
    code.append(
        "\n\ndef setup_graph(notify: Optional[Callable[Dict[str, Any], None]] = None) -> Tuple[Graph, Dict[str, TaskWorker]]:"
    )
    code.append("    # TODO: Replace with your actual LLM configuration")
    code.append("    print('Warning: Using dummy LLM configurations.')")
    code.append("    llm_fast = llm_code = llm_writing = LLMInterface() # Placeholder")
    code.append(
        "\n    graph, workers = create_graph(llm_fast=llm_fast, llm_code=llm_code, llm_writing=llm_writing)"
    )
    code.append("\n    # TODO: Configure sinks if needed, e.g.:")
    code.append("    # response_publisher = workers.get('responsePublisher')")
    code.append("    # if response_publisher:")
    code.append("    #    response_publisher.sink(Response, notify=notify)")
    code.append("\n    return graph, workers")

    # 6. Main Execution Block (Simplified)
    code.append("\n\nif __name__ == '__main__':")
    code.append('    print("Setting up and running the generated PlanAI graph...")')
    code.append("    graph, workers = setup_graph()")

    # --- Code Generation End ---

    final_code = "\n".join(code)

    # Format the generated code using black
    try:
        formatted_code = black.format_str(final_code, mode=black.FileMode())
        print(f"Successfully generated and formatted code for module: {module_name}")
        print("--- Generated Code ---")
        print(formatted_code)
        print("--- End Generated Code ---")
        return formatted_code, module_name
    except black.InvalidInput as e:
        print(f"Error formatting generated code with black: {e}")
        print("--- Generated Code (Unformatted) ---")
        print(final_code)
        print("--- End Generated Code (Unformatted) ---")
        return None, None  # Indicate failure
