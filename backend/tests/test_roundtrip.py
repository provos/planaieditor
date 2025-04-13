import os
import sys
import tempfile
import pytest
from pathlib import Path

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.patch import get_task_definitions_from_file
from app.python import generate_python_module


@pytest.fixture
def sample_planai_module():
    """Fixture that provides a sample PlanAI module with Task definitions."""
    return """
from pydantic import Field
from typing import List, Optional, Literal
from planai import Task

class SimpleTask(Task):
    name: str = Field(description="Name of the task")
    value: int = Field(description="Task value")

class ComplexTask(Task):
    text: str = Field(description="Text content")
    tags: List[str] = Field([], description="List of tags")
    priority: Optional[int] = Field(None, description="Task priority")
    status: Literal["pending", "in_progress", "completed"] = Field(..., description="Current status")
    subtasks: List[SimpleTask] = Field([], description="List of subtasks")
"""


@pytest.fixture
def temp_file():
    """Fixture to create and clean up a temporary file."""
    temp_files = []

    def _create_temp_file(content):
        temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
        temp_file.write(content)
        temp_file.close()
        temp_files.append(temp_file.name)
        return temp_file.name

    yield _create_temp_file

    # Clean up temporary files
    for file_path in temp_files:
        try:
            os.unlink(file_path)
        except:
            pass


def test_task_roundtrip(sample_planai_module, temp_file):
    """Test roundtrip conversion of Task definitions between Python and JSON."""
    # Step 1: Write the sample module to a temporary file
    original_file = temp_file(sample_planai_module)

    # Step 2: Use patch.py to parse the Tasks into JSON
    task_definitions = get_task_definitions_from_file(original_file)

    # Print for debugging if needed
    print("\nParsed Task definitions:")
    for task in task_definitions:
        print(f"  {task['className']} with {len(task['fields'])} fields")

    # Check we found the expected tasks
    assert len(task_definitions) == 2, "Expected exactly 2 Task classes"
    assert any(t['className'] == 'SimpleTask' for t in task_definitions), "SimpleTask not found"
    assert any(t['className'] == 'ComplexTask' for t in task_definitions), "ComplexTask not found"

    # Step 3: Prepare the graph data structure expected by python.py
    # Create nodes for each Task
    nodes = []
    for i, task_def in enumerate(task_definitions):
        nodes.append({
            "id": f"task_{i}",
            "type": "task",
            "data": task_def
        })

    graph_data = {
        "nodes": nodes,
        "edges": []
    }

    # Step 4: Use python.py to regenerate Python code from the JSON
    python_code, module_name, error = generate_python_module(graph_data)

    # Check for errors
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code was generated"

    # Step 5: Write the generated code to a new temporary file
    regen_file = temp_file(python_code)

    # Step 6: Parse the regenerated file to validate Task definitions
    regen_task_definitions = get_task_definitions_from_file(regen_file)

    # Print for debugging if needed
    print("\nRegenerated Task definitions:")
    for task in regen_task_definitions:
        print(f"  {task['className']} with {len(task['fields'])} fields")

    # Step 7: Compare original and regenerated Task definitions
    assert len(task_definitions) == len(regen_task_definitions), "Number of Task classes doesn't match"

    # Map task definitions by class name for easier comparison
    orig_tasks_by_name = {task['className']: task for task in task_definitions}
    regen_tasks_by_name = {task['className']: task for task in regen_task_definitions}

    # Check that all original tasks were regenerated with the same properties
    for class_name, orig_task in orig_tasks_by_name.items():
        assert class_name in regen_tasks_by_name, f"Task {class_name} missing in regenerated code"

        regen_task = regen_tasks_by_name[class_name]

        # Compare fields by name
        orig_fields_by_name = {field['name']: field for field in orig_task['fields']}
        regen_fields_by_name = {field['name']: field for field in regen_task['fields']}

        assert len(orig_fields_by_name) == len(regen_fields_by_name), \
               f"Number of fields in {class_name} doesn't match"

        for field_name, orig_field in orig_fields_by_name.items():
            assert field_name in regen_fields_by_name, \
                   f"Field {field_name} missing in regenerated {class_name}"

            regen_field = regen_fields_by_name[field_name]

            # Compare essential field properties
            assert orig_field['type'] == regen_field['type'], \
                   f"Type mismatch for {class_name}.{field_name}"
            assert orig_field['isList'] == regen_field['isList'], \
                   f"isList mismatch for {class_name}.{field_name}"
            assert orig_field['required'] == regen_field['required'], \
                   f"required mismatch for {class_name}.{field_name}"

            # If it's a literal type, check the literal values
            if orig_field['type'] == 'literal' and 'literalValues' in orig_field:
                assert 'literalValues' in regen_field, \
                       f"literalValues missing for {class_name}.{field_name}"
                assert set(orig_field['literalValues']) == set(regen_field['literalValues']), \
                       f"literalValues mismatch for {class_name}.{field_name}"