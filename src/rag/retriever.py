from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parents[2]
VECTOR_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

DEFAULT_COLLECTION_NAME = "plantops_documents"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

class PlantOpsRetriever:
    def __init__(
            self,
            collection_name: str = DEFAULT_COLLECTION_NAME,
            embedding_model: str = DEFAULT_EMBEDDING_MODEL
    ) -> None:
        self.collection_name = collection_name
        self.embedding_model = embedding_model

        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=self.embedding_model
        )

        self.client = chromadb.PersistentClient(path=str(VECTOR_DIR))

        self.collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function
        )
    
    def search(
            self,
            query: str,
            top_k: int = 5,
            source_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_filter = None

        if source_type:
            where_filter = {"source_type": source_type}
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"]
        )

        output = []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for item_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances
        ):
            similarity = max(0.0, 1.0 - float(distance))

            output.append(
                {
                    "id": item_id,
                    "text": document,
                    "metadata": metadata,
                    "distance": float(distance),
                    "similarity": round(similarity, 4),
                    "citation": self._format_citation(metadata)
                }
            )
        
        return output
    
    @staticmethod
    def _format_citation(metadata: Dict[str, Any]) -> str:
        source_file = metadata.get("source_file", "unknown")
        heading = metadata.get("heading", "unknown section")
        return f"{source_file} | {heading}"

if __name__ == "__main__":
    retriever = PlantOpsRetriever()

    query = "PKG-L3 high vibration motor current overheating"

    results = retriever.search(query=query, top_k=3)

    for result in results:
        print("=" * 80)
        print(result["citation"])
        print(f"Similarity: {result['similarity']}")
        print(result["text"])
