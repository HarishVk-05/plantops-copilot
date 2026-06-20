def get_document_category(file_name: str) -> str:
    """
    Categorize documents for agent-specific retrieval.
    """

    file_name = file_name.lower()

    # Safety SOPs
    if "safety" in file_name:
        return "safety"
    
    # Historical maintenance tickets
    if file_name.startswith("wo-"):
        return "historical_ticket"
    
    # Future inventory docs
    if "inventory" in file_name:
        return "inventory"

    # Default
    return "maintenance"