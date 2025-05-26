import os

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_simple_worker_drag_and_drop_workflow(page: Page):
    """
    Tests the complete workflow of:
    1. Dragging a task node onto the canvas
    2. Dragging a task worker onto the canvas
    3. Clicking on task node to open side pane with task definitions tab
    4. Creating a new task in the list pane
    5. Verifying the new task appears in TaskConfig
    6. Selecting the new task as output type for the task worker
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # 4. Switch to Configuration tab in ToolShelf to access task and worker nodes
    helper.switch_to_tab("config")

    # 5. Drag a task node onto the canvas
    drop_x, drop_y = helper.drag_element_to_canvas('[data-testid="draggable-task"]')

    # Wait for task node to appear on canvas
    expect(page.locator('[data-testid="task-node"]')).to_be_visible(
        timeout=helper.timeout
    )
    print("Task node successfully added to canvas.")

    # 6. Switch to Workers tab and drag a TaskWorker onto the canvas
    helper.switch_to_tab("workers")

    # Drag TaskWorker with offset to the right of the task node
    drop_x_worker, drop_y_worker = helper.drag_element_to_canvas(
        '[data-testid="draggable-taskworker"]', offset_x=200
    )

    # Wait for TaskWorker node to appear on canvas
    expect(page.locator('[data-testid="taskworker-node"]')).to_be_visible(
        timeout=helper.timeout
    )
    print("TaskWorker node successfully added to canvas.")

    # Verify we now have 2 nodes on the canvas
    helper.wait_for_nodes(2)

    # 7. Click on the task node to open the side pane
    helper.click_node('[data-testid="task-node"]')

    # Wait for side pane to open and verify Task Definitions tab is active
    expect(page.locator('[data-testid="tasks-tab"]')).to_be_visible(
        timeout=helper.timeout
    )
    expect(
        page.locator('[data-testid="tasks-tab"][data-state="active"]')
    ).to_be_visible(timeout=helper.timeout)
    print("Side pane opened with Task Definitions tab active.")

    # 8. Create a new task in the list pane
    print("Creating new task...")
    # Look for the plus button to add a new task within the tasks tab content
    tasks_tab_content = page.locator('[data-testid="tasks-tab-content"]')
    add_task_button = tasks_tab_content.locator(
        '[data-testid="create-new-item-button"]'
    )
    expect(add_task_button).to_be_visible(timeout=helper.timeout)
    add_task_button.click()

    # Wait for the task to be created and the edit pane to show TaskConfig
    expect(page.locator('input[type="text"]').first).to_be_visible(
        timeout=helper.timeout
    )
    print("New task created and TaskConfig opened in edit pane.")

    # 9. Verify TaskConfig is displayed with editable fields
    print("Verifying TaskConfig interface...")
    # Check for class name input field
    class_name_input = page.locator('[data-testid="task-name-value"]')
    expect(class_name_input).to_be_visible(timeout=helper.timeout)

    # Get the current task name
    current_task_name = class_name_input.text_content()
    print(f"Current task name: '{current_task_name}'")

    # If the task name is empty or default, set a proper name
    if not current_task_name or current_task_name.strip() in ["", "Task", "Unknown"]:
        print("Setting explicit task name...")
        # Click on the task name to edit it
        class_name_input.click()
        # Clear and set a new name
        class_name_input.fill("MyTestTask")
        # Press Enter to save
        class_name_input.press("Enter")
        page.wait_for_timeout(500)  # Wait for save
        current_task_name = "MyTestTask"
        print(f"Set task name to: '{current_task_name}'")

    # Ensure we have a valid task name
    assert (
        current_task_name and current_task_name.strip()
    ), f"Task name is empty or invalid: '{current_task_name}'"

    # Verify we can see field editing interface
    expect(page.locator("text=No fields")).to_be_visible(timeout=helper.timeout)

    # Add a simple field to make the task more realistic
    add_field_button = page.locator('button[title="Add field"]')
    expect(add_field_button).to_be_visible(timeout=helper.timeout)
    add_field_button.click()

    # Fill in field details
    field_name_input = page.locator('input[placeholder="field_name"]')
    expect(field_name_input).to_be_visible(timeout=helper.timeout)
    field_name_input.fill("message")

    # Save the field
    save_field_button = page.locator('button:has-text("Add")')
    expect(save_field_button).to_be_visible(timeout=helper.timeout)
    save_field_button.click()

    print("Field added to task successfully.")

    print("Clicking outside the edit area...")
    canvas = page.locator(".svelte-flow")
    canvas.click()
    page.wait_for_timeout(500)

    # 10. Click on the TaskWorker node to configure it
    helper.click_node('[data-testid="taskworker-node"]')

    # Wait for TaskWorker configuration to appear
    expect(page.locator('[data-testid="output-types-section"]')).to_be_visible(
        timeout=helper.timeout
    )
    print("TaskWorker configuration opened.")

    # 11. Verify the new task appears as a selectable output type
    print("Verifying new task appears in output type options...")

    # Look for the Output Types section within the TaskWorker node
    output_types_section = page.locator('[data-testid="output-types-section"]')
    expect(output_types_section).to_be_visible(timeout=helper.timeout)

    # Find the dropdown with "Add output type..." option within the output types section
    output_type_dropdown = output_types_section.locator(
        '[data-testid="output-type-dropdown"]'
    )
    expect(output_type_dropdown).to_be_visible(timeout=helper.timeout)

    # Click the dropdown to open it
    output_type_dropdown.click()

    # Debug: Check what tasks are available in the browser
    print("Debugging: Checking available tasks in browser...")
    available_tasks = page.evaluate(
        """
        () => {
            // Check if taskClassNamesStore is available
            if (window.taskClassNamesStore) {
                return Array.from(window.taskClassNamesStore);
            }
            // Fallback: check localStorage for tasks
            const nodes = JSON.parse(localStorage.getItem('nodes') || '[]');
            const taskNodes = nodes.filter(node => node.type === 'task');
            return taskNodes.map(node => node.data?.className || 'Unknown');
        }
    """
    )
    print(f"Available tasks in browser: {available_tasks}")

    # Verify our new task appears as an option in the dropdown
    # Note: We don't check visibility of options since they're hidden when dropdown is closed
    # Instead, we'll verify by attempting to select the option
    print(f"Looking for task '{current_task_name}' in output type dropdown...")

    # Select the task as an output type
    try:
        # First verify the option exists
        target_option = output_type_dropdown.locator(
            f'option:has-text("{current_task_name}")'
        )
        expect(target_option).to_be_attached(timeout=helper.timeout)

        # Use a more reliable method to trigger the selection and change event
        # Instead of select_option(), we'll use evaluate to trigger the change event properly
        result = page.evaluate(
            """
            (taskName) => {
                const dropdown = document.querySelector('[data-testid="output-type-dropdown"]');
                if (!dropdown) {
                    return { error: 'Dropdown not found' };
                }
                
                // Check if the option exists
                const option = dropdown.querySelector(`option[value="${taskName}"]`);
                if (!option) {
                    const allOptions = Array.from(dropdown.options).map(opt => opt.value);
                    return { error: 'Option not found', availableOptions: allOptions };
                }
                
                dropdown.value = taskName;
                
                // Trigger change event manually to ensure event handlers fire
                const event = new Event('change', { bubbles: true });
                dropdown.dispatchEvent(event);
                
                return { success: true, selectedValue: dropdown.value };
            }
        """,
            current_task_name,
        )

        print(f"Dropdown selection result: {result}")

        if result.get("error"):
            raise ValueError(
                f"Dropdown selection failed: {result['error']}. Available options: {result.get('availableOptions', 'unknown')}"
            )

        print(
            f"✓ Selected '{current_task_name}' as output type using manual event dispatch."
        )

        # Wait a moment for the UI to update
        page.wait_for_timeout(1000)

    except ValueError as e:
        # If selection fails, it means the option doesn't exist
        print(
            f"Failed to select '{current_task_name}' - option may not exist in dropdown"
        )
        # Get all available options for debugging
        all_options = output_type_dropdown.locator("option").all()
        option_values = [opt.get_attribute("value") for opt in all_options]
        print(f"Available options: {option_values}")
        raise AssertionError(
            f"Task '{current_task_name}' not found in dropdown options: {option_values}"
        ) from e

    # Verify the task now appears in the output types list
    print(f"Verifying that '{current_task_name}' appears in the output types list...")

    # Look for the task name within the output types section
    output_type_item = output_types_section.locator(
        f'span.font-mono:has-text("{current_task_name}")'
    )

    # Add some debugging if the element is not found
    try:
        expect(output_type_item).to_be_visible(timeout=helper.timeout)
        print(f"✓ Task '{current_task_name}' now appears in the output types list.")
    except Exception as e:
        print(f"Failed to find task '{current_task_name}' in output types list")
        # Debug: Check if "No output types defined" message is still showing
        no_output_msg = output_types_section.locator("text=No output types defined")
        if no_output_msg.is_visible():
            print(
                "'No output types defined' message is still visible - selection may have failed"
            )

        # Debug: Look for any span.font-mono elements in the output types section
        all_output_spans = output_types_section.locator("span.font-mono").all()
        if all_output_spans:
            span_texts = [span.text_content() for span in all_output_spans]
            print(f"Found output type spans: {span_texts}")
        else:
            print("No span.font-mono elements found in output types section")

        raise AssertionError(
            f"Task '{current_task_name}' not found in output types list"
        ) from e

    print("Test completed successfully!")
    print("✓ Task node dragged onto canvas")
    print("✓ TaskWorker node dragged onto canvas")
    print("✓ Task node click opened side pane with Task Definitions tab")
    print("✓ New task created via list pane")
    print("✓ TaskConfig displayed in edit pane")
    print("✓ Field added to new task")
    print("✓ New task available as output type for TaskWorker")
    print("✓ New task successfully selected as output type")
    print("✓ New task appears in TaskWorker's output types list")
