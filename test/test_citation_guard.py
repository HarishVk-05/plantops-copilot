from src.agents.citation_guard import collect_document_citations, filter_citations, filter_cited_items

def test_collect_document_citations():
    documents = [
        {
            "metadata": {
                "source_file": "manual.md",
                "heading": "Inspection"
            }
        },
        {
            "citation": "ticket.md | Root Cause"
        }
    ]

    citations = collect_document_citations(documents)

    assert citations == {
        "manual.md | Inspection",
        "ticket.md | Root Cause"
    }

def test_filter_unsupported_citations():
    allowed = {"manual.md | Inspection"}

    result = filter_citations(
        [
            "manual.md | Inspection",
            "invented.md | Unknown"
        ],
        allowed
    )

    assert result == ["manual.md | Inspection"]

def test_filter_unsupported_cited_items():
    items = [
        {
            "text": "Inspect belt alignment.",
            "citation": "manual.md | Inspection"
        },
        {
            "text": "Replace the motor.",
            "citation": "invented.md | Repair"
        }
    ]

    result = filter_cited_items(
        items,
        {"manual.md | Inspection"}
    )

    assert result == [items[0]]