import json
import os
import sys
from pathlib import Path

import pytest
from comparison_utils import (
    get_expected_node_count_from_definitions,
    verify_functional_equivalence,
)
from playwright.sync_api import Page
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)

# Ensure planaieditor can be imported (adjust if your structure differs)
# This might be handled by running pytest from the 'backend' dir
sys.path.insert(0, str(Path(__file__).parent.parent))
from planaieditor.patch import get_definitions_from_python  # noqa: E402

# Path relative to the backend directory
TEST_FIXTURE_PATHS = [
    Path(__file__).parent / "fixtures/releasenotes_fixture.py",
    Path(__file__).parent / "fixtures/deepsearch_fixture.py",
]


# --- Pytest Fixtures ---


# --- Test Case ---


@pytest.mark.parametrize(
    "test_fixture_path",
    TEST_FIXTURE_PATHS,
    ids=[p.stem for p in TEST_FIXTURE_PATHS],  # Use filename stems for clearer test IDs
)
def test_import_export_roundtrip(page: Page, test_fixture_path: Path, request):
    """
    Tests the import-export roundtrip for various fixture files.
    """
    assert test_fixture_path.exists(), f"Test fixture not found at {test_fixture_path}"
    original_code = test_fixture_path.read_text()

    # Pre-parse the fixture to get expected node count
    print(f"Pre-parsing fixture {test_fixture_path.name} for node count...")
    original_defs = get_definitions_from_python(code_string=original_code)
    assert (
        original_defs is not None
    ), f"Failed to pre-parse fixture: {test_fixture_path}"

    expected_node_count = get_expected_node_count_from_definitions(original_defs)
    print(f"Expected nodes: {expected_node_count}")

    # Set up basic test environment (navigate, clear graph, setup venv)
    helper = setup_basic_test_environment(page)

    # 3. Import the fixture file
    try:
        helper.import_python_file(test_fixture_path)
    except Exception as e:
        pytest.fail(f"Failed during file import: {e}")

    # 4. Wait for graph to render after import with the expected node count
    helper.wait_for_nodes(expected_node_count, timeout_multiplier=2)

    # 5. Extract transformed data using page.evaluate
    try:
        graph_data_transformed = helper.get_graph_data_from_browser()
    except Exception as e:
        pytest.fail(f"Failed to get graph data from browser: {e}")

    # Write transformed data to file for debugging
    if request.config.getoption("--write-transformed-data"):
        with open(f"transformed_data_{test_fixture_path.stem}.json", "w") as f:
            json.dump(graph_data_transformed, f, indent=2)

    # 6. Export graph to Python code
    try:
        exported_code = helper.export_graph_to_python(graph_data_transformed)
    except Exception as e:
        pytest.fail(f"Failed to export graph to Python: {e}")

    # 7. Verify Functional Equivalence
    assert verify_functional_equivalence(
        original_code, exported_code
    ), "Functional equivalence check failed."
    print("Functional equivalence check passed.")
