import os
import base64
import zlib
import json
from typing import List, Dict
from pinecone import Pinecone
from openai import OpenAI

# Initialize Pinecone client
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    Get the embedding of a text using OpenAI's API.
    """
    client = OpenAI(api_key=os.environ['OPENAI_API_KEY'])
    response = client.embeddings.create(
        input=text,
        model=model
    )
    embedding = response.data[0].embedding
    return embedding


def fetch_nos_text(current_role: str) -> List[str]:
    """
    Fetch NOS text from Pinecone based on current role.
    
    """
    query_vector = get_embedding(f"Occupation relevant to {current_role}")  

    # Query the Pinecone index
    ## Get NOS ID
    index = pinecone_client.Index('test-nos')  
    nos_searched_from_relavant_occupations = index.query(
            vector=query_vector,
            top_k=1,
            include_metadata=True,
            filter={"type":"Developed by"},

        )
    nos_id = nos_searched_from_relavant_occupations['matches'][0]['metadata']['nos_id']


    ## Get NOS sections
    nos_sections_from_nos_id = index.query(
            vector=query_vector,
            top_k=2,
            include_metadata=True,
            filter={"nos_id": nos_id,  
                    "$or": [
            {"type": "Performance criteria"},
            {"type": "Knowledge and understanding"}]
            })

    matching_nos_doc = "\n".join([match['metadata']['text'] for match in nos_sections_from_nos_id['matches']])
    return matching_nos_doc, nos_id

def decompress_text(compressed_str):
    """Decompress text from base64 string back to original format."""
    if not compressed_str:
        return ''
    compressed_bytes = base64.b64decode(compressed_str.encode('utf-8'))
    decompressed = zlib.decompress(compressed_bytes)
    return json.loads(decompressed.decode('utf-8'))

def fetch_ofqual_text(query: str) -> List[str]:
    """
    Fetch qualification text from Ofqual index based on search query.
    
    Args:
        query (str): Search query text
        
    Returns:
        tuple[str, str]: Tuple containing (text, markscheme) from the qualification
    """
    query_vector = get_embedding(query)

    # Query the Pinecone index having unitwise data ingested
    index = pinecone_client.Index('sales-ofqual') ## TODO: Change to ofqual index
    
    # Search for relevant qualifications without filters
    results = index.query(
        vector=query_vector,
        top_k=1,
        include_metadata=True
    )

    text = decompress_text(results['matches'][0]['metadata']['text'])
    markscheme = decompress_text(results['matches'][0]['metadata']['markscheme'])
    
    return text, markscheme
