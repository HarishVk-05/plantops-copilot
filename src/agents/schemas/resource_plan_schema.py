from typing import List

from pydantic import BaseModel, Field


class ToolMatch(BaseModel):
    requested_text: str
    tool_id: str
    tool_name: str
    quantity_available: int
    availability: str


class SkillMatch(BaseModel):
    requested_text: str
    skill_id: str
    skill_name: str


class TechnicianCandidate(BaseModel):
    tech_id: str
    tech_name: str
    shift: str
    availability: str
    matched_skills: List[str] = Field(default_factory=list)
    covers_all_required_skills: bool
    eligible: bool


class SparePartOption(BaseModel):
    part_id: str
    part_name: str
    stock_qty: int
    stock_status: str
    critical_spare: bool


class ResourcePlan(BaseModel):
    matched_tools: List[ToolMatch] = Field(default_factory=list)
    unmatched_tools: List[str] = Field(default_factory=list)
    matched_skills: List[SkillMatch] = Field(default_factory=list)
    unmatched_skills: List[str] = Field(default_factory=list)
    technician_candidates: List[TechnicianCandidate] = Field(
        default_factory=list
    )
    compatible_spare_parts: List[SparePartOption] = Field(
        default_factory=list
    )
    resource_warnings: List[str] = Field(default_factory=list)