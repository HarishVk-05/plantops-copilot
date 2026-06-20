import json

from src.agents.llm import llm, invoke_llm
from src.rag.work_order_retriever import retrieve_work_order_documents
from src.agents.schemas.work_order_schema import WorkOrderReport
from src.agents.citation_guard import filter_cited_items

structured_llm = llm.with_structured_output(WorkOrderReport)

def work_order_agent_node(state):
    rca_report = state["rca_report"]
    safety_report = state["safety_report"]

    recommendations = rca_report.get("recommendations", [])

    retrieval_query = f"""
    Machine: {state["machine_id"]}
    Root cause: {rca_report["likely_root_cause"]}

    Recommended actions:
    {chr(10).join(f"- {item}" for item in recommendations)}
    """

    retrieved_documents = retrieve_work_order_documents(
        query=retrieval_query,
        machine_id=state["machine_id"]
    )

    work_order_context = []

    for document in retrieved_documents:
        metadata = document.get("metadata", {})

        citation = (
            f"{metadata.get('source_file', 'unknown_source')} | "
            f"{metadata.get('heading', 'unknown_heading')}"
        )

        work_order_context.append(
            {
                "citation": citation,
                "document_title": metadata.get("document_title", ""),
                "content": document.get("text", "")[:1200],
                "similarity": document.get(
                    "similarity", 0
                )
            }
        )
    
    historical_work_order_heading = {
        "root cause",
        "action taken",
        "parts used",
        "tools used",
        "skills used",
        "verification result",
        "work outcome",
        "duration"
    }

    existing_citations = {
        document["citation"]
        for document in work_order_context
    }

    for document in state.get(
        "retrieved_docs",
        []
    ):
        metadata = document.get("metadata", {})

        if (
            metadata.get("document_category")
            != "historical_ticket"
            ):
            continue

        heading = metadata.get("heading", "").strip()

        if (
            heading.lower()
            not in historical_work_order_heading
        ):
            continue

        citation = (
            f"{metadata.get('source_file', 'unknown_source')} | "
            f"{heading}"
        )

        if citation in existing_citations:
            continue

        existing_citations.add(citation)

        work_order_context.append(
            {
                "citation": citation,
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

    maintenance_citations = set(
        document["citation"]
        for document in work_order_context
        if document.get("citation")
    )

    safety_citations = set()

    for field_items in safety_report.values():
        if not isinstance(field_items, list):
            continue

        for item in field_items:
            if (
                isinstance(item, dict)
                and item.get("citation")
            ):
                safety_citations.add(
                    item["citation"]
                )
    base_prompt = f"""
You are a senior industrial maintenance planner.

Generate a work order using only the supplied RCA, safety
report, maintenance manuals, and historical work-order
evidence.

Citation rules:

- Every list item must contain a citation.
- Citations must exactly match one of the supplied allowed
  citations.
- Maintenance steps, tools and success criteria must cite
  an allowed maintenance citation.
- Safety requirements must cite an allowed safety citation.
- Required skills may cite maintenance or safety evidence.
- Never cite "RCA report" as a citation.
- Never invent or modify a citation.

Corrective-action rules:

- Maintenance steps must be executable and sequenced.
- Include at least one corrective action that directly
  addresses the selected root cause when supported evidence
  exists.
- Clearly distinguish diagnostic checks from corrective
  actions and verification actions.
- Do not return only diagnostic checks when a matching
  historical ticket documents a corrective action.
- A historical Action Taken may be used only when the
  historical Root Cause matches the RCA root cause.
- Do not copy actions from a historical ticket with a
  different root cause.

Tool and skill rules:

- Tools must be explicitly named in maintenance evidence.
- An instrument or device used to perform an action, such as
  an ultrasonic leak detector, is a tool and not a skill.
- Historical tools may be used only when explicitly listed
  under Tools Used.
- Skills must be explicitly listed under Required Skills,
  Skills Used, Required Competency, or equivalent evidence.
- Never infer a skill from the maintenance action.
- Historical skills may be used only when explicitly listed
  under Skills Used.
- Return an empty list when tools or skills are unsupported.

Safety rules:

- Copy relevant safety controls from the Safety Report.
- Do not invent or rewrite safety requirements.

Success criteria:

- Success criteria must come from an explicit verification
  procedure, acceptance criterion, operating limit, or
  historical Verification Result.
- Do not convert a maintenance action into a success
  criterion.
- Use the historical Verification Result only when its
  historical Root Cause matches the RCA root cause.

Other fields:

- Use an estimated duration only when explicitly documented.
- Use "Unknown" when priority or duration is unsupported.
- Prefer an empty list over unsupported information.

RCA REPORT:

{json.dumps(rca_report, indent=2)}

SAFETY REPORT:

{json.dumps(safety_report, indent=2)}

ALLOWED MAINTENANCE CITATIONS:

{json.dumps(sorted(maintenance_citations), indent=2)}

ALLOWED SAFETY CITATIONS:

{json.dumps(sorted(safety_citations), indent=2)}

MAINTENANCE EVIDENCE:

{json.dumps(work_order_context, indent=2)}
"""
    
    final_report = None

    for attempt in range(2):
        prompt = base_prompt

        if attempt > 0:
            prompt += """
The previous response did not contain valid maintenance steps.

Generate at least one evidence-supported maintenance step.
Each maintenance step must use an exact citation from
ALLOWED MAINTENANCE CITATIONS.
"""
        response = invoke_llm(
            structured_llm, prompt, "Work-order generation"
        )

        report = response.model_dump()

        report["maintenance_steps"] = filter_cited_items(
            report.get("maintenance_steps", []),
            maintenance_citations
        )

        report["required_tools"] = filter_cited_items(
            report.get("required_tools", []),
            maintenance_citations
        )

        report["success_criteria"] = filter_cited_items(
            report.get("success_criteria", []),
            maintenance_citations
        )

        report["safety_requirements"] = filter_cited_items(
            report.get("safety_requirements", []),
            safety_citations
        )

        report["required_skills"] = filter_cited_items(
            report.get("required_skills", []),
            maintenance_citations | safety_citations
        )

        final_report = report

        if report["maintenance_steps"]:
            break

    if not final_report["maintenance_steps"]:
        raise RuntimeError(
            "Work-order validation failed because no valid "
            "maintenance steps were generated."
        )
    
    safety_requirements = []
    seen_safety_items = set()

    for field in [
        "required_safety_steps",
        "required_ppe"
    ]:
        for item in safety_report.get(field, []):
            key = (
                item.get("text"),
                item.get("citation")
            )

            if key in seen_safety_items:
                continue

            seen_safety_items.add(key)
            safety_requirements.append(item)
    final_report["safety_requirements"] = (
        safety_requirements
    )

    return {
        **state,
        "work_order_report": final_report,
        "historical_work_orders": work_order_context
    }   