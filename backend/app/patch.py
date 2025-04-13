import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Define the base class name we are looking for
TASK_BASE_CLASS = "Task"

# Define known PlanAI Worker base class names (ordered roughly by specificity)
WORKER_BASE_CLASSES = [
    "CachedLLMTaskWorker",
    "CachedTaskWorker",
    "LLMTaskWorker",
    "JoinedTaskWorker",  # Keep for potential future use
    "TaskWorker",
]
# Map to frontend types
WORKER_TYPE_MAP = {
    "CachedLLMTaskWorker": "cachedllmtaskworker",
    "LLMTaskWorker": "llmtaskworker",
    "CachedTaskWorker": "cachedtaskworker",
    "JoinedTaskWorker": "joinedtaskworker",
    "TaskWorker": "taskworker",
}

# Keep the list of all known PlanAI classes for potential future use
# PLANAI_CLASSES = [
#     "Task",
#     "TaskWorker",
#     "LLMTaskWorker",
#     "CachedTaskWorker",
#     "CachedLLMTaskWorker",
#     "JoinedTaskWorker",
#     "MergedTaskWorker",
# ]


def get_ast_from_file(filename: str) -> ast.Module:
    """Parses a Python file and returns its AST."""
    with open(filename, "r") as f:
        code = f.read()
    return ast.parse(code)


def get_class_definitions(parsed_ast: ast.Module) -> List[ast.ClassDef]:
    """Extracts all class definitions from an AST module."""
    return [node for node in parsed_ast.body if isinstance(node, ast.ClassDef)]


def _resolve_base_classes(
    class_def: ast.ClassDef, all_classes: Dict[str, ast.ClassDef]
) -> List[str]:
    """Recursively resolve base class names for a given class definition."""
    base_names = set()
    for base in class_def.bases:
        if isinstance(base, ast.Name):
            base_name = base.id
            base_names.add(base_name)
            # Recursively find bases of the base class if it's in the current AST
            if base_name in all_classes:
                base_names.update(
                    _resolve_base_classes(all_classes[base_name], all_classes)
                )
        # TODO: Handle more complex base class expressions if needed (e.g., attribute access)
    return list(base_names)


def filter_derived_classes(
    class_definitions: List[ast.ClassDef], target_base_class: str
) -> List[ast.ClassDef]:
    """Filters class definitions to find those inheriting from a specific base class."""
    all_classes_map = {cls.name: cls for cls in class_definitions}
    derived_classes = []

    for class_def in class_definitions:
        resolved_bases = _resolve_base_classes(class_def, all_classes_map)
        if target_base_class in resolved_bases:
            derived_classes.append(class_def)

    return derived_classes


def _parse_annotation(
    annotation: ast.expr, known_task_types: Set[str]
) -> Tuple[str, bool, Optional[List[str]], bool]:
    """Parses a type annotation AST node into a type string, list status, and literal values.

    Recognizes basic types, List[...], Optional[...], known custom Task types, and Literal types.
    Returns:
        - Type name (str): The extracted type name
        - Is List (bool): Whether the type is wrapped in List[]
        - Literal values (Optional[List[str]]): Values for Literal types
        - Is Optional (bool): Whether the type is wrapped in Optional[]
    """
    is_list = False
    is_optional = False
    base_type_str = "Any"  # Default type string
    literal_values = None  # For Literal["val1", "val2", ...]

    # Helper to unwrap Optional
    def unwrap_optional(annotation_node):
        nonlocal is_optional
        if (
            isinstance(annotation_node, ast.Subscript)
            and isinstance(annotation_node.value, ast.Name)
            and annotation_node.value.id == "Optional"
        ):
            is_optional = True
            # Extract the inner type
            if isinstance(annotation_node.slice, ast.Name):
                return annotation_node.slice  # Return inner type node
            elif isinstance(annotation_node.slice, ast.Subscript):
                return (
                    annotation_node.slice
                )  # Return inner type node (could be List[str], etc.)
            else:
                # Fallback for other versions
                return annotation_node.slice
        return annotation_node  # Not Optional, return as is

    # Check for and unwrap Optional
    annotation = unwrap_optional(annotation)

    if isinstance(annotation, ast.Name):
        base_type_str = annotation.id
    elif isinstance(annotation, ast.Subscript):
        # Check if it's a Literal type
        if isinstance(annotation.value, ast.Name) and annotation.value.id == "Literal":
            # It's a Literal type, extract the values
            base_type_str = "literal"  # Special frontend type for literals
            literal_values = []

            # Handle different Python versions and AST structures
            if isinstance(annotation.slice, ast.Tuple):
                # Python 3.8: Literal["val1", "val2"]
                for elt in annotation.slice.elts:
                    if isinstance(elt, ast.Constant):
                        literal_values.append(str(elt.value))
                    elif isinstance(elt, ast.Str):  # Python 3.7 and earlier
                        literal_values.append(elt.s)
            elif isinstance(annotation.slice, ast.Constant):
                # Python 3.9+: Literal["val1"]
                literal_values.append(str(annotation.slice.value))
            elif hasattr(annotation.slice, "elts"):
                # Fallback for other versions
                for elt in annotation.slice.elts:
                    if hasattr(elt, "value"):
                        literal_values.append(str(elt.value))
                    elif hasattr(elt, "s"):
                        literal_values.append(elt.s)
            else:
                # Fallback for complex cases - use string parsing
                slice_str = ast.unparse(annotation.slice)
                # Use regex to extract string literals
                string_literals = re.findall(r'"([^"]*)"', slice_str)
                if string_literals:
                    literal_values = string_literals
                else:
                    # Try for numeric literals too
                    numeric_literals = re.findall(r"\b(\d+)\b", slice_str)
                    if numeric_literals:
                        literal_values = numeric_literals

        # Check for List[...] or list[...]
        elif isinstance(annotation.value, ast.Name) and annotation.value.id in (
            "List",
            "list",
        ):
            is_list = True
            # Get the inner type - might be Optional[...] too, so check recursively
            inner_annotation = annotation.slice
            if isinstance(inner_annotation, ast.Name):
                base_type_str = inner_annotation.id
            elif isinstance(
                inner_annotation, ast.Constant
            ):  # Handle List['str'] etc. Python 3.9+
                base_type_str = str(inner_annotation.value)
            elif (
                isinstance(inner_annotation, ast.Subscript)
                and isinstance(inner_annotation.value, ast.Name)
                and inner_annotation.value.id == "Optional"
            ):
                # Handle List[Optional[...]]
                is_optional = True
                # Extract inner type from Optional
                if isinstance(inner_annotation.slice, ast.Name):
                    base_type_str = inner_annotation.slice.id
                else:
                    base_type_str = ast.unparse(inner_annotation.slice)
            else:
                base_type_str = ast.unparse(
                    inner_annotation
                )  # Fallback for complex inner types
        else:
            # Handle other subscripted types like Dict, Union etc. (not Optional, we handled it earlier)
            # For now, just unparse it
            base_type_str = ast.unparse(annotation)
    elif isinstance(
        annotation, ast.Constant
    ):  # Handle string annotations like 'MyTask'
        base_type_str = annotation.value
    else:  # Fallback for more complex annotations
        base_type_str = ast.unparse(annotation)

    # Map to frontend types only if not a Literal type (which we already handled)
    if base_type_str != "literal":
        # Check if the resolved base type is a known custom Task type
        if base_type_str in known_task_types:
            frontend_type = base_type_str  # Return the custom task name directly
        else:
            # Map to frontend primitive types (simple mapping for now)
            type_mapping = {
                "str": "string",
                "int": "integer",
                "float": "float",
                "bool": "boolean",
                # Add other mappings if needed
            }
            # Default to the original base_type_str if not a primitive, could be Any or complex
            frontend_type = type_mapping.get(base_type_str, base_type_str)
    else:
        frontend_type = "literal"  # Keep our special type

    return frontend_type, is_list, literal_values, is_optional


def _get_field_description(node: ast.AnnAssign) -> Optional[str]:
    """Extract description from Field() constructor keywords."""
    # Check for Field call with keywords
    if (
        isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "Field"
    ):
        for keyword in node.value.keywords:
            if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                return keyword.value.value
    return None


def extract_task_fields(
    class_def: ast.ClassDef, source_code: str, known_task_types: Set[str]
) -> List[Dict[str, Any]]:
    """Extracts field definitions (AnnAssign) from a Task class AST node."""
    fields = []

    for node in class_def.body:
        if isinstance(node, ast.AnnAssign):
            field_name = node.target.id if isinstance(node.target, ast.Name) else None
            if not field_name:
                continue  # Skip complex targets for now

            # Debug output
            print("--------------------------------")
            print(ast.unparse(node))
            print(ast.dump(node))

            field_type, is_list, literal_values, is_optional = _parse_annotation(
                node.annotation, known_task_types
            )
            print(f"field_type: {field_type}")
            print(f"is_list: {is_list}")
            print(f"literal_values: {literal_values}")
            print(f"is_optional: {is_optional}")

            # Field is not required if:
            # 1. It has an Optional[] annotation
            # 2. Field has None as first arg in pydantic Field constructor
            is_default_none = False
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "Field"
                and node.value.args
                and isinstance(node.value.args[0], ast.Constant)
                and node.value.args[0].value is None
            ):
                is_default_none = True

            is_required = not (is_optional or is_default_none)
            print(f"is_required: {is_required}")
            print("--------------------------------")

            description = _get_field_description(node)

            # Attempt to get type from annotation if AnnAssign for Field() case
            field_type_str = field_type
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "Field"
                and isinstance(node, ast.AnnAssign)
            ):
                # Try to get a more specific type from the annotation
                annot_type, _, _, _ = _parse_annotation(
                    node.annotation, known_task_types
                )
                if annot_type != "Any":  # Prefer annotation type if not generic 'Any'
                    field_type_str = annot_type

            field_data = {
                "name": field_name,
                "type": field_type_str,  # Use potentially refined type
                "isList": is_list,
                "required": is_required,
                "description": description,
            }

            # Add literal values if present
            if literal_values:
                field_data["literalValues"] = literal_values

            fields.append(field_data)
    return fields


def get_worker_definitions(
    class_definitions: List[ast.ClassDef],
) -> List[Tuple[ast.ClassDef, str]]:
    """
    Identifies class definitions inheriting from known Worker base classes.
    Returns a list of tuples: (ClassDef, worker_type_string).
    The worker_type_string corresponds to the *most specific* base class found.
    """
    all_classes_map = {cls.name: cls for cls in class_definitions}
    worker_definitions = []

    for class_def in class_definitions:
        resolved_bases = _resolve_base_classes(class_def, all_classes_map)
        found_worker_type = None
        # Check against known worker bases in order of specificity
        for base in WORKER_BASE_CLASSES:
            if base in resolved_bases:
                found_worker_type = WORKER_TYPE_MAP.get(
                    base, "taskworker"
                )  # Default fallback
                break  # Found the most specific type

        if found_worker_type:
            worker_definitions.append((class_def, found_worker_type))

    return worker_definitions


def _parse_list_of_types(node: ast.List) -> List[str]:
    """Parses an AST List node expected to contain type names (e.g., [Type1, Type2])."""
    types = []
    for elt in node.elts:
        if isinstance(elt, ast.Name):
            types.append(elt.id)
        elif isinstance(elt, ast.Attribute):  # Handle potential module.Type references
            types.append(ast.unparse(elt))  # Store full name like module.Type
        else:
            # Fallback for complex elements: unparse the node
            types.append(ast.unparse(elt))
    return types


def _parse_type_annotation_name(annotation: Optional[ast.expr]) -> Optional[str]:
    """Parses a type annotation to get the base type name string."""
    if annotation is None:
        return None
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):  # String annotation 'MyType'
        return annotation.value
    # Add more complex parsing if needed (e.g., Subscript like Optional[Type])
    return ast.unparse(annotation)  # Fallback


def extract_worker_details(
    class_def: ast.ClassDef, worker_type: str, source_code: str
) -> Dict[str, Any]:
    """Extracts details from a Worker class AST node."""
    details = {
        "className": class_def.name,
        "workerType": worker_type,
        "classVars": {},
        "methods": {},
        "otherMembers": {},
    }
    known_method_names = {
        "consume_work",
        "post_process",
        "pre_process",
        "format_prompt",
        "extra_validation",
        "pre_consume_work",
        "extra_cache_key",
    }
    known_class_var_names = {
        "output_types",
        "llm_input_type",
        "llm_output_type",
        "prompt",
        "system_prompt",
        "debug_mode",
        "use_xml",
    }

    for node in class_def.body:
        if isinstance(node, ast.Assign) or isinstance(node, ast.AnnAssign):
            var_name = None
            # Simple assignment: var = value
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
            ):
                var_name = node.targets[0].id
            # Annotated assignment: var: type = value or var: type
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                var_name = node.target.id

            if var_name and var_name in known_class_var_names:
                value_repr = None
                value_node = node.value
                if value_node:
                    if isinstance(value_node, ast.Constant):
                        value_repr = (
                            value_node.value
                        )  # Direct value for str, int, bool, etc.
                    elif (
                        isinstance(value_node, ast.List) and var_name == "output_types"
                    ):
                        value_repr = _parse_list_of_types(value_node)
                    elif isinstance(value_node, ast.Name) and var_name in (
                        "llm_input_type",
                        "llm_output_type",
                    ):
                        value_repr = value_node.id
                    elif isinstance(value_node, ast.Constant) and var_name in (
                        "llm_input_type",
                        "llm_output_type",
                    ):  # String annotation like 'MyTask'
                        value_repr = value_node.value
                    elif (
                        isinstance(value_node, ast.Call)
                        and isinstance(value_node.func, ast.Name)
                        and value_node.func.id == "Field"
                    ):
                        # Handle Pydantic Field for custom worker attributes
                        field_info = {
                            "isField": True,
                            "description": _get_field_description(node),
                        }
                        # Try to get type from annotation if AnnAssign
                        if isinstance(node, ast.AnnAssign):
                            field_info["type"] = _parse_type_annotation_name(
                                node.annotation
                            )
                        # Check for default value (e.g., Field(..., description="..."))
                        if node.value.args:
                            # Might contain default value or description - complex to parse robustly here
                            pass  # Keep it simple for now
                        value_repr = field_info
                    else:
                        # Fallback: unparse the value node
                        try:
                            value_repr = ast.unparse(value_node)
                        except Exception:
                            value_repr = f"<Error unparsing value for {var_name}>"
                details["classVars"][var_name] = value_repr

            elif (
                var_name
            ):  # It's an assignment, but not a known class var - treat as other member
                try:
                    details["otherMembers"][var_name] = ast.unparse(node)
                except Exception:
                    details["otherMembers"][
                        var_name
                    ] = f"<Error unparsing other member {var_name}>"

        elif isinstance(node, ast.FunctionDef):
            method_name = node.name
            try:
                method_source = ast.unparse(node)
            except Exception:
                method_source = f"<Error unparsing method {method_name}>"

            if method_name in known_method_names:
                details["methods"][method_name] = method_source
            else:  # Not a specifically handled method
                details["otherMembers"][method_name] = method_source
        # Could add handling for other node types like Import, If, etc. if needed

    return details


def get_definitions_from_file(filename: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses a Python file, extracts Task and Worker class definitions,
    and formats them into separate lists within a dictionary.
    Returns: {"tasks": [...], "workers": [...]}
    """
    try:
        with open(filename, "r") as f:
            source_code = f.read()
        parsed_ast = ast.parse(source_code)
    except FileNotFoundError:
        print(f"Error: File not found '{filename}'")
        return {"tasks": [], "workers": []}
    except SyntaxError as e:
        print(f"Error: Syntax error parsing '{filename}': {e}")
        return {"tasks": [], "workers": []}
    except Exception as e:
        print(f"Error: Could not read or parse file '{filename}': {e}")
        return {"tasks": [], "workers": []}

    class_definitions = get_class_definitions(parsed_ast)

    # --- Extract Tasks ---
    task_class_definitions = filter_derived_classes(class_definitions, TASK_BASE_CLASS)

    # Get the names of all identified Task classes to pass to the field parser
    known_task_names = {cls.name for cls in task_class_definitions}

    task_results = []
    for class_def in task_class_definitions:
        # Pass the set of known task names to the field extractor
        fields = extract_task_fields(class_def, source_code, known_task_names)
        task_results.append({"className": class_def.name, "fields": fields})

    # --- Extract Workers ---
    worker_definitions_with_type = get_worker_definitions(class_definitions)
    worker_results = []
    for class_def, worker_type in worker_definitions_with_type:
        details = extract_worker_details(class_def, worker_type, source_code)
        worker_results.append(details)

    return {"tasks": task_results, "workers": worker_results}


# Example usage (optional, can be removed or kept for testing)
def main():
    # Use a relative path or an absolute path accessible by the backend
    # Example: Assume 'examples/harness.py' exists relative to where app.py runs
    # filename = "examples/harness.py"
    filename = "/home/provos/src/deepsearch/deepsearch/interact/harness.py"  # Keep using absolute for now
    # filename = "/home/provos/src/planaieditor/example.py" # Test with another file
    if not filename:
        print("Please provide a filename.")
        return

    definitions = get_definitions_from_file(filename)

    if definitions["tasks"] or definitions["workers"]:
        import json

        print(json.dumps(definitions, indent=2))
    else:
        print(f"No Task or Worker definitions found in '{filename}'.")


if __name__ == "__main__":
    # Simple test execution
    # You might want to pass the filename via command line args in a real scenario
    main()
