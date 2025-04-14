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
