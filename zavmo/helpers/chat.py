import os
import logging
import tiktoken
import openai
import anthropic
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Union, List
import functools
load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


logger = logging.getLogger(__name__)


def log_tokens(func):
    """Log the token usage of the decorated function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if hasattr(result, 'usage'):
            usage = result.usage.to_dict()
            logger.info(f"Function {func.__name__} token usage:")
            logger.info(f"  Completion tokens: {usage['completion_tokens']}")
            logger.info(f"  Prompt tokens: {usage['prompt_tokens']}")
            logger.info(f"  Total tokens: {usage['total_tokens']}")
            if 'completion_tokens_details' in usage:
                logger.info(f"  Reasoning tokens: {usage['completion_tokens_details'].get('reasoning_tokens', 'N/A')}")
            if 'prompt_tokens_details' in usage:
                logger.info(f"  Cached tokens: {usage['prompt_tokens_details'].get('cached_tokens', 'N/A')}")
        return result
    return wrapper

def get_prompt(prompt_file, prompt_dir="assets/prompts"):
    """Load a prompt from a file.

    Args:
        prompt_file (str): Name of the prompt file.
        prompt_dir (str, optional): Path to the prompt directory. Defaults to 'assets/prompts'.

    Returns:
        str: prompt
    """
    if not prompt_file.endswith('.md'):
        prompt_file += '.md'
        
    prompt_path = os.path.join(prompt_dir, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    return prompt

def count_tokens_str(doc, model="cl100k_base"):
    """Count tokens in a string.

    Args:
        doc (str): String to count tokens for.
    Returns:
        int: number of tokens in the string

    """
    encoder = tiktoken.get_encoding(model)  # BPE encoder # type: ignore
    return len(encoder.encode(doc, disallowed_special=()))

def count_tokens(messages):
    """
    Counts tokens in a list of messages.
    Source: https://platform.openai.com/docs/guides/chat/introduction

    Args:
        messages (list): list of messages to count tokens for
    Returns:
        int: number of tokens in the list of messages
    """
    num_tokens = 0
    for message in messages:
        # every message follows <im_start>{role/name}\n{content}<im_end>\n
        num_tokens += 4
        for key, value in message.items():
            num_tokens += count_tokens_str(value)
            if key == "name":  # if there's a name, the role is omitted
                num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with <im_start>assistant
    return num_tokens

def get_openai_completion(messages, model="gpt-4o-mini", **kwargs):
    """Completes the chat given a list of messages.
            
    Args:
        messages (list): list of messages to complete the chat with
        **kwargs: additional arguments to pass to the OpenAI API, such as
            temperature, max_tokens, etc.
    Returns:
        str: the chat completion
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        **kwargs,
    )        
    return response.choices[0].message.content

def get_claude_response(sys_mssg,messages,model="claude-3-opus-20240229"):
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model=model,
        max_tokens=1024,
        system=sys_mssg,
        messages=messages
    )
    return message.content[0].text

### TODO: Create a separate function for making tool calls, with automatic tool choice and parallel execution


@log_tokens
def force_tool_call(tools: Union[List[BaseModel], BaseModel],
                   messages, 
                   model='gpt-4o-mini', 
                   tool_choice='required', # NOTE: Forcing tool to be called here
                   parallel_tool_calls=True,
                   **kwargs
                   ):
    """
    Make tool calls and return the parsed response.
    # IMPORTANT: Always specify these kwargs: `tool_choice`, and `parallel_tool_calls`
    """
    is_single_tool = not isinstance(tools, list)
    tools_list = [tools] if is_single_tool else tools

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[openai.pydantic_function_tool(t) for t in tools_list],
        tool_choice=tool_choice,
        parallel_tool_calls=parallel_tool_calls,
        **kwargs
    )    
    message    = response.choices[0].message
    tool_calls = response.choices[0].message.tool_calls
    parsed_tools = []
    for tool_call in tool_calls:
        tool_call_func = tool_call.function
        tool_name, tool_args = tool_call_func.name, tool_call_func.arguments
        # Get the pydantic model from the tools list that has the name of the tool call
        tool_model = next((tool for tool in tools_list if tool.__name__ == tool_name), None)
        try:
            parsed_tool = tool_model.model_validate_json(tool_args)
            parsed_tools.append(parsed_tool)
        except Exception as e:
            logger.debug(f"Error parsing tool call: {e}")
            # Log the error, but don't raise it
    
    return parsed_tools[0] if is_single_tool else parsed_tools
        
 

def make_structured_call(tool:BaseModel, messages, model='gpt-4o-mini', **kwargs):
    """Make a structured output call with OpenAI API, with pydantic models."""
    try:
        completion = client.beta.chat.completions.parse(
            model=model,
            messages=messages,
            response_format=tool,
            **kwargs
        )
        message = completion.choices[0].message
        if message.parsed:
            return message.parsed
        elif message.refusal:
            print(message.refusal)
            return None
    except Exception as e:
        print(e)
        return None



def create_message_payload(user_content=None, system_message=None, messages=[], max_tokens=20000):  # IMPORTANT
    """Create a message payload for the conversation.
    
    Args:
        user_content (str, optional): the user's message content. Defaults to None.
        system_message (dict): system message {'role': 'system', 'content': 'message'}
        messages List[dict]: list of messages to add to the message history
        max_tokens (int, optional): Maximum number of tokens to limit the message history to. Defaults to 20000.
        
    Returns:
        List[dict]: message history
    """
    message_history = []
    total_tokens = 0
    system_token_count = count_tokens([system_message])
    max_tokens        -= system_token_count  # subtract the system prompt tokens

    if user_content:
        messages = messages + [{'role': 'user', 'content': user_content}]

    for message in reversed(messages):
        message_tokens = count_tokens([message])
        if total_tokens + message_tokens <= max_tokens:
            total_tokens += message_tokens
            # This inserts the message at the beginning of the list
            message_history.insert(0, message)
        else:
            break
    
    if system_message:
        message_history.insert(0, system_message)
    
    return message_history

def log_tokens(func: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        response = func(*args, **kwargs)
        
        if hasattr(response, 'usage'):
            print(f"Input tokens: {response.usage.prompt_tokens}")
            print(f"Output tokens: {response.usage.completion_tokens}")
            print(f"Total tokens: {response.usage.total_tokens}")
        else:
            print("No usage information available in the response.")
        
        return response
    return wrapper


def summarize_stage_data(stage_data, stage_name):
    """
    Get a markdown summary of the stage data.
    """
    summary = f"**{stage_name.title()}**\n\n"# if empty, say so 
    if not stage_data:
        summary += f"No data available for {stage_name} yet."
    else:
        for key, value in stage_data.items():
            summary += f"**{key}**: {value}\n"
    return summary.strip()

def summarize_profile(profile_data):
    """
    Get a markdown summary of the profile data.
    """
    summary = f"**Learner's Profile**\n\n"
    summary += f"The learner is at the **{profile_data['stage_name']}** stage.\n\n"
    stage_names = profile_data['stage_data'].keys()
    for stage_name in stage_names:
        summary  += summarize_stage_data(profile_data['stage_data'][stage_name], stage_name)
    return summary.strip()

def summarize_history(history):
    """
    Summarize the history of the conversation.
    """
    summary = f"**Conversation History**\n\n"
    for message in history:
        role = 'Zavmo' if message['role'] == 'assistant' else 'Learner'
        summary += f"**{role}**: {message['content']}\n\n"
    return summary.strip()