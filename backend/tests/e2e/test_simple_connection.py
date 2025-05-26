import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_simple_connection_workflow(page: Page):
    """
    Tests the complete workflow of:
    1. Loading a JSON file with two TaskWorker nodes
    2. Connecting the output handle from TaskWorker1 to the input handle of TaskWorker2
    3. Validating that TaskWorker2's input type becomes "Task1"
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # Load the two-workers.json file
    json_file_path = Path(__file__).parent.parent / "data" / "two-workers.json"
    assert json_file_path.exists(), f"Test data file not found: {json_file_path}"

    helper.load_json_file(json_file_path)

    # Wait for the nodes to be loaded (should be 2 TaskWorker nodes = 2 total)
    helper.wait_for_nodes(2)
    print("All nodes loaded successfully.")

    # Verify we have the expected nodes
    taskworker1_node = page.locator('[data-testid="taskworker-node"]').first
    taskworker2_node = page.locator('[data-testid="taskworker-node"]').nth(1)

    expect(taskworker1_node).to_be_visible(timeout=helper.timeout)
    expect(taskworker2_node).to_be_visible(timeout=helper.timeout)
    print("Verified all expected nodes are present.")

    # Get the Task1 ID from the JSON data to construct the correct handle ID
    # From the JSON, we can see the task has id "task-952d1928-5a93-4569-9f9b-ec8acfa11daf"
    task1_id = "task-952d1928-5a93-4569-9f9b-ec8acfa11daf"
    source_handle_id = f"output-{task1_id}"

    # We need to find the specific TaskWorker nodes by their IDs from the JSON
    # TaskWorker1 has id "taskworker-658e1ee3-16e3-4f71-8eb8-ecb7c9d5f675"
    # TaskWorker2 has id "taskworker-c0d03e66-c5b8-44f3-8ff5-09338670934f"
    taskworker1_selector = '[data-id="taskworker-658e1ee3-16e3-4f71-8eb8-ecb7c9d5f675"]'
    taskworker2_selector = '[data-id="taskworker-c0d03e66-c5b8-44f3-8ff5-09338670934f"]'

    # Before connecting, verify TaskWorker2 has no input types
    helper.click_node(taskworker2_selector)
    page.wait_for_timeout(500)  # Wait for UI to update

    # Check initial state - TaskWorker2 should have no input types
    initial_input_types = helper.get_node_input_types(taskworker2_selector)
    print(f"Initial input types for TaskWorker2: {initial_input_types}")

    # Click away to deselect
    canvas = page.locator(".svelte-flow")
    canvas.click()
    page.wait_for_timeout(500)

    # Now perform the connection by dragging from TaskWorker1's output handle to TaskWorker2's input handle
    print("Attempting to connect TaskWorker1 output to TaskWorker2 input...")

    helper.drag_from_handle_to_handle(
        source_node_selector=taskworker1_selector,
        source_handle_id=source_handle_id,
        target_node_selector=taskworker2_selector,
        target_handle_id="input",
    )

    # Wait for the connection to be established
    page.wait_for_timeout(1000)

    # Verify that an edge was created
    edges = page.locator(".svelte-flow__edge")
    expect(edges).to_have_count(1, timeout=helper.timeout)
    print("Edge created successfully.")

    # Click on TaskWorker2 to check its input types
    helper.click_node(taskworker2_selector)
    page.wait_for_timeout(500)  # Wait for UI to update

    # Verify that TaskWorker2 now has "Task1" as its input type
    final_input_types = helper.get_node_input_types(taskworker2_selector)
    print(f"Final input types for TaskWorker2: {final_input_types}")

    # Validate that "Task1" is now in the input types
    assert (
        "Task1" in final_input_types
    ), f"Expected 'Task1' in input types, but got: {final_input_types}"

    print("Test completed successfully!")
    print("✓ JSON file loaded with two TaskWorker nodes")
    print("✓ Connection established from TaskWorker1 output to TaskWorker2 input")
    print("✓ TaskWorker2 input type correctly updated to 'Task1'")


def test_connection_fails_with_incompatible_types(page: Page):
    """
    Tests that connection fails when trying to connect incompatible types:
    1. Loading a JSON file with two TaskWorker nodes
    2. Manually setting TaskWorker2's input type to "Task2"
    3. Attempting to connect TaskWorker1 (outputs Task1) to TaskWorker2 (expects Task2)
    4. Validating that the connection fails (no edge is created)
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # Load the two-workers.json file
    json_file_path = Path(__file__).parent.parent / "data" / "two-workers.json"
    assert json_file_path.exists(), f"Test data file not found: {json_file_path}"

    helper.load_json_file(json_file_path)

    # Wait for the nodes to be loaded (should be 2 TaskWorker nodes = 2 total)
    helper.wait_for_nodes(2)
    print("All nodes loaded successfully.")

    # Verify we have the expected nodes
    taskworker1_node = page.locator('[data-testid="taskworker-node"]').first
    taskworker2_node = page.locator('[data-testid="taskworker-node"]').nth(1)

    expect(taskworker1_node).to_be_visible(timeout=helper.timeout)
    expect(taskworker2_node).to_be_visible(timeout=helper.timeout)
    print("Verified all expected nodes are present.")

    # We need to find the specific TaskWorker nodes by their IDs from the JSON
    # TaskWorker1 has id "taskworker-658e1ee3-16e3-4f71-8eb8-ecb7c9d5f675"
    # TaskWorker2 has id "taskworker-c0d03e66-c5b8-44f3-8ff5-09338670934f"
    taskworker1_selector = '[data-id="taskworker-658e1ee3-16e3-4f71-8eb8-ecb7c9d5f675"]'
    taskworker2_selector = '[data-id="taskworker-c0d03e66-c5b8-44f3-8ff5-09338670934f"]'

    # Manually set TaskWorker2's input type to "Task2" (incompatible with TaskWorker1's output "Task1")
    helper.set_manual_input_type(taskworker2_selector, "Task2")

    # Verify that TaskWorker2 now has "Task2" as its input type
    input_types_after_manual_set = helper.get_node_input_types(taskworker2_selector)
    print(
        f"Input types for TaskWorker2 after manual setting: {input_types_after_manual_set}"
    )
    assert (
        "Task2" in input_types_after_manual_set
    ), f"Expected 'Task2' in input types, but got: {input_types_after_manual_set}"

    # Click away to deselect
    canvas = page.locator(".svelte-flow")
    canvas.click()
    page.wait_for_timeout(500)

    # Get the Task1 ID from the JSON data to construct the correct handle ID
    task1_id = "task-952d1928-5a93-4569-9f9b-ec8acfa11daf"
    source_handle_id = f"output-{task1_id}"

    # Now attempt the connection by dragging from TaskWorker1's output handle to TaskWorker2's input handle
    # This should fail because TaskWorker1 outputs "Task1" but TaskWorker2 expects "Task2"
    print(
        "Attempting to connect TaskWorker1 output (Task1) to TaskWorker2 input (expects Task2)..."
    )

    helper.drag_from_handle_to_handle(
        source_node_selector=taskworker1_selector,
        source_handle_id=source_handle_id,
        target_node_selector=taskworker2_selector,
        target_handle_id="input",
    )

    # Wait for any potential connection attempt to complete
    page.wait_for_timeout(1000)

    # Verify that the connection failed (no edge was created)
    connection_failed = helper.verify_connection_failed()
    assert (
        connection_failed
    ), "Expected connection to fail due to incompatible types, but an edge was created"

    # Verify that TaskWorker2 still has "Task2" as its input type (unchanged)
    helper.click_node(taskworker2_selector)
    page.wait_for_timeout(500)  # Wait for UI to update

    final_input_types = helper.get_node_input_types(taskworker2_selector)
    print(f"Final input types for TaskWorker2: {final_input_types}")

    # Validate that "Task2" is still the input type (not changed to "Task1")
    assert (
        "Task2" in final_input_types
    ), f"Expected 'Task2' to remain in input types, but got: {final_input_types}"
    assert (
        "Task1" not in final_input_types
    ), f"Expected 'Task1' NOT to be in input types, but got: {final_input_types}"

    print("Test completed successfully!")
    print("✓ JSON file loaded with two TaskWorker nodes")
    print("✓ TaskWorker2 input type manually set to 'Task2'")
    print(
        "✓ Connection attempt from TaskWorker1 (Task1) to TaskWorker2 (Task2) correctly failed"
    )
    print("✓ TaskWorker2 input type remained 'Task2' (unchanged)")
