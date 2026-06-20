import re

from src.agents.schemas.resource_plan_schema import (
    ResourcePlan,
    SkillMatch,
    SparePartOption,
    TechnicianCandidate,
    ToolMatch
)

from src.database.sql_tools import PlantOpsSQLTool

sql_tool = PlantOpsSQLTool()

def _normalize(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower()
    ).strip()

def _matches(requested: str, catalog_value: str) -> bool:
    requested_normalized = _normalize(requested)
    catalog_normalized = _normalize(catalog_value)

    if not requested_normalized or not catalog_normalized:
        return False
    
    return (
        catalog_normalized in requested_normalized
        or requested_normalized in catalog_normalized
    )

def resource_planner_node(state):
    work_order = state["work_order_report"]
    machine_id = state["machine_id"]

    tool_inventory = sql_tool.get_tool_inventory()
    skill_catalog = sql_tool.get_skill_catalog()
    technicians = sql_tool.get_technicians_with_skills()
    spare_parts = sql_tool.get_spare_parts_for_machine(machine_id)

    matched_tools = []
    unmatched_tools = []
    warnings = []

    for requested_item in work_order.get("required_tools", []):
        requested_text = requested_item.get("text", "")

        match = next(
            (
                tool
                for tool in tool_inventory
                if _matches(
                    requested_text,
                    tool["tool_name"]
                )
            ),
            None
        )

        if not match:
            unmatched_tools.append(requested_text)
            warnings.append(
                f"Tool not found in inventory: {requested_text}"
            )
            continue

        matched_tools.append(
            ToolMatch(
                requested_text=requested_text,
                tool_id=match["tool_id"],
                tool_name=match["tool_name"],
                quantity_available=int(match["qty"]),
                availability=match["availability"]
            )
        )

        if match["availability"] != "available":
            warnings.append(
                f"Tool unavailable: {match['tool_name']}"
            )
    
    matched_skills = []
    unmatched_skills = []

    for requested_item in work_order.get("required_skills", []):
        requested_text = requested_item.get("text", "")

        match = next(
            (
                skill
                for skill in skill_catalog
                if _matches(
                    requested_text,
                    skill["skill_name"]
                )
            ),
            None
        )

        if not match:
            unmatched_skills.append(requested_text)
            warnings.append(
                f"Skill not found in catalog: {requested_text}"
            )
            continue

        matched_skills.append(
            SkillMatch(
                requested_text=requested_text,
                skill_id=match["skill_id"],
                skill_name=match["skill_name"]
            )
        )

    required_skill_ids = {
        skill.skill_id
        for skill in matched_skills
    }

    technician_candidates = []

    if required_skill_ids:
        for technician in technicians:
            technician_skill_map = {
                skill["skill_id"]: skill["skill_name"]
                for skill in technician["skills"]
            }

            matched_ids = (
                required_skill_ids
                & set(technician_skill_map)
            )

            if not matched_ids:
                continue

            covers_all = (
                required_skill_ids <= set(technician_skill_map)
            )

            is_available = (
                technician["availability"].lower() == "available"
            )

            technician_candidates.append(
                TechnicianCandidate(
                    tech_id= technician["tech_id"],
                    tech_name= technician["tech_name"],
                    shift= technician["shift"],
                    availability= technician["availability"],
                    matched_skills=[
                        technician_skill_map[skill_id]
                        for skill_id in sorted(matched_ids)
                    ],
                    covers_all_required_skills= covers_all,
                    eligible= covers_all and is_available
                )
            )
        
        technician_candidates.sort(
            key= lambda candidate: (
                not candidate.eligible,
                not candidate.covers_all_required_skills,
                -len(candidate.matched_skills),
                candidate.tech_name
            )
        )

        if not any(
            candidate.eligible
            for candidate in technician_candidates
        ):
            warnings.append(
                "No available technician covers all required skills."
            )
    else:
        warnings.append(
            "No required skills could be matched, so a technician cannot be assigned automatically."
        )
        
    compatible_spare_parts = []

    for part in spare_parts:
        compatible_spare_parts.append(
            SparePartOption(
                part_id=part["part_id"],
                part_name=part["part_name"],
                stock_qty=int(part["stock_qty"]),
                stock_status=part["stock_status"],
                critical_spare=bool(part["critical_spare"])
            )
        )

        if part["stock_status"] != "available":
            warnings.append(
                f"Spare part {part['part_name']} is "
                f"{part['stock_status']}"
            )
        
    resource_plan = ResourcePlan(
        matched_tools=matched_tools,
        unmatched_tools=unmatched_tools,
        matched_skills=matched_skills,
        unmatched_skills=unmatched_skills,
        technician_candidates=technician_candidates,
        compatible_spare_parts=compatible_spare_parts,
        resource_warnings=list(dict.fromkeys(warnings))
    )

    return {
        **state,
        "resource_plan": resource_plan.model_dump()
    }