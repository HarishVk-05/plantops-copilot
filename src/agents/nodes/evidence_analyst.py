import json

from src.agents.llm import llm, invoke_llm
from src.agents.schemas.evidence_analysis_schema import EvidenceAnalysis

structured_llm = llm.with_structured_output(
    EvidenceAnalysis
)

def evidence_analyst_node(state):
    
    evidence_package = state["evidence_package"]

    prompt = f"""
    You are a manufacturing reliability evidence analyst.

    Analyze relationships across the supplied evidence sources.

    Your task is to produce:

    1. derived_findings
    2. candidate_causes
    3. competing_hypotheses

    Rules:

    - Use only the supplied evidence.
    - Do not invent measurements, events, causes, or citations.
    - Do not generate confidence scores or evidence-strength ratings.
    - Do not treat an alarm name as proof of its physical cause.
    - Do not treat temporal correlation as proof of causation.
    - A historical ticket supports a candidate cause only when its
    symptom pattern is relevant to the current telemetry and alarms.
    - A historical ticket from the same machine is not automatically
    relevant.
    - Manuals describe possible causes, not confirmed causes.
    - Clearly preserve contradictory evidence.
    - Candidate causes must be supported by at least one supplied source.
    - Derived findings should connect evidence from at least two
    different source types whenever possible.
    - Include available document citations inside the finding text.
    - If evidence is insufficient, return empty lists rather than
    inventing conclusions.

    EVIDENCE PACKAGE:

    {json.dumps(evidence_package, indent=2)}
    """

    response = invoke_llm(structured_llm,
                          prompt,
                          "Evidence analysis")

    return {
        **state,
        "evidence_analysis": response.model_dump()
    }