from datetime import datetime

from src.agents.tools.investigation_tool import investigate_incident

def _parse_timestamp(value: str, field_name: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} must be a valid ISO-8601 timestamp. "
            f"Got: {value!r}"
        ) from exc
    

def investigator_node(state):
    start_time = state.get("start_time")
    end_time = state.get("end_time")

    if not start_time or not end_time:
        raise ValueError(
            "Both start_time and end_time are required "
            "to investigate an incident."
        )

    parsed_start = _parse_timestamp(start_time, "start_time")
    parsed_end = _parse_timestamp(end_time, "end_time")

    if parsed_start.tzinfo != parsed_end.tzinfo:
        raise ValueError(
            "start_time and end_time must use the same timezone format."
        )
    
    if parsed_start > parsed_end:
        raise ValueError(
            "start_time must be earlier than or equal to end_time."
        )
    
    context = investigate_incident(
        machine_id=state["machine_id"],
        start_time=start_time,
        end_time=end_time
    )

    machine_info = context.get("machine_info", {})

    if not machine_info.get("found", False):
        raise ValueError(
            machine_info.get(
                "message",
                f"Machine {state['machine_id']} was not found."
            )
        )
    
    sensor_summary = context.get("sensor_summary", {})

    if not sensor_summary.get("found", False):
        raise ValueError(
            "No sensor data was found for "
            f"machine {state['machine_id']} between "
            f"{start_time} and {end_time}."
        )
    

    return {
        **state,
        "incident_context": context
    }