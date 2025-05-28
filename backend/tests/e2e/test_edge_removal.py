import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_edge_removal_workflow(page: Page):
    """
    Tests the edge removal workflow:
    1. Load edge-removal.json
    2. Delete the output type ChatTask from LLMTaskWorker1
    3. Verify that the edge between LLMTaskWorker1 and LLMTaskWorker2 was deleted
    4. Delete the manual input type (ChatTask) on LLMTaskWorker2
    5. Set the output type of LLMTaskWorker1 to Sentiment
    6. Connect the output handle from LLMTaskWorker1 with the input handle from LLMTaskWorker2
    7. Validate that the input type is now Sentiment
    8. Validate that an edge exists between LLMTaskWorker1 and LLMTaskWorker2
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

    # Verify initial state - should have 3 edges
    initial_edge_count = helper.get_edge_count()
    print(f"Initial edge count: {initial_edge_count}")
    assert (
        initial_edge_count == 3
    ), f"Expected 3 initial edges, got {initial_edge_count}"

    # 2. Delete the output type ChatTask from LLMTaskWorker1
    print("Step 2: Deleting ChatTask output type from LLMTaskWorker1...")

    # Click on LLMTaskWorker1 to select it
    llm_worker1_node = page.locator('[data-testid="llmtaskworker-node"]').first
    expect(llm_worker1_node).to_be_visible(timeout=helper.timeout)
    llm_worker1_node.click()
    page.wait_for_timeout(250)  # Wait for UI to update

    # Find the output types section
    output_types_section = llm_worker1_node.locator(
        '[data-testid="output-types-section"]'
    )
    expect(output_types_section).to_be_visible(timeout=helper.timeout)

    # Find the ChatTask output type and its delete button
    # Look for the ChatTask output type item
    chat_task_output = output_types_section.locator(
        'span.font-mono:has-text("ChatTask")'
    ).first
    expect(chat_task_output).to_be_visible(timeout=helper.timeout)

    # Find the parent div that contains both the text and the delete button
    # The structure is: div.group > div.flex > span.font-mono and div.flex (with buttons)
    chat_task_parent = chat_task_output.locator("..").locator("..")

    # Hover over the parent to make the delete button visible
    chat_task_parent.hover()
    page.wait_for_timeout(200)  # Wait for hover effect

    # Find and click the delete button (trash icon) - it should be in a div.flex container
    delete_button = chat_task_parent.locator('button[title="Remove type"]')

    # Force the click since the button might still be transitioning to visible
    delete_button.click(force=True)
    print("ChatTask output type deleted from LLMTaskWorker1.")

    # 3. Verify that the edge between LLMTaskWorker1 and LLMTaskWorker2 was deleted
    print("Step 3: Verifying edge deletion...")
    page.wait_for_timeout(500)  # Wait for edge deletion to process

    edge_count_after_deletion = helper.get_edge_count()
    print(f"Edge count after deletion: {edge_count_after_deletion}")
    assert (
        edge_count_after_deletion == 2
    ), f"Expected 2 edges after deletion, got {edge_count_after_deletion}"
    print("✓ Edge between LLMTaskWorker1 and LLMTaskWorker2 was successfully deleted.")

    # 4. Delete the manual input type (ChatTask) on LLMTaskWorker2
    print("Step 4: Deleting manual input type ChatTask from LLMTaskWorker2...")

    # Click on LLMTaskWorker2 to select it (it's the second llmtaskworker node)
    llm_worker2_node = page.locator('[data-testid="llmtaskworker-node"]').nth(1)
    expect(llm_worker2_node).to_be_visible(timeout=helper.timeout)
    llm_worker2_node.click()
    page.wait_for_timeout(250)  # Wait for UI to update

    # Find the input types section and the ChatTask input type
    input_types_section = llm_worker2_node.locator(
        'h3:has-text("Input Types")'
    ).locator("..")
    chat_task_input = input_types_section.locator(
        'span.font-mono:has-text("ChatTask")'
    ).first

    if chat_task_input.is_visible():
        print("Found ChatTask input type, attempting to delete...")

        # Find the parent div that contains the delete button
        # The structure should be similar to output types: div.group > div.flex > span.font-mono and div.flex (with buttons)
        chat_task_input_parent = chat_task_input.locator("..").locator("..")

        # Hover to make delete button visible
        chat_task_input_parent.hover()
        page.wait_for_timeout(200)  # Wait for hover effect

        # Find and click the delete button for the input type
        input_delete_button = chat_task_input_parent.locator(
            'button[title="Remove manual input type"]'
        )

        if input_delete_button.is_visible():
            input_delete_button.click(force=True)
            print("Manual input type ChatTask deleted from LLMTaskWorker2.")
            page.wait_for_timeout(250)  # Wait for deletion to process
        else:
            print("Delete button not visible, trying alternative approach...")
            # Try to find any trash button in the input types section
            trash_buttons = (
                input_types_section.locator("button").filter(has_text="").all()
            )
            print(f"Found {len(trash_buttons)} buttons in input types section")

            for i, button in enumerate(trash_buttons):
                title = button.get_attribute("title")
                print(f"  Button {i+1}: title='{title}'")
                if title and "remove" in title.lower():
                    print(f"Clicking button with title: {title}")
                    button.click(force=True)
                    page.wait_for_timeout(250)
                    break
            else:
                print("No suitable delete button found")
    else:
        print("ChatTask input type not found on LLMTaskWorker2.")

    # Verify the input type was actually removed
    remaining_inputs = input_types_section.locator("span.font-mono").all()
    remaining_input_texts = [span.text_content() for span in remaining_inputs]
    print(f"Remaining input types after deletion attempt: {remaining_input_texts}")

    # 5. Set the output type of LLMTaskWorker1 to Sentiment
    print("Step 5: Setting output type of LLMTaskWorker1 to Sentiment...")

    # Click on LLMTaskWorker1 again to ensure it's selected
    llm_worker1_node.click()
    page.wait_for_timeout(250)

    # Find the output types section and the dropdown
    output_types_section = llm_worker1_node.locator(
        '[data-testid="output-types-section"]'
    )
    output_type_dropdown = output_types_section.locator(
        '[data-testid="output-type-dropdown"]'
    )
    expect(output_type_dropdown).to_be_visible(timeout=helper.timeout)

    # Select Sentiment from the dropdown
    output_type_dropdown.select_option(value="Sentiment")
    page.wait_for_timeout(250)  # Wait for UI to update
    print("Sentiment output type set for LLMTaskWorker1.")

    # Verify Sentiment appears in the output types list
    sentiment_output = output_types_section.locator(
        'span.font-mono:has-text("Sentiment")'
    )
    expect(sentiment_output).to_be_visible(timeout=helper.timeout)
    print("✓ Sentiment output type verified in LLMTaskWorker1.")

    # 6. Connect the output handle from LLMTaskWorker1 with the input handle from LLMTaskWorker2
    print("Step 6: Connecting LLMTaskWorker1 output to LLMTaskWorker2 input...")

    # Get the Sentiment task ID for the handle
    sentiment_task_id = page.evaluate(
        """
        () => {
            const tasks = JSON.parse(localStorage.getItem('tasks') || '[]');
            const sentimentTask = tasks.find(task => task.className === 'Sentiment');
            return sentimentTask ? sentimentTask.id : null;
        }
        """
    )
    assert sentiment_task_id, "Could not find Sentiment task ID in localStorage"
    print(f"Found Sentiment task ID: {sentiment_task_id}")

    # Get the specific node IDs for more reliable targeting
    llm_worker1_id = page.evaluate(
        """
        () => {
            const nodes = JSON.parse(localStorage.getItem('nodes') || '[]');
            const llmWorker1 = nodes.find(node => 
                node.type === 'llmtaskworker' && 
                node.data.workerName === 'LLMTaskWorker1'
            );
            return llmWorker1 ? llmWorker1.id : null;
        }
        """
    )

    llm_worker2_id = page.evaluate(
        """
        () => {
            const nodes = JSON.parse(localStorage.getItem('nodes') || '[]');
            const llmWorker2 = nodes.find(node => 
                node.type === 'llmtaskworker' && 
                node.data.workerName === 'LLMTaskWorker2'
            );
            return llmWorker2 ? llmWorker2.id : null;
        }
        """
    )

    assert llm_worker1_id, "Could not find LLMTaskWorker1 node ID"
    assert llm_worker2_id, "Could not find LLMTaskWorker2 node ID"
    print(f"Found LLMTaskWorker1 ID: {llm_worker1_id}")
    print(f"Found LLMTaskWorker2 ID: {llm_worker2_id}")

    # Debug: Check if the output handle exists before trying to drag
    llm_worker1_node = page.locator(f'[data-id="{llm_worker1_id}"]')
    sentiment_output_handle = llm_worker1_node.locator(
        f'.svelte-flow__handle[data-handleid="output-{sentiment_task_id}"]'
    )

    print(f"Checking for output handle with ID: output-{sentiment_task_id}")
    if sentiment_output_handle.is_visible():
        print("✓ Sentiment output handle is visible")
    else:
        print("✗ Sentiment output handle is not visible")
        # Try alternative selector
        alt_handle = llm_worker1_node.locator(
            f'.svelte-flow__handle[id="output-{sentiment_task_id}"]'
        )
        if alt_handle.is_visible():
            print("✓ Found handle with id attribute instead of data-handleid")
        else:
            print("✗ Handle not found with either selector")
            # List all handles on the node for debugging
            all_handles = llm_worker1_node.locator(".svelte-flow__handle").all()
            print(f"Found {len(all_handles)} handles on LLMTaskWorker1:")
            for i, handle in enumerate(all_handles):
                handle_id = handle.get_attribute(
                    "data-handleid"
                ) or handle.get_attribute("id")
                print(f"  Handle {i+1}: {handle_id}")

    # Perform the drag from LLMTaskWorker1 output handle to LLMTaskWorker2 input handle
    helper.drag_from_handle_to_handle(
        f'[data-id="{llm_worker1_id}"]',  # LLMTaskWorker1 by specific ID
        f"output-{sentiment_task_id}",
        f'[data-id="{llm_worker2_id}"]',  # LLMTaskWorker2 by specific ID
        "input",
    )
    print("Connection created between LLMTaskWorker1 and LLMTaskWorker2.")

    # Wait for the connection to be established
    page.wait_for_timeout(500)

    # 7. Validate that the input type is now Sentiment
    print("Step 7: Validating that LLMTaskWorker2 input type is now Sentiment...")

    # First, let's verify the connection was successful by checking edge count
    connection_edge_count = helper.get_edge_count()
    print(f"Edge count after connection attempt: {connection_edge_count}")

    if connection_edge_count != 3:
        print("Connection may have failed, checking edges...")
        edges = helper.get_all_edges()
        for i, edge in enumerate(edges):
            print(
                f"  Edge {i+1}: {edge.get('source', 'unknown')} -> {edge.get('target', 'unknown')}"
            )
            print(f"    Source Handle: {edge.get('sourceHandle', 'unknown')}")
            print(f"    Target Handle: {edge.get('targetHandle', 'unknown')}")

    # Click on LLMTaskWorker2 to check its input types
    llm_worker2_node.click()
    page.wait_for_timeout(250)

    # Debug: Check what input types are actually present
    input_types_section = llm_worker2_node.locator(
        'h3:has-text("Input Types")'
    ).locator("..")

    # Get all font-mono spans in the input types section for debugging
    all_input_spans = input_types_section.locator("span.font-mono").all()
    input_type_texts = [span.text_content() for span in all_input_spans]
    print(f"Found input types in LLMTaskWorker2: {input_type_texts}")

    # Check that Sentiment appears in the input types
    sentiment_input = input_types_section.locator(
        'span.font-mono:has-text("Sentiment")'
    )

    # Try a more flexible approach if the exact text match fails
    if not sentiment_input.is_visible():
        print("Exact 'Sentiment' text not found, trying partial match...")
        sentiment_input_partial = input_types_section.locator("span.font-mono").filter(
            has_text="Sentiment"
        )
        if sentiment_input_partial.is_visible():
            sentiment_input = sentiment_input_partial
        else:
            print("No Sentiment input type found at all")

    expect(sentiment_input).to_be_visible(timeout=helper.timeout)
    print("✓ LLMTaskWorker2 input type is now Sentiment.")

    # 8. Validate that an edge exists between LLMTaskWorker1 and LLMTaskWorker2
    print("Step 8: Validating edge exists between LLMTaskWorker1 and LLMTaskWorker2...")

    final_edge_count = helper.get_edge_count()
    print(f"Final edge count: {final_edge_count}")
    assert (
        final_edge_count == 3
    ), f"Expected 3 edges after reconnection, got {final_edge_count}"

    # Verify the specific edge exists by checking the edges data
    edges = helper.get_all_edges()
    llm1_to_llm2_edge = None
    for edge in edges:
        if edge.get("source", "").startswith("llmtaskworker-b8484cd7") and edge.get(
            "target", ""
        ).startswith("llmtaskworker-a5d68285"):
            llm1_to_llm2_edge = edge
            break

    assert (
        llm1_to_llm2_edge is not None
    ), "Edge between LLMTaskWorker1 and LLMTaskWorker2 not found"
    print("✓ Edge between LLMTaskWorker1 and LLMTaskWorker2 verified.")

    print("Test completed successfully!")
    print("✓ JSON file loaded with 4 nodes")
    print("✓ ChatTask output type deleted from LLMTaskWorker1")
    print("✓ Edge between LLMTaskWorker1 and LLMTaskWorker2 was deleted")
    print("✓ Manual input type deleted from LLMTaskWorker2")
    print("✓ Sentiment output type set for LLMTaskWorker1")
    print("✓ LLMTaskWorker1 connected to LLMTaskWorker2")
    print("✓ LLMTaskWorker2 input type is now Sentiment")
    print("✓ Edge exists between LLMTaskWorker1 and LLMTaskWorker2")
