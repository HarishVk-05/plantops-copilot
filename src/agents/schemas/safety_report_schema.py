from pydantic import BaseModel, Field
from typing import List

class SafetyItem(BaseModel):
    text: str
    citation: str

class SafetyReport(BaseModel):

    required_safety_steps: List[SafetyItem] = Field(default_factory=list)

    required_ppe: List[SafetyItem] = Field(default_factory=list)

    prohibited_actions: List[SafetyItem] = Field(default_factory=list)

    supervisor_approval_required: List[SafetyItem] = Field(default_factory=list)
