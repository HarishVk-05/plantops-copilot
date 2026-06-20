def undetermined_handler_node(state):
    """
    Terminal handler for abstention cases.

    If RCA cannot determine a supported root cause, the system must not create
    corrective maintenance steps, assign tools, assign technicians, or reserve
    spare parts.
    """

    safety_report = {
        "required_safety_steps": [],
        "required_ppe": [],
        "prohibited_actions": [],
        "supervisor_approval_required": []
    }

    work_order_report = {
        "work_order_title": "No corrective work order generated",
        "priority": "None",
        "maintenance_steps": [],
        "safety_requirements": [],
        "required_tools": [],
        "required_skills": [],
        "success_criteria": [],
        "estimated_duration": "N/A"
    }

    resource_plan = {
        "matched_tools": [],
        "unmatched_tools": [],
        "matched_skills": [],
        "unmatched_skills": [],
        "technician_candidates": [],
        "compatible_spare_parts": [],
        "resource_warnings": [
            "No resources assigned because the root cause is undetermined."
        ]
    }

    return {
        **state,
        "safety_report": safety_report,
        "safety_documents": [],
        "work_order_report": work_order_report,
        "work_order_documents": [],
        "historical_work_orders": [],
        "resource_plan": resource_plan
    }