import json
import os
import pprint
import sys
from pathlib import Path

import pytest
from playwright.sync_api import APIResponse, Page, Route, expect

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)

# Ensure planaieditor can be imported (adjust if your structure differs)
# This might be handled by running pytest from the 'backend' dir
sys.path.insert(0, str(Path(__file__).parent.parent))
from planaieditor.patch import get_definitions_from_python  # noqa: E402

# --- Configuration ---
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
# Use a different port for the test backend server to avoid conflicts
BACKEND_TEST_PORT = os.environ.get("BACKEND_TEST_PORT", "5001")
BACKEND_TEST_URL = f"http://localhost:{BACKEND_TEST_PORT}"
# Path relative to the backend directory
TEST_FIXTURE_PATHS = [
    Path(__file__).parent / "fixtures/releasenotes_fixture.py",
    Path(__file__).parent / "fixtures/deepsearch_fixture.py",
]
# Timeout for waiting for elements or status changes (in milliseconds)
TIMEOUT = 15000  # Increased timeout slightly

# --- Helper Functions / Verification Logic --- #


# Helper function for recursive comparison
def _recursive_compare(obj1, obj2, path=""):
    """Recursively compares two objects (dicts, lists, primitives) and returns a list of differences."""
    diffs = []

    # --- Type Mismatch ---
    if type(obj1) is not type(obj2):
        diffs.append(
            {
                "path": path,
                "type": "type_mismatch",
                "old_type": type(obj1).__name__,
                "new_type": type(obj2).__name__,
            }
        )
        # Cannot compare further if types are different
        return diffs

    # --- Dictionary Comparison ---
    if isinstance(obj1, dict):
        keys1 = set(obj1.keys())
        keys2 = set(obj2.keys())
        added = keys2 - keys1
        removed = keys1 - keys2
        common = keys1 & keys2

        for k in added:
            full_path = f"{path}.{k}" if path else k
            diffs.append({"path": full_path, "type": "added", "value": obj2[k]})
        for k in removed:
            full_path = f"{path}.{k}" if path else k
            diffs.append({"path": full_path, "type": "removed", "value": obj1[k]})
        # Recursively compare common keys
        for k in common:
            full_path = f"{path}.{k}" if path else k
            diffs.extend(_recursive_compare(obj1[k], obj2[k], full_path))

    # --- List Comparison ---
    elif isinstance(obj1, list):
        len1, len2 = len(obj1), len(obj2)
        # Compare common elements recursively
        for i in range(min(len1, len2)):
            item_path = f"{path}[{i}]"
            diffs.extend(_recursive_compare(obj1[i], obj2[i], item_path))
        # Report elements only in the longer list
        if len1 > len2:
            for i in range(len2, len1):
                item_path = f"{path}[{i}]"
                diffs.append({"path": item_path, "type": "removed", "value": obj1[i]})
        elif len2 > len1:
            for i in range(len1, len2):
                item_path = f"{path}[{i}]"
                diffs.append({"path": item_path, "type": "added", "value": obj2[i]})
        # Optional: Add a specific diff entry for length mismatch itself if desired
        # if len1 != len2:
        #      diffs.append({"path": path, "type": "list_length_mismatch", "old_len": len1, "new_len": len2})

    # --- Primitive/Other Comparison ---
    elif obj1 != obj2:
        # Use repr for potentially more informative diffs, especially with strings containing whitespace
        diffs.append(
            {"path": path, "type": "changed", "old": repr(obj1), "new": repr(obj2)}
        )

    return diffs


def format_diff(diff):
    """Formats a single difference dictionary into a readable string."""
    path = diff["path"] if diff["path"] else "<root>"  # Handle empty path for top level
    dtype = diff["type"]
    if dtype == "type_mismatch":
        return f"{path}: Type mismatch - {diff['old_type']} vs {diff['new_type']}"
    elif dtype == "added":
        # Indent multi-line values for clarity
        value_str = pprint.pformat(diff["value"], indent=2, width=60)
        if "\n" in value_str:
            lines = value_str.split("\n")
            # Indent all lines after the first one
            indented_lines = [lines[0]] + ["    " + line for line in lines[1:]]
            value_str = "\n    " + "\n".join(
                indented_lines
            )  # Start on newline, indented
        return f"{path}: Added = {value_str}"
    elif dtype == "removed":
        value_str = pprint.pformat(diff["value"], indent=2, width=60)
        if "\n" in value_str:
            lines = value_str.split("\n")
            indented_lines = [lines[0]] + ["    " + line for line in lines[1:]]
            value_str = "\n    " + "\n".join(
                indented_lines
            )  # Start on newline, indented
        return f"{path}: Removed = {value_str}"
    elif (
        dtype == "list_length_mismatch"
    ):  # If you add this type back in _recursive_compare
        return f"{path}: List length mismatch - {diff['old_len']} vs {diff['new_len']}"
    elif dtype == "changed":
        old_repr = diff["old"]
        new_repr = diff["new"]
        # max_len = 100
        # if len(old_repr) > max_len: old_repr = old_repr[:max_len] + '...'
        # if len(new_repr) > max_len: new_repr = new_repr[:max_len] + '...'
        # Build string line by line to avoid f-string complexity with repr()
        lines = [f"{path}: Changed", f"    Old: {old_repr}", f"    New: {new_repr}"]
        return "\n".join(lines)
    else:
        # Fallback for unknown diff types
        return f"Unknown diff @ {path}: {pprint.pformat(diff)}"


def compare_dicts(dict1: dict, dict2: dict) -> bool:
    """
    Recursively compares two dictionaries and pretty-prints the differences.
    Returns True if they are equal, False otherwise.
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        print("Error: Both inputs must be dictionaries for compare_dicts.")
        # Return False as they are not 'equal' in the context of comparing dicts
        return False

    # Start recursion with an empty path
    differences = _recursive_compare(dict1, dict2, path="")

    if not differences:
        # Keep tests quieter by default, uncomment if needed for debugging passing cases
        # print("Dictionaries are identical.")
        return True
    else:
        print("--- Dictionary Comparison Differences ---")
        for diff in differences:
            # Indent each difference report for readability
            print(f"  {format_diff(diff)}")
        print("--- End Dictionary Comparison ---")
        return False


def compare_definitions(defs1: dict, defs2: dict) -> bool:
    """
    Compares the dictionaries produced by get_definitions_from_python.
    Focuses on comparing names, types, fields, classVars, edges, entries.
    Ignores method bodies and otherMembersSource for flexibility.
    Handles expected differences (e.g., llmConfig presence).
    """
    print("Comparing parsed definitions...")

    # Call the new compare_dicts for detailed initial output if different
    # We still need the specific logic below to handle acceptable differences.
    compare_dicts(defs1, defs2)

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
    """
    print("Verifying functional equivalence using AST parsing...")

    # Parse original code
    print("Parsing original code...")
    original_defs = get_definitions_from_python(code_string=original_code)
    if not original_defs or (
        not original_defs.get("tasks") and not original_defs.get("workers")
    ):
        print("ERROR: Failed to parse original code or no definitions found.")
        return False

    # Parse exported code
    print("Parsing exported code...")
    exported_defs = get_definitions_from_python(code_string=exported_code)
    if not exported_defs or (
        not exported_defs.get("tasks") and not exported_defs.get("workers")
    ):
        print("ERROR: Failed to parse exported code or no definitions found.")
        return False

    # Compare the parsed structures
    return compare_definitions(original_defs, exported_defs)


# --- Pytest Fixtures ---


# --- Test Case ---


@pytest.mark.parametrize(
    "test_fixture_path",
    TEST_FIXTURE_PATHS,
    ids=[p.stem for p in TEST_FIXTURE_PATHS],  # Use filename stems for clearer test IDs
)
def test_import_export_roundtrip(page: Page, test_fixture_path: Path, request):
    """
    Tests the import-export roundtrip for various fixture files.
    """
    assert test_fixture_path.exists(), f"Test fixture not found at {test_fixture_path}"
    original_code = test_fixture_path.read_text()

    # Pre-parse the fixture to get expected node count
    print(f"Pre-parsing fixture {test_fixture_path.name} for node count...")
    original_defs = get_definitions_from_python(code_string=original_code)
    assert (
        original_defs is not None
    ), f"Failed to pre-parse fixture: {test_fixture_path}"

    expected_node_count = len(original_defs.get("workers", []))
    if original_defs.get("module_imports"):
        expected_node_count += 1
    print(f"Expected nodes: {expected_node_count}")

    # ** Simplified Route Handler **
    def handle_route(route: Route):
        # Only log the interception, let wait_for_response handle capturing
        if "/api/" in route.request.url:
            print(f"Intercepted request: {route.request.method} {route.request.url}")
        route.continue_()

    page.route("**/*", handle_route)

    # 1. Navigate to the frontend
    print(f"Navigating to frontend: {FRONTEND_URL}")
    page.goto(FRONTEND_URL)
    expect(page.locator('[data-testid="toolshelf-container"]')).to_be_visible(
        timeout=TIMEOUT
    )  # Wait for tool shelf
    print("Frontend loaded.")

    # 2. Clear any existing graph
    clear_button = page.locator('button[title="Clear Graph"]')
    if page.locator(".svelte-flow__node").first.is_visible(timeout=2000):
        print("Clearing existing graph...")
        # Use force=True if the button might be obscured sometimes
        clear_button.click(force=True)
        # Re-add dialog handler just in case it wasn't persistent
        page.once("dialog", lambda dialog: dialog.accept())
        # Wait for nodes to disappear
        expect(page.locator(".svelte-flow__node")).to_have_count(0, timeout=TIMEOUT)
        print("Graph cleared.")
    else:
        print("No existing graph detected, skipping clear.")

        # 3. Import the fixture file
    print(f"Importing fixture: {test_fixture_path}")
    try:
        # for some reason, import only works when there is a venv
        interpreter_button = page.locator('button[data-testid="interpreter-button"]')
        expect(interpreter_button).to_be_visible(timeout=TIMEOUT)
        expect(interpreter_button).to_be_enabled(timeout=TIMEOUT)
        with page.expect_response(
            lambda response: "/api/set-venv" in response.url
            and response.request.method == "POST",
            timeout=TIMEOUT,
        ) as response_info:
            interpreter_button.click()

        # First, we need to simulate a real user click to satisfy browser security requirements
        import_button = page.locator('button[data-testid="import-button"]')
        expect(import_button).to_be_visible(timeout=TIMEOUT)
        expect(import_button).to_be_enabled(timeout=TIMEOUT)

        # Set up both file chooser and API response expectations
        with page.expect_file_chooser(timeout=TIMEOUT) as file_chooser_info:
            print("Clicking import button with real user gesture...")
            import_button.click()
            print("Import button clicked")
            import_button.hover()  # Simulate mouse moving over
            page.mouse.down()  # Press the left mouse button
            page.mouse.up()  # Release the left mouse button

        # Handle the file chooser that should now be open
        file_chooser = file_chooser_info.value
        print(f"File chooser opened, setting file: {test_fixture_path}")

        # Now set up the API response expectation and set the files
        with page.expect_response(
            lambda response: "/api/import-python" in response.url
            and response.request.method == "POST",
            timeout=TIMEOUT,
        ) as response_info:
            file_chooser.set_files(test_fixture_path)
            print("File selected via file chooser")

        # Wait for the API response
        api_response: APIResponse = response_info.value
        print(
            f"Received API response from {api_response.url} (Status: {api_response.status})"
        )
        assert (
            api_response.ok
        ), f"API import call failed with status {api_response.status}. Response: {api_response.text()}"
        api_response_data = api_response.json()
        assert (
            api_response_data.get("success") is True
        ), f"API import failed: {api_response_data.get('error')}"
        print("API import successful.")

    except Exception as e:
        # Print page content on error for debugging
        # print("PAGE CONTENT ON ERROR:\n", page.content())
        pytest.fail(f"Failed during file import or API wait: {e}")

    # 4. Wait for graph to render after import with the expected node count
    print(f"Waiting for {expected_node_count} nodes to render...")
    expect(page.locator(".svelte-flow__node")).to_have_count(
        expected_node_count, timeout=TIMEOUT * 2
    )  # Increased timeout slightly
    print(f"{expected_node_count} nodes rendered after import.")

    # 5. Extract transformed data using page.evaluate
    try:
        print(
            "Retrieving data from localStorage and calling window.convertGraphToJSON..."
        )
        graph_data_transformed = page.evaluate(
            """
            async () => {
                const nodes_raw = JSON.parse(localStorage.getItem('nodes'));
                const edges_raw = JSON.parse(localStorage.getItem('edges'));
                if (!nodes_raw || !edges_raw) {
                    console.error('Missing nodes or edges in localStorage'); return null;
                }
                if (typeof window.convertGraphToJSON !== 'function') {
                    console.error('window.convertGraphToJSON is not defined'); return null;
                }
                console.log('Executing window.convertGraphToJSON...');
                try {
                    const result = window.convertGraphToJSON(nodes_raw, edges_raw, mode="export");
                    console.log('window.convertGraphToJSON result:', result);
                    return result;
                } catch (error) {
                    console.error('Error executing window.convertGraphToJSON:', error);
                    return { error: error.message }; // Return error details
                }
            }
            """
        )

        assert (
            graph_data_transformed is not None
        ), "window.convertGraphToJSON evaluation returned null"
        if "error" in graph_data_transformed:
            pytest.fail(
                f"Error in window.convertGraphToJSON: {graph_data_transformed['error']}"
            )
        assert isinstance(
            graph_data_transformed, dict
        ), f"Expected dict from convertGraphToJSON, got {type(graph_data_transformed)}"
        assert (
            "nodes" in graph_data_transformed and "edges" in graph_data_transformed
        ), f"convertGraphToJSON did not return expected structure. Got: {graph_data_transformed}"
        assert isinstance(graph_data_transformed["nodes"], list) and isinstance(
            graph_data_transformed["edges"], list
        ), "Transformed data structure is invalid"
        print(
            f"Received transformed data: {len(graph_data_transformed['nodes'])} nodes, {len(graph_data_transformed['edges'])} edges."
        )
    except Exception as e:
        pytest.fail(f"page.evaluate for transformation failed: {e}")

    # Write transformed data to file for debugging
    if request.config.getoption("--write-transformed-data"):
        with open(f"transformed_data_{test_fixture_path.stem}.json", "w") as f:
            json.dump(graph_data_transformed, f, indent=2)

    # 6. Trigger Export API Call with TRANSFORMED data
    export_api_url = f"{BACKEND_TEST_URL}/api/export-transformed"
    print(f"Triggering export API: {export_api_url}...")
    api_context = page.request
    try:
        response = api_context.post(
            export_api_url,
            data=json.dumps(graph_data_transformed),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT * 2,
        )
    except Exception as e:
        pytest.fail(f"API call to {export_api_url} failed: {e}")

    # 7. Get exported code from response
    print(f"Export API response status: {response.status}")
    assert (
        response.ok
    ), f"Export API call failed with status {response.status}. Response: {response.text()}"
    response_json = response.json()
    assert (
        response_json.get("success") is True
    ), f"Backend export API reported failure: {response_json.get('error', 'Unknown error')}"
    exported_code = response_json.get("python_code")
    assert exported_code is not None and isinstance(
        exported_code, str
    ), "Exported Python code not found or invalid in backend response."
    print("Successfully received exported code from backend API.")

    # 8. Verify Functional Equivalence
    assert verify_functional_equivalence(
        original_code, exported_code
    ), "Functional equivalence check failed."
    print("Functional equivalence check passed.")
