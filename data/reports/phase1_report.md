# Phase 1 Baseline Report

## Source and lineage

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Load mode | saved raw snapshot |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |
| Raw response | `D:\VinAI\Lab\K3_Day10_Data-Pipeline-Data-Observability\data\raw\crossref_response.json` |
| Raw records artifact | `D:\VinAI\Lab\K3_Day10_Data-Pipeline-Data-Observability\data\raw\crossref_records.json` |

## Retrieval and answer metrics

| Metric | Value |
| --- | ---: |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 0.9583 |
| `mean_judge_score` | 4.8333 |

- Evaluation samples: 24
- Judge mode: llm (24 LLM / 0 fallback)
- Ragas: `{'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'}`

## Data quality

- Overall status: **PASS**
- Passed checks: 8
- Failed checks: 0

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
| row_count | completeness | PASS | 24 |
| paper_id_not_blank | completeness | PASS | 0 |
| paper_id_unique | uniqueness | PASS | 0 |
| title_not_blank | completeness | PASS | 0 |
| summary_not_blank | completeness | PASS | 0 |
| embedding_text_not_blank | completeness | PASS | 0 |
| age_days_valid | validity | PASS | 0 |
| records_within_freshness_threshold | freshness | PASS | 0 |

## Freshness

| Field | Value |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Threshold (days) | 180 |
| Stale rows | 0 |
| Invalid date rows | 0 |
| Status | FRESH |

## Evidence boundary

This report is generated from the saved baseline metrics, quality checks, freshness results, and raw-source lineage. Ragas is reported as skipped or failed when it was not successfully executed.
