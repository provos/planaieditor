import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest
from planaieditor.patch import get_definitions_from_file  # noqa: E402
from planaieditor.python import generate_python_module  # noqa: E402


# Utility functions for roundtrip testing
def parse_python_file(file_path: str) -> Dict[str, Any]:
    """Parse a Python file and return the extracted definitions."""
    print(f"\nParsing file: {file_path}")
    definitions = get_definitions_from_file(file_path)
    print_definitions_summary(definitions)
    return definitions


def print_definitions_summary(definitions: Dict[str, Any]) -> None:
    """Print a summary of parsed definitions."""
    task_defs = definitions.get("tasks", [])
    worker_defs = definitions.get("workers", [])
    edges = definitions.get("edges", [])
    imported_tasks = definitions.get("imported_tasks", [])

    print(
        f"Parsed {len(task_defs)} tasks, {len(worker_defs)} workers, {len(edges)} edges, {len(imported_tasks)} imported tasks."
    )

    if imported_tasks:
        print("Imported tasks:")
        for task in imported_tasks:
            print(f"  {task.get('className')} from {task.get('modulePath')}")

    if worker_defs:
        print("Workers:")
        for worker in worker_defs:
            worker_type = worker.get("workerType", "unknown")
            factory_fn = worker.get("factoryFunction", "")
            print(
                f"  {worker.get('className')} ({worker_type}{': ' + factory_fn if factory_fn else ''})"
            )


def create_graph_data(
    task_defs: List[Dict],
    worker_defs: List[Dict],
    imported_tasks: List[Dict],
    edges: List[Dict],
) -> Dict[str, Any]:
    """Create a graph data structure for code generation."""
    nodes = []

    # Add task nodes
    for i, task_def in enumerate(task_defs):
        nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    # Add imported task nodes
    for i, imp_task in enumerate(imported_tasks):
        nodes.append(
            {
                "id": f"imported_task_{i}",
                "type": "taskimport",
                "data": {
                    "className": imp_task["className"],
                    "modulePath": imp_task["modulePath"],
                    "nodeId": f"imported_task_{i}",
                    # If isImplicit exists in the original, preserve it
                    **(
                        {"isImplicit": imp_task["isImplicit"]}
                        if "isImplicit" in imp_task
                        else {}
                    ),
                },
            }
        )

    # Add worker nodes
    for i, worker_def in enumerate(worker_defs):
        nodes.append(
            {"id": f"worker_{i}", "type": worker_def["workerType"], "data": worker_def}
        )

    return {"nodes": nodes, "edges": edges}


def generate_and_parse(
    graph_data: Dict[str, Any], temp_file_func, print_generated_code: bool = False
) -> Tuple[str, Dict[str, Any]]:
    """Generate Python code from graph data, write to file, and parse again."""
    # Generate Python code
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    if print_generated_code:
        print("\nGenerated Python code:")
        print(python_code)

    # Write to file and parse again
    regen_file = temp_file_func(python_code)
    regen_definitions = get_definitions_from_file(regen_file)

    print("\nRe-parsed definitions summary:")
    print_definitions_summary(regen_definitions)

    return python_code, regen_definitions


def compare_tasks(orig_tasks: List[Dict], regen_tasks: List[Dict]) -> None:
    """Compare original and regenerated Task definitions."""
    assert len(orig_tasks) == len(regen_tasks), "Task count mismatch"

    # Create maps by class name
    orig_tasks_by_name = {t["className"]: t for t in orig_tasks}
    regen_tasks_by_name = {t["className"]: t for t in regen_tasks}

    # Check class names match
    assert set(orig_tasks_by_name.keys()) == set(
        regen_tasks_by_name.keys()
    ), f"Task class names mismatch: {set(orig_tasks_by_name.keys())} vs {set(regen_tasks_by_name.keys())}"

    # For each task, we could compare fields more thoroughly if needed
    # This is a basic check for now


def compare_workers(orig_workers: List[Dict], regen_workers: List[Dict]) -> None:
    """Compare original and regenerated Worker definitions."""
    assert len(orig_workers) == len(regen_workers), "Worker count mismatch"

    # Create maps by class name
    orig_workers_by_name = {w["className"]: w for w in orig_workers}
    regen_workers_by_name = {w["className"]: w for w in regen_workers}

    # Check class names match
    assert set(orig_workers_by_name.keys()) == set(
        regen_workers_by_name.keys()
    ), f"Worker class names mismatch: {set(orig_workers_by_name.keys())} vs {set(regen_workers_by_name.keys())}"

    # Check worker types
    for class_name, orig_worker in orig_workers_by_name.items():
        regen_worker = regen_workers_by_name[class_name]
        assert (
            orig_worker["workerType"] == regen_worker["workerType"]
        ), f"Worker type mismatch for {class_name}: {orig_worker['workerType']} vs {regen_worker['workerType']}"


def compare_edges(orig_edges: List[Dict], regen_edges: List[Dict]) -> None:
    """Compare original and regenerated edges."""
    assert len(orig_edges) == len(
        regen_edges
    ), f"Edge count mismatch: {len(orig_edges)} vs {len(regen_edges)}"

    # Convert to tuples for comparison
    def edge_to_tuple(edge):
        return (edge.get("source"), edge.get("target"), edge.get("targetInputType"))

    orig_edge_tuples = {edge_to_tuple(e) for e in orig_edges}
    regen_edge_tuples = {edge_to_tuple(e) for e in regen_edges}

    assert (
        orig_edge_tuples == regen_edge_tuples
    ), f"Edge definitions mismatch.\nOriginal: {orig_edge_tuples}\nRegenerated: {regen_edge_tuples}"


def compare_imported_tasks(
    orig_imported: List[Dict], regen_imported: List[Dict]
) -> None:
    """Compare original and regenerated imported task references."""

    # Convert to sets of tuples for comparison
    def imported_task_to_tuple(imp_task):
        return (imp_task["modulePath"], imp_task["className"])

    orig_imported_set = {imported_task_to_tuple(t) for t in orig_imported}
    regen_imported_set = {imported_task_to_tuple(t) for t in regen_imported}

    assert (
        orig_imported_set == regen_imported_set
    ), f"Imported task definitions mismatch.\nOriginal: {orig_imported_set}\nRegenerated: {regen_imported_set}"


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
        except Exception:
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

    def post_process(self, respponse: AnalysisTask, input_task: InputTask):
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

    assert len(worker_defs) == 4, f"Expected 3 worker classes, got {len(worker_defs)}"

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

        if name == "AdvancedLLMWorker":
            assert (
                regen_worker["workerType"] == "cachedllmtaskworker"
            ), f"Expected AdvancedLLMWorker to be CachedLLMTaskWorker, got {regen_worker['workerType']}"

        # Compare classVars (basic check for key presence and simple values)
        orig_vars = orig_worker.get("classVars", {})
        regen_vars = regen_worker.get("classVars", {})
        # Don't compare prompts directly due to potential formatting nuances
        keys_to_compare = set(orig_vars.keys()) - {"prompt", "system_prompt"}
        assert keys_to_compare == (
            set(regen_vars.keys()) - {"prompt", "system_prompt"}
        ), f"Class var keys mismatch for {name}: {orig_vars.keys()} != {regen_vars.keys()}"
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
        Path(__file__).parent.parent
        / "planaieditor"
        / "codesnippets"
        / "releasenotes.py"
    )
    assert original_file_path.exists(), f"Original file not found: {original_file_path}"

    # Parse original file
    definitions = parse_python_file(str(original_file_path))
    orig_task_defs = definitions.get("tasks", [])
    orig_worker_defs = definitions.get("workers", [])
    orig_edges = definitions.get("edges", [])
    orig_imported_tasks = definitions.get("imported_tasks", [])

    # Create graph data structure for regeneration
    graph_data = create_graph_data(
        orig_task_defs, orig_worker_defs, orig_imported_tasks, orig_edges
    )

    # Generate Python code and parse it again
    _, regen_definitions = generate_and_parse(
        graph_data, temp_file, print_generated_code=False  # Set to True to debug
    )

    # Get regenerated components
    regen_task_defs = regen_definitions.get("tasks", [])
    regen_worker_defs = regen_definitions.get("workers", [])
    regen_edges = regen_definitions.get("edges", [])
    regen_imported_tasks = regen_definitions.get("imported_tasks", [])

    # Compare components
    compare_tasks(orig_task_defs, regen_task_defs)
    compare_workers(orig_worker_defs, regen_worker_defs)
    compare_edges(orig_edges, regen_edges)
    compare_imported_tasks(orig_imported_tasks, regen_imported_tasks)

    # Print a summary of the test
    print("\nReleasenotes roundtrip summary:")
    print(
        f"Original tasks: {len(orig_task_defs)}, Regenerated tasks: {len(regen_task_defs)}"
    )
    print(
        f"Original workers: {len(orig_worker_defs)}, Regenerated workers: {len(regen_worker_defs)}"
    )
    print(f"Original edges: {len(orig_edges)}, Regenerated edges: {len(regen_edges)}")
    print(
        f"Original imported tasks: {len(orig_imported_tasks)}, Regenerated imported tasks: {len(regen_imported_tasks)}"
    )


def test_imported_task_roundtrip(temp_file):
    """Test roundtrip involving imported Task nodes."""
    original_code = """
from planai import Task, TaskWorker, Graph
from planai.patterns import SearchQuery, SearchResult # Allowed import
from typing import List, Type

# Local Task
class ProcessedResult(Task):
    processed_data: str

# Worker using imported Task
class SearchProcessor(TaskWorker):
    output_types: List[Type[Task]] = [ProcessedResult]

    def consume_work(self, task: SearchQuery):
        # Dummy processing
        print(f"Processing search query: {task.query_text}")
        self.publish_work(ProcessedResult(processed_data=task.query_text.upper()))

# Another worker using local task
class ResultAggregator(TaskWorker):
    def consume_work(self, task: ProcessedResult):
        print(f"Aggregating: {task.processed_data}")

# Graph setup function (simplified for test)
def setup_graph():
    graph = Graph(name="ImportTestGraph")
    search_proc = SearchProcessor()
    aggregator = ResultAggregator()

    graph.add_workers(search_proc, aggregator)
    graph.set_dependency(search_proc, aggregator)
    graph.set_entry(search_proc)
    return graph

"""
    original_file = temp_file(original_code)

    # Step 1: Parse original file
    print(f"\nParsing original file for imported task roundtrip: {original_file}")
    definitions = get_definitions_from_file(original_file)
    orig_task_defs = definitions.get("tasks", [])
    orig_worker_defs = definitions.get("workers", [])
    orig_edges = definitions.get("edges", [])
    orig_imported_tasks = definitions.get("imported_tasks", [])

    print(f"Parsed {len(orig_task_defs)} local tasks.")
    print(f"Parsed {len(orig_imported_tasks)} imported tasks: {orig_imported_tasks}")
    print(f"Parsed {len(orig_worker_defs)} workers.")
    print(f"Parsed {len(orig_edges)} edges.")

    # Verify initial parsing found the imported task
    assert (
        len(orig_imported_tasks) == 2
    ), "Expected 2 imported tasks (SearchQuery, SearchResult)"
    assert any(t["className"] == "SearchQuery" for t in orig_imported_tasks)
    assert any(t["className"] == "SearchResult" for t in orig_imported_tasks)
    assert any(t["modulePath"] == "planai.patterns" for t in orig_imported_tasks)

    # Step 2: Create graph data for regeneration
    task_nodes = []
    for i, task_def in enumerate(orig_task_defs):
        task_nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    # Create taskimport nodes for the *parsed* imported tasks
    imported_task_nodes = []
    for i, imp_task_ref in enumerate(orig_imported_tasks):
        imported_task_nodes.append(
            {
                "id": f"imp_task_{i}",
                "type": "taskimport",  # Crucial: use taskimport type
                "data": {
                    "modulePath": imp_task_ref["modulePath"],
                    "className": imp_task_ref["className"],
                    "nodeId": f"imp_task_{i}",  # Match node ID
                    "fields": [],  # Fields are fetched by frontend, not stored here
                },
            }
        )

    worker_nodes = []
    for i, worker_def in enumerate(orig_worker_defs):
        worker_nodes.append(
            {
                "id": f"worker_{i}",
                "type": worker_def["workerType"],
                "data": worker_def,
            }
        )

    # Combine nodes and include original edges
    all_nodes = task_nodes + imported_task_nodes + worker_nodes
    graph_data = {"nodes": all_nodes, "edges": orig_edges}

    # Step 3: Regenerate Python code
    print("\nRegenerating Python code with imported tasks...")
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    # Check if the import statement was added correctly by python.py
    assert "from planai.patterns import SearchQuery, SearchResult" in python_code

    # Step 4: Write and parse regenerated code
    regen_file = temp_file(python_code)
    print(f"Parsing regenerated file: {regen_file}")
    regen_definitions = get_definitions_from_file(regen_file)
    regen_task_defs = regen_definitions.get("tasks", [])
    regen_worker_defs = regen_definitions.get("workers", [])
    regen_edges = regen_definitions.get("edges", [])
    regen_imported_tasks = regen_definitions.get("imported_tasks", [])

    print(f"Regenerated {len(regen_task_defs)} local tasks.")
    print(
        f"Regenerated {len(regen_imported_tasks)} imported tasks: {regen_imported_tasks}"
    )
    print(f"Regenerated {len(regen_worker_defs)} workers.")
    print(f"Regenerated {len(regen_edges)} edges.")

    # Step 5: Compare regenerated results with original
    # Compare local tasks, workers, edges (basic counts and names for brevity)
    assert len(orig_task_defs) == len(regen_task_defs), "Local task count mismatch"
    assert {t["className"] for t in orig_task_defs} == {
        t["className"] for t in regen_task_defs
    }

    assert len(orig_worker_defs) == len(regen_worker_defs), "Worker count mismatch"
    assert {w["className"] for w in orig_worker_defs} == {
        w["className"] for w in regen_worker_defs
    }

    assert len(orig_edges) == len(regen_edges), "Edge count mismatch"
    # Could add detailed edge comparison if needed

    # *** Crucial: Compare the list of IMPORTED tasks ***
    def imported_task_to_tuple(imp_task):
        return (imp_task["modulePath"], imp_task["className"])

    orig_imported_set = {imported_task_to_tuple(t) for t in orig_imported_tasks}
    regen_imported_set = {imported_task_to_tuple(t) for t in regen_imported_tasks}

    assert (
        orig_imported_set == regen_imported_set
    ), f"Imported task definitions mismatch.\nOriginal: {orig_imported_set}\nRegenerated: {regen_imported_set}"


def test_subgraph_factory_roundtrip(temp_file):
    """Test roundtrip conversion of factory-created SubGraphWorkers between Python and JSON."""
    original_code = """
from pydantic import Field
from typing import List, Type
from planai import Task, TaskWorker, Graph, LLMTaskWorker
from planai.patterns import PlanRequest, FinalPlan, SearchQuery, ConsolidatedPages
from planai.patterns import create_planning_worker, create_search_fetch_worker

# --- Task Definitions ---
class InitialRequest(Task):
    query: str

class ProcessedResult(Task):
    processed_data: str

class FinalOutput(Task):
    summary: str

# --- Worker Definitions ---
class InputProcessor(TaskWorker):
    output_types: List[Type[Task]] = [PlanRequest]

    def consume_work(self, task: InitialRequest):
        # Convert to PlanRequest
        plan_req = PlanRequest(query_text=task.query)
        self.publish_work(plan_req, input_task=task)

class OutputProcessor(LLMTaskWorker):
    llm_input_type = FinalPlan
    output_types = [FinalOutput]
    prompt: str = "Summarize the final plan: {task.plan_text}"

    def consume_work(self, task: FinalPlan):
        # Process final plan
        summary = f"Summary of: {task.plan_text}"
        self.publish_work(FinalOutput(summary=summary), input_task=task)

# Simple function to build graph
def build_graph():
    graph = Graph(name="FactoryWorkerGraph")

    # Regular workers
    input_proc = InputProcessor()
    output_proc = OutputProcessor(llm=get_llm())

    # Factory-created SubGraphWorkers
    planner = create_planning_worker(
        llm=get_llm(),
        num_variations=2
    )

    # Factory with explicit name
    searcher = create_search_fetch_worker(
        llm=get_llm(),
        name="CustomSearchFetcher"
    )

    # Add workers
    graph.add_workers(input_proc, planner, searcher, output_proc)

    # Connect regular worker to factory worker
    graph.set_dependency(input_proc, planner)

    # Connect factory worker to another factory worker
    graph.set_dependency(planner, searcher)

    # Connect factory worker to regular worker
    graph.set_dependency(searcher, output_proc)

    # Set entry point
    graph.set_entry(input_proc)

    return graph

def get_llm():
    # Dummy function for the test
    return "dummy_llm"
"""
    original_file = temp_file(original_code)

    # Step 1: Parse original file
    definitions = get_definitions_from_file(original_file)
    task_defs = definitions["tasks"]
    worker_defs = definitions["workers"]
    edges = definitions["edges"]
    imported_tasks = definitions.get("imported_tasks", [])  # Important for this test

    print("\nParsed Task definitions:")
    print(f"  Local tasks: {len(task_defs)}")
    for task in task_defs:
        print(f"    {task['className']}")

    print(f"  Imported tasks: {len(imported_tasks)}")
    for task in imported_tasks:
        print(f"    {task['className']} from {task['modulePath']}")

    print("\nParsed Worker definitions:")
    for worker in worker_defs:
        worker_type = worker.get("workerType", "unknown")
        factory_fn = worker.get("factoryFunction", "")
        print(
            f"  {worker['className']} ({worker_type}{': ' + factory_fn if factory_fn else ''})"
        )

    print("\nParsed Edges:")
    for edge in edges:
        print(f"  {edge.get('source', '?')} -> {edge.get('target', '?')}")

    # Verify imported tasks
    assert (
        len(imported_tasks) >= 4
    ), f"Expected at least 4 imported tasks, got {len(imported_tasks)}"
    imported_task_names = {task["className"] for task in imported_tasks}
    for name in ["PlanRequest", "FinalPlan", "SearchQuery", "ConsolidatedPages"]:
        assert (
            name in imported_task_names
        ), f"Imported task '{name}' not found in {imported_task_names}"

    # Verify we found the factory-created workers
    # Find workers by class name
    planner = next(
        (
            w
            for w in worker_defs
            if w.get("factoryFunction") == "create_planning_worker"
        ),
        None,
    )
    searcher = next(
        (
            w
            for w in worker_defs
            if w.get("factoryFunction") == "create_search_fetch_worker"
        ),
        None,
    )

    assert planner is not None, "Factory-created planning worker not found"
    assert searcher is not None, "Factory-created search worker not found"
    assert (
        planner["workerType"] == "subgraphworker"
    ), "Planner should be a subgraphworker"
    assert (
        searcher["workerType"] == "subgraphworker"
    ), "Searcher should be a subgraphworker"
    assert (
        searcher["className"] == "CustomSearchFetcher"
    ), "Custom name not preserved for searcher"

    # Verify we have the expected edges
    assert len(edges) == 3, f"Expected 3 edges, got {len(edges)}"

    # Find edges by matching source and target
    edge1 = next(
        (
            e
            for e in edges
            if e.get("source") == "InputProcessor"
            and e.get("target") == planner["className"]
        ),
        None,
    )
    edge2 = next(
        (
            e
            for e in edges
            if e.get("source") == planner["className"]
            and e.get("target") == searcher["className"]
        ),
        None,
    )
    edge3 = next(
        (
            e
            for e in edges
            if e.get("source") == searcher["className"]
            and e.get("target") == "OutputProcessor"
        ),
        None,
    )

    assert edge1 is not None, "Edge from InputProcessor to Planner not found"
    assert edge2 is not None, "Edge from Planner to Searcher not found"
    assert edge3 is not None, "Edge from Searcher to OutputProcessor not found"

    # Step 2: Create graph data for code generation
    nodes = []

    # Add task nodes for local tasks
    for i, task_def in enumerate(task_defs):
        nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    # Add nodes for imported tasks
    for i, imp_task in enumerate(imported_tasks):
        nodes.append(
            {
                "id": f"imported_task_{i}",
                "type": "taskimport",
                "data": {
                    "className": imp_task["className"],
                    "modulePath": imp_task["modulePath"],
                    "nodeId": f"imported_task_{i}",
                },
            }
        )

    # Add worker nodes (both regular and factory-created)
    for i, worker_def in enumerate(worker_defs):
        worker_type = worker_def["workerType"]
        nodes.append({"id": f"worker_{i}", "type": worker_type, "data": worker_def})

    graph_data = {"nodes": nodes, "edges": edges}

    # Step 3: Generate Python code
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    print("\nGenerated Python code:")
    print(python_code)

    # Check if imported tasks are included in the imports
    assert (
        "from planai.patterns import " in python_code
    ), "Imported tasks not included in imports"
    for name in ["PlanRequest", "FinalPlan", "SearchQuery", "ConsolidatedPages"]:
        assert (
            name in python_code
        ), f"Imported task '{name}' not included in the generated code"

    # Check if factory functions are called correctly with exact arguments

    # remove all whitespace includign newlines
    expected_planner_call = (
        "create_planning_worker(llm=get_llm(), num_variations=2)"
    ).replace(" ", "")
    replaced_python_code = python_code.replace(" ", "").replace("\n", "")
    assert (
        expected_planner_call in replaced_python_code
    ), f'Expected call "{expected_planner_call}" not found or incorrect in generated code.'

    # Check search fetcher call with name
    expected_searcher_call = (
        'create_search_fetch_worker(llm=get_llm(), name="CustomSearchFetcher")'
    ).replace(" ", "")
    assert (
        expected_searcher_call in replaced_python_code
    ), f'Expected call "{expected_searcher_call}" not found or incorrect in generated code.'

    # Step 4: Write and parse the regenerated code
    regen_file = temp_file(python_code)
    regen_definitions = get_definitions_from_file(regen_file)
    regen_worker_defs = regen_definitions["workers"]
    regen_edges = regen_definitions["edges"]
    regen_imported_tasks = regen_definitions.get("imported_tasks", [])

    print("\nRegenparsed Worker definitions:")
    for worker in regen_worker_defs:
        worker_type = worker.get("workerType", "unknown")
        factory_fn = worker.get("factoryFunction", "")
        print(
            f"  {worker['className']} ({worker_type}{': ' + factory_fn if factory_fn else ''})"
        )

    print("\nRegenparsed Imported Tasks:")
    for task in regen_imported_tasks:
        print(f"  {task['className']} from {task['modulePath']}")

    # Verify imported tasks were preserved
    assert (
        len(regen_imported_tasks) >= 4
    ), f"Expected at least 4 imported tasks in regenerated code, got {len(regen_imported_tasks)}"
    regen_imported_task_names = {task["className"] for task in regen_imported_tasks}
    for name in ["PlanRequest", "FinalPlan", "SearchQuery", "ConsolidatedPages"]:
        assert (
            name in regen_imported_task_names
        ), f"Imported task '{name}' not found in regenerated code"

    # Verify regenerated code contains factory workers
    regen_planner = next(
        (
            w
            for w in regen_worker_defs
            if w.get("factoryFunction") == "create_planning_worker"
        ),
        None,
    )
    regen_searcher = next(
        (
            w
            for w in regen_worker_defs
            if w.get("factoryFunction") == "create_search_fetch_worker"
        ),
        None,
    )

    assert (
        regen_planner is not None
    ), "Factory-created planning worker not in regenerated code"
    assert (
        regen_searcher is not None
    ), "Factory-created search worker not in regenerated code"
    assert (
        regen_searcher["className"] == "CustomSearchFetcher"
    ), "Custom name not preserved in regenerated code"

    # Verify edges were preserved
    assert (
        len(regen_edges) == 3
    ), f"Expected 3 edges in regenerated code, got {len(regen_edges)}"


def test_llm_config_roundtrip(temp_file):
    """Test roundtrip conversion of LLM configurations between Python and JSON."""
    original_code = """
from planai import Task, LLMTaskWorker, Graph, llm_from_config
from typing import Type

class QueryTask(Task):
    query: str

class ResponseTask(Task):
    answer: str

class OpenAIProcessor(LLMTaskWorker):
    llm_input_type: Type[Task] = QueryTask
    output_types = [ResponseTask]
    prompt = "Answer the query: {task.query}"

    def post_process(self, response, input_task):
        return ResponseTask(answer=response.content)

class AnthropicProcessor(LLMTaskWorker):
    llm_input_type = QueryTask
    output_types = [ResponseTask]
    prompt = "Process this question: {task.query}"
    system_prompt = "You are a helpful assistant."

    def post_process(self, response, input_task):
        return ResponseTask(answer=response.content)

def build_graph():
    graph = Graph(name="LLM Config Test")

    # Create LLMs
    openai_llm = llm_from_config(
        provider="openai",
        model_name="gpt-4",
        max_tokens=1024
    )

    claude_llm = llm_from_config(
        provider="anthropic",
        model_name="claude-3-opus-20240229",
        max_tokens=2048
    )

    # Create workers with LLMs
    openai_worker = OpenAIProcessor(llm=openai_llm)
    anthropic_worker = AnthropicProcessor(llm=claude_llm)

    graph.add_workers(openai_worker, anthropic_worker)
    return graph
"""
    original_file = temp_file(original_code)

    # Step 1: Parse original file
    definitions = get_definitions_from_file(original_file)
    task_defs = definitions["tasks"]
    worker_defs = definitions["workers"]

    print("\nParsed Worker definitions:")
    for worker in worker_defs:
        print(f"  {worker['className']} ({worker['workerType']})")
        if "llmConfigFromCode" in worker:
            print(f"    LLM Config: {worker['llmConfigFromCode']}")

    # Verify that we parsed the LLM configurations
    assert len(worker_defs) == 2, f"Expected 2 worker classes, got {len(worker_defs)}"
    openai_worker = next(
        (w for w in worker_defs if w["className"] == "OpenAIProcessor"), None
    )
    anthropic_worker = next(
        (w for w in worker_defs if w["className"] == "AnthropicProcessor"), None
    )

    assert openai_worker is not None, "OpenAIProcessor not found"
    assert anthropic_worker is not None, "AnthropicProcessor not found"

    assert (
        "llmConfigFromCode" in openai_worker
    ), "LLM config missing from OpenAIProcessor"
    assert (
        "llmConfigFromCode" in anthropic_worker
    ), "LLM config missing from AnthropicProcessor"

    # Check config values
    assert (
        openai_worker["llmConfigFromCode"]["provider"]["value"] == "openai"
    ), "Provider value mismatch for OpenAI"
    assert (
        openai_worker["llmConfigFromCode"]["provider"]["is_literal"] is True
    ), "Provider should be literal for OpenAI"
    assert openai_worker["llmConfigFromCode"]["model_name"]["value"] == "gpt-4"
    assert openai_worker["llmConfigFromCode"]["model_name"]["is_literal"] is True
    assert openai_worker["llmConfigFromCode"]["max_tokens"]["value"] == 1024
    assert openai_worker["llmConfigFromCode"]["max_tokens"]["is_literal"] is True

    assert anthropic_worker["llmConfigFromCode"]["provider"]["value"] == "anthropic"
    assert anthropic_worker["llmConfigFromCode"]["provider"]["is_literal"] is True
    assert (
        anthropic_worker["llmConfigFromCode"]["model_name"]["value"]
        == "claude-3-opus-20240229"
    )
    assert anthropic_worker["llmConfigFromCode"]["model_name"]["is_literal"] is True
    assert anthropic_worker["llmConfigFromCode"]["max_tokens"]["value"] == 2048
    assert anthropic_worker["llmConfigFromCode"]["max_tokens"]["is_literal"] is True

    # Step 2: Create graph data for regeneration
    task_nodes = []
    for i, task_def in enumerate(task_defs):
        task_nodes.append({"id": f"task_{i}", "type": "task", "data": task_def})

    worker_nodes = []
    for i, worker_def in enumerate(worker_defs):
        # Simulate the frontend creating the llmConfig based on llmConfigFromCode
        if "llmConfigFromCode" in worker_def:
            original_llm_config = worker_def["llmConfigFromCode"]
            # Create the new llmConfig structure for the regeneration step
            new_llm_config = {}
            for key, config_item in original_llm_config.items():
                # Ensure config_item is the dictionary { "value": ..., "is_literal": ... }
                new_llm_config[key] = (
                    config_item  # Already in correct format (shouldn't happen yet)
                )

            # Replace llmConfigFromCode with the new llmConfig for regeneration
            worker_def["llmConfig"] = new_llm_config
            del worker_def["llmConfigFromCode"]

        worker_nodes.append(
            {
                "id": f"worker_{i}",
                "type": worker_def["workerType"],
                "data": worker_def,  # Pass the potentially modified worker_def
            }
        )

    graph_data = {"nodes": task_nodes + worker_nodes, "edges": []}

    # Step 3: Regenerate Python code
    python_code, _, error = generate_python_module(graph_data)
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code generated"

    # Print the generated code for debugging
    print("\nRegenerated Python code:")
    print(python_code)

    # Step 4: Write and parse regenerated code
    regen_file = temp_file(python_code)
    regen_definitions = get_definitions_from_file(regen_file)
    regen_worker_defs = regen_definitions["workers"]

    print("\nRegenerated Worker definitions:")
    for worker in regen_worker_defs:
        print(f"  {worker['className']} ({worker['workerType']})")

    # Step 5: Verify that the regenerated code contains the LLM instantiations
    assert (
        "llm_from_config(" in python_code
    ), "llm_from_config call missing in generated code"
    assert (
        'provider="openai"' in python_code
    ), "OpenAI provider missing in generated code"
    assert (
        'provider="anthropic"' in python_code
    ), "Anthropic provider missing in generated code"
    assert (
        'model_name="gpt-4"' in python_code
    ), "GPT-4 model name missing in generated code"
    assert (
        'model_name="claude-3-opus-20240229"' in python_code
    ), "Claude model name missing in generated code"
    assert (
        "max_tokens=1024" in python_code
    ), "OpenAI max_tokens missing in generated code"
    assert (
        "max_tokens=2048" in python_code
    ), "Anthropic max_tokens missing in generated code"


def test_deepsearch_fixture_roundtrip(temp_file):
    """Test roundtrip conversion of the deepsearch fixture."""
    # Parse the original file
    # Define the path to the original releasenotes example
    original_file_path = (
        Path(__file__).parent.parent
        / "tests"
        / "e2e"
        / "fixtures"
        / "deepsearch_fixture.py"
    )
    orig_definitions = parse_python_file(original_file_path)

    # Extract original components
    orig_task_defs = orig_definitions.get("tasks", [])
    orig_worker_defs = orig_definitions.get("workers", [])
    orig_edges = orig_definitions.get("edges", [])
    orig_imported_tasks = orig_definitions.get("imported_tasks", [])

    # Create graph data structure
    graph_data = create_graph_data(
        orig_task_defs, orig_worker_defs, orig_imported_tasks, orig_edges
    )

    # Generate Python code and parse the regenerated definitions
    _, regen_definitions = generate_and_parse(
        graph_data, temp_file, print_generated_code=False  # Set to True for debugging
    )

    # Extract regenerated components
    regen_task_defs = regen_definitions.get("tasks", [])
    regen_worker_defs = regen_definitions.get("workers", [])
    regen_edges = regen_definitions.get("edges", [])
    regen_imported_tasks = regen_definitions.get("imported_tasks", [])

    # Compare components
    compare_tasks(orig_task_defs, regen_task_defs)
    compare_workers(orig_worker_defs, regen_worker_defs)
    compare_edges(orig_edges, regen_edges)
    compare_imported_tasks(orig_imported_tasks, regen_imported_tasks)

    # Print a summary of the test
    print("\nDeepsearch fixture roundtrip summary:")
    print(
        f"Original tasks: {len(orig_task_defs)}, Regenerated tasks: {len(regen_task_defs)}"
    )
    print(
        f"Original workers: {len(orig_worker_defs)}, Regenerated workers: {len(regen_worker_defs)}"
    )
    print(f"Original edges: {len(orig_edges)}, Regenerated edges: {len(regen_edges)}")
    print(
        f"Original imported tasks: {len(orig_imported_tasks)}, Regenerated imported tasks: {len(regen_imported_tasks)}"
    )
