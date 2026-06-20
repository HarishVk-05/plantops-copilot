# PlantOps Retrieval Evaluation

This evaluation runs entirely against the local ChromaDB index. It does not call
Groq or any other LLM API.

## Run all 15 queries

From the project root:

```bash
python evaluation/evaluate_retrieval.py
```

The detailed report is saved to:

```text
evaluation/results/retrieval_results.json
```

## Run selected queries

```bash
python evaluation/evaluate_retrieval.py --query-id K01 --query-id S01
```

## Metrics

- `Precision@K`: fraction of ranked results labelled relevant.
- `Recall@K`: fraction of labelled relevant citations retrieved.
- `MRR@K`: reciprocal rank of the first relevant citation.
- `nDCG@K`: ranking quality with relevance grades from 1 to 3.
- `final_group_coverage`: coverage after ticket or work-order section expansion.
- Forbidden-source checks detect cross-machine evidence contamination.

Knowledge retrieval is evaluated in two stages. The top-five maintenance results
and top-three ticket seeds form the ranked list. The production `retrieve_knowledge`
output is then checked for complete evidence-group coverage. Work-order retrieval
uses its top-four semantic seeds for ranking and its expanded result for coverage.

A query passes when all required evidence groups are covered, at least one
relevant result appears in the ranked output, and no forbidden source is returned.
The unknown-machine case passes only when retrieval returns no documents.
