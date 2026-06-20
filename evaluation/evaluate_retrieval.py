import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.rag.safety_retriever import retrieve_safety_documents
from src.rag.search_vector_index import search_documents
from src.rag.work_order_retriever import retrieve_work_order_documents
from src.agents.tools.retrieval_tool import retrieve_knowledge


DEFAULT_GOLDEN_SET = (
    Path(__file__).resolve().parent
    / "retrieval_golden_set.json"
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parent
    / "results"
    / "retrieval_results.json"
)


def citation_from_result(result):
    metadata = result.get("metadata", {})

    return (
        f"{metadata.get('source_file', 'unknown')} | "
        f"{metadata.get('heading', 'unknown')}"
    )


def deduplicate_results(results):
    unique = []
    seen = set()

    for result in results:
        result_id = result.get("id")
        citation = citation_from_result(result)
        key = result_id or citation

        if key in seen:
            continue

        seen.add(key)
        unique.append(result)

    return unique


def run_knowledge_retriever(case):
    query = case["query"]
    machine_id = case["machine_id"]

    maintenance_seeds = search_documents(
        query=query,
        top_k=5,
        document_category="maintenance",
        machine_id=machine_id
    )

    ticket_seeds = search_documents(
        query=query,
        top_k=3,
        document_category="historical_ticket",
        machine_id=machine_id
    )

    ranked_results = deduplicate_results(
        maintenance_seeds + ticket_seeds
    )

    final_results = retrieve_knowledge(
        query=query,
        machine_id=machine_id
    )

    return ranked_results, final_results


def run_safety_retriever(case):
    results = retrieve_safety_documents(
        query=case["query"],
        top_k=case.get("ranked_top_k", 5)
    )

    results = deduplicate_results(results)
    return results, results


def run_work_order_retriever(case):
    query = case["query"]
    machine_id = case["machine_id"]
    seed_top_k = case.get("ranked_top_k", 4)

    ranked_results = search_documents(
        query=query,
        top_k=seed_top_k,
        document_category="maintenance",
        machine_id=machine_id
    )

    final_results = retrieve_work_order_documents(
        query=query,
        machine_id=machine_id,
        seed_top_k=seed_top_k
    )

    return (
        deduplicate_results(ranked_results),
        deduplicate_results(final_results)
    )


def run_retriever(case):
    retriever = case["retriever"]

    if retriever == "knowledge":
        return run_knowledge_retriever(case)

    if retriever == "safety":
        return run_safety_retriever(case)

    if retriever == "work_order":
        return run_work_order_retriever(case)

    raise ValueError(
        f"Unsupported retriever: {retriever}"
    )


def precision_at_k(citations, relevant, k):
    if k <= 0:
        return 0.0

    retrieved = citations[:k]

    if not retrieved:
        return 0.0

    relevant_count = sum(
        citation in relevant
        for citation in retrieved
    )

    return relevant_count / len(retrieved)


def recall_at_k(citations, relevant, k):
    if not relevant:
        return 1.0 if not citations[:k] else 0.0

    retrieved_relevant = {
        citation
        for citation in citations[:k]
        if citation in relevant
    }

    return len(retrieved_relevant) / len(relevant)


def reciprocal_rank(citations, relevant, k):
    for rank, citation in enumerate(
        citations[:k],
        start=1
    ):
        if citation in relevant:
            return 1.0 / rank

    return 0.0


def dcg_at_k(citations, relevance, k):
    score = 0.0

    for rank, citation in enumerate(
        citations[:k],
        start=1
    ):
        gain = relevance.get(citation, 0)

        if gain:
            score += (
                (2 ** gain - 1)
                / math.log2(rank + 1)
            )

    return score


def ndcg_at_k(citations, relevance, k):
    actual = dcg_at_k(
        citations,
        relevance,
        k
    )

    ideal_gains = sorted(
        relevance.values(),
        reverse=True
    )[:k]

    ideal = sum(
        (2 ** gain - 1)
        / math.log2(rank + 1)
        for rank, gain in enumerate(
            ideal_gains,
            start=1
        )
    )

    if ideal == 0:
        return 1.0 if not citations[:k] else 0.0

    return actual / ideal


def calculate_group_coverage(
    final_citations,
    required_groups
):
    if not required_groups:
        return 1.0, []

    citation_set = set(final_citations)
    missing_groups = []

    for group in required_groups:
        if not citation_set.intersection(group):
            missing_groups.append(group)

    covered = len(required_groups) - len(
        missing_groups
    )

    return (
        covered / len(required_groups),
        missing_groups
    )


def find_forbidden_sources(
    final_results,
    forbidden_sources
):
    forbidden = set(forbidden_sources)
    found = set()

    for result in final_results:
        source_file = result.get(
            "metadata", {}
        ).get("source_file")

        if source_file in forbidden:
            found.add(source_file)

    return sorted(found)


def serialize_result(result, rank):
    metadata = result.get("metadata", {})

    return {
        "rank": rank,
        "citation": citation_from_result(result),
        "source_file": metadata.get("source_file"),
        "document_category": metadata.get(
            "document_category"
        ),
        "machine_id": metadata.get("machine_id"),
        "similarity": result.get("similarity")
    }


def evaluate_case(case):
    ranked_results, final_results = run_retriever(
        case
    )

    k = case.get(
        "ranked_top_k",
        len(ranked_results)
    )

    ranked_citations = [
        citation_from_result(result)
        for result in ranked_results
    ]

    final_citations = [
        citation_from_result(result)
        for result in final_results
    ]

    relevance = case.get("relevance", {})
    relevant = set(relevance)

    precision = precision_at_k(
        ranked_citations,
        relevant,
        k
    )

    recall = recall_at_k(
        ranked_citations,
        relevant,
        k
    )

    mrr = reciprocal_rank(
        ranked_citations,
        relevant,
        k
    )

    ndcg = ndcg_at_k(
        ranked_citations,
        relevance,
        k
    )

    group_coverage, missing_groups = (
        calculate_group_coverage(
            final_citations,
            case.get(
                "required_citation_groups", []
            )
        )
    )

    forbidden_sources = find_forbidden_sources(
        final_results,
        case.get("forbidden_source_files", [])
    )

    expect_empty = case.get(
        "expect_empty", False
    )

    if expect_empty:
        passed = not final_results
    else:
        passed = (
            group_coverage == 1.0
            and not forbidden_sources
            and mrr > 0.0
        )

    return {
        "id": case["id"],
        "name": case["name"],
        "retriever": case["retriever"],
        "expect_empty": expect_empty,
        "passed": passed,
        "metrics": {
            f"precision@{k}": round(
                precision, 4
            ),
            f"recall@{k}": round(
                recall, 4
            ),
            f"mrr@{k}": round(mrr, 4),
            f"ndcg@{k}": round(ndcg, 4),
            "final_group_coverage": round(
                group_coverage, 4
            )
        },
        "missing_citation_groups": missing_groups,
        "forbidden_sources_found": (
            forbidden_sources
        ),
        "ranked_results": [
            serialize_result(result, rank)
            for rank, result in enumerate(
                ranked_results,
                start=1
            )
        ],
        "final_result_count": len(final_results),
        "final_citations": final_citations
    }


def mean(values):
    if not values:
        return 0.0

    return sum(values) / len(values)


def metric_value(result, prefix):
    for name, value in result["metrics"].items():
        if name.startswith(prefix):
            return value

    return 0.0


def build_summary(results):
    positive_results = [
        result
        for result in results
        if not result["expect_empty"]
    ]

    return {
        "query_count": len(results),
        "passed": sum(
            result["passed"]
            for result in results
        ),
        "failed": sum(
            not result["passed"]
            for result in results
        ),
        "mean_precision": round(
            mean([
                metric_value(result, "precision@")
                for result in positive_results
            ]),
            4
        ),
        "mean_recall": round(
            mean([
                metric_value(result, "recall@")
                for result in positive_results
            ]),
            4
        ),
        "mean_mrr": round(
            mean([
                metric_value(result, "mrr@")
                for result in positive_results
            ]),
            4
        ),
        "mean_ndcg": round(
            mean([
                metric_value(result, "ndcg@")
                for result in positive_results
            ]),
            4
        ),
        "mean_final_group_coverage": round(
            mean([
                result["metrics"][
                    "final_group_coverage"
                ]
                for result in results
            ]),
            4
        )
    }


def print_case_result(result):
    status = "PASS" if result["passed"] else "FAIL"

    print(
        f"[{result['id']}] {status} - "
        f"{result['name']}"
    )

    metrics_text = ", ".join(
        f"{name}={value:.4f}"
        for name, value in result[
            "metrics"
        ].items()
    )

    print(f"  {metrics_text}")

    if result["missing_citation_groups"]:
        print("  Missing required citation groups:")

        for group in result[
            "missing_citation_groups"
        ]:
            print(f"    - {' OR '.join(group)}")

    if result["forbidden_sources_found"]:
        print(
            "  Forbidden sources: "
            + ", ".join(
                result["forbidden_sources_found"]
            )
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate PlantOps production retrievers "
            "against a golden citation set."
        )
    )

    parser.add_argument(
        "--golden-set",
        type=Path,
        default=DEFAULT_GOLDEN_SET
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT
    )

    parser.add_argument(
        "--query-id",
        action="append",
        help=(
            "Run only a selected query ID. May be "
            "provided multiple times."
        )
    )

    return parser.parse_args()


def main():
    args = parse_args()

    golden_set = json.loads(
        args.golden_set.read_text(
            encoding="utf-8"
        )
    )

    cases = golden_set["queries"]

    if args.query_id:
        selected_ids = set(args.query_id)
        cases = [
            case
            for case in cases
            if case["id"] in selected_ids
        ]

        missing_ids = selected_ids - {
            case["id"]
            for case in cases
        }

        if missing_ids:
            raise ValueError(
                "Unknown query IDs: "
                + ", ".join(sorted(missing_ids))
            )

    results = []

    for index, case in enumerate(
        cases,
        start=1
    ):
        print(
            f"\nRunning {index}/{len(cases)}: "
            f"{case['id']}"
        )

        result = evaluate_case(case)
        results.append(result)
        print_case_result(result)

    summary = build_summary(results)

    report = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "golden_set_version": golden_set.get(
            "version"
        ),
        "summary": summary,
        "results": results
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    args.output.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8"
    )

    print("\n" + "=" * 72)
    print(
        f"RETRIEVAL EVALUATION: "
        f"{summary['passed']}/{summary['query_count']} passed"
    )
    print(
        f"Mean precision: {summary['mean_precision']:.4f}"
    )
    print(
        f"Mean recall:    {summary['mean_recall']:.4f}"
    )
    print(
        f"Mean MRR:       {summary['mean_mrr']:.4f}"
    )
    print(
        f"Mean nDCG:      {summary['mean_ndcg']:.4f}"
    )
    print(
        "Group coverage: "
        f"{summary['mean_final_group_coverage']:.4f}"
    )
    print(f"Saved report: {args.output}")
    print("=" * 72)


if __name__ == "__main__":
    main()
