from src.agents.tools.retrieval_tool import retrieve_knowledge

def knowledge_node(state):

    docs = retrieve_knowledge(
        state["user_query"]
    )

    return {
        **state,
        "retrieved_docs": docs
    }