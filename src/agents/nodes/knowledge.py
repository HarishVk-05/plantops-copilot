from src.agents.tools.retrieval_tool import retrieve_knowledge

def _build_retrieval_query(state) -> str:
    incident_context = state.get("incident_context", {})

    machine_info = incident_context.get("machine_info", {}).get("machine", {})

    sensor_summary = incident_context.get("sensor_summary", {}) 

    alarms = incident_context.get("alarms", [])

    query_parts = [
        state["user_query"],
        F"Machine ID: {state['machine_id']}"
    ]

    if machine_info:
        query_parts.append(
            f"Machine type: {machine_info.get('machine_type', '')}"
        )

        query_parts.append(
            f"Machine name: {machine_info.get('machine_name', '')}"
        )
    
    violations = sensor_summary.get(
        "limit_violations", []
    )

    if violations:
        violation_text = [
            (
                f"{item.get('label')} "
                f"{item.get('operator')} "
                f"{item.get('threshold')} "
                f"{item.get('unit', '')}"
            )
            for item in violations
        ]

        query_parts.append(
            "Observed telemetry limit violations: "
            + ", ".join(violation_text)
        )
    
    alarm_codes = [
        alarm.get("alarm_code")
        for alarm in alarms
        if alarm.get("alarm_code")
    ]

    if alarm_codes:
        query_parts.append(
            "Alarm codes: "
            + ", ".join(dict.fromkeys(alarm_codes))
        )
    
    return "\n".join(query_parts)

def knowledge_node(state):
    retrieval_query = _build_retrieval_query(state)

    docs = retrieve_knowledge(
        query=retrieval_query,
        machine_id=state["machine_id"]
    )

    return {
        **state,
        "retrieved_docs": docs
    }