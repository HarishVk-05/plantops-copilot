from typing import Any, Dict, List

def _extract_sensor_findings(sensor_summary):
    if not sensor_summary.get("found", False):
        return []
    
    findings = []
    
    for violation in sensor_summary.get(
        "limit_violations", []
    ):
        label = violation.get("label",
                              violation.get("metric", "Metric"))
        
        operator = violation.get("operator", "")
        threshold = violation.get("threshold")
        unit = violation.get("unit", "")
        severity = violation.get("severity", "warning")
        count = violation.get("violation_count", 0)

        findings.append(
            f"{label} produced {count} {severity} limit "
            f"violations ({operator} {threshold} {unit})."
        )

    stats = sensor_summary.get("stats", {})

    for metric, values in stats.items():
        findings.append(
            f"{metric}: minimum {values.get('min')}, "
            f"maximum {values.get('max')}, "
            f"mean {values.get('mean')}, "
            f"change {values.get('change')}."
        )
    return findings

def _extract_alarm_findings(alarms):

    critical_alarms = []
    warning_alarms = []

    for alarm in alarms:
        severity = str(
            alarm.get("severity","")
            ).strip().lower()

        code = alarm.get(
            "alarm_code","UNKNOWN"
        )

        if severity == "critical":
            critical_alarms.append(code)
        
        elif severity == "warning":
            warning_alarms.append(code)

    return {
        "critical_alarms": critical_alarms,
        "warning_alarms": warning_alarms
    }

def _extract_document_findings(docs):
    findings = []

    for doc in docs:
        metadata = doc.get("metadata", {})

        findings.append(
            {
                "citation": (
                    f"{metadata.get('source_file', 'unknown')} | "
                    f"{metadata.get('heading', 'unknown')}"
                ),
                "document_category": metadata.get(
                    "document_category", "unknown"
                ),
                "similarity": round(
                    doc.get("similarity", 0), 4
                ),
                "snippet": doc.get("text", "")[:500]
            }
        )

    return findings

def _count_limit_violations(sensor_summary):
    total = 0

    for violation in sensor_summary.get(
        "limit_violations", []
    ):
        count = violation.get(
            "violation_count", 0
        )

        try:
            total += int(count)
        except (TypeError, ValueError):
            continue

    return total


def _build_evidence_status(
    sensor_summary,
    alarm_findings
):
    sensor_data_found = bool(
        sensor_summary.get("found", False)
    )

    limit_violation_count = (
        _count_limit_violations(sensor_summary)
    )

    critical_alarm_count = len(
        alarm_findings["critical_alarms"]
    )

    warning_alarm_count = len(
        alarm_findings["warning_alarms"]
    )

    abnormal_alarm_count = (
        critical_alarm_count
        + warning_alarm_count
    )

    abnormal_evidence_present = (
        limit_violation_count > 0
        or abnormal_alarm_count > 0
    )

    if abnormal_evidence_present:
        operational_state = "abnormal"

    elif sensor_data_found:
        operational_state = "normal"

    else:
        operational_state = "insufficient_data"

    return {
        "sensor_data_found": sensor_data_found,
        "limit_violation_count": (
            limit_violation_count
        ),
        "critical_alarm_count": (
            critical_alarm_count
        ),
        "warning_alarm_count": (
            warning_alarm_count
        ),
        "abnormal_evidence_present": (
            abnormal_evidence_present
        ),
        "operational_state": operational_state
    }


def evidence_synthesizer_node(state):

    incident_context = state["incident_context"]

    sensor_summary = incident_context.get(
        "sensor_summary", {}
    )

    alarms = incident_context.get(
        "alarms", []
    )

    retrieved_docs = state.get(
        "retrieved_docs", []
    )

    sensor_findings = _extract_sensor_findings(
        sensor_summary
    )

    alarm_findings = _extract_alarm_findings(
        alarms
    )

    document_findings = _extract_document_findings(
        retrieved_docs
    )

    evidence_status = _build_evidence_status(
        sensor_summary,
        alarm_findings
    )

    evidence_package = {
        "machine_id": state["machine_id"],
        "sensor_findings": sensor_findings,
        "alarm_findings": alarm_findings,
        "evidence_status": evidence_status,
        "document_findings": document_findings
    }

    return {
        **state,
        "evidence_package": evidence_package
    }
