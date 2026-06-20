import json
from pathlib import Path

JUDGE_RESULTS_DIR = Path("evaluation/results/llm_judge")
OUTPUT_PATH = JUDGE_RESULTS_DIR / "llm_judge_final_summary.json"

DIMENSIONS = [
    "groundedness",
    "rca_quality",
    "citation_quality",
    "safety_quality",
    "work_order_quality",
    "resource_quality",
    "abstention_quality",
]

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)

def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent = 2)

def main():
    judge_files = sorted(
        path
        for path in JUDGE_RESULTS_DIR.glob("E2E-*_judge.json")
    )

    if not judge_files:
        raise FileNotFoundError(
            "No per-scenario judge files found in evaluation/results/llm_judge"
        )
    
    items = []

    for judge_file in judge_files:
        result = load_json(judge_file)

        items.append(
            {
                 "scenario_id": judge_file.stem.replace("_judge", ""),
                "judge_file": str(judge_file),
                "overall_pass": result.get("overall_pass", False),
                "scores": {
                    dimension: result.get(dimension, {}).get("score")
                    for dimension in DIMENSIONS
                },
                "hallucination_flags": result.get("hallucination_flags", []),
                "missing_items": result.get("missing_items", []),
                "pass_fail_reasons": result.get("pass_fail_reasons", []),
                "final_comment": result.get("final_comment", "")
            }
        )

    total = len(items)
    passed = sum(item["overall_pass"] for item in items)
    failed = total - passed

    mean_scores = {}

    for dimension in DIMENSIONS:
        scores = [
            item["scores"][dimension]
            for item in items
            if isinstance(item["scores"][dimension], int)
        ]

        mean_scores[dimension] = (
            sum(scores) / len(scores)
            if scores
            else 0
        )
    failures = [
        item for item in items if not item["overall_pass"]
    ]

    summary = {
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / total if total else 0,
        "mean_dimension_scores": mean_scores,
        "failures": failures,
        "items": items
    }

    save_json(OUTPUT_PATH, summary)

    print("\n" + "=" * 69)
    print("FINAL LLM-AS-JUDGE EVALUATION")
    print("=" * 60)
    print(f"Total scenarios: {total}")
    print(f"Passed:          {passed}")
    print(f"Failed:          {failed}")
    print(f"Pass rate:       {summary['pass_rate']:.2%}")

    print("\nMean dimension scores:")

    for dimension, score in mean_scores.items():
        print(f"- {dimension}: {score:.2f}")
    
    if failures:
        print("\nFailures:")

        for failure in failures:
            print(f"- {failure['scenario_id']}")

            for reason in failure.get("pass_fail_reasons", []):
                print(f"  - {reason}")
            
            for flag in failure.get("hallucination_flags", []):
                print(f"  - Hallucination flag: {flag}")
            
            for missing in failure.get("missing_items", []):
                print(f"  - Missing: {missing}")
    else:
        print("\nFailures: none")
    
    print(f"\nSaved final summary: {OUTPUT_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()
