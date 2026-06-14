from src.agents.tools.investigation_tool import investigate_incident

def investigator_node(state):

    context = investigate_incident(
        machine_id=state["machine_id"],
        start_time="2026-06-10T10:30:00",
        end_time="2026-06-10T11:10:00"
    )

    return {
        **state,
        "incident_context": context
    }