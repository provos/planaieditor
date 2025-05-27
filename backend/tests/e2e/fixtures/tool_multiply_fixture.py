# Auto-generated PlanAI module
from typing import (  # noqa: F401
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Tuple,
    Type,
)

from llm_interface import Tool, tool  # noqa: F401
from planai import (  # noqa: F401
    CachedLLMTaskWorker,
    CachedTaskWorker,
    ChatTaskWorker,
    Graph,
    InitialTaskWorker,
    JoinedTaskWorker,
    LLMInterface,
    LLMTaskWorker,
    Task,
    TaskWorker,
    llm_from_config,
)
from pydantic import ConfigDict, Field, PrivateAttr  # noqa: F401


@tool(name="multiply", description="efficiently multiplies two numbers")
def multiply(x: float, y: float):
    return x * y


# Task Definitions


class Task1(Task):
    math_problem: str = Field(..., description="a math problem to solve")


class Task2(Task):
    answer: str = Field(..., description="the provider answer in markdown")


# Worker Definitions

# Worker class: LLMTaskWorker1


class LLMTaskWorker1(LLMTaskWorker):
    output_types: List[Type[Task]] = [Task2]
    llm_input_type: Type[Task] = Task1
    prompt: str = (
        """Please, solve the math problem for the user. You can use the provided tool for multiplying numbers."""
    )
    system_prompt: str = """You are a helpful task processing assistant."""
    tools: List[Tool] = [multiply]
    use_xml: bool = False


# End Worker Definitions (used for error handling)

# --- Graph Setup ---


def execute_graph():
    graph = Graph(name="GeneratedPlan")

    # --- LLM Configs ---

    # Instantiate: LLMTaskWorker1
    llmtaskworker1_worker = LLMTaskWorker1(
        llm=llm_from_config(provider="openai", model_name="gpt-4o-mini")
    )
    graph.add_workers(llmtaskworker1_worker)

    def callback_DataOutput1(unused, task: Task2):
        print(
            f"Received task from dataoutput-1747761645782 for metadata_DataOutput1: {task.model_dump_json()}"
        )

    graph.set_sink(llmtaskworker1_worker, Task2, callback_DataOutput1)

    print("Graph setup complete.")

    initial_tasks = []

    initial_tasks.append(
        (
            llmtaskworker1_worker,
            Task1.model_validate({"math_problem": "what's 8.3 * 9.2?"}),
        )
    )

    # Run the graph
    if initial_tasks:
        print("Running graph with initial tasks...")
        graph.run(initial_tasks=initial_tasks, display_terminal=False)

        # Get the output from the graph
        output = graph.get_output_tasks()

        # Print the output
        print(output)
    else:
        print("No initial tasks provided.")


if __name__ == "__main__":
    print("Setting up and running the generated PlanAI graph...")
    execute_graph()
    print("Script execution finished.")
