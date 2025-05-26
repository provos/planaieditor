"""
E2E Test Utilities for PlanAI Editor

This module provides common utilities and patterns for E2E tests using Playwright.
"""

import json
import os
import pprint
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from playwright.sync_api import APIResponse, Page, Route, expect

# --- Configuration Constants ---
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
BACKEND_TEST_PORT = os.environ.get("BACKEND_TEST_PORT", "5001")
BACKEND_TEST_URL = f"http://localhost:{BACKEND_TEST_PORT}"
TIMEOUT = 15000  # Default timeout in milliseconds

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)

# Ensure planaieditor can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))


class E2ETestHelper:
    """
    A helper class that encapsulates common E2E test operations.

    This class provides a high-level interface for common test operations
    like page setup, navigation, graph manipulation, and API interactions.
    """

    def __init__(self, page: Page, timeout: int = TIMEOUT):
        self.page = page
        self.timeout = timeout
        self._setup_route_handler()

    def _setup_route_handler(self, debug: bool = True):
        """Set up route handler for debugging API calls."""

        def handle_route(route: Route):
            if debug and "/api/" in route.request.url:
                print(
                    f"Intercepted request: {route.request.method} {route.request.url}"
                )
            route.continue_()

        self.page.route("**/*", handle_route)

    def navigate_to_frontend(self) -> None:
        """Navigate to the frontend and wait for it to load."""
        print(f"Navigating to frontend: {FRONTEND_URL}")
        self.page.goto(FRONTEND_URL)
        expect(self.page.locator('[data-testid="toolshelf-container"]')).to_be_visible(
            timeout=self.timeout
        )
        print("Frontend loaded.")

    def clear_graph(self) -> None:
        """Clear any existing graph from the canvas."""
        clear_button = self.page.locator('button[title="Clear Graph"]')
        if self.page.locator(".svelte-flow__node").first.is_visible(timeout=2000):
            print("Clearing existing graph...")
            clear_button.click(force=True)
            self.page.once("dialog", lambda dialog: dialog.accept())
            expect(self.page.locator(".svelte-flow__node")).to_have_count(
                0, timeout=self.timeout
            )
            print("Graph cleared.")
        else:
            print("No existing graph detected, skipping clear.")

    def setup_virtual_environment(self) -> APIResponse:
        """Set up virtual environment and return the API response."""
        print("Setting up virtual environment...")
        interpreter_button = self.page.locator(
            'button[data-testid="interpreter-button"]'
        )
        expect(interpreter_button).to_be_visible(timeout=self.timeout)
        expect(interpreter_button).to_be_enabled(timeout=self.timeout)

        with self.page.expect_response(
            lambda response: "/api/set-venv" in response.url
            and response.request.method == "POST",
            timeout=self.timeout,
        ) as response_info:
            interpreter_button.click()

        api_response: APIResponse = response_info.value
        print(f"Virtual environment setup response: {api_response.status}")
        assert (
            api_response.ok
        ), f"Virtual environment setup failed with status {api_response.status}"

        return api_response

    def switch_to_tab(self, tab_name: str) -> None:
        """Switch to a specific tab in the ToolShelf."""
        print(f"Switching to {tab_name} tab...")
        tab_selector = f'[data-testid="{tab_name.lower()}-tab"]'
        tab = self.page.locator(tab_selector)
        expect(tab).to_be_visible(timeout=self.timeout)
        tab.click()

        # Wait for the tab content to be visible
        active_tab_selector = (
            f'[data-testid="{tab_name.lower()}-tab"][data-state="active"]'
        )
        expect(self.page.locator(active_tab_selector)).to_be_visible(
            timeout=self.timeout
        )
        print(f"{tab_name} tab activated.")

    def drag_element_to_canvas(
        self, draggable_selector: str, offset_x: int = 0, offset_y: int = 0
    ) -> tuple[float, float]:
        """
        Drag an element from the toolshelf onto the canvas.

        Args:
            draggable_selector: CSS selector for the draggable element
            offset_x: X offset from canvas center
            offset_y: Y offset from canvas center

        Returns:
            Tuple of (drop_x, drop_y) coordinates where the element was dropped
        """
        print(f"Dragging element {draggable_selector} onto canvas...")
        draggable = self.page.locator(draggable_selector)
        expect(draggable).to_be_visible(timeout=self.timeout)

        # Get the canvas area for dropping
        canvas = self.page.locator(".svelte-flow")
        expect(canvas).to_be_visible(timeout=self.timeout)

        # Get bounding boxes for drag and drop
        draggable_box = draggable.bounding_box()
        canvas_box = canvas.bounding_box()

        assert (
            draggable_box is not None
        ), f"Draggable element {draggable_selector} bounding box not found"
        assert canvas_box is not None, "Canvas bounding box not found"

        # Calculate drop position (center of canvas + offset)
        drop_x = canvas_box["x"] + canvas_box["width"] / 2 + offset_x
        drop_y = canvas_box["y"] + canvas_box["height"] / 2 + offset_y

        # Perform drag and drop
        self.page.mouse.move(
            draggable_box["x"] + draggable_box["width"] / 2,
            draggable_box["y"] + draggable_box["height"] / 2,
        )
        self.page.mouse.down()
        self.page.mouse.move(drop_x, drop_y)
        self.page.mouse.up()

        print(f"Element dragged to position ({drop_x}, {drop_y})")
        return drop_x, drop_y

    def wait_for_nodes(self, expected_count: int, timeout_multiplier: int = 1) -> None:
        """Wait for a specific number of nodes to appear on the canvas."""
        timeout = self.timeout * timeout_multiplier
        print(f"Waiting for {expected_count} nodes to render...")
        expect(self.page.locator(".svelte-flow__node")).to_have_count(
            expected_count, timeout=timeout
        )
        print(f"{expected_count} nodes rendered.")

    def click_node(self, node_selector: str) -> None:
        """Click on a specific node on the canvas."""
        print(f"Clicking on node {node_selector}...")
        node = self.page.locator(node_selector)
        expect(node).to_be_visible(timeout=self.timeout)
        node.click()
        print(f"Node {node_selector} clicked.")

    def import_python_file(self, file_path: Path) -> APIResponse:
        """
        Import a Python file using the file chooser dialog.

        Args:
            file_path: Path to the Python file to import

        Returns:
            The API response from the import operation
        """
        print(f"Importing Python file: {file_path}")

        # First, we need to simulate a real user click to satisfy browser security requirements
        import_button = self.page.locator('button[data-testid="import-button"]')
        expect(import_button).to_be_visible(timeout=self.timeout)
        expect(import_button).to_be_enabled(timeout=self.timeout)

        # Set up both file chooser and API response expectations
        with self.page.expect_file_chooser(timeout=self.timeout) as file_chooser_info:
            print("Clicking import button with real user gesture...")
            import_button.click()
            print("Import button clicked")
            import_button.hover()  # Simulate mouse moving over
            self.page.mouse.down()  # Press the left mouse button
            self.page.mouse.up()  # Release the left mouse button

        # Handle the file chooser that should now be open
        file_chooser = file_chooser_info.value
        print(f"File chooser opened, setting file: {file_path}")

        # Now set up the API response expectation and set the files
        with self.page.expect_response(
            lambda response: "/api/import-python" in response.url
            and response.request.method == "POST",
            timeout=self.timeout,
        ) as response_info:
            file_chooser.set_files(file_path)
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

        return api_response

    def get_graph_data_from_browser(self) -> Dict[str, Any]:
        """Extract graph data from the browser using localStorage and convertGraphToJSON."""
        print(
            "Retrieving data from localStorage and calling window.convertGraphToJSON..."
        )

        graph_data_transformed = self.page.evaluate(
            """
            async () => {
                const nodes_raw = JSON.parse(localStorage.getItem('nodes'));
                const edges_raw = JSON.parse(localStorage.getItem('edges'));
                if (!nodes_raw || !edges_raw) {
                    console.error('Missing nodes or edges in localStorage'); 
                    return null;
                }
                if (typeof window.convertGraphToJSON !== 'function') {
                    console.error('window.convertGraphToJSON is not defined'); 
                    return null;
                }
                console.log('Executing window.convertGraphToJSON...');
                try {
                    const result = window.convertGraphToJSON(nodes_raw, edges_raw, mode="export");
                    console.log('window.convertGraphToJSON result:', result);
                    return result;
                } catch (error) {
                    console.error('Error executing window.convertGraphToJSON:', error);
                    return { error: error.message };
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
            f"Received transformed data: {len(graph_data_transformed['nodes'])} nodes, "
            f"{len(graph_data_transformed['edges'])} edges."
        )

        return graph_data_transformed

    def export_graph_to_python(self, graph_data: Dict[str, Any]) -> str:
        """
        Export graph data to Python code using the backend API.

        Args:
            graph_data: The graph data to export

        Returns:
            The generated Python code as a string
        """
        export_api_url = f"{BACKEND_TEST_URL}/api/export-transformed"
        print(f"Triggering export API: {export_api_url}...")

        api_context = self.page.request
        try:
            response = api_context.post(
                export_api_url,
                data=json.dumps(graph_data),
                headers={"Content-Type": "application/json"},
                timeout=self.timeout * 2,
            )
        except Exception as e:
            pytest.fail(f"API call to {export_api_url} failed: {e}")

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
        return exported_code


# --- Standalone Utility Functions ---


def setup_basic_test_environment(page: Page) -> E2ETestHelper:
    """
    Set up a basic test environment with common initialization steps.

    This function performs the most common setup steps:
    1. Navigate to frontend
    2. Clear any existing graph
    3. Set up virtual environment

    Returns:
        An E2ETestHelper instance ready for use
    """
    helper = E2ETestHelper(page)
    helper.navigate_to_frontend()
    helper.clear_graph()
    helper.setup_virtual_environment()
    return helper


def create_new_task_in_side_pane(
    helper: E2ETestHelper, task_name: str = "MyTestTask"
) -> str:
    """
    Create a new task using the side pane interface.

    Args:
        helper: An E2ETestHelper instance
        task_name: Name for the new task

    Returns:
        The name of the created task
    """
    print("Creating new task...")

    # Look for the plus button to add a new task within the tasks tab content
    tasks_tab_content = helper.page.locator('[data-testid="tasks-tab-content"]')
    add_task_button = tasks_tab_content.locator(
        '[data-testid="create-new-item-button"]'
    )
    expect(add_task_button).to_be_visible(timeout=helper.timeout)
    add_task_button.click()

    # Wait for the task to be created and the edit pane to show TaskConfig
    expect(helper.page.locator('input[type="text"]').first).to_be_visible(
        timeout=helper.timeout
    )
    print("New task created and TaskConfig opened in edit pane.")

    # Set task name
    class_name_input = helper.page.locator('[data-testid="task-name-value"]')
    expect(class_name_input).to_be_visible(timeout=helper.timeout)

    current_task_name = class_name_input.text_content()
    if not current_task_name or current_task_name.strip() in ["", "Task", "Unknown"]:
        print(f"Setting task name to: {task_name}")
        class_name_input.click()
        class_name_input.fill(task_name)
        class_name_input.press("Enter")
        helper.page.wait_for_timeout(500)  # Wait for save
        current_task_name = task_name

    # Add a simple field to make the task more realistic
    add_field_button = helper.page.locator('button[title="Add field"]')
    expect(add_field_button).to_be_visible(timeout=helper.timeout)
    add_field_button.click()

    # Fill in field details
    field_name_input = helper.page.locator('input[placeholder="field_name"]')
    expect(field_name_input).to_be_visible(timeout=helper.timeout)
    field_name_input.fill("message")

    # Save the field
    save_field_button = helper.page.locator('button:has-text("Add")')
    expect(save_field_button).to_be_visible(timeout=helper.timeout)
    save_field_button.click()

    print("Field added to task successfully.")

    return current_task_name


def _recursive_compare(obj1: Any, obj2: Any, path: str = "") -> List[Dict[str, Any]]:
    """Recursively compares two objects and returns a list of differences."""
    diffs = []

    # Type mismatch
    if type(obj1) is not type(obj2):
        diffs.append(
            {
                "path": path,
                "type": "type_mismatch",
                "old_type": type(obj1).__name__,
                "new_type": type(obj2).__name__,
            }
        )
        return diffs

    # Dictionary comparison
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
        for k in common:
            full_path = f"{path}.{k}" if path else k
            diffs.extend(_recursive_compare(obj1[k], obj2[k], full_path))

    # List comparison
    elif isinstance(obj1, list):
        len1, len2 = len(obj1), len(obj2)
        for i in range(min(len1, len2)):
            item_path = f"{path}[{i}]"
            diffs.extend(_recursive_compare(obj1[i], obj2[i], item_path))
        if len1 > len2:
            for i in range(len2, len1):
                item_path = f"{path}[{i}]"
                diffs.append({"path": item_path, "type": "removed", "value": obj1[i]})
        elif len2 > len1:
            for i in range(len1, len2):
                item_path = f"{path}[{i}]"
                diffs.append({"path": item_path, "type": "added", "value": obj2[i]})

    # Primitive comparison
    elif obj1 != obj2:
        diffs.append(
            {"path": path, "type": "changed", "old": repr(obj1), "new": repr(obj2)}
        )

    return diffs


def format_diff(diff: Dict[str, Any]) -> str:
    """Formats a single difference dictionary into a readable string."""
    path = diff["path"] if diff["path"] else "<root>"
    dtype = diff["type"]

    if dtype == "type_mismatch":
        return f"{path}: Type mismatch - {diff['old_type']} vs {diff['new_type']}"
    elif dtype == "added":
        value_str = pprint.pformat(diff["value"], indent=2, width=60)
        if "\n" in value_str:
            lines = value_str.split("\n")
            indented_lines = [lines[0]] + ["    " + line for line in lines[1:]]
            value_str = "\n    " + "\n".join(indented_lines)
        return f"{path}: Added = {value_str}"
    elif dtype == "removed":
        value_str = pprint.pformat(diff["value"], indent=2, width=60)
        if "\n" in value_str:
            lines = value_str.split("\n")
            indented_lines = [lines[0]] + ["    " + line for line in lines[1:]]
            value_str = "\n    " + "\n".join(indented_lines)
        return f"{path}: Removed = {value_str}"
    elif dtype == "changed":
        return f"{path}: Changed\n    Old: {diff['old']}\n    New: {diff['new']}"
    else:
        return f"Unknown diff @ {path}: {pprint.pformat(diff)}"


def compare_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> bool:
    """
    Recursively compares two dictionaries and pretty-prints the differences.
    Returns True if they are equal, False otherwise.
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        print("Error: Both inputs must be dictionaries for compare_dicts.")
        return False

    differences = _recursive_compare(dict1, dict2, path="")

    if not differences:
        return True
    else:
        print("--- Dictionary Comparison Differences ---")
        for diff in differences:
            print(f"  {format_diff(diff)}")
        print("--- End Dictionary Comparison ---")
        return False


# --- Test Debugging Utilities ---


def save_debug_data(
    data: Any, filename: str, test_request: Optional[Any] = None
) -> None:
    """
    Save debug data to a file if the appropriate pytest option is set.

    Args:
        data: The data to save
        filename: Name of the file to save to
        test_request: pytest request object (optional)
    """
    if test_request and hasattr(test_request.config, "getoption"):
        if test_request.config.getoption("--write-transformed-data", default=False):
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Debug data saved to {filename}")


def get_available_tasks_from_browser(page: Page) -> List[str]:
    """Get list of available tasks from the browser for debugging."""
    return page.evaluate(
        """
        () => {
            // Check if taskClassNamesStore is available
            if (window.taskClassNamesStore) {
                return Array.from(window.taskClassNamesStore);
            }
            // Fallback: check localStorage for tasks
            const tasks = JSON.parse(localStorage.getItem('tasks') || '[]');
            return tasks.map(task => task.className || 'Unknown');
        }
        """
    )
