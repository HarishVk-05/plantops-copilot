from src.agents.nodes.resource_planner import (
    resource_planner_node
)


def test_resource_planner_matches_resources():
    state = {
        "machine_id": "PKG-L3",
        "work_order_report": {
            "required_tools": [
                {
                    "text": "Belt tension gauge",
                    "citation": "manual.md | Tools"
                }
            ],
            "required_skills": [
                {
                    "text": "Mechanical Maintenance Technician",
                    "citation": "manual.md | Skills"
                },
                {
                    "text": "Conveyor Alignment Training",
                    "citation": "manual.md | Skills"
                }
            ]
        }
    }

    result = resource_planner_node(state)
    plan = result["resource_plan"]

    assert len(plan["matched_tools"]) == 1
    assert len(plan["matched_skills"]) == 2
    assert len(plan["compatible_spare_parts"]) == 2

    assert any(
        candidate["tech_id"] == "TECH-001"
        and candidate["eligible"]
        for candidate in plan["technician_candidates"]
    )