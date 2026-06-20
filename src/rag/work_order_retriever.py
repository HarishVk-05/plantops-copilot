from src.rag.search_vector_index import search_documents

def retrieve_work_order_documents(
        query: str,
        machine_id: str,
        seed_top_k: int = 4
):
    seed_documents = search_documents(
        query=query,
        top_k=seed_top_k,
        document_category="maintenance",
        machine_id=machine_id
    )

    documents = []
    seen_ids = set()

    def add_documents(results):
        for result in results:
            document_id = result.get("id")

            if document_id in seen_ids:
                continue

            seen_ids.add(document_id)
            documents.append(result)
    add_documents(seed_documents)

    relevant_sources = list(
        dict.fromkeys(
            document.get(
                "metadata",
                {}
            ).get("source_file")
            for document in seed_documents
            if document.get(
                "metadata",
                {}
            ).get("source_file")
        )
    )

    section_queries = [
        "required tools",
        "required skills qualifications competency",
        "verification procedure",
        "acceptance criteria",
        "estimated duration"
    ]

    for source_file in relevant_sources:
        for section_query in section_queries:
            section_documents = search_documents(
                query=section_query,
                top_k=1,
                document_category="maintenance",
                source_file=source_file,
                machine_id=machine_id
            )

            add_documents(section_documents)

    return documents

