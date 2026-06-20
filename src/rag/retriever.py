from typing import Any, Dict, List, Optional

from src.rag.search_vector_index import (
    DEFAULT_COLLECTION_NAME,
    DEFAULT_EMBEDDING_MODEL,
    search_documents
)

class PlantOpsRetriever:

    def __init__(self,
                 collection_name: str = DEFAULT_COLLECTION_NAME,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL
                 ) -> None:
        self.collection_name = collection_name
        self.embedding_model = embedding_model
    
    def search(self,
               query: str,
               top_k: int = 5,
               source_type: Optional[str] = None
               ) -> List[Dict[str, Any]]:
        return search_documents(
            query=query,
            top_k=top_k,
            source_type=source_type,
            collection_name=self.collection_name,
            embedding_model=self.embedding_model
        )
        