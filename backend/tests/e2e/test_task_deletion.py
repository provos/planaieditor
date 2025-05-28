import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_task_deletion_workflow(page: Page):
    """
    Tests the task deletion workflow:
    1. Load edge-removal.json
    2. Drag open the side pane to show the task definitions
    3. Under the task definitions tab, delete Sentiment
    4. Validate that Sentiment is no longer a defined task
    5. Try to delete the task definition for Response
    6. Validate that the button for deleting Response is disabled
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # 1. Load the edge-removal.json file
    print("Loading edge-removal.json...")
    json_file_path = Path(__file__).parent.parent / "data/edge-removal.json"
    assert json_file_path.exists(), f"Test fixture not found at {json_file_path}"

    helper.load_json_file(json_file_path)

    # Wait for nodes to be loaded (4 nodes: datainput, 2 llmtaskworkers, dataoutput)
    helper.wait_for_nodes(4)
    print("JSON file loaded successfully with 4 nodes.")

    # 2. Open the side pane to show the task definitions
    print("Step 2: Opening the side pane...")
    helper.open_split_pane_programmatically()

    # Verify the side pane is open and Task Definitions tab is visible
    tasks_tab = page.locator('[data-testid="tasks-tab"]')
    expect(tasks_tab).to_be_visible(timeout=helper.timeout)
    print("✓ Side pane opened and Task Definitions tab is visible.")

    # Check if the tasks tab is already active (it should be by default)
    active_tasks_tab = page.locator('[data-testid="tasks-tab"][data-state="active"]')
    if not active_tasks_tab.is_visible():
        # If not active, try to click it with force to overcome overlapping elements
        print("Tasks tab not active, clicking to activate...")
        tasks_tab.click(force=True)
        page.wait_for_timeout(250)
    else:
        print("Tasks tab is already active.")

    # Wait a bit more for the split pane to fully open
    page.wait_for_timeout(1000)

    # Debug: Check if the tasks tab content exists but is hidden
    tasks_tab_content = page.locator('[data-testid="tasks-tab-content"]')
    if tasks_tab_content.count() > 0:
        print("Tasks tab content element exists")
        # Check if it's visible
        if tasks_tab_content.is_visible():
            print("✓ Task Definitions tab content is visible.")
        else:
            print("Tasks tab content exists but is not visible, waiting longer...")
            # Wait longer and try to make it visible by scrolling or other actions
            page.wait_for_timeout(2000)

            # Try scrolling to the element
            try:
                tasks_tab_content.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
            except Exception:
                pass

            # Check again
            if tasks_tab_content.is_visible():
                print("✓ Task Definitions tab content is now visible after scrolling.")
            else:
                print("Tasks tab content still not visible, proceeding anyway...")
    else:
        print("Tasks tab content element does not exist")

    # Continue with the test even if content is not fully visible
    print("Proceeding with task deletion test...")

    # 3. Under the task definitions tab, delete Sentiment
    print("Step 3: Deleting Sentiment task...")

    # Find the Sentiment task in the list
    sentiment_task_item = tasks_tab_content.locator(
        '[data-testid="list-item"][data-item-name="Sentiment"]'
    )
    expect(sentiment_task_item).to_be_visible(timeout=helper.timeout)
    print("Found Sentiment task in the list.")

    # Hover over the Sentiment task to make the delete button visible
    sentiment_task_item.hover()
    page.wait_for_timeout(200)  # Wait for hover effect

    # Find and click the delete button for Sentiment
    sentiment_delete_button = sentiment_task_item.locator(
        '[data-testid="delete-item-button"]'
    )
    expect(sentiment_delete_button).to_be_visible(timeout=helper.timeout)
    expect(sentiment_delete_button).to_be_enabled(timeout=helper.timeout)

    sentiment_delete_button.click()
    page.wait_for_timeout(500)  # Wait for deletion to process
    print("Sentiment task deleted.")

    # 4. Validate that Sentiment is no longer a defined task
    print("Step 4: Validating that Sentiment is no longer defined...")

    # Check that the Sentiment task item is no longer in the list
    sentiment_task_item_after = tasks_tab_content.locator(
        '[data-testid="list-item"][data-item-name="Sentiment"]'
    )
    expect(sentiment_task_item_after).not_to_be_visible(timeout=helper.timeout)
    print("✓ Sentiment task is no longer visible in the task list.")

    # Also verify by checking the browser's localStorage for tasks
    remaining_tasks = page.evaluate(
        """
        () => {
            const tasks = JSON.parse(localStorage.getItem('tasks') || '[]');
            return tasks.map(task => task.className);
        }
        """
    )
    print(f"Remaining tasks in localStorage: {remaining_tasks}")
    assert (
        "Sentiment" not in remaining_tasks
    ), f"Sentiment should not be in remaining tasks: {remaining_tasks}"
    print("✓ Sentiment task confirmed removed from localStorage.")

    # 5. Try to delete the task definition for Response
    print("Step 5: Attempting to delete Response task...")

    # Find the Response task in the list
    response_task_item = tasks_tab_content.locator(
        '[data-testid="list-item"][data-item-name="Response"]'
    )
    expect(response_task_item).to_be_visible(timeout=helper.timeout)
    print("Found Response task in the list.")

    # Hover over the Response task to make the delete button visible
    response_task_item.hover()
    page.wait_for_timeout(200)  # Wait for hover effect

    # Find the delete button for Response
    response_delete_button = response_task_item.locator(
        '[data-testid="delete-item-button"]'
    )
    expect(response_delete_button).to_be_visible(timeout=helper.timeout)

    # 6. Validate that the button for deleting Response is disabled
    print("Step 6: Validating that Response delete button is disabled...")

    # Check that the delete button is disabled
    expect(response_delete_button).to_be_disabled(timeout=helper.timeout)
    print("✓ Response task delete button is disabled.")

    # Verify the disabled state by checking the aria-disabled attribute
    aria_disabled = response_delete_button.get_attribute("aria-disabled")
    assert (
        aria_disabled == "true"
    ), f"Expected aria-disabled='true', got '{aria_disabled}'"
    print("✓ Response task delete button has aria-disabled='true'.")

    # Verify the title attribute explains why it's disabled
    title_text = response_delete_button.get_attribute("title")
    assert (
        "Cannot delete item with connected edges" in title_text
    ), f"Expected disabled tooltip, got: '{title_text}'"
    print("✓ Response task delete button has appropriate disabled tooltip.")

    # Try clicking the disabled button to ensure it doesn't work
    print("Attempting to click disabled delete button...")
    response_delete_button.click(force=True)
    page.wait_for_timeout(500)

    # Verify Response task is still in the list after attempted deletion
    response_task_item_after = tasks_tab_content.locator(
        '[data-testid="list-item"][data-item-name="Response"]'
    )
    expect(response_task_item_after).to_be_visible(timeout=helper.timeout)
    print("✓ Response task is still visible after clicking disabled delete button.")

    # Verify Response is still in localStorage
    final_tasks = page.evaluate(
        """
        () => {
            const tasks = JSON.parse(localStorage.getItem('tasks') || '[]');
            return tasks.map(task => task.className);
        }
        """
    )
    print(f"Final tasks in localStorage: {final_tasks}")
    assert (
        "Response" in final_tasks
    ), f"Response should still be in tasks: {final_tasks}"
    print("✓ Response task confirmed still in localStorage.")

    print("Test completed successfully!")
    print("✓ JSON file loaded with 4 nodes")
    print("✓ Side pane opened to show task definitions")
    print("✓ Task Definitions tab activated")
    print("✓ Sentiment task successfully deleted")
    print("✓ Sentiment task no longer appears in task list")
    print("✓ Sentiment task removed from localStorage")
    print("✓ Response task delete button is disabled")
    print("✓ Response task delete button has correct disabled attributes")
    print("✓ Response task cannot be deleted (still in list and localStorage)")
