import os
import logging
from typing import List, Dict, Union, Optional
from pinecone import Pinecone, ServerlessSpec

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Pinecone client
pinecone_client = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

class PineconeIndex:
    def __init__(self, index_name: str, dimension: int):
        if not index_name:
            raise ValueError("Index name is required")
        
        self.index_name = index_name
        self.dimension = dimension
        self.index = self._create_or_connect_index()

    def _create_or_connect_index(self):
        # Check if the index already exists
        if self.index_name not in pinecone_client.list_indexes().names():
            logger.info(f"Creating index: {self.index_name}")
            pinecone_client.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
        else:
            logger.info(f"Connecting to existing index: {self.index_name}")
        
        return pinecone_client.Index(self.index_name)

    def delete_all(self):
        """Delete all items from the index."""
        logger.info("Deleting all items from the index")
        self.index.delete(delete_all=True)

    def upsert_vectors(self, vectors: List[Dict[str, Union[str, List[float], Dict]]]):
        """Upsert vectors into the index."""
        logger.info(f"Upserting {len(vectors)} vectors into the index")
        self.index.upsert(vectors)

    def search_items(self, query_vectors: List[List[float]], top_k: int = 10) -> List[Dict]:
        """Search the index with query vectors."""
        logger.info(f"Searching the index with {len(query_vectors)} query vectors")
        results = []
        for query_vector in query_vectors:
            response = self.index.query(
                vector=query_vector,
                top_k=top_k,
                include_metadata=True
            )
            results.extend(response.matches)
        return results

    def get_vector_count(self) -> int:
        """Get the number of vectors in the index."""
        stats = self.index.describe_index_stats()
        vector_count = stats['total_vector_count']
        logger.info(f"Total vectors in the index: {vector_count}")
        return vector_count

    def check_vector_dimensions(self, vectors: List[Dict[str, Union[str, List[float], Dict]]], expected_dimension: int):
        """Check and print the dimensions of a few vectors."""
        for i, vector in enumerate(vectors[:5]):  # Check the first 5 vectors
            vector_dimension = len(vector['values'])  # Assuming 'values' is the key for the vector data
            print(f"Vector {i} dimension: {vector_dimension}")
            if vector_dimension != expected_dimension:
                print(f"Warning: Vector {i} has incorrect dimension: {vector_dimension}")

    
    


