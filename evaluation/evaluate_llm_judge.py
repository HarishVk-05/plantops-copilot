import argparse
import json
import sys
from pathlib import Path
from typing import List

from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from src.agents.llm import llm, invoke_llm


REPORTS_DIR = PROJECT_ROOT / "evaluation" / "results" / "e2e" / "reports"
JUDGE_RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results" / "llm_judge"

class JudgeDimension(BaseModel):
    score: int = Field(ge=1, le=5)
    rationale: str

class LLMJudgeReport(BaseModel):
    overall_pass: bool

    groundedness: JudgeDimension
    rca_quality: JudgeDimension
    citation_quality: JudgeDimension
    safety_quality: JudgeDimension
    work_order_quality: JudgeDimension
    resource_quality: JudgeDimension
    abstention_quality: JudgeDimension

    hallucination_flags: List[str] = Field(default_factory=list)
    missing_items: List[str] = Field(default_factory=list)
    final_comment: str

structured_judge_llm = llm.with_structured_output(LLMJudgeReport)

JUDGE_SYSTEM_PROMPT = """
You are an expert evaluator for an industrial maintenance AI agent.

You judge exactly ONE scenario report at a time.

You must evaluate the report only from the provided scenario, evidence package,
retrieved evidence summary, and final agent outputs.

Do not use outside knowledge.
Do not treat the user's claim as evidence.
Do not reward unsupported conclusions.

Score each dimension from 1 to 5 using the anchors below.

GROUNDING SCORE:
5 = Every important claim is directly supported by telemetry, alarms, retrieved documents, or historical tickets.
4 = Main claims are supported; only minor wording is broader than the evidence.
3 = Root conclusion is mostly supported, but some supporting statements are weak or generic.
2 = Several important claims are not clearly supported by evidence.
1 = Main conclusion is unsupported, contradicted, or based mainly on the user prompt.

RCA QUALITY SCORE:
5 = Selects the correct single root cause, handles alternatives, and explains why competing causes are weaker.
4 = Correct root cause with minor gaps in comparison or reasoning.
3 = Plausible root cause but reasoning is incomplete or weakly distinguishes alternatives.
2 = Root cause is questionable, ambiguous, combined, or weakly justified.
1 = Wrong root cause, unsafe confirmation of user hypothesis, or failure to abstain when required.

CITATION QUALITY SCORE:
5 = Citations precisely support the root cause, recommendations, safety steps, tools, skills, and work order.
4 = Citations support the main answer with only minor citation granularity issues.
3 = Citations are relevant but incomplete, generic, or not attached to all important claims.
2 = Some citations are irrelevant, missing for important claims, or weakly supportive.
1 = Citations are absent, fabricated, cross-machine contaminated, or do not support the conclusion.

SAFETY QUALITY SCORE:
5 = Complete mandatory LOTO/PPE and relevant prohibited/supervisor controls are present and cited.
4 = Mandatory safety controls are present; only minor optional controls are missing or extra.
3 = Basic safety controls are present but incomplete or somewhat noisy.
2 = Important safety controls are missing, poorly filtered, or mixed with irrelevant controls.
1 = Missing LOTO/PPE for planned maintenance, unsafe advice, or safety-critical contradiction.

WORK ORDER QUALITY SCORE:
5 = Work order is actionable, specific, correctly tied to root cause, and includes steps, tools, skills, success criteria.
4 = Work order is usable with minor missing detail.
3 = Work order is partially actionable but generic or incomplete.
2 = Work order is weak, missing major required items, or not well tied to the RCA.
1 = Work order is unsafe, unsupported, wrong-machine, or generated when the agent should abstain.

RESOURCE QUALITY SCORE:
5 = Correct tools, skills, technician eligibility, spares, and warnings are matched.
4 = Correct resource matching with minor omissions.
3 = Basic resource plan is usable but incomplete.
2 = Major tools/skills/technician/spare warnings are missing or incorrect.
1 = Resource plan is misleading, unsafe, or assigns resources despite unsupported RCA.

ABSTENTION QUALITY SCORE:
5 = Correctly abstains when evidence is insufficient and avoids corrective recommendations/work orders.
4 = Abstains correctly with minor wording issues.
3 = Partially abstains but leaves some unnecessary or vague action items.
2 = Claims uncertainty but still recommends corrective maintenance without support.
1 = Fails to abstain, confirms unsupported user claim, or fabricates a root cause.

OVERALL PASS GUIDANCE:
You should set overall_pass=True only when the report is acceptable for an
industrial maintenance assistant.

However, your overall_pass value will be checked by deterministic hard gates
afterward, so score each dimension honestly.

Hard failure examples:
- Unsupported or wrong root cause.
- Cross-machine evidence used for final conclusion.
- Missing LOTO/PPE when maintenance work is planned.
- Fabricated citations.
- Corrective work order generated for an Undetermined case.
- User hypothesis confirmed without evidence.
"""

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)
    
def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent= 2)

def load_scenarios_from_batch(batch_path: Path):
    return load_json(batch_path)

def compact_text(text, max_chars= 700):
    if text is None:
        return None
    
    text = str(text)

    if len(text) <= max_chars:
        return text
    
    return text[:max_chars] + "...[truncated]"

def compact_evidence_package(evidence_package: dict):
    if not isinstance(evidence_package, dict):
        return {}
    
    document_findings = []

    for finding in evidence_package.get("document_findings", []):
        document_findings.append(
            {
                "citation": finding.get("citation"),
                "category": finding.get("category"),
                "similarity": finding.get("similarity"),
                "snippet": compact_text(finding.get("snippet"), 500)
            }
        )
    
    return {
        "machine_id": evidence_package.get("machine_id"),
        "evidence_status": evidence_package.get("evidence_status"),
        "sensor_findings": evidence_package.get("sensor_findings", []),
        "alarm_findings": evidence_package.get("alarm_findings", {}),
        "document_findings": document_findings[:25]
    }

def compact_retrieved_docs(result: dict):
    docs = []

    for doc in result.get("retrieved_docs", []):
        metadata = doc.get("metadata", {})

        docs.append(
            {
                "source_file": metadata.get("source_file"),
                "heading": metadata.get("heading"),
                "document_category": metadata.get("document_category"),
                "source_type": metadata.get("source_type"),
                "similarity": doc.get("similarity")
            }
        )
    
    return docs[:35]

def compact_report(result: dict):
    return {
        "evidence_package": compact_evidence_package(
            result.get("evidence_package", {})
        ),
        "evidence_analysis": result.get("evidence_analysis", {}),
        "retrieved_document_headings": compact_retrieved_docs(result),
        "rca_report": result.get("rca_report", {}),
        "safety_report": result.get("safety_report", {}),
        "work_order_report": result.get("work_order_report", {}),
        "resource_plan": result.get("resource_plan", {}),
    }

def build_judge_prompt(scenario: dict, report: dict):
    compacted = compact_report(report)

    return f"""
SCENARIO:
{json.dumps(scenario, indent=2)}

AGENT FINAL REPORT AND EVIDENCE SUMMARY:
{json.dumps(compacted, indent=2)}

Evaluate this ONE scenario using the rubric.

Return a strict structured judgment.

Guidance:
- Use the expected fields from the scenario as the evaluation target.
- Equivalent wording is acceptable.
- Penalize unsupported or cross-machine evidence.
- Penalize missing safety controls when maintenance is planned.
- For Undetermined cases, reward abstention and absence of corrective work orders.
"""

def _score(judge_result: dict, dimension: str) -> int:
    value = judge_result.get(dimension, {})

    if not isinstance(value, dict):
        return 1

    try:
        return int(value.get("score", 1))
    except Exception:
        return 1


def _is_expected_undetermined(scenario: dict) -> bool:
    expected_root = (
        scenario
        .get("expected", {})
        .get("root_cause", "")
        .strip()
        .lower()
    )

    return expected_root == "undetermined"


def _has_corrective_work(report: dict) -> bool:
    rca_report = report.get("rca_report", {})
    work_order = report.get("work_order_report", {})

    recommendations = rca_report.get("recommendations", [])
    maintenance_steps = work_order.get("maintenance_steps", [])

    return bool(recommendations or maintenance_steps)


def _compute_overall_pass(
        scenario: dict,
        report: dict,
        judge_result: dict
) -> tuple[bool, list[str]]:
    """
    Deterministic overall pass policy.

    The LLM judge scores dimensions, but Python decides pass/fail.
    This prevents inconsistent weighting across scenarios.
    """

    reasons = []

    expected_undetermined = _is_expected_undetermined(scenario)
    corrective_work_present = _has_corrective_work(report)

    groundedness = _score(judge_result, "groundedness")
    rca_quality = _score(judge_result, "rca_quality")
    citation_quality = _score(judge_result, "citation_quality")
    safety_quality = _score(judge_result, "safety_quality")
    work_order_quality = _score(judge_result, "work_order_quality")
    resource_quality = _score(judge_result, "resource_quality")
    abstention_quality = _score(judge_result, "abstention_quality")

    # Universal hard gates.
    if groundedness <= 2:
        reasons.append(
            "Hard gate failed: groundedness score must be at least 3."
        )

    if rca_quality <= 2:
        reasons.append(
            "Hard gate failed: RCA quality score must be at least 3."
        )

    if judge_result.get("hallucination_flags"):
        reasons.append(
            "Hard gate failed: hallucination flags were reported."
        )

    # Determined RCA cases.
    if not expected_undetermined:
        if citation_quality <= 2:
            reasons.append(
                "Hard gate failed: citation quality must be at least 3 "
                "for determined RCA cases."
            )

        if corrective_work_present and safety_quality <= 2:
            reasons.append(
                "Hard gate failed: safety quality must be at least 3 "
                "when maintenance work is planned."
            )

        if corrective_work_present and work_order_quality <= 2:
            reasons.append(
                "Hard gate failed: work order quality must be at least 3 "
                "when maintenance work is planned."
            )

        if corrective_work_present and resource_quality <= 2:
            reasons.append(
                "Hard gate failed: resource quality must be at least 3 "
                "when maintenance work is planned."
            )

        if corrective_work_present and safety_quality == 1:
            reasons.append(
                "Hard gate failed: safety_quality=1 is never acceptable "
                "when maintenance work is planned."
            )

    # Undetermined / abstention cases.
    if expected_undetermined:
        if abstention_quality <= 2:
            reasons.append(
                "Hard gate failed: abstention quality must be at least 3 "
                "for expected Undetermined cases."
            )

        if corrective_work_present:
            reasons.append(
                "Hard gate failed: corrective work was generated for an "
                "expected Undetermined case."
            )

    return len(reasons) == 0, reasons

def find_cached_report_path(scenario_id: str) -> Path:
    """
    Find the cached E2E report for a scenario.

    Primary expected path:
      evaluation/results/e2e/reports/E2E-001.json

    Fallback:
      recursively search under evaluation/results/e2e
    """

    expected_path = REPORTS_DIR / f"{scenario_id}.json"

    if expected_path.exists():
        return expected_path

    search_root = PROJECT_ROOT / "evaluation" / "results" / "e2e"

    matches = sorted(
        path
        for path in search_root.rglob(f"{scenario_id}*.json")
        if "judge" not in path.name.lower()
        and "summary" not in path.name.lower()
    )

    if matches:
        return matches[0]

    raise FileNotFoundError(
        "Cached E2E report not found.\n"
        f"Expected: {expected_path}\n"
        f"Searched under: {search_root}\n"
        f"Scenario ID: {scenario_id}"
    )

def evaluate_one_scenario(scenario: dict, force: bool = False):
    scenario_id = scenario["id"]

    report_path = find_cached_report_path(scenario_id)
    judge_path = JUDGE_RESULTS_DIR / f"{scenario_id}_judge.json"

    if judge_path.exists() and not force:
        return {
            "scenario_id": scenario_id,
            "cached": True,
            "judge_result": load_json(judge_path),
            "judge_path": str(judge_path),
        }
    report = load_json(report_path)

    prompt = build_judge_prompt(
        scenario=scenario,
        report = report
    )

    response = invoke_llm(
        structured_judge_llm,
        [
            ("system", JUDGE_SYSTEM_PROMPT),
            ("human", prompt)
        ],
        "LLM judge evaluation"
    )

    judge_result = response.model_dump()

    computed_pass, pass_fail_reasons = _compute_overall_pass(
        scenario=scenario,
        report=report,
        judge_result=judge_result
    )

    judge_result["llm_report_overall_pass"] = judge_result.get(
        "overall_pass"
    )

    judge_result["overall_pass"] = computed_pass
    judge_result["pass_fail_reasons"] = pass_fail_reasons

    save_json(judge_path, judge_result)

    return {
        "scenario_id": scenario_id,
        "cached": False,
        "judge_result": judge_result,
        "judge_path": str(judge_path),
    }

def aggregate_judge_results(items):
    total = len(items)

    passed = sum(
        1
        for item in items
        if item["judge_result"].get("overall_pass")
    )

    dimension_names = [
        "groundedness",
        "rca_quality",
        "citation_quality",
        "safety_quality",
        "work_order_quality",
        "resource_quality",
        "abstention_quality",
    ]

    dimension_scores = {}

    for dimension in dimension_names:
        scores = [
            item["judge_result"][dimension]["score"]
            for item in items
            if dimension in item["judge_result"]
        ]

        dimension_scores[dimension] = (
            sum(scores) / len(scores)
            if scores
            else 0
        )

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total if total else 0,
        "mean_dimension_scores": dimension_scores,
        "items": items,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--batch",
        required=True,
        help="Path to E2E batch JSON file."
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Rerun judge even if cached judge outputs exist."
    )

    args = parser.parse_args()

    batch_path = Path(args.batch)

    scenarios = load_scenarios_from_batch(batch_path)

    JUDGE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    for index, scenario in enumerate(scenarios, start=1):
        print(
            f"\n[{index}/{len(scenarios)}] "
            f"Judging {scenario['id']} - {scenario['name']}"
        )

        try:
            item = evaluate_one_scenario(
                scenario=scenario,
                force=args.force
            )

            judge_result = item["judge_result"]

            status = (
                "PASS"
                if judge_result.get("overall_pass")
                else "FAIL"
            )

            cached_label = (
                "cached"
                if item["cached"]
                else "new"
            )

            print(f"Status: {status} ({cached_label})")
            print(
                "Scores: "
                f"groundedness={judge_result['groundedness']['score']}, "
                f"rca={judge_result['rca_quality']['score']}, "
                f"citations={judge_result['citation_quality']['score']}, "
                f"safety={judge_result['safety_quality']['score']}, "
                f"work_order={judge_result['work_order_quality']['score']}, "
                f"resources={judge_result['resource_quality']['score']}, "
                f"abstention={judge_result['abstention_quality']['score']}"
            )

            if judge_result.get("hallucination_flags"):
                print("Hallucination flags:")
                for flag in judge_result["hallucination_flags"]:
                    print(f"- {flag}")

            if judge_result.get("missing_items"):
                print("Missing items:")
                for item_text in judge_result["missing_items"]:
                    print(f"- {item_text}")

            print(f"Comment: {judge_result.get('final_comment', '')}")

            results.append(item)

        except Exception as exc:
            print("Status: ERROR")
            print(str(exc))

            results.append(
                {
                    "scenario_id": scenario["id"],
                    "cached": False,
                    "judge_result": {
                        "overall_pass": False,
                        "error": str(exc)
                    },
                    "judge_path": None,
                }
            )

    summary = aggregate_judge_results(results)

    summary_path = (
        JUDGE_RESULTS_DIR
        / f"{batch_path.stem}_judge_summary.json"
    )

    save_json(summary_path, summary)

    print("\n" + "=" * 72)
    print("LLM-AS-JUDGE BATCH SUMMARY")
    print("=" * 72)
    print(f"Batch:     {batch_path}")
    print(f"Passed:    {summary['passed']}/{summary['total']}")
    print(f"Pass rate: {summary['pass_rate']:.2%}")

    print("\nMean dimension scores:")

    for name, score in summary["mean_dimension_scores"].items():
        print(f"- {name}: {score:.2f}")

    print(f"\nSaved summary: {summary_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()