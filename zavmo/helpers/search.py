import os
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

def fetch_nos_text(industry: str, current_role: str) -> List[str]:
    """
    Fetch NOS text from Pinecone based on industry and current role.
    
    """
    query_vector = get_embedding(f"Occupation relevant to {current_role}")  

    # Query the Pinecone index
    index = pinecone_client.Index('test-nos')  
    response = index.query(
        vector=query_vector,
        top_k=10,
        include_metadata=True,
        filter={"industry": industry}
    )

    # Extract and return the NOS texts from the response
    nos_texts = [match['metadata']['text'] for match in response.matches]
    return nos_texts
