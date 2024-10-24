# Standard library imports
import os
import copy
import json
import inspect
from dotenv import load_dotenv
from helpers.chat import log_tokens
from helpers.utils import get_redis_connection
load_dotenv()
# Package/library imports
import openai
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
# Define a decorator to handle context uniformly
import logging
from _types import Agent, Tool, Result, Response, AgentFunction, function_to_json
from typing import List, Dict, Any
from collections import defaultdict

redis_client = get_redis_connection()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _tool_call(tool: Tool, messages: List[Dict[str, Any]], context: Dict = {}):
    """Make a tool call to the given tool."""
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=[function_to_json(tool)],
        tool_choice="required",
        parallel_tool_calls=False,
    )
    return response

def make_tool_call(tool: Tool, messages: List[Dict[str, Any]], context: Dict = {}):
    """Make a tool call to the given tool."""
    response = _tool_call(tool, messages, context=context)
    try:
        result = tool.model_validate_json(response.choices[0].message.tool_calls[0].function.arguments)
    except Exception as e:
        print(f"Error in {tool.__name__} Model Validation: {e}")
        raise e
    return result

def fetch_agent_response(agent: Agent, history: List, context: Dict) -> ChatCompletionMessage:
    """Fetches the response from an agent."""
    context      = defaultdict(str, context)
    instructions = agent.instructions(context) if callable(agent.instructions) else agent.instructions
    messages     = [{"role": "system", "content": instructions}] + history

    tools        = [function_to_json(f) for f in agent.functions]

    create_params = {
        "model": agent.model,
        "messages": messages,
        "tools": tools or None,
        "tool_choice": agent.tool_choice,
    }

    if tools:
        create_params["parallel_tool_calls"] = agent.parallel_tool_calls

    return openai_client.chat.completions.create(**create_params)

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
        return Result(value=str(result.execute(context=context)))
    else:
        try:
            return Result(value=str(result), context=context)
        except Exception as e:
            error_message = f"Failed to cast response to string: {result}. Make sure agent functions return a string or Result object. Error: {str(e)}"
            raise TypeError(error_message)

def execute_tool_calls(tool_calls: List[ChatCompletionMessageToolCall], functions: List[AgentFunction], context: Dict) -> Response:
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
            raw_result    = tool_instance.execute(context=context)
        elif isinstance(func, Tool):
            raw_result = func.execute(context=context)
        else:
            # Ensure context is passed to functions that require it
            if 'context' in inspect.signature(func).parameters:
                raw_result = func(**args, context=context)
            else:
                raw_result = func(**args)

        # Process the result based on its type
        result: Result = process_function_result(raw_result, context=context)

        # Add the result to the tool call response
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

def run_step(agent: Agent, messages: List, context: Dict = {}, max_turns: int = 5) -> Response:
    active_agent = agent
    history = copy.deepcopy(messages)
    turns = 0

    while active_agent and turns < max_turns:
        logging.info(f"Running step {turns} with agent {active_agent.name}")
        completion = fetch_agent_response(active_agent, history, context=context)
        message = completion.choices[0].message
        message.sender = active_agent.name
        history.append(json.loads(message.model_dump_json()))

        if not message.tool_calls:
            break

        partial_response = execute_tool_calls(message.tool_calls, active_agent.functions, context=context)

        # Append tool response messages to history
        history.extend(partial_response.messages)

        context.update(copy.deepcopy(partial_response.context))

        if partial_response.agent:
            active_agent = partial_response.agent

        turns += 1  # Increment the turn counter

    new_history = history[len(messages):]
    return Response(
        messages=new_history,
        agent=active_agent,
        context=context,
    )