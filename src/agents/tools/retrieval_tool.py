from src.rag.retriever import PlantOpsRetriever

retriever = PlantOpsRetriever()

def retrieve_knowledge(query: str):
    return retriever.search(
        query=query,
        top_k=5
    )