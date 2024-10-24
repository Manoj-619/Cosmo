# Standard library imports
import os
import copy
import json
import inspect
from collections import defaultdict
from collections.abc import Callable
from typing import List, Dict, Union, Optional, Any, ForwardRef
from dotenv import load_dotenv
from helpers.chat import log_tokens

load_dotenv()

# Package/library imports
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall

# Third-party imports
from pydantic import BaseModel, Field

# Define a decorator to handle context uniformly
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def with_context(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract context from kwargs if it exists, otherwise use an empty dict
        context = kwargs.pop('context', {})
        
        # Call the function with the original args and kwargs, plus context
        result = func(*args, **kwargs, context=context)
        
        # If the result is a dict and contains a 'context' key, update the context
        if isinstance(result, dict) and 'context' in result:
            context.update(result['context'])
        
        # If the result is a Response object, update its context
        elif isinstance(result, Response):
            result.context.update(context)
        
        return result
    return wrapper

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
    # Removed max_turns attribute

class Tool(BaseModel):
    """
    A base class for tools that can be used by agents.
    """
    @with_context
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
            raise ValueError(f"Failed to get signature for function {func.__name__}: {str(e)}")

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

        required = [param.name for param in signature.parameters.values()  if param.default == inspect._empty and param.name != 'context']

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


@log_tokens
def _tool_call(tool: Tool, messages: List[Dict[str, Any]]):
    """Make a tool call to the given tool."""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        tools=[openai.pydantic_function_tool(tool)],
        tool_choice="required",
        parallel_tool_calls=False,
    )
    return response

def make_tool_call(tool: Tool, messages: List[Dict[str, Any]]):
    """Make a tool call to the given tool."""
    response = _tool_call(tool, messages)
    try:
        result = tool.model_validate_json(response.choices[0].message.tool_calls[0].function.arguments)
    except Exception as e:
        print(f"Error in {tool.__name__} MCQ Design: {e}")
        raise e
    return result

@with_context
@log_tokens
def fetch_agent_response(agent: Agent, history: List, context: Dict) -> ChatCompletionMessage:
    """Fetches the response from an agent."""
    context = defaultdict(str, context)
    instructions = agent.instructions(context) if callable(agent.instructions) else agent.instructions
    messages = [{"role": "system", "content": instructions}] + history

    tools = [function_to_json(f) for f in agent.functions]

    create_params = {
        "model": agent.model,
        "messages": messages,
        "tools": tools or None,
        "tool_choice": agent.tool_choice,
    }

    if tools:
        create_params["parallel_tool_calls"] = agent.parallel_tool_calls

    return client.chat.completions.create(**create_params)

@with_context
def process_function_result(result, context: Dict) -> Result:
    """
    Processes the result of an agent function or Tool.
    """
    if isinstance(result, Result):
        return result
    elif isinstance(result, Agent):
        return Result(
            value=json.dumps({"assistant": result.name}),
            context=context,
            agent=result,
        )
    elif isinstance(result, Tool):
        # Handle the tool result via the execute method
        return Result(value=str(result.execute()), context=context)
    else:
        try:
            return Result(value=str(result), context=context)
        except Exception as e:
            error_message = f"Failed to cast response to string: {result}. Make sure agent functions return a string or Result object. Error: {str(e)}"
            raise TypeError(error_message)
        
@with_context
def execute_tool_calls(tool_calls: List[ChatCompletionMessageToolCall], functions: List[AgentFunction], context: Dict = {}) -> Response:
    """
    Executes tool calls from the agent and updates the context.
    """
    function_map = {}
    for f in functions:
        if inspect.isclass(f) and issubclass(f, Tool):
            func_name = f.__name__
        elif isinstance(f, Tool):
            func_name = type(f).__name__
        elif callable(f):
            func_name = f.__name__
        else:
            continue  # Unsupported function type
        function_map[func_name] = f

    partial_response = Response(messages=[], agent=None, context=copy.deepcopy(context))

    for tool_call in tool_calls:
        name = tool_call.function.name
        if name not in function_map:
            partial_response.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "tool_name": name,
                "content": f"Error: Tool {name} not found."
            })
            continue

        args = json.loads(tool_call.function.arguments)
        func = function_map[name]

        # Detect if the function is a Tool, use its `execute` method
        if inspect.isclass(func) and issubclass(func, Tool):
            # Instantiate the Tool with arguments
            tool_instance = func(**args)
            raw_result = tool_instance.execute(context=partial_response.context)  # Pass context here
        elif isinstance(func, Tool):
            raw_result = func.execute(context=partial_response.context)  # Pass context here
        elif hasattr(func, '_with_context'):
            # Use context if available
            raw_result = func(**args, context=partial_response.context)
        else:
            raw_result = func(**args)

        # Process the result based on its type
        result: Result = process_function_result(raw_result)

        partial_response.messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "tool_name": name,
            "content": result.value,
        })
        partial_response.context.update(copy.deepcopy(result.context))

        if result.agent:
            partial_response.agent = result.agent

        logging.info(f"Updated context after {name} call: {partial_response.context}")

    return partial_response

@with_context
def run_step(agent: Agent, messages: List, context: Dict = {}, max_turns: int = 5) -> Response:
    """
    Manages the conversation loop with an agent, respecting max turns and updating context.
    """
    active_agent = agent
    history      = copy.deepcopy(messages)
    turns        = 0

    while active_agent and turns < max_turns:
        logging.info(f"Running step {turns} with agent {active_agent.name}")
        completion = fetch_agent_response(active_agent, history, context=context)
        message = completion.choices[0].message
        message.sender = active_agent.name
        history.append(json.loads(message.model_dump_json()))

        if not message.tool_calls:
            break

        partial_response = execute_tool_calls(message.tool_calls, active_agent.functions, context=context)
        history.extend(partial_response.messages)
        context.update(copy.deepcopy(partial_response.context))

        if partial_response.agent:
            active_agent = partial_response.agent
            turns = 0  # Reset turns for the new agent

        turns += 1  # Increment the turn counter

    return Response(
        messages=history[len(messages):],
        agent=active_agent,
        context=context,
    )
    
