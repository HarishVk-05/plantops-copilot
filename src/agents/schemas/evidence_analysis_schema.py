from pydantic import BaseModel
from typing import List

class EvidenceAnalysis(BaseModel):

    derived_findings: List[str]

    candidate_causes: List[str]

    competing_hypotheses: List[str]