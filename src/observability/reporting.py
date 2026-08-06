from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else str(value)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline report strictly from generated artifacts."""
    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    metric_rows = "\n".join(
        f"| `{name}` | {_metric(metrics.get(name, 'N/A'))} |" for name in metric_names
    )
    check_rows = "\n".join(
        f"| {item['name']} | {item['dimension']} | {'PASS' if item['success'] else 'FAIL'} | {item['observed']} |"
        for item in quality.get("checks", [])
    ) or "| No checks | N/A | FAIL | N/A |"
    ragas = metrics.get("ragas", {})
    text = f"""# Phase 1 Baseline Report

## Source and lineage

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'N/A')} |
| Load mode | {source_summary.get('mode', 'N/A')} |
| Query | {source_summary.get('query', 'N/A')} |
| Filter | {source_summary.get('filter', 'N/A')} |
| Raw records | {source_summary.get('raw_records', 'N/A')} |
| Clean records | {source_summary.get('clean_records', 'N/A')} |
| Raw response | `{source_summary.get('raw_api_response', 'N/A')}` |
| Raw records artifact | `{source_summary.get('raw_records_json', 'N/A')}` |

## Retrieval and answer metrics

| Metric | Value |
| --- | ---: |
{metric_rows}

- Evaluation samples: {metrics.get('samples', 'N/A')}
- Judge mode: {metrics.get('judge_mode', 'N/A')} ({metrics.get('llm_judge_samples', 0)} LLM / {metrics.get('fallback_judge_samples', 0)} fallback)
- Ragas: `{ragas}`

## Data quality

- Overall status: **{'PASS' if quality.get('success') else 'FAIL'}**
- Passed checks: {quality.get('passed_checks', 0)}
- Failed checks: {quality.get('failed_checks', 0)}

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
{check_rows}

## Freshness

| Field | Value |
| --- | --- |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Threshold (days) | {freshness.get('freshness_threshold_days', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 'N/A')} |
| Invalid date rows | {freshness.get('invalid_date_rows', 'N/A')} |
| Status | {'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'} |

## Evidence boundary

This report is generated from the saved baseline metrics, quality checks, freshness results, and raw-source lineage. Ragas is reported as skipped or failed when it was not successfully executed.
"""
    write_text(report_path, text)


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """TODO(student): viet markdown report so sanh baseline/corrupted/repaired."""
    raise NotImplementedError("Student task: implement corruption comparison report.")
