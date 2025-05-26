# E2E Test Utilities for PlanAI Editor

This directory contains utilities and patterns for writing End-to-End (E2E) tests for the PlanAI Editor using Playwright.

## Prerequisites

Before running E2E tests, you need to have both the frontend and backend running:

### Frontend
```bash
cd frontend
npm run dev
```

### Backend
```bash
cd backend
FLASK_ENV=development poetry run python -m planaieditor.app
```

The tests expect the frontend to be available at `http://localhost:5173` and the backend at `http://localhost:5001`.

## Overview

We provide utility functions for common patterns to make it easier to write end-to-end UI tests.

## Modules

### `utils.py` - Core E2E Test Utilities

The main utilities module provides:

#### `E2ETestHelper` Class
A helper class that encapsulates common E2E test operations:

- **Page Setup**: Navigation, graph clearing, virtual environment setup
- **UI Interactions**: Tab switching, drag and drop, node clicking
- **API Operations**: File import, graph export, data extraction
- **Waiting Utilities**: Wait for nodes, elements, API responses

#### Key Methods:
- `navigate_to_frontend()` - Navigate to the frontend URL
- `clear_graph()` - Clear the current graph
- `setup_virtual_environment()` - Set up Python virtual environment
- `switch_to_tab(tab_name)` - Switch between UI tabs
- `drag_element_to_canvas(selector, offset_x=0, offset_y=0)` - Drag elements to canvas
- `click_node(selector)` - Click on graph nodes
- `wait_for_nodes(count, timeout_multiplier=1)` - Wait for specific node count
- `import_python_file(file_path)` - Import Python files via API
- `export_graph_to_python(graph_data)` - Export graph to Python code
- `get_graph_data_from_browser()` - Extract graph data from browser

#### Standalone Utility Functions
- `setup_basic_test_environment(page)` - One-line setup for most tests

### `comparison_utils.py` - PlanAI Definition Comparison

Specialized utilities for comparing PlanAI definitions:

- `compare_definitions()` - Compare parsed PlanAI definitions
- `verify_functional_equivalence()` - End-to-end equivalence verification
- `get_expected_node_count_from_definitions()` - Calculate expected UI nodes

## Usage Examples

### Basic Test Setup

```python
from playwright.sync_api import Page
from utils import setup_basic_test_environment

def test_my_feature(page: Page):
    # One-line setup: navigate, clear graph, setup venv
    helper = setup_basic_test_environment(page)
    
    # Your test logic here
    helper.switch_to_tab("config")
    helper.drag_element_to_canvas('[data-testid="draggable-task"]')
    helper.wait_for_nodes(1)
```

### Simple Worker Test Pattern

```python
def test_simple_worker_workflow(page: Page):
    helper = setup_basic_test_environment(page)
    
    # Switch to config tab and create nodes
    helper.switch_to_tab("config")
    helper.drag_element_to_canvas('[data-testid="draggable-task"]')
    
    helper.switch_to_tab("workers")
    helper.drag_element_to_canvas('[data-testid="draggable-taskworker"]', offset_x=200)
    
    helper.wait_for_nodes(2)
    
    # Configure nodes
    helper.click_node('[data-testid="task-node"]')
    # ... continue with test logic
```

### Import/Export Testing

```python
from pathlib import Path
from comparison_utils import verify_functional_equivalence, get_expected_node_count_from_definitions

def test_import_export(page: Page):
    helper = setup_basic_test_environment(page)
    
    # Import a Python file
    fixture_path = Path("fixtures/my_fixture.py")
    helper.import_python_file(fixture_path)
    
    # Wait for expected nodes
    expected_count = get_expected_node_count_from_definitions(original_defs)
    helper.wait_for_nodes(expected_count, timeout_multiplier=2)
    
    # Export and verify equivalence
    graph_data = helper.get_graph_data_from_browser()
    exported_code = helper.export_graph_to_python(graph_data)
    
    original_code = fixture_path.read_text()
    assert verify_functional_equivalence(original_code, exported_code)
```

## Configuration

The utilities use these environment variables:

- `FRONTEND_URL` - Frontend URL (default: http://localhost:5173)
- `BACKEND_TEST_PORT` - Backend test port (default: 5001)
- `SKIP_E2E_TESTS` - Skip E2E tests if set to "true"

## Current Tests

### `test_simple_worker.py` (291 lines, down from 398)
Tests the complete workflow of:
1. Dragging task and worker nodes onto canvas
2. Creating new tasks in the side pane
3. Configuring output types for workers

**Key improvements:**
- Uses `setup_basic_test_environment()` for setup
- Uses helper methods for all UI interactions
- Reduced from 398 to 291 lines (27% reduction)

### `test_import_export.py` (94 lines, down from 628)
Tests import/export roundtrip functionality for PlanAI fixtures:
1. Imports Python files containing PlanAI graphs
2. Verifies correct node rendering
3. Exports back to Python and verifies functional equivalence

**Key improvements:**
- Uses `setup_basic_test_environment()` for setup
- Uses comparison utilities for verification
- Reduced from 628 to 94 lines (85% reduction)

## Writing New Tests

1. **Start with `setup_basic_test_environment()`** for most tests
2. **Use the `E2ETestHelper` methods** for UI interactions
3. **Import comparison utilities** for import/export tests
4. **Follow the existing patterns** in the current test files

### Example New Test Structure

```python
import os
import pytest
from playwright.sync_api import Page
from utils import setup_basic_test_environment

# Skip e2e tests if SKIP_E2E_TESTS is set
if os.environ.get("SKIP_E2E_TESTS") == "true":
    pytest.skip("Skipping e2e tests as SKIP_E2E_TESTS is set", allow_module_level=True)

def test_my_new_feature(page: Page):
    """Test description"""
    helper = setup_basic_test_environment(page)
    
    # Your test logic using helper methods
    helper.switch_to_tab("config")
    # ... rest of test
```


### Debug Utilities

The helper class provides debugging methods:
- `save_debug_data()` - Save test state for analysis
- `get_available_tasks_from_browser()` - Check task availability
- Console logging throughout helper methods for troubleshooting
