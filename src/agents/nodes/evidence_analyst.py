import json

from src.agents.llm import llm
from src.agents.schemas.evidence_analysis_schema import EvidenceAnalysis

structured_llm = llm.with_structured_output(
    EvidenceAnalysis
)

def evidence_analyst_node(state):
    
    evidence_package = state["evidence_package"]

    prompt = f"""
    Your task is NOT to summarize evidence.

Your task is to synthesize evidence across sources.

A good derived finding must combine information from at least two different evidence sources.

Examples:

BAD:
- Temperature exceeded threshold.
- Vibration exceeded threshold.

GOOD:
- Manual guidance links simultaneous vibration and motor current increase to belt misalignment.
- Historical ticket WO-2026-001 shows highly similar symptoms and identified belt misalignment as the root cause.
- Telemetry and alarm patterns are consistent with a mechanical overload event.

For every derived finding:
- Combine evidence from multiple sources.
- Explain why the relationship matters.
- Do not simply restate telemetry values.

    Evidence:

    {json.dumps(evidence_package, indent=2)}
    """

    response = structured_llm.invoke(prompt)

    return {
        **state,
        "evidence_analysis": response.model_dump()
    }