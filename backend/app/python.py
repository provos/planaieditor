# Updated function to generate PlanAI Python code from graph data
import json
import os
import re
from pathlib import Path
from textwrap import dedent, indent
from typing import Optional, Tuple

import black
from app.utils import is_valid_python_class_name

CODE_SNIPPETS_DIR = os.path.join(os.path.dirname(__file__), "codesnippets")


def custom_format(template: str, **kwargs) -> str:
    """
    Custom format function that only replaces patterns matching '# {format_key}'.

    Args:
        template: The template string containing format specifiers.
        **kwargs: The format specifiers to replace.

    Returns:
        The formatted string.
    """

    def replace_match(match):
        key = match.group(1)
        if key in kwargs:
            return kwargs[key]
        return match.group(0)  # If key not found, return the original match

    pattern = r"# \{(\w+)\}"
    return re.sub(pattern, replace_match, template)


def return_code_snippet(name):
    """
    Returns a code snippet from the codesnippets directory.
    """
    with Path(CODE_SNIPPETS_DIR, f"{name}.py").open("r", encoding="utf-8") as f:
        return f.read() + "\n\n"


def generate_python_module(
    graph_data: dict,
) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
    """
    Converts the graph data (nodes, edges) into executable PlanAI Python code,
    including internal error handling that outputs structured JSON.

    Args:
        graph_data (dict): Dictionary containing 'nodes' and 'edges'.

    Returns:
        tuple: (python_code_string, suggested_module_name, error_json)
               Returns (None, None, error_json) if conversion fails.
    """
    print("Generating PlanAI Python module from graph data...")
    module_name = "generated_plan"
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    print("--------------------------------")
    print(json.dumps(graph_data, indent=4))

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
            class_name = data.get("className")
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
                    description = field.get("description", "")
                    is_list = field.get("isList", False)
                    literal_values = field.get("literalValues", None)
                    is_required = field.get("required", True)

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

                    # Handle Optional fields
                    if not is_required:
                        py_type = f"Optional[{py_type}]"
                        default_value = "None"
                    else:
                        default_value = "..."

                    # Build Field arguments
                    field_args = []
                    # Always add the default value as first argument
                    field_args.append(default_value)

                    # Add description if we have one
                    if description:
                        # Escape quotes within description if necessary
                        escaped_description = description.replace('"', '\\"')
                        field_args.append(f'description="{escaped_description}"')

                    # Format the complete field with appropriate spacing
                    field_args_str = ", ".join(field_args)
                    tasks.append(
                        f"    {field_name}: {py_type} = Field({field_args_str})"
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
        if n.get("type")
        in (
            "taskworker",
            "llmtaskworker",
            "joinedtaskworker",
            "cachedtaskworker",
            "cachedllmtaskworker",
        )
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
            worker_name = data.get("className")
            if not is_valid_python_class_name(worker_name):
                raise ValueError(f"Invalid worker name: {worker_name}")
            worker_classes[node_id] = worker_name  # Store class name

            # Determine base class based on node type, including cached variants
            base_class = "TaskWorker"  # Default
            if node_type == "llmtaskworker":
                base_class = "LLMTaskWorker"
            elif node_type == "joinedtaskworker":
                base_class = "JoinedTaskWorker"
            elif node_type == "cachedtaskworker":
                base_class = "CachedTaskWorker"
            elif node_type == "cachedllmtaskworker":
                base_class = "CachedLLMTaskWorker"

            workers.append(f"\nclass {worker_name}({base_class}):")
            class_body = []  # Store lines for the current class body

            # --- Process Class Variables ---
            class_vars = data.get("classVars", {})
            # Read output_types from class_vars, not the top-level data
            output_types = class_vars.get("output_types", [])
            # Retrieve specific class variables from the classVars dict
            llm_input_type = class_vars.get("llm_input_type")
            llm_output_type = class_vars.get("llm_output_type")
            join_type = class_vars.get("join_type")
            prompt = class_vars.get("prompt")
            system_prompt = class_vars.get("system_prompt")

            # Handle Output Types
            if output_types:
                types_str = ", ".join(get_task_class_name(t) for t in output_types)
                class_body.append(f"    output_types: List[Type[Task]] = [{types_str}]")

            # Handle LLM Input Type
            if llm_input_type:
                try:
                    input_type_class = get_task_class_name(llm_input_type)
                    class_body.append(
                        f"    llm_input_type: Type[Task] = {input_type_class}"
                    )
                except ValueError:
                    print(
                        f"Warning: Could not find Task definition for llm_input_type '{llm_input_type}' in {worker_name}. Skipping."
                    )

            # Handle LLM Output Type
            if llm_output_type:
                try:
                    output_type_class = get_task_class_name(llm_output_type)
                    class_body.append(
                        f"    llm_output_type: Type[Task] = {output_type_class}"
                    )
                except ValueError:
                    print(
                        f"Warning: Could not find Task definition for llm_output_type '{llm_output_type}' in {worker_name}. Skipping."
                    )

            # Handle Join Type
            if join_type:
                class_body.append(f"    join_type: Type[TaskWorker] = {join_type}")

            # Handle Prompts
            if prompt:
                dedented_prompt = dedent(prompt).strip()
                class_body.append(f'    prompt: str = """{dedented_prompt}"""')
            if system_prompt:
                dedented_sys_prompt = dedent(system_prompt).strip()
                class_body.append(
                    f'    system_prompt: str = """{dedented_sys_prompt}"""'
                )

            # Handle Boolean Flags (use_xml, debug_mode)
            if class_vars.get("use_xml") is True:
                class_body.append("    use_xml: bool = True")
            if class_vars.get("debug_mode") is True:
                class_body.append("    debug_mode: bool = True")

            # --- Process Methods ---
            methods = data.get("methods", {})
            if methods:
                # Determine input type hint for consume_work/consume_work_joined
                input_type_hint = "Task"  # Default
                input_types = data.get("inputTypes", [])
                if input_types:
                    try:
                        input_type_hint = get_task_class_name(input_types[0])
                    except ValueError:
                        print(
                            f"Warning: Could not find Task definition for input type '{input_types[0]}' in {worker_name}. Using default 'Task'."
                        )

                for method_name, method_source in methods.items():
                    # Handle signatures for known methods
                    if method_name == "consume_work":
                        signature = f"def consume_work(self, task: {input_type_hint}):"
                    elif method_name == "consume_work_joined":
                        signature = f"def consume_work_joined(self, tasks: List[{input_type_hint}]):"
                    # Add signatures for other known methods if needed
                    elif method_name == "post_process":
                        # Ensure correct signature, potentially needs input_task too?
                        # Assuming it processes the output task type for now.
                        output_type_hint = "Task"  # Default
                        if (
                            base_class == "LLMTaskWorker"
                            or base_class == "CachedLLMTaskWorker"
                        ):
                            # Try to get llm_output_type
                            llm_output_type_name = class_vars.get("llm_output_type")
                            if llm_output_type_name and isinstance(
                                llm_output_type_name, str
                            ):
                                try:
                                    output_type_hint = get_task_class_name(
                                        llm_output_type_name
                                    )
                                except ValueError:
                                    pass  # Keep default if task not found
                        signature = f"def post_process(self, task: {output_type_hint}):"
                    elif method_name == "extra_cache_key":
                        signature = f"def extra_cache_key(self, task: {input_type_hint}) -> str:"
                    # Add more method signatures as needed
                    else:
                        # Fallback: try to extract signature from source (simple cases)
                        match = re.match(r"^\s*def\s+(\w+)\s*\((.*?)\):", method_source)
                        if match:
                            signature = f"def {match.group(1)}({match.group(2)}):"
                        else:
                            signature = (
                                f"def {method_name}(self, ...):"  # Generic fallback
                            )

                    # Dedent and prepare the body code lines
                    dedented_code = dedent(method_source).strip()
                    body_lines = dedented_code.splitlines()

                    # Remove the signature line if it exists in the source already
                    if body_lines and body_lines[0].strip().startswith(
                        signature.split("(")[0].strip()
                    ):
                        body_lines = body_lines[1:]

                    # Ensure body is not empty
                    if not body_lines or all(not line.strip() for line in body_lines):
                        body_lines = ["pass"]

                    class_body.append(f"\n    {signature}")
                    # Indent each line of the body correctly
                    for line in body_lines:
                        class_body.append(
                            f"        {line.rstrip()}"
                        )  # Indent with 8 spaces

            # --- Process Other Members Source ---
            other_source = data.get("otherMembersSource", None)
            if other_source:
                dedented_other = dedent(other_source).strip()
                if dedented_other:
                    indented_other = indent(dedented_other, "    ").strip()
                    class_body.append("\n    # --- Other Class Members ---")
                    class_body.append(f"    {indented_other}")

            # Add pass if class body is empty
            if not class_body:
                class_body.append("    pass")

            workers.extend(class_body)

    # 4. Graph Creation Function
    worker_setup = []

    worker_names = []

    if not worker_classes:
        worker_setup.append("# No workers to instantiate")
    else:
        for node_id, worker_class_name in worker_classes.items():
            worker_node = next((n for n in nodes if n["id"] == node_id), None)
            if worker_node:
                instance_name = worker_to_instance_name(worker_class_name)
                worker_names.append(instance_name)
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

    worker_setup.append(f"graph.add_workers([{', '.join(worker_names)}])")

    dep_code_lines = []

    # --- Generate Code for Dependencies and Entry Point *inside* create_graph ---
    if not edges:
        dep_code_lines.append("# No edges defined in the graph data.")
    else:
        # Create the dependency setting code strings
        for edge in edges:
            source_class_name = edge.get("source")
            target_class_name = edge.get("target")

            # Find the nodes by matching the CLASS NAME stored in their data
            source_node = next(
                (
                    n
                    for n in worker_nodes
                    if n.get("data", {}).get("className") == source_class_name
                ),
                None,
            )
            target_node = next(
                (
                    n
                    for n in worker_nodes
                    if n.get("data", {}).get("className") == target_class_name
                ),
                None,
            )

            if source_node and target_node:
                # Get the definitive class name (already validated)
                source_worker_class = source_node.get("data", {}).get("className")
                target_worker_class = target_node.get("data", {}).get("className")

                if source_worker_class and target_worker_class:
                    source_inst_name = worker_to_instance_name(source_worker_class)
                    target_inst_name = worker_to_instance_name(target_worker_class)

                    dep_code_lines.append(
                        f"    graph.set_dependency({source_inst_name}, {target_inst_name})"
                    )
                else:
                    print(
                        f"Warning: Could not retrieve class names for edge {source_class_name} -> {target_class_name}"
                    )
            else:
                print(
                    f"Warning: Could not find nodes for edge {source_class_name} -> {target_class_name}"
                )

    final_code = custom_format(
        code_to_format,
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
        return formatted_code, module_name, None
    except black.InvalidInput as e:
        print(f"Error formatting generated code with black: {e}")
        print("--- Generated Code (Unformatted) ---")
        print(final_code)
        print("--- End Generated Code (Unformatted) ---")
        return (
            None,
            None,
            {
                "success": False,
                "error": {
                    "message": f"Error formatting generated code with black: {e}",
                    "nodeName": None,
                    "fullTraceback": None,
                },
            },
        )


def worker_to_instance_name(worker_class_name: str) -> str:
    return worker_class_name.lower() + "_worker"
