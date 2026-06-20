from pydantic import BaseModel
from typing import List

class CitedItem(BaseModel):
    text: str
    citation: str

class WorkOrderReport(BaseModel):

    work_order_title: str

    priority: str

    maintenance_steps: List[CitedItem]

    safety_requirements: List[CitedItem]

    required_tools: List[CitedItem]

    required_skills: List[CitedItem]

    success_criteria: List[CitedItem]

    estimated_duration: str