import inspect
import openai
from pydantic import BaseModel
from collections.abc import Callable
from typing import List, Dict, Union, Optional, Any, ForwardRef, Literal

# Define forward references
AgentRef = ForwardRef('Agent')
StrictToolRef = ForwardRef('StrictTool')
PermissiveToolRef = ForwardRef('PermissiveTool')
# Define the agent function type
AgentFunction = Union[Callable[..., Union[str,
                                          AgentRef, dict]], StrictToolRef, PermissiveToolRef]


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
        service (Literal["openai", "azure"]): The service provider to use (default: "openai")
    """
    name: str = "Agent"
    id: str = "agent"
    model: str = "gpt-4o-mini"
    instructions: Union[str, Callable[[], str]] = "You are a helpful agent."
    # TODO: Add an Optional Initial message - to save history
    start_message: str = ""
    functions: List[AgentFunction] = []
    tool_choice: str = None
    parallel_tool_calls: bool = True
    context: dict = {}
    service: Literal["openai", "azure"] = "openai"


class StrictTool(BaseModel):
    """
    A base class for tools that can be used by agents with strict schema validation.
    """

    def execute(self, context: Dict = {}) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")


class PermissiveTool(BaseModel):
    """
    A base class for tools that can be used by agents with permissive schema validation.
    """

    def execute(self, context: Dict = {}) -> Any:
        raise NotImplementedError("Subclasses must implement execute method")


# Update forward references
Agent.update_forward_refs()
AgentFunction = Union[Callable[..., Union[str,
                                          Agent, dict]], StrictTool, PermissiveTool]


class Response(BaseModel):
    """
    Encapsulates the possible return values for an agent function.

    Attributes:
        messages (List): A list of messages - New messages from the agent.
        agent (Agent): The agent instance, if applicable.
        context (dict): A dictionary of context variables.
        usage (Dict): A dictionary containing the number of input and output tokens used in the completion.
        stop: bool = False (Whether to stop the agent chain)
    """
    messages: List = []
    agent: Optional[Agent] = None
    context: dict = {}
    usage: Dict = {}
    stop: bool = False


class Result(BaseModel):
    """
    Encapsulates the possible return values for an agent function.
    
    Attributes:
        value (str): The result value as a string.
        agent (Agent): The agent instance, if applicable.
        context (dict): A dictionary of context variables.
        stop: bool = False (Whether to stop the agent chain)
        usage: Dict = {} (A dictionary containing the number of input and output tokens used in the completion)
    """
    value: str = ""
    agent: Optional[Agent] = None
    context: dict = {}
    usage: Dict = {}
    stop: bool = False


def function_to_json(func) -> dict:
    """
    Converts a Python function or Tool into a JSON-serializable dictionary
    that describes the function's signature, including its name, description, and parameters.
    """
    if inspect.isclass(func) and issubclass(func, StrictTool):
        # Handle Pydantic model classes that inherit from Tool
        schema = openai.pydantic_function_tool(func)
        schema["function"]["strict"] = True
        return schema
    elif inspect.isclass(func) and issubclass(func, PermissiveTool):
        # Handle instances of PermissiveTool or its subclasses
        schema = openai.pydantic_function_tool(func)
        schema["function"]["strict"] = False
        return schema

    elif inspect.isclass(func) and issubclass(func, BaseModel):
        # Handle instances of StrictTool or PermissiveTool
        schema = openai.pydantic_function_tool(func)
        schema["function"]["strict"] = False
        return schema

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
