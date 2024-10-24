from pydantic import BaseModel, Field
from collections import defaultdict
from collections.abc import Callable
from typing import List, Dict, Union, Optional, Any, ForwardRef
import inspect
import openai

# Define forward references
AgentRef = ForwardRef('Agent')
ToolRef = ForwardRef('Tool')
# Define the agent function type
AgentFunction = Union[Callable[..., Union[str, AgentRef, dict]], ToolRef]


class Agent(BaseModel):
    """
    An agent class that can be used to create agents.
    
    Attributes:
        name (str): The name of the agent.
        model (str): The model to use for the agent.
        instructions (Union[str, Callable[[], str]]): The instructions for the agent.
        functions (List[AgentFunction]): The functions that the agent can use.
        tool_choice (str): The tool choice for the agent.
        parallel_tool_calls (bool): Whether to allow parallel tool calls.
    """
    name: str = "Agent"
    model: str = "gpt-4"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True


class Tool(BaseModel):
    """
    A base class for tools that can be used by agents.
    """

    def execute(self, context: Dict = {}) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")


# Update forward references
Agent.update_forward_refs()
AgentFunction = Union[Callable[..., Union[str, Agent, dict]], Tool]


class Response(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        messages (List): A list of messages - New messages from the agent.
        agent (Agent): The agent instance, if applicable.
        context (dict): A dictionary of context variables.
    """
    messages: List = []
    agent: Optional[Agent] = None
    context: dict = {}


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.
    
    Attributes:
        value (str): The result value as a string.
        agent (Agent): The agent instance, if applicable.
        context (dict): A dictionary of context variables.
    """
    value: str = ""
    agent: Optional[Agent] = None
    context: dict = {}


def function_to_json(func) -> dict:
    """
    Converts a Python function or Tool into a JSON-serializable dictionary
    that describes the function's signature, including its name, description, and parameters.
    """
    if inspect.isclass(func) and issubclass(func, Tool):
        # Handle Pydantic model classes that inherit from Tool
        return openai.pydantic_function_tool(func)
    elif isinstance(func, Tool):
        # Handle instances of Tool or its subclasses
        return openai.pydantic_function_tool(func)
    elif callable(func):
        # Standard function signature processing for non-tool functions
        type_map = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            list: {"type": "array"},
            dict: {"type": "object"},
            type(None): {"type": "null"},
        }

        try:
            signature = inspect.signature(func)
        except ValueError as e:
            raise ValueError(
                f"Failed to get signature for function {func.__name__}: {str(e)}")

        parameters = {}
        for param_name, param in signature.parameters.items():
            # Skip the 'context' parameter
            if param_name == 'context':
                continue

            param_annotation = param.annotation
            if param_annotation in type_map:
                param_schema = type_map[param_annotation]
            else:
                param_schema = {"type": "string"}

            parameters[param_name] = param_schema

        required = [param.name for param in signature.parameters.values(
        ) if param.default == inspect._empty and param.name != 'context']

        return {
            "type": "function",
            "function": {
                "name": func.__name__,
                "description": func.__doc__ or "",
                "parameters": {
                    "type": "object",
                    "properties": parameters,
                    "required": required,
                },
            },
        }
    else:
        raise TypeError(f"Unsupported function or tool: {func}")
