from pprint import pprint

from src.agents.graph.plantops_graph import graph

result = graph.invoke(
    {
        "user_query": 
        "PKG-L3 stopped unexpectedly due to overheating",

        "machine_id": 
        "PKG-L3"
    }
)

pprint(
    result["rca_report"]
    )