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
        tasks.append("# No Task nodes defined in the graph.")
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
                    field_type_frontend = field.get(
                        "type", "Any"
                    )  # Type from frontend/import
                    description = field.get("description", "No description")
                    is_list = field.get("isList", False)
                    literal_values = field.get("literalValues", None)

                    # Handle Literal types
                    if field_type_frontend == "literal" and literal_values:
                        # Join the literal values with commas, properly quoted for strings
                        # Format properly: Literal["value1", "value2"] or Literal[1, 2, 3]
                        literal_items = []
                        for val in literal_values:
                            # Check if it's numeric by attempting to convert
                            try:
                                float(val)  # If this works, it's numeric
                                # Add numeric value without quotes
                                literal_items.append(val)
                            except ValueError:
                                # Add string value with quotes
                                literal_items.append(f'"{val}"')

                        # Create the Literal type expression
                        py_type = f"Literal[{', '.join(literal_items)}]"
                        # Make sure we add the import for Literal if not already present
                        # We'll handle this at the top of the code generation
                    else:
                        # Map frontend primitive types to Python types
                        primitive_type_mapping = {
                            "string": "str",
                            "integer": "int",
                            "float": "float",
                            "boolean": "bool",
                        }

                        # Check if it's a primitive type
                        if field_type_frontend.lower() in primitive_type_mapping:
                            py_type = primitive_type_mapping[
                                field_type_frontend.lower()
                            ]
                        else:
                            # Assume it's a custom Task type (or Any/other complex type)
                            # Use the name directly, ensure it's a valid identifier if possible
                            # Basic validation: if it contains invalid chars, default to Any
                            if is_valid_python_class_name(field_type_frontend):
                                py_type = field_type_frontend
                            else:
                                print(
                                    f"Warning: Invalid field type '{field_type_frontend}' encountered, defaulting to Any."
                                )
                                py_type = "Any"

                    # Handle List type
                    if is_list:
                        py_type = f"List[{py_type}]"

                    # Handle Optional fields (basic check: !required)
                    # TODO: Enhance based on how optionality is represented in frontend/import
                    if not field.get("required", True):
                        py_type = f"Optional[{py_type}]"
                        default_value = "None"
                    else:
                        default_value = "..."

                    # Include description in Field
                    # Escape quotes within description if necessary

                    if description:
                        escaped_description = description.replace('"', '\\"')
                        field_args = f'description="{escaped_description}"'
                    else:
                        field_args = ""

                    # Assemble the field definition line
                    tasks.append(
                        f"    {field_name}: {py_type} = Field({default_value}, {field_args})"
                    )

    # Helper to map frontend type names (like 'TaskA') to generated Task class names
    def get_task_class_name(type_name: str) -> str:
        # Find the task node whose className matches type_name
        for _, task_name in task_class_names.items():
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
            input_type = get_task_class_name(data.get("inputTypes", ["Task"])[0])
            if node_type == "llmtaskworker":
                workers.append(f"    llm_input_type: Type[Task] = {input_type}")
                system_prompt = data.get("systemPrompt", "You are a helpful assistant.")
                prompt = data.get("prompt", "# Define your prompt here")
                workers.append(
                    f'    system_prompt: str = """{dedent(system_prompt)}"""'
                )
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

    # 4. Graph Creation Function
    worker_setup = []

    if not worker_classes:
        worker_setup.append("# No workers to instantiate")
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
                worker_setup.append(f"\n# Instantiate: {worker_class_name}")
                worker_setup.append("try:")
                worker_setup.append(
                    f"  {instance_name} = {worker_class_name}({llm_arg})"
                )
                worker_setup.append(
                    f"  workers_dict['{instance_name}'] = {instance_name}"
                )
                worker_setup.append(
                    f"  instance_to_node_id['{instance_name}'] = '{node_id}'"
                )  # Map generated instance name to original node ID
                worker_setup.append("except Exception as e:")
                # Format error JSON including the worker_class_name which failed
                # We construct the Python code that will *create* the dictionary string
                # Use repr(str(e)) to safely embed the exception message
                worker_setup.append(
                    f'  error_info_dict = {{ "success": False, "error": {{ "message": f"Failed to instantiate {worker_class_name}: {{repr(str(e))}}", "nodeName": "{worker_class_name}", "fullTraceback": traceback.format_exc() }} }}'
                )
                worker_setup.append(
                    '  print("##ERROR_JSON_START##", flush=True)'
                )  # Marker start
                worker_setup.append("  print(json.dumps(error_info_dict), flush=True)")
                worker_setup.append(
                    '  print("##ERROR_JSON_END##", flush=True)'
                )  # Marker end
                worker_setup.append("  sys.exit(1)")  # Exit after reporting error

    dep_code_lines = []

    # --- Generate Code for Dependencies and Entry Point *inside* create_graph ---
    if not edges:
        dep_code_lines.append("# No edges defined in the graph data.")
    else:
        # Create the dependency setting code strings
        for edge in edges:
            source_node_id = edge.get("source")
            target_node_id = edge.get("target")

            # Find the instance names corresponding to these node IDs
            # This check happens *at runtime* inside the generated code
            dep_code_lines.append(
                f"source_inst_name = next((inst for inst, node_id in instance_to_node_id.items() if node_id == '{source_node_id}'), None)"
            )
            dep_code_lines.append(
                f"target_inst_name = next((inst for inst, node_id in instance_to_node_id.items() if node_id == '{target_node_id}'), None)"
            )
            dep_code_lines.append(
                "if source_inst_name in workers_dict and target_inst_name in workers_dict:"
            )
            # Assuming simple one-to-one dependencies for now, not chaining .next()
            dep_code_lines.append("  try:")  # Add try-except for set_dependency
            dep_code_lines.append(
                "    graph.set_dependency(workers_dict[source_inst_name], workers_dict[target_inst_name])"
            )
            dep_code_lines.append("  except Exception as e:")
            dep_code_lines.append(
                '    print(f"Warning: Failed to set dependency {{source_inst_name}} -> {{target_inst_name}}: {{e}}")'
            )
            dep_code_lines.append(
                "elif source_inst_name or target_inst_name:"
            )  # Only print warning if at least one was expected
            dep_code_lines.append(
                f'  print(f"Warning: Skipping edge {source_node_id} -> {target_node_id} due to failed worker instantiation.")'
            )

    final_code = code_to_format.format(
        task_definitions="\n".join(tasks),
        worker_definitions="\n".join(workers),
        worker_instantiation=indent(dedent("\n".join(worker_setup)), "    ")[4:],
        dependency_setup=indent(dedent("\n".join(dep_code_lines)), "    ")[4:],
    )

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
