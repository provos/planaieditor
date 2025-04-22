import ast
import os
import sys
import textwrap
from pathlib import Path

import pytest

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from planaieditor.python import create_worker_class, split_method_signature_body


def test_split_single_line_signature():
    """Test splitting a method with a simple single-line signature."""
    method_source = """def simple_method(self, arg1: str, arg2: int = 10) -> bool:
    # A simple method
    print(f"Processing {arg1}")
    return arg2 > 10
"""
    signature, body_lines = split_method_signature_body(method_source)

    # With the fixed implementation, the signature should only include the function declaration line
    assert signature == "def simple_method(self, arg1: str, arg2: int = 10) -> bool:"

    # The body should include all lines after the signature
    assert len(body_lines) == 3
    assert body_lines[0] == "# A simple method"
    assert body_lines[1] == 'print(f"Processing {arg1}")'
    assert body_lines[2] == "return arg2 > 10"


def test_split_multi_line_signature():
    """Test splitting a method with a multi-line signature."""
    method_source = """def multi_line_method(
    self,
    arg1: str,
    arg2: int = 10
) -> bool:
    # A method with multi-line signature
    print(f"Processing {arg1}")
    return arg2 > 10
"""
    signature, body_lines = split_method_signature_body(method_source)

    # The signature should include all lines up to and including the line with the colon
    assert (
        signature
        == """def multi_line_method(
    self,
    arg1: str,
    arg2: int = 10
) -> bool:"""
    )

    # The body should start with the comment line
    assert len(body_lines) == 3
    assert body_lines[0] == "# A method with multi-line signature"
    assert body_lines[1] == 'print(f"Processing {arg1}")'
    assert body_lines[2] == "return arg2 > 10"


def test_split_pass_only_method():
    """Test splitting a method with just 'pass'."""
    method_source = """def empty_method(self):
    pass
"""
    signature, body_lines = split_method_signature_body(method_source)

    assert signature == "def empty_method(self):"
    assert body_lines == ["pass"]


def test_split_with_docstring():
    """Test splitting a method with a docstring."""
    method_source = '''def doc_method(self):
    """This is a docstring.

    With multiple lines.
    """
    return True
'''
    signature, body_lines = split_method_signature_body(method_source)

    assert signature == "def doc_method(self):"

    # The docstring should be part of the body
    assert len(body_lines) == 5
    assert body_lines[0] == '"""This is a docstring.'
    assert body_lines[3] == '"""'
    assert body_lines[4] == "return True"


def test_split_malformed_method():
    """Test handling of malformed method syntax."""
    method_source = """def broken_method(self,
    # Missing closing parenthesis and colon
    return True
"""
    signature, body_lines = split_method_signature_body(method_source)

    # Should return None for signature when parsing fails
    assert signature is None
    # Should return the original lines
    assert body_lines == method_source.splitlines()


def test_split_invalid_input():
    """Test handling of non-function input."""
    method_source = """
    # This is not a function at all
    x = 10
    y = 20
    """
    signature, body_lines = split_method_signature_body(method_source)

    # Should return None for signature when parsing fails
    assert signature is None
    # Should return the original lines
    assert body_lines == method_source.splitlines()


def test_worker_class_method_handling():
    """Test how create_worker_class handles different method definitions."""
    # Create a fake node with methods of different formats
    node = {
        "type": "taskworker",
        "data": {
            "className": "TestWorker",
            "classVars": {},
            "methods": {
                # Simple single-line method
                "consume_work": "def consume_work(self, task: InputTask):\n    return self.publish_work(OutputTask())",
                # Multi-line method signature
                "post_process": "def post_process(\n    self,\n    response: OutputTask,\n    input_task: InputTask\n):\n    response.value = 'processed'\n    return response",
                # Malformed method - should be handled gracefully now
                "extra_cache_key": "def extra_cache_key(self, task \n    # Missing parenthesis\n    return 'key'",
            },
            "inputTypes": ["InputTask"],
        },
    }

    worker_class_code = create_worker_class(node)

    # Check if the worker class was created
    assert worker_class_code is not None
    assert "class TestWorker(TaskWorker):" in worker_class_code

    # Check if consume_work was formatted correctly
    assert "def consume_work(self, task: InputTask):" in worker_class_code
    assert "return self.publish_work(OutputTask())" in worker_class_code

    # Check if post_process with multi-line signature was handled correctly
    assert "def post_process(" in worker_class_code
    assert "self," in worker_class_code
    assert "response: OutputTask," in worker_class_code
    assert "input_task: InputTask" in worker_class_code
    assert "response.value = 'processed'" in worker_class_code

    # For malformed methods, check if some reasonable handling occurs
    assert "extra_cache_key" in worker_class_code


def test_worker_class_with_real_examples():
    """Test create_worker_class with real-world examples of method definitions."""
    # Examples based on test_patch.py and test_roundtrip.py
    node = {
        "type": "llmtaskworker",
        "data": {
            "className": "RealWorldWorker",
            "classVars": {
                "llm_input_type": "QueryTask",
                "output_types": ["ResponseTask"],
            },
            "methods": {
                # LLM post_process method with annotations
                "post_process": """def post_process(
    self, response: AnalysisTask, input_task: QueryTask
):
    # Add timestamp to response
    response.analysis['timestamp'] = "now"
    return response""",
                # Consume work with complex logic
                "consume_work": """def consume_work(self, task: QueryTask):
    print(f"Processing query: {task.query}")
    result = self._process_query(task.query)
    self.notify_status(task, "Query processed")
    self.publish_work(ResponseTask(result=result), input_task=task)""",
                # Method with just a pass
                "format_prompt": """def format_prompt(self, task: QueryTask) -> str:
    pass""",
            },
            "inputTypes": ["QueryTask"],
        },
    }

    worker_class_code = create_worker_class(node)

    # Verify the worker class was created with all methods
    assert worker_class_code is not None
    assert "class RealWorldWorker(LLMTaskWorker):" in worker_class_code
    assert "llm_input_type: Type[Task] = QueryTask" in worker_class_code
    assert "output_types: List[Type[Task]] = [ResponseTask]" in worker_class_code

    # Check post_process with multi-line signature
    assert (
        "def post_process(\n    self, response: AnalysisTask, input_task: QueryTask\n):"
        in worker_class_code
    )
    assert "response.analysis['timestamp'] = \"now\"" in worker_class_code

    # Check consume_work
    assert "def consume_work(self, task: QueryTask):" in worker_class_code
    assert 'print(f"Processing query: {task.query}")' in worker_class_code
    assert 'self.notify_status(task, "Query processed")' in worker_class_code

    # Check format_prompt with just pass
    assert "def format_prompt(self, task: QueryTask) -> str:" in worker_class_code
    assert "pass" in worker_class_code
