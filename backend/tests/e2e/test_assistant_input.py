import os

import pytest
from playwright.sync_api import Page, expect
from utils import get_task_imports_from_browser, setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_assistant_input_workflow(page: Page):
    """
    Tests the complete assistant input workflow:
    1. Drag an assistant input node from the data tab onto the canvas
    2. Validate that a ChatTask was added to the taskImports store
    3. Wait and check that the datainput node has a validation error
    4. Clear the graph and validate everything is cleaned up
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # 1. Switch to Data tab in ToolShelf to access assistant input node
    helper.switch_to_tab("data")

    # Verify we start with no task imports
    initial_task_imports = get_task_imports_from_browser(page)
    print(f"Initial task imports: {initial_task_imports}")
    assert (
        len(initial_task_imports) == 0
    ), f"Expected no initial task imports, but found: {initial_task_imports}"

    # 2. Drag an assistant input node onto the canvas
    print("Dragging assistant input node onto canvas...")

    # Look for the assistant input draggable element
    assistant_input_draggable = page.locator('[data-testid="draggable-assistantinput"]')
    expect(assistant_input_draggable).to_be_visible(timeout=helper.timeout)

    # Perform the drag and drop
    helper.drag_element_to_canvas('[data-testid="draggable-assistantinput"]')

    # Wait for the datainput node to appear on canvas (assistant input becomes a datainput node)
    expect(page.locator('[data-testid="datainput-node"]')).to_be_visible(
        timeout=helper.timeout
    )
    print("Assistant input node (DataInput) successfully added to canvas.")

    # Verify we now have 1 node on the canvas
    helper.wait_for_nodes(1)

    # 3. Validate that a ChatTask was added to the taskImports store
    print("Checking that ChatTask was added to taskImports store...")
    page.wait_for_timeout(150)  # Brief wait for store updates

    task_imports = get_task_imports_from_browser(page)
    print(f"Task imports after adding assistant input: {task_imports}")

    # Verify we have exactly one task import
    assert (
        len(task_imports) == 1
    ), f"Expected 1 task import, but found {len(task_imports)}: {task_imports}"

    # Verify it's a ChatTask
    chat_task_import = task_imports[0]
    assert (
        chat_task_import["className"] == "ChatTask"
    ), f"Expected ChatTask, but found: {chat_task_import['className']}"
    assert (
        chat_task_import["modulePath"] == "planai"
    ), f"Expected modulePath 'planai', but found: {chat_task_import['modulePath']}"
    assert (
        chat_task_import["type"] == "taskimport"
    ), f"Expected type 'taskimport', but found: {chat_task_import['type']}"

    print("✓ ChatTask successfully added to taskImports store")

    # 4. Wait about a second and then check for validation error
    print("Waiting for validation error to appear...")
    page.wait_for_timeout(250)  # Wait 1 second as specified

    # Look for error message in the datainput node
    datainput_node = page.locator('[data-testid="datainput-node"]')
    expect(datainput_node).to_be_visible(timeout=helper.timeout)

    # Check for validation error text
    error_text = datainput_node.locator('text="1 validation error for ChatTask"')
    expect(error_text).to_be_visible(timeout=helper.timeout)
    print(
        "✓ Validation error '1 validation error for ChatTask' found in DataInput node"
    )

    # 5. Clear the graph by pressing the clear button
    print("Clearing the graph...")
    clear_button = page.locator('[data-testid="clear-button"]')
    expect(clear_button).to_be_visible(timeout=helper.timeout)

    # Set up dialog handler before clicking
    page.on("dialog", lambda dialog: dialog.accept())

    # Click clear button
    clear_button.click()
    print("Clicked clear button and accepted confirmation dialog")

    # Wait for nodes to be removed
    expect(page.locator(".svelte-flow__node")).to_have_count(0, timeout=helper.timeout)
    print("✓ All nodes removed from canvas")

    # 6. Validate that task imports are also cleared
    print("Verifying task imports are cleared...")
    page.wait_for_timeout(150)  # Brief wait for store cleanup

    final_task_imports = get_task_imports_from_browser(page)
    print(f"Final task imports after clear: {final_task_imports}")
    assert (
        len(final_task_imports) == 0
    ), f"Expected no task imports after clear, but found: {final_task_imports}"
    print("✓ Task imports store cleared successfully")

    print("Test completed successfully!")
    print("✓ Assistant input node dragged onto canvas")
    print("✓ ChatTask added to taskImports store")
    print("✓ Validation error appeared in DataInput node")
    print("✓ Graph cleared successfully")
    print("✓ Task imports store cleaned up")
