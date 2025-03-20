import os
import base64
import zlib
import json
from typing import List, Dict
from pinecone import Pinecone
from neomodel import config, db
from helpers.chat import get_openai_embedding
import ast

# Initialize Pinecone client
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize Neo4j client
config.DATABASE_URL =  f'bolt://{os.getenv("NEO4J_USERNAME")}:{os.getenv("NEO4J_PASSWORD")}@{os.getenv("NEO4J_URI")}'

def retrieve_nos_from_pinecone(query: str) -> List[str]:
    """
    Fetch NOS text from Pinecone based on current role.
    
    """
    query_vector = get_openai_embedding(query)  

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
    query_vector = get_openai_embedding(query)

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

def retrieve_ofquals_from_neo4j(nos_id: str) -> List[Dict[str, Any]]:
    """Get the ofquals mapped to a nos_id"""
    query = """
    MATCH (n:NOSNode {nos_id: $nos_id})-[:MAPS_TO]->(o:OFQUALUnit)
    RETURN o.unit_id AS unit_id, 
           o.unit_uid AS unit_uid,
           o.unit_title AS unit_title, 
           o.overview AS overview, 
           o.qualification_type AS qualification_type, 
           o.qualification_level AS qualification_level, 
           o.awarding_organisation AS awarding_organisation, 
           o.total_credits AS total_credits, 
           o.guided_learning_hours AS guided_learning_hours, 
           o.total_qualification_time AS total_qualification_time, 
           o.unit_learning_outcomes AS learning_outcomes, 
           o.assessment_methods AS assessment_methods,
           o.markscheme AS markscheme
    """
    json_columns = ['markscheme']
    # Execute the query
    results, meta = db.cypher_query(query, {'nos_id': nos_id})
    
    # Process and return results
    ofqual_units = []
    for row in results:
        # Convert row to dictionary using column names from meta
        unit = {}
        for i, col_name in enumerate(meta):
            val = row[i]
            if col_name in json_columns:
                val = [json.loads(x) for x in json.loads(val)]               
            unit[col_name] = val
        ofqual_units.append(unit)    
    return ofqual_units


def retrieve_nos_from_neo4j(query, index_name='nos_vector_index', top_k=5):
    """Retrieve NOS from Neo4j"""
    query_embedding = get_openai_embedding(query)
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