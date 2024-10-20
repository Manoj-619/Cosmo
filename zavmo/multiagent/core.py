"""Borrowed from https://github.com/openai/swarm/blob/main/swarm/core.py"""

# Standard library imports
from _types import (
    Agent,
    AgentFunction,
    ChatCompletionMessage,
    ChatCompletionMessageToolCall,
    Function,
    Response,
    Result,
)
from util import function_to_json, debug_print
import os
import copy
import json
import openai
from collections import defaultdict
from typing import List, Callable, Union
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


__CTX_VARS_NAME__ = "context"

class Swarm:
    def __init__(self):
        # Initialize the OpenAI client with the API key from environment variables
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def get_chat_completion(
        self,
        agent: Agent,
        history: List,
        context: dict,
        debug: bool,
    ) -> ChatCompletionMessage:
        # Prepare the context and instructions for the chat completion
        context = defaultdict(str, context)
        instructions = (
            agent.instructions(context)
            if callable(agent.instructions)
            else agent.instructions
        )
        # Combine system instructions with conversation history
        messages = [{"role": "system", "content": instructions}] + history
        debug_print(debug, "Getting chat completion for...:", messages)

        # Prepare the tools (functions) for the agent
        tools = [function_to_json(f) for f in agent.functions]
        
        # Hide context variables from the model
        # IMPORTANT: Why?
        for tool in tools:
            params = tool["function"]["parameters"]
            params["properties"].pop(__CTX_VARS_NAME__, None)
            if __CTX_VARS_NAME__ in params["required"]:
                params["required"].remove(__CTX_VARS_NAME__)

        # Set up parameters for the chat completion API call
        create_params = {
            "model": agent.model,
            "messages": messages,
            "tools": tools or None,
            "tool_choice": agent.tool_choice,
        }

        if tools:
            create_params["parallel_tool_calls"] = agent.parallel_tool_calls

        # Make the API call to get the chat completion
        return self.client.chat.completions.create(**create_params)

    def handle_function_result(self, result, debug) -> Result:
        # Process the result of a function call
        match result:
            case Result() as result:
                return result
            case Agent() as agent:
                # If the result is an Agent, create a Result object for agent handoff
                return Result(
                    value=json.dumps({"assistant": agent.name}),
                    agent=agent,
                    context={},
                )
            case BaseModel() as model:
                return Result(
                    value=str(model),
                    agent=None,
                    context={},
                    tool_calls=[],
                )
            case _:
                # For other types, attempt to convert to string
                try:
                    return Result(value=str(result))
                except Exception as e:
                    error_message = f"Failed to cast response to string: {result}. Make sure agent functions return a string or Result object. Error: {str(e)}"
                    debug_print(debug, error_message)
                    raise TypeError(error_message)



    def handle_tool_calls(
        self,
        tool_calls: List[ChatCompletionMessageToolCall],
        functions: List[AgentFunction],
        context: dict,
        debug: bool,
    ) -> Response:
        function_map = {f.__name__: f for f in functions}
        partial_response = Response(messages=[], agent=None, context={})

        for tool_call in tool_calls:
            name = tool_call.function.name
            if name not in function_map:
                debug_print(debug, f"Tool {name} not found in function map.")
                partial_response.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "tool_name": name,
                        "content": f"Error: Tool {name} not found.",
                    }
                )
                continue
            args = json.loads(tool_call.function.arguments)
            debug_print(debug, f"Processing tool call: {name} with arguments {args}")

            func = function_map[name]
            
            # Check if func is a Pydantic model or a callable function
            if isinstance(func, type) and issubclass(func, BaseModel):
                # If it's a Pydantic model, create an instance with the arguments
                raw_result = func(**args)
            else:
                # If it's a callable function, check for context variables
                if hasattr(func, '__code__') and __CTX_VARS_NAME__ in func.__code__.co_varnames:
                    args[__CTX_VARS_NAME__] = context
                # Run the function with the arguments and return the result
                raw_result = func(**args)

            result: Result = self.handle_function_result(raw_result, debug)
            partial_response.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "tool_name": name,
                    "content": result.value,
                }
            )
            partial_response.context.update(result.context)
            if result.agent:
                debug_print(debug, f"Partial response agent: {result.agent}")
                partial_response.agent = result.agent

        return partial_response

    def run(
        self,
        agent: Agent,
        messages: List,
        context: dict = {},
        debug: bool = False,
        max_turns: int = float("inf"),
        execute_tools: bool = True,
    ) -> Response:
        # Initialize the conversation
        active_agent = agent
        context = copy.deepcopy(context)
        history = copy.deepcopy(messages)
        init_len = len(messages)

        while len(history) - init_len < max_turns and active_agent:
            # Get completion with current history and agent
            completion = self.get_chat_completion(
                agent=active_agent,
                history=history,
                context=context,
                debug=debug,
            )
            message = completion.choices[0].message
            debug_print(debug, "Received completion:", message)
            message.sender = active_agent.name
            history.append(
                json.loads(message.model_dump_json())
            )  # Convert OpenAI types to standard Python types

            # Check if there are tool calls to execute
            if not message.tool_calls or not execute_tools:
                debug_print(debug, "Ending turn.")
                break
            
            # Handle function calls, update context, and switch agents if necessary
            partial_response = self.handle_tool_calls(message.tool_calls, active_agent.functions, context, debug)
            history.extend(partial_response.messages)
            context.update(partial_response.context)
            
            # Switch to the new agent if necessary
            if partial_response.agent:
                active_agent = partial_response.agent
                debug_print(debug, f"Switching to new agent: {active_agent.name}")

        # Return the final response
        return Response(
            messages=history[init_len:],
            agent=active_agent,
            context=context,
        )
