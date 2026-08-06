from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.config import load_settings, normalized_provider, require_llm_credentials
from core.utils import read_json
from retrieval.agent import build_agent
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


PROJECT_DIR = Path(__file__).resolve().parent
STATE_ORDER = ("baseline", "corrupted", "repaired")
STATE_LABELS = {
    "baseline": "Baseline",
    "corrupted": "Corrupted",
    "repaired": "Repaired",
}
STATE_COLORS = {
    "baseline": "#2563EB",
    "corrupted": "#DC2626",
    "repaired": "#16A34A",
}
METRIC_LABELS = {
    "retrieval_hit_rate": "Retrieval hit rate",
    "mean_token_f1": "Mean token F1",
    "judge_accuracy": "Judge accuracy",
    "mean_judge_score": "Mean judge score",
}


st.set_page_config(
    page_title="Day 10 · RAG Data Observability",
    page_icon="📊",
    layout="wide",
)


@st.cache_resource(show_spinner="Đang load MiniLM và ba Chroma collections...")
def load_indexes() -> dict[str, LocalEmbeddingIndex]:
    settings = load_settings(PROJECT_DIR)
    return {
        "baseline": LocalEmbeddingIndex.load(settings, settings.paths.embeddings_json),
        "corrupted": LocalEmbeddingIndex.load(
            settings, settings.paths.corrupted_embeddings_json
        ),
        "repaired": LocalEmbeddingIndex.load(settings, settings.paths.repaired_embeddings_json),
    }


@st.cache_resource(show_spinner="Đang khởi tạo OpenAI agents...")
def load_openai_agents() -> dict[str, Any]:
    settings = load_settings(PROJECT_DIR)
    if normalized_provider(settings) != "openai":
        raise RuntimeError("Hãy đặt LLM_PROVIDER=openai trong file .env.")
    require_llm_credentials(settings)
    return {
        state: build_agent(settings, index)
        for state, index in load_indexes().items()
    }


@st.cache_data
def load_artifacts() -> dict[str, Any]:
    settings = load_settings(PROJECT_DIR)
    return {
        "settings": settings,
        "metrics": {
            "baseline": read_json(settings.paths.baseline_metrics),
            "corrupted": read_json(settings.paths.corrupted_metrics),
            "repaired": read_json(settings.paths.repaired_metrics),
        },
        "quality": {
            "baseline": read_json(
                settings.paths.quality_dir / "baseline_quality_report.json"
            ),
            "corrupted": read_json(
                settings.paths.quality_dir / "corrupted_quality_report.json"
            ),
            "repaired": read_json(
                settings.paths.quality_dir / "repaired_quality_report.json"
            ),
        },
        "freshness": {
            "baseline": read_json(settings.paths.freshness_report),
            "corrupted": read_json(settings.paths.corrupted_freshness_report),
            "repaired": read_json(settings.paths.repaired_freshness_report),
        },
        "clean": {
            "baseline": read_json(settings.paths.clean_json),
            "corrupted": read_json(settings.paths.corrupted_clean_json),
            "repaired": read_json(settings.paths.repaired_clean_json),
        },
        "corruption_log": read_json(settings.paths.corruption_log),
        "test_set": read_json(settings.paths.eval_testset),
    }


def metric_frame(metrics: dict[str, dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for name, label in METRIC_LABELS.items():
        for state in STATE_ORDER:
            rows.append(
                {
                    "Metric": label,
                    "Trạng thái": STATE_LABELS[state],
                    "Giá trị": float(metrics[state][name]),
                }
            )
    return pd.DataFrame(rows)


def quality_frame(
    quality: dict[str, dict[str, Any]], freshness: dict[str, dict[str, Any]]
) -> pd.DataFrame:
    rows = []
    for state in STATE_ORDER:
        report = quality[state]
        rows.append(
            {
                "Trạng thái": STATE_LABELS[state],
                "Quality": "PASS" if report.get("success") else "FAIL",
                "Check đạt": report.get("passed_checks", 0),
                "Check lỗi": report.get("failed_checks", 0),
                "Freshness": "FRESH"
                if freshness[state].get("is_fresh")
                else "STALE/INVALID",
                "Row stale": freshness[state].get("stale_rows", 0),
            }
        )
    return pd.DataFrame(rows)


def records_by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(record["paper_id"]): record for record in records}


def corruption_evidence_rows(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    baseline = records_by_id(artifacts["clean"]["baseline"])
    corrupted = records_by_id(artifacts["clean"]["corrupted"])
    repaired = records_by_id(artifacts["clean"]["repaired"])
    rows: list[dict[str, Any]] = []
    for entry in artifacts["corruption_log"].get("corruptions", []):
        for paper_id in entry.get("affected_record_ids", []):
            base = baseline.get(str(paper_id), {})
            bad = corrupted.get(str(paper_id), {})
            fixed = repaired.get(str(paper_id), {})
            rows.append(
                {
                    "Loại corruption": entry.get("type", "N/A"),
                    "paper_id": paper_id,
                    "Baseline title": base.get("title", "Đã bị drop"),
                    "Corrupted title": bad.get("title", "Đã bị drop"),
                    "Repaired title": fixed.get("title", "Chưa phục hồi"),
                    "Baseline published": base.get("published", "N/A"),
                    "Corrupted published": bad.get("published", "Đã bị drop"),
                    "Repaired published": fixed.get("published", "N/A"),
                    "Baseline summary": base.get("summary", ""),
                    "Corrupted summary": bad.get("summary", "Đã bị drop"),
                    "Repaired summary": fixed.get("summary", ""),
                }
            )
    return rows


def render_metric_cards(metrics: dict[str, dict[str, Any]]) -> None:
    cols = st.columns(3)
    for col, state in zip(cols, STATE_ORDER, strict=True):
        values = metrics[state]
        with col:
            st.markdown(
                f"<div class='state-card' style='border-top-color:{STATE_COLORS[state]}'>"
                f"<div class='state-title'>{STATE_LABELS[state]}</div>"
                f"<div class='state-value'>{values['mean_token_f1']:.4f}</div>"
                "<div class='state-caption'>mean_token_f1</div>"
                f"<div class='mini-row'>Judge accuracy <b>{values['judge_accuracy']:.4f}</b></div>"
                f"<div class='mini-row'>Mean judge score <b>{values['mean_judge_score']:.4f}</b></div>"
                "</div>",
                unsafe_allow_html=True,
            )


def invoke_agent_with_trace(agent: Any, question: str) -> tuple[str, list[dict[str, str]]]:
    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    messages = result.get("messages", [])
    trace: list[dict[str, str]] = []
    for message in messages:
        message_type = getattr(message, "type", message.__class__.__name__)
        for tool_call in getattr(message, "tool_calls", []) or []:
            trace.append(
                {
                    "Bước": "Tool call",
                    "Tool": str(tool_call.get("name", "N/A")),
                    "Nội dung": str(tool_call.get("args", {})),
                }
            )
        if message_type == "tool":
            content = str(getattr(message, "content", ""))
            trace.append(
                {
                    "Bước": "Tool result",
                    "Tool": str(getattr(message, "name", "N/A")),
                    "Nội dung": content[:1200] + ("…" if len(content) > 1200 else ""),
                }
            )
    final = getattr(messages[-1], "content", "") if messages else ""
    return str(final), trace


def render_query_demo(artifacts: dict[str, Any]) -> None:
    st.subheader("Cùng một query trên ba trạng thái")
    settings = artifacts["settings"]
    mode = st.radio(
        "Chế độ trả lời",
        ["Local QA", "OpenAI Agent"],
        horizontal=True,
        help="OpenAI Agent dùng model gọi tools trên từng Chroma collection trước khi trả lời.",
    )
    if mode == "OpenAI Agent":
        provider_ok = normalized_provider(settings) == "openai"
        key_ok = bool(settings.openai_api_key)
        if provider_ok and key_ok:
            st.success(f"OpenAI đã sẵn sàng · Model: `{settings.model_name}`")
        else:
            st.warning(
                "Cần `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` và "
                "`OPENAI_API_KEY` trong `.env`."
            )
        st.caption(
            "Mỗi trạng thái tạo một OpenAI request và gửi query cùng tool result tương ứng."
        )
    else:
        st.caption(
            "Local QA chạy bằng MiniLM + Chroma và logic QA local; không gọi LLM provider."
        )
    questions = artifacts["test_set"]
    question_map = {
        f"{item['id']} · {item['question']}": item["question"] for item in questions
    }
    selected = st.selectbox("Chọn câu hỏi từ evaluation set", list(question_map))
    custom = st.text_input(
        "Hoặc nhập query riêng",
        placeholder="Ví dụ: What is the publication date of ...?",
    )
    question = custom.strip() or question_map[selected]
    top_k = st.slider("top_k", min_value=1, max_value=8, value=4)

    button_label = "Chạy OpenAI Agent trên 3 trạng thái" if mode == "OpenAI Agent" else "Chạy so sánh"
    if st.button(button_label, type="primary", width="stretch"):
        try:
            indexes = load_indexes()
        except Exception as exc:
            st.error(
                "Không load được Chroma collections. Hãy chạy baseline và corruption flow "
                f"trước khi mở UI. Chi tiết: {exc}"
            )
            return
        agents: dict[str, Any] = {}
        if mode == "OpenAI Agent":
            try:
                agents = load_openai_agents()
            except Exception as exc:
                st.error(f"Không khởi tạo được OpenAI Agent: {exc}")
                return
        columns = st.columns(3)
        for col, state in zip(columns, STATE_ORDER, strict=True):
            with col:
                st.markdown(f"### {STATE_LABELS[state]}")
                if mode == "OpenAI Agent":
                    with st.spinner(f"{STATE_LABELS[state]} đang gọi {settings.model_name}..."):
                        try:
                            answer, trace = invoke_agent_with_trace(agents[state], question)
                        except Exception as exc:
                            st.error(f"OpenAI request thất bại: {exc}")
                            continue
                    st.markdown(
                        f"<div class='answer-box' style='border-color:{STATE_COLORS[state]}'>"
                        f"{html.escape(answer) if answer else '<em>Câu trả lời rỗng</em>'}</div>",
                        unsafe_allow_html=True,
                    )
                    if trace:
                        st.caption(f"Agent đã thực hiện {sum(row['Bước'] == 'Tool call' for row in trace)} tool call(s).")
                        with st.expander("Xem tool trace", expanded=True):
                            st.dataframe(pd.DataFrame(trace), hide_index=True, width="stretch")
                    else:
                        st.warning("Agent không gọi tool; không nên dùng kết quả này làm demo factual.")
                    continue

                result = answer_question(question, settings, indexes[state], top_k=top_k)
                st.markdown(
                    f"<div class='answer-box' style='border-color:{STATE_COLORS[state]}'>"
                    f"{html.escape(result.answer) if result.answer else '<em>Câu trả lời rỗng</em>'}</div>",
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Top document: {result.retrieved_doc_ids[0] if result.retrieved_doc_ids else 'Không có'}"
                )
                with st.expander("Xem retrieval results"):
                    rows = []
                    for rank, (paper_id, title) in enumerate(
                        zip(
                            result.retrieved_doc_ids,
                            result.retrieved_titles,
                            strict=False,
                        ),
                        start=1,
                    ):
                        rows.append({"Rank": rank, "paper_id": paper_id, "Title": title})
                    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def main() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; padding-bottom: 3rem;}
        .hero {padding: 1.4rem 1.6rem; border-radius: 18px; color: white;
               background: linear-gradient(120deg, #0f172a, #1e3a8a 55%, #0f766e);}
        .hero h1 {margin: 0; font-size: 2.15rem;}
        .hero p {margin: .5rem 0 0; color: #dbeafe;}
        .state-card {background: white; border: 1px solid #e2e8f0; border-top: 5px solid;
                     border-radius: 14px; padding: 1rem 1.1rem; min-height: 190px;
                     box-shadow: 0 4px 18px rgba(15, 23, 42, .06);}
        .state-title {font-size: 1.05rem; font-weight: 700; color: #334155;}
        .state-value {font-size: 2.2rem; font-weight: 800; color: #0f172a; margin-top: .35rem;}
        .state-caption {color: #64748b; margin-bottom: .8rem;}
        .mini-row {display:flex; justify-content:space-between; border-top:1px solid #f1f5f9;
                   padding-top:.45rem; margin-top:.45rem; color:#475569;}
        .answer-box {border-left: 5px solid; background:#f8fafc; border-radius:10px;
                     padding:1rem; min-height:130px; color:#0f172a;}
        </style>
        <div class="hero">
          <h1>Data Observability cho RAG</h1>
          <p>So sánh Baseline → Corrupted → Repaired bằng artifacts và metrics thật.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        artifacts = load_artifacts()
    except Exception as exc:
        st.error(f"Thiếu hoặc không đọc được artifacts: {exc}")
        st.stop()

    tabs = st.tabs(
        ["📊 Tổng quan", "🩺 Quality & Freshness", "🧪 Corruption evidence", "🔎 RAG Demo"]
    )

    with tabs[0]:
        st.subheader("Kết quả chính")
        render_metric_cards(artifacts["metrics"])
        st.markdown("#### So sánh toàn bộ metrics")
        frame = metric_frame(artifacts["metrics"])
        pivot = frame.pivot(index="Metric", columns="Trạng thái", values="Giá trị")
        st.bar_chart(
            pivot[["Baseline", "Corrupted", "Repaired"]],
            color=[STATE_COLORS[state] for state in STATE_ORDER],
        )
        st.info(
            "Corrupted không làm giảm retrieval_hit_rate, nhưng làm giảm mean_token_f1, "
            "judge_accuracy và mean_judge_score. Điều này cho thấy tìm thấy document chưa "
            "đồng nghĩa với việc nội dung của document còn đủ tốt để trả lời."
        )

    with tabs[1]:
        st.subheader("Quality và freshness transition")
        st.dataframe(
            quality_frame(artifacts["quality"], artifacts["freshness"]),
            hide_index=True,
            width="stretch",
        )
        st.success("Baseline PASS/FRESH → Corrupted FAIL/STALE → Repaired PASS/FRESH")
        state = st.selectbox(
            "Xem chi tiết quality checks",
            STATE_ORDER,
            format_func=lambda value: STATE_LABELS[value],
        )
        checks = artifacts["quality"][state].get("checks", [])
        st.dataframe(pd.DataFrame(checks), hide_index=True, width="stretch")

    with tabs[2]:
        st.subheader("Corruption log và khả năng repair")
        evidence = corruption_evidence_rows(artifacts)
        summary = pd.DataFrame(
            [
                {
                    "Loại corruption": entry["type"],
                    "Record bị tác động": len(entry.get("affected_record_ids", [])),
                    "Số row trước": entry["before_count"],
                    "Số row sau": entry["after_count"],
                    "paper_id": ", ".join(entry.get("affected_record_ids", [])),
                }
                for entry in artifacts["corruption_log"].get("corruptions", [])
            ]
        )
        st.dataframe(summary, hide_index=True, width="stretch")
        selected_type = st.selectbox(
            "Chọn corruption để xem trước/sau",
            [row["Loại corruption"] for row in evidence],
        )
        selected_row = next(
            row for row in evidence if row["Loại corruption"] == selected_type
        )
        st.markdown(f"**paper_id:** `{selected_row['paper_id']}`")
        compare_cols = st.columns(3)
        for col, state in zip(compare_cols, STATE_ORDER, strict=True):
            label = STATE_LABELS[state]
            with col:
                st.markdown(f"### {label}")
                st.write(selected_row[f"{label} title"])
                st.caption(f"Published: {selected_row[f'{label} published']}")
                with st.expander("Xem summary", expanded=state == "corrupted"):
                    st.write(selected_row[f"{label} summary"] or "(Rỗng)")

    with tabs[3]:
        render_query_demo(artifacts)

    st.divider()
    st.caption(
        "Nguồn: Crossref raw snapshot · Embedding: sentence-transformers/all-MiniLM-L6-v2 · "
        "Vector store: ChromaDB · OpenAI Agent: gpt-4o-mini"
    )


if __name__ == "__main__":
    main()
