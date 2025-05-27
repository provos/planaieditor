import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_data_input_connection_workflow(page: Page):
    """
    Tests the complete data input connection workflow:
    1. Load data-input-test.json
    2. Click on select output task type in the datainput node
    3. Select Task1 from the dropdown
    4. Connect the output handle from the data input with the input handle from TaskWorker1
    5. Validate that TaskWorker1.data.entryPoint is true
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # 1. Load the data-input-test.json file
    print("Loading data-input-test.json...")
    json_file_path = Path(__file__).parent.parent / "data/data-input-test.json"
    assert json_file_path.exists(), f"Test fixture not found at {json_file_path}"

    helper.load_json_file(json_file_path)

    # Wait for nodes to be loaded (2 nodes: datainput and taskworker)
    helper.wait_for_nodes(2)
    print("JSON file loaded successfully with 2 nodes.")

    # 2. Click on the datainput node to ensure it's selected
    datainput_node = page.locator('[data-testid="datainput-node"]')
    expect(datainput_node).to_be_visible(timeout=helper.timeout)
    datainput_node.click()
    print("DataInput node clicked.")

    # 3. Select Task1 from the output task type dropdown
    print("Selecting Task1 from output task type dropdown...")
    output_task_dropdown = datainput_node.locator(
        '[data-testid="datainput-output-task-dropdown"]'
    )
    expect(output_task_dropdown).to_be_visible(timeout=helper.timeout)

    # Select Task1 from the dropdown
    output_task_dropdown.select_option(value="Task1")
    print("Task1 selected from dropdown.")

    # Wait for the output handle to appear after task selection
    page.wait_for_timeout(2000)  # Wait for the UI to update after selection

    # Look for the output handle on the DataInput node
    output_handle = datainput_node.locator(".svelte-flow__handle")
    expect(output_handle.first).to_be_visible(timeout=helper.timeout)
    print("Output handle appeared on DataInput node.")

    # 4. Connect the output handle from the data input with the input handle from TaskWorker1
    print("Connecting DataInput output to TaskWorker1 input...")

    # Find the TaskWorker node
    taskworker_node = page.locator('[data-testid="taskworker-node"]')
    expect(taskworker_node).to_be_visible(timeout=helper.timeout)

    # Get the task ID from the DataInput node to construct the correct handle ID
    task_id = page.evaluate(
        """
        () => {
            const tasks = JSON.parse(localStorage.getItem('tasks') || '[]');
            const task1 = tasks.find(task => task.className === 'Task1');
            return task1 ? task1.id : null;
        }
        """
    )
    assert task_id, "Could not find Task1 ID in localStorage"
    print(f"Found Task1 ID: {task_id}")

    # Perform the drag from DataInput output handle to TaskWorker input handle
    helper.drag_from_handle_to_handle(
        '[data-testid="datainput-node"]',
        f"output-{task_id}",
        '[data-testid="taskworker-node"]',
        "input",
    )
    print("Connection created between DataInput and TaskWorker.")

    # Wait for the connection to be established
    page.wait_for_timeout(250)

    # Verify that an edge was created
    assert helper.verify_connection_succeeded(
        expected_edge_count=1
    ), "Connection failed - no edge created"
    print("✓ Connection verified - edge created successfully")

    # 5. Validate that TaskWorker1.data.entryPoint is true
    print("Validating that TaskWorker1.data.entryPoint is true...")

    # Get the TaskWorker node data from the browser
    taskworker_data = page.evaluate(
        """
        () => {
            const nodes = JSON.parse(localStorage.getItem('nodes') || '[]');
            const taskworkerNode = nodes.find(node => node.type === 'taskworker');
            return taskworkerNode ? taskworkerNode.data : null;
        }
        """
    )

    assert taskworker_data, "Could not find TaskWorker node data"
    print(f"TaskWorker data: {taskworker_data}")

    # Verify that entryPoint is true
    assert (
        taskworker_data.get("entryPoint") is True
    ), f"Expected entryPoint to be true, but got: {taskworker_data.get('entryPoint')}"
    print("✓ TaskWorker1.data.entryPoint is true")

    print("Test completed successfully!")
    print("✓ JSON file loaded")
    print("✓ Task1 selected as output type for DataInput")
    print("✓ DataInput connected to TaskWorker1")
    print("✓ TaskWorker1.data.entryPoint is true")
