import ast
import inspect
from typing import Any, Dict, List, Optional, Tuple

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


def _parse_annotation(annotation: ast.expr) -> Tuple[str, bool]:
    """Parses a type annotation AST node into a type string and list status."""
    is_list = False
    base_type = "Any"  # Default type

    if isinstance(annotation, ast.Name):
        base_type = annotation.id
    elif isinstance(annotation, ast.Subscript):
        if isinstance(annotation.value, ast.Name) and annotation.value.id in (
            "List",
            "list",
        ):
            is_list = True
            # Get the inner type
            if isinstance(annotation.slice, ast.Name):
                base_type = annotation.slice.id
            elif isinstance(
                annotation.slice, ast.Constant
            ):  # Handle List[str] etc. Python 3.9+
                base_type = str(annotation.slice.value)
            else:
                base_type = ast.unparse(
                    annotation.slice
                )  # Fallback for complex inner types
        else:
            # Handle other subscripted types like Dict, Optional, Union etc. if needed
            # For now, just unparse it
            base_type = ast.unparse(annotation)
    elif isinstance(
        annotation, ast.Constant
    ):  # Handle string annotations like 'MyClass'
        base_type = annotation.value
    else:  # Fallback for more complex annotations
        base_type = ast.unparse(annotation)

    # Map to frontend types (simple mapping for now)
    type_mapping = {
        "str": "string",
        "int": "integer",
        "float": "float",
        "bool": "boolean",  # Added boolean
        # Add other mappings if needed
    }
    frontend_type = type_mapping.get(
        base_type, "string"
    )  # Default to string if unknown

    return frontend_type, is_list


def _get_field_description(
    node: ast.AnnAssign, source_lines: List[str]
) -> Optional[str]:
    """Extracts a comment description immediately following the field definition."""
    # Check for inline comment on the same line
    line_content = source_lines[node.lineno - 1]
    parts = line_content.split("#", 1)
    if len(parts) > 1:
        comment = parts[1].strip()
        # Check if the comment is associated with this specific assignment
        # This is a heuristic: assumes comment after target/annotation relates to the field
        target_end_col = (
            node.target.end_col_offset
            if hasattr(node.target, "end_col_offset")
            else len(ast.unparse(node.target))
        )
        annotation_end_col = (
            node.annotation.end_col_offset
            if hasattr(node.annotation, "end_col_offset")
            else target_end_col + len(ast.unparse(node.annotation)) + 1
        )  # Approximate
        comment_start_col = line_content.find("#")

        # Only take comment if it starts reasonably close after annotation/value
        # Adjust threshold as needed
        if (
            comment_start_col
            > (node.value.end_col_offset if node.value else annotation_end_col) + 1
        ):
            return comment

    # Could also check for comments on the line above, but that's more complex.
    return None


def extract_task_fields(
    class_def: ast.ClassDef, source_code: str
) -> List[Dict[str, Any]]:
    """Extracts field definitions (AnnAssign) from a Task class AST node."""
    fields = []
    source_lines = source_code.splitlines()

    for node in class_def.body:
        if isinstance(node, ast.AnnAssign):
            field_name = node.target.id if isinstance(node.target, ast.Name) else None
            if not field_name:
                continue  # Skip complex targets for now

            field_type, is_list = _parse_annotation(node.annotation)

            # Determine if required (simple check: no default value implies required)
            # A more robust check could look for Optional[...] or Union[..., None]
            is_required = node.value is None

            description = _get_field_description(node, source_lines)

            fields.append(
                {
                    "name": field_name,
                    "type": field_type,
                    "isList": is_list,
                    "required": is_required,
                    "description": description,
                }
            )
        # TODO: Could potentially parse fields from __init__ as well, but AnnAssign is preferred
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
        # parsed_ast = get_ast_from_file(filename) # Reuse existing function if preferred
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

    results = []
    for class_def in task_class_definitions:
        fields = extract_task_fields(class_def, source_code)
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
