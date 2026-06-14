from pydantic import BaseModel
from typing import List

class RCAReport(BaseModel):

    incident_summary: str

    likely_root_cause: str

    evidence_strength: str # (strong, moderate, weak, insufficient)

    supporting_evidence: List[str]

    contradictory_evidence: list[str]

    recommendations: List[str]

    citations: list[str]