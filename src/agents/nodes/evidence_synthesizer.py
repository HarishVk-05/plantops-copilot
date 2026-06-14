from typing import Any, Dict, List

def _extract_sensor_findings(sensor_summary: Dict[str, Any]) -> List[str]:
    findings = []

    if not sensor_summary.get("found", False):
        return findings
    
    threshold_flags = sensor_summary.get("threshold_flags", {})

    if threshold_flags.get("temperature_above_85c_count", 0) > 0:
        findings.append(
            "Temperature exceeded 85°C operating threshold."
        )
    
    if threshold_flags.get("temperature_above_90c_count", 0) > 0:
        findings.append(
            "Temperature exceeded 90°C critical threshold."
        )
    
    if threshold_flags.get("vibration_above_6_count", 0) > 0:
        findings.append(
            "Vibration exceeded normal operating range."
        )

    if threshold_flags.get("vibration_above_7_5_count", 0) > 0:
        findings.append(
            "Vibration exceeded critical threshold of 7.5 mm/s."
        )

    if threshold_flags.get("current_above_15a_count", 0) > 0:
        findings.append(
            "Motor current exceeded 15A threshold."
        )

    if threshold_flags.get("current_above_17a_count", 0) > 0:
        findings.append(
            "Motor current exceeded critical threshold of 17A."
        )

    if threshold_flags.get("pressure_below_5_8_bar_count", 0) > 0:
        findings.append(
            "Pressure dropped below normal operating range."
        )

    if threshold_flags.get("pressure_below_5_3_bar_count", 0) > 0:
        findings.append(
            "Pressure dropped below critical threshold."
        )

    stats = sensor_summary.get("stats", {})

    if "temperature_c" in stats:
        findings.append(
            f"Maximum temperature observed: "
            f"{stats['temperature_c']['max']}°C."
        )

    if "vibration_mm_s" in stats:
        findings.append(
            f"Maximum vibration observed: "
            f"{stats['vibration_mm_s']['max']} mm/s."
        )

    if "current_a" in stats:
        findings.append(
            f"Maximum motor current observed: "
            f"{stats['current_a']['max']} A."
        )

    return findings

def _extract_alarm_findings(alarms):

    critical_alarms = []

    warning_alarms = []

    for alarm in alarms:

        severity = alarm.get(
            "severity",
            ""
        ).lower()

        code = alarm.get(
            "alarm_code",
            "UNKNOWN"
        )

        if severity == "critical":

            critical_alarms.append(
                code
            )

        else:

            warning_alarms.append(
                code
            )

    return {
        "critical_alarms":
        critical_alarms,

        "warning_alarms":
        warning_alarms
    }

def _detect_incident_patterns(
    sensor_findings,
    alarm_findings
):

    patterns = []

    sensor_text = " ".join(
        sensor_findings
    ).lower()

    critical_alarms = alarm_findings.get(
        "critical_alarms",
        []
    )

    if (
        "temperature exceeded" in sensor_text
        and
        "vibration exceeded" in sensor_text
        and
        "motor current exceeded" in sensor_text
    ):
        patterns.append(
            "Mechanical overload pattern"
        )

    if (
        "temperature exceeded" in sensor_text
        and
        "vibration exceeded" not in sensor_text
    ):
        patterns.append(
            "Cooling system failure pattern"
        )

    if (
        "MOTOR_OVERLOAD"
        in critical_alarms
    ):
        patterns.append(
            "Electrical overload pattern"
        )

    if (
        "MACHINE_STOPPED"
        in critical_alarms
    ):
        patterns.append(
            "Production interruption event"
        )

    return patterns


def _extract_document_findings(docs):

    findings = []

    for doc in docs[:5]:

        findings.append(
            {
                "citation":
                doc.get("citation"),

                "similarity":
                round(
                    doc.get("similarity", 0),
                    4
                ),

                "snippet":
                doc.get(
                    "text",
                    ""
                )[:300]
            }
        )

    return findings


def _extract_historical_findings(
    history: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:

    findings = []

    for ticket in history[:5]:

        findings.append(
            {
                "ticket_id":
                ticket.get("ticket_id"),

                "root_cause":
                ticket.get("root_cause"),

                "symptoms":
                ticket.get("symptoms")
            }
        )

    return findings


def _compute_evidence_strength(
    sensor_findings: List[str],
    alarm_findings: List[str],
    document_findings: List[Dict[str, Any]],
    historical_findings: List[Dict[str, Any]],
) -> str:
    
    alarm_count = (
        len(
            alarm_findings["critical_alarms"]
        )
        +
        len(
            alarm_findings["warning_alarms"]
        )
    )

    score = (
        len(sensor_findings)
        + alarm_count
        + len(document_findings)
        + len(historical_findings)
    )

    if score >= 12:
        return "strong"

    if score >= 6:
        return "moderate"

    return "weak"


def evidence_synthesizer_node(state):

    incident_context = state["incident_context"]

    sensor_summary = incident_context.get(
        "sensor_summary",
        {}
    )

    alarms = incident_context.get(
        "alarms",
        []
    )

    maintenance_history = incident_context.get(
        "maintenance_history",
        []
    )

    retrieved_docs = state.get(
        "retrieved_docs",
        []
    )

    sensor_findings = _extract_sensor_findings(
        sensor_summary
    )

    alarm_findings = _extract_alarm_findings(
        alarms
    )

    incident_patterns = (
        _detect_incident_patterns(
            sensor_findings,
            alarm_findings
        )
    )

    document_findings = _extract_document_findings(
        retrieved_docs
    )

    historical_findings = _extract_historical_findings(
        maintenance_history
    )

    evidence_strength = _compute_evidence_strength(
        sensor_findings,
        alarm_findings,
        document_findings,
        historical_findings
    )

    evidence_package = {
        "machine_id":
        state["machine_id"],

        "user_query":
        state["user_query"],

        "evidence_strength":
        evidence_strength,

        "incident_patterns":
        incident_patterns,

        "sensor_findings":
        sensor_findings,

        "alarm_findings":
        alarm_findings,

        "document_findings":
        document_findings,

        "historical_findings":
        historical_findings
    }

    return {
        **state,
        "evidence_package": evidence_package
    }
