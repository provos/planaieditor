import os

import pytest
from playwright.sync_api import APIResponse, Page, Route, expect

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)

# --- Configuration ---
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
# Use a different port for the test backend server to avoid conflicts
BACKEND_TEST_PORT = os.environ.get("BACKEND_TEST_PORT", "5001")
BACKEND_TEST_URL = f"http://localhost:{BACKEND_TEST_PORT}"
# Timeout for waiting for elements or status changes (in milliseconds)
TIMEOUT = 15000


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

    # Set up route handler for debugging
    def handle_route(route: Route):
        if "/api/" in route.request.url:
            print(f"Intercepted request: {route.request.method} {route.request.url}")
        route.continue_()

    page.route("**/*", handle_route)

    # 1. Navigate to the frontend
    print(f"Navigating to frontend: {FRONTEND_URL}")
    page.goto(FRONTEND_URL)
    expect(page.locator('[data-testid="toolshelf-container"]')).to_be_visible(
        timeout=TIMEOUT
    )
    print("Frontend loaded.")

    # 2. Clear any existing graph
    clear_button = page.locator('button[title="Clear Graph"]')
    if page.locator(".svelte-flow__node").first.is_visible(timeout=2000):
        print("Clearing existing graph...")
        clear_button.click(force=True)
        page.once("dialog", lambda dialog: dialog.accept())
        expect(page.locator(".svelte-flow__node")).to_have_count(0, timeout=TIMEOUT)
        print("Graph cleared.")
    else:
        print("No existing graph detected, skipping clear.")

    # 3. Set up virtual environment (required for UI interactions to work)
    print("Setting up virtual environment...")
    interpreter_button = page.locator('button[data-testid="interpreter-button"]')
    expect(interpreter_button).to_be_visible(timeout=TIMEOUT)
    expect(interpreter_button).to_be_enabled(timeout=TIMEOUT)

    with page.expect_response(
        lambda response: "/api/set-venv" in response.url
        and response.request.method == "POST",
        timeout=TIMEOUT,
    ) as response_info:
        interpreter_button.click()

    api_response: APIResponse = response_info.value
    print(f"Virtual environment setup response: {api_response.status}")
    assert (
        api_response.ok
    ), f"Virtual environment setup failed with status {api_response.status}"

    # 4. Switch to Configuration tab in ToolShelf to access task and worker nodes
    print("Switching to Configuration tab...")
    config_tab = page.locator('[data-testid="config-tab"]')
    expect(config_tab).to_be_visible(timeout=TIMEOUT)
    config_tab.click()

    # Wait for the tab content to be visible
    expect(
        page.locator('[data-testid="config-tab"][data-state="active"]')
    ).to_be_visible(timeout=TIMEOUT)

    # 5. Drag a task node onto the canvas
    print("Dragging task node onto canvas...")
    task_node_draggable = page.locator('[data-testid="draggable-task"]')
    expect(task_node_draggable).to_be_visible(timeout=TIMEOUT)

    # Get the canvas area for dropping
    canvas = page.locator(".svelte-flow")
    expect(canvas).to_be_visible(timeout=TIMEOUT)

    # Get bounding boxes for drag and drop
    task_box = task_node_draggable.bounding_box()
    canvas_box = canvas.bounding_box()

    assert task_box is not None, "Task node bounding box not found"
    assert canvas_box is not None, "Canvas bounding box not found"

    # Calculate drop position (center of canvas)
    drop_x = canvas_box["x"] + canvas_box["width"] / 2
    drop_y = canvas_box["y"] + canvas_box["height"] / 2

    # Perform drag and drop
    page.mouse.move(
        task_box["x"] + task_box["width"] / 2, task_box["y"] + task_box["height"] / 2
    )
    page.mouse.down()
    page.mouse.move(drop_x, drop_y)
    page.mouse.up()

    # Wait for task node to appear on canvas
    expect(page.locator('[data-testid="task-node"]')).to_be_visible(timeout=TIMEOUT)
    print("Task node successfully added to canvas.")

    # 6. Switch to Workers tab and drag a TaskWorker onto the canvas
    print("Switching to Workers tab...")
    workers_tab = page.locator('[data-testid="workers-tab"]')
    expect(workers_tab).to_be_visible(timeout=TIMEOUT)
    workers_tab.click()

    # Wait for workers tab content
    expect(
        page.locator('[data-testid="workers-tab"][data-state="active"]')
    ).to_be_visible(timeout=TIMEOUT)

    print("Dragging TaskWorker node onto canvas...")
    taskworker_draggable = page.locator('[data-testid="draggable-taskworker"]')
    expect(taskworker_draggable).to_be_visible(timeout=TIMEOUT)

    # Get bounding box for TaskWorker
    taskworker_box = taskworker_draggable.bounding_box()
    assert taskworker_box is not None, "TaskWorker bounding box not found"

    # Calculate different drop position for TaskWorker (offset from task node)
    drop_x_worker = drop_x + 200  # Offset to the right
    drop_y_worker = drop_y

    # Perform drag and drop for TaskWorker
    page.mouse.move(
        taskworker_box["x"] + taskworker_box["width"] / 2,
        taskworker_box["y"] + taskworker_box["height"] / 2,
    )
    page.mouse.down()
    page.mouse.move(drop_x_worker, drop_y_worker)
    page.mouse.up()

    # Wait for TaskWorker node to appear on canvas
    expect(page.locator('[data-testid="taskworker-node"]')).to_be_visible(
        timeout=TIMEOUT
    )
    print("TaskWorker node successfully added to canvas.")

    # Verify we now have 2 nodes on the canvas
    expect(page.locator(".svelte-flow__node")).to_have_count(2, timeout=TIMEOUT)

    # 7. Click on the task node to open the side pane
    print("Clicking on task node to open side pane...")
    task_node_on_canvas = page.locator('[data-testid="task-node"]')
    expect(task_node_on_canvas).to_be_visible(timeout=TIMEOUT)
    task_node_on_canvas.click()

    # Wait for side pane to open and verify Task Definitions tab is active
    expect(page.locator('[data-testid="tasks-tab"]')).to_be_visible(timeout=TIMEOUT)
    expect(
        page.locator('[data-testid="tasks-tab"][data-state="active"]')
    ).to_be_visible(timeout=TIMEOUT)
    print("Side pane opened with Task Definitions tab active.")

    # 8. Create a new task in the list pane
    print("Creating new task...")
    # Look for the plus button to add a new task within the tasks tab content
    tasks_tab_content = page.locator('[data-testid="tasks-tab-content"]')
    add_task_button = tasks_tab_content.locator(
        '[data-testid="create-new-item-button"]'
    )
    expect(add_task_button).to_be_visible(timeout=TIMEOUT)
    add_task_button.click()

    # Wait for the task to be created and the edit pane to show TaskConfig
    expect(page.locator('input[type="text"]').first).to_be_visible(timeout=TIMEOUT)
    print("New task created and TaskConfig opened in edit pane.")

    # 9. Verify TaskConfig is displayed with editable fields
    print("Verifying TaskConfig interface...")
    # Check for class name input field
    class_name_input = page.locator('[data-testid="task-name-value"]')
    expect(class_name_input).to_be_visible(timeout=TIMEOUT)

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
    expect(page.locator("text=No fields")).to_be_visible(timeout=TIMEOUT)

    # Add a simple field to make the task more realistic
    add_field_button = page.locator('button[title="Add field"]')
    expect(add_field_button).to_be_visible(timeout=TIMEOUT)
    add_field_button.click()

    # Fill in field details
    field_name_input = page.locator('input[placeholder="field_name"]')
    expect(field_name_input).to_be_visible(timeout=TIMEOUT)
    field_name_input.fill("message")

    # Save the field
    save_field_button = page.locator('button:has-text("Add")')
    expect(save_field_button).to_be_visible(timeout=TIMEOUT)
    save_field_button.click()

    print("Field added to task successfully.")

    print("Clicking outside the edit area...")
    canvas = page.locator(".svelte-flow")
    canvas.click()
    page.wait_for_timeout(500)

    # 10. Click on the TaskWorker node to configure it
    print("Clicking on TaskWorker node...")
    taskworker_node_on_canvas = page.locator('[data-testid="taskworker-node"]')
    expect(taskworker_node_on_canvas).to_be_visible(timeout=TIMEOUT)
    taskworker_node_on_canvas.click()

    # Wait for TaskWorker configuration to appear
    expect(page.locator('[data-testid="output-types-section"]')).to_be_visible(
        timeout=TIMEOUT
    )
    print("TaskWorker configuration opened.")

    # 11. Verify the new task appears as a selectable output type
    print("Verifying new task appears in output type options...")

    # Look for the Output Types section within the TaskWorker node
    output_types_section = page.locator('[data-testid="output-types-section"]')
    expect(output_types_section).to_be_visible(timeout=TIMEOUT)

    # Find the dropdown with "Add output type..." option within the output types section
    output_type_dropdown = output_types_section.locator(
        '[data-testid="output-type-dropdown"]'
    )
    expect(output_type_dropdown).to_be_visible(timeout=TIMEOUT)

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
        expect(target_option).to_be_attached(timeout=TIMEOUT)

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
            raise Exception(
                f"Dropdown selection failed: {result['error']}. Available options: {result.get('availableOptions', 'unknown')}"
            )

        print(
            f"✓ Selected '{current_task_name}' as output type using manual event dispatch."
        )

        # Wait a moment for the UI to update
        page.wait_for_timeout(1000)

    except Exception as e:
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
        expect(output_type_item).to_be_visible(timeout=TIMEOUT)
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
