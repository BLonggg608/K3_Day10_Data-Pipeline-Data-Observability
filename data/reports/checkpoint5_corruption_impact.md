# Checkpoint 5 — Corruption impact evidence

## Evaluation contract

- Test set: `data/eval/test_set.json`
- Test-set SHA-256 matches `data/results/checkpoint4_baseline_lock.json`: **YES**
- Samples: 24 in both baseline and corrupted runs
- `top_k`: 4
- Corrupted collection: `papers-corrupted`
- Corrupted manifest documents: 24
- Corrupted Chroma documents: 24

The corrupted run used the locked test set. Baseline artifacts were not overwritten.

## Metric comparison

| Metric | Baseline | Corrupted | Delta |
| --- | ---: | ---: | ---: |
| Retrieval hit rate | 1.0000 | 1.0000 | 0.0000 |
| Mean token F1 | 1.0000 | 0.8414 | -0.1586 |
| Judge accuracy | 0.9583 | 0.7917 | -0.1667 |
| Mean judge score | 4.8333 | 4.2500 | -0.5833 |

Retrieval hit rate did not decrease, but answer-quality metrics did. A retrieval hit only means the ground-truth document appeared somewhere in top 4; it does not guarantee that the first document used to answer was correct.

## Evaluator fallback audit

| Field | Baseline | Corrupted |
| --- | ---: | ---: |
| Judge mode | `llm` | `llm` |
| LLM judge samples | 24 | 24 |
| Fallback judge samples | 0 | 0 |

No evaluator sample silently fell back to the heuristic. Ragas was skipped in both runs and is not reported as a successful Ragas evaluation.

## Quality and freshness comparison

| Signal | Baseline | Corrupted | Changed? |
| --- | ---: | ---: | --- |
| Row count | 24 | 24 | No |
| Blank `paper_id` | 0 | 0 | No |
| Duplicate `paper_id` rows | 0 | 1 | Yes, worse |
| Blank title | 0 | 0 | No |
| Blank summary | 0 | 1 | Yes, worse |
| Blank embedding text | 0 | 0 | No |
| Invalid `age_days` | 0 | 0 | No |
| Stale rows | 0 | 1 | Yes, worse |
| Invalid published dates | 0 | 0 | No |
| Latest published | 2026-08-01 | 2026-07-13 | Yes, older |
| Oldest published | 2026-02-12 | 2024-02-13 | Yes, older |
| Overall quality | PASS | FAIL | Yes, worse |
| Freshness status | FRESH | STALE | Yes, worse |

Row count stayed at 24 because one latest record was dropped and one duplicate row was added. This unchanged aggregate does not mean completeness and uniqueness were preserved.

## Case-level evidence

### Case 1 — blank summary directly damaged an answer

- Question: `q-01-summary`
- Ground-truth paper: `10.1007/s10278-026-02086-9`
- Corruption log: `blank_summary`
- Baseline answer: non-empty and matched the reference
- Corrupted answer: empty
- Token F1: `1.0 → 0.0`
- Judge score: `5 → 2`
- Retrieval hit: `true → true`

The document was still retrieved, but its missing summary made the generated answer unusable.

### Case 2 — truncated title broke exact lookup and changed the top answer source

- Questions: `q-03-summary`, `q-03-authors`
- Ground-truth paper: `10.1111/exsy.70341`
- Corruption log: `truncate_title`, retained characters: 10
- Summary Token F1: `1.0 → 0.1935`
- Summary judge score: `5 → 2`
- Authors Token F1: `1.0 → 0.0`
- Authors judge score: `5 → 1`
- Retrieval hit remained `true`

The original title in the locked question no longer matched the truncated indexed title. The ground-truth paper still appeared in top 4, so retrieval hit stayed true, but another paper became the first result used for the answer.

### Case 3 — stale publication date changed a factual answer

- Question: `q-04-date`
- Ground-truth paper: `10.20944/preprints202602.0996.v1`
- Corruption log: `stale_publication_date`, shifted by 730 days
- Answer: `2026-02-12 → 2024-02-13`
- Token F1: `1.0 → 0.0`
- Judge score: `5 → 1`
- Freshness signal: stale rows `0 → 1`

This case connects the logged date corruption to both an observability alert and an incorrect RAG answer.

## Signals and corruptions without demonstrated RAG impact

- Retrieval hit rate stayed at 1.0.
- Row count stayed at 24 because drop and duplicate operations cancelled at aggregate level.
- Blank-ID, blank-title, blank-embedding-text, invalid-age and invalid-date signals did not change.
- The injected-noise paper and duplicated paper did not produce a demonstrated decrease for the locked test samples.
- The dropped paper was not among the six papers selected by the locked test set, so this run does not prove that dropping it reduced answer metrics.
- Ragas was not enabled, so no claim is made about Ragas metrics.

## Conclusion

The evidence supports a limited conclusion: controlled corruption degraded completeness, uniqueness and freshness, and three logged corruption types caused four locked evaluation cases to return worse answers. It does not support the claim that every corruption type reduced RAG quality, nor that retrieval hit rate detected the answer degradation.
