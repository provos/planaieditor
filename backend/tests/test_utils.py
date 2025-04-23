from planaieditor.utils import split_method_signature_body


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
