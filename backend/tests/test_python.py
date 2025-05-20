import ast  # Added for ast.parse in the new test
import json
import os

from planaieditor.python import (
    create_all_graph_dependencies,
    create_worker_class,
    generate_python_module,
    worker_to_instance_name,
)


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
    user_chat_entry_point = "graph.set_entry(chat_worker)" in python_code

    print("\nAnalyzing generated code for UserChat -> ChatAdapter edge:")
    print("✓ Edge found" if user_chat_to_chat_adapter else "✗ Edge missing")

    print("\nAnalyzing generated code for UserChat entry point:")
    print("✓ Entry point found" if user_chat_entry_point else "✗ Entry point missing")

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
    if not user_chat_to_chat_adapter or not user_chat_entry_point:
        print("\nTest failed: Missing expected edges in generated code")
        assert False, "Missing expected edges"


def test_create_all_graph_dependencies_simple():
    """Test create_all_graph_dependencies with a simple graph structure."""
    graph_data = {
        "nodes": [
            {
                "id": "taskworker-1745444179489",
                "type": "taskworker",
                "data": {
                    "inputTypes": ["Task1"],
                    "methods": {
                        "consume_work": 'self.publish_work(Task1(name="processed " + task.name), input_task=task)'
                    },
                    "nodeId": "taskworker-1745444179489",
                    "className": "TaskWorker1",
                    "classVars": {"output_types": ["Task1"]},
                    "entryPoint": True,
                },
            },
            {
                "id": "task-1745444182416",
                "type": "task",
                "data": {
                    "className": "Task1",
                    "fields": [
                        {
                            "name": "name",
                            "type": "string",
                            "isList": False,
                            "required": True,
                        }
                    ],
                    "nodeId": "task-1745444182416",
                },
            },
            {
                "id": "datainput-1745447545023",
                "type": "datainput",
                "data": {
                    "className": "Task1",
                    "jsonData": '{"name": "niels" }',
                    "nodeId": "datainput-1745447545023",
                    "isJsonValid": True,
                },
            },
            {
                "id": "dataoutput-1745531780182",
                "type": "dataoutput",
                "data": {
                    "nodeId": "dataoutput-1745531780182",
                    "receivedData": [],
                    "inputTypes": ["Task1"],
                    "className": "DataOutput1",
                },
            },
        ],
        "edges": [
            {"source": "datainput-Task1", "target": "TaskWorker1"},
            {"source": "TaskWorker1", "target": "DataOutput1"},
        ],
    }

    nodes = graph_data["nodes"]
    edges = graph_data["edges"]

    task_nodes = [n for n in nodes if n["type"] == "task"]
    task_import_nodes = [n for n in nodes if n["type"] == "taskimport"]
    worker_nodes = [n for n in nodes if n["type"] == "taskworker"]
    output_nodes = [n for n in nodes if n["type"] == "dataoutput"]

    dependency_code = create_all_graph_dependencies(
        task_nodes, task_import_nodes, worker_nodes, output_nodes, edges
    )

    expected_entry_call = "graph.set_entry(taskworker1_worker)"
    expected_sink_call = (
        "graph.set_sink(taskworker1_worker, Task1, callback_DataOutput1)"
    )
    expected_callback_def = "def callback_DataOutput1(unused, task: Task1):"
    expected_metadata_def = '"node_id": "dataoutput-1745531780182"'

    # Check for key calls and definitions instead of exact string match
    assert (
        expected_entry_call in dependency_code
    ), f"Expected entry call '{expected_entry_call}' not found in:\n{dependency_code}"
    assert (
        expected_sink_call in dependency_code
    ), f"Expected sink call '{expected_sink_call}' not found in:\n{dependency_code}"
    assert (
        expected_callback_def in dependency_code
    ), f"Expected callback definition '{expected_callback_def}' not found in:\n{dependency_code}"
    assert (
        expected_metadata_def in dependency_code
    ), f"Expected metadata definition containing '{expected_metadata_def}' not found in:\n{dependency_code}"


def test_roundtrip_fixture_conversion():
    """Test that we can convert JSON fixture -> Python -> JSON and get the same workers and edges."""
    import json
    import tempfile
    from pathlib import Path

    from planaieditor.patch import get_definitions_from_python

    # Load the fixture data
    fixture_path = os.path.join(
        os.path.dirname(__file__), "data", "transformed_data_deepsearch_fixture.json"
    )
    with open(fixture_path, "r") as f:
        fixture_data = json.load(f)

    # Step 1: Convert JSON to Python code
    python_code, module_name, error = generate_python_module(fixture_data)

    # Verify code generation succeeded
    assert error is None, f"Error generating Python code: {error}"
    assert python_code is not None, "No Python code was generated"

    # Step 2: Write Python code to a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
        temp_file.write(python_code)
        temp_file_path = temp_file.name

    try:
        # Step 3: Parse Python code back to JSON
        parsed_data = get_definitions_from_python(temp_file_path)

        # Step 4: Compare the original and parsed data

        # Create maps of workers by className for easier comparison
        original_workers = {}
        # Map to store node type by class name
        node_type_by_class = {}

        for node in fixture_data["nodes"]:
            if node["type"] not in ["task", "taskimport"]:
                class_name = node["data"]["className"]
                original_workers[class_name] = node["data"]
                node_type_by_class[class_name] = node["type"]

        parsed_workers = {
            worker["className"]: worker for worker in parsed_data["workers"]
        }

        # Check that all original workers are in the parsed data
        for class_name, original_worker in original_workers.items():
            assert (
                class_name in parsed_workers
            ), f"Worker {class_name} missing from parsed data"

            # Get the expected worker type from the node type
            original_type = node_type_by_class.get(class_name, "").lower()
            expected_worker_type = original_type

            parsed_type = parsed_workers[class_name]["workerType"].lower()
            assert (
                parsed_type == expected_worker_type
            ), f"Worker {class_name} type mismatch: {parsed_type} != {expected_worker_type}"

        # Normalize edges for comparison
        original_edges_worker = set()
        for edge in fixture_data["edges"]:
            original_edges_worker.add((edge["source"], edge["target"]))

        parsed_edges_worker = set()
        for edge in parsed_data["edges"]:
            parsed_edges_worker.add((edge["source"], edge["target"]))

        # Check worker-to-worker edges
        assert (
            parsed_edges_worker == original_edges_worker
        ), f"Worker-to-worker edge mismatch.\nExpected: {original_edges_worker}\nGot: {parsed_edges_worker}"

        # Print a summary
        print("\nRound-trip conversion report:")
        print(f"Original workers: {len(original_workers)}")
        print(f"Parsed workers: {len(parsed_workers)}")
        print(f"Original worker edges: {len(original_edges_worker)}")
        print(f"Parsed worker edges: {len(parsed_edges_worker)}")

    finally:
        # Clean up the temporary file
        Path(temp_file_path).unlink()


def test_input_types():
    """Test that input types are correctly set for workers."""
    json_data = {
        "nodes": [
            {
                "id": "taskworker-1745444179489",
                "type": "taskworker",
                "data": {
                    "inputTypes": ["Task1"],
                    "methods": {
                        "consume_work": 'self.publish_work(Task1(name="processed " + task.name), input_task=task)'
                    },
                    "nodeId": "taskworker-1745444179489",
                    "className": "TaskWorker1",
                    "classVars": {"output_types": ["Task1"]},
                },
            },
            {
                "id": "task-1745444182416",
                "type": "task",
                "data": {
                    "className": "Task1",
                    "fields": [
                        {
                            "name": "name",
                            "type": "string",
                            "isList": False,
                            "required": True,
                        }
                    ],
                    "nodeId": "task-1745444182416",
                },
            },
            {
                "id": "datainput-1745447545023",
                "type": "datainput",
                "data": {
                    "className": "Task1",
                    "jsonData": '{"name": "niels" }',
                    "nodeId": "datainput-1745447545023",
                    "isJsonValid": True,
                },
            },
            {
                "id": "dataoutput-1745531780182",
                "type": "dataoutput",
                "data": {
                    "nodeId": "dataoutput-1745531780182",
                    "receivedData": [],
                    "inputTypes": ["Task2"],
                    "className": "DataOutput1",
                },
            },
            {
                "id": "llmtaskworker-1745544328318",
                "type": "llmtaskworker",
                "data": {
                    "inputTypes": ["Task1"],
                    "extraValidation": "return None",
                    "formatPrompt": "return self.prompt",
                    "preProcess": "return task",
                    "postProcess": "return task",
                    "enabledFunctions": {
                        "extraValidation": False,
                        "formatPrompt": False,
                        "preProcess": False,
                        "postProcess": False,
                    },
                    "nodeId": "llmtaskworker-1745544328318",
                    "className": "LLMTaskWorker1",
                    "llmConfig": {
                        "provider": {"value": "openrouter", "is_literal": True},
                        "modelId": {
                            "value": "google/gemini-2.5-flash-preview",
                            "is_literal": True,
                        },
                    },
                    "classVars": {
                        "prompt": "Based on the input, provide some short philosophical musings",
                        "system_prompt": "You are a helpful task processing assistant.",
                        "use_xml": False,
                        "debug_mode": False,
                        "llm_output_type": "",
                        "output_types": ["Task2"],
                    },
                },
            },
            {
                "id": "task-1745544357606",
                "type": "task",
                "position": {"x": 12, "y": 12},
                "data": {
                    "className": "Task2",
                    "fields": [
                        {
                            "name": "story",
                            "type": "string",
                            "isList": False,
                            "required": True,
                            "description": "a story based on the input",
                        },
                        {
                            "name": "rationale",
                            "type": "string",
                            "isList": False,
                            "required": True,
                            "description": "why you chose this story",
                        },
                    ],
                    "nodeId": "task-1745544357606",
                },
            },
        ],
        "edges": [
            {"source": "Task1", "target": "TaskWorker1"},
            {"source": "datainput-Task1", "target": "TaskWorker1"},
            {"source": "TaskWorker1", "target": "LLMTaskWorker1"},
            {"source": "LLMTaskWorker1", "target": "DataOutput1"},
        ],
    }

    # Extract nodes for processing
    worker_nodes = [
        n
        for n in json_data["nodes"]
        if n.get("type") in ["taskworker", "llmtaskworker"]
    ]

    # Get the specific worker nodes to test
    taskworker_node = next(
        n for n in worker_nodes if n["data"]["className"] == "TaskWorker1"
    )
    llmtaskworker_node = next(
        n for n in worker_nodes if n["data"]["className"] == "LLMTaskWorker1"
    )

    # Generate the Python code for the workers
    from planaieditor.python import create_worker_class

    # Test TaskWorker input and output types
    taskworker_code = create_worker_class(taskworker_node)
    assert taskworker_code is not None, "Failed to generate TaskWorker code"

    # Check TaskWorker output_types
    assert (
        "output_types: List[Type[Task]] = [Task1]" in taskworker_code
    ), f"TaskWorker output_types not correctly set in generated code: {taskworker_code}"

    # Check TaskWorker consume_work input type
    assert (
        "def consume_work(self, task: Task1):" in taskworker_code
    ), f"TaskWorker consume_work input type not correctly set in generated code: {taskworker_code}"

    # Test LLMTaskWorker input and output types
    llmtaskworker_code = create_worker_class(llmtaskworker_node)
    assert llmtaskworker_code is not None, "Failed to generate LLMTaskWorker code"

    # Check LLMTaskWorker output_types
    assert (
        "output_types: List[Type[Task]] = [Task2]" in llmtaskworker_code
    ), f"LLMTaskWorker output_types not correctly set in generated code: {llmtaskworker_code}"

    # Check LLMTaskWorker llm_input_type
    assert (
        "llm_input_type: Type[Task] = Task1" in llmtaskworker_code
    ), f"LLMTaskWorker llm_input_type not correctly set in generated code: {llmtaskworker_code}"


def test_tool_code_generation_in_module():
    """Tests that tool function code (from patch.py's 'code' field) is correctly included in the generated module."""
    tool_name = "my_sample_tool_for_generation"
    # This simulates the 'code' field from patch.py for a tool: a full function definition string.
    tool_function_definition_str = f'''
def {tool_name}(param_x: str, param_y: int = 123) -> str:
    """Docstring for {tool_name}.

    Args:
        param_x: A string parameter.
        param_y: An integer parameter with a default value of 123.

    Returns:
        A string representing the result of the calculation.
    """
    upper_param_x = param_x.upper()
    calculation = f'Result is {{upper_param_x}} with value {{param_y * 3}}'
    return calculation
'''

    # Ensure real newlines for the string as ast.unparse would produce
    tool_function_definition_str = tool_function_definition_str.replace("\\n", "\n")

    graph_data = {
        "nodes": [
            {
                "id": "tool-1745544328318",
                "type": "tool",
                "data": {
                    "name": tool_name,
                    "description": "A sample tool for testing generate_python_module.",
                    "code": tool_function_definition_str,
                },
            },
        ],
        "edges": [],
        # Assuming module_imports might be needed or can be empty
        "module_imports": "import os\nfrom typing import List, Dict",
    }

    generated_module_code, module_name, error = generate_python_module(graph_data)

    assert error is None, f"generate_python_module failed with an error: {error}"
    assert (
        generated_module_code is not None
    ), "generate_python_module did not produce any code."

    # Verify that essential parts of the tool function definition are present in the generated module code.
    # This is more robust to minor full-module formatting changes by Black than an exact full string match.
    assert (
        f"def {tool_name}(param_x: str, param_y: int = 123) -> str:"
        in generated_module_code
    ), "Tool function signature missing."
    assert (
        f'"""Docstring for {tool_name}.' in generated_module_code
    ), "Tool docstring missing."
    assert (
        "upper_param_x = param_x.upper()" in generated_module_code
    ), "First line of tool body missing."
    assert (
        'calculation = f"Result is {upper_param_x} with value {param_y * 3}"'
        in generated_module_code
    ), "Second line of tool body missing."
    assert (
        "return calculation" in generated_module_code
    ), "Return statement of tool missing."

    # Optionally, verify the generated code is syntactically valid Python
    try:
        ast.parse(generated_module_code)
    except SyntaxError as e:
        assert (
            False
        ), f"The generated module code has syntax errors: {e}\n--- Generated Code ---:\n{generated_module_code}"


def test_llm_task_worker_with_tool_generation():
    """Tests that LLMTaskWorkers correctly include tool definitions and references."""
    tool_node_id = "tool-12345"
    tool_name = "custom_calculator_tool"
    tool_function_code = '''
def custom_calculator_tool(operation: str, val1: float, val2: float) -> float:
    """Performs a calculation based on the operation.
    
    Args:
        operation: The operation to perform ('add', 'subtract').
        val1: The first value.
        val2: The second value.

    Returns:
        The result of the calculation.
    """
    if operation == "add":
        return val1 + val2
    elif operation == "subtract":
        return val1 - val2
    else:
        raise ValueError("Unsupported operation")
'''

    graph_data = {
        "nodes": [
            {
                "id": tool_node_id,
                "type": "tool",
                "data": {
                    "name": tool_name,
                    "description": "A custom calculator tool.",
                    "code": tool_function_code,
                },
            },
            {
                "id": "llmworker-67890",
                "type": "llmtaskworker",
                "data": {
                    "className": "MathSolverLLM",
                    "classVars": {
                        "llm_input_type": "MathProblemTask",
                        "output_types": ["MathSolutionTask"],
                        "prompt": "Solve the math problem using the available tools.",
                        "tool_ids": [tool_node_id],  # Reference the tool by its ID
                    },
                    "llmConfig": {  # Dummy config, not central to this test
                        "provider": {"value": "openai", "is_literal": True},
                        "modelId": {"value": "gpt-4", "is_literal": True},
                    },
                    "inputTypes": [
                        "MathProblemTask"
                    ],  # Added for consume_work signature
                },
            },
            # Minimal Task definitions to make the generated code valid
            {
                "id": "task-mathproblem",
                "type": "task",
                "data": {
                    "className": "MathProblemTask",
                    "fields": [{"name": "problem", "type": "string"}],
                },
            },
            {
                "id": "task-mathsolution",
                "type": "task",
                "data": {
                    "className": "MathSolutionTask",
                    "fields": [{"name": "solution", "type": "string"}],
                },
            },
        ],
        "edges": [],
        "module_imports": "from planai.tools import tool",  # Ensure @tool is available
    }

    generated_module_code, _, error = generate_python_module(graph_data)

    assert error is None, f"generate_python_module failed with an error: {error}"
    assert (
        generated_module_code is not None
    ), "generate_python_module did not produce any code."

    # 1. Check for the @tool decorator and the tool function definition
    expected_tool_decorator = (
        f'@tool(name="{tool_name}", description="A custom calculator tool.")'
    )
    assert (
        expected_tool_decorator in generated_module_code
    ), f"Tool decorator missing or incorrect. Expected: {expected_tool_decorator}"

    # Check for the presence of the core tool function signature and body elements
    # Normalizing whitespace in the provided tool_function_code for comparison
    normalized_tool_function_code_lines = [
        line.strip() for line in tool_function_code.split("\n") if line.strip()
    ]
    for line in normalized_tool_function_code_lines:
        assert line in generated_module_code, f"Tool function line missing: '{line}'"

    # 2. Check for the LLMTaskWorker class and its 'tools' attribute
    assert (
        "class MathSolverLLM(LLMTaskWorker):" in generated_module_code
    ), "LLMTaskWorker class definition missing."
    expected_tools_attribute = f"tools: List[Tool] = [{tool_name}]"  # Tool name, not id
    assert (
        expected_tools_attribute in generated_module_code
    ), f"LLMTaskWorker 'tools' attribute missing or incorrect. Expected: {expected_tools_attribute}"

    # 3. Verify the generated code is syntactically valid Python
    try:
        ast.parse(generated_module_code)
    except SyntaxError as e:
        assert (
            False
        ), f"The generated module code has syntax errors: {e}\\n--- Generated Code ---:\\n{generated_module_code}"
