# Standard library imports
import os
import copy
import json
import inspect
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
from pydantic import BaseModel
import logging
from helpers._types import (
    Agent,
    StrictTool,
    PermissiveTool,
    Result,
    Response,
    AgentFunction,
    function_to_json,
)
from typing import List, Dict, Any
from collections import defaultdict

load_dotenv()

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def fetch_agent_response(agent: Agent, history: List, context: Dict) -> ChatCompletionMessage:
    """Fetches the response from an agent."""
    context = defaultdict(str, context)
    instructions = agent.instructions

    # Start with system message
    messages = [{"role": "system", "content": instructions}] + history
    tools = [function_to_json(f) for f in agent.functions]

    create_params = {
        "model": agent.model,
        "messages": messages,
        "tools": tools or None,
        "tool_choice": agent.tool_choice if tools else "auto",
    }
    if tools:
        create_params["parallel_tool_calls"] = agent.parallel_tool_calls

    return openai_client.chat.completions.create(**create_params)


def execute_tool_calls(
    tool_calls: List[ChatCompletionMessageToolCall], functions: List[AgentFunction], context: Dict
) -> Response:
    function_map = {f.__name__: f for f in functions}
    partial_response = Response(
        messages=[],
        context=copy.deepcopy(context),
        usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )

    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        # Add logging for tool calls
        logging.info(f"Executing tool: {name} with args: {args}")

        # Handle missing tool case
        if name not in function_map:
            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "tool_name": name,
                    "content": f"Error: Tool {name} not found.",
                }
            )
            continue

        func = function_map[name]
        result = None
        try:
            # Execute the function or tool
            if inspect.isclass(func) and issubclass(func, StrictTool):
                tool_instance = func(**args)
                raw_result = tool_instance.execute(context=context)

            elif inspect.isclass(func) and issubclass(func, PermissiveTool):
                tool_instance = func(**args)
                raw_result = tool_instance.execute(context=context)
            elif inspect.isclass(func) and issubclass(func, BaseModel):
                tool_instance = func(**args)
                raw_result = tool_instance.model_dump()
            else:
                if "context" in inspect.signature(func).parameters:
                    raw_result = func(**args, context=context)
                else:
                    raw_result = func(**args)
            # Process the result
            if isinstance(raw_result, Result):
                result = raw_result
                # Add tool's token usage to partial response if it exists
                if result.usage:
                    for key in partial_response.usage:
                        partial_response.usage[key] += result.usage.get(key, 0)
                # Set stop flag if result indicates to stop
                if result.stop:
                    partial_response.stop = True
            elif isinstance(raw_result, Agent):
                result = Result(value=json.dumps(
                    {"assistant": raw_result.name}), agent=raw_result)
            else:
                result = Result(value=str(raw_result), context=context)
            # Only append the tool response message
            tool_response = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "tool_name": name,
                "content": str(result.value),  # Don't use json.dumps here
            }
            partial_response.messages.append(tool_response)
        except Exception as e:
            logging.error(f"Error executing tool {name}: {str(e)}")
            tool_response = {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "tool_name": name,
                "content": f"Error executing tool: {str(e)}",
            }
            partial_response.messages.append(tool_response)

        # Update context and agent if necessary
        if result and result.context:
            partial_response.context.update(result.context)

        if result and result.agent:
            partial_response.agent = result.agent

        # Break early if stop is True
        if partial_response.stop:
            break
    return partial_response


def run_step(agent: Agent, messages: List, context: Dict = {}, max_turns: int = 5) -> Response:
    active_agent = agent
    history = copy.deepcopy(messages)
    init_length = len(history)
    context = copy.deepcopy(context)
    turns = 0

    # Add token tracking
    usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    # If no active agent, we're done
    while active_agent and turns < max_turns:
        logging.info(f"Running step {turns+1} with agent {active_agent.name}")
        completion = fetch_agent_response(
            active_agent, history, context=context)

        # Track token usage from completion
        usage["prompt_tokens"] += completion.usage.prompt_tokens
        usage["completion_tokens"] += completion.usage.completion_tokens
        usage["total_tokens"] += completion.usage.total_tokens

        message = completion.choices[0].message
        message.sender = active_agent.name
        # Convert the message to dict and add to history
        message_dict = json.loads(message.model_dump_json())

        # If no tool calls, we're done with this turn
        if not message.tool_calls:
            history.append(message_dict)
            break

        # Add current agent to context before executing tool calls
        context['current_agent'] = active_agent.name
        # Execute tool calls and get responses
        partial_response = execute_tool_calls(
            message.tool_calls, active_agent.functions, context=context
        )

        # Add tool usage to total usage
        for key in usage:
            usage[key] += partial_response.usage.get(key, 0)

        # Append assistant message and tool responses together
        history.append(message_dict)
        if partial_response.messages:
            history.extend(partial_response.messages)
        if partial_response.stop:
            logging.info("Stopping agent chain")
            break
        # Update context
        context.update(partial_response.context)

        # Update active_agent if a new agent is returned
        if partial_response.agent and partial_response.agent != active_agent:
            active_agent = partial_response.agent
            logging.info(f"Agent changed to: {active_agent.name}")

        turns += 1

    logging.info(f"Number of turns: {turns}")

    return Response(
        messages=history[init_length:],
        agent=active_agent,
        context=context,
        usage=usage
    )
