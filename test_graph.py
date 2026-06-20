from pprint import pprint

from src.agents.graph.plantops_graph import graph


SCENARIOS = [
    {
        "name": "Packaging machine overheating",
        "input": {
            "user_query": (
                "PKG-L3 stopped unexpectedly due to "
                "overheating"
            ),
            "machine_id": "PKG-L3",
            "start_time": "2026-06-10T10:30:00",
            "end_time": "2026-06-10T11:10:00"
        }
    },
    {
        "name": "Compressor low pressure",
        "input": {
            "user_query": (
                "CMP-A1 has low discharge pressure during "
                "high production demand"
            ),
            "machine_id": "CMP-A1",
            "start_time": "2026-06-10T14:15:00",
            "end_time": "2026-06-10T14:55:00"
        }
    }
]


def run_scenario(scenario):
    print("\n" + "=" * 90)
    print(f"SCENARIO: {scenario['name']}")
    print("=" * 90)

    result = graph.invoke(
        scenario["input"]
    )

    print("\n===== RETRIEVED DOCUMENT HEADINGS =====")

    for document in result.get(
        "retrieved_docs",
        []
    ):
        metadata = document.get("metadata", {})

        print(
            metadata.get("source_file"),
            "|",
            metadata.get("heading")
        )

    print("\n===== EVIDENCE ANALYSIS =====")
    pprint(result["evidence_analysis"])

    print("\n===== RCA =====")
    pprint(result["rca_report"])

    print("\n===== SAFETY =====")
    pprint(result["safety_report"])

    print("\n===== WORK ORDER =====")
    pprint(result["work_order_report"])

    print("\n===== RESOURCE PLAN =====")
    pprint(result["resource_plan"])


def main():
    for scenario in SCENARIOS:
        run_scenario(scenario)


if __name__ == "__main__":
    main()