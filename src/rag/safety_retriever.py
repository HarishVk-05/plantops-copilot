from src.rag.search_vector_index import search_documents

def retrieve_safety_documents(query: str, 
                              top_k: int = 5,
                              document_category="safety"):

    return search_documents(
        query=query,
        top_k=top_k,
        document_category=document_category
        )
