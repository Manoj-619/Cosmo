import os
import re
import json
import random
import logging
import tiktoken
import numpy as np
import openai
import anthropic
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


logger = logging.getLogger(__name__)

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

def make_function_call(func, messages=[], model='gpt-4o-mini',force=True, **kwargs):
    """    
    Force function calling with openai.ChatCompletion.create()

    Args:
        - func (dict): function schema
        - messages (list): list of messages to complete the chat with
        - model (str): model to use for completion
    """    
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[func.openai_schema()],
        tool_choice={
            "type": "function",
            "function":{ "name": func.openai_schema()['function']["name"]}
            } if force else "auto",
        stream=False,
        **kwargs
    )
    result = func.from_response(response)
    return result

### TODO: Create a separate function for making tool calls, with automatic tool choice and parallel execution

def force_tool_call(tools,
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
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=[openai.pydantic_function_tool(t) for t in tools],
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
        tool_model = next((tool for tool in tools if tool.__name__ == tool_name), None)
        try:
            parsed_tool = tool_model.model_validate_json(tool_args)
            parsed_tools.append(parsed_tool)
        except Exception as e:
            logger.debug(f"Error parsing tool call: {e}")
            # Log the error, but don't raise it
    return parsed_tools
        
 

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


def split_text_into_sents(text):
    """
        Description: Split context into sentenences by splitting them only at - new lines/ stops/ question marks/ exclamation marks.

        Args:
            text (str): Text to be split into sentences.
        Returns: Array of sentences
    """
    splits = re.split(r'( *[\.\?!\n][\'"\)\]]* *)', text)
    sents, seps = splits[0::2], splits[1::2]
    ### IMPORTANT: Fix for sentences that do not end with a stop
    if len(seps)==0:
        seps = ['']
    sentences = [sents[s] + seps[s] for s in range(len(seps))]
    # There could be an empty sentence at the end
    if sentences[-1] == '':
        sentences = sentences[:-1]
    return np.asarray(sentences)

def get_text_windows(sentences, token_counts, window_size=384, overlap=128):
    """
    Description: Get sliding windows of text.

    Args:
        sentences (list): List of sentences.
        token_counts (list): List of token counts for each sentence.
        window_size (int): Size of the window.
        overlap (int): Overlap between windows.
    Returns: Returns List of text windows.
    """
    # Initialize offset variable
    offset = 0
    L = len(sentences)

    context_windows = []

    # Loop until offset reaches end of sentences
    while offset < L:
        # Get indices of sentences that fit in window_size
        indices = np.argwhere(np.cumsum(token_counts[offset:]) <= window_size)[:, 0]
        
        # If indices array is empty, handle single sentence case
        if len(indices) == 0:
            indices = [0]
        
        # Get start and stop indices
        start_idx, stop_idx = offset, indices[-1] + offset + 1

        # Join sentences to form text window
        text_window = " ".join(sentences[start_idx:stop_idx])
        # Append text window to list
        context_windows.append(text_window)
        
        # Update offset
        token_indices = np.argwhere(np.cumsum(token_counts[offset:]) <= (window_size - overlap))
        if len(token_indices) == 0:
            offset = stop_idx
        else:
            offset += token_indices[-1, 0] + 1

        # Break if stop index reaches or exceeds end of sentences
        if stop_idx >= L:
            break

    return context_windows

def get_sliding_windows(text, window_size, overlap, model='cl100k_base'):
    """
        Description: Split context into sentenences and get sliding windows of text.

        Args:
            text (str): text
            window_size (int): Size of the window.
            overlap (int): Overlap between windows.
        Returns: Returns List of text windows.
    """
    sentences    = split_text_into_sents(text)
    token_counts = [count_tokens_str(s, model=model)  for s in sentences]
    context_windows = get_text_windows(sentences, token_counts, window_size, overlap)
    return context_windows