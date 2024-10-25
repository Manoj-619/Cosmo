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
from helpers.chat import filter_history
from helpers._types import Agent, Tool, Result, Response, AgentFunction, function_to_json
from typing import List, Dict, Any
from collections import defaultdict

redis_client = get_redis_connection()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_agent_response(agent: Agent, history: List, context: Dict) -> ChatCompletionMessage:
    """Fetches the response from an agent."""
    context      = defaultdict(str, context)
    instructions = agent.instructions(context) if callable(agent.instructions) else agent.instructions
    messages     = [{"role": "system", "content": instructions}] + filter_history(history, max_tokens=60000)

    tools        = [function_to_json(f) for f in agent.functions]

    create_params = {
        "model": agent.model,
        "messages": messages,
        "tools": tools or None,
        "tool_choice": agent.tool_choice,
    }

    if tools:
        create_params["parallel_tool_calls"] = agent.parallel_tool_calls
    logging.debug(f"Messages being sent to OpenAI API: {json.dumps(messages, indent=2)}")

    return openai_client.chat.completions.create(**create_params)

def execute_tool_calls(tool_calls: List[ChatCompletionMessageToolCall], history: List, functions: List[AgentFunction], context: Dict) -> Response:
    function_map     = {f.__name__: f for f in functions}
    partial_response = Response(messages=history, context=copy.deepcopy(context))

    for tool_call in tool_calls:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        func = function_map.get(name)

        if func is None:
            # Function not found
            partial_response.messages.append({
                "role": "function",
                "name": name,
                "content": f"Error: Tool {name} not found."
            })
            continue

        # Execute the function or tool
        if isinstance(func, Tool) or (inspect.isclass(func) and issubclass(func, Tool)):
            if inspect.isclass(func):
                # Instantiate the Tool with arguments
                tool_instance = func(**args)
                raw_result = tool_instance.execute(context=context)
            else:
                raw_result = func.execute(context=context)
        else:
            # Regular function
            if 'context' in inspect.signature(func).parameters:
                raw_result = func(**args, context=context)
            else:
                raw_result = func(**args)

        # Process the result
        if isinstance(raw_result, Result):
            result = raw_result
            
        elif isinstance(raw_result, Agent):
            result = Result(
                value=f"Successfully transferred to {raw_result.name}.",
                context=context,
                agent=raw_result,
            )
        else:
            result = Result(value=str(raw_result), context=context)

        # Append the function response message
        partial_response.messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,            
            "name": name,
            "content": json.dumps(result.value),            
        })
        
    if result.agent:
        partial_response.agent = result.agent
    
    partial_response.context.update(result.context)
    partial_response.context['history'] = partial_response.messages

    return partial_response

def run_step(agent: Agent, messages: List, context: Dict = {}, max_turns: int = 5) -> Response:
    active_agent = agent
    history = copy.deepcopy(messages)
    context = copy.deepcopy(context)
    turns = 0

    while active_agent and turns < max_turns:
        logging.info(f"Running step {turns} with agent {active_agent.name}")
        completion = fetch_agent_response(active_agent, history, context=context)
        message = completion.choices[0].message
        message.sender = active_agent.name

        # Convert the message to dict
        message_dict = json.loads(message.model_dump_json())
        history.append(message_dict)
        
        if not message.tool_calls:
            break

        # Execute tool calls and get responses
        partial_response = execute_tool_calls(message.tool_calls, history, active_agent.functions, context=context)

        # Update history and context
        history = partial_response.messages
        context.update(partial_response.context)

        # Update active_agent and stage if a new agent is returned
        if partial_response.agent and partial_response.agent != active_agent:
            active_agent = partial_response.agent
            context['stage'] = active_agent.id  # Ensure stage is updated
            logging.info(f"Stage changed to: {active_agent.id}")

        turns += 1

    # Important: Ensure final context has correct stage
    context['stage'] = active_agent.id
    context['history'] = history
    
    return Response(
        messages=history,
        agent=active_agent,
        context=context,
    )
