import json

from src.agents.llm import llm, invoke_llm
from src.agents.prompts.rca_prompt import RCA_SYSTEM_PROMPT
from src.agents.schemas.rca_schema import RCAReport
from src.agents.citation_guard import filter_citations

structured_llm = llm.with_structured_output(RCAReport)

def _contains_multiple_causes(
        root_cause: str
) -> bool:
    normalized = root_cause.lower()

    markers = [
        " or ",
        " and/or ",
        "/"
    ]

    return any(
        marker in normalized
        for marker in markers
    )


def _build_undetermined_report(
    state,
    reason
):
    return {
        "incident_summary": (
            f"Root cause analysis for "
            f"{state['machine_id']}: {reason}"
        ),
        "likely_root_cause": "Undetermined",
        "supporting_evidence": [],
        "contradictory_evidence": [],
        "recommendations": [],
        "citations": []
    }


def _has_abnormal_evidence(
    evidence_package
):
    evidence_status = (
        evidence_package.get(
            "evidence_status", {}
        )
    )

    return bool(
        evidence_status.get(
            "abnormal_evidence_present",
            False
        )
    )


def _is_valid_rca(
        report: dict,
        allowed_citations: set
) -> bool:
    root_cause = report.get(
        "likely_root_cause", ""
    ).strip()

    if not root_cause:
        return False
    
    if root_cause.lower() == "undetermined":
        return (
            not report.get("citations")
            and not report.get(
                "supporting_evidence"
            )
        )
    
    if _contains_multiple_causes(root_cause):
        return False
    
    citations = report.get(
        "citations", []
    )

    supporting_evidence = report.get(
        "supporting_evidence", []
    )

    if not citations:
        return False
    
    if not supporting_evidence:
        return False
    
    return all(
        citation in allowed_citations
        for citation in citations
    )

def rca_node(state):
    evidence_package = state["evidence_package"]
    evidence_analysis = state.get("evidence_analysis", {})
    evidence_status = evidence_package.get("evidence_status", {})
    operational_state = evidence_status.get("operational_state", "insufficient_data")
    
    if not _has_abnormal_evidence(
        evidence_package
    ):
        if operational_state == "normal":
            reason = (
                "available telemetry and alarms do "
                "not show an abnormal condition."
            )
        else:
            reason = (
                "insufficient operational evidence "
                "is available to confirm a fault."
            )

        report = _build_undetermined_report(
            state,
            reason
        )

        return {
            **state,
            "rca_report": report
        }
    
    allowed_citations = {
        finding["citation"]
        for finding in evidence_package.get("document_findings", [])
        if finding.get("citation")
    }

    base_prompt = f"""
MACHINE:

{state["machine_id"]}

OPERATIONAL EVIDENCE:

{json.dumps(evidence_package, indent=2)}

SECONDARY EVIDENCE ANALYSIS:

{json.dumps(evidence_analysis, indent=2)}

ALLOWED CITATIONS:

{json.dumps(sorted(allowed_citations), indent=2)}

Generate the RCA report.

Evidence rules:

- Treat only telemetry, alarms, maintenance documents, and
  matching historical tickets as evidence.
- The user's proposed diagnosis is not evidence and must not
  influence root-cause selection.
- Telemetry proves abnormal behaviour but does not, by itself,
  prove a physical cause.
- A manual list of possible causes proves only that a cause is
  possible. It does not prove that the cause occurred.
- A historical root cause is supporting evidence only when its
  machine and symptom pattern match the current operational
  evidence.
- Prefer the cause that explains the complete current symptom
  pattern, not merely one symptom.
- Treat SECONDARY EVIDENCE ANALYSIS as interpretation rather
  than source evidence.
- Do not select a cause solely because it appears in candidate
  causes or competing hypotheses.
- Do not invent evidence from the machine identifier or general
  engineering knowledge.

Output rules:

- Select exactly one root cause.
- Never combine causes using "or", "and/or", or "/".
- A determined root cause must have supporting evidence.
- A determined root cause must include at least one exact
  citation from ALLOWED CITATIONS.
- Put only exact ALLOWED CITATIONS in the citations field.
- If one cause is not sufficiently supported, return
  "Undetermined".
- When returning "Undetermined", return empty supporting
  evidence, recommendations, and citations.
"""


    latest_report = None

    for attempt in range(2):
        prompt = base_prompt

        if attempt > 0:
            prompt += """
The previous response failed evidence validation.

Re-evaluate the current operational pattern independently.
Do not repeat a diagnosis merely because it is listed as a
possible cause. Return one evidence-supported cause or return
"Undetermined".
"""
        response = invoke_llm(
            structured_llm,
            [
                ("system", RCA_SYSTEM_PROMPT),
                ("human", prompt)
            ],
            "Root cause analysis"
        )

        latest_report = response.model_dump()

        latest_report["citations"] = filter_citations(
            latest_report.get("citations", []),
            allowed_citations
        )

        if _is_valid_rca(latest_report, allowed_citations):
            return {
                **state,
                "rca_report": latest_report
            }
    
    fallback_report = (
        _build_undetermined_report(
            state,
            (
                "the available evidence did not support one valid root cause."
            )
        )
    )

    return {
        **state,
        "rca_report": fallback_report
    }