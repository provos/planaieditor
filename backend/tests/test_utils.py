from planaieditor.utils import parse_traceback, split_method_signature_body
import unittest


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


def test_split_no_signature_just_code():
    """Test handling input that has no method signature at all."""
    method_source = """# Process the input task and produce output
self.publish_work(Task1(name=\"processed this: \" + task.name, input_task=task))"""

    signature, body_lines = split_method_signature_body(method_source)

    # Should return None for signature when there's no method signature
    assert signature is None
    # Should return the original lines
    assert body_lines == method_source.splitlines()


# New test class for parse_traceback
class TestParseTraceback(unittest.TestCase):
    """Tests for the parse_traceback function."""

    def test_parse_traceback_valid(self):
        """Test parsing a valid traceback with a class name."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmpg2bbp4sq.py", line 92, in <module>
    graph = create_graph()
  File "/tmp/tmpg2bbp4sq.py", line 85, in create_graph
    graph.add_workers(worker1, worker2)
  File "/path/to/planai/graph.py", line 100, in add_workers
    # some planai code
  File "/tmp/tmpg2bbp4sq.py", line 25, in TaskWorker1
    some_undefined_variable
NameError: name 'some_undefined_variable' is not defined
"""
        expected_result = {
            "success": False,
            "error": {
                "message": "    some_undefined_variable\nNameError: name 'some_undefined_variable' is not defined\n",
                "nodeName": "TaskWorker1",
                "fullTraceback": None,
            },
        }
        result = parse_traceback(traceback_str)
        self.assertIsNotNone(result)
        self.assertEqual(expected_result, result)

    def test_parse_traceback_no_class_name(self):
        """Test parsing a traceback without a clear class/function name in the relevant frame."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_script.py", line 5, in <module>
    result = 1 / 0
ZeroDivisionError: division by zero
"""
        result = parse_traceback(traceback_str)
        self.assertIsNone(result, "Expected None when no class/function name is found")

    def test_parse_traceback_module_level_error(self):
        """Test parsing a traceback with an error at the module level."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_module_error.py", line 3, in <module>
    import non_existent_module
ModuleNotFoundError: No module named 'non_existent_module'
"""
        result = parse_traceback(traceback_str)
        # Depending on the exact implementation, this might return None or extract '<module>'
        # Based on the current code, it should return None as it looks for a class name
        self.assertIsNone(
            result, "Expected None for module-level errors without class context"
        )

    def test_parse_traceback_empty_string(self):
        """Test parsing an empty string."""
        traceback_str = ""
        result = parse_traceback(traceback_str)
        self.assertIsNone(result)

    def test_parse_traceback_not_a_traceback(self):
        """Test parsing a string that isn't a traceback."""
        traceback_str = "This is just a regular error message, not a traceback."
        result = parse_traceback(traceback_str)
        self.assertIsNone(result)

    def test_parse_traceback_nested_functions(self):
        """Test parsing traceback going through nested functions within a class."""
        traceback_str = """
Traceback (most recent call last):
  File "/tmp/tmp_nested.py", line 20, in <module>
    instance.outer_method()
  File "/tmp/tmp_nested.py", line 15, in outer_method
    self.inner_method()
  File "/tmp/tmp_nested.py", line 10, in InnerClass
    print(undefined_var)
NameError: name 'undefined_var' is not defined
"""
        expected_result = {
            "success": False,
            "error": {
                "message": "    print(undefined_var)\nNameError: name 'undefined_var' is not defined\n",
                "nodeName": "InnerClass",  # Extracts the class/function where the error occurred
                "fullTraceback": None,
            },
        }
        result = parse_traceback(traceback_str)
        self.assertIsNotNone(result)
        self.assertEqual(expected_result, result)

