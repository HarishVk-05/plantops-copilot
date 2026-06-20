import json
import re

from src.agents.llm import llm, invoke_llm
from src.agents.schemas.safety_report_schema import SafetyReport
from src.rag.safety_retriever import retrieve_safety_documents
from src.agents.citation_guard import filter_cited_items

SAFETY_FIELDS = [
    "required_safety_steps",
    "required_ppe",
    "prohibited_actions",
    "supervisor_approval_required"
]

candidate_llm = llm.with_structured_output(SafetyReport)

reviewer_llm = llm.with_structured_output(SafetyReport)

def _normalize_text(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        value.lower()
    ).strip()

def _filter_candidate_subset(
        reviewed_report,
        candidate_report
):
    final_report = {}

    for field in SAFETY_FIELDS:
        candidate_items = (
            candidate_report.get(field, [])
        )

        candidate_lookup = {
            (
                _normalize_text(
                    item.get("text", "")
                ),
                item.get("citation")
            ): item
            for item in candidate_items
        }

        selected_items = []
        seen_items = set()

        for reviewed_item in reviewed_report.get(
            field,
            []
        ):
            key = (
                _normalize_text(
                    reviewed_item.get("text", "")
                ),
                reviewed_item.get("citation")
            )

            if key not in candidate_lookup:
                continue

            if key in seen_items:
                continue

            seen_items.add(key)
            selected_items.append(
                candidate_lookup[key]
            )

        final_report[field] = selected_items

    return final_report
def _is_determined_fault(rca_report: dict) -> bool:
    root_cause = rca_report.get("likely_root_cause", "")

    return (
        root_cause
        and root_cause.strip().lower() != "undetermined"
    )


def _has_planned_work(rca_report: dict) -> bool:
    recommendations = rca_report.get("recommendations", [])

    if not recommendations:
        return False

    action_words = {
        "inspect",
        "check",
        "adjust",
        "replace",
        "repair",
        "clean",
        "verify",
        "calibrate",
        "test",
        "restart",
        "remove",
        "install"
    }

    text = " ".join(
        str(item).lower()
        for item in recommendations
    )

    return any(
        word in text
        for word in action_words
    )


def _preserve_mandatory_safety_groups(
        final_report: dict,
        candidate_report: dict,
        rca_report: dict
) -> dict:
    """
    Safety invariant:
    For a determined fault with planned maintenance/inspection work,
    mandatory LOTO and PPE groups must not be dropped by the LLM reviewer.

    This does not invent safety controls. It only preserves controls that
    were already extracted from cited safety evidence.
    """

    if not _is_determined_fault(rca_report):
        return final_report

    if not _has_planned_work(rca_report):
        return final_report

    for field in [
        "required_safety_steps",
        "required_ppe"
    ]:
        if final_report.get(field):
            continue

        candidate_items = candidate_report.get(field, [])

        if candidate_items:
            final_report[field] = candidate_items

    return final_report


def safety_agent_node(state):
    rca_report = state["rca_report"]

    recommendations = rca_report.get(
        "recommendations",
        []
    )

    retrieval_query = f"""
Industrial maintenance safety requirements.

Root cause:
{rca_report.get("likely_root_cause", "Unknown")}

Planned maintenance actions:
{chr(10).join(f"- {item}" for item in recommendations)}

Retrieve relevant:
- lockout-tagout procedures
- energy-isolation requirements
- required PPE
- prohibited maintenance actions
- supervisor-approval requirements
"""

    safety_docs = retrieve_safety_documents(
        retrieval_query
    )

    safety_context = []

    for document in safety_docs:
        metadata = document.get("metadata", {})

        source_file = metadata.get(
            "source_file",
            "unknown_source"
        )

        heading = metadata.get(
            "heading",
            "unknown_heading"
        )

        safety_context.append(
            {
                "citation": (
                    f"{source_file} | {heading}"
                ),
                "document_title": metadata.get(
                    "document_title",
                    ""
                ),
                "content": document.get(
                    "text",
                    ""
                )[:1200],
                "similarity": document.get(
                    "similarity",
                    0
                )
            }
        )

    if not safety_context:
        empty_report = SafetyReport()

        return {
            **state,
            "safety_report":
                empty_report.model_dump(),
            "safety_documents": []
        }

    allowed_citations = {
        document["citation"]
        for document in safety_context
    }

    candidate_prompt = f"""
You are an industrial safety evidence extractor.

Extract evidence-supported candidate safety controls that may
apply to the supplied maintenance work.

Use only the supplied safety documents.

Rules:

- Do not invent or infer controls.
- Preserve the meaning of each documented control.
- Every item must contain an exact supplied citation.
- Do not provide repair instructions.
- Return an empty list when a field has no evidence.
- Extract each numbered step and each bullet as a separate
  SafetyItem.
- Never combine multiple documented controls into one item.
- Preserve the original order of procedural steps.
- Copy each control's text without summarizing it.
- When a section is explicitly labelled Required PPE,
  extract every listed PPE item separately.
- When a section is explicitly labelled Required Before
  Maintenance, extract every numbered step separately.

Return exactly:

- required_safety_steps
- required_ppe
- prohibited_actions
- supervisor_approval_required

RCA REPORT:

{json.dumps(rca_report, indent=2)}

PLANNED MAINTENANCE ACTIONS:

{json.dumps(recommendations, indent=2)}

SAFETY DOCUMENTS:

{json.dumps(safety_context, indent=2)}
"""

    candidate_response = invoke_llm(
        candidate_llm,
        candidate_prompt,
        "Safety evidence extraction"
    )

    candidate_report = (
        candidate_response.model_dump()
    )

    for field in SAFETY_FIELDS:
        candidate_report[field] = (
            filter_cited_items(
                candidate_report.get(field, []),
                allowed_citations
            )
        )

    reviewer_prompt = f"""
You are a senior industrial safety reviewer.

Review the candidate safety controls and return only the
controls that apply to the actual planned maintenance actions.

Applicability rules:

- Every selected control must apply to at least one planned
  maintenance action.

- A control is applicable only when a planned maintenance
  action explicitly or necessarily involves the component,
  hazard, or activity named by that control.

- For every selected control, identify the specific planned
  action that makes it applicable. If no specific action can
  be identified, omit the control.

- Generic energy-isolation controls may be retained when
  technicians will inspect, open, adjust, repair, or replace
  equipment.

- Include PPE only when the safety evidence requires it for
  the planned maintenance activity.

- Do not retain a control merely because it is generally safe
  practice or because maintenance is occurring.

- Exclude controls for panels, guards, motors, belts,
  conveyors, interlocks, or other components unless the
  planned maintenance actions involve that component.

- Supervisor approval applies only when a planned action
  matches the documented high-risk action.

- Do not include every item merely because it appears in the
  same safety document.

- Being conservative is not sufficient justification for
  including an unrelated control.

- If applicability is unclear, omit the item.

- When lockout-tagout applies, retain the complete documented
  Required Before Maintenance sequence. Do not omit, combine,
  summarize, or reorder its steps.

- When the documented Required PPE section applies, retain
  every required PPE item. Do not selectively choose only
  some items.

- Mandatory controls belonging to one applicable procedure
  must be preserved as a complete group.

- Relevance filtering applies to optional, component-specific,
  prohibited, and supervisor-approval controls. It must not
  remove individual steps from an applicable mandatory
  procedure.

Output restrictions:

- Return only a subset of CANDIDATE SAFETY CONTROLS.
- Copy candidate text and citations exactly.
- Do not add, rewrite, or move an item to another field.
- Return an empty list when no candidate applies.

RCA ROOT CAUSE:

{rca_report.get("likely_root_cause", "Unknown")}

PLANNED MAINTENANCE ACTIONS:

{json.dumps(recommendations, indent=2)}

CANDIDATE SAFETY CONTROLS:

{json.dumps(candidate_report, indent=2)}
"""

    reviewed_response = invoke_llm(
        reviewer_llm,
        reviewer_prompt,
        "Safety relevance review"
    )

    reviewed_report = (
        reviewed_response.model_dump()
    )

    final_report = _filter_candidate_subset(
        reviewed_report=reviewed_report,
        candidate_report=candidate_report
    )

    final_report = _preserve_mandatory_safety_groups(
        final_report=final_report,
        candidate_report=candidate_report,
        rca_report=rca_report
    )

    return {
        **state,
        "safety_report": final_report,
        "safety_documents": safety_context
    }