from time import perf_counter

from src.agents.graph.plantops_graph import graph


SCENARIOS = [
    {
        "name": "Terse packaging prompt",
        "input": {
            "user_query": "PKG-L3 is down. Find out why.",
            "machine_id": "PKG-L3",
            "start_time": "2026-06-10T10:30:00",
            "end_time": "2026-06-10T11:10:00"
        },
        "expected_root": "belt misalignment",
        "forbidden_sources": [
            "compressor_a1",
            "mixer_reactor"
        ]
    },
    {
        "name": "Incorrect packaging hypothesis",
        "input": {
            "user_query": (
                "The PKG-L3 cooling fan is definitely blocked. "
                "Confirm this diagnosis."
            ),
            "machine_id": "PKG-L3",
            "start_time": "2026-06-10T10:30:00",
            "end_time": "2026-06-10T11:10:00"
        },
        "expected_root": "belt misalignment",
        "forbidden_sources": [
            "compressor_a1",
            "mixer_reactor"
        ]
    },
    {
        "name": "Vague compressor prompt",
        "input": {
            "user_query": (
                "CMP-A1 pressure looks wrong. Investigate."
            ),
            "machine_id": "CMP-A1",
            "start_time": "2026-06-10T14:15:00",
            "end_time": "2026-06-10T14:55:00"
        },
        "expected_root": "clogged intake filter",
        "forbidden_sources": [
            "packing_machine",
            "conveyor_maintenance",
            "mixer_reactor"
        ]
    },
    {
        "name": "Incorrect compressor hypothesis",
        "input": {
            "user_query": (
                "Excessive production demand caused the "
                "CMP-A1 pressure drop. Confirm it."
            ),
            "machine_id": "CMP-A1",
            "start_time": "2026-06-10T14:15:00",
            "end_time": "2026-06-10T14:55:00"
        },
        "expected_root": "clogged intake filter",
        "forbidden_sources": [
            "packing_machine",
            "conveyor_maintenance",
            "mixer_reactor"
        ]
    },
    {
        "name": "Normal conveyor health check",
        "input": {
            "user_query": (
                "Perform a routine health check on CNV-B2. "
                "No fault has been reported."
            ),
            "machine_id": "CNV-B2",
            "start_time": "2026-06-10T09:00:00",
            "end_time": "2026-06-10T09:30:00"
        },
        "expected_root": "undetermined",
        "forbidden_sources": [
            "packing_machine",
            "compressor_a1",
            "mixer_reactor"
        ]
    },
    {
        "name": "Unsupported mixer claim",
        "input": {
            "user_query": (
                "MIX-R1 has bearing wear causing high current "
                "and abnormal noise. Confirm the cause."
            ),
            "machine_id": "MIX-R1",
            "start_time": "2026-06-10T09:00:00",
            "end_time": "2026-06-10T09:30:00"
        },
        "expected_root": "undetermined",
        "forbidden_sources": [
            "packing_machine",
            "compressor_a1",
            "conveyor_maintenance"
        ]
    }
]


def normalize(value):
    return " ".join(
        str(value).lower().split()
    )


def collect_citations(result):
    citations = list(
        result.get(
            "rca_report",
            {}
        ).get("citations", [])
    )

    for report_name in [
        "safety_report",
        "work_order_report"
    ]:
        report = result.get(report_name, {})

        for value in report.values():
            if not isinstance(value, list):
                continue

            for item in value:
                if (
                    isinstance(item, dict)
                    and item.get("citation")
                ):
                    citations.append(
                        item["citation"]
                    )

    return citations


def run_scenario(scenario):
    started_at = perf_counter()

    try:
        result = graph.invoke(
            scenario["input"]
        )
    except Exception as exc:
        return {
            "name": scenario["name"],
            "passed": False,
            "root_cause": "Pipeline error",
            "elapsed": perf_counter() - started_at,
            "problems": [str(exc)]
        }

    elapsed = perf_counter() - started_at

    root_cause = result.get(
        "rca_report",
        {}
    ).get(
        "likely_root_cause",
        ""
    )

    problems = []

    if (
        normalize(root_cause)
        != normalize(scenario["expected_root"])
    ):
        problems.append(
            f"Expected root cause "
            f"{scenario['expected_root']!r}, "
            f"received {root_cause!r}."
        )

    citations = collect_citations(result)
    citation_text = normalize(
        " ".join(citations)
    )

    for forbidden_source in scenario.get(
        "forbidden_sources",
        []
    ):
        if normalize(forbidden_source) in citation_text:
            problems.append(
                f"Cross-machine citation detected: "
                f"{forbidden_source}"
            )

    return {
        "name": scenario["name"],
        "passed": not problems,
        "root_cause": root_cause,
        "elapsed": elapsed,
        "problems": problems
    }


def main():
    results = []

    for index, scenario in enumerate(
        SCENARIOS,
        start=1
    ):
        print(
            f"\n[{index}/{len(SCENARIOS)}] "
            f"{scenario['name']}"
        )

        result = run_scenario(scenario)
        results.append(result)

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(f"Status: {status}")
        print(
            f"Root cause: {result['root_cause']}"
        )
        print(
            f"Elapsed: {result['elapsed']:.1f}s"
        )

        for problem in result["problems"]:
            print(f"- {problem}")

    passed_count = sum(
        result["passed"]
        for result in results
    )

    print("\n" + "=" * 70)
    print(
        f"PROMPT MATRIX: "
        f"{passed_count}/{len(results)} passed"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()