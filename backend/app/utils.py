import re


def is_valid_python_class_name(name: str) -> bool:
    """Check if a string is a valid Python class name."""
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))
