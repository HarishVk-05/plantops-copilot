from functools import lru_cache

import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = Path(__file__).resolve().parents[2]

VECTOR_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

DEFAULT_COLLECTION_NAME = "plantops_documents"
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"

@lru_cache(maxsize=4)
def get_collection(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
):
    try:
        embedding_function = (
            SentenceTransformerEmbeddingFunction(model_name=embedding_model)
        )

        client = chromadb.PersistentClient(path=str(VECTOR_DIR))

        return client.get_collection(
            name=collection_name,
            embedding_function=embedding_function
        )
    
    except Exception as exc:
        raise RuntimeError(
            "Unable to load the ChromaDB collection or "
            "embedding model. Run:\n"
            "python -m src.rag.build_vector_index --reset"
        ) from exc

def search_documents(
        query: str,
        top_k: int = 5,
        source_type: Optional[str] = None,
        document_category = None,
        source_file: Optional[str] = None,
        machine_id: Optional[str] = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        embedding_model: str = DEFAULT_EMBEDDING_MODEL
) -> List[Dict[str, Any]]:
    
    if not query or not query.strip():
        raise ValueError(
            "The retrieval query cannot be empty."
        )
    
    if top_k <= 0:
        raise ValueError(
            "top_k must be greater than zero."
        )
    
    collection = get_collection(
        collection_name = collection_name,
        embedding_model=embedding_model
    )
    
    conditions = []

    if source_type:
        conditions.append(
            {"source_type": source_type}
        )
    
    if document_category:
        conditions.append(
            {"document_category": document_category}
        )
    
    if machine_id:
        conditions.append(
            {"machine_id": machine_id}
        )
    
    if source_file:
        conditions.append(
            {"source_file": source_file}
        )
    
    if len(conditions) == 1:
        where_clause = conditions[0]
    elif len(conditions) > 1:
        where_clause = {
            "$and": conditions
        }
    else:
        where_clause = None

    try:
        document_count = collection.count()

        if document_count == 0:
            return []
        
        results = collection.query(
            query_texts = [query.strip()],
            n_results= min(top_k, document_count),
            where= where_clause,
            include=[
                "documents",
                "metadatas",
                "distances"
            ]
        )
    except Exception as exc:
        raise RuntimeError(
            "Document retrieval failed. Check the "
            "ChromaDB index and embedding model."
        ) from exc

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
                "similarity": round(similarity, 4)
            }
        )
    
    return output

def print_results(results: List[Dict[str, Any]]) -> None:
    if not results:
        print("No matching documents found.")
        return
    
    for index, result in enumerate(results, start=1):
        metadata = result["metadata"]

        print("=" * 80)
        print(f"Result {index}")
        print(f"Similarity: {result['similarity']}")
        print(f"Source file: {metadata.get('source_file')}")
        print(f"Source type: {metadata.get('source_type')}")
        print(f"Document title: {metadata.get('document_title')}")
        print(f"Heading: {metadata.get('heading')}")
        print(f"Path: {metadata.get('source_path')}")
        print("-" * 80)
        print(result['text'])
        print()
    

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search PlantOps Copilot ChromaDB vector index."
    )

    parser.add_argument(
        "query",
        type = str,
        help = "Search query."
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of search results."
    )

    parser.add_argument(
        "--source-type",
        choices=["manual", "maintenance_ticket"],
        default=None,
        help="optional source filter."
    )

    parser.add_argument(
        "--collection-name",
        default=DEFAULT_COLLECTION_NAME,
        help="ChromaDB collection name."
    )

    parser.add_argument(
        "--embedding-model",
        default=DEFAULT_EMBEDDING_MODEL,
        help="SentenceTransformer embedding model name."
    )

    args = parser.parse_args()

    results = search_documents(
        query=args.query,
        top_k=args.top_k,
        source_type=args.source_type,
        collection_name=args.collection_name,
        embedding_model=args.embedding_model
    )

    print_results(results)

if __name__ == "__main__":
    main()
    