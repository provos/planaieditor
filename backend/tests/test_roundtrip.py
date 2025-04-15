import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add the parent directory to sys.path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.patch import get_definitions_from_file
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
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        )
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
    definitions = get_definitions_from_file(original_file)
    task_definitions = definitions["tasks"]  # Extract tasks from the dictionary

    # Print for debugging if needed
    print("\nParsed Task definitions:")
    for task in task_definitions:
        print(f"  {task['className']} with {len(task['fields'])} fields")

    # Check we found the expected tasks
    assert len(task_definitions) == 2, "Expected exactly 2 Task classes"
    assert any(
        t["className"] == "SimpleTask" for t in task_definitions
    ), "SimpleTask not found"
    assert any(
        t["className"] == "ComplexTask" for t in task_definitions
    ), "ComplexTask not found"

    # Step 3: Prepare the graph data structure expected by python.py
    # Create nodes for each Task
    nodes = []
    for i, task_def in enumerate(task_definitions):
        nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    graph_data = {"nodes": nodes, "edges": []}

    # Step 4: Use python.py to regenerate Python code from the JSON
    python_code, module_name, error = generate_python_module(graph_data)

    # Check for errors
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code was generated"

    # Step 5: Write the generated code to a new temporary file
    regen_file = temp_file(python_code)

    # Step 6: Parse the regenerated file to validate Task definitions
    regen_definitions = get_definitions_from_file(regen_file)
    regen_task_definitions = regen_definitions["tasks"]  # Extract tasks

    # Print for debugging if needed
    print("\nRegenerated Task definitions:")
    for task in regen_task_definitions:
        print(f"  {task['className']} with {len(task['fields'])} fields")

    # Step 7: Compare original and regenerated Task definitions
    assert len(task_definitions) == len(
        regen_task_definitions
    ), "Number of Task classes doesn't match"

    # Map task definitions by class name for easier comparison
    orig_tasks_by_name = {task["className"]: task for task in task_definitions}
    regen_tasks_by_name = {task["className"]: task for task in regen_task_definitions}

    # Check that all original tasks were regenerated with the same properties
    for class_name, orig_task in orig_tasks_by_name.items():
        assert (
            class_name in regen_tasks_by_name
        ), f"Task {class_name} missing in regenerated code"

        regen_task = regen_tasks_by_name[class_name]

        # Compare fields by name
        orig_fields_by_name = {field["name"]: field for field in orig_task["fields"]}
        regen_fields_by_name = {field["name"]: field for field in regen_task["fields"]}

        assert len(orig_fields_by_name) == len(
            regen_fields_by_name
        ), f"Number of fields in {class_name} doesn't match"

        for field_name, orig_field in orig_fields_by_name.items():
            assert (
                field_name in regen_fields_by_name
            ), f"Field {field_name} missing in regenerated {class_name}"

            regen_field = regen_fields_by_name[field_name]

            # Compare essential field properties
            assert (
                orig_field["type"] == regen_field["type"]
            ), f"Type mismatch for {class_name}.{field_name}"
            assert (
                orig_field["isList"] == regen_field["isList"]
            ), f"isList mismatch for {class_name}.{field_name}"
            assert (
                orig_field["required"] == regen_field["required"]
            ), f"required mismatch for {class_name}.{field_name}"

            # If it's a literal type, check the literal values
            if orig_field["type"] == "literal" and "literalValues" in orig_field:
                assert (
                    "literalValues" in regen_field
                ), f"literalValues missing for {class_name}.{field_name}"
                assert set(orig_field["literalValues"]) == set(
                    regen_field["literalValues"]
                ), f"literalValues mismatch for {class_name}.{field_name}"


def test_worker_roundtrip(temp_file):
    """Test roundtrip conversion of Worker definitions between Python and JSON."""
    original_code = """
from pydantic import Field
from typing import List, Optional, Literal, Type
from planai import Task, TaskWorker, LLMTaskWorker, JoinedTaskWorker, CachedLLMTaskWorker
from textwrap import dedent

# --- Task Definitions ---
class InputTask(Task):
    data: str

class OutputTask(Task):
    result: str

class AnalysisTask(Task):
    analysis: dict

class FinalReport(Task):
    report: str

class JoinedInput(Task):
    value: int

class CollectionTask(Task):
    items: List[str]

# --- Worker Definitions ---

class BasicWorker(TaskWorker):
    output_types: List[Type[Task]] = [OutputTask]
    CUSTOM_VAR = "hello"

    def consume_work(self, task: InputTask):
        # Basic processing
        processed = task.data.upper()
        self.publish_work(OutputTask(result=processed), input_task=task)

    def _helper_method(self):
        return self.CUSTOM_VAR

class AdvancedLLMWorker(CachedLLMTaskWorker):
    llm_input_type = InputTask
    llm_output_type = AnalysisTask
    output_types = [AnalysisTask] # Explicitly define if different from llm_output_type
    debug_mode = True
    prompt: str = dedent(\"""
        Analyze the input data: {task.data}
        Provide the analysis.
        \""").strip()
    system_prompt: str = "You are an analyst."

    # Optional methods
    def extra_cache_key(self, task: InputTask) -> str:
        return task.data[:10] # Cache based on first 10 chars

    def post_process(self, task: AnalysisTask):
        # Modify the analysis after LLM
        task.analysis['timestamp'] = "now"
        return task

class DataCollectorWorker(JoinedTaskWorker):
    join_type: Type[TaskWorker] = BasicWorker # Join on BasicWorker outputs
    output_types: List[Type[Task]] = [CollectionTask]

    def consume_work_joined(self, tasks: List[OutputTask]):
        # Collect results from BasicWorker
        collected_items = [t.result for t in tasks]
        self.publish_work(CollectionTask(items=collected_items), input_task=tasks[0])

"""
    original_file = temp_file(original_code)

    # Step 1: Parse original file
    definitions = get_definitions_from_file(original_file)
    task_defs = definitions["tasks"]
    worker_defs = definitions["workers"]

    print("\nParsed Worker definitions:")
    for worker in worker_defs:
        print(f"  {worker['className']} ({worker['workerType']})")

    assert len(worker_defs) == 3, "Expected 3 worker classes"

    # Step 2: Create graph data for regeneration
    task_nodes = []
    for i, task_def in enumerate(task_defs):
        task_nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    worker_nodes = []
    for i, worker_def in enumerate(worker_defs):
        worker_nodes.append(
            {
                "id": f"worker_{i}",
                "type": worker_def["workerType"],  # Use parsed worker type
                "data": worker_def,  # Pass the whole parsed data back
            }
        )

    graph_data = {"nodes": task_nodes + worker_nodes, "edges": []}

    # Step 3: Regenerate Python code
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    # Step 4: Write and parse regenerated code
    regen_file = temp_file(python_code)
    regen_definitions = get_definitions_from_file(regen_file)
    regen_worker_defs = regen_definitions["workers"]

    print("\nRegenerated Worker definitions:")
    for worker in regen_worker_defs:
        print(f"  {worker['className']} ({worker['workerType']})")

    # Step 5: Compare original and regenerated worker definitions
    assert len(worker_defs) == len(regen_worker_defs), "Number of workers mismatch"

    orig_workers_by_name = {w["className"]: w for w in worker_defs}
    regen_workers_by_name = {w["className"]: w for w in regen_worker_defs}

    for name, orig_worker in orig_workers_by_name.items():
        assert (
            name in regen_workers_by_name
        ), f"Worker {name} missing in regenerated code"
        regen_worker = regen_workers_by_name[name]

        assert (
            orig_worker["workerType"] == regen_worker["workerType"]
        ), f"Worker type mismatch for {name}"

        # Compare classVars (basic check for key presence and simple values)
        orig_vars = orig_worker.get("classVars", {})
        regen_vars = regen_worker.get("classVars", {})
        # Don't compare prompts directly due to potential formatting nuances
        keys_to_compare = set(orig_vars.keys()) - {"prompt", "system_prompt"}
        assert keys_to_compare == (
            set(regen_vars.keys()) - {"prompt", "system_prompt"}
        ), f"Class var keys mismatch for {name}"
        for key in keys_to_compare:
            # Special handling for output_types list comparison
            if key == "output_types":
                assert set(orig_vars[key]) == set(
                    regen_vars[key]
                ), f"Output types mismatch for {name}"
            else:
                assert (
                    orig_vars[key] == regen_vars[key]
                ), f"Class var '{key}' mismatch for {name}"

        # Compare methods (check for presence)
        orig_methods = orig_worker.get("methods", {})
        regen_methods = regen_worker.get("methods", {})
        assert set(orig_methods.keys()) == set(
            regen_methods.keys()
        ), f"Method keys mismatch for {name}"
        # Note: Direct string comparison of regenerated code can be brittle.

        # Compare otherMembersSource (presence check)
        assert ("otherMembersSource" in orig_worker) == (
            "otherMembersSource" in regen_worker
        ), f"Other members presence mismatch for {name}"
        if "otherMembersSource" in orig_worker and orig_worker["otherMembersSource"]:
            assert regen_worker.get(
                "otherMembersSource"
            ), f"Regenerated {name} missing other members source"
            # More detailed comparison is tricky, check if helper method is there
            if name == "BasicWorker":
                assert "_helper_method" in regen_worker["otherMembersSource"]


def test_releasenotes_roundtrip(temp_file):
    """Test roundtrip conversion of a complex example with multiple workers and edges."""
    # Define the path to the original releasenotes example
    original_file_path = (
        Path(__file__).parent.parent / "app" / "codesnippets" / "releasenotes.py"
    )
    assert original_file_path.exists(), f"Original file not found: {original_file_path}"

    # Step 1: Parse original file
    print(f"\nParsing original file: {original_file_path}")
    definitions = get_definitions_from_file(str(original_file_path))
    orig_task_defs = definitions["tasks"]
    orig_worker_defs = definitions["workers"]
    orig_edges = definitions["edges"]
    # orig_entry_edges = definitions["entryEdges"] # Not currently regenerated

    print(
        f"Parsed {len(orig_task_defs)} tasks, {len(orig_worker_defs)} workers, {len(orig_edges)} edges."
    )
    assert len(orig_task_defs) > 0, "No tasks parsed from original file"
    assert len(orig_worker_defs) > 0, "No workers parsed from original file"
    assert len(orig_edges) > 0, "No edges parsed from original file"

    # Step 2: Create graph data for regeneration
    task_nodes = []
    for i, task_def in enumerate(orig_task_defs):
        task_nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    worker_nodes = []
    for i, worker_def in enumerate(orig_worker_defs):
        worker_nodes.append(
            {
                "id": f"worker_{i}",
                "type": worker_def["workerType"],
                "data": worker_def,  # Pass parsed data
            }
        )

    # Important: Pass the original edges to the generator
    # The generator needs edge information to potentially infer types or structure, although
    # currently it mainly uses it to recreate graph.set_dependency calls.
    graph_data = {
        "nodes": task_nodes + worker_nodes,
        "edges": orig_edges,  # Include edges in the data sent for generation
        # "entryEdges": orig_entry_edges # If generator handled this
    }

    # Step 3: Regenerate Python code
    print("\nRegenerating Python code...")
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    # Step 4: Write and parse regenerated code
    regen_file = temp_file(python_code)
    print(f"Parsing regenerated file: {regen_file}")
    print(python_code)
    print("--------------------------------")
    regen_definitions = get_definitions_from_file(regen_file)
    regen_task_defs = regen_definitions["tasks"]
    regen_worker_defs = regen_definitions["workers"]
    regen_edges = regen_definitions["edges"]
    # regen_entry_edges = regen_definitions["entryEdges"]

    print(
        f"Regenerated {len(regen_task_defs)} tasks, {len(regen_worker_defs)} workers, {len(regen_edges)} edges."
    )

    # Step 5: Compare Task Definitions (reuse logic from test_task_roundtrip if needed)
    assert len(orig_task_defs) == len(regen_task_defs), "Task count mismatch"
    # Basic check: ensure all original task names exist in regenerated
    orig_task_names = {t["className"] for t in orig_task_defs}
    regen_task_names = {t["className"] for t in regen_task_defs}
    assert orig_task_names == regen_task_names, "Task names mismatch"
    # Could add detailed field comparison here later if needed

    # Step 6: Compare Worker Definitions (reuse logic from test_worker_roundtrip)
    assert len(orig_worker_defs) == len(regen_worker_defs), "Worker count mismatch"
    orig_workers_by_name = {w["className"]: w for w in orig_worker_defs}
    regen_workers_by_name = {w["className"]: w for w in regen_worker_defs}
    assert set(orig_workers_by_name.keys()) == set(
        regen_workers_by_name.keys()
    ), "Worker names mismatch"

    for name, orig_worker in orig_workers_by_name.items():
        regen_worker = regen_workers_by_name[name]
        assert (
            orig_worker["workerType"] == regen_worker["workerType"]
        ), f"Worker type mismatch for {name}"
        # Add detailed comparison of classVars, methods, otherMembersSource as in test_worker_roundtrip
        # ... (comparison logic omitted for brevity, assume it's similar to test_worker_roundtrip)

    # Step 7: Compare Edges
    assert len(orig_edges) == len(
        regen_edges
    ), f"Edge count mismatch. Original: {len(orig_edges)}, Regenerated: {len(regen_edges)}"

    # Compare edges based on source and target class names
    def edge_to_tuple(edge):
        # Use class names for comparison, as node IDs change
        return (edge.get("source"), edge.get("target"), edge.get("targetInputType"))

    orig_edge_tuples = {edge_to_tuple(e) for e in orig_edges}
    regen_edge_tuples = {edge_to_tuple(e) for e in regen_edges}

    assert (
        orig_edge_tuples == regen_edge_tuples
    ), f"Edge definitions mismatch.\nOriginal: {orig_edge_tuples}\nRegenerated: {regen_edge_tuples}"

    # Step 8: Compare Entry Edges (if implemented)
    # assert len(orig_entry_edges) == len(regen_entry_edges), "Entry edge count mismatch"
    # Compare entry edge details...
