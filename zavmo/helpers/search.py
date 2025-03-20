import os
import base64
import zlib
import json
from typing import List, Dict
from pinecone import Pinecone
from neomodel import config, db
from openai import OpenAI
import ast

# Initialize Pinecone client
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize Neo4j client
config.DATABASE_URL =  f'bolt://{os.getenv("NEO4J_USERNAME")}:{os.getenv("NEO4J_PASSWORD")}@{os.getenv("NEO4J_URI")}'

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


def retrieve_nos_from_pinecone(query: str) -> List[str]:
    """
    Fetch NOS text from Pinecone based on current role.
    
    """
    query_vector = get_embedding(query)  

    # Query the Pinecone index
    ## Get NOS ID
    index = pinecone_client.Index('nos-202501')  ## previous index was 'test-nos'
    nos_docs = index.query(
            vector=query_vector,
            top_k=5,
            include_metadata=True
        )
    nos_ids = [match['metadata']['nos_id'] for match in nos_docs['matches']]
    relevant_nos_docs_combined = "\n".join([match['metadata']['text'] for match in nos_docs['matches']])
    return relevant_nos_docs_combined, nos_ids

def decompress_text(compressed_str):
    """Decompress text from base64 string back to original format."""
    if not compressed_str:
        return ''
    compressed_bytes = base64.b64decode(compressed_str.encode('utf-8'))
    decompressed = zlib.decompress(compressed_bytes)
    return json.loads(decompressed.decode('utf-8'))

def retrieve_ofquals_from_pinecone(query: str) -> List[str]:
    """
    Fetch qualification text from Ofqual index based on search query.
    
    Args:
        query (str): Search query text
        
    Returns:
        tuple[str, str]: Tuple containing (text, markscheme) from the qualification
    """
    query_vector = get_embedding(query)

    # Query the Pinecone index having unitwise data ingested
    index = pinecone_client.Index('centrica-ofqual') ## TODO: Change to ofqual index
    
    # Search for relevant qualifications without filters
    results = index.query(
        vector=query_vector,
        top_k=1,
        include_metadata=True
    )

    text = decompress_text(results['matches'][0]['metadata']['text'])
    markscheme = ast.literal_eval(decompress_text(results['matches'][0]['metadata']['markscheme']))
    
    return text, markscheme

def retrieve_ofquals_from_neo4j(nos_id: str) -> List[str]:
    """Get the ofquals mapped to a nos_id"""
    query = """
    MATCH (n:NOSNode {nos_id: $nos_id})-[:MAPS_TO]->(o:OFQUALUnit)
    RETURN o.unit_id AS unit_id, o.unit_title AS unit_title, 
    o.overview AS overview, 
    o.level AS level, 
    o.qualification_type AS qualification_type, 
    o.qualification_level AS qualification_level, 
    o.awarding_organisation AS awarding_organisation, 
    o.total_credits AS total_credits, 
    o.guided_learning_hours AS guided_learning_hours, 
    o.total_qualification_time AS total_qualification_time, 
    o.unit_learning_outcomes AS learning_outcomes, 
    o.assessment_methods AS assessment_methods,
    o.ofqual_id as ofqual_id,
    o.markscheme AS marksscheme
    """
    
    # Execute the query
    results, _ = db.cypher_query(query, {'nos_id': nos_id})
    
    connected_ofqual_units = [{'unit_id': row[0], 'unit_title': row[1], 'overview': row[2], 'level': row[3], 
                        'qualification_type': row[4], 'qualification_level': row[5], 'awarding_organisation': row[6], 
                        'total_credits': row[7], 'guided_learning_hours': row[8], 'total_qualification_time': row[9], 
                        'learning_outcomes': row[10], 'assessment_methods': row[11], 'ofqual_id': row[12], 'marksscheme': json.loads(row[13])} for row in results]
    
    return connected_ofqual_units

def retrieve_nos_from_neo4j(query,index_name='nos_vector_index', top_k=5):
    """Retrieve NOS from Neo4j"""
    query_embedding = get_embedding(query)
    cypher_query = f"""
        CALL db.index.vector.queryNodes('{index_name}', $top_k, $query_embedding) 
            YIELD node, score
            RETURN 
                node.nos_id AS nos_id, 
                node.title AS title, 
                node.performance_criteria AS performance_criteria,
                node.knowledge_understanding AS knowledge_understanding,
                score
            ORDER BY score DESC
        """

    result, columns = db.cypher_query(cypher_query, {"query_embedding": query_embedding, "top_k": top_k})
        
    formatted_results = [dict(zip(columns, row)) for row in result]
        
    return formatted_results[:top_k]