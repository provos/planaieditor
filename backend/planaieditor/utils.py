import os
import re
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

CODE_SNIPPETS_DIR = os.path.join(os.path.dirname(__file__), "codesnippets")


def is_valid_python_class_name(name: str) -> bool:
    """Check if a string is a valid Python class name."""
    if not name:
        return False
    return bool(re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name))


def split_method_signature_body(method_source: str) -> Tuple[Optional[str], List[str]]:
    """
    Splits Python method source code into its signature and body lines using ast.

    Args:
        method_source: The source code of the method.

    Returns:
        A tuple containing:
        - The signature string or None if parsing failed.
        - A list of strings representing the body lines (dedented).
          If parsing failed, returns original lines.
    """
    try:
        # Dedent source before parsing to handle indentation correctly
        dedented_source = dedent(method_source).strip()

        # Check if this is actually a method definition
        if not re.search(r"^\s*def\s+", dedented_source):
            return None, method_source.splitlines()

        # Using a simpler but reliable approach for splitting signature and body
        # Look for the first occurrence of "):", ")->" or ") ->" which typically marks the end of a signature
        lines = dedented_source.splitlines()
        signature_lines = []
        body_lines = []

        # Track if we're in the signature part
        in_signature = True
        paren_level = 0

        for i, line in enumerate(lines):
            if in_signature:
                # Count opening and closing parentheses
                paren_level += line.count("(") - line.count(")")

                # Add to signature if we're still in the signature part
                signature_lines.append(line)

                # Check if this line contains the end of the signature
                if paren_level <= 0 and ":" in line:
                    # This line contains the end of the signature
                    in_signature = False

                    # The rest of the lines are body
                    body_lines = lines[i + 1 :] if i + 1 < len(lines) else []
                    break
            else:
                # Already in body, just append
                body_lines.append(line)

        # If we never found the end of the signature, parsing failed
        if in_signature:
            raise ValueError(
                "Could not find end of signature (closing parenthesis and colon)"
            )

        # Join the signature lines
        signature = "\n".join(signature_lines)

        # Handle empty body
        if not body_lines:
            body_lines = ["pass"]
        else:
            body_lines = dedent("\n".join(body_lines)).strip().splitlines()

        return signature, body_lines

    except (SyntaxError, ValueError, IndexError) as e:
        print(f"Info: Splitting failed: {e}")
        # Parsing failed, return None for signature, and original lines as body
        return None, method_source.splitlines()


def parse_traceback(traceback_str: str) -> Optional[Dict[str, Any]]:
    """Parses a traceback string and returns a structured error message."""
    # Traceback (most recent call last):
    # File "/tmp/tmpg2bbp4sq.py", line 92, in <module>
    #   class TaskWorker1(TaskWorker):
    # File "/tmp/tmpg2bbp4sq.py", line 100, in TaskWorker1
    #   blubber
    # NameError: name 'blubber' is not defined

    in_traceback = False
    collected_lines = []
    class_name = None
    for line in traceback_str.split("\n"):
        if not in_traceback:
            if line.startswith("Traceback (most recent call last):"):
                in_traceback = True
            continue

        class_worker_match = re.search(r"File \"(.*)\", line (\d+), in (\w+)", line)
        if class_worker_match:
            class_name = class_worker_match.group(3)
            collected_lines = []
            continue

        if class_name:
            collected_lines.append(line)

    if not class_name:
        return None

    return {
        "success": False,
        "error": {
            "message": "\n".join(collected_lines),
            "nodeName": class_name,
            "fullTraceback": None,
        },
    }


def return_code_snippet(name: str) -> str:
    """
    Returns a code snippet from the codesnippets directory.
    """
    with Path(CODE_SNIPPETS_DIR, f"{name}.py").open("r", encoding="utf-8") as f:
        return f.read() + "\n\n"
