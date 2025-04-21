import importlib
import inspect
import json
import sys
import traceback
from pathlib import Path


# Add the directory containing the module to the Python path
# This might need adjustment based on how module_path is provided
def add_module_path(module_path):
    # Convert module path (e.g., my_package.my_module) to directory path
    parts = module_path.split(".")
    # Attempt to find the base directory of the module
    # This is a simplification and might not cover all package structures
    current_dir = Path.cwd()  # Or a more relevant base path if needed
    module_dir = current_dir
    # Find the first part that is likely a directory
    for i in range(len(parts)):
        potential_path = current_dir / "/".join(parts[: i + 1])
        if potential_path.is_dir():
            module_dir = potential_path
            break
        elif (potential_path.parent / (parts[i] + ".py")).is_file():
            module_dir = potential_path.parent
            break
    # Try adding common locations relative to a potential project root
    possible_roots = [module_dir, module_dir.parent, Path.cwd(), Path.cwd().parent]
    for root in possible_roots:
        if root not in sys.path:
            sys.path.insert(0, str(root))
        # Also check for a possible 'src' directory
        src_dir = root / "src"
        if src_dir.is_dir() and str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))


def is_planai_task(cls):
    try:
        # Attempt to import planai.Task dynamically
        # This assumes planai is installed in the target environment
        planai_module = importlib.import_module("planai")
        Task = getattr(planai_module, "Task", None)
        if Task is None:
            return False  # planai or planai.Task not found
        return issubclass(cls, Task) and cls is not Task
    except ImportError:
        # planai is not installed in the target environment
        return False
    except TypeError:
        # Handle cases where cls is not a class (e.g., a function)
        return False


def get_pydantic_fields(cls):
    if not hasattr(cls, "model_fields") or not isinstance(cls.model_fields, dict):
        return []  # Not a Pydantic model or no fields

    fields_data = []
    for name, field_info in cls.model_fields.items():
        field_type = field_info.annotation
        is_list = False
        is_optional = False
        type_name = "unknown"
        literal_values = None

        origin = getattr(field_type, "__origin__", None)
        args = getattr(field_type, "__args__", [])

        # Handle Optional[...]
        if origin is Union and type(None) in args:
            is_optional = True
            # Get the actual type from Optional[ActualType, None]
            non_none_args = [t for t in args if t is not type(None)]
            if len(non_none_args) == 1:
                field_type = non_none_args[0]
                # Update origin and args for potential List/Literal checks
                origin = getattr(field_type, "__origin__", None)
                args = getattr(field_type, "__args__", [])
            else:
                # Handle Optional[Union[...]] - complex, default to string
                type_name = "str"  # Or represent Union? For now, simplify.
                origin = None  # Reset origin to stop further processing

        # Handle List[...]
        if origin is list or origin is List:
            is_list = True
            if args:
                field_type = args[0]  # Get the inner type
                # Update origin and args again for potential Literal check inside List
                origin = getattr(field_type, "__origin__", None)
                args = getattr(field_type, "__args__", [])
            else:
                # List without type specified, default inner to Any/str
                field_type = str  # Default to string

        # Handle Literal[...]
        if origin is Literal:
            type_name = "literal"
            # Extract literal values, converting non-strings might be needed
            literal_values = [str(v) for v in args]
        elif hasattr(field_type, "__name__"):
            type_name = field_type.__name__
            # Map common Python types back to frontend identifiers if needed
            type_mapping_reverse = {
                "str": "string",
                "int": "integer",
                "float": "float",
                "bool": "boolean",
            }
            type_name = type_mapping_reverse.get(type_name, type_name)
        elif isinstance(field_type, type):
            # Fallback for complex types not handled above
            type_name = str(field_type)  # Use string representation

        fields_data.append(
            {
                "name": name,
                "type": type_name,
                "isList": is_list,
                "required": not is_optional and field_info.is_required(),
                "description": field_info.description,
                "literalValues": literal_values,
            }
        )
    return fields_data


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Missing module path argument."}))
        sys.exit(1)

    module_path = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else "list_classes"
    class_name_arg = sys.argv[3] if len(sys.argv) > 3 else None

    # Attempt to import necessary types dynamically from the target env
    try:
        from typing import Any, List, Literal, Optional, Union  # noqa: F401

        from pydantic import Field  # noqa: F401
    except ImportError as e:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Missing core dependencies (typing, pydantic) in the selected environment: {e}",
                }
            )
        )
        sys.exit(1)

    try:
        add_module_path(module_path)
        module = importlib.import_module(module_path)

        if action == "list_classes":
            task_classes = []
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and is_planai_task(obj):
                    task_classes.append(name)
            print(json.dumps({"success": True, "classes": sorted(task_classes)}))

        elif action == "get_fields" and class_name_arg:
            TargetClass = getattr(module, class_name_arg, None)
            if (
                TargetClass
                and inspect.isclass(TargetClass)
                and is_planai_task(TargetClass)
            ):
                fields = get_pydantic_fields(TargetClass)
                print(json.dumps({"success": True, "fields": fields}))
            elif not TargetClass:
                print(
                    json.dumps(
                        {
                            "success": False,
                            "error": f"Class '{class_name_arg}' not found in module '{module_path}'.",
                        }
                    )
                )
            else:
                print(
                    json.dumps(
                        {
                            "success": False,
                            "error": f"Class '{class_name_arg}' is not a valid PlanAI Task.",
                        }
                    )
                )
        else:
            print(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Invalid action '{action}' or missing class name.",
                    }
                )
            )

    except ImportError as e:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"Module '{module_path}' not found or contains import errors: {e}\nTraceback:\n{traceback.format_exc()}",
                }
            )
        )
    except Exception as e:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": f"An unexpected error occurred: {e}\nTraceback:\n{traceback.format_exc()}",
                }
            )
        )
