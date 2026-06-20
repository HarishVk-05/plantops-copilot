import pytest

from src.agents.nodes.investigator import investigator_node

VALID_STATE = {
    "user_query": "PKG-L3 stopped due to overheating",
    "machine_id": "PKG-L3",
    "start_time": "2026-06-10T10:30:00",
    "end_time": "2026-06-10T11:10:00"
}

def test_investigator_uses_request_window():
    result = investigator_node(VALID_STATE)

    summary = result["incident_context"]["sensor_summary"]

    assert summary["start_time"] == VALID_STATE["start_time"]
    assert summary["end_time"] == VALID_STATE["end_time"]
    assert summary["row_count"] == 41

def test_investigator_rejects_missing_window():
    state = {
        "user_query": "Machine stopped",
        "machine_id": "PKG-L3"
    }

    with pytest.raises(ValueError):
        investigator_node(state)

def test_investigator_rejects_reversed_window():
    state = {
        **VALID_STATE,
        "start_time": VALID_STATE["end_time"],
        "end_time": VALID_STATE["start_time"]
    }

    with pytest.raises(ValueError):
        investigator_node(state)

def test_investigator_rejects_unknown_machine():
    state = {
        **VALID_STATE,
        "machine_id": "UNKNOWN"
    }

    with pytest.raises(ValueError):
        investigator_node(state)