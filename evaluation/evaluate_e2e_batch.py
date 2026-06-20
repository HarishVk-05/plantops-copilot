import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RESULTS_DIR = Path("evaluation/results/e2e")
REPORTS_DIR = RESULTS_DIR / "Report"

def normalize(value):
    return " ".join(str(value).lower().split())

def ensure_dirs():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(path):
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)

def save_json(path, data):
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(data, file, indent = 2)

def collect_final_citations(result):
    citations = []

    rca_report = result.get("rca_report", {})
    citations.extend(rca_report.get("citations", []))

    for report_name in [
        "safety_report",
        "work_order_report"
    ]:
        report = result.get(report_name, {})

        for value in report.values():
            if not isinstance(value, list):
                continue

            for item in value:
                if isinstance(item, dict) and item.get("citation"):
                    citations.append(item["citation"])
    return citations

def collect_retrieved_sources(result):
    sources = []

    for document in result.get("retrieved_docs", []):
        metadata = document.get("metadata", {})

        source_file = metadata.get("source_file")
        heading = metadata.get("heading")

        if source_file and heading:
            sources.append(f"{source_file} | {heading}")
        elif source_file:
            sources.append(source_file)
    
    return sources

def item_texts(report, field):
    values = report.get(field, [])

    if not isinstance(values, list):
        return []

    return [
        item.get("text", "")
        for item in values
        if isinstance(item, dict)
    ]


def contains_expected_text(actual_texts, expected_text):
    expected_norm = normalize(expected_text)

    return any(
        expected_norm in normalize(text)
        or normalize(text) in expected_norm
        for text in actual_texts
    )


def evaluate_result(scenario, result):
    expected = scenario["expected"]
    problems = []

    rca_report = result.get("rca_report", {})
    work_order = result.get("work_order_report", {})
    safety_report = result.get("safety_report", {})
    resource_plan = result.get("resource_plan", {})

    root_cause = rca_report.get("likely_root_cause", "")

    if normalize(root_cause) != normalize(expected["root_cause"]):
        problems.append(
            f"Expected root cause {expected['root_cause']!r}, "
            f"received {root_cause!r}."
        )

    final_citations = collect_final_citations(result)
    retrieved_sources = collect_retrieved_sources(result)

    combined_source_text = normalize(
        " ".join(final_citations + retrieved_sources)
    )

    for required in expected.get("required_citation_substrings", []):
        if normalize(required) not in normalize(" ".join(final_citations)):
            problems.append(
                f"Required final citation substring missing: {required}"
            )

    for forbidden in expected.get("forbidden_source_substrings", []):
        if normalize(forbidden) in combined_source_text:
            problems.append(
                f"Forbidden source appeared in final/retrieved evidence: "
                f"{forbidden}"
            )

    if expected.get("expect_empty_recommendations"):
        if rca_report.get("recommendations"):
            problems.append(
                "Expected empty RCA recommendations for undetermined case."
            )

        if rca_report.get("citations"):
            problems.append(
                "Expected empty RCA citations for undetermined case."
            )

        maintenance_steps = work_order.get("maintenance_steps", [])
        required_tools = work_order.get("required_tools", [])
        required_skills = work_order.get("required_skills", [])
        technician_candidates = resource_plan.get("technician_candidates", [])
        compatible_spares = resource_plan.get("compatible_spare_parts", [])

        eligible_technicians = [
            candidate
            for candidate in technician_candidates
            if isinstance(candidate, dict)
            and candidate.get("eligible")
        ]

        if maintenance_steps:
            problems.append(
                "Expected no corrective maintenance steps for undetermined case."
            )
        
        if required_tools:
            problems.append(
                "Expected no required tools for undetermined case."
            )
        
        if required_skills:
            problems.append(
                "Expected no required skills for undetermined case."
            )
        
        if eligible_technicians:
            problems.append(
                "Expected no eligible technician assignment for undetermined case."
            )
        
        if compatible_spares:
            problems.append(
                "Expected no spare-part plan for undetermined case."
            )
        
        return problems

    min_steps = expected.get("min_maintenance_steps")

    if min_steps is not None:
        actual_steps = work_order.get("maintenance_steps", [])

        if len(actual_steps) < min_steps:
            problems.append(
                f"Expected at least {min_steps} maintenance steps, "
                f"received {len(actual_steps)}."
            )

    tool_texts = item_texts(work_order, "required_tools")

    for tool in expected.get("required_tools", []):
        if not contains_expected_text(tool_texts, tool):
            problems.append(
                f"Required tool missing from work order: {tool}"
            )

    skill_texts = item_texts(work_order, "required_skills")

    for skill in expected.get("required_skills", []):
        if not contains_expected_text(skill_texts, skill):
            problems.append(
                f"Required skill missing from work order: {skill}"
            )

    loto_steps = safety_report.get("required_safety_steps", [])
    ppe_items = safety_report.get("required_ppe", [])

    min_loto_steps = expected.get("min_loto_steps")

    if min_loto_steps is not None and len(loto_steps) < min_loto_steps:
        problems.append(
            f"Expected at least {min_loto_steps} LOTO steps, "
            f"received {len(loto_steps)}."
        )

    min_ppe_items = expected.get("min_ppe_items")

    if min_ppe_items is not None and len(ppe_items) < min_ppe_items:
        problems.append(
            f"Expected at least {min_ppe_items} PPE items, "
            f"received {len(ppe_items)}."
        )

    eligible_technician = expected.get("eligible_technician")

    if eligible_technician:
        candidates = resource_plan.get("technician_candidates", [])

        matched = any(
            candidate.get("eligible")
            and normalize(candidate.get("tech_name", ""))
            == normalize(eligible_technician)
            for candidate in candidates
        )

        if not matched:
            problems.append(
                f"Expected eligible technician {eligible_technician!r}."
            )

    warnings = resource_plan.get("resource_warnings", [])
    warning_text = normalize(" ".join(warnings))

    for warning in expected.get("resource_warning_substrings", []):
        if normalize(warning) not in warning_text:
            problems.append(
                f"Expected resource warning missing: {warning}"
            )

    return problems


def run_scenario(scenario, force=False):
    report_path = REPORTS_DIR / f"{scenario['id']}.json"

    if report_path.exists() and not force:
        result = load_json(report_path)

        return {
            "id": scenario["id"],
            "name": scenario["name"],
            "cached": True,
            "elapsed_seconds": 0,
            "result": result
        }

    from src.agents.graph.plantops_graph import graph

    started_at = perf_counter()

    result = graph.invoke(scenario["input"])

    elapsed = perf_counter() - started_at

    save_json(report_path, result)

    return {
        "id": scenario["id"],
        "name": scenario["name"],
        "cached": False,
        "elapsed_seconds": elapsed,
        "result": result
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch",
        default="evaluation/e2e_batches/batch1.json"
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun scenarios even if cached reports exist."
    )

    args = parser.parse_args()

    ensure_dirs()

    scenarios = load_json(args.batch)

    summaries = []

    for index, scenario in enumerate(scenarios, start=1):
        print(
            f"\n[{index}/{len(scenarios)}] "
            f"{scenario['id']} - {scenario['name']}"
        )

        try:
            run_output = run_scenario(
                scenario,
                force=args.force
            )

            result = run_output["result"]
            problems = evaluate_result(
                scenario,
                result
            )

            passed = not problems

            root_cause = result.get(
                "rca_report",
                {}
            ).get(
                "likely_root_cause",
                ""
            )

            status = "PASS" if passed else "FAIL"

            cached_label = (
                "cached"
                if run_output["cached"]
                else "new"
            )

            print(f"Status: {status} ({cached_label})")
            print(f"Root cause: {root_cause}")
            print(
                f"Elapsed: "
                f"{run_output['elapsed_seconds']:.1f}s"
            )

            for problem in problems:
                print(f"- {problem}")

            summaries.append(
                {
                    "id": scenario["id"],
                    "name": scenario["name"],
                    "passed": passed,
                    "cached": run_output["cached"],
                    "elapsed_seconds":
                        run_output["elapsed_seconds"],
                    "root_cause": root_cause,
                    "problems": problems,
                    "report_path": str(
                        REPORTS_DIR
                        / f"{scenario['id']}.json"
                    )
                }
            )

        except Exception as exc:
            print("Status: ERROR")
            print(str(exc))

            summaries.append(
                {
                    "id": scenario["id"],
                    "name": scenario["name"],
                    "passed": False,
                    "cached": False,
                    "elapsed_seconds": 0,
                    "root_cause": "Pipeline error",
                    "problems": [str(exc)],
                    "report_path": None
                }
            )

    passed_count = sum(
        item["passed"]
        for item in summaries
    )

    summary = {
        "batch_file": args.batch,
        "passed": passed_count,
        "total": len(summaries),
        "scenarios": summaries
    }

    summary_path = (
        RESULTS_DIR
        / f"{Path(args.batch).stem}_summary.json"
    )

    save_json(summary_path, summary)

    print("\n" + "=" * 72)
    print(
        f"E2E BATCH RESULT: "
        f"{passed_count}/{len(summaries)} passed"
    )
    print(f"Saved summary: {summary_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()