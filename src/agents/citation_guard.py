def collect_document_citations(documents):
    citations = set()

    for document in documents:
        citation = document.get("citation")

        if citation:
            citations.add(citation)
            continue

        metadata = document.get("metadata", {})

        source_file = metadata.get("source_file")
        heading = metadata.get("heading")

        if source_file and heading:
            citations.add(
                f"{source_file} | {heading}"
            )
    return citations

def filter_citations(citations, allowed_citations):
    return [
        citation
        for citation in citations
        if citation in allowed_citations
    ]

def filter_cited_items(items, allowed_citations):
    return [
        item 
        for item in items
        if item.get("citation") in allowed_citations
    ]