from typing import Optional, TypedDict

class AgentState(TypedDict):
    user_query: str
    machine_id: str

    start_time: Optional[str]
    end_time: Optional[str]
    
    incident_context: dict
    
    retrieved_docs: list

    evidence_package: dict
    
    evidence_analysis: dict
    
    rca_report: dict
    
    safety_report: dict
    
    work_order: dict
