import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple

# Define the base class name we are looking for
TASK_BASE_CLASS = "Task"

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

            field_data = {
                "name": field_name,
                "type": field_type,  # This will now contain primitives, custom Task names, or "literal"
                "isList": is_list,
                "required": is_required,
                "description": description,
            }

            # Add literal values if present
            if literal_values:
                field_data["literalValues"] = literal_values

            fields.append(field_data)
    return fields


def get_task_definitions_from_file(filename: str) -> List[Dict[str, Any]]:
    """
    Parses a Python file, extracts Task class definitions, and formats them.
    Returns a list of dictionaries, where each dict represents a Task class
    with its name and fields.
    """
    try:
        with open(filename, "r") as f:
            source_code = f.read()
        parsed_ast = ast.parse(source_code)
    except FileNotFoundError:
        print(f"Error: File not found '{filename}'")
        return []
    except SyntaxError as e:
        print(f"Error: Syntax error parsing '{filename}': {e}")
        return []
    except Exception as e:
        print(f"Error: Could not read or parse file '{filename}': {e}")
        return []

    class_definitions = get_class_definitions(parsed_ast)
    task_class_definitions = filter_derived_classes(class_definitions, TASK_BASE_CLASS)

    # Get the names of all identified Task classes to pass to the field parser
    known_task_names = {cls.name for cls in task_class_definitions}

    results = []
    for class_def in task_class_definitions:
        # Pass the set of known task names to the field extractor
        fields = extract_task_fields(class_def, source_code, known_task_names)
        results.append({"className": class_def.name, "fields": fields})

    return results


# Example usage (optional, can be removed or kept for testing)
def main():
    # Use a relative path or an absolute path accessible by the backend
    # Example: Assume 'examples/harness.py' exists relative to where app.py runs
    # filename = "examples/harness.py"
    filename = "/home/provos/src/deepsearch/deepsearch/interact/harness.py"  # Keep using absolute for now
    if not filename:
        print("Please provide a filename.")
        return

    task_definitions = get_task_definitions_from_file(filename)

    if task_definitions:
        import json

        print(json.dumps(task_definitions, indent=2))
    else:
        print(f"No Task definitions found in '{filename}'.")


if __name__ == "__main__":
    # Simple test execution
    # You might want to pass the filename via command line args in a real scenario
    main()
