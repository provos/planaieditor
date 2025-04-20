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

# Ensure planai can be imported (adjust if your structure differs)
# This might be handled by running pytest from the 'backend' dir
# sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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

# --- Helper Functions / Verification Logic (Placeholders) ---


def adapt_code_to_return_graph(code_string: str) -> str:
    """
    Attempts to modify the input code string so that instead of running
    the graph or main function, it assigns the created graph object to
    a known variable name (__returned_graph__) and returns it.

    This is a simplified placeholder and might need AST manipulation for robustness.
    """
    # Simple approach: comment out graph.run() and main() calls
    # and try to find the graph assignment.
    modified_lines = []
    graph_var_name = None
    in_main_def = False
    main_call_found = False

    # Find the likely graph variable name
    for line in code_string.splitlines():
        stripped_line = line.strip()
        if stripped_line.startswith("graph = Graph") or stripped_line.startswith(
            "g = Graph"
        ):
            # Basic check, might need regex for robustness
            graph_var_name = stripped_line.split("=")[0].strip()
            break  # Assume first assignment is the main graph

    if not graph_var_name:
        print("Warning: Could not reliably determine graph variable name.")
        # Fallback or raise error? For now, try 'graph'
        graph_var_name = "graph"

    for line in code_string.splitlines():
        stripped_line = line.strip()

        # Comment out graph.run() or graph.execute()
        if (
            f"{graph_var_name}.run(" in stripped_line
            or f"{graph_var_name}.execute(" in stripped_line
        ):
            modified_lines.append(f"# {line}")
            continue

        # Comment out the main execution block
        if stripped_line == 'if __name__ == "__main__":':
            in_main_def = True
            modified_lines.append(f"# {line}")
            continue
        elif in_main_def and line.startswith((" ", "\t")):
            modified_lines.append(f"# {line}")
            continue
        elif in_main_def:  # End of main block
            in_main_def = False
            # Add assignment after the commented block
            modified_lines.append(f"__returned_graph__ = {graph_var_name}")

        # Comment out direct calls to main() if found at top level
        if stripped_line.startswith("main()"):
            modified_lines.append(f"# {line}")
            main_call_found = True
            continue

        modified_lines.append(line)

    # If main block wasn't found but main() call was, add assignment at end
    if not in_main_def and main_call_found:
        modified_lines.append(f"__returned_graph__ = {graph_var_name}")
    # If neither was found, assume graph var is assigned globally and add assignment at end
    elif not in_main_def and not main_call_found:
        modified_lines.append(f"\n__returned_graph__ = {graph_var_name}")

    return "\n".join(modified_lines)


def get_graph_from_code(
    code_string: str, filename: str = "<string>"
) -> Optional["Graph"]:
    """
    Executes Python code defining a PlanAI graph and returns the Graph object.
    Uses a temporary file for execution via importlib.
    """
    # Ensure planai is importable for type hint and potential internal use
    from planai import Graph  # type: ignore

    modified_code = adapt_code_to_return_graph(code_string)
    # print(f"--- Modified Code for {filename} ---")
    # print(modified_code)
    # print("-------------------------------------")

    # Use a temporary file to execute the code
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False) as tmp_file:
        tmp_file_path = tmp_file.name
        tmp_file.write(modified_code)
        tmp_file.flush()  # Ensure content is written

    graph_instance: Optional[Graph] = None
    spec = None
    module = None
    try:
        # Dynamically import the temporary module
        module_name = Path(tmp_file_path).stem
        spec = importlib.util.spec_from_file_location(module_name, tmp_file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = (
                module  # Add to sys.modules for potential relative imports
            )
            spec.loader.exec_module(module)
            # Retrieve the graph instance assigned by adapt_code_to_return_graph
            graph_instance = getattr(module, "__returned_graph__", None)
        else:
            print(f"Error: Could not create module spec for {tmp_file_path}")

    except Exception as e:
        print(f"Error executing code from {filename} in {tmp_file_path}: {e}")
        # print("--- Failing Code ---")
        # print(modified_code)
        # print("--------------------")
        graph_instance = None  # Ensure it's None on error
    finally:
        # Clean up the temporary file and remove from sys.modules
        if module_name in sys.modules:
            del sys.modules[module_name]
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

    if not isinstance(graph_instance, Graph):
        print(f"Warning: Failed to retrieve a valid Graph object from {filename}.")
        return None

    return graph_instance


def compare_worker_configs(worker1, worker2) -> bool:
    """Compares relevant configuration attributes of two worker instances."""
    from planai import (  # type: ignore
        CachedLLMTaskWorker,
        CachedTaskWorker,
        JoinedTaskWorker,
        LLMTaskWorker,
        SubGraphWorker,
        TaskWorker,
    )

    if type(worker1) != type(worker2):
        print(f"Worker type mismatch: {type(worker1)} vs {type(worker2)}")
        return False

    attrs_to_compare = ["name"]  # Always compare name

    # Basic TaskWorker attributes (inherited)
    # attrs_to_compare.extend(['output_types']) # Comparing types is tricky due to potential dynamic generation

    if isinstance(worker1, LLMTaskWorker):  # Includes CachedLLMTaskWorker
        attrs_to_compare.extend(
            [
                "prompt",
                "system_prompt",
                "llm_input_type",
                "llm_output_type",
                "use_xml",
                "debug_mode",
            ]
        )
        # TODO: Compare LLM config if feasible?

    if isinstance(worker1, CachedTaskWorker):  # Includes CachedLLMTaskWorker
        # Compare cache settings if applicable
        pass  # Add cache-related attributes if needed

    if isinstance(worker1, JoinedTaskWorker):
        attrs_to_compare.extend(["join_type"])  # Compare join_type (by name?)

    if isinstance(worker1, SubGraphWorker):
        # Compare subgraph details - might need deeper comparison
        attrs_to_compare.extend(["entry_worker", "exit_worker"])
        # Recursively compare subgraphs? graph1.graph vs graph2.graph?
        # For now, just check entry/exit worker names if they are strings
        if not compare_graphs(worker1.graph, worker2.graph):
            print(f"Subgraph comparison failed for {worker1.name}")
            return False

    for attr in attrs_to_compare:
        val1 = getattr(worker1, attr, None)
        val2 = getattr(worker2, attr, None)

        # Special handling for type comparisons (compare names)
        if attr in ("llm_input_type", "llm_output_type", "join_type"):
            name1 = val1.__name__ if val1 else None
            name2 = val2.__name__ if val2 else None
            if name1 != name2:
                print(
                    f"Worker '{worker1.name}' attribute '{attr}' mismatch: {name1} vs {name2}"
                )
                return False
            continue  # Skip normal comparison

        # Compare entry/exit worker names for SubGraphWorker
        if isinstance(worker1, SubGraphWorker) and attr in (
            "entry_worker",
            "exit_worker",
        ):
            name1 = val1.name if val1 else None  # Assuming they have .name
            name2 = val2.name if val2 else None
            if name1 != name2:
                print(
                    f"Subgraph worker '{worker1.name}' attribute '{attr}' mismatch: {name1} vs {name2}"
                )
                return False
            continue

        if val1 != val2:
            # Improve printing for long prompts
            if (
                attr in ("prompt", "system_prompt")
                and isinstance(val1, str)
                and isinstance(val2, str)
            ):
                if len(val1) > 100 or len(val2) > 100:
                    print(
                        f"Worker '{worker1.name}' attribute '{attr}' mismatch (showing first 100 chars):"
                    )
                    print(f"  Graph1: {val1[:100]}...")
                    print(f"  Graph2: {val2[:100]}...")
                else:
                    print(
                        f"Worker '{worker1.name}' attribute '{attr}' mismatch: {val1!r} vs {val2!r}"
                    )

            else:
                print(
                    f"Worker '{worker1.name}' attribute '{attr}' mismatch: {val1} vs {val2}"
                )
            return False
    return True


def compare_graphs(graph1: Optional["Graph"], graph2: Optional["Graph"]) -> bool:
    """
    Compares two PlanAI Graph objects for functional equivalence.
    Focuses on structure and configuration, not instance IDs.
    """
    from planai import Graph  # type: ignore

    if graph1 is None or graph2 is None:
        print("Cannot compare graphs, one or both failed to load.")
        return False
    if not isinstance(graph1, Graph) or not isinstance(graph2, Graph):
        print("Cannot compare, inputs are not Graph objects.")
        return False

    # 1. Compare Name
    if graph1.name != graph2.name:
        print(f"Graph name mismatch: '{graph1.name}' vs '{graph2.name}'")
        return False

    # 2. Compare Workers (by name and configuration)
    workers1_map = {w.name: w for w in graph1.workers}
    workers2_map = {w.name: w for w in graph2.workers}

    if set(workers1_map.keys()) != set(workers2_map.keys()):
        print(f"Worker set mismatch:")
        print(f"  Graph1: {set(workers1_map.keys())}")
        print(f"  Graph2: {set(workers2_map.keys())}")
        return False

    for name, worker1 in workers1_map.items():
        worker2 = workers2_map[name]
        if not compare_worker_configs(worker1, worker2):
            # Error already printed in compare_worker_configs
            return False

    # 3. Compare Dependencies (structure based on worker names)
    deps1 = set()
    for source, targets in graph1.dependencies.items():
        for target in targets:
            deps1.add((source.name, target.name))

    deps2 = set()
    for source, targets in graph2.dependencies.items():
        for target in targets:
            deps2.add((source.name, target.name))

    if deps1 != deps2:
        print(f"Dependency mismatch:")
        print(f"  Graph1: {deps1}")
        print(f"  Graph2: {deps2}")
        return False

    # 4. Compare Entry Points (by worker name and input task type name)
    # Assuming entry_points stores tuples of (worker, task_type)
    # We need to compare worker.name and task_type.__name__
    entries1 = set()
    for worker, task_type in graph1.entry_points:
        type_name = task_type.__name__ if task_type else None
        entries1.add((worker.name, type_name))

    entries2 = set()
    for worker, task_type in graph2.entry_points:
        type_name = task_type.__name__ if task_type else None
        entries2.add((worker.name, type_name))

    if entries1 != entries2:
        print(f"Entry point mismatch:")
        print(f"  Graph1: {entries1}")
        print(f"  Graph2: {entries2}")
        return False

    # TODO: Compare Sinks?
    # TODO: Compare Task Definitions? (Implicitly checked via worker configs/entry points)

    print("Graph comparison successful.")
    return True


def verify_functional_equivalence(original_code: str, exported_code: str) -> bool:
    """
    Verifies functional equivalence by extracting and comparing Graph objects.
    """
    print("Verifying functional equivalence...")
    # print("--- Original Code ---")
    # print(original_code[:500] + "...") # Print snippet
    # print("--- Exported Code ---")
    # print(exported_code[:500] + "...") # Print snippet

    original_graph = get_graph_from_code(original_code, "original")
    exported_graph = get_graph_from_code(exported_code, "exported")

    return compare_graphs(original_graph, exported_graph)


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
        raise RuntimeError(
            f"Backend server failed to start. Exit code: {server_process.returncode}"
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
    import_button = page.locator('button[data-testid="import-button"]')
    expect(import_button).to_be_enabled(timeout=TIMEOUT)

    try:
        # Start waiting for the response *before* clicking the button
        # that triggers the action causing the response.
        with page.expect_response(
            lambda response: "/api/import-python" in response.url
            and response.request.method == "POST",
            timeout=TIMEOUT,
        ) as response_info:
            with page.expect_file_chooser(timeout=TIMEOUT) as fc_info:
                print("Clicking import button...")
                import_button.click()
                print("Import button clicked.")
            file_chooser = fc_info.value
            print(f"File chooser opened, setting file: {TEST_FIXTURE_PATH}")
            file_chooser.set_files(TEST_FIXTURE_PATH)
            print("File chooser handled and file set.")

        # Now process the response
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

        # Give frontend a moment to process the successful response and render nodes
        page.wait_for_timeout(1000)

    except Exception as e:
        pytest.fail(f"Failed during file chooser or API wait: {e}")

    # 4. Wait for import success indication
    # Check for a specific node from releasenotes.py (e.g., CommitCollector)
    commit_collector_node_selector = (
        'div.svelte-flow__node[data-id*="imported-taskworker-CommitCollector"]'
    )
    print(f"Waiting for node: {commit_collector_node_selector}")
    expect(page.locator(commit_collector_node_selector)).to_be_visible(timeout=TIMEOUT)
    print("CommitCollector node found.")

    # 5. Get graph data from frontend localStorage for export
    # Give the frontend a moment to potentially update localStorage after import
    page.wait_for_timeout(500)
    nodes_data = page.evaluate("() => JSON.parse(localStorage.getItem('nodes'))")
    edges_data = page.evaluate("() => JSON.parse(localStorage.getItem('edges'))")

    assert nodes_data is not None, "Failed to retrieve nodes data from localStorage"
    assert edges_data is not None, "Failed to retrieve edges data from localStorage"
    assert len(nodes_data) > 0, "No nodes found in localStorage after import"

    graph_data = {"nodes": nodes_data, "edges": edges_data}
    print(
        f"Retrieved {len(nodes_data)} nodes and {len(edges_data)} edges from frontend localStorage."
    )

    # Verify Export button is present and enabled (even though we call API directly)
    export_button = page.locator('button[data-testid="export-button"]')
    expect(export_button).to_be_visible(timeout=TIMEOUT)
    expect(export_button).to_be_enabled(timeout=TIMEOUT)

    # 6. Trigger Export via Synchronous Backend API
    # This requires the backend Flask app to have an endpoint like /api/export-sync
    export_api_url = f"{BACKEND_TEST_URL}/api/export-sync"
    print(f"Triggering export via synchronous API: {export_api_url}...")

    # Use Playwright's request context to make the API call directly to the backend
    api_context = page.request
    try:
        response = api_context.post(
            export_api_url,
            data=json.dumps(graph_data),
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT,  # Add timeout to the request
        )
    except Exception as e:
        pytest.fail(f"API call to {export_api_url} failed: {e}")

    # 7. Get exported code from response
    print(f"Export API response status: {response.status}")
    expect(response).to_be_ok(
        message=f"Export API call failed with status {response.status}. Response: {response.text()}"
    )
    response_json = response.json()

    # Check backend response structure (needs to match what backend endpoint returns)
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


# Add more tests for different fixture files if needed
# def test_another_graph_roundtrip(page: Page, backend_server):
#     ...
