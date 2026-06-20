from src.rag.search_vector_index import search_documents

def _deduplicate_documents(documents):
    unique_documents = []
    seen_ids = set()

    for document in documents:
        document_id = document.get("id")

        if document_id in seen_ids:
            continue

        seen_ids.add(document_id)
        unique_documents.append(document)
    
    return unique_documents

def _expand_historical_tickets(
    seed_tickets,
    machine_id
):
    expanded_tickets = list(seed_tickets)

    relevant_ticket_files = list(
        dict.fromkeys(
            ticket.get(
                "metadata",
                {}
            ).get("source_file")
            for ticket in seed_tickets
            if ticket.get(
                "metadata",
                {}
            ).get("source_file")
        )
    )

    required_headings = {
        "symptoms",
        "root cause",
        "action taken",
        "parts used",
        "tools used",
        "skills used",
        "verification result",
        "work outcome",
        "duration"
    }

    for source_file in relevant_ticket_files:
        ticket_sections = search_documents(
            query="historical maintenance ticket",
            top_k=50,
            document_category="historical_ticket",
            source_file=source_file,
            machine_id=machine_id
        )

        for section in ticket_sections:
            heading = section.get(
                "metadata",
                {}
            ).get(
                "heading",
                ""
            ).strip().lower()

            if heading in required_headings:
                expanded_tickets.append(section)

    return _deduplicate_documents(
        expanded_tickets
    )

def retrieve_knowledge(
        query: str,
        machine_id: str,
        maintenance_top_k: int = 5,
        ticket_top_k: int = 3
):
    maintenance_docs = search_documents(
        query=query,
        top_k=maintenance_top_k,
        document_category="maintenance",
        machine_id=machine_id
    )

    seed_tickets = search_documents(
        query=query,
        top_k=ticket_top_k,
        document_category="historical_ticket",
        machine_id=machine_id
    )

    historical_tickets = _expand_historical_tickets(
        seed_tickets=seed_tickets,
        machine_id=machine_id
    )

    return maintenance_docs + historical_tickets