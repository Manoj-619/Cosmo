import os
import logging
import tiktoken
import openai
import anthropic
from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Union, List, Any, Callable, Literal
import functools
from helpers.utils import batch_list
import requests
from django.core.cache import cache


load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


logger = logging.getLogger(__name__)

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


def get_prompt(prompt_file, context={}, prompt_dir="assets/prompts"):
    """Load a prompt from a file and format it with a context.

    Args:
        prompt_file (str): Name of the prompt file.
        context (dict, optional): Context to format the prompt with. Defaults to {}.
        prompt_dir (str, optional): Path to the prompt directory. Defaults to 'assets/prompts'.

    Returns:
        str: prompt
    """
    # if extension is not .md, add it
    if not prompt_file.endswith(".md"):
        prompt_file += ".md"
    prompt_path = os.path.join(prompt_dir, prompt_file)
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt = f.read()
    if context:
        prompt = prompt.format(**context)
    return prompt

def count_tokens_str(doc, model="cl100k_base"):
    """Count tokens in a string.

    Args:
        doc (str): String to count tokens for.
    Returns:
        int: number of tokens in the string
    """
    if doc is None:
        return 0
    encoder = tiktoken.get_encoding(model)  # BPE encoder # type: ignore
    return len(encoder.encode(str(doc), disallowed_special=()))

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
            if value is not None:  # Only count tokens if value is not None
                num_tokens += count_tokens_str(value)
                if key == "name":  # if there's a name, the role is omitted
                    num_tokens += -1  # role is always required and always 1 token
    num_tokens += 2  # every reply is primed with 
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

def filter_history(history, max_tokens=84000):
    """Filter the history to a maximum number of tokens."""
    message_history = []
    total_tokens = 0

    for message in reversed(history):
        # Skip messages with None or empty content unless it's a tool call message
        if message.get('tool_call_id') or message.get('tool_calls'):
            pass
        elif not message.get('content'):
            continue

        message_tokens = count_tokens([message])
        if total_tokens + message_tokens <= max_tokens:
            total_tokens += message_tokens
            message_history.insert(0, message)

    # Check if the first message is a tool call message and remove it if so
    if message_history and message_history[0].get('role') == 'tool':
        message_history.pop(0)
    return message_history

def validate_message_history(filtered_messages):
    """
    Validates that every assistant message with tool_calls has a corresponding tool response.
    
    Args:
        filtered_messages (list): The list of filtered messages to test.

    Returns:
        bool: True if all tool_calls have valid responses, False otherwise.
    """
    # Map of tool_call_ids to responses
    tool_responses = {
        msg.get('tool_call_id'): msg for msg in filtered_messages if msg.get('role') == 'tool'
    }
    
    # Iterate through messages to check assistant tool calls
    for msg in filtered_messages:
        if msg.get('role') == 'assistant' and msg.get('tool_calls'):
            for tool_call in msg['tool_calls']:
                tool_call_id = tool_call.get('id')
                if tool_call_id not in tool_responses:
                    print(f"Missing response for tool_call_id: {tool_call_id}")
                    return False
    return True


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


def summarize_history(history):
    """
    Summarize the history of the conversation.
    """
    summary = f"**Conversation History**\n\n"
    for message in history:
        if message['role'] == 'assistant':  
            role = 'Zavmo'
        elif message['role'] == 'user':
            role = 'Learner'
        else:
            continue
        summary += f"**{role}**: {message['content']}\n\n"
    return summary.strip()


def validate_message_history(message_history):
    """
    Ensure that assistant messages with tool_calls are immediately followed by tool responses.
    """
    valid_history = []
    skip_next = False
    for i, msg in enumerate(message_history):
        if skip_next:
            skip_next = False
            continue
        valid_history.append(msg)
        if msg['role'] == 'assistant' and 'tool_calls' in msg:
            if i + 1 < len(message_history) and message_history[i + 1]['role'] == 'tool':
                valid_history.append(message_history[i + 1])
                skip_next = True
            else:
                # Incomplete tool response, remove the assistant message
                valid_history.pop()
        elif msg['role'] == 'user':
            valid_history.append(msg)
    return valid_history



def get_openai_client(service: Literal["openai", "azure"] = "openai", **kwargs):
    """
    Get an OpenAI or Azure OpenAI client.
    
    Args:
        service (Literal["openai", "azure"]): The service to use. Defaults to "openai".
        **kwargs: Additional arguments to pass to the client constructor.
    
    Returns:
        OpenAI or AzureOpenAI: The appropriate client instance.
    
    Raises:
        NotImplementedError: If the service is not supported.
    """
    if service == "openai":
        openai_client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            **kwargs
        )
    elif service == "azure":
        openai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            **kwargs
        )
    else:
        raise NotImplementedError(f"OpenAI client for {service} not implemented")
    return openai_client


def get_openai_embedding(text, model="text-embedding-3-small", **kwargs):
    """
    Get the embeddings of the text from OpenAI API.

    Args:
        text (str): Text to get embeddings for.
        model (str): Model to use for embeddings.
    Returns:
        list: Embeddings of the text.
    """
    response = client.embeddings.create(
        model=model,
        input=[text],
        **kwargs,
    )
    return response.data[0].embedding


def get_batch_openai_embedding(texts: list, model="text-embedding-3-small", **kwargs):
    """
    Get embeddings of a batch of texts from OpenAI API.

    Args:
        texts (list): List of texts to get embeddings for.
        model (str): Model to use for embeddings.
        **kwargs: Additional arguments to pass to the OpenAI API.
    Returns:
        list[list]: List of embeddings of the texts.
    """
    text_batches = batch_list(texts, 1024) if len(texts) > 1024 else [texts]
    embeddings = []
    for text_batch in text_batches:
        response = client.embeddings.create(
            model=model,
            input=text_batch,
            **kwargs,
        )
        embeddings += [r.embedding for r in response.data]
    return embeddings

def get_operational_service() -> Literal["openai", "azure"]:
    """
    Check which service is operational.
    Returns openai by default if both are operational.
    
    Returns:
        Literal["openai", "azure"]: The operational service to use
    
    Raises:
        RuntimeError: If both services are experiencing outages
    """

    url = "https://status.openai.com/api/v2/summary.json"
    try:

        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        # Find the API component

        for component in data["components"]:
            if component["name"].startswith("Completions"):
                openai_status = component["status"] == "operational"
                if openai_status:
                    return "openai" 
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error checking OpenAI status: {e}")
    return "azure"