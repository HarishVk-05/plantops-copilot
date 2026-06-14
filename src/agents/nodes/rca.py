import json

from src.agents.llm import llm
from src.agents.prompts.rca_prompt import RCA_SYSTEM_PROMPT
from src.agents.schemas.rca_schema import RCAReport

def rca_node(state):

    evidence_package = state["evidence_package"]
    
    evidence_analysis = state["evidence_analysis"]

    prompt = f"""

    USER INCIDENT:
    {state["user_query"]}

    EVIDENCE PACKAGE:
    {json.dumps(evidence_package, indent=2)}

    Evidence Analysis:
    {json.dumps(evidence_analysis, indent = 2)}
    
    Generate RCA report.
    """

    structured_llm = llm.with_structured_output(RCAReport)
    
    response = structured_llm.invoke(
        [
            ("system",RCA_SYSTEM_PROMPT),
            ("human", prompt)
        ]
    )

    return {
        **state,
        "rca_report":
            response.model_dump()
    }