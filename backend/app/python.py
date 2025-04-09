# Updated function to generate PlanAI Python code from graph data
import os
from pathlib import Path
from textwrap import dedent, indent

import black
from app.utils import is_valid_python_class_name

CODE_SNIPPETS_DIR = os.path.join(os.path.dirname(__file__), "codesnippets")


def return_code_snippet(name):
    """
    Returns a code snippet from the codesnippets directory.
    """
    with Path(CODE_SNIPPETS_DIR, f"{name}.py").open("r", encoding="utf-8") as f:
        return f.read() + "\n\n"


def generate_python_module(graph_data):
    """
    Converts the graph data (nodes, edges) into executable PlanAI Python code,
    including internal error handling that outputs structured JSON.

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

    # 1. Imports
    code_to_format = return_code_snippet("imports")
    
    # 2. Task Definitions (from 'task' nodes)
    tasks = []
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
            tasks.append(f"\nclass {class_name}(Task):")
            fields = data.get("fields", [])
            if not fields:
                tasks.append("    pass # No fields defined")
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

                    tasks.append(
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
    workers = []
    worker_nodes = [
        n
        for n in nodes
        if n.get("type") in ("taskworker", "llmtaskworker", "joinedtaskworker")
    ]
    worker_classes = {}  # Map node ID to worker class name
    # Instance names will be generated later
    if not worker_nodes:
        workers.append("# No Worker nodes defined in the graph.")
    else:
        for node in worker_nodes:
            node_id = node["id"]
            node_type = node["type"]
            data = node.get("data", {})
            worker_name = data.get("workerName", f"Worker_{node_id}")
            if not is_valid_python_class_name(worker_name):
                raise ValueError(f"Invalid worker name: {worker_name}")
            worker_classes[node_id] = worker_name  # Store class name

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

            workers.append(f"\nclass {worker_name}({base_class}):")

            # Input/Output Types
            if len(data.get("inputTypes", [])) > 1 and node_type != "mergedtaskworker":
                raise ValueError(
                    f'Only MergedTaskWorker can have multiple input types. Got {len(data.get("inputTypes", []))} for {worker_name}.'
                )
            output_types_str = ", ".join(
                get_task_class_name(t) for t in data.get("outputTypes", [])
            )
            workers.append(f"    output_types: List[Type[Task]] = [{output_types_str}]")

            # LLM Specifics
            print("--------------------------------")
            print(data)
            print(data.get("inputTypes", ["Task"]))
            input_type = get_task_class_name(data.get("inputTypes", ["Task"])[0])
            if node_type == "llmtaskworker":
                workers.append(f"    llm_input_type: Type[Task] = {input_type}")
                system_prompt = data.get("systemPrompt", "You are a helpful assistant.")
                prompt = data.get("prompt", "# Define your prompt here")
                workers.append(f'    system_prompt: str = """{dedent(system_prompt)}"""')
                workers.append(f'    prompt: str = """{dedent(prompt)}"""')
                # TODO: Add llm_input_type/llm_output_type mapping
                # llm_input = data.get('llmInputType')
                # llm_output = data.get('llmOutputType')
                # if llm_input: code.append(f"    llm_input_type: Type[Task] = {get_task_class_name(llm_input)}")
                # if llm_output: code.append(f"    llm_output_type: Type[Task] = {get_task_class_name(llm_output)}")

            # Consume Work Method
            consume_work_code = data.get("consumeWork", None)
            if consume_work_code:
                indented_consume_work = indent(dedent(consume_work_code), "        ")
                workers.append(f"\n    def consume_work(self, task: {input_type}):")
                workers.append(indented_consume_work)
                workers.append("\n")
                
    code_to_format = code_to_format.format(
        task_definitions="\n".join(tasks),
        worker_definitions="\n".join(workers),
    )
    
    code = []
    code.append(code_to_format)

    # 4. Graph Creation Function
    code.append("\n# --- Graph Setup ---")
    code.append(
        "\ndef create_graph(*, llm_fast: LLMInterface, llm_code: LLMInterface, llm_writing: LLMInterface) -> Tuple[Graph, Dict[str, TaskWorker]]:"
    )
    code.append('    graph = Graph(name="GeneratedPlan")')

    code.append("\n    # --- Worker Instantiation with Error Handling ---")
    code.append("    workers_dict: Dict[str, TaskWorker] = {}")
    # Keep track of mapping from generated instance name back to original frontend node ID
    code.append("    instance_to_node_id: Dict[str, str] = {}")

    if not worker_classes:
        code.append("    # No workers to instantiate")
    else:
        for node_id, worker_class_name in worker_classes.items():
            worker_node = next((n for n in nodes if n["id"] == node_id), None)
            if worker_node:
                instance_name = worker_class_name[0].lower() + worker_class_name[1:]

                # Basic LLM assignment - needs refinement based on node config/needs
                llm_arg = ""
                if worker_node["type"] == "llmtaskworker":
                    llm_arg = "llm=llm_code"  # Default to code llm for LLM workers
                elif worker_node["type"] == "joinedtaskworker":
                    pass  # Joined workers don't take LLM directly
                else:  # Basic taskworker might sometimes need an LLM? Defaulting to none.
                    pass

                # Wrap instantiation in try-except
                code.append(f"\n    # Instantiate: {worker_class_name}")
                code.append(f"    try:")
                code.append(f"        {instance_name} = {worker_class_name}({llm_arg})")
                code.append(
                    f"        workers_dict['{instance_name}'] = {instance_name}"
                )
                code.append(
                    f"        instance_to_node_id['{instance_name}'] = '{node_id}'"
                )  # Map generated instance name to original node ID
                code.append(f"    except Exception as e:")
                # Format error JSON including the worker_class_name which failed
                # We construct the Python code that will *create* the dictionary string
                # Use repr(str(e)) to safely embed the exception message
                code.append(
                    f'        error_info_dict = {{ "success": False, "error": {{ "message": f"Failed to instantiate {worker_class_name}: {{repr(str(e))}}", "nodeName": "{worker_class_name}", "fullTraceback": traceback.format_exc() }} }}'
                )
                code.append(
                    f'        print("##ERROR_JSON_START##", flush=True)'
                )  # Marker start
                code.append(f"        print(json.dumps(error_info_dict), flush=True)")
                code.append(
                    f'        print("##ERROR_JSON_END##", flush=True)'
                )  # Marker end
                code.append(f"        sys.exit(1)")  # Exit after reporting error

    # Add graph workers *after* instantiation block
    code.append(f"\n    all_worker_instances = list(workers_dict.values())")
    code.append("    if all_worker_instances:")  # Only add if any were successful
    code.append("        graph.add_workers(*all_worker_instances)")
    code.append("    else:")
    code.append(
        '        print("Warning: No worker instances were successfully created.")'
    )

    # --- Generate Code for Dependencies and Entry Point *inside* create_graph ---
    code.append("\n    # Set Dependencies (Edges)")
    code.append("    if not workers_dict:")
    code.append(
        '        print("Warning: Skipping dependency setup as no workers were instantiated.")'
    )
    code.append("    else:")
    if not edges:
        code.append("        # No edges defined in the graph data.")
    else:
        # Create the dependency setting code strings
        dep_code_lines = []
        for edge in edges:
            source_node_id = edge.get("source")
            target_node_id = edge.get("target")

            # Find the instance names corresponding to these node IDs
            # This check happens *at runtime* inside the generated code
            dep_code_lines.append(
                f"        source_inst_name = next((inst for inst, node_id in instance_to_node_id.items() if node_id == '{source_node_id}'), None)"
            )
            dep_code_lines.append(
                f"        target_inst_name = next((inst for inst, node_id in instance_to_node_id.items() if node_id == '{target_node_id}'), None)"
            )
            dep_code_lines.append(
                f"        if source_inst_name in workers_dict and target_inst_name in workers_dict:"
            )
            # Assuming simple one-to-one dependencies for now, not chaining .next()
            dep_code_lines.append(
                f"            try:"
            )  # Add try-except for set_dependency
            dep_code_lines.append(
                f"                graph.set_dependency(workers_dict[source_inst_name], workers_dict[target_inst_name])"
            )
            dep_code_lines.append(f"            except Exception as e:")
            dep_code_lines.append(
                f'                print(f"Warning: Failed to set dependency {{source_inst_name}} -> {{target_inst_name}}: {{e}}")'
            )
            dep_code_lines.append(
                f"        elif source_inst_name or target_inst_name:"
            )  # Only print warning if at least one was expected
            dep_code_lines.append(
                f'            print(f"Warning: Skipping edge {source_node_id} -> {target_node_id} due to failed worker instantiation.")'
            )

        # Add the generated dependency lines to the main code block
        code.extend([f"    {line}" for line in dep_code_lines])

    # --- Generate Code for Entry Point *inside* create_graph ---
    code.append("\n    # Determine Entry Point")
    code.append("    if not workers_dict:")
    code.append(
        '        print("Warning: Cannot set entry point as no workers were instantiated.")'
    )
    code.append("    else:")
    code.append("        target_node_ids_instantiated = set()")
    # Re-calculate target_node_ids based on *successful* workers and valid edges
    if edges:
        code.append(
            "        for edge in " + repr(edges) + ": # Use repr to embed edges data"
        )
        code.append('            source_node_id = edge.get("source")')
        code.append('            target_node_id = edge.get("target")')
        code.append(
            "            source_inst = next((inst for inst, nodeid in instance_to_node_id.items() if nodeid == source_node_id), None)"
        )
        code.append(
            "            target_inst = next((inst for inst, nodeid in instance_to_node_id.items() if nodeid == target_node_id), None)"
        )
        code.append(
            "            if source_inst in workers_dict and target_inst in workers_dict:"
        )
        code.append("                 target_node_ids_instantiated.add(target_node_id)")

    code.append("        entry_node_ids = [")
    code.append("            node_id")
    code.append("            for instance_name, node_id in instance_to_node_id.items()")
    code.append(
        "            if instance_name in workers_dict and node_id not in target_node_ids_instantiated"
    )
    code.append("        ]")

    code.append("        if not entry_node_ids:")
    code.append(
        '            print("Warning: Could not determine entry point among instantiated workers.")'
    )
    code.append("        elif len(entry_node_ids) > 1:")
    code.append(
        '            print(f"Warning: Multiple potential entry points found: {entry_node_ids}. Using the first one: {entry_node_ids[0]}")'
    )
    code.append(
        "            entry_instance_name = next(inst_name for inst_name, nodeid in instance_to_node_id.items() if nodeid == entry_node_ids[0])"
    )
    code.append(
        "            if entry_instance_name in workers_dict:"
    )  # Check before accessing
    code.append("                 graph.set_entry(workers_dict[entry_instance_name])")
    code.append("            else:")
    code.append(
        '                 print(f"Error: Selected entry instance {entry_instance_name} not found in workers_dict.")'
    )
    code.append("        else:")
    code.append("            entry_node_id = entry_node_ids[0]")
    code.append(
        "            entry_instance_name = next(inst_name for inst_name, nodeid in instance_to_node_id.items() if nodeid == entry_node_id)"
    )
    code.append(
        "            if entry_instance_name in workers_dict:"
    )  # Check before accessing
    code.append("                 graph.set_entry(workers_dict[entry_instance_name])")
    code.append("            else:")
    code.append(
        '                 print(f"Error: Selected entry instance {entry_instance_name} not found in workers_dict.")'
    )

    code.append("\n    return graph, workers_dict")

    # 5. Setup Graph Function (Simplified LLM config)
    code.append(
        "\n\ndef setup_graph(notify: Optional[Callable[Dict[str, Any], None]] = None) -> Tuple[Graph, Dict[str, TaskWorker]]:"
    )
    code.append("    # TODO: Replace with your actual LLM configuration")
    code.append("    print('Warning: Using dummy LLM configurations.')")
    code.append("    llm_fast = llm_code = llm_writing = LLMInterface() # Placeholder")

    code.append("\n    graph = None")  # Initialize
    code.append("    workers = None")
    code.append("    try:")
    code.append(
        "        graph, workers = create_graph(llm_fast=llm_fast, llm_code=llm_code, llm_writing=llm_writing)"
    )

    code.append(
        "    except Exception as e:"
    )  # Catch errors during create_graph itself (e.g., edge setup)
    code.append(
        f'        error_info_dict = {{ "success": False, "error": {{ "message": f"Error during graph setup: {{repr(str(e))}}", "nodeName": None, "fullTraceback": traceback.format_exc() }} }}'
    )
    code.append(f'        print("##ERROR_JSON_START##", flush=True)')
    code.append(f"        print(json.dumps(error_info_dict), flush=True)")
    code.append(f'        print("##ERROR_JSON_END##", flush=True)')
    code.append(f"        sys.exit(1)")

    code.append("\n    # TODO: Configure sinks if needed, e.g.:")
    code.append("    # response_publisher = workers.get('responsePublisher')")

    # 6. Main Execution Block (Simplified)
    code.append("\n\nif __name__ == '__main__':")
    code.append('    print("Setting up and running the generated PlanAI graph...")')
    code.append("    try:")
    code.append("        graph, workers = setup_graph()")
    code.append("        # If setup completes without error, print success JSON")
    code.append(
        '        success_info = { "success": True, "message": "Graph setup successful." }'
    )
    code.append(f'        print("##SUCCESS_JSON_START##", flush=True)')
    code.append(f"        print(json.dumps(success_info), flush=True)")
    code.append(f'        print("##SUCCESS_JSON_END##", flush=True)')
    code.append("    except SystemExit:")  # Don't catch sys.exit(1) from inner blocks
    code.append("        pass")
    code.append(
        "    except Exception as e:"
    )  # Catch errors during setup_graph call itself
    code.append(
        f'        error_info_dict = {{ "success": False, "error": {{ "message": f"Error running setup_graph: {{repr(str(e))}}", "nodeName": None, "fullTraceback": traceback.format_exc() }} }}'
    )
    code.append(f'        print("##ERROR_JSON_START##", flush=True)')
    code.append(f"        print(json.dumps(error_info_dict), flush=True)")
    code.append(f'        print("##ERROR_JSON_END##", flush=True)')
    # No sys.exit here, script will end naturally

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
