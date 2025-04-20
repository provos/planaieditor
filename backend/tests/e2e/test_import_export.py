import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Optional

import pytest
from playwright.sync_api import APIResponse, Page, Route, expect

# Ensure planaieditor can be imported (adjust if your structure differs)
# This might be handled by running pytest from the 'backend' dir
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from planaieditor.patch import get_definitions_from_file  # Import the parser

# --- Configuration ---
os.environ["FLASK_ENV"] = "development"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
# Use a different port for the test backend server to avoid conflicts
BACKEND_TEST_PORT = os.environ.get("BACKEND_TEST_PORT", "5001")
BACKEND_TEST_URL = f"http://localhost:{BACKEND_TEST_PORT}"
# Path relative to the backend directory
TEST_FIXTURE_PATH = Path(__file__).parent / "fixtures/releasenotes_fixture.py"
# Timeout for waiting for elements or status changes (in milliseconds)
TIMEOUT = 15000  # Increased timeout slightly

# --- Helper Functions / Verification Logic --- #


def compare_definitions(defs1: dict, defs2: dict) -> bool:
    """
    Compares the dictionaries produced by get_definitions_from_file.
    Focuses on comparing names, types, fields, classVars, edges, entries.
    Ignores method bodies and otherMembersSource for flexibility.
    Handles expected differences (e.g., llmConfig presence).
    """
    print("Comparing parsed definitions...")
    all_match = True

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
    get_definitions_from_file and comparing the resulting structures.
    """
    print("Verifying functional equivalence using AST parsing...")

    # Parse original code
    print("Parsing original code...")
    original_defs = get_definitions_from_file(code_string=original_code)
    if not original_defs or (
        not original_defs.get("tasks") and not original_defs.get("workers")
    ):
        print("ERROR: Failed to parse original code or no definitions found.")
        return False

    # Parse exported code
    print("Parsing exported code...")
    exported_defs = get_definitions_from_file(code_string=exported_code)
    if not exported_defs or (
        not exported_defs.get("tasks") and not exported_defs.get("workers")
    ):
        print("ERROR: Failed to parse exported code or no definitions found.")
        # Optionally print the exported code here for debugging
        # print("--- Exported Code Start ---")
        # print(exported_code)
        # print("--- Exported Code End ---")
        return False

    # Compare the parsed structures
    return compare_definitions(original_defs, exported_defs)


# --- Pytest Fixtures ---


@pytest.fixture(scope="session", autouse=True)
def backend_server():
    """Starts the backend Flask server for the test session on a specific port."""
    print(f"Starting backend server on port {BACKEND_TEST_PORT}...")
    # Command to run Flask development server from the backend directory
    # Ensure environment variables like FLASK_APP are set if needed by your setup
    # We assume running pytest from the 'backend' directory context
    # or that the path to app.py is correctly resolved.
    flask_app_path = Path(__file__).parent.parent / "app.py"
    cmd = [
        sys.executable,  # Use the same python interpreter pytest is using
        "-m",
        "flask",
        "run",
        "--port",
        BACKEND_TEST_PORT,
    ]
    env = {
        **os.environ,
        "FLASK_APP": "app.py",  # Use filename relative to backend dir
        "FLASK_DEBUG": "0",  # Ensure debug mode is off for stability if needed
    }

    # Start Flask server as a non-blocking subprocess
    # Run from the parent of the 'backend' dir to allow correct module resolution?
    # Or assume pytest is run *from* backend dir. Let's assume the latter for now.
    # cwd = str(Path(__file__).parent.parent) # Directory containing app.py
    server_process = subprocess.Popen(
        cmd,
        # cwd=cwd, # Run flask from the directory containing app.py
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    # Wait a bit for the server to start - might need adjustment
    time.sleep(5)
    # Check if the server started successfully (poll() returns None if running)
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        print("Backend stdout:\n", stdout.decode(errors="ignore"))
        print("Backend stderr:\n", stderr.decode(errors="ignore"))
        print(
            f"Backend server failed to start. Exit code: {server_process.returncode} - assuming the regular server is running"
        )

    print(f"Backend server assumed started on {BACKEND_TEST_URL}.")
    yield server_process  # Provide the process object to the tests if needed

    print("Stopping backend server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)  # Wait for graceful termination
    except subprocess.TimeoutExpired:
        print("Backend server did not terminate gracefully, killing.")
        server_process.kill()
    print("Backend server stopped.")


# --- Test Case ---


def test_releasenotes_roundtrip(page: Page, backend_server):
    """
    Tests the import-export roundtrip for the releasenotes.py example.
    """
    assert TEST_FIXTURE_PATH.exists(), f"Test fixture not found at {TEST_FIXTURE_PATH}"
    original_code = TEST_FIXTURE_PATH.read_text()

    # ** Simplified Route Handler **
    def handle_route(route: Route):
        # Only log the interception, let wait_for_response handle capturing
        if "/api/" in route.request.url:
            print(f"Intercepted request: {route.request.url}")
        route.continue_()

    page.route("**/*", handle_route)

    # 1. Navigate to the frontend
    print(f"Navigating to frontend: {FRONTEND_URL}")
    page.goto(FRONTEND_URL)
    # Use a less specific title check if needed, or wait for an element
    # expect(page).to_have_title(r"PlanAI Editor")
    expect(page.locator('[data-testid="toolshelf-container"]')).to_be_visible(
        timeout=TIMEOUT
    )  # Wait for tool shelf
    print("Frontend loaded.")

    # 2. Clear any existing graph (find button by specific attribute if possible)
    clear_button = page.locator(
        'button[title="Clear Graph"]'
    )  # Assuming title attribute
    # Check if nodes exist before clearing
    if page.locator(".svelte-flow__node").first.is_visible(
        timeout=2000
    ):  # Short timeout for check
        print("Clearing existing graph...")
        clear_button.click()
        # Accept confirmation dialog
        page.once("dialog", lambda dialog: dialog.accept())
        # Wait for nodes to disappear
        expect(page.locator(".svelte-flow__node")).to_have_count(0, timeout=TIMEOUT)
        print("Graph cleared.")
    else:
        print("No existing graph detected, skipping clear.")

    # 3. Import the fixture file
    print(f"Importing fixture: {TEST_FIXTURE_PATH}")
    try:
        # Start waiting for the response *before* triggering the action
        with page.expect_response(
            lambda response: "/api/import-python" in response.url
            and response.request.method == "POST",
            timeout=TIMEOUT * 2,  # Generous timeout for API response
        ) as response_info:

            # --- Hybrid Approach: Click button, then interact with input ---
            import_button = page.locator('button[data-testid="import-button"]')
            expect(import_button).to_be_visible(timeout=TIMEOUT)
            expect(import_button).to_be_enabled(timeout=TIMEOUT)
            print("Clicking import button (standard)...")
            import_button.click()
            print("Import button clicked (may not open chooser headless).")

            # Wait briefly for any state changes from the click
            page.wait_for_timeout(200)

            # Now interact directly with the hidden input
            file_input = page.locator('input[data-testid="file-input"]')
            expect(file_input).to_be_attached()
            print(f"Setting input file directly: {TEST_FIXTURE_PATH}")
            file_input.set_input_files(TEST_FIXTURE_PATH)
            print("Dispatching 'change' event directly...")
            file_input.dispatch_event("change")  # Trigger Svelte's onchange
            print("Direct file input set and event dispatched.")
            # --- End Hybrid Approach ---

        # Now process the response (outside the expect_response block)
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
        pytest.fail(f"Failed during file chooser or API wait: {e}")

    # 4. Wait for graph to render after import
    commit_collector_node_selector = (
        'div.svelte-flow__node[data-id*="imported-taskworker-CommitCollector"]'
    )
    print(f"Waiting for node: {commit_collector_node_selector}")
    expect(page.locator(commit_collector_node_selector)).to_be_visible(timeout=TIMEOUT)
    # Wait for expected number of nodes
    expect(page.locator(".svelte-flow__node")).to_have_count(10, timeout=TIMEOUT)
    print("Expected number of nodes rendered after import.")

    # 5. Click Export Button to trigger frontend transformation
    export_button = page.locator('button[data-testid="export-button"]')
    expect(export_button).to_be_visible(timeout=TIMEOUT)
    expect(export_button).to_be_enabled(timeout=TIMEOUT)
    print("Clicking export button...")
    export_button.click()
    print("Export button clicked.")
    # Give a brief moment for any potential state updates triggered by the click
    page.wait_for_timeout(500)

    # 6. Extract transformed data using page.evaluate
    # Define the JS transformation logic again (reading from localStorage inside)
    js_transform_function = """
    () => { // No arguments needed, reads directly from localStorage
        const nodes_raw = JSON.parse(localStorage.getItem('nodes'));
        const edges_raw = JSON.parse(localStorage.getItem('edges'));
        const llm_configs_raw = JSON.parse(localStorage.getItem('llmConfigs')); // Get LLM configs if needed by logic below

        if (!nodes_raw || !Array.isArray(nodes_raw)) {
             console.error('[evaluate] Invalid or missing nodes data in localStorage');
             return null;
        }
        const safe_edges_raw = edges_raw && Array.isArray(edges_raw) ? edges_raw : [];
        const safe_llm_configs = llm_configs_raw && Array.isArray(llm_configs_raw) ? llm_configs_raw : [];

        console.log(`[evaluate] Read ${nodes_raw.length} nodes, ${safe_edges_raw.length} edges, ${safe_llm_configs.length} LLM configs from localStorage.`);

        // --- Replicate core logic from convertGraphtoJSON ---
        const nodeIdToNameMap = new Map();
        nodes_raw.forEach(node => {
            const data = node.data;
            const name = data?.className || data?.workerName;
            if (name) {
                nodeIdToNameMap.set(node.id, name);
            }
        });

        const exportedNodes = nodes_raw.map(node => {
            const data = node.data;
            let processedData = { ...data };

            if (data?.workerName) {
                processedData.className = data.workerName;
                delete processedData.workerName;
            }

            // --- Include LLM config injection logic again, using safe_llm_configs ---
            if ((node.type === 'llmtaskworker' || node.type === 'cachedllmtaskworker') && data?.llmConfigName) {
                const configName = data.llmConfigName;
                const foundConfig = safe_llm_configs.find(c => c.name === configName);
                if (foundConfig) {
                    processedData.llmConfig = foundConfig;
                    delete processedData.llmConfigName;
                } else {
                    console.warn(`[evaluate] LLM Config '${configName}' not found during transformation.`);
                    delete processedData.llmConfig;
                    delete processedData.llmConfigName;
                }
            }
            // --- End LLM config logic ---

            const knownClassVars = [
                'prompt', 'system_prompt', 'use_xml', 'debug_mode',
                'llm_input_type', 'llm_output_type', 'join_type', 'output_types'
            ];
            if (node.type?.endsWith('worker')) {
                if (!processedData.classVars) processedData.classVars = {};
                for (const key of knownClassVars) {
                    if (processedData[key] !== undefined) {
                        processedData.classVars[key] = processedData[key];
                        delete processedData[key];
                    }
                }
            }

            if (node.type === 'subgraphworker' && data?.isFactoryCreated) {
                delete processedData.isFactoryCreated;
            }

            return { ...node, data: processedData };
        });

        const exportedEdges = safe_edges_raw
            .map(edge => {
                const sourceName = nodeIdToNameMap.get(edge.source);
                const targetName = nodeIdToNameMap.get(edge.target);
                if (!sourceName || !targetName) return null;
                return { source: sourceName, target: targetName };
            })
            .filter(edge => edge !== null);
        // --- End Replicated Logic ---

        const result = { nodes: exportedNodes, edges: exportedEdges };
        console.log('[evaluate] Returning transformed data:', result);
        return result;
    }
    """

    # Execute the transformation in the browser
    try:
        print("Executing frontend transformation logic via page.evaluate...")
        graph_data_transformed = page.evaluate(js_transform_function)
        assert (
            graph_data_transformed is not None
        ), "Frontend transformation returned null or had errors (check browser console)"
        assert (
            "nodes" in graph_data_transformed and "edges" in graph_data_transformed
        ), "Transformed data missing nodes/edges"
        print(
            f"Received transformed data: {len(graph_data_transformed['nodes'])} nodes, {len(graph_data_transformed['edges'])} edges."
        )
    except Exception as e:
        pytest.fail(f"page.evaluate for transformation failed: {e}")

    # 7. Trigger Export API Call with TRANSFORMED data
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

    # 8. Get exported code from response
    print(f"Export API response status: {response.status}")
    assert (
        response.ok
    ), f"Export API call failed with status {response.status}. Response: {response.text()}"
    response_json = response.json()

    # Check backend response structure (needs to match what backend endpoint returns)
    assert (
        response_json.get("success") is True
    ), f"Backend export API reported failure: {response_json.get('error', 'Unknown error')}"
    exported_code = response_json.get("python_code")
    assert exported_code is not None and isinstance(
        exported_code, str
    ), "Exported Python code not found or invalid in backend response."
    print(f"Successfully received exported code from backend API.")

    # 9. Verify Functional Equivalence
    assert verify_functional_equivalence(
        original_code, exported_code
    ), "Functional equivalence check failed."
    print("Functional equivalence check passed.")
