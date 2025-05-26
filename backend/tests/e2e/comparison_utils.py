"""
Comparison utilities for PlanAI definitions in E2E tests.

This module provides specialized comparison functions for validating
that imported and exported PlanAI definitions are functionally equivalent.
"""

import sys
from pathlib import Path
from typing import Any, Dict

# Ensure planaieditor can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from planaieditor.patch import get_definitions_from_python  # noqa: E402


def compare_definitions(defs1: Dict[str, Any], defs2: Dict[str, Any]) -> bool:
    """
    Compares the dictionaries produced by get_definitions_from_python.
    Focuses on comparing names, types, fields, classVars, edges, entries.
    Ignores method bodies and otherMembersSource for flexibility.
    Handles expected differences (e.g., llmConfig presence).

    Args:
        defs1: First definitions dictionary
        defs2: Second definitions dictionary

    Returns:
        True if definitions are functionally equivalent, False otherwise
    """
    print("Comparing parsed definitions...")

    all_match = True  # Assume match initially

    # Compare Tasks (name, fields - name, type, isList, required)
    tasks1 = {t["className"]: t for t in defs1.get("tasks", [])}
    tasks2 = {t["className"]: t for t in defs2.get("tasks", [])}
    if set(tasks1.keys()) != set(tasks2.keys()):
        print(
            f"Task className mismatch:\nDefs1: {set(tasks1.keys())}\nDefs2: {set(tasks2.keys())}"
        )
        all_match = False
    else:
        for name, task1 in tasks1.items():
            task2 = tasks2[name]
            fields1 = {f["name"]: f for f in task1.get("fields", [])}
            fields2 = {f["name"]: f for f in task2.get("fields", [])}
            if set(fields1.keys()) != set(fields2.keys()):
                print(
                    f"Task '{name}' field name mismatch:\nDefs1: {set(fields1.keys())}\nDefs2: {set(fields2.keys())}"
                )
                all_match = False
                continue
            for fname, field1 in fields1.items():
                field2 = fields2[fname]
                # Compare key field attributes
                for attr in [
                    "type",
                    "isList",
                    "required",
                    "literalValues",
                ]:  # Added literalValues
                    val1 = field1.get(attr)
                    val2 = field2.get(attr)
                    if val1 != val2:
                        # Allow type Any vs specific type if one is missing (e.g., from simple generation)
                        if attr == "type" and (
                            "Any" in [val1, val2] and (val1 is None or val2 is None)
                        ):
                            print(
                                f"Task '{name}' field '{fname}': Tolerating type mismatch ('{val1}' vs '{val2}')"
                            )
                            continue
                        print(
                            f"Task '{name}' field '{fname}' attribute '{attr}' mismatch: {val1} vs {val2}"
                        )
                        all_match = False

    # Compare Workers (className, workerType, classVars - *selectively*)
    workers1 = {w["className"]: w for w in defs1.get("workers", [])}
    workers2 = {w["className"]: w for w in defs2.get("workers", [])}
    if set(workers1.keys()) != set(workers2.keys()):
        print(
            f"Worker className mismatch:\nDefs1: {set(workers1.keys())}\nDefs2: {set(workers2.keys())}"
        )
        all_match = False
    else:
        for name, worker1 in workers1.items():
            worker2 = workers2[name]
            # Compare type
            if worker1.get("workerType") != worker2.get("workerType"):
                print(
                    f"Worker '{name}' workerType mismatch: {worker1.get('workerType')} vs {worker2.get('workerType')}"
                )
                all_match = False
            # Compare classVars selectively
            vars1 = worker1.get("classVars", {})
            vars2 = worker2.get("classVars", {})
            vars_to_check = [
                "output_types",
                "llm_input_type",
                "llm_output_type",
                "join_type",
                "use_xml",
                "debug_mode",
                "prompt",
                "system_prompt",
                "code",
            ]
            for vname in vars_to_check:
                val1 = vars1.get(vname)
                val2 = vars2.get(vname)

                # Normalize prompt strings before comparison
                if (
                    vname in ("prompt", "system_prompt")
                    and isinstance(val1, str)
                    and isinstance(val2, str)
                ):
                    val1 = val1.strip()
                    val2 = val2.strip()

                if val1 != val2:
                    # Use repr() to show potential hidden characters
                    print(
                        f"Worker '{name}' classVar '{vname}' mismatch: {repr(val1)} vs {repr(val2)}"
                    )
                    all_match = False
            # Compare factory details if present
            if worker1.get("factoryFunction") or worker2.get("factoryFunction"):
                if worker1.get("factoryFunction") != worker2.get("factoryFunction"):
                    print(
                        f"Worker '{name}' factoryFunction mismatch: {worker1.get('factoryFunction')} vs {worker2.get('factoryFunction')}"
                    )
                    all_match = False
                if worker1.get("factoryInvocation") != worker2.get("factoryInvocation"):
                    print(
                        f"Worker '{name}' factoryInvocation mismatch:\nDefs1: {worker1.get('factoryInvocation')}\nDefs2: {worker2.get('factoryInvocation')}"
                    )
                    all_match = False

            # Compare LLM configuration
            # Note: This compares the config *parsed* from code, not the potentially
            # different config injected during export from the UI state.
            # We rely on the final python code generation to handle the llmConfig correctly.
            llm_config_var1 = worker1.get("llmConfigVar")
            llm_config_var2 = worker2.get("llmConfigVar")
            if llm_config_var1 != llm_config_var2:
                # Allow mismatch if one is None (e.g., inline vs variable)
                if not (llm_config_var1 is None or llm_config_var2 is None):
                    print(
                        f"Worker '{name}' llmConfigVar mismatch: {llm_config_var1} vs {llm_config_var2}"
                    )
                    all_match = False

            llm_config1 = worker1.get("llmConfigFromCode")
            llm_config2 = worker2.get("llmConfigFromCode")

            if isinstance(llm_config1, dict) and isinstance(llm_config2, dict):
                if set(llm_config1.keys()) != set(llm_config2.keys()):
                    print(
                        f"Worker '{name}' llmConfigFromCode keys mismatch:\n"  # type: ignore
                        f"  Defs1: {set(llm_config1.keys())}\n"
                        f"  Defs2: {set(llm_config2.keys())}"
                    )
                    all_match = False
                else:
                    for key in llm_config1:
                        val_info1 = llm_config1[key]
                        val_info2 = llm_config2[key]
                        if not isinstance(val_info1, dict) or not isinstance(
                            val_info2, dict
                        ):
                            print(
                                f"Worker '{name}' llmConfigFromCode item '{key}' has unexpected format: {val_info1} vs {val_info2}"
                            )
                            all_match = False
                            continue
                        if val_info1.get("value") != val_info2.get(
                            "value"
                        ) or val_info1.get("is_literal") != val_info2.get("is_literal"):
                            print(
                                f"Worker '{name}' llmConfigFromCode item '{key}' mismatch: {val_info1} vs {val_info2}"
                            )
                            all_match = False
            elif llm_config1 is not None or llm_config2 is not None:
                # Mismatch if one has config and the other doesn't (and they aren't both None)
                print(
                    f"Worker '{name}' llmConfigFromCode presence mismatch: {llm_config1 is not None} vs {llm_config2 is not None}"
                )
                all_match = False

    # Compare Edges (source, target)
    edges1 = {(e["source"], e["target"]) for e in defs1.get("edges", [])}
    edges2 = {(e["source"], e["target"]) for e in defs2.get("edges", [])}
    if edges1 != edges2:
        print(f"Edge mismatch:\nDefs1: {edges1}\nDefs2: {edges2}")
        all_match = False

    # Compare Entry Edges (sourceTask, targetWorker)
    entries1 = {
        (e["sourceTask"], e["targetWorker"]) for e in defs1.get("entryEdges", [])
    }
    entries2 = {
        (e["sourceTask"], e["targetWorker"]) for e in defs2.get("entryEdges", [])
    }
    if entries1 != entries2:
        print(f"Entry edge mismatch:\nDefs1: {entries1}\nDefs2: {entries2}")
        all_match = False

    # Compare Imported Tasks (modulePath, className)
    imports1 = {
        (t["modulePath"], t["className"]) for t in defs1.get("imported_tasks", [])
    }
    imports2 = {
        (t["modulePath"], t["className"]) for t in defs2.get("imported_tasks", [])
    }
    if imports1 != imports2:
        print(f"Imported tasks mismatch:\nDefs1: {imports1}\nDefs2: {imports2}")
        all_match = False

    if all_match:
        print("Parsed definitions comparison successful.")
    else:
        print("Parsed definitions comparison failed.")
    return all_match


def verify_functional_equivalence(original_code: str, exported_code: str) -> bool:
    """
    Verifies functional equivalence by parsing both code strings using
    get_definitions_from_python and comparing the resulting structures.

    Args:
        original_code: The original Python code
        exported_code: The exported Python code

    Returns:
        True if the codes are functionally equivalent, False otherwise
    """
    print("Verifying functional equivalence using AST parsing...")

    # Parse original code
    print("Parsing original code...")
    try:
        original_defs = get_definitions_from_python(code_string=original_code)
    except ImportError as e:
        print(f"ERROR: Cannot import planaieditor.patch: {e}")
        return False

    if not original_defs or (
        not original_defs.get("tasks") and not original_defs.get("workers")
    ):
        print("ERROR: Failed to parse original code or no definitions found.")
        return False

    # Parse exported code
    print("Parsing exported code...")
    try:
        exported_defs = get_definitions_from_python(code_string=exported_code)
    except ImportError as e:
        print(f"ERROR: Cannot import planaieditor.patch: {e}")
        return False

    if not exported_defs or (
        not exported_defs.get("tasks") and not exported_defs.get("workers")
    ):
        print("ERROR: Failed to parse exported code or no definitions found.")
        return False

    # Compare the parsed structures
    return compare_definitions(original_defs, exported_defs)


def get_expected_node_count_from_definitions(definitions: Dict[str, Any]) -> int:
    """
    Calculate the expected number of nodes from parsed definitions.

    Args:
        definitions: Parsed definitions from get_definitions_from_python

    Returns:
        Expected number of nodes that should appear in the UI
    """
    expected_count = len(definitions.get("workers", []))
    if definitions.get("module_imports"):
        expected_count += 1
    return expected_count
