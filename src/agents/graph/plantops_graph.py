from langgraph.graph import StateGraph
from langgraph.graph import END

from src.agents.graph.state import AgentState

from src.agents.nodes.investigator import investigator_node
from src.agents.nodes.knowledge import knowledge_node
from src.agents.nodes.rca import rca_node
from src.agents.nodes.evidence_synthesizer import evidence_synthesizer_node
from src.agents.nodes.evidence_analyst import evidence_analyst_node


builder = StateGraph(AgentState)

builder.add_node(
    "investigator",
    investigator_node
)

builder.add_node(
    "knowledge",
    knowledge_node
)

builder.add_node(
    "rca",
    rca_node
)

builder.add_node(
    "evidence_analyst",
    evidence_analyst_node
)

builder.add_node(
    "evidence_synthesizer",
    evidence_synthesizer_node
)

builder.set_entry_point(
    "investigator" 
)

builder.add_edge(
    "investigator",
    "knowledge"
)

builder.add_edge(
    "knowledge",
    "evidence_synthesizer"
)

builder.add_edge(
    "evidence_synthesizer",
    "evidence_analyst"
)

builder.add_edge(
    "evidence_analyst",
    "rca"
)


builder.add_edge(
    "rca",
    END
)

graph = builder.compile()

