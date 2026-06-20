from pydantic import BaseModel, Field

from typing import List

class RCAReport(BaseModel):

    incident_summary: str

    likely_root_cause: str

    supporting_evidence: List[str] = Field(default_factory=list)

    contradictory_evidence: list[str] = Field(default_factory=list)

    recommendations: List[str] = Field(default_factory=list)

    citations: list[str] = Field(default_factory = list)