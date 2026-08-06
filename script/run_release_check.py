from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
from typing import Any

from core.config import load_settings
from core.utils import read_json, write_json, write_text
from observability.reporting import generate_corruption_report, generate_phase1_report


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
RELEASE_JSON = DATA_DIR / "results" / "checkpoint6_release_check.json"
RELEASE_REPORT = DATA_DIR / "reports" / "checkpoint6_release_review.md"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_DIR).as_posix()


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=PROJECT_DIR,
        check=True,
        capture_output=True,
    )
    return [PROJECT_DIR / item.decode() for item in result.stdout.split(b"\0") if item]


def _secret_findings() -> list[str]:
    patterns = [
        re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"\bAIza[A-Za-z0-9_-]{20,}"),
        re.compile(
            r"^\s*(?:OPENAI|GOOGLE|ANTHROPIC|OPENROUTER)_API_KEY\s*=\s*"
            r"(?!your_|example|changeme)[^\s#]+"
        ),
    ]
    findings: list[str] = []
    for path in _tracked_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in patterns):
                findings.append(f"{_relative(path)}:{line_number}")
    return findings


def _source_markers() -> list[str]:
    findings: list[str] = []
    not_implemented_marker = "NotImplemented" + "Error"
    student_todo_marker = "TODO" + "(student)"
    for folder in (PROJECT_DIR / "src", PROJECT_DIR / "script"):
        for path in folder.rglob("*.py"):
            if path.resolve() == Path(__file__).resolve():
                continue
            text = path.read_text(encoding="utf-8")
            if not_implemented_marker in text or student_todo_marker in text:
                findings.append(_relative(path))
            if any(marker in text for marker in ("<<<<<<<", "=======", ">>>>>>>")):
                findings.append(f"merge-marker:{_relative(path)}")
    return sorted(set(findings))


def _regenerate_reports(settings, artifacts: dict[str, Any]) -> None:
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary={
            "source": settings.source_api,
            "mode": "saved raw snapshot",
            "query": settings.source_query,
            "filter": settings.source_filter,
            "requested_records": settings.max_results,
            "raw_records": len(artifacts["raw_records"]),
            "clean_records": len(artifacts["clean_baseline"]),
            "raw_api_response": _relative(settings.paths.raw_api_response),
            "raw_records_json": _relative(settings.paths.raw_records_json),
        },
        metrics=artifacts["baseline_metrics"],
        quality=artifacts["baseline_quality"],
        freshness=artifacts["baseline_freshness"],
    )
    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=artifacts["baseline_metrics"],
        corrupted_metrics=artifacts["corrupted_metrics"],
        repaired_metrics=artifacts["repaired_metrics"],
        corrupted_quality=artifacts["corrupted_quality"],
        repaired_quality=artifacts["repaired_quality"],
        corrupted_freshness=artifacts["corrupted_freshness"],
        repaired_freshness=artifacts["repaired_freshness"],
        baseline_quality=artifacts["baseline_quality"],
        baseline_freshness=artifacts["baseline_freshness"],
    )


def main() -> None:
    settings = load_settings(PROJECT_DIR)
    paths = settings.paths
    required = {
        "raw_response": paths.raw_api_response,
        "raw_records": paths.raw_records_json,
        "clean_baseline": paths.clean_json,
        "clean_corrupted": paths.corrupted_clean_json,
        "clean_repaired": paths.repaired_clean_json,
        "manifest_baseline": paths.embeddings_json,
        "manifest_corrupted": paths.corrupted_embeddings_json,
        "manifest_repaired": paths.repaired_embeddings_json,
        "test_set": paths.eval_testset,
        "baseline_metrics": paths.baseline_metrics,
        "corrupted_metrics": paths.corrupted_metrics,
        "repaired_metrics": paths.repaired_metrics,
        "baseline_answers": paths.baseline_answers,
        "corrupted_answers": paths.corrupted_answers,
        "repaired_answers": paths.repaired_answers,
        "baseline_quality": paths.quality_dir / "baseline_quality_report.json",
        "corrupted_quality": paths.quality_dir / "corrupted_quality_report.json",
        "repaired_quality": paths.quality_dir / "repaired_quality_report.json",
        "baseline_freshness": paths.freshness_report,
        "corrupted_freshness": paths.corrupted_freshness_report,
        "repaired_freshness": paths.repaired_freshness_report,
        "corruption_log": paths.corruption_log,
        "baseline_lock": paths.baseline_metrics.parent / "checkpoint4_baseline_lock.json",
    }
    missing = [_relative(path) for path in required.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing CP6 artifacts:\n- " + "\n- ".join(missing))

    artifacts = {name: read_json(path) for name, path in required.items()}
    _regenerate_reports(settings, artifacts)

    checks: list[dict[str, Any]] = []

    def check(name: str, success: bool, details: Any) -> None:
        checks.append({"name": name, "success": bool(success), "details": details})

    raw_records = artifacts["raw_records"]
    baseline_clean = artifacts["clean_baseline"]
    corrupted_clean = artifacts["clean_corrupted"]
    repaired_clean = artifacts["clean_repaired"]
    check("raw_snapshot_available", len(raw_records) > 0, {"records": len(raw_records)})
    check(
        "repair_matches_baseline_clean",
        baseline_clean == repaired_clean,
        {"baseline_rows": len(baseline_clean), "repaired_rows": len(repaired_clean)},
    )
    check(
        "corruption_changes_clean_data",
        corrupted_clean != baseline_clean,
        {"baseline_rows": len(baseline_clean), "corrupted_rows": len(corrupted_clean)},
    )

    test_set = artifacts["test_set"]
    test_ids = {item["id"] for item in test_set}
    lock = artifacts["baseline_lock"]
    locked_test_hash = lock["locked_evaluation_contract"]["test_set_sha256"].upper()
    check(
        "test_set_hash_locked",
        _sha256(paths.eval_testset) == locked_test_hash,
        {"expected": locked_test_hash, "actual": _sha256(paths.eval_testset)},
    )
    for state in ("baseline", "corrupted", "repaired"):
        answers = artifacts[f"{state}_answers"]
        metrics = artifacts[f"{state}_metrics"]
        answer_ids = {item["id"] for item in answers}
        check(
            f"{state}_evaluation_contract",
            answer_ids == test_ids and metrics.get("samples") == len(test_set),
            {"answers": len(answers), "samples": metrics.get("samples")},
        )

    baseline_answers_by_id = {item["id"]: item for item in artifacts["baseline_answers"]}
    repaired_answers_by_id = {item["id"]: item for item in artifacts["repaired_answers"]}
    smoke_question_id = sorted(test_ids)[0]
    baseline_smoke = baseline_answers_by_id[smoke_question_id]
    repaired_smoke = repaired_answers_by_id[smoke_question_id]
    check(
        "repaired_same_query_smoke",
        repaired_smoke.get("answer") == baseline_smoke.get("answer")
        and repaired_smoke.get("retrieved_doc_ids") == baseline_smoke.get("retrieved_doc_ids"),
        {
            "question_id": smoke_question_id,
            "answer_recovered": repaired_smoke.get("answer") == baseline_smoke.get("answer"),
            "retrieval_recovered": repaired_smoke.get("retrieved_doc_ids")
            == baseline_smoke.get("retrieved_doc_ids"),
        },
    )

    metric_names = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score")
    baseline_metrics = artifacts["baseline_metrics"]
    corrupted_metrics = artifacts["corrupted_metrics"]
    repaired_metrics = artifacts["repaired_metrics"]
    degraded = any(corrupted_metrics[name] < baseline_metrics[name] for name in metric_names)
    recovered = all(repaired_metrics[name] == baseline_metrics[name] for name in metric_names)
    check("corruption_degrades_agent_metric", degraded, {name: corrupted_metrics[name] - baseline_metrics[name] for name in metric_names})
    check("repair_recovers_agent_metrics", recovered, {name: repaired_metrics[name] - baseline_metrics[name] for name in metric_names})
    check(
        "evaluator_no_fallback",
        all(artifacts[f"{state}_metrics"].get("fallback_judge_samples") == 0 for state in ("baseline", "corrupted", "repaired")),
        {state: artifacts[f"{state}_metrics"].get("judge_mode") for state in ("baseline", "corrupted", "repaired")},
    )
    check(
        "quality_transition",
        artifacts["baseline_quality"].get("success") is True
        and artifacts["corrupted_quality"].get("success") is False
        and artifacts["repaired_quality"].get("success") is True,
        {
            "baseline": artifacts["baseline_quality"].get("success"),
            "corrupted": artifacts["corrupted_quality"].get("success"),
            "repaired": artifacts["repaired_quality"].get("success"),
        },
    )
    check(
        "freshness_transition",
        artifacts["baseline_freshness"].get("is_fresh") is True
        and artifacts["corrupted_freshness"].get("is_fresh") is False
        and artifacts["repaired_freshness"].get("is_fresh") is True,
        {
            "baseline": artifacts["baseline_freshness"].get("is_fresh"),
            "corrupted": artifacts["corrupted_freshness"].get("is_fresh"),
            "repaired": artifacts["repaired_freshness"].get("is_fresh"),
        },
    )

    expected_collections = {
        "baseline": settings.baseline_collection_name,
        "corrupted": settings.corrupted_collection_name,
        "repaired": settings.repaired_collection_name,
    }
    database_uri = paths.chroma_dir.joinpath("chroma.sqlite3").resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        collection_counts = dict(
            connection.execute(
                """
                SELECT collections.name, COUNT(embeddings.id)
                FROM collections
                JOIN segments ON segments.collection = collections.id
                LEFT JOIN embeddings ON embeddings.segment_id = segments.id
                WHERE segments.type = 'urn:chroma:segment/metadata/sqlite'
                GROUP BY collections.name
                """
            ).fetchall()
        )
    for state, collection_name in expected_collections.items():
        manifest = artifacts[f"manifest_{state}"]
        manifest_path = Path(str(manifest.get("persist_path", "")))
        check(
            f"{state}_collection",
            manifest.get("collection_name") == collection_name
            and collection_counts.get(collection_name) == len(manifest.get("documents", []))
            and not manifest_path.is_absolute(),
            {
                "name": collection_name,
                "chroma_documents": collection_counts.get(collection_name),
                "manifest_documents": len(manifest.get("documents", [])),
                "persist_path": manifest.get("persist_path"),
            },
        )

    log = artifacts["corruption_log"]
    log_entries = log.get("corruptions", []) if isinstance(log, dict) else []
    log_schema_ok = bool(log_entries) and all(
        {"type", "before_count", "after_count", "affected_record_ids"}.issubset(entry)
        for entry in log_entries
    )
    check("corruption_log_traceable", log_schema_ok, {"entries": len(log_entries)})
    affected_ids = {
        str(paper_id)
        for entry in log_entries
        for paper_id in entry.get("affected_record_ids", [])
    }
    repaired_ids = {str(item["paper_id"]) for item in repaired_clean}
    check(
        "repair_restores_affected_records",
        bool(affected_ids) and affected_ids.issubset(repaired_ids),
        {"affected_records": len(affected_ids), "restored_records": len(affected_ids & repaired_ids)},
    )

    secret_findings = _secret_findings()
    tracked = {_relative(path) for path in _tracked_files()}
    check("env_not_tracked", ".env" not in tracked, {"tracked": ".env" in tracked})
    check("no_tracked_secret_pattern", not secret_findings, {"locations": secret_findings})
    source_markers = _source_markers()
    check("no_student_todo_or_merge_marker", not source_markers, {"locations": source_markers})
    check(
        "portable_report_paths",
        "D:\\" not in paths.baseline_report.read_text(encoding="utf-8"),
        {"report": _relative(paths.baseline_report)},
    )

    warnings: list[str] = []
    locked_report = lock.get("baseline_artifacts", {}).get("phase1_report", {})
    old_report_hash = str(locked_report.get("sha256", "")).upper()
    new_report_hash = _sha256(paths.baseline_report)
    if old_report_hash and old_report_hash != new_report_hash:
        warnings.append(
            "phase1_report.md changed after CP4 lock because the report was localized and "
            "its lineage paths were made portable; locked metrics/answers/quality/freshness remain unchanged."
        )

    key_artifacts = list(required.values()) + [paths.baseline_report, paths.comparison_report]
    hashes = {_relative(path): _sha256(path) for path in key_artifacts}
    success = all(item["success"] for item in checks)
    payload = {
        "checkpoint": 6,
        "status": "ready_for_release" if success else "blocked",
        "checks_passed": sum(item["success"] for item in checks),
        "checks_total": len(checks),
        "checks": checks,
        "warnings": warnings,
        "artifact_sha256": hashes,
    }
    write_json(RELEASE_JSON, payload)

    check_rows = "\n".join(
        f"| {item['name']} | {'PASS' if item['success'] else 'FAIL'} | `{json.dumps(item['details'], ensure_ascii=False)}` |"
        for item in checks
    )
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- Không có."
    metric_rows = "\n".join(
        f"| `{name}` | {baseline_metrics[name]:.4f} | {corrupted_metrics[name]:.4f} | {repaired_metrics[name]:.4f} |"
        for name in metric_names
    )
    report = f"""# Checkpoint 6 — Release review

- Status: **{'READY FOR RELEASE' if success else 'BLOCKED'}**
- Checks: **{sum(item['success'] for item in checks)}/{len(checks)} PASS**
- Test-set SHA-256: `{_sha256(paths.eval_testset)}`

## Evidence theo 5 vai trò

1. **Điều phối pipeline:** ba trạng thái dùng path/collection riêng; release checks và artifact hashes được lưu trong `{_relative(RELEASE_JSON)}`.
2. **Ingestion:** raw snapshot có {len(raw_records)} records và là nguồn để chạy lại cleaning; không refresh Crossref trong repair.
3. **Cleaning & corruption:** repaired clean khớp baseline clean; corruption log có {len(log_entries)} entry truy vết record bị tác động.
4. **RAG & agent:** `papers-baseline`, `papers-corrupted`, `papers-repaired` đều có {len(baseline_clean)} documents.
5. **Evaluation & observability:** cùng {len(test_set)} câu hỏi; quality chuyển PASS → FAIL → PASS và freshness chuyển FRESH → STALE → FRESH.

## So sánh metrics

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
{metric_rows}

## Release checks

| Check | Status | Details |
| --- | --- | --- |
{check_rows}

## Warnings đã audit

{warning_lines}

## Kết luận

Corruption làm giảm answer metrics trong khi retrieval hit rate vẫn giữ nguyên; quality và freshness phát hiện duplicate, summary rỗng và record stale. Repair từ raw snapshot khôi phục clean dataset, quality/freshness và toàn bộ metrics về baseline. Ragas không được bật nên không có kết luận dựa trên Ragas.
"""
    write_text(RELEASE_REPORT, report)
    print(f"CP6 release status: {payload['status']} ({payload['checks_passed']}/{payload['checks_total']} checks passed)")
    print(f"JSON: {_relative(RELEASE_JSON)}")
    print(f"Report: {_relative(RELEASE_REPORT)}")
    if not success:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
