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
    imported_tasks = {}  # Store details of imported tasks: {className: modulePath}
    task_import_nodes = [n for n in nodes if n.get("type") == "taskimport"]
    task_class_names = {}  # Map node ID to generated Task class name

    # Add imports for TaskImportNodes first
    import_statements = []
    for node in task_import_nodes:
        node_id = node["id"]
        data = node.get("data", {})
        # Read modulePath and className directly from data for taskimport nodes
        module_path = data.get("modulePath")
        class_name = data.get("className")

        if module_path and class_name and is_valid_python_class_name(class_name):
            # Group imports by module path
            if module_path not in imported_tasks:
                imported_tasks[module_path] = set()
            if class_name not in imported_tasks[module_path]:
                imported_tasks[module_path].add(class_name)
                # Store mapping for dependency resolution later
                task_class_names[node_id] = class_name  # Map node ID to class name
            else:
                print(
                    f"Warning: Task '{class_name}' from module '{module_path}' already imported or name collision."
                )
                # Still map the ID even if duplicate import detected
                task_class_names[node_id] = class_name
        else:
            print(
                f"Warning: Invalid or missing import details for node {node['id']}. Module: '{module_path}', Class: '{class_name}'"
            )

    # Generate the import statements from the grouped dictionary
    for module_path, class_names in imported_tasks.items():
        if class_names:
            sorted_class_names = sorted(list(class_names))
            import_statements.append(
                f"from {module_path} import {', '.join(sorted_class_names)}"
            )

    # Add locally defined Task nodes
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
        for node_id, task_name in task_class_names.items():
            if task_name == type_name:
                return task_name

        # If not found by mapping (shouldn't happen if graph is consistent)
        # Check if it was an imported task by name
        # imported_tasks is a list of dicts with 'className' and 'modulePath'
        imported_task_names = [task["className"] for task in imported_tasks]
        if type_name in imported_task_names:
            return type_name

        # Check against the task_class_names generated from TaskImportNodes as well
        # The key in task_class_names is the node ID, the value is the className
        # We need to check if the type_name matches any value in task_class_names
        if type_name in task_class_names.values():
            return type_name

        raise ValueError(
            f"Could not find Task definition or import for type '{type_name}'"
        )

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
            "subgraphworker",
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
            factory_function = data.get("factoryFunction")

            if not is_valid_python_class_name(worker_name):
                raise ValueError(f"Invalid worker name: {worker_name}")

            worker_classes[node_id] = worker_name  # Store class name

            # Only generate class definition if it's NOT a factory worker
            if not factory_function:
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
                    class_body.append(
                        f"    output_types: List[Type[Task]] = [{types_str}]"
                    )

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
                            signature = (
                                f"def consume_work(self, task: {input_type_hint}):"
                            )
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
                            signature = (
                                f"def post_process(self, task: {output_type_hint}):"
                            )
                        elif method_name == "extra_cache_key":
                            signature = f"def extra_cache_key(self, task: {input_type_hint}) -> str:"
                        # Add more method signatures as needed
                        else:
                            # Fallback: try to extract signature from source (simple cases)
                            match = re.match(
                                r"^\s*def\s+(\w+)\s*\((.*?)\):", method_source
                            )
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
                        if not body_lines or all(
                            not line.strip() for line in body_lines
                        ):
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

    # Track factory-created workers for special handling and imports
    factory_created_workers = {}
    factories_used = set()  # Track factory function names used

    if not worker_classes:
        worker_setup.append("# No workers to instantiate")
    else:
        # Iterate through all worker nodes, not just the classes map
        for node in worker_nodes:
            node_id = node["id"]
            data = node.get("data", {})
            worker_class_name = data.get("className")
            factory_function = data.get("factoryFunction")
            worker_type = node.get("type")

            if not worker_class_name:
                print(f"Warning: Skipping node {node_id} due to missing className.")
                continue

            instance_name = worker_to_instance_name(worker_class_name)
            worker_names.append(instance_name)  # Keep track of all instance names

            # Check if this is a factory-created worker
            if factory_function and worker_type == "subgraphworker":
                # Handle factory-created SubGraphWorker
                factory_created_workers[worker_class_name] = {
                    "factoryFunction": factory_function,
                    "instanceName": instance_name,
                    "node": node,
                }
                factories_used.add(factory_function)  # Track factory usage for imports

                # Retrieve pre-unparsed arguments from the data
                factory_args_strings = data.get("factoryArgsStrings", [])
                factory_keywords_strings = data.get("factoryKeywordsStrings", {})

                # Combine arguments for the call string
                all_args = list(factory_args_strings)
                all_args.extend(
                    [f"{k}={v}" for k, v in factory_keywords_strings.items()]
                )
                combined_args_string = ", ".join(all_args)

                # Wrap instantiation in try-except
                worker_setup.append(
                    f"\n# Create SubGraphWorker using {factory_function}"
                )
                worker_setup.append("try:")
                # Use the directly reconstructed argument string
                worker_setup.append(
                    f"  {instance_name} = {factory_function}({combined_args_string})"
                )
                worker_setup.append(
                    f"  workers_dict['{instance_name}'] = {instance_name}"
                )
                worker_setup.append("except Exception as e:")
                worker_setup.append(
                    f'  error_info_dict = {{ "success": False, "error": {{ "message": f"Failed to create {worker_class_name} using {factory_function}: {{repr(str(e))}}", "nodeName": "{worker_class_name}", "fullTraceback": traceback.format_exc() }} }}'
                )
                worker_setup.append('  print("##ERROR_JSON_START##", flush=True)')
                worker_setup.append("  print(json.dumps(error_info_dict), flush=True)")
                worker_setup.append('  print("##ERROR_JSON_END##", flush=True)')
                worker_setup.append("  sys.exit(1)")
            elif not factory_function:  # Only process regular workers here
                # Basic LLM assignment - needs refinement based on node config/needs
                llm_arg = ""
                if worker_type == "llmtaskworker":
                    llm_arg = "llm=llm_code"  # Default to code llm for LLM workers
                elif worker_type == "joinedtaskworker":
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

    # Make sure all worker names are included in add_workers
    if worker_names:  # Only add if there are workers
        worker_setup.append(f"graph.add_workers({', '.join(worker_names)})")
    else:
        worker_setup.append("# No workers instantiated.")

    # --- Generate Code for Dependencies and Entry Point *inside* create_graph ---
    dep_code_lines = []  # Renamed from dep_code_lines
    if not edges:
        dep_code_lines.append("# No edges defined in the graph data.")
    else:
        # Create a lookup for worker instance names by className
        worker_instance_by_class_name = {}
        # Populate lookup using all worker nodes (including factory)
        for node in worker_nodes:
            data = node.get("data", {})
            class_name = data.get("className")
            # Node ID mapping to class name should already exist in worker_classes
            if class_name:
                instance_name = worker_to_instance_name(class_name)
                worker_instance_by_class_name[class_name] = instance_name

        # Create the dependency setting code strings
        for edge in edges:
            source_class_name = edge.get("source")
            target_class_name = edge.get("target")

            # Use the lookup to find the instance names
            source_inst_name = worker_instance_by_class_name.get(source_class_name)
            target_inst_name = worker_instance_by_class_name.get(target_class_name)

            if source_inst_name and target_inst_name:
                dep_code_lines.append(
                    f"    graph.set_dependency({source_inst_name}, {target_inst_name})"
                )
            else:
                print(
                    f"Warning: Could not find worker instances for edge {source_class_name} -> {target_class_name}"
                )

    # Assuming factory functions come from planai.patterns for now
    factory_import_line = ""
    if factories_used:
        sorted_factories = sorted(list(factories_used))
        factory_import_line = (
            f"from planai.patterns import {', '.join(sorted_factories)}"
        )

    final_code = custom_format(
        code_to_format,
        import_statements="\n".join(
            [*import_statements, factory_import_line]
            if factory_import_line
            else import_statements
        ),
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
