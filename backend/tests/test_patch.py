import ast
import os
import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Add app directory to path for import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from planaieditor.patch import (  # noqa: E402
    _get_consume_work_input_type,
    get_definitions_from_file,
)

# --- Fixtures ---


@pytest.fixture
def temp_python_file(tmp_path):
    """Fixture to write python code to a temporary file."""

    def _writer(code_content: str, filename="test_module.py") -> Path:
        file_path = tmp_path / filename
        file_path.write_text(code_content, encoding="utf-8")
        return file_path

    return _writer


# --- Test Cases ---


def test_extract_simple_task(temp_python_file):
    """Test basic extraction of a simple Task definition."""
    code = """
from planai import Task
from pydantic import Field

class MyTask(Task):
    description: str = Field(..., description="Task description")
    count: int = 10
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert "tasks" in definitions
    assert "workers" in definitions
    assert len(definitions["tasks"]) == 1
    assert len(definitions["workers"]) == 0

    task = definitions["tasks"][0]
    assert task["className"] == "MyTask"
    assert len(task["fields"]) == 2
    assert any(
        f["name"] == "description" and f["type"] == "string" for f in task["fields"]
    )
    assert any(f["name"] == "count" and f["type"] == "integer" for f in task["fields"])


def test_extract_worker_no_hint(temp_python_file):
    """Test worker extraction where consume_work has no type hint."""
    code = """
from planai import Task, TaskWorker

class InputTask(Task):
    data: str

class WorkerNoHint(TaskWorker):
    output_types = [InputTask] # Example output

    def consume_work(self, task):
        print(f"Processing task: {task}")
        # self.publish_work(...)
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["tasks"]) == 1
    assert len(definitions["workers"]) == 1

    worker = definitions["workers"][0]
    assert worker["className"] == "WorkerNoHint"
    assert worker["workerType"] == "taskworker"
    assert "consume_work" in worker["methods"]
    # Crucially, inputTypes should NOT be present if no hint was found
    assert "inputTypes" not in worker
    assert worker["classVars"].get("output_types") == ["InputTask"]


def test_extract_worker_with_hint(temp_python_file):
    """Test worker extraction where consume_work HAS a type hint."""
    code = """
from planai import Task, TaskWorker

class MyInputTask(Task):
    data: str

class WorkerWithHint(TaskWorker):

    def consume_work(self, task: MyInputTask):
        print(f"Processing task: {task.data}")
        # self.publish_work(...)
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["tasks"]) == 1
    assert len(definitions["workers"]) == 1

    worker = definitions["workers"][0]
    assert worker["className"] == "WorkerWithHint"
    assert worker["workerType"] == "taskworker"
    assert "consume_work" in worker["methods"]
    # **** THE KEY ASSERTION ****
    assert "inputTypes" in worker
    assert worker["inputTypes"] == ["MyInputTask"]


def test_extract_llm_worker_details(temp_python_file):
    """Test extraction of specific LLM worker properties."""
    code = """
from planai import Task, LLMTaskWorker
from typing import Type

class Query(Task):
    text: str

class Response(Task):
    answer: str

class MyLLMWorker(LLMTaskWorker):
    llm_input_type: Type[Query] = Query
    llm_output_type = Response # No Type[] annotation
    prompt: str = "Answer the query."
    system_prompt: str = "You are helpful."
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["tasks"]) == 2
    assert len(definitions["workers"]) == 1

    worker = definitions["workers"][0]
    assert worker["className"] == "MyLLMWorker"
    assert worker["workerType"] == "llmtaskworker"
    assert worker["classVars"].get("llm_input_type") == "Query"
    assert worker["classVars"].get("llm_output_type") == "Response"
    assert worker["classVars"].get("prompt") == "Answer the query."
    assert worker["classVars"].get("system_prompt") == "You are helpful."


def test_extract_dedented_prompt(temp_python_file):
    """Test extraction of prompt defined with dedent().strip()."""
    code = """
from planai import Task, LLMTaskWorker
from textwrap import dedent

class PromptTask(Task):
    input: str

class MyLLMWorkerWithDedent(LLMTaskWorker):
    llm_input_type = PromptTask
    prompt: str = dedent(\"""
        This is the first line.
          This is the second line, indented.
        This is the third line.
    \""").strip()
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["workers"]) == 1
    worker = definitions["workers"][0]
    expected_prompt = (
        "This is the first line.\n"
        "  This is the second line, indented.\n"
        "This is the third line."
    )
    actual_prompt = dedent(worker["classVars"].get("prompt")).strip()
    print(f"Expected Prompt:\n{expected_prompt}")  # Debug print
    print(f"Actual Prompt:\n{actual_prompt}")  # Debug print
    assert actual_prompt == expected_prompt
    assert "dedent(" not in actual_prompt  # Ensure helper calls are removed
    assert ".strip()" not in actual_prompt


def test_extract_other_members(temp_python_file):
    """Test consolidation of unknown members into otherMembersSource."""
    code = """
from planai import Task, TaskWorker

class OtherInput(Task):
    val: int

class WorkerWithOtherStuff(TaskWorker):
    output_types = [OtherInput]
    SOME_CONSTANT = 123

    def consume_work(self, task: OtherInput):
        processed = self._helper_method(task.val)
        self.publish_work(OtherInput(val=processed))

    def _helper_method(self, value: int) -> int:
        # This is a custom helper
        return value * self.SOME_CONSTANT + self._another_helper()

    def _another_helper(self):
        return 5

    another_var: str = "hello"
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["workers"]) == 1
    worker = definitions["workers"][0]
    assert worker["className"] == "WorkerWithOtherStuff"
    assert "inputTypes" in worker and worker["inputTypes"] == ["OtherInput"]
    assert "consume_work" in worker["methods"]

    assert "otherMembersSource" in worker
    other_source = worker["otherMembersSource"]
    print(f"Other Source:\n{other_source}")  # Debug print

    # Check that the source snippets are present
    assert "SOME_CONSTANT = 123" in other_source
    assert "def _helper_method(self, value: int) -> int:" in other_source
    assert "def _another_helper(self):" in other_source
    assert "another_var: str = 'hello'" in other_source  # Check AnnAssign

    # Check that known members are NOT in other source
    assert "output_types" not in other_source
    assert "consume_work" not in other_source


def test_get_consume_work_input_type_helper():
    """Test the helper function for extracting consume_work input type."""
    # Test case with valid hint
    code_with_hint = """
def consume_work(self, task: InputData):
    pass
"""
    tree_with_hint = ast.parse(code_with_hint)
    func_def_with_hint = tree_with_hint.body[0]
    assert isinstance(func_def_with_hint, ast.FunctionDef)
    assert _get_consume_work_input_type(func_def_with_hint) == "InputData"

    # Test case without hint
    code_no_hint = """
def consume_work(self, task):
    pass
"""
    tree_no_hint = ast.parse(code_no_hint)
    func_def_no_hint = tree_no_hint.body[0]
    assert isinstance(func_def_no_hint, ast.FunctionDef)
    assert _get_consume_work_input_type(func_def_no_hint) is None

    # Test case with different method name
    code_wrong_name = """
def process_task(self, task: InputData):
    pass
"""
    tree_wrong_name = ast.parse(code_wrong_name)
    func_def_wrong_name = tree_wrong_name.body[0]
    assert isinstance(func_def_wrong_name, ast.FunctionDef)
    assert _get_consume_work_input_type(func_def_wrong_name) is None

    # Test case with no second argument
    code_no_task_arg = """
def consume_work(self):
    pass
"""
    tree_no_task_arg = ast.parse(code_no_task_arg)
    func_def_no_task_arg = tree_no_task_arg.body[0]
    assert isinstance(func_def_no_task_arg, ast.FunctionDef)
    assert _get_consume_work_input_type(func_def_no_task_arg) is None


def test_extract_llm_worker_input_type_precedence(temp_python_file):
    """Test that llm_input_type overrides consume_work hint for input type."""
    code = """
from planai import Task, LLMTaskWorker
from typing import Type

class ConsumeHintTask(Task):
    data: str

class LLMInputTypeTask(Task):
    info: str

class PrecedenceWorker(LLMTaskWorker):
    llm_input_type: Type[LLMInputTypeTask] = LLMInputTypeTask

    # This hint should be IGNORED because llm_input_type is set
    def consume_work(self, task: ConsumeHintTask):
        print(f"Task: {task}")

    def post_process(self, response, input_task):
        pass # Required for some workers
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["workers"]) == 1
    worker = definitions["workers"][0]

    assert worker["className"] == "PrecedenceWorker"
    assert worker["workerType"] == "llmtaskworker"
    assert "inputTypes" in worker
    # Verify it used llm_input_type, NOT ConsumeHintTask
    assert worker["inputTypes"] == ["LLMInputTypeTask"]
    # Also check that the classVar was parsed correctly
    assert worker["classVars"].get("llm_input_type") == "LLMInputTypeTask"


def test_extract_joined_worker_input_type(temp_python_file):
    """Test that input type is extracted from consume_work_joined for JoinedTaskWorker."""
    code = """
from planai import Task, JoinedTaskWorker
from typing import List

class SourceTask1(Task):
    data1: int

class SourceTask2(Task):
    data2: str

class MyJoinedWorker(JoinedTaskWorker):
    def consume_work_joined(self, tasks: List[SourceTask2]):
        print(f"Joined tasks: {tasks}")
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["workers"]) == 1
    worker = definitions["workers"][0]

    assert worker["className"] == "MyJoinedWorker"
    assert worker["workerType"] == "joinedtaskworker"
    assert "inputTypes" in worker
    # Verify it used the inner type from List[SourceTask2]
    assert worker["inputTypes"] == ["SourceTask2"]


def test_extract_joined_worker_join_type(temp_python_file):
    """Test that join_type class variable is extracted from JoinedTaskWorker."""
    code = """
from planai import Task, TaskWorker, JoinedTaskWorker
from typing import List, Type

class InitialTask(Task):
    initial_data: str

class ResultTask(Task):
    final_data: str

class ChangeCollection(Task):
    changes: List[str]

class InitialTaskWorker(TaskWorker): # The worker we join on
    output_types = [ResultTask]
    def consume_work(self, task: InitialTask):
        pass

class ChangeCollector(JoinedTaskWorker):
    \"""Worker that collects all analyzed changes\"""
    join_type: Type[TaskWorker] = InitialTaskWorker # Assign join_type
    output_types: List[Type[Task]] = [ChangeCollection]

    def consume_work_joined(self, tasks: List[ResultTask]):
        self.publish_work(ChangeCollection(changes=[t.final_data for t in tasks]), input_task=tasks[0])
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert len(definitions["workers"]) == 2
    # Find the JoinedTaskWorker
    joined_worker = next(
        (w for w in definitions["workers"] if w["className"] == "ChangeCollector"), None
    )
    assert joined_worker is not None, "ChangeCollector worker not found"

    assert joined_worker["workerType"] == "joinedtaskworker"
    # Check if join_type was extracted correctly
    assert "classVars" in joined_worker
    assert "join_type" in joined_worker["classVars"]
    assert joined_worker["classVars"]["join_type"] == "InitialTaskWorker"
    # Check that consume_work_joined method is present
    assert "methods" in joined_worker
    assert "consume_work_joined" in joined_worker["methods"]


def test_extract_edges(temp_python_file):
    """Test extraction of graph edges from set_dependency and next calls."""
    code = """
from planai import Graph, TaskWorker, Task

class TaskA(Task):
    pass
class TaskB(Task):
    pass
class TaskC(Task):
    pass
class TaskD(Task):
    pass

class Worker1(TaskWorker):
    output_types = [TaskA]
    def consume_work(self, task):
        pass

class Worker2(TaskWorker):
    output_types = [TaskB]
    def consume_work(self, task: TaskA):
        pass

class Worker3(TaskWorker):
    output_types = [TaskC]
    def consume_work(self, task: TaskB):
        pass

class Worker4(TaskWorker):
    output_types = [TaskD]
    def consume_work(self, task: TaskC):
        pass

class Worker5(TaskWorker):
    def consume_work(self, task: TaskB):
        pass

def build_my_graph():
    graph = Graph()
    w1 = Worker1()
    w2 = Worker2()
    w3 = Worker3()
    w4 = Worker4()
    w5 = Worker5()

    graph.add_workers(w1, w2, w3, w4, w5)

    # Test simple set_dependency
    graph.set_dependency(w1, w2)

    # Test chained calls
    graph.set_dependency(w2, w3).next(w4)

    # Test simple next
    w2.next(w5)

    return graph
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert "edges" in definitions
    edges = definitions["edges"]
    print(f"Extracted Edges: {edges}")

    assert len(edges) == 4
    # Check for specific edges (order might vary depending on statement order)
    expected_edges = [
        # targetInputType comes from the type hint in the target worker's consume_work
        {"source": "Worker1", "target": "Worker2", "targetInputType": "TaskA"},
        {"source": "Worker2", "target": "Worker3", "targetInputType": "TaskB"},
        {"source": "Worker3", "target": "Worker4", "targetInputType": "TaskC"},
        {"source": "Worker2", "target": "Worker5", "targetInputType": "TaskB"},
    ]

    # Check if all expected edges are present
    for expected in expected_edges:
        found = False
        for e in edges:
            if e["source"] == expected["source"] and e["target"] == expected["target"]:
                assert e.get("targetInputType") == expected.get(
                    "targetInputType"
                ), f"Edge {expected} found, but targetInputType mismatch: expected {expected.get('targetInputType')}, got {e.get('targetInputType')}"
                found = True
                break
        assert found, f"Expected edge {expected} not found in {edges}"


def test_extract_entry_point(temp_python_file):
    """Test extraction of the graph entry point edge."""
    code = """
from planai import Graph, TaskWorker, Task

class EntryTask(Task):
    data: str

class EntryWorker(TaskWorker):
    def consume_work(self, task: EntryTask):
        pass

class AnotherWorker(TaskWorker):
    pass

def build_graph_with_entry():
    graph = Graph()
    ent = EntryWorker()
    aw = AnotherWorker()

    graph.add_workers(ent, aw)
    graph.set_dependency(ent, aw)
    graph.set_entry(ent) # Set entry point

    return graph
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert "entryEdges" in definitions
    entry_edges = definitions["entryEdges"]
    print(f"Extracted Entry Edges: {entry_edges}")

    assert len(entry_edges) == 1
    expected_entry = {"sourceTask": "EntryTask", "targetWorker": "EntryWorker"}
    assert entry_edges[0]["sourceTask"] == expected_entry["sourceTask"]
    assert entry_edges[0]["targetWorker"] == expected_entry["targetWorker"]


def test_extract_entry_point_indirect(temp_python_file):
    """Test extraction of the graph entry point edge."""
    code = """
from planai import Graph, TaskWorker, Task

class EntryTask(Task):
    data: str

class EntryWorker(TaskWorker):
    def consume_work(self, task: EntryTask):
        pass

class AnotherWorker(TaskWorker):
    pass

def build_graph_with_entry():
    graph = Graph()
    ent = EntryWorker()
    aw = AnotherWorker()

    graph.add_workers(ent, aw)
    graph.set_dependency(ent, aw)
    # Create initial task with repository information
    initial_task = [
        (ent, EntryTask(data="test"))
    ]

    setup_logging()

    # Run the graph
    graph.run(initial_tasks=initial_task, run_dashboard=False, display_terminal=True)

    return graph
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    assert "entryEdges" in definitions
    entry_edges = definitions["entryEdges"]
    print(f"Extracted Entry Edges: {entry_edges}")

    assert len(entry_edges) == 1
    expected_entry = {"sourceTask": "EntryTask", "targetWorker": "EntryWorker"}
    assert entry_edges[0]["sourceTask"] == expected_entry["sourceTask"]
    assert entry_edges[0]["targetWorker"] == expected_entry["targetWorker"]


def test_extract_imported_tasks(temp_python_file):
    """Test extraction of imported Task definitions based on allow list."""
    code = """
from planai import Task, TaskWorker
# Allowed imports
from planai.patterns import SearchQuery, SearchResult
from planai.patterns.planner import FinalPlan as FP # Aliased

# Disallowed import (assuming not in allow list)
from external_module import ExternalTask

# Local task
class LocalTask(Task):
    data: str

# Worker using imported task
class QueryProcessor(TaskWorker):
    def consume_work(self, task: SearchQuery):
        # Process SearchQuery
        pass

# Worker using aliased imported task
class PlanFinalizer(TaskWorker):
    def consume_work(self, task: FP):
        # Process FinalPlan
        pass
"""
    file_path = temp_python_file(code)
    # Note: get_definitions_from_file uses the ALLOWED_TASK_IMPORTS defined in patch.py
    definitions = get_definitions_from_file(str(file_path))

    assert "imported_tasks" in definitions
    imported_tasks = definitions["imported_tasks"]
    print(f"Extracted Imported Tasks: {imported_tasks}")

    expected_imported = [
        {"modulePath": "planai.patterns", "className": "SearchQuery"},
        {"modulePath": "planai.patterns", "className": "SearchResult"},
        {
            "modulePath": "planai.patterns.planner",
            "className": "FP",
        },  # Check aliased name
    ]

    # Convert lists of dicts to sets of tuples for easier comparison (order doesn't matter)
    expected_set = {tuple(sorted(d.items())) for d in expected_imported}
    actual_set = {tuple(sorted(d.items())) for d in imported_tasks}

    assert (
        actual_set == expected_set
    ), f"Imported tasks mismatch.\nExpected: {expected_set}\nGot: {actual_set}"

    # Ensure ExternalTask was not included
    assert not any(t["className"] == "ExternalTask" for t in imported_tasks)

    # Ensure local task wasn't included in imported_tasks
    assert not any(t["className"] == "LocalTask" for t in imported_tasks)
    assert any(t["className"] == "LocalTask" for t in definitions["tasks"])

    # Ensure workers are still parsed correctly
    assert len(definitions["workers"]) == 2
    assert any(w["className"] == "QueryProcessor" for w in definitions["workers"])
    assert any(w["className"] == "PlanFinalizer" for w in definitions["workers"])


def test_extract_factory_workers_and_edges(temp_python_file):
    """Test detection of workers created via factory functions and their edges."""
    code = """
from planai import Graph, TaskWorker, Task
from planai.patterns import PlanRequest, FinalPlan, ConsolidatedPages, SearchQuery
from planai.patterns import create_planning_worker  # Factory function
from planai.patterns import create_search_fetch_worker  # Factory function

class InputPreprocessor(TaskWorker):
    def consume_work(self, task: PlanRequest):
        # Process PlanRequest
        pass

class PlanProcessor(TaskWorker):
    def consume_work(self, task: FinalPlan):
        # Process FinalPlan
        pass

def build_graph_with_factory():
    graph = Graph()

    # Regular worker instantiation
    preprocessor = InputPreprocessor()
    processor = PlanProcessor()

    # Worker created via factory function - gets default className
    planner = create_planning_worker(llm="my_llm", num_variations=2)
    searcher = create_search_fetch_worker(llm="my_llm")

    # Worker with explicit name
    simple_planner = create_planning_worker(
        llm="my_llm",
        num_variations=0,
        name="SimplePlanningWorker"
    )

    graph.add_workers(preprocessor, planner, simple_planner, processor, searcher)

    # Connect regular worker to factory worker
    graph.set_dependency(preprocessor, planner)

    # Connect factory worker to another factory worker
    graph.set_dependency(planner, simple_planner)

    # Connect factory worker to regular worker
    graph.set_dependency(simple_planner, processor)

    graph.set_dependency(processor, searcher)

    # Set entry point
    graph.set_entry(preprocessor)

    return graph
"""
    file_path = temp_python_file(code)
    definitions = get_definitions_from_file(str(file_path))

    # Check if workers were correctly extracted
    workers = definitions["workers"]
    print(f"Extracted Workers: {workers}")

    # We now need to find workers by className (primary identifier) AND check variableName
    input_preprocessor = next(
        (w for w in workers if w["className"] == "InputPreprocessor"), None
    )
    plan_processor = next(
        (w for w in workers if w["className"] == "PlanProcessor"), None
    )

    # Factory workers should have their respective class names
    planner = next(
        (
            w
            for w in workers
            if "factoryFunction" in w and w["className"] == "PlanningWorkerSubgraph"
        ),
        None,
    )
    simple_planner = next(
        (
            w
            for w in workers
            if "factoryFunction" in w and w["className"] == "SimplePlanningWorker"
        ),
        None,
    )
    searcher = next(
        (w for w in workers if w["className"] == "SearchFetchWorker"),
        None,
    )
    # Verify all workers were found
    assert input_preprocessor is not None, "InputPreprocessor not found"
    assert plan_processor is not None, "PlanProcessor not found"
    assert planner is not None, "Factory-created PlanningWorkerSubgraph not found"
    assert simple_planner is not None, "Factory-created SimplePlanningWorker not found"
    assert searcher is not None, "Factory-created SearchFetchWorker not found"
    # Verify variable names are still tracked
    assert input_preprocessor.get("variableName") == "preprocessor"
    assert plan_processor.get("variableName") == "processor"
    assert planner.get("variableName") == "planner"
    assert simple_planner.get("variableName") == "simple_planner"
    assert searcher.get("variableName") == "searcher"
    # Verify factory worker details
    assert planner["workerType"] == "subgraphworker"
    assert "factoryFunction" in planner
    assert planner["factoryFunction"] == "create_planning_worker"
    # Check for the combined invocation string
    assert "factoryInvocation" in planner
    assert (
        planner["factoryInvocation"] == "llm='my_llm', num_variations=2"
    )  # Check combined string (using single quotes)
    assert planner["inputTypes"] == ["PlanRequest"]  # From factory config
    assert planner["classVars"]["output_types"] == ["FinalPlan"]  # From factory config

    # Verify factory search fetch worker
    assert searcher["workerType"] == "subgraphworker"
    assert "factoryFunction" in searcher
    assert searcher["factoryFunction"] == "create_search_fetch_worker"
    assert searcher["inputTypes"] == ["SearchQuery"]
    assert searcher["classVars"]["output_types"] == ["ConsolidatedPages"]

    # Verify factory worker with explicit name
    assert simple_planner["workerType"] == "subgraphworker"
    assert (
        simple_planner["className"] == "SimplePlanningWorker"
    )  # Explicit name from keyword arg
    assert "factoryFunction" in simple_planner
    assert simple_planner["factoryFunction"] == "create_planning_worker"
    # Check invocation string for simple_planner
    assert "factoryInvocation" in simple_planner
    assert (
        simple_planner["factoryInvocation"]
        == "llm='my_llm', num_variations=0, name='SimplePlanningWorker'"
    )

    # Check edges - now definitely use class names, not variable names
    edges = definitions["edges"]
    print(f"Extracted Edges: {edges}")

    # Expected edges should now use class names
    expected_edges = [
        {
            "source": "InputPreprocessor",
            "target": "PlanningWorkerSubgraph",
            "targetInputType": "PlanRequest",
        },
        {
            "source": "PlanningWorkerSubgraph",
            "target": "SimplePlanningWorker",
            "targetInputType": "PlanRequest",
        },
        {
            "source": "SimplePlanningWorker",
            "target": "PlanProcessor",
            "targetInputType": "FinalPlan",
        },
        {
            "source": "PlanProcessor",
            "target": "SearchFetchWorker",
            "targetInputType": "SearchQuery",
        },
    ]

    # Verify all expected edges are present
    for expected in expected_edges:
        assert any(
            e["source"] == expected["source"]
            and e["target"] == expected["target"]
            and e.get("targetInputType") == expected.get("targetInputType")
            for e in edges
        ), f"Expected edge {expected} not found in {edges}"

    # Check entry point - should use class name
    entry_edges = definitions["entryEdges"]
    assert len(entry_edges) == 1
    assert entry_edges[0]["sourceTask"] == "PlanRequest"
    assert entry_edges[0]["targetWorker"] == "InputPreprocessor"
