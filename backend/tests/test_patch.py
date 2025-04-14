import ast
import os
import sys
from pathlib import Path
from textwrap import dedent

import pytest

# Add app directory to path for import
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.patch import _get_consume_work_input_type, get_definitions_from_file

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
        {"source": "Worker1", "target": "Worker2"},  # from graph.set_dependency(w1, w2)
        {"source": "Worker2", "target": "Worker3"},  # from graph.set_dependency(w2, w3)
        {"source": "Worker3", "target": "Worker4"},  # from .next(w4)
        {"source": "Worker2", "target": "Worker5"},  # from w2.next(w5)
    ]

    # Check if all expected edges are present
    for expected in expected_edges:
        assert any(
            e["source"] == expected["source"] and e["target"] == expected["target"]
            for e in edges
        ), f"Expected edge {expected} not found in {edges}"
