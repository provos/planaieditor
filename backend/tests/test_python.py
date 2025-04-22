import ast
import json
import os
import sys
import textwrap
from pathlib import Path

import pytest

# Add the parent directory to sys.path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from planaieditor.python import (
    create_worker_class,
    generate_python_module,
    split_method_signature_body,
    worker_to_instance_name,
)


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


def test_fixture_worker_to_instance_name():
    """Test that worker_to_instance_name correctly handles all node types from our fixture."""
    # Load the fixture data
    fixture_path = os.path.join(
        os.path.dirname(__file__), "data", "transformed_data_deepsearch_fixture.json"
    )
    with open(fixture_path, "r") as f:
        fixture_data = json.load(f)

    # Test a few specific nodes to ensure they get correct instance names
    nodes = fixture_data["nodes"]

    # Find the UserChat node - type chattaskworker
    user_chat_node = next(n for n in nodes if n["data"]["className"] == "UserChat")
    instance_name = worker_to_instance_name(user_chat_node)
    assert (
        instance_name == "chat_worker"
    ), f"Expected 'chat_worker', got '{instance_name}'"

    # Find the ChatAdapter node - type taskworker
    chat_adapter_node = next(
        n for n in nodes if n["data"]["className"] == "ChatAdapter"
    )
    instance_name = worker_to_instance_name(chat_adapter_node)
    assert (
        instance_name == "chat_adapter"
    ), f"Expected 'chat_adapter', got '{instance_name}'"


def test_fixture_edge_generation():
    """Test edge generation using the fixture to debug the missing instances issue."""
    # Load the fixture data
    fixture_path = os.path.join(
        os.path.dirname(__file__), "data", "transformed_data_deepsearch_fixture.json"
    )
    with open(fixture_path, "r") as f:
        fixture_data = json.load(f)

    # Extract just the nodes relevant to our failing edges for a simplified test
    all_nodes = fixture_data["nodes"]

    # Include only the nodes we need for this test
    nodes_to_include = ["UserChat", "ChatAdapter", "ChatTask", "ResponsePublisher"]

    reduced_nodes = [
        n
        for n in all_nodes
        if n.get("data", {}).get("className") in nodes_to_include
        or n.get("type") == "taskimport"
        and n.get("data", {}).get("className") == "ChatTask"
    ]

    # Only include the relevant edges
    edges_to_include = [
        {"source": "UserChat", "target": "ChatAdapter"},
        {"source": "ChatTask", "target": "UserChat"},
        {"source": "ChatAdapter", "target": "ResponsePublisher"},
    ]

    # Create a simplified graph with just the problematic nodes and edges
    test_graph = {"nodes": reduced_nodes, "edges": edges_to_include}

    # Generate Python code from this simplified graph
    python_code, module_name, error = generate_python_module(test_graph)

    # Check if generation succeeded
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code was generated"

    # Check if the edge dependencies were set correctly
    assert (
        "graph.set_dependency(chat_worker, chat_adapter)" in python_code
    ), "Missing edge from UserChat to ChatAdapter"

    # We don't expect to see a direct dependency from ChatTask to UserChat
    # because ChatTask is likely an input task, not a worker

    # Also check if chat_worker and chat_adapter are properly instantiated
    assert (
        "chat_worker = UserChat(" in python_code
    ), "UserChat worker not properly instantiated"
    assert (
        "chat_adapter = ChatAdapter(" in python_code
    ), "ChatAdapter worker not properly instantiated"

    # Print the generated code for debugging
    print("\nGenerated Python code from fixture:")
    print(python_code)


def test_fixture_edge_generation_full():
    """Test edge generation with the full fixture to get detailed debugging information."""
    # Load the fixture data
    fixture_path = os.path.join(
        os.path.dirname(__file__), "data", "transformed_data_deepsearch_fixture.json"
    )
    with open(fixture_path, "r") as f:
        fixture_data = json.load(f)

    # Create a dictionary to collect debugging info
    debug_info = {"worker_instances": {}, "task_names": set(), "edge_processing": []}

    # Map class names to instance names for all worker nodes
    for node in fixture_data["nodes"]:
        if node.get("type") in [
            "taskworker",
            "llmtaskworker",
            "cachedtaskworker",
            "cachedllmtaskworker",
            "joinedtaskworker",
            "chattaskworker",
            "subgraphworker",
        ]:
            class_name = node.get("data", {}).get("className")
            instance_name = worker_to_instance_name(node)
            debug_info["worker_instances"][class_name] = instance_name

    # Collect task names
    for node in fixture_data["nodes"]:
        if node.get("type") == "task" or node.get("type") == "taskimport":
            class_name = node.get("data", {}).get("className")
            if class_name:
                debug_info["task_names"].add(class_name)

    # Analyze each edge
    for edge in fixture_data["edges"]:
        source = edge.get("source")
        target = edge.get("target")

        source_instance = debug_info["worker_instances"].get(source)
        target_instance = debug_info["worker_instances"].get(target)

        edge_info = {
            "source_class": source,
            "target_class": target,
            "source_instance": source_instance,
            "target_instance": target_instance,
            "is_task_to_worker": source in debug_info["task_names"],
            "is_valid": source_instance is not None and target_instance is not None,
        }

        debug_info["edge_processing"].append(edge_info)

    # Generate Python code
    python_code, module_name, error = generate_python_module(fixture_data)

    # Print debugging information
    print("\nDebugging information:")
    print(f"Worker instances: {debug_info['worker_instances']}")
    print(f"Task names: {debug_info['task_names']}")

    print("\nEdge processing:")
    problematic_edges = []
    for edge_info in debug_info["edge_processing"]:
        print(f"Edge: {edge_info['source_class']} -> {edge_info['target_class']}")
        print(f"  Source instance: {edge_info['source_instance']}")
        print(f"  Target instance: {edge_info['target_instance']}")
        print(f"  Is task->worker: {edge_info['is_task_to_worker']}")
        print(f"  Is valid edge: {edge_info['is_valid']}")

        # Keep track of problematic edges
        if not edge_info["is_valid"] and not edge_info["is_task_to_worker"]:
            problematic_edges.append(edge_info)

    # Inspect problematic edges more closely
    if problematic_edges:
        print("\nProblematic edges found:")
        for edge in problematic_edges:
            print(f"  {edge['source_class']} -> {edge['target_class']}")

            # Check if source and target exist in the nodes list
            source_exists = any(
                n.get("data", {}).get("className") == edge["source_class"]
                for n in fixture_data["nodes"]
            )
            target_exists = any(
                n.get("data", {}).get("className") == edge["target_class"]
                for n in fixture_data["nodes"]
            )

            print(f"  Source class exists in nodes: {source_exists}")
            print(f"  Target class exists in nodes: {target_exists}")

    # Check for specific edges in the code
    user_chat_to_chat_adapter = (
        "graph.set_dependency(chat_worker, chat_adapter)" in python_code
    )
    chat_task_to_user_chat = "graph.set_entry(chat_worker)" in python_code

    print("\nAnalyzing generated code for UserChat -> ChatAdapter edge:")
    print("✓ Edge found" if user_chat_to_chat_adapter else "✗ Edge missing")

    print("\nAnalyzing generated code for ChatTask -> UserChat edge:")
    print("✓ Edge found" if chat_task_to_user_chat else "✗ Edge missing")

    # Output a relevant portion of the generated code for debugging
    if python_code:
        # Look for the part of the code that sets up edges
        print("\nCode excerpt for edge setup:")
        lines = python_code.split("\n")
        for i, line in enumerate(lines):
            if "set_dependency" in line or "set_entry" in line:
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                print("\n".join(lines[start:end]))

    # Check the issue with worker_to_instance_name
    for node in fixture_data["nodes"]:
        if node.get("data", {}).get("className") in ["UserChat", "ChatAdapter"]:
            node_class = node.get("data", {}).get("className")
            node_type = node.get("type")
            var_name = node.get("data", {}).get("variableName")
            instance = worker_to_instance_name(node)
            print(f"\nDetail for {node_class}:")
            print(f"  Type: {node_type}")
            print(f"  variableName: {var_name}")
            print(f"  Calculated instance name: {instance}")

    # Forcefully fail the test to see output
    if not user_chat_to_chat_adapter or not chat_task_to_user_chat:
        print("\nTest failed: Missing expected edges in generated code")
        assert False, "Missing expected edges"
