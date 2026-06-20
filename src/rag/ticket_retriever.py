from src.rag.search_vector_index import search_documents

def retrieve_historical_tickets(
        query: str,
        top_k: int = 5,
        document_category = "historical_ticket"
):
    return search_documents(
        query=query,
        top_k=top_k,
        document_category=document_category
    )