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


def _delta(current: Any, baseline: Any) -> str:
    if isinstance(current, (int, float)) and isinstance(baseline, (int, float)):
        diff = current - baseline
        sign = "+" if diff >= 0 else ""
        return f"{sign}{diff:.4f}"
    return "N/A"


def _quality_section(title: str, quality: dict[str, Any]) -> str:
    check_rows = "\n".join(
        f"| {CHECK_LABELS.get(item['name'], item['name'])} | "
        f"{DIMENSION_LABELS.get(item['dimension'], item['dimension'])} | "
        f"{'PASS' if item['success'] else 'FAIL'} | {item['observed']} |"
        for item in quality.get("checks", [])
    ) or "| Không có check | N/A | FAIL | N/A |"
    return f"""### {title}

- Overall status: **{'PASS' if quality.get('success') else 'FAIL'}**
- Passed checks: {quality.get('passed_checks', 0)}
- Failed checks: {quality.get('failed_checks', 0)}

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
{check_rows}
"""


def _freshness_section(title: str, freshness: dict[str, Any]) -> str:
    return f"""### {title}

| Field | Value |
| --- | --- |
| Latest published | {freshness.get('latest_published', 'N/A')} |
| Oldest published | {freshness.get('oldest_published', 'N/A')} |
| Freshness threshold (days) | {freshness.get('freshness_threshold_days', 'N/A')} |
| Stale rows | {freshness.get('stale_rows', 'N/A')} |
| Invalid date rows | {freshness.get('invalid_date_rows', 'N/A')} |
| Status | {'FRESH' if freshness.get('is_fresh') else 'STALE/INVALID'} |
"""


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
    baseline_quality: dict[str, Any] | None = None,
    baseline_freshness: dict[str, Any] | None = None,
) -> None:
    """Viet markdown report so sanh baseline/corrupted/repaired."""
    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    metric_rows = "\n".join(
        f"| `{name}` | {_metric(baseline_metrics.get(name, 'N/A'))} | "
        f"{_metric(corrupted_metrics.get(name, 'N/A'))} | "
        f"{_delta(corrupted_metrics.get(name), baseline_metrics.get(name))} | "
        f"{_metric(repaired_metrics.get(name, 'N/A'))} | "
        f"{_delta(repaired_metrics.get(name), baseline_metrics.get(name))} |"
        for name in metric_names
    )
    text = f"""# Báo cáo so sánh Corruption: Baseline → Corrupted → Repaired

## Retrieval và answer metrics

| Metric | Baseline | Corrupted | Δ (Corrupted − Baseline) | Repaired | Δ (Repaired − Baseline) |
| --- | ---: | ---: | ---: | ---: | ---: |
{metric_rows}

- Corrupted samples: {corrupted_metrics.get('samples', 'N/A')}
- Repaired samples: {repaired_metrics.get('samples', 'N/A')}

## Data quality

{_quality_section("Baseline", baseline_quality) if baseline_quality else ""}
{_quality_section("Corrupted", corrupted_quality)}
{_quality_section("Repaired", repaired_quality)}

## Freshness

{_freshness_section("Baseline", baseline_freshness) if baseline_freshness else ""}
{_freshness_section("Corrupted", corrupted_freshness)}
{_freshness_section("Repaired", repaired_freshness)}

## Evidence boundary

Báo cáo này được tạo hoàn toàn từ metrics, quality checks và freshness report thật của ba trạng thái baseline/corrupted/repaired; không có số liệu nào bị chỉnh sửa thủ công. Nếu repaired chưa khôi phục hoàn toàn về mức baseline, delta ở trên sẽ vẫn khác 0 và cần được nêu rõ khi demo thay vì tô hồng kết quả.
"""
    write_text(report_path, text)
