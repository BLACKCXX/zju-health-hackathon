from __future__ import annotations

import html
import json
import os

import gradio as gr

from src.rag_pipeline import (
    answer_question,
    build_textbook_index,
    build_uploaded_index,
    get_environment_status,
    get_index_status,
)


CSS = """
:root {
  --health-blue: #2563eb;
  --health-green: #059669;
  --panel: #ffffff;
  --line: #dbe3ef;
  --text: #162033;
}

body, .gradio-container {
  background: #f6f8fb !important;
  color: var(--text);
}

.gradio-container {
  max-width: 1500px !important;
  margin: 0 auto !important;
}

.hero {
  padding: 24px 28px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #eef7f4 52%, #edf4ff 100%);
  box-shadow: 0 14px 34px rgba(22, 32, 51, 0.08);
  margin-bottom: 16px;
}

.hero h1 {
  font-size: 34px;
  line-height: 1.15;
  margin: 0 0 8px 0;
  letter-spacing: 0;
}

.hero .subtitle {
  font-size: 18px;
  color: #31506f;
  margin: 0 0 6px 0;
}

.hero .flow {
  color: #0f766e;
  font-weight: 700;
  margin: 0 0 10px 0;
}

.hero .note {
  color: #475569;
  margin: 0;
}

.hero .safety {
  display: inline-block;
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  background: rgba(5, 150, 105, 0.1);
  color: #075f45;
  font-weight: 600;
}

.panel {
  border: 1px solid var(--line);
  border-radius: 14px;
  background: var(--panel);
  box-shadow: 0 10px 24px rgba(22, 32, 51, 0.06);
  padding: 14px;
}

.status-card, .route-card, .retrieval-item {
  border: 1px solid #e3eaf3;
  border-radius: 10px;
  padding: 11px 12px;
  background: #fbfdff;
  margin-bottom: 10px;
}

.status-card strong, .route-card strong {
  color: #0f172a;
}

.small-muted {
  color: #64748b;
  font-size: 12px;
}

.retrieval-box, .route-box {
  max-height: 420px;
  overflow: auto;
}

.retrieval-item {
  background: #ffffff;
}

.retrieval-meta {
  color: #0f766e;
  font-weight: 700;
  margin-bottom: 6px;
}

.retrieval-text {
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-wrap;
}

button.primary {
  background: var(--health-blue) !important;
}
"""


def ensure_localhost_no_proxy() -> None:
    required_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    for key in ("NO_PROXY", "no_proxy"):
        current = os.environ.get(key, "")
        values = [item.strip() for item in current.split(",") if item.strip()]
        for host in required_hosts:
            if host not in values:
                values.append(host)
        os.environ[key] = ",".join(values)


def status_html() -> tuple[str, str, str]:
    status = get_environment_status()
    index = status["index"]
    api_text = "已检测到 DEFAULT_API_KEY 或 Answer Agent API_KEY" if status["answer_api_configured"] else "未配置"
    textbook_text = (
        f"textbooks/ 存在，发现 {status['pdf_count']} 个 PDF"
        if status["textbook_dir_exists"] and status["pdf_count"] > 0
        else "当前部署环境未发现教材 PDF，可使用普通聊天或上传 PDF 后构建临时索引。"
    )
    index_text = (
        f"已构建，{index['chunk_count']} 个 chunk<br>"
        f"Embedding: {index.get('has_embedding')}；TF-IDF: {index.get('has_tfidf')}<br>"
        f"最近构建时间：{index.get('built_at') or '-'}"
        if index["exists"]
        else "未构建索引"
    )
    api_card = (
        "<div class='status-card'><strong>API 配置状态</strong><br>"
        f"{api_text}<br>"
        f"<span class='small-muted'>Answer 模型：{html.escape(status['answer_model'])}</span><br>"
        f"<span class='small-muted'>Embedding 模型：{html.escape(status['embedding_model'])}</span>"
        "</div>"
    )
    textbook_card = (
        "<div class='status-card'><strong>教材目录状态</strong><br>"
        f"{html.escape(textbook_text)}<br>"
        f"<span class='small-muted'>{html.escape(status['textbook_dir'])}</span>"
        "</div>"
    )
    index_card = (
        "<div class='status-card'><strong>索引状态</strong><br>"
        f"{index_text}<br>"
        f"<span class='small-muted'>后端：{html.escape(status['retrieval_backend'])}</span>"
        "</div>"
    )
    return api_card, textbook_card, index_card


def format_plan(query_plan: dict) -> str:
    if not query_plan:
        return "<div class='route-box'><p>本轮尚无 Agent 路由信息。</p></div>"
    rows = [
        ("intent", query_plan.get("intent")),
        ("need_pdf_search", query_plan.get("need_pdf_search")),
        ("search_keywords", ", ".join(query_plan.get("search_keywords") or [])),
        ("expanded_query", query_plan.get("expanded_query")),
        ("answer_focus", query_plan.get("answer_focus")),
    ]
    body = "".join(
        f"<div class='route-card'><strong>{html.escape(key)}</strong><br>{html.escape(str(value or ''))}</div>"
        for key, value in rows
    )
    return f"<div class='route-box'>{body}</div>"


def format_contexts(contexts: list[dict]) -> str:
    if not contexts:
        return "<div class='retrieval-box'><p>本轮没有展示教材检索片段。</p></div>"

    items = []
    for item in contexts:
        text = html.escape(item.get("text", "")[:800])
        source = html.escape(str(item.get("source_file", "")))
        page = html.escape(str(item.get("page", "")))
        score = float(item.get("score", 0.0))
        match_type = html.escape(str(item.get("match_type", "")))
        items.append(
            "<div class='retrieval-item'>"
            f"<div class='retrieval-meta'>#{item.get('rank', '')} {source} · 第 {page} 页 · 相似度 {score:.4f}</div>"
            f"<div class='small-muted'>命中方式：{match_type}</div>"
            f"<div class='retrieval-text'>{text}</div>"
            "</div>"
        )
    return "<div class='retrieval-box'>" + "\n".join(items) + "</div>"


def build_index_ui(debug: bool, max_pages_per_pdf: int) -> tuple[str, str, str, str]:
    result = build_textbook_index(max_pages_per_pdf=max_pages_per_pdf if debug else None)
    api_status, textbook_status, index_status = status_html()
    message = html.escape(result["message"])
    if result.get("errors"):
        message += "<br><br>部分 PDF 读取异常：<br>" + "<br>".join(html.escape(err) for err in result["errors"][:5])
    return api_status, textbook_status, index_status, f"<div class='status-card'><strong>构建结果</strong><br>{message}</div>"


def check_index_ui() -> tuple[str, str, str, str]:
    api_status, textbook_status, index_status = status_html()
    index = get_index_status()
    detail = "<br>".join(
        [
            f"是否可加载：{index['exists']}",
            f"chunk 数量：{index.get('chunk_count', 0)}",
            f"是否包含 embedding：{index.get('has_embedding')}",
            f"是否包含 TF-IDF：{index.get('has_tfidf')}",
            f"Embedding 模型：{html.escape(str(index.get('embedding_model', '')))}",
            f"构建时间：{index.get('built_at') or '-'}",
            f"PDF 文件：{html.escape(', '.join(index.get('pdf_files') or []))}",
        ]
    )
    return api_status, textbook_status, index_status, f"<div class='status-card'><strong>检查索引</strong><br>{detail}</div>"


def upload_build_ui(files: list | None, debug: bool, max_pages_per_pdf: int) -> tuple[str, str, str, str]:
    result = build_uploaded_index(files, max_pages_per_pdf=max_pages_per_pdf if debug else None)
    api_status, textbook_status, index_status = status_html()
    message = html.escape(result.get("message", "上传索引构建完成。"))
    return api_status, textbook_status, index_status, f"<div class='status-card'><strong>上传构建结果</strong><br>{message}</div>"


def chat_ui(
    user_message: str,
    chat_history: list[dict] | None,
    top_k: int,
    force_pdf_search: bool,
    debug: bool,
) -> tuple[str, list[dict], str, str]:
    chat_history = chat_history or []
    if not user_message.strip():
        return "", chat_history, format_plan({}), format_contexts([])

    result = answer_question(
        user_query=user_message,
        history=chat_history,
        top_k=top_k,
        force_pdf_search=force_pdf_search,
        debug=debug,
    )
    updated_history = chat_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": result["answer"]},
    ]
    return "", updated_history, format_plan(result.get("query_plan", {})), format_contexts(result.get("contexts", []))


def clear_chat() -> tuple[list[dict], str, str, str]:
    return [], "", format_plan({}), format_contexts([])


with gr.Blocks(title="HealthPDF Agent") as demo:
    gr.HTML(
        """
        <section class="hero">
          <h1>HealthPDF Agent</h1>
          <p class="subtitle">面向大健康教材的多 Agent 问答系统</p>
          <p class="flow">Router Agent → PDF Search Agent → Answer Agent</p>
          <p class="note">系统会先理解用户意图，必要时检索本地医学教材，再生成带引用的结构化回答。</p>
          <span class="safety">仅用于学习与信息辅助理解，不提供医学诊断，不能替代医生建议。</span>
        </section>
        """
    )

    api_status_init, textbook_status_init, index_status_init = status_html()

    with gr.Row(equal_height=False):
        with gr.Column(scale=1, min_width=300, elem_classes=["panel"]):
            gr.Markdown("### 控制面板")
            api_status = gr.HTML(api_status_init)
            textbook_status = gr.HTML(textbook_status_init)
            index_status = gr.HTML(index_status_init)
            action_result = gr.HTML("")
            build_button = gr.Button("构建/刷新教材索引", variant="primary")
            check_button = gr.Button("检查索引")
            top_k = gr.Slider(1, 10, value=5, step=1, label="检索 top_k")
            force_pdf_search = gr.Checkbox(value=True, label="强制检索 PDF")
            debug_mode = gr.Checkbox(value=False, label="调试模式")
            max_pages = gr.Slider(10, 300, value=50, step=10, label="max_pages_per_pdf")
            uploaded_files = gr.File(label="上传 PDF 构建临时索引", file_count="multiple", file_types=[".pdf"])
            upload_build_button = gr.Button("基于上传 PDF 构建索引")
            clear_button = gr.Button("清空对话")

        with gr.Column(scale=2, min_width=520, elem_classes=["panel"]):
            gr.Markdown("### 多轮聊天")
            chatbot = gr.Chatbot(
                label="HealthPDF Agent",
                height=560,
                buttons=["copy", "copy_all"],
            )
            with gr.Row():
                user_input = gr.Textbox(
                    placeholder="请输入医学、健康、生物教材相关问题，例如：我肩膀肿胀，可能是什么原因？",
                    label="用户问题",
                    lines=2,
                    scale=5,
                )
                send_button = gr.Button("发送", variant="primary", scale=1)

        with gr.Column(scale=1, min_width=360, elem_classes=["panel"]):
            gr.Markdown("### 本轮 Agent 路由信息")
            route_panel = gr.HTML(format_plan({}))
            gr.Markdown("### 本轮教材片段")
            retrieval_panel = gr.HTML(format_contexts([]))

    build_button.click(
        build_index_ui,
        inputs=[debug_mode, max_pages],
        outputs=[api_status, textbook_status, index_status, action_result],
    )
    check_button.click(
        check_index_ui,
        inputs=[],
        outputs=[api_status, textbook_status, index_status, action_result],
    )
    upload_build_button.click(
        upload_build_ui,
        inputs=[uploaded_files, debug_mode, max_pages],
        outputs=[api_status, textbook_status, index_status, action_result],
    )
    send_button.click(
        chat_ui,
        inputs=[user_input, chatbot, top_k, force_pdf_search, debug_mode],
        outputs=[user_input, chatbot, route_panel, retrieval_panel],
    )
    user_input.submit(
        chat_ui,
        inputs=[user_input, chatbot, top_k, force_pdf_search, debug_mode],
        outputs=[user_input, chatbot, route_panel, retrieval_panel],
    )
    clear_button.click(
        clear_chat,
        inputs=[],
        outputs=[chatbot, user_input, route_panel, retrieval_panel],
    )


if __name__ == "__main__":
    ensure_localhost_no_proxy()
    port = int(os.environ.get("PORT", 7860))
    share = os.environ.get("GRADIO_SHARE", "0") == "1"
    print(f"Local browser URL: http://127.0.0.1:{port}")
    print(f"Deploy bind URL: http://0.0.0.0:{port}")
    demo.launch(
        server_name="0.0.0.0",
        server_port=port,
        share=share,
        css=CSS,
    )
