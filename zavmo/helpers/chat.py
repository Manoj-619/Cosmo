import os
import re
import json
import random
import tiktoken
import numpy as np
import openai
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv(override=True)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_prompt(prompt_file, prompt_dir="assets/prompts"):
    """Load a prompt from a file.

    Args:
        prompt_file (str): Name of the prompt file.
        prompt_dir (str, optional): Path to the prompt directory. Defaults to 'assets/prompts'.

    Returns:
        str: prompt
    """
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

# def make_tool_call(tools, messages, model='gpt-4o-mini', **kwargs):
#     """Make a tool call with OpenAI API."""
#     response = client.chat.completions.create(
#         model=model,
#         messages=messages,
#         tools=[tool.openai_schema() for tool in tools],
#         tool_choice="required",
#         stream=False,
#         **kwargs
#     )
#     tool_calls = response.choices[0].message.tool_calls
#     tool_funcs = []
#     for tool_call in tool_calls:
#         try:
#             tool_data = json.loads(tool_call.function.json())
#             tool_args = json.loads(tool_data['arguments'])        
#             tool_name = tool_data['name']
#             tool_func = getattr(tools,tool_name)
#             tool_func = tool_func.from_arguments(tool_args)
#             tool_funcs.append(tool_func)
#         except Exception as e:
#             print(e)
#             print(tool_args)
#     return [tool.execute() for tool in tool_funcs]


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