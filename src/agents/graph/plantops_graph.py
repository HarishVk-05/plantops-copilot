from langgraph.graph import StateGraph
from langgraph.graph import END

from src.agents.graph.state import AgentState

from src.agents.nodes.investigator import investigator_node
from src.agents.nodes.knowledge import knowledge_node
from src.agents.nodes.rca import rca_node
from src.agents.nodes.evidence_synthesizer import evidence_synthesizer_node
from src.agents.nodes.evidence_analyst import evidence_analyst_node
from src.agents.nodes.safety_agent import safety_agent_node
from src.agents.nodes.work_order_agent import work_order_agent_node
from src.agents.nodes.resource_planner import resource_planner_node
from src.agents.nodes.undetermined_handler import undetermined_handler_node



def route_after_rca(state):
    rca_report = state.get("rca_report", {})
    root_cause = rca_report.get("likely_root_cause", "")

    if root_cause.strip().lower() == "undetermined":
        return "undetermined_handler"
    
    return "safety_agent"

builder = StateGraph(AgentState)

builder.add_node(
    "investigator",
    investigator_node
)

builder.add_node(
    "undetermined_handler",
    undetermined_handler_node
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

builder.add_node(
    "safety_agent",
    safety_agent_node
)

builder.add_node(
    "work_order_agent",
    work_order_agent_node
)

builder.add_node(
    "resource_planner",
    resource_planner_node
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

builder.add_conditional_edges(
    "rca",
    route_after_rca,
    {
        "undetermined_handler": "undetermined_handler",
        "safety_agent": "safety_agent"
    }
)

builder.add_edge("undetermined_handler", END)

builder.add_edge(
    "safety_agent",
    "work_order_agent"
)

builder.add_edge(
    "work_order_agent",
    "resource_planner"
)

builder.add_edge(
    "resource_planner",
    END
)

graph = builder.compile()

