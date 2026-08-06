from __future__ import annotations

from typing import Any

from core.utils import write_text


def _metric(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) else str(value)


CHECK_LABELS = {
    "row_count": "Row count",
    "paper_id_not_blank": "paper_id không rỗng",
    "paper_id_unique": "paper_id duy nhất",
    "title_not_blank": "title không rỗng",
    "summary_not_blank": "summary không rỗng",
    "embedding_text_not_blank": "embedding text không rỗng",
    "age_days_valid": "age_days hợp lệ",
    "records_within_freshness_threshold": "Records nằm trong freshness threshold",
}

DIMENSION_LABELS = {
    "completeness": "Completeness",
    "uniqueness": "Uniqueness",
    "validity": "Validity",
    "freshness": "Freshness",
}


def _ragas_status(ragas: Any) -> str:
    if isinstance(ragas, dict) and "skipped" in ragas:
        return "Đã bỏ qua (chưa bật `RUN_RAGAS=1`)."
    if isinstance(ragas, dict) and "error" in ragas:
        return f"Chạy thất bại: {ragas['error']}"
    return str(ragas)


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Tạo báo cáo baseline hoàn toàn từ các artifact đã sinh."""
    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    metric_rows = "\n".join(
        f"| `{name}` | {_metric(metrics.get(name, 'N/A'))} |" for name in metric_names
    )
    check_rows = "\n".join(
        f"| {CHECK_LABELS.get(item['name'], item['name'])} | "
        f"{DIMENSION_LABELS.get(item['dimension'], item['dimension'])} | "
        f"{'PASS' if item['success'] else 'FAIL'} | {item['observed']} |"
        for item in quality.get("checks", [])
    ) or "| Không có check | N/A | FAIL | N/A |"
    ragas = metrics.get("ragas", {})
    source_mode = source_summary.get("mode", "N/A")
    if source_mode == "saved raw snapshot":
        source_mode = "Dùng raw snapshot đã lưu"
    text = f"""# Báo cáo baseline Pha 1

## Data source và lineage

| Field | Value |
| --- | --- |
| Source | {source_summary.get('source', 'N/A')} |
| Load mode | {source_mode} |
| Query | {source_summary.get('query', 'N/A')} |
| Filter | {source_summary.get('filter', 'N/A')} |
| Raw records | {source_summary.get('raw_records', 'N/A')} |
| Clean records | {source_summary.get('clean_records', 'N/A')} |
| Raw response | `{source_summary.get('raw_api_response', 'N/A')}` |
| Artifact raw records | `{source_summary.get('raw_records_json', 'N/A')}` |

## Retrieval và answer metrics

| Metric | Value |
| --- | ---: |
{metric_rows}

- Evaluation samples: {metrics.get('samples', 'N/A')}
- Judge mode: {metrics.get('judge_mode', 'N/A')} ({metrics.get('llm_judge_samples', 0)} LLM samples / {metrics.get('fallback_judge_samples', 0)} fallback samples)
- Ragas: {_ragas_status(ragas)}

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
| Freshness threshold (days) | {freshness.get('freshness_threshold_days', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 'N/A')} |
| Invalid date rows | {freshness.get('invalid_date_rows', 'N/A')} |
| Status | {'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'} |

## Evidence boundary

Báo cáo này được tạo từ metrics baseline, kết quả kiểm tra chất lượng, freshness và thông tin truy vết nguồn raw đã lưu. Ragas được ghi rõ là bỏ qua hoặc thất bại nếu chưa chạy thành công; báo cáo không coi bước bị bỏ qua là đã đạt.
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
    """Tạo comparison report từ metrics và observability artifacts thực tế."""
    metric_names = (
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    )
    metric_rows = []
    degraded_metrics = []
    recovered_metrics = []
    for name in metric_names:
        baseline = baseline_metrics.get(name)
        corrupted = corrupted_metrics.get(name)
        repaired = repaired_metrics.get(name)
        if not all(isinstance(value, (int, float)) for value in (baseline, corrupted, repaired)):
            metric_rows.append(f"| `{name}` | N/A | N/A | N/A | N/A | N/A |")
            continue
        corruption_delta = corrupted - baseline
        repair_delta = repaired - corrupted
        metric_rows.append(
            f"| `{name}` | {_metric(baseline)} | {_metric(corrupted)} | "
            f"{_metric(repaired)} | {corruption_delta:+.4f} | {repair_delta:+.4f} |"
        )
        if corrupted < baseline:
            degraded_metrics.append(name)
        if corrupted < baseline and repaired > corrupted:
            recovered_metrics.append(name)

    quality_rows = "\n".join(
        (
            f"| {state} | {'PASS' if payload.get('success') else 'FAIL'} | "
            f"{payload.get('passed_checks', 'N/A')} | {payload.get('failed_checks', 'N/A')} |"
        )
        for state, payload in (
            ("Corrupted", corrupted_quality),
            ("Repaired", repaired_quality),
        )
    )
    freshness_rows = "\n".join(
        (
            f"| {state} | {'FRESH' if payload.get('is_fresh') else 'STALE/INVALID'} | "
            f"{payload.get('stale_rows', 'N/A')} | {payload.get('invalid_date_rows', 'N/A')} |"
        )
        for state, payload in (
            ("Corrupted", corrupted_freshness),
            ("Repaired", repaired_freshness),
        )
    )
    degraded_text = ", ".join(f"`{name}`" for name in degraded_metrics) or "Không có metric nào"
    recovered_text = ", ".join(f"`{name}`" for name in recovered_metrics) or "Không có metric nào"

    text = f"""# Báo cáo corruption, repair và comparison

## Evaluation contract

- Baseline, corrupted và repaired dùng cùng test set và metric names.
- Baseline judge mode: `{baseline_metrics.get('judge_mode', 'N/A')}`.
- Corrupted judge mode: `{corrupted_metrics.get('judge_mode', 'N/A')}`.
- Repaired judge mode: `{repaired_metrics.get('judge_mode', 'N/A')}`.
- Ragas được ghi nhận theo artifact; bước bị skip không được coi là PASS.

## Metrics comparison

| Metric | Baseline | Corrupted | Repaired | Corruption delta | Repair delta |
| --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(metric_rows)}

## Data quality

| State | Overall status | Passed checks | Failed checks |
| --- | --- | ---: | ---: |
{quality_rows}

## Freshness

| State | Status | Stale rows | Invalid date rows |
| --- | --- | ---: | ---: |
{freshness_rows}

## Kết luận dựa trên evidence

- Metrics giảm sau corruption: {degraded_text}.
- Metrics tăng lại sau repair: {recovered_text}.
- Corruption chỉ được kết luận có impact đối với metrics hoặc quality/freshness signals thực sự thay đổi trong bảng trên.
- Repair chỉ được xem là phục hồi hoàn toàn khi repaired metrics và signals quay về baseline; nếu không, report giữ nguyên chênh lệch thay vì tô đẹp kết quả.
"""
    write_text(report_path, text)
