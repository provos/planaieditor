import os
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)


def test_llm_taskworker_configuration_and_export(page: Page):
    """
    Tests the complete workflow of:
    1. Loading a JSON file with an LLMTaskWorker node
    2. Setting Input Type to "LLMInput"
    3. Setting Output Type to "FinalOutput"
    4. Setting LLM Output Type to "LLMOutput"
    5. Exporting to Python and validating the generated code
    """

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # Load the simple-llmtaskworker.json file
    json_file_path = Path(__file__).parent.parent / "data" / "simple-llmtaskworker.json"
    assert json_file_path.exists(), f"Test data file not found: {json_file_path}"

    helper.load_json_file(json_file_path)

    # Wait for the nodes to be loaded (should be 1 LLMTaskWorker node)
    helper.wait_for_nodes(1)
    print("LLMTaskWorker node loaded successfully.")

    # Find the LLMTaskWorker node by its ID from the JSON
    llm_taskworker_selector = (
        '[data-id="llmtaskworker-680898fb-3b6a-4384-a3eb-1c9c842b38f6"]'
    )

    # Verify the node is present
    llm_taskworker_node = page.locator(llm_taskworker_selector)
    expect(llm_taskworker_node).to_be_visible(timeout=helper.timeout)
    print("Verified LLMTaskWorker node is present.")

    # Click on the LLMTaskWorker node to select it
    helper.click_node(llm_taskworker_selector)
    page.wait_for_timeout(500)  # Wait for UI to update

    # Step 1: Set Input Type to "LLMInput"
    print("Setting Input Type to 'LLMInput'...")
    helper.set_manual_input_type(llm_taskworker_selector, "LLMInput")

    # Validate that the input type was set correctly
    input_types = helper.get_node_input_types(llm_taskworker_selector)
    print(f"Input types after setting: {input_types}")
    assert (
        "LLMInput" in input_types
    ), f"Expected 'LLMInput' in input types, but got: {input_types}"
    print("✓ Input Type successfully set to 'LLMInput'")

    # Step 2: Set Output Type to "FinalOutput"
    helper.set_output_type(llm_taskworker_selector, "FinalOutput")

    # Validate that the output type was set correctly
    output_type_set = helper.verify_output_type_set(
        llm_taskworker_selector, "FinalOutput"
    )
    assert output_type_set, "Failed to set output type to 'FinalOutput'"
    print("✓ Output Type successfully set to 'FinalOutput'")

    # Step 3: Set LLM Output Type to "LLMOutput"
    helper.set_llm_output_type(llm_taskworker_selector, "LLMOutput")
    print("✓ LLM Output Type successfully set to 'LLMOutput'")

    # Click away to deselect
    canvas = page.locator(".svelte-flow")
    canvas.click()
    page.wait_for_timeout(500)

    # Step 4: Export the graph to Python and validate the generated code
    print("Exporting graph to Python...")

    # Get the graph data from the browser
    graph_data = helper.get_graph_data_from_browser()

    # Export to Python code
    exported_code = helper.export_graph_to_python(graph_data)

    print("Exported Python code:")
    print("=" * 50)
    print(exported_code)
    print("=" * 50)

    # Step 5: Validate the exported code contains the expected fields
    print("Validating exported Python code...")

    # Check for llm_input_type = LLMInput
    assert (
        "llm_input_type: Type[Task] = LLMInput" in exported_code
        or "llm_input_type = LLMInput" in exported_code
    ), "Expected 'llm_input_type = LLMInput' in exported code"
    print("✓ llm_input_type correctly set to LLMInput")

    # Check for output_types = [FinalOutput]
    assert (
        "output_types: List[Type[Task]] = [FinalOutput]" in exported_code
        or "output_types = [FinalOutput]" in exported_code
    ), "Expected 'output_types = [FinalOutput]' in exported code"
    print("✓ output_types correctly set to [FinalOutput]")

    # Check for llm_output_type = LLMOutput
    assert (
        "llm_output_type: Type[Task] = LLMOutput" in exported_code
        or "llm_output_type = LLMOutput" in exported_code
    ), "Expected 'llm_output_type = LLMOutput' in exported code"
    print("✓ llm_output_type correctly set to LLMOutput")

    # Additional validation: Check that the class name is LLMTaskWorker1
    assert (
        "class LLMTaskWorker1(" in exported_code
    ), "Expected 'class LLMTaskWorker1(' in exported code"
    print("✓ Class name correctly set to LLMTaskWorker1")

    # Check that it inherits from LLMTaskWorker
    assert (
        "LLMTaskWorker1(LLMTaskWorker)" in exported_code
        or "LLMTaskWorker1(CachedLLMTaskWorker)" in exported_code
    ), "Expected LLMTaskWorker1 to inherit from LLMTaskWorker or CachedLLMTaskWorker"
    print("✓ LLMTaskWorker1 correctly inherits from LLMTaskWorker")

    print("Test completed successfully!")
    print("✓ JSON file loaded with LLMTaskWorker node")
    print("✓ Input Type set to 'LLMInput' and validated")
    print("✓ Output Type set to 'FinalOutput' and validated")
    print("✓ LLM Output Type set to 'LLMOutput' and validated")
    print("✓ Python export generated with correct field configurations")
    print("✓ All exported fields validated successfully")
