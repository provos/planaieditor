# Auto-generated PlanAI module
import json
import sys
import traceback
from typing import Any, Callable, Dict, List, Literal, Optional, Set, Tuple, Type

from planai import (
    Graph,
    JoinedTaskWorker,
    LLMInterface,
    LLMTaskWorker,
    Task,
    TaskWorker,
    llm_from_config,
)
from pydantic import ConfigDict, Field

# Add any other necessary imports based on worker code (e.g., planai.patterns)

# Task Definitions

{task_definitions}

# Worker Definitions

{worker_definitions}
