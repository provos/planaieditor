import json
import re
from reprlib import repr as smart_repr
from textwrap import dedent, indent
from typing import Any, Dict, List, Optional, Set, Tuple

import black
import isort
from planaieditor.utils import (
    is_valid_python_class_name,
    return_code_snippet,
    split_method_signature_body,
)

VALID_LLM_PROVIDERS = [
    "ollama",
    "remote_ollama",
    "openai",
    "anthropic",
    "gemini",
    "openrouter",
]


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


def create_worker_to_instance_mapping(
    worker_nodes: List[Dict[str, Any]],
) -> Dict[str, str]:
    """
    Creates a mapping of worker class names to instance names.
    """
    # Create a lookup for worker instance names by className
    worker_instance_by_class_name = {}
    # Populate lookup using all worker nodes (including factory)
    for node in worker_nodes:
        data = node.get("data", {})
        class_name = data.get("className")

        if class_name:
            instance_name = worker_to_instance_name(node)
            worker_instance_by_class_name[class_name] = instance_name

    return worker_instance_by_class_name


def create_initial_tasks(
    node: Dict[str, Any],
    worker_nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Creates a datainput task from a node.
    """
    assert node.get("type") == "datainput"
    data = node.get("data", {})
    class_name = data.get("className")
    json_data = data.get("jsonData")

    edge = next(
        (e for e in edges if e.get("source") == "datainput-" + class_name),
        None,
    )
    if not edge:
        print(
            f"Warning: Could not find edge for datainput {class_name}. Skipping initial task creation."
        )
        return None

    worker_instance_by_class_name = create_worker_to_instance_mapping(worker_nodes)
    target_class_name = edge.get("target")
    target_instance_name = worker_instance_by_class_name.get(target_class_name)
    if not target_instance_name:
        print(
            f"Warning: Could not find worker instance for {target_class_name}. Skipping initial task creation."
        )
        return None

    return f"initial_tasks.append(({target_instance_name}, {class_name}.model_validate({json_data})))"


def create_all_graph_dependencies(
    task_nodes: List[Dict[str, Any]],
    task_import_nodes: List[Dict[str, Any]],
    worker_nodes: List[Dict[str, Any]],
    output_nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Creates the dependency setting code for the graph.
    """
    # Map all the task names
    task_names = set()
    for node in task_nodes:
        data = node.get("data", {})
        class_name = data.get("className")
        if class_name:
            task_names.add(class_name)

    # Also add task names from taskimport nodes
    for node in task_import_nodes:
        data = node.get("data", {})
        class_name = data.get("className")
        if class_name:
            task_names.add(class_name)

    # Create a lookup for worker instance names by className
    worker_instance_by_class_name = create_worker_to_instance_mapping(worker_nodes)

    output_nodes_by_class_name = {
        node.get("data", {}).get("className"): node for node in output_nodes
    }

    code = []
    # Create the dependency setting code strings
    for edge in edges:
        source_class_name: str = edge.get("source")
        target_class_name: str = edge.get("target")

        if source_class_name.startswith("datainput-"):
            continue

        # Use the lookup to find the instance names
        source_inst_name = worker_instance_by_class_name.get(source_class_name)
        target_inst_name = worker_instance_by_class_name.get(target_class_name)

        target_type = output_nodes_by_class_name.get(target_class_name, {}).get("type")

        if source_inst_name and target_inst_name:
            code.append(
                f"    graph.set_dependency({source_inst_name}, {target_inst_name})"
            )
        elif source_class_name in task_names and target_inst_name:
            # obsolete
            print(f"Warning: Obsolete edge {source_class_name} -> {target_class_name}")
        elif source_inst_name and target_type == "dataoutput":
            node = output_nodes_by_class_name.get(target_class_name, {})
            node_id = node.get("id")
            class_name = node.get("data", {}).get("className")
            input_types = node.get("data", {}).get("inputTypes", [])
            if input_types:
                # we know that class names are unique in the graph
                sink_code = f"""
                    def callback_{class_name}(unused, task: {input_types[0]}):
                        print(f"Received task from {node_id} for metadata_{class_name}: {{task.model_dump_json()}}")
                        send_debug_event("dataoutput_callback", {{
                            "task": task.model_dump_json(),
                            "node_id": "{node_id}",
                            "input_type": "{input_types[0]}"
                        }})
                    graph.set_sink({source_inst_name}, {input_types[0]}, callback_{class_name})
                    """
                code.append(indent(dedent(sink_code).strip(), "    "))
            else:
                print(
                    f"Warning: Could not find input type for dataoutput node {node_id}"
                )
        else:
            print(
                f"Warning: Could not find worker instances for edge {source_class_name} -> {target_class_name}"
            )

    # Create the entry point setting code strings
    for worker in worker_nodes:
        data = worker.get("data", {})
        is_entry_point = data.get("entryPoint", False)
        class_name = data.get("className")
        if is_entry_point and class_name:
            target_inst_name = worker_instance_by_class_name.get(class_name)
            if target_inst_name:
                code.append(f"    graph.set_entry({target_inst_name})")

    return "\n".join(code)


def add_to_task_import_state(node: Dict[str, Any], imported_tasks: Dict[str, Set[str]]):
    """
    Creates a task import state from a node.

    Args:
        node: The node to create the task import state from.
        imported_tasks: A dictionary of unique imported tasks.
    """
    assert node.get("type") == "taskimport"
    data = node.get("data", {})

    # Skip implicit imports
    if data.get("isImplicit"):
        return None

    # Read modulePath and className directly from data for taskimport nodes
    module_path = data.get("modulePath")
    class_name = data.get("className")

    if module_path and class_name and is_valid_python_class_name(class_name):
        # Group imports by module path
        if module_path not in imported_tasks:
            imported_tasks[module_path] = set()
        if class_name not in imported_tasks[module_path]:
            imported_tasks[module_path].add(class_name)
        else:
            print(
                f"Warning: Task '{class_name}' from module '{module_path}' already imported or name collision."
            )
    else:
        print(
            f"Warning: Invalid or missing import details for node {node['id']}. Module: '{module_path}', Class: '{class_name}'"
        )


def create_task_class(node: Dict[str, Any]) -> Optional[str]:
    """
    Creates a Pydantic Task class from a node.
    """
    assert node.get("type") == "task"
    data = node.get("data", {})
    class_name = data.get("className")
    if not is_valid_python_class_name(class_name):
        raise ValueError(f"Invalid class name: {class_name}")

    code = []
    code.append(f"\nclass {class_name}(Task):")
    fields = data.get("fields", [])
    if not fields:
        code.append("    pass # No fields defined")
        return "\n".join(code)

    # Add ConfigDict for arbitrary_types_allowed if needed later
    # code.append("    model_config = ConfigDict(arbitrary_types_allowed=True)")
    for field in fields:
        field_name = field.get("name", "unnamed_field")
        field_type_frontend = field.get("type", "Any")  # Type from frontend/import
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
                py_type = primitive_type_mapping[field_type_frontend.lower()]
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
        code.append(f"    {field_name}: {py_type} = Field({field_args_str})")

    return "\n".join(code)


def create_worker_class(
    node: Dict[str, Any], add_comment: bool = True
) -> Optional[str]:
    # Determine base class based on node type, including cached variants
    node_type = node.get("type")
    data = node.get("data", {})

    if data.get("factoryFunction"):
        return None

    code = []

    worker_name = data.get("className")
    if not is_valid_python_class_name(worker_name):
        raise ValueError(f"Invalid worker class name: {worker_name}")

    match node_type:
        case "taskworker":
            base_class = "TaskWorker"
        case "llmtaskworker":
            base_class = "LLMTaskWorker"
        case "joinedtaskworker":
            base_class = "JoinedTaskWorker"
        case "chattaskworker":
            base_class = "ChatTaskWorker"
        case _:
            raise ValueError(f"Invalid worker type: {node_type}")

    if data.get("isCached") and node_type in ["llmtaskworker", "taskworker"]:
        base_class = "Cached" + base_class

    if add_comment:
        code.append(f"# Worker class: {worker_name}\n")
    code.append(f"class {worker_name}({base_class}):")
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
    if output_types and node_type != "chattaskworker":
        types_str = ", ".join(get_task_class_name(t) for t in output_types)
        class_body.append(f"    output_types: List[Type[Task]] = [{types_str}]")

    # Handle LLM Input Type
    if llm_input_type:
        input_type_class = get_task_class_name(llm_input_type)
        class_body.append(f"    llm_input_type: Type[Task] = {input_type_class}")
    elif node_type == "llmtaskworker":
        input_type = data.get("inputTypes", [])
        if input_type:
            input_type_class = get_task_class_name(input_type[0])
            class_body.append(f"    llm_input_type: Type[Task] = {input_type_class}")

    # Handle LLM Output Type
    if llm_output_type:
        output_type_class = get_task_class_name(llm_output_type)
        class_body.append(f"    llm_output_type: Type[Task] = {output_type_class}")

    # Handle Join Type
    if join_type:
        class_body.append(f"    join_type: Type[TaskWorker] = {join_type}")

    # Handle Prompts
    if prompt:
        dedented_prompt = dedent(prompt).strip()
        class_body.append(f'    prompt: str = """{dedented_prompt}"""')
    if system_prompt:
        dedented_sys_prompt = dedent(system_prompt).strip()
        class_body.append(f'    system_prompt: str = """{dedented_sys_prompt}"""')

    # Handle Boolean Flags (use_xml, debug_mode)
    if class_vars.get("use_xml") is True:
        class_body.append("    use_xml: bool = True")
    elif class_vars.get("use_xml") is False:
        class_body.append("    use_xml: bool = False")

    if class_vars.get("debug_mode") is True:
        class_body.append("    debug_mode: bool = True")

    # --- Process Other Members Source ---
    other_source = data.get("otherMembersSource", None)
    if other_source:
        dedented_other = dedent(other_source).strip()
        if dedented_other:
            indented_other = indent(dedented_other, "    ").strip()
            if add_comment:
                class_body.append("\n    # --- Other Class Members ---")
            class_body.append(f"    {indented_other}")

    # --- Process Methods ---
    methods = data.get("methods", {})
    if methods:
        # Determine input type hint for consume_work/consume_work_joined
        input_type_hint = "Task"  # Default
        input_types = data.get("inputTypes", [])
        if input_types:
            input_type_hint = get_task_class_name(input_types[0])

        for method_name, method_source in methods.items():
            # Handle signatures for known methods
            if method_name == "consume_work":
                signature = f"def consume_work(self, task: {input_type_hint}):"
            elif method_name == "consume_work_joined":
                signature = (
                    f"def consume_work_joined(self, tasks: List[{input_type_hint}]):"
                )
            # Add signatures for other known methods if needed
            elif method_name == "post_process":
                # Ensure correct signature, potentially needs input_task too?
                # Assuming it processes the output task type for now.
                output_type_hint = "Task"  # Default
                if base_class == "LLMTaskWorker" or base_class == "CachedLLMTaskWorker":
                    # Try to get llm_output_type
                    llm_output_type_name = class_vars.get("llm_output_type")
                    if llm_output_type_name and isinstance(llm_output_type_name, str):
                        output_type_hint = get_task_class_name(llm_output_type_name)
                    else:
                        output_type_hint = output_types[0]

                signature = f"def post_process(self, response: {output_type_hint}, input_task: {input_type_hint}):"
            elif method_name == "extra_cache_key":
                signature = (
                    f"def extra_cache_key(self, task: {input_type_hint}) -> str:"
                )
            # Add more method signatures as needed
            else:
                # For unknown methods, we don't have an expected signature
                signature = None

            # Use the new helper function to split signature and body
            found_signature, body_lines = split_method_signature_body(method_source)

            if found_signature is not None:
                # AST parsing succeeded or fallback used expected_signature
                class_body.append(f"\n    {found_signature}")
                # Indent each line of the body correctly
                for line in body_lines:
                    class_body.append(f"        {line.rstrip()}")
            elif signature is not None:
                # Not signature included, so we use the expected signature
                class_body.append(f"\n    {signature}")
                class_body.append(indent(dedent(method_source).strip(), " " * 8))
            else:
                raise ValueError(f"Failed to parse method: {method_name}")

    # Add pass if class body is empty
    if not class_body:
        class_body.append("    pass")

    code.extend(class_body)

    return "\n".join(code)


def format_python_code(code: str) -> str:
    try:
        isort_config = isort.Config(profile="black")
        sorted_code = isort.code(code, config=isort_config)
        formatted_code = black.format_str(sorted_code, mode=black.FileMode())
        return formatted_code
    except Exception as e:
        print(f"Error formatting code: {e}")
        return code


def wrap_instantiation_in_try_except(
    injected_code: str, worker_class_name: str, error_message: str
) -> str:
    code = []
    code.append("try:")
    code.append(indent(injected_code, "    "))
    code.append("except Exception as e:")
    code.append(
        f'  error_info_dict = {{ "success": False, "error": {{ "message": f"{error_message}: {{repr(str(e))}}", "nodeName": "{worker_class_name}", "fullTraceback": traceback.format_exc() }} }}'
    )
    code.append('  print("##ERROR_JSON_START##", flush=True)')
    code.append("  print(json.dumps(error_info_dict), flush=True)")
    code.append('  print("##ERROR_JSON_END##", flush=True)')
    code.append("  sys.exit(1)")
    return "\n".join(code)


def create_factory_worker_instance(
    node: Dict[str, Any], factories_used: Set[str], wrap_in_try_except: bool = True
) -> str:
    data = node.get("data", {})
    worker_class_name = data.get("className")
    factory_function = data.get("factoryFunction")
    factory_invocation = data.get("factoryInvocation", "")
    instance_name = worker_to_instance_name(node)

    # Handle factory-created SubGraphWorker
    factories_used.add(factory_function)  # Track factory usage for imports

    code = []

    # Wrap instantiation in try-except
    code.append(f"\n# Create SubGraphWorker using {factory_function}")
    # Use the directly retrieved invocation string
    code.append(f"{instance_name} = {factory_function}({factory_invocation})")

    if wrap_in_try_except:
        return wrap_instantiation_in_try_except(
            "\n".join(code),
            worker_class_name,
            f"Failed to create {worker_class_name} using {factory_function}",
        )
    else:
        return "\n".join(code)


def create_worker_instance(
    node: Dict[str, Any],
    llm_name: Optional[str] = None,
    wrap_in_try_except: bool = True,
) -> str:
    data = node.get("data", {})
    worker_class_name = data.get("className")
    instance_name = worker_to_instance_name(node)
    worker_type = node.get("type")

    code = []
    # Wrap instantiation in try-except
    code.append(f"# Instantiate: {worker_class_name}")

    # Basic LLM assignment - needs refinement based on node config/needs
    if worker_type in ["llmtaskworker", "cachedllmtaskworker", "chattaskworker"]:
        if llm_name:
            llm_arg = f"llm={llm_name}"
        else:
            llm_arg = "llm=None"
            llm_config = data.get("llmConfig")

            if llm_config:
                llm_args_list = create_llm_args(llm_config)

                llm_args_str = ", ".join(llm_args_list)
                llm_arg = (
                    f"llm=llm_from_config({llm_args_str})"  # Construct the llm argument
                )

        code.append(f"{instance_name} = {worker_class_name}({llm_arg})")
    else:
        code.append(f"{instance_name} = {worker_class_name}()")

    if wrap_in_try_except:
        return wrap_instantiation_in_try_except(
            "\n".join(code),
            worker_class_name,
            f"Failed to instantiate {worker_class_name}",
        )
    else:
        return "\n".join(code)


def create_llm_args(llm_config: Dict[str, Any]) -> List[str]:
    """
    Generates a list of string arguments (e.g., 'provider="openai"', 'model_name=args.model')
    for an llm_from_config call, based on the structured llmConfig data.
    Handles both literal values and variable/expression references.
    """
    llm_args_list = []

    # Map frontend/config keys to backend llm_from_config keys if different
    key_map = {
        "modelId": "model_name",
        "baseUrl": "host",
        "remoteHostname": "hostname",
        "remoteUsername": "username",
    }

    for frontend_key, backend_key in key_map.items():
        if frontend_key in llm_config:
            llm_config[backend_key] = llm_config.pop(frontend_key)

    for arg_name in llm_config:
        arg_info = llm_config[arg_name]

        value = arg_info["value"]
        is_literal = arg_info.get(
            "is_literal", True
        )  # Default to literal if flag missing?

        if is_literal:
            # Format literals correctly (strings quoted, others not)
            # Use smart_repr for potentially long strings
            formatted_value = smart_repr(value)
            llm_args_list.append(f"{arg_name}={formatted_value}")
        else:
            # Use the value directly as it's a variable/expression
            llm_args_list.append(f"{arg_name}={value}")

    return llm_args_list


def get_task_class_name(type_name: str) -> str:
    return type_name


def generate_python_module(
    graph_data: dict,
    debug_print: bool = False,
) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
    """
    Converts the graph data (nodes, edges) into executable PlanAI Python code,
    including internal error handling that outputs structured JSON.

    Args:
        graph_data (dict): Dictionary containing 'nodes' and 'edges'.
        debug_print (bool): If True, print debug information during generation.

    Returns:
        tuple: (python_code_string, suggested_module_name, error_json)
               Returns (None, None, error_json) if conversion fails.
    """
    # Define conditional print function
    if debug_print:
        dprint = print
    else:

        def dprint(*args, **kwargs):
            pass

    dprint("Generating PlanAI Python module from graph data...")
    module_name = "generated_plan"
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    dprint("--------------------------------")
    dprint(json.dumps(graph_data, indent=4))

    # --- Code Generation Start ---

    # 1. Imports
    mode = graph_data.get("mode", "export")
    code_to_format = return_code_snippet(
        "export_execute" if mode == "execute" else "export_clean"
    )

    imported_tasks = {}  # Store details of imported tasks: {className: modulePath}
    task_import_nodes = [n for n in nodes if n.get("type") == "taskimport"]

    # Add imports for TaskImportNodes first
    import_statements = []
    for node in task_import_nodes:
        add_to_task_import_state(node, imported_tasks)

    # Generate the import statements from the grouped dictionary
    for module_path, class_names in imported_tasks.items():
        if class_names:
            sorted_class_names = sorted(list(class_names))
            import_statements.append(
                f"from {module_path} import {', '.join(sorted_class_names)}"
            )
    # Get the module level imports
    module_level_import_nodes = [
        n for n in nodes if n.get("type") == "modulelevelimport"
    ]
    for node in module_level_import_nodes:
        import_statements.append(node.get("data", {}).get("code"))

    # 2. Task Definitions (from 'task' nodes)
    tasks_code = []
    task_nodes = [n for n in nodes if n.get("type") == "task"]

    # Add locally defined Task nodes
    for node in task_nodes:
        tasks_code.append(create_task_class(node))
    if not task_nodes:
        tasks_code.append("# No Task nodes defined in the graph.")

    # 3. Worker Definitions (from worker nodes)
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
            "chattaskworker",
        )
    ]

    # Instance names will be generated later
    workers = []
    for node in worker_nodes:
        code = create_worker_class(node)
        if code:
            workers.append(code)

    if not workers:
        workers.append("# No Worker nodes defined in the graph.")

    # 4. Graph Creation Function
    worker_setup = []
    worker_names = []
    llm_configs = []
    llm_names_used = set()

    # Track factory-created workers for special handling and imports
    factories_used = set()  # Track factory function names used

    for node in worker_nodes:
        node_id = node["id"]
        data = node.get("data", {})
        worker_class_name = data.get("className")
        factory_function = data.get("factoryFunction")

        if not worker_class_name:
            print(f"Warning: Skipping node {node_id} due to missing className.")
            continue

        instance_name = worker_to_instance_name(node)
        worker_names.append(instance_name)  # Keep track of all instance names

        # Check if this is a factory-created worker
        if factory_function:
            # Handle factory-created SubGraphWorker
            worker_setup.append(
                create_factory_worker_instance(
                    node, factories_used, wrap_in_try_except=mode == "execute"
                )
            )
        else:  # Only process regular workers here
            llm_config = data.get("llmConfig")
            llm_name = data.get("llmConfigVar")
            if llm_config and llm_name and llm_name not in llm_names_used:
                llm_configs.append(
                    f"    {llm_name} = llm_from_config({', '.join(create_llm_args(llm_config))})"
                )
                llm_names_used.add(llm_name)
            worker_setup.append(
                create_worker_instance(
                    node, llm_name, wrap_in_try_except=mode == "execute"
                )
            )

    # Assuming factory functions come from planai.patterns for now
    factory_import_line = ""
    if factories_used:
        sorted_factories = sorted(list(factories_used))
        factory_import_line = (
            f"from planai.patterns import {', '.join(sorted_factories)}"
        )

    # Make sure all worker names are included in add_workers
    if worker_nodes:  # Only add if there are workers
        worker_setup.append(f"graph.add_workers({', '.join(worker_names)})")

    if not worker_setup:
        worker_setup.append("# No workers instantiated.")

    # --- Generate Code for Dependencies and Entry Point *inside* create_graph ---
    output_nodes = [n for n in nodes if n.get("type") == "dataoutput"]

    dep_code_lines = []
    dep_code_lines.append(
        create_all_graph_dependencies(
            task_nodes, task_import_nodes, worker_nodes, output_nodes, edges
        )
    )
    if not dep_code_lines:
        dep_code_lines.append("# No dependencies defined in the graph data.")

    # 5. Initial Tasks
    datainput_nodes = [n for n in nodes if n.get("type") == "datainput"]
    initial_tasks = []
    for node in datainput_nodes:
        inital_task = create_initial_tasks(node, worker_nodes, edges)
        if inital_task:
            initial_tasks.append(inital_task)

    final_code = custom_format(
        code_to_format,
        import_statements="\n".join(
            filter(
                None,
                [  # Filter out empty strings
                    *import_statements,
                    factory_import_line,
                ],
            )
        ),
        task_definitions="\n".join(tasks_code),
        worker_definitions="\n".join(workers),
        llm_configs="\n".join(llm_configs)[4:],
        worker_instantiation=indent(dedent("\n".join(worker_setup)), "    ")[4:],
        dependency_setup=indent(dedent("\n".join(dep_code_lines)), "    ")[4:],
        initial_tasks=indent(dedent("\n".join(initial_tasks)), "    ")[4:],
    )

    # Format the generated code using black
    try:
        isort_config = isort.Config(profile="black")
        sorted_code = isort.code(final_code, config=isort_config)
        formatted_code = black.format_str(sorted_code, mode=black.FileMode())
        dprint(f"Successfully generated and formatted code for module: {module_name}")
        dprint("--- Generated Code ---")
        dprint(formatted_code)
        dprint("--- End Generated Code ---")
        return formatted_code, module_name, None
    except black.InvalidInput as e:
        print(f"Error formatting generated code with black: {e}")
        # cannot parse: 57:14: 'some error message'
        error_match = re.match(r"Cannot parse: (\d+):(\d+): (.*)", str(e))
        worker_name = None
        if error_match:
            line_number = error_match.group(1)
            lines = final_code.split("\n")[: int(line_number) - 1]
            lines.reverse()
            for line in lines:
                if line.strip().startswith("# End Worker Definitions"):
                    break
                if line.strip().startswith("# Worker class: "):
                    worker_name = line.split(": ")[1].strip()
                    break
        return (
            None,
            None,
            {
                "success": False,
                "error": {
                    "message": f"Error formatting generated code with black: {e}",
                    "nodeName": worker_name,
                    "fullTraceback": None,
                },
            },
        )


def worker_to_instance_name(node: Dict[str, Any]) -> str:
    data = node.get("data", {})
    if data.get("variableName"):
        return data.get("variableName")
    worker_class_name = data.get("className")
    return worker_class_name.lower() + "_worker"
