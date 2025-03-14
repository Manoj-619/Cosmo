from dotenv import load_dotenv
load_dotenv(override=True)

import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_batch_list(texts):
    batches = []
    current_batch = []
    current_batch_length = 0
    # Set a conservative max length per batch (characters)
    # OpenAI's text-embedding-3-small has an 8192 token limit
    # A rough estimate is ~4 characters per token, so ~32,000 chars should be safe
    max_batch_length = 30000
    
    for text in texts:
        text_length = len(text)
        
        # If a single text is too long, truncate it
        if text_length > max_batch_length:
            text = text[:max_batch_length]
            text_length = max_batch_length
            
        # If adding this text would exceed the batch limit, start a new batch
        if current_batch_length + text_length > max_batch_length and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_batch_length = 0
            
        # Add the text to the current batch
        current_batch.append(text)
        current_batch_length += text_length
        
    # Add the last batch if it's not empty
    if current_batch:
        batches.append(current_batch)
        
    return batches

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
    text_batches = get_batch_list(texts)
    print(f"total batches: {len(text_batches)}")
    embeddings = []
    for text_batch in text_batches:
        response = client.embeddings.create(
            model=model,
            input=text_batch,
            **kwargs,
        )
        embeddings += [r.embedding for r in response.data]
    return embeddings


def get_parent_ssa(sub_ssa):
    """
    Maps a sub-SSA to its parent SSA category.
    
    Args:
        sub_ssa (str): The sub-SSA to map
        
    Returns:
        str: The parent SSA category, or None if not found
    """

    SSA_MAPPING = json.load(open(os.path.join("zavmo/classification/data", "ofqual_SSAs.json")))
    sub_ssa_to_parent = {
        sub_ssa: parent_ssa
        for item in SSA_MAPPING
        for parent_ssa, sub_ssas in item.items()
        for sub_ssa in sub_ssas
    }
    return sub_ssa_to_parent.get(sub_ssa)
