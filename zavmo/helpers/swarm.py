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
from helpers.chat import filter_history, validate_message_history
from helpers._types import Agent, Tool, Result, Response, AgentFunction, function_to_json
from typing import List, Dict, Any
from collections import defaultdict

redis_client = get_redis_connection()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def fetch_agent_response(agent: Agent, history: List, context: Dict) -> ChatCompletionMessage:
    """Fetches the response from an agent."""
    context      = defaultdict(str, context)
    instructions = agent.instructions    
    
    # Start with system message
    messages     = [{"role": "system", "content": instructions}] + history
    tools        = [function_to_json(f) for f in agent.functions]

    create_params = {
        "model": agent.model,
        "messages": messages,
        "tools": tools or None,
        "tool_choice": agent.tool_choice if tools else "auto"
    }
    logging.info(f"\n\nLogging from - fetch_agent_response\nmessages passed:\n{messages}\n\n")
    if tools:
        create_params["parallel_tool_calls"] = agent.parallel_tool_calls
    logging.debug(f"Messages being sent to OpenAI API: {json.dumps(messages, indent=2)}")
    return openai_client.chat.completions.create(**create_params)
def execute_tool_calls(
    tool_calls: List[ChatCompletionMessageToolCall],
    functions: List[AgentFunction],
    context: Dict
) -> Response:
    function_map = {f.__name__: f for f in functions}
    partial_response = Response(messages=[], context=copy.deepcopy(context))
    tool_call = tool_calls[0]
    name = tool_call.function.name
    # Handle missing tool case
    args = json.loads(tool_call.function.arguments)
    func = function_map[name]
    result = None
    try:
        # Execute the function or tool
        if inspect.isclass(func) and issubclass(func, Tool):
            tool_instance = func(**args)
            raw_result = tool_instance.execute(context=context)
        else:
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
                agent=raw_result
            )
        else:
            result = Result(value=str(raw_result), context=context)
        # Only append the tool response message
        tool_response = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "tool_name": name,
            "content": str(result.value)  # Don't use json.dumps here
        }
        partial_response.messages.append(tool_response)
    except Exception as e:
        logging.error(f"Error executing tool {name}: {str(e)}")
        tool_response = {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": name,
            "content": f"Error executing tool: {str(e)}"
        }
        partial_response.messages.append(tool_response)

    logging.info(f"\n\nLogging from - execute_tool_calls\nPartial Response\n{partial_response}\n\n")

    # Update context and agent if necessary
    if result and result.context:
        partial_response.context.update(result.context)
        
    if result and result.agent:
        partial_response.agent = result.agent
        partial_response.context['stage'] = result.agent.id
    return partial_response

def run_step(agent: Agent, messages: List, context: Dict = {}, max_turns: int = 5) -> Response:
    active_agent = agent
    history = copy.deepcopy(messages)
    init_length = len(history)
    context = copy.deepcopy(context)
    turns = 0

    while active_agent and turns < max_turns:
        logging.info(f"\n\nLogging from - run_step\nPassing history\n{history}\n")
        logging.info(f"Running step {turns} with agent {active_agent.name}")
        completion = fetch_agent_response(active_agent, history, context=context)
        message = completion.choices[0].message
        message.sender = active_agent.name
        logging.info(f"Logging from - run_step\nCompletion message: {message}")
        # Convert the message to dict and add to history
        message_dict = json.loads(message.model_dump_json())
        
        # If no tool calls, we're done with this turn
        if not message.tool_calls:
            history.append(message_dict)
            break

        # Execute tool calls and get responses
        partial_response = execute_tool_calls(message.tool_calls, active_agent.functions, context=context) 

        # Append assistant message and tool responses together
        history.append(message_dict)
        if partial_response.messages:
            history.extend(partial_response.messages)

        # Update context
        context.update(partial_response.context)

        # Update active_agent if a new agent is returned
        if partial_response.agent and partial_response.agent != active_agent:
            active_agent = partial_response.agent
            context['stage'] = active_agent.id
            logging.info(f"Stage changed to: {active_agent.id}")
            break  # Break after agent transfer to prevent duplicate messages

        turns += 1
    
    # Clean up history and ensure final context has correct stage
    context['stage'] = active_agent.id
    
    return Response(
        messages=history,
        agent=active_agent,
        context=context,
    )
