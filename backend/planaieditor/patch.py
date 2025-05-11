import ast
import re
from textwrap import dedent
from typing import Any, Dict, List, Optional, Set, Tuple

import black
import isort
from planaieditor.utils import return_code_snippet

# Define the base class name we are looking for
TASK_BASE_CLASS = "Task"

# Define known PlanAI Worker base class names (ordered roughly by specificity)
WORKER_BASE_CLASSES = [
    "CachedLLMTaskWorker",
    "CachedTaskWorker",
    "LLMTaskWorker",
    "JoinedTaskWorker",  # Keep for potential future use
    "SubGraphWorker",  # Add SubGraphWorker itself if it can be directly subclassed
    "TaskWorker",
    "ChatTaskWorker",
]
# Map to frontend types
WORKER_TYPE_MAP = {
    "CachedLLMTaskWorker": ("llmtaskworker", True),
    "LLMTaskWorker": ("llmtaskworker", False),
    "CachedTaskWorker": ("taskworker", True),
    "JoinedTaskWorker": ("joinedtaskworker", False),
    "SubGraphWorker": ("subgraphworker", False),  # Map SubGraphWorker
    "TaskWorker": ("taskworker", False),
    "ChatTaskWorker": ("chattaskworker", False),
}

# --- Allow List for Imported Tasks ---
ALLOWED_TASK_IMPORTS: Dict[str, List[str]] = {
    "planai.patterns": [
        "ConsolidatedPages",
        "SearchQuery",
        "SearchResult",
        "FinalPlan",
        "PlanRequest",
    ],
    "planai.patterns.planner": [
        "PlanRequest",
        "FinalPlan",
    ],
    "planai.patterns.search_fetcher": [
        "SearchQuery",
        "SearchResult",
    ],
    "planai": [
        "ChatMessage",
        "ChatTask",
    ],
    # Add modules that might contain Tasks used by subgraphs if needed
}

# --- Configuration for Subgraph Factory Functions ---
SUBGRAPH_FACTORIES: Dict[str, Dict[str, Any]] = {
    "create_planning_worker": {
        "inputTypes": ["PlanRequest"],
        "classVars": {
            "output_types": ["FinalPlan"],
        },
        "defaultClassName": "PlanningWorkerSubgraph",
    },
    "create_search_fetch_worker": {
        "inputTypes": ["SearchQuery"],
        "classVars": {
            "output_types": ["ConsolidatedPages"],
        },
        "defaultClassName": "SearchFetchWorker",
    },
}


def get_ast_from_file(filename: str) -> ast.Module:
    """Parses a Python file and returns its AST."""
    with open(filename, "r") as f:
        code = f.read()
    return ast.parse(code)


def get_import_statements(parsed_ast: ast.Module) -> List[ast.Import]:
    """Extracts all import statements from an AST module."""
    return [node for node in parsed_ast.body if isinstance(node, ast.Import)]


def get_import_from_statements(parsed_ast: ast.Module) -> List[ast.ImportFrom]:
    """Extracts all import statements from an AST module."""
    return [node for node in parsed_ast.body if isinstance(node, ast.ImportFrom)]


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

            field_type, is_list, literal_values, is_optional = _parse_annotation(
                node.annotation, known_task_types
            )

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
) -> List[Tuple[ast.ClassDef, str, bool]]:
    """
    Identifies class definitions inheriting from known Worker base classes.
    Returns a list of tuples: (ClassDef, worker_type_string, is_cached).
    The worker_type_string corresponds to the *most specific* base class found.
    The is_cached boolean indicates if the worker is a cached worker.
    """
    all_classes_map = {cls.name: cls for cls in class_definitions}
    worker_definitions = []

    for class_def in class_definitions:
        resolved_bases = _resolve_base_classes(class_def, all_classes_map)
        found_worker_type = None
        # Check against known worker bases in order of specificity
        for base in WORKER_BASE_CLASSES:
            if base in resolved_bases:
                found_worker_type, is_cached = WORKER_TYPE_MAP.get(
                    base, ("taskworker", False)
                )  # Default fallback
                break  # Found the most specific type

        if found_worker_type:
            worker_definitions.append((class_def, found_worker_type, is_cached))

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


# --- Helper for Input Type Extraction ---


def _get_consume_work_input_type(method_node: ast.FunctionDef) -> Optional[str]:
    """Parses the type hint of the second argument (task) of consume_work."""
    if method_node.name == "consume_work":
        if len(method_node.args.args) > 1:  # Check if there is an arg after self
            task_arg = method_node.args.args[1]
            if task_arg.annotation:
                # Use the existing helper to parse the annotation node
                # We don't need known_task_types here, just the basic name
                input_type_name, _, _, _ = _parse_annotation(task_arg.annotation, set())
                if input_type_name != "Any":
                    return input_type_name
    return None


def _get_joined_consume_work_input_type(method_node: ast.FunctionDef) -> Optional[str]:
    """Parses the List type hint of the second argument (tasks) of consume_work_joined."""
    if method_node.name == "consume_work_joined":
        if len(method_node.args.args) > 1:
            tasks_arg = method_node.args.args[1]
            if tasks_arg.annotation:
                # Use _parse_annotation, expecting a List
                inner_type_name, is_list, _, _ = _parse_annotation(
                    tasks_arg.annotation, set()
                )
                if is_list and inner_type_name != "Any":
                    return inner_type_name  # Return the inner type of the List
    return None


# --- Worker Detail Extraction ---


def extract_worker_details(
    class_def: ast.ClassDef, worker_type: str, source_code: str
) -> Dict[str, Any]:
    """Extracts details from a Worker class AST node.

    Handles special cases like dedent("...").strip() for prompts.
    """
    details = {
        "className": class_def.name,
        "workerType": worker_type,
        "classVars": {},
        "methods": {},
        "otherMembersSource": "",  # Consolidated source for other members
    }
    known_method_names = {
        "consume_work",
        "post_process",
        "pre_process",
        "format_prompt",
        "extra_validation",
        "pre_consume_work",
        "extra_cache_key",
        "consume_work_joined",
    }
    known_class_var_names = {
        "output_types",
        "llm_input_type",
        "llm_output_type",
        "prompt",
        "system_prompt",
        "debug_mode",
        "use_xml",
        "join_type",
    }

    # Helper function to parse potentially complex value assignments
    def parse_value(value_node: Optional[ast.expr], var_name: str) -> Any:
        if not value_node:
            return None

        if var_name in ("prompt", "system_prompt"):
            # Handle dedent("...")
            if (
                isinstance(value_node, ast.Call)
                and isinstance(value_node.func, ast.Name)
                and value_node.func.id == "dedent"
            ):
                return dedent(value_node.args[0].value).strip()

            # Handle dedent("...").strip()
            if (
                isinstance(value_node, ast.Call)
                and isinstance(value_node.func, ast.Attribute)
                and value_node.func.attr == "strip"
                and isinstance(value_node.func.value, ast.Call)
                and isinstance(value_node.func.value.func, ast.Name)
                and value_node.func.value.func.id == "dedent"
                and value_node.func.value.args
                and isinstance(value_node.func.value.args[0], ast.Constant)
            ):
                # Extract the raw string from inside dedent()
                return dedent(value_node.func.value.args[0].value).strip()

        # Standard Constant (str, int, bool, etc.)
        if isinstance(value_node, ast.Constant):
            return value_node.value
        # List of types (e.g., output_types)
        if isinstance(value_node, ast.List) and var_name == "output_types":
            return _parse_list_of_types(value_node)
        # Simple type name (e.g., llm_input_type)
        if isinstance(value_node, ast.Name) and var_name in (
            "llm_input_type",
            "llm_output_type",
            "join_type",
        ):
            return value_node.id
        # String annotation for type name
        if isinstance(value_node, ast.Constant) and var_name in (
            "llm_input_type",
            "llm_output_type",
            "join_type",
        ):
            return value_node.value
        # Pydantic Field
        if (
            isinstance(value_node, ast.Call)
            and isinstance(value_node.func, ast.Name)
            and value_node.func.id == "Field"
        ):
            field_info = {"isField": True, "description": _get_field_description(node)}
            if isinstance(node, ast.AnnAssign):
                field_info["type"] = _parse_type_annotation_name(node.annotation)
            # Could add default value parsing here if needed
            return field_info
        # Fallback: unparse the node
        try:
            return ast.unparse(value_node)
        except Exception:
            return f"<Error unparsing value for {var_name}>"

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
                    value_repr = parse_value(value_node, var_name)
                details["classVars"][var_name] = value_repr

            elif (
                var_name
            ):  # It's an assignment, but not a known class var - treat as other member
                try:
                    details["otherMembersSource"] += dedent(ast.unparse(node)) + "\n"
                except Exception:
                    details[
                        "otherMembersSource"
                    ] += f"<Error unparsing other member {var_name}>"

        elif isinstance(node, ast.FunctionDef):
            method_name = node.name
            try:
                # Extract source code from the original source text using line numbers
                start_lineno = node.lineno - 1  # AST lineno is 1-based
                end_lineno = node.end_lineno  # AST end_lineno is 1-based and inclusive
                # Split source into lines and get the relevant slice
                source_lines = source_code.splitlines()
                method_source = "\n".join(source_lines[start_lineno:end_lineno])
            except Exception:
                method_source = f"<Error unparsing method {method_name}>"

            if method_name in known_method_names:
                details["methods"][method_name] = method_source
            else:  # Not a specifically handled method, add to consolidated source
                details["otherMembersSource"] += "\n" + dedent(method_source) + "\n"
        # Could add handling for other node types like Import, If, etc. if needed

    # Clean up trailing newlines from the consolidated source
    details["otherMembersSource"] = details["otherMembersSource"].strip()
    if details["otherMembersSource"] == "":
        del details["otherMembersSource"]

    # Special case for ChatTaskWorker
    if worker_type == "chattaskworker":
        details["inputTypes"] = ["ChatTask"]
        details["classVars"]["output_types"] = ["ChatMessage"]

    # --- Determine Input Type based on Worker Type and available info ---
    input_type = extract_input_type(class_def, worker_type, details)
    if input_type:
        details["inputTypes"] = [input_type]
    elif "inputTypes" in details:  # Clean up if no type was found but key exists
        del details["inputTypes"]

    return details


def extract_input_type(
    class_def: ast.ClassDef, worker_type: str, details: Dict[str, Any]
) -> Optional[str]:
    input_type_from_consume = None
    input_type_from_joined = None
    llm_input_type_val = None

    # Re-iterate or access stored method nodes if needed to get types
    # (This assumes methods are stored in details["methods"] - adjust if structure differs)
    consume_work_node = next(
        (
            n
            for n in class_def.body
            if isinstance(n, ast.FunctionDef) and n.name == "consume_work"
        ),
        None,
    )
    if consume_work_node:
        input_type_from_consume = _get_consume_work_input_type(consume_work_node)

    consume_work_joined_node = next(
        (
            n
            for n in class_def.body
            if isinstance(n, ast.FunctionDef) and n.name == "consume_work_joined"
        ),
        None,
    )
    if consume_work_joined_node:
        input_type_from_joined = _get_joined_consume_work_input_type(
            consume_work_joined_node
        )

    if worker_type in ("llmtaskworker", "cachedllmtaskworker"):
        llm_input_type_val = details["classVars"].get("llm_input_type")
        # Handle string or Field dict
        if (
            isinstance(llm_input_type_val, dict)
            and llm_input_type_val.get("isField")
            and llm_input_type_val.get("type")
        ):
            llm_input_type_val = llm_input_type_val["type"]
        elif not isinstance(llm_input_type_val, str):
            llm_input_type_val = None  # Ensure it's a string or None

    final_input_type = None
    if worker_type == "joinedtaskworker" and input_type_from_joined:
        final_input_type = input_type_from_joined
    elif worker_type in ("llmtaskworker", "cachedllmtaskworker") and llm_input_type_val:
        final_input_type = llm_input_type_val
    elif worker_type == "chattaskworker":
        final_input_type = "ChatTask"
    elif input_type_from_consume:  # Fallback for all types
        final_input_type = input_type_from_consume

    return final_input_type


# Helper to evaluate constant AST nodes and determine if literal
def _evaluate_ast_node(node: Optional[ast.expr]) -> Tuple[Any, bool]:
    """
    Evaluates an AST node if it's a simple literal constant.

    Returns:
        Tuple[Any, bool]: (evaluated_value, is_literal)
        is_literal is True if the node is a Constant, False otherwise.
        evaluated_value is the constant value if is_literal is True, else None.
    """
    if isinstance(node, ast.Constant):
        return node.value, True
    # Handle NameConstant for True, False, None in older Python versions if necessary
    # elif isinstance(node, ast.NameConstant):
    #    return node.value, True
    return None, False


def find_assignment_in_scope(
    var_name: str, start_node: ast.AST, scope_node: ast.FunctionDef
) -> Optional[ast.expr]:
    """Finds the value assigned to var_name before start_node within the scope_node."""
    # Simple approach: find the last assignment in the function scope.
    # A more robust approach might consider line numbers or control flow.
    assignments_in_scope = {}
    for stmt in ast.walk(scope_node):
        if isinstance(stmt, ast.Assign):
            # Simple assignment: var = value
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target_name = stmt.targets[0].id
                assignments_in_scope[target_name] = stmt.value

    return assignments_in_scope.get(var_name)


def find_graph_builder_function(parsed_ast: ast.Module) -> Optional[ast.FunctionDef]:
    """Finds a function likely responsible for building the PlanAI graph."""
    for node in ast.walk(parsed_ast):
        if isinstance(node, ast.FunctionDef):
            # Look for graph instantiation or specific method calls
            # More robust check: look for graph = Graph(...) assignment specifically
            graph_assigned = False
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    # Check for graph = Graph(...)
                    if (
                        isinstance(stmt.value, ast.Call)
                        and isinstance(stmt.value.func, ast.Name)
                        and stmt.value.func.id == "Graph"
                        and len(stmt.targets) == 1
                        and isinstance(stmt.targets[0], ast.Name)
                        and stmt.targets[0].id == "graph"
                    ):
                        graph_assigned = True
                        break  # Found graph assignment in this function

            # Also check if common graph methods are called
            calls_graph_methods = False
            if graph_assigned:  # Only check methods if graph is assigned here
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, ast.Call) and isinstance(
                        sub_node.func, ast.Attribute
                    ):
                        # Check if the call is on an object named 'graph' (or 'g')
                        if isinstance(
                            sub_node.func.value, ast.Name
                        ) and sub_node.func.value.id in ("graph", "g"):
                            if sub_node.func.attr in (
                                "add_workers",
                                "set_dependency",
                                "set_entry",
                                "set_sink",
                                "run",
                            ):
                                calls_graph_methods = True
                                break  # Found a relevant graph method call

            if graph_assigned and calls_graph_methods:
                return node  # Found a likely candidate

    return None  # Function not found


def get_llm_assignments(
    func_node: ast.FunctionDef,
) -> Dict[str, Dict[str, Any]]:
    """
    Extracts variable assignments for llm_from_config calls within a function.
    Returns a dictionary mapping variable names to parsed keyword arguments.
    Also identifies inline llm_from_config calls in worker constructors.
    """
    assignments = {}

    def extract_llm_from_config_args(call_node: ast.Call) -> Optional[Dict[str, Any]]:
        """Extract kwargs from an llm_from_config call node, if it is one."""
        func_name = None
        if (
            isinstance(call_node.func, ast.Name)
            and call_node.func.id == "llm_from_config"
        ):
            func_name = "llm_from_config"
        elif (
            isinstance(call_node.func, ast.Attribute)
            and call_node.func.attr == "llm_from_config"
        ):
            # Handle cases like planai.llm_from_config(...)
            func_name = "llm_from_config"

        if func_name == "llm_from_config":
            # Parse keyword arguments into the new structure
            llm_args = {}
            for kw in call_node.keywords:
                if kw.arg:
                    value, is_literal = _evaluate_ast_node(kw.value)
                    if is_literal:
                        llm_args[kw.arg] = {"value": value, "is_literal": True}
                    else:
                        # If not a literal, unparse the node to get the variable/expression string
                        try:
                            unparsed_value = ast.unparse(kw.value)
                            llm_args[kw.arg] = {
                                "value": unparsed_value,
                                "is_literal": False,
                            }
                        except Exception:
                            # Store error information if unparsing fails
                            llm_args[kw.arg] = {
                                "value": "<Unparse Error>",
                                "is_literal": False,
                                "error": True,
                            }
            return llm_args
        return None

    def find_assignments_in_body(body: List[ast.stmt]):
        for stmt in body:
            target_stmt = None
            # Check if it's a direct assignment
            if isinstance(stmt, ast.Assign):
                target_stmt = stmt
            # Check if it's a try block, look inside its body
            elif isinstance(stmt, ast.Try):
                find_assignments_in_body(stmt.body)
                continue

            if (
                target_stmt
                and len(target_stmt.targets) == 1
                and isinstance(target_stmt.targets[0], ast.Name)
            ):
                var_name = target_stmt.targets[0].id

                # Case 1: Direct llm_from_config assignment to a variable
                if isinstance(target_stmt.value, ast.Call):
                    call_node = target_stmt.value
                    llm_args = extract_llm_from_config_args(call_node)

                    if llm_args:
                        assignments[var_name] = llm_args
                        print(
                            f"Found llm_from_config assignment: {var_name} = {llm_args}"
                        )

                    # Case 2: Worker constructor with inline llm_from_config
                    for kw in call_node.keywords:
                        if kw.arg == "llm" and isinstance(kw.value, ast.Call):
                            llm_args = extract_llm_from_config_args(kw.value)
                            if llm_args:
                                # Use special key format to indicate this is an inline LLM for this worker
                                inline_key = f"inline_{var_name}"
                                assignments[inline_key] = llm_args
                                print(
                                    f"Found inline llm_from_config in worker constructor: {var_name} with {llm_args}"
                                )

    find_assignments_in_body(func_node.body)
    return assignments


def get_worker_assignments(
    func_node: ast.FunctionDef, worker_classes: Set[str]
) -> Dict[str, Dict[str, Any]]:
    """
    Extracts variable assignments for worker instances within a function,
    including direct class instantiations and calls to known factory functions.
    Looks inside try blocks as well.

    Returns:
        A dictionary mapping variable names to details about the worker instance:
        {
            var_name: {
                'type': 'direct' | 'factory',
                'class_name': str | None,      # For 'direct' type
                'factory_name': str | None,    # For 'factory' type
                'args': List[ast.expr],        # Positional args from the call
                'keywords': Dict[str, ast.expr] # Keyword args from the call
            },
            ...
        }
    """
    assignments = {}

    def find_assignments_in_body(body: List[ast.stmt]):
        for stmt in body:
            target_stmt = None
            # Check if it's a direct assignment
            if isinstance(stmt, ast.Assign):
                target_stmt = stmt
            # Check if it's a try block, look inside its body
            elif isinstance(stmt, ast.Try):
                # Recursively search within the try block's body
                find_assignments_in_body(stmt.body)
                # Optionally, could also check stmt.handlers or stmt.finalbody
                continue  # Continue to next statement after processing try block

            # Process the assignment statement if found
            if (
                target_stmt
                and len(target_stmt.targets) == 1
                and isinstance(target_stmt.targets[0], ast.Name)
                and isinstance(target_stmt.value, ast.Call)  # Must be a call
                # Allow simple function/class name or attribute access like planai.patterns.create_planning_worker
                # We only care about the final name called
            ):
                var_name = target_stmt.targets[0].id
                call_node = target_stmt.value
                func_name = None
                if isinstance(
                    call_node.func, ast.Name
                ):  # Simple name like MyWorker() or create_planning_worker()
                    func_name = call_node.func.id
                elif isinstance(
                    call_node.func, ast.Attribute
                ):  # Attribute like patterns.create_planning_worker()
                    # We might only need the final attribute name
                    func_name = call_node.func.attr
                    # TODO: Consider if we need the full path (e.g., planai.patterns.create_planning_worker)
                    # For now, assume the final name is unique enough or configured in SUBGRAPH_FACTORIES

                if func_name:
                    args = call_node.args
                    # Store keyword args
                    keywords_ast = {
                        kw.arg: kw.value for kw in call_node.keywords if kw.arg
                    }

                    # Check for llm parameter specifically
                    llm_var_name = None
                    if "llm" in keywords_ast and isinstance(
                        keywords_ast["llm"], ast.Name
                    ):
                        llm_var_name = keywords_ast["llm"].id

                    if func_name in worker_classes:
                        # Direct instantiation of a known worker class
                        assignments[var_name] = {
                            "type": "direct",
                            "class_name": func_name,
                            "factory_name": None,
                            "args": args,
                            "keywords": keywords_ast,  # Store AST nodes
                            "llm_variable_name": llm_var_name,
                        }
                    elif func_name in SUBGRAPH_FACTORIES:
                        # Call to a known factory function
                        assignments[var_name] = {
                            "type": "factory",
                            "class_name": None,
                            "factory_name": func_name,
                            "args": args,
                            "keywords": keywords_ast,  # Store AST nodes
                            "llm_variable_name": llm_var_name,  # Also track for factories if they take 'llm'
                        }

    # Start search from the main function body
    find_assignments_in_body(func_node.body)
    return assignments


def parse_edge_statement(
    stmt: ast.stmt,
    worker_assignments: Dict[str, str],
    worker_details_map: Dict[
        str, Dict[str, Any]
    ],  # Map className to its full details dict
) -> List[Dict[str, str]]:
    """Parses a statement to extract PlanAI graph edges.

    Edges source/target use the worker's className.
    """
    edges = []
    call_node = None

    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call_node = stmt.value
    elif isinstance(stmt, ast.Assign) and isinstance(stmt.value, ast.Call):
        # We care about the call on the right, assignment target is not directly needed for edges
        call_node = stmt.value

    if not call_node:
        return edges

    # Walk the chain of calls (e.g., graph.set_dependency(...).next(...))
    chain = []
    current = call_node
    while isinstance(current, ast.Call) and isinstance(current.func, ast.Attribute):
        method_name = current.func.attr
        args = current.args
        chain.append({"method": method_name, "args": args})
        current = current.func.value  # Move left

    # Check the start of the chain (should be graph or a worker variable)
    if isinstance(current, ast.Name):
        chain.append({"method": "start", "var_name": current.id})
    else:
        return edges  # Invalid chain start

    chain.reverse()  # Process in execution order

    last_node_var = None
    for call_info in chain:
        method = call_info["method"]
        args = call_info.get("args", [])

        if method == "start":
            last_node_var = call_info.get("var_name")
            continue

        if (
            method == "set_dependency"
            and len(args) == 2
            and isinstance(args[0], ast.Name)
            and isinstance(args[1], ast.Name)
        ):
            source_var = args[0].id
            target_var = args[1].id
            source_class = worker_assignments.get(source_var)
            target_class = worker_assignments.get(target_var)
            if source_class and target_class:
                edge_info = {"source": source_class, "target": target_class}
                # Add target input type if available
                target_details = worker_details_map.get(target_class)
                if target_details and target_details.get("inputTypes"):
                    edge_info["targetInputType"] = target_details["inputTypes"][0]
                edges.append(edge_info)
            last_node_var = target_var  # set_dependency result flows from target

        elif method == "next" and len(args) == 1 and isinstance(args[0], ast.Name):
            if last_node_var:  # Ensure we have a source from the previous chain link
                source_var = last_node_var
                target_var = args[0].id
                source_class = worker_assignments.get(source_var)
                target_class = worker_assignments.get(target_var)
                if source_class and target_class:
                    edge_info = {"source": source_class, "target": target_class}
                    # Add target input type if available
                    target_details = worker_details_map.get(target_class)
                    if target_details and target_details.get("inputTypes"):
                        edge_info["targetInputType"] = target_details["inputTypes"][0]
                    edges.append(edge_info)
                last_node_var = target_var  # next result flows from its argument
            else:
                last_node_var = None  # Break chain if source is lost
        else:
            last_node_var = None  # Unknown method breaks the chain tracking

    return edges


def parse_set_entry_statement(stmt: ast.stmt) -> Optional[str]:
    """Parses a graph.set_entry(worker) statement.

    Target worker will be the worker's className.

    Returns:
        - Optional[str]: entry worker class name
    """
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
        call_node = stmt.value
        # Check for graph.set_entry(worker_var)
        if (
            isinstance(call_node.func, ast.Attribute)
            and call_node.func.attr == "set_entry"
            and isinstance(call_node.func.value, ast.Name)
            and call_node.func.value.id == "graph"
            and len(call_node.args) == 1
            and isinstance(call_node.args[0], ast.Name)
        ):

            entry_worker_var = call_node.args[0].id
            return entry_worker_var

    return None


def parse_graph_run_entry_points(
    stmt: ast.stmt,
    func_node: ast.FunctionDef,  # Pass the function node for scope lookup
) -> Optional[List[str]]:
    """Parses a graph.run(initial_tasks=[...]) call to extract entry points.

    Target worker will be the worker's className.
    """
    if not (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call)):
        return None

    call_node = stmt.value
    # Check for graph.run(...)
    if not (
        isinstance(call_node.func, ast.Attribute)
        and call_node.func.attr == "run"
        and isinstance(call_node.func.value, ast.Name)
        # Assume graph variable name is 'graph' for now
        and call_node.func.value.id == "graph"
    ):
        return None

    # Find the initial_tasks keyword argument
    initial_tasks_arg_value = None
    for keyword in call_node.keywords:
        if keyword.arg == "initial_tasks":
            initial_tasks_arg_value = keyword.value
            break

    if not initial_tasks_arg_value:
        return None

    initial_tasks_list_node = None
    if isinstance(initial_tasks_arg_value, ast.List):
        # Direct list literal
        initial_tasks_list_node = initial_tasks_arg_value
    elif isinstance(initial_tasks_arg_value, ast.Name):
        # Variable name, find its assignment in the current function scope
        var_name = initial_tasks_arg_value.id
        assigned_value_node = find_assignment_in_scope(var_name, stmt, func_node)
        if isinstance(assigned_value_node, ast.List):
            initial_tasks_list_node = assigned_value_node
        else:
            print(
                f"Warning: Could not resolve variable '{var_name}' for initial_tasks to a List node."
            )
            return None  # Couldn't resolve or not a list
    else:
        # Not a list literal or a variable name we can resolve
        return None

    if not initial_tasks_list_node:
        return None

    # --- Now parse the initial_tasks_list_node (ast.List) ---
    entry_worker_vars = []

    for element in initial_tasks_list_node.elts:
        if not (isinstance(element, ast.Tuple) and len(element.elts) == 2):
            continue

        worker_node = element.elts[0]

        worker_var_name = None
        if isinstance(worker_node, ast.Name):
            worker_var_name = worker_node.id

        if worker_var_name:
            entry_worker_vars.append(worker_var_name)
    return entry_worker_vars


def filter_out_default_imports(module_imports: List[ast.stmt]) -> List[ast.stmt]:
    # filter out default imports
    export_code_snippet = return_code_snippet("export_clean")
    export_code_ast = ast.parse(export_code_snippet)
    export_code_imports = get_import_statements(export_code_ast)
    export_code_import_from_statements = get_import_from_statements(export_code_ast)

    # Create sets for efficient lookup of default imports
    default_import_names = set()
    for imp in export_code_imports:
        for alias in imp.names:
            default_import_names.add(alias.name)

    default_import_from_tuples = set()
    for imp_from in export_code_import_from_statements:
        module_name = imp_from.module or ""  # Handle relative imports if needed later
        for alias in imp_from.names:
            default_import_from_tuples.add((module_name, alias.name))

    filtered_imports = []
    for import_node in module_imports:
        if isinstance(import_node, ast.Import):
            non_default_aliases = []
            for alias in import_node.names:
                if alias.name not in default_import_names:
                    non_default_aliases.append(alias)
            # If any names remain after filtering, add a new Import node with only those names
            if non_default_aliases:
                filtered_imports.append(ast.Import(names=non_default_aliases))
        elif isinstance(import_node, ast.ImportFrom):
            non_default_names = []
            module_name = import_node.module or ""
            for alias in import_node.names:
                # Check if the specific import (module, name) is in the defaults
                if (module_name, alias.name) not in default_import_from_tuples:
                    non_default_names.append(alias)
            # If any names remain after filtering, add a new ImportFrom node
            if non_default_names:
                filtered_imports.append(
                    ast.ImportFrom(
                        module=import_node.module,  # Keep original module name
                        names=non_default_names,
                        level=import_node.level,  # Keep original level
                    )
                )

    return filtered_imports


def get_imported_tasks_and_module_imports(
    parsed_ast: ast.Module,
    worker_defs: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, str]], List[str]]:
    """Extracts all imported task names and module imports from an AST module."""
    imported_tasks = []
    module_imports = []

    # get all the use factory names as these imports will be automatically added
    factory_names = set([w["factoryFunction"] for w in worker_defs])

    for node in get_import_from_statements(parsed_ast):
        module_path = node.module
        if module_path and module_path in ALLOWED_TASK_IMPORTS:
            allowed_classes = ALLOWED_TASK_IMPORTS[module_path]
            for alias in node.names:
                original_name = alias.name
                imported_as = alias.asname or original_name
                if original_name in factory_names:
                    # these will be added automatically
                    continue
                if original_name in allowed_classes:
                    # Found an allowed imported Task
                    imported_tasks.append(
                        {
                            "modulePath": module_path,
                            "className": imported_as,  # Use the name it's imported as
                        }
                    )
                else:
                    # reconstruct ast.ImportFrom node
                    module_imports.append(
                        ast.ImportFrom(
                            module=module_path, names=[ast.alias(name=imported_as)]
                        )
                    )
        else:
            module_imports.append(node)

    # By convention, we expect all PlanAI imports to be "from planai import <name>"
    for node in get_import_statements(parsed_ast):
        for name in node.names:
            if name.name not in ALLOWED_TASK_IMPORTS:
                module_imports.append(node)

    # filter out default imports
    module_imports = filter_out_default_imports(module_imports)
    # convert module_imports to string
    module_import_strings = [ast.unparse(node) for node in module_imports]

    return imported_tasks, module_import_strings


def get_definitions_from_file(
    filename: Optional[str] = None, code_string: Optional[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Parses Python code (from a file or a string), extracts Task and Worker
    class definitions, graph edges, and formats them into separate lists
    within a dictionary.
    Returns: {"tasks": [...], "workers": [...], "edges": [...], ...}
    """
    source_code = ""
    if code_string is not None:
        source_code = code_string
        parse_target = "<string>"  # For error messages
    elif filename is not None:
        parse_target = filename
        try:
            with open(filename, "r") as f:
                source_code = f.read()
        except FileNotFoundError:
            print(f"Error: File not found '{filename}'")
            return {
                "tasks": [],
                "workers": [],
                "edges": [],
                "entryEdges": [],
                "imported_tasks": [],
            }
        except Exception as e:
            print(f"Error: Could not read file '{filename}': {e}")
            return {
                "tasks": [],
                "workers": [],
                "edges": [],
                "entryEdges": [],
                "imported_tasks": [],
            }
    else:
        raise ValueError("Either filename or code_string must be provided")

    try:
        parsed_ast = ast.parse(source_code)
    except SyntaxError as e:
        print(f"Error: Syntax error parsing {parse_target}: {e}")
        # Try to return partial info if possible, or just empty
        # Add more detailed error info?
        error_line = (
            source_code.splitlines()[e.lineno - 1] if e.lineno else "<unknown line>"
        )
        print(f"  Error near line {e.lineno}, offset {e.offset}: {error_line.strip()}")
        return {
            "tasks": [],
            "workers": [],
            "edges": [],
            "entryEdges": [],
            "imported_tasks": [],
        }
    except Exception as e:
        print(f"Error: Could not parse {parse_target}: {e}")
        return {
            "tasks": [],
            "workers": [],
            "edges": [],
            "entryEdges": [],
            "imported_tasks": [],
        }

    # The rest of the function remains the same, operating on parsed_ast and source_code
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
    for class_def, worker_type, is_cached in worker_definitions_with_type:
        details = extract_worker_details(class_def, worker_type, source_code)
        details["isCached"] = is_cached
        # Add worker details including its assigned variable name if found later
        worker_results.append(details)

    # --- Extract Edges & Process Assignments --- #
    edges = []
    graph_func_node = find_graph_builder_function(parsed_ast)

    # Combined list of all worker definitions including factory-created ones
    all_worker_defs = list(worker_results)  # Start with directly defined workers

    # Map className -> worker details (will include factory workers)
    worker_details_map = {w["className"]: w for w in worker_results}

    # Map to store variable name -> className for all workers
    var_to_class_map = {}

    if graph_func_node:
        print(f"Found graph builder function: {graph_func_node.name}")
        # Get all worker class names defined in the file (needed for get_worker_assignments)
        directly_defined_worker_classes = {w["className"] for w in worker_results}

        # Find all relevant assignments (direct instantiations and factory calls)
        worker_instances = get_worker_assignments(
            graph_func_node, directly_defined_worker_classes
        )
        print(f"Worker instances found: {worker_instances}")

        # Get LLM variable assignments first
        llm_assignments = get_llm_assignments(graph_func_node)
        print(f"Found LLM assignments: {llm_assignments}")

        # Process directly defined workers first
        for var_name, instance_info in worker_instances.items():
            if instance_info["type"] == "direct":
                class_name = instance_info["class_name"]
                # Store the variable name -> class name mapping
                var_to_class_map[var_name] = class_name

                # Also set variableName on the worker details for completeness
                # (but className remains the primary identifier)
                worker_entry = worker_details_map.get(class_name)
                if worker_entry:
                    worker_entry["variableName"] = var_name

                # Check for standard LLM variable reference
                llm_var = instance_info.get("llm_variable_name")
                if not llm_var:
                    # check if there is an inline llm assignment for this worker
                    llm_var = f"inline_{var_name}"

                # Handle standard llm variable reference
                if (
                    llm_var
                    and llm_var in llm_assignments
                    and class_name
                    and class_name in worker_details_map
                ):
                    print(
                        f"Associating LLM config from '{llm_var}' with worker '{class_name}' (var: {var_name})"
                    )
                    worker_details_map[class_name]["llmConfigFromCode"] = (
                        llm_assignments[llm_var]
                    )
                    if llm_var != f"inline_{var_name}":
                        worker_details_map[class_name]["llmConfigVar"] = llm_var

            elif instance_info["type"] == "factory":
                factory_name = instance_info["factory_name"]
                factory_config = SUBGRAPH_FACTORIES.get(factory_name)
                if factory_config:
                    # Extract 'name' keyword argument if present
                    name_kw_node = instance_info["keywords"].get("name")
                    explicit_name = None
                    if isinstance(name_kw_node, ast.Constant) and isinstance(
                        name_kw_node.value, str
                    ):
                        explicit_name = name_kw_node.value

                    # Determine className - priority to explicit name provided in factory call
                    factory_class_name = (
                        explicit_name
                        or factory_config.get("defaultClassName")
                        or f"{factory_name}_worker"
                    )

                    # Store the variable name -> class name mapping
                    var_to_class_map[var_name] = factory_class_name

                    # Unparse arguments for direct use in regeneration
                    factory_args_strings = [
                        ast.unparse(arg) for arg in instance_info["args"]
                    ]
                    factory_keywords_strings = {
                        kw_name: ast.unparse(kw_value)
                        for kw_name, kw_value in instance_info["keywords"].items()
                    }

                    # Combine args and kwargs into a single invocation string
                    all_args_list = list(factory_args_strings)
                    all_args_list.extend(
                        [
                            f"{kw_name}={kw_value}"
                            for kw_name, kw_value in factory_keywords_strings.items()
                        ]
                    )
                    factory_invocation_string = ", ".join(all_args_list)

                    # Create new worker definition
                    factory_worker_def = {
                        "className": factory_class_name,  # Use this as the primary identifier
                        "variableName": var_name,
                        "workerType": "subgraphworker",
                        "inputTypes": factory_config.get("inputTypes", []),
                        "classVars": factory_config.get("classVars", {}),
                        "factoryFunction": factory_name,
                        "factoryInvocation": factory_invocation_string,  # Store combined invocation string
                    }

                    # Add to combined list and details map
                    all_worker_defs.append(factory_worker_def)
                    worker_details_map[factory_class_name] = factory_worker_def
                else:
                    print(
                        f"Warning: Factory function '{factory_name}' assigned to '{var_name}' not found in SUBGRAPH_FACTORIES configuration."
                    )

        # --- Parse Edges using the variable -> className Map ---
        print(f"Parsing edges with var_to_class_map: {var_to_class_map}")
        for stmt in graph_func_node.body:
            # Pass the var -> class map to parse edges
            edges.extend(
                parse_edge_statement(stmt, var_to_class_map, worker_details_map)
            )

            # Check for graph.set_entry(...)
            entry_worker_var = parse_set_entry_statement(stmt)
            if entry_worker_var:
                assert entry_worker_var
                entry_worker_class = var_to_class_map[entry_worker_var]
                worker_details_map[entry_worker_class]["entryPoint"] = True

            # Check for graph.run(initial_tasks=...)
            # Pass the graph_func_node for scope analysis
            entry_worker_vars = parse_graph_run_entry_points(stmt, graph_func_node)
            if entry_worker_vars:
                for entry_worker_var in entry_worker_vars:
                    assert entry_worker_var
                    entry_worker_class = var_to_class_map[entry_worker_var]
                    worker_details_map[entry_worker_class]["entryPoint"] = True

        print(f"Extracted edges: {edges}")
    else:
        print("Warning: Could not find a graph builder function.")

    # --- Extract Imported Tasks (Based on Allow List) ---
    imported_tasks, module_imports = get_imported_tasks_and_module_imports(
        parsed_ast, [w for w in all_worker_defs if w["workerType"] == "subgraphworker"]
    )

    # Add implicit imports based on worker types
    imported_tasks = add_implicit_imports(
        imported_tasks, {w["workerType"] for w in all_worker_defs}
    )

    # create the custom modulelevelimport data structure
    # clean up the imports with black
    try:
        module_imports_str = "\n".join(module_imports)
        isort_config = isort.Config(profile="black")
        module_imports_str = isort.code(module_imports_str, config=isort_config)
        module_imports_str = black.format_str(module_imports_str, mode=black.Mode())
    except Exception as e:
        print(f"Error: Could not format module imports: {e}")
        module_imports_str = "\n".join(module_imports)

    return {
        "tasks": task_results,
        "workers": all_worker_defs,
        "edges": edges,
        "imported_tasks": imported_tasks,
        "module_imports": module_imports_str,
    }


def add_implicit_imports(
    imported_tasks: List[Dict[str, Any]], worker_types: Set[str]
) -> List[Dict[str, Any]]:
    """
    Add implicit imports based on worker types
    """

    implicit_imports = [
        ("chattaskworker", {"modulePath": "planai", "className": "ChatTask"}),
        ("chattaskworker", {"modulePath": "planai", "className": "ChatMessage"}),
    ]

    imports = imported_tasks.copy()
    for worker_type, import_info in implicit_imports:
        if worker_type in worker_types:
            if import_info not in imports:
                # we don't want to re-create the import if it never existed in the original source code
                copied_import = import_info.copy()
                copied_import["isImplicit"] = True
                imports.append(copied_import)

    return imports


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

    if definitions["tasks"] or definitions["workers"] or definitions["edges"]:
        import json

        print(json.dumps(definitions, indent=2))
    else:
        print(f"No Task or Worker definitions found in '{filename}'.")


if __name__ == "__main__":
    # Simple test execution
    # You might want to pass the filename via command line args in a real scenario
    main()
