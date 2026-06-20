from src.agents.nodes.evidence_synthesizer import (
    evidence_synthesizer_node
)


def test_synthesizer_packages_facts_without_diagnosis():
    state = {
        "user_query": "Machine overheating",
        "machine_id": "PKG-L3",
        "incident_context": {
            "sensor_summary": {
                "found": True,
                "limit_violations": [
                    {
                        "metric": "temperature_c",
                        "label": "Motor temperature",
                        "unit": "°C",
                        "severity": "warning",
                        "operator": ">",
                        "threshold": 85,
                        "violation_count": 4
                    }
                ],
                "stats": {
                    "temperature_c": {
                        "min": 70,
                        "max": 91,
                        "mean": 82,
                        "change": 15
                    }
                }
            },
            "alarms": [
                {
                    "severity": "critical",
                    "alarm_code": "MOTOR_OVERLOAD"
                }
            ]
        },
        "retrieved_docs": [
            {
                "text": "Inspect belt alignment.",
                "similarity": 0.8,
                "metadata": {
                    "source_file": "manual.md",
                    "heading": "Inspection",
                    "document_category": "maintenance"
                }
            }
        ]
    }

    result = evidence_synthesizer_node(state)
    package = result["evidence_package"]

    assert package["machine_id"] == "PKG-L3"
    assert len(package["sensor_findings"]) > 0
    assert len(package["document_findings"]) == 1
    assert "incident_patterns" not in package
    assert "evidence_strength" not in package
    assert "historical_findings" not in package