from __future__ import annotations

from .integration_agent import compare_sources_for_node
from .router_agent import extract_keywords


SAFETY_NOTE = "本系统仅用于学习与信息辅助理解，不能替代医生诊断和治疗建议。"


def generate_ask_answer(question: str, evidence: list[dict]) -> dict:
    keywords = extract_keywords(question)
    if not evidence:
        return {
            "answer": "当前教材证据不足，暂不能基于教材给出可靠回答。请先构建索引或换一个更具体的教材主题。",
            "keywords": keywords,
            "citations": [],
            "flashcards": [],
            "agent_trace": {"intent": "ask", "topic": keywords[0] if keywords else question, "retrieved_count": 0},
        }
    topic = keywords[0] if keywords else question[:20]
    top_quotes = [item.get("quote") or item.get("text", "")[:160] for item in evidence[:3]]
    answer = (
        f"围绕“{topic}”，教材证据提示："
        + "；".join(_clean_quote(q, 90) for q in top_quotes if q)
        + f"\n\n{SAFETY_NOTE}"
    )
    citations = [_citation(item) for item in evidence[:6]]
    flashcards = [
        {
            "title": topic,
            "definition": _clean_quote(top_quotes[0], 120) if top_quotes else "证据不足",
            "key_points": [_clean_quote(q, 70) for q in top_quotes if q][:3],
            "related_terms": keywords[1:6],
            "source_refs": [{"book": item.get("book", ""), "page": item.get("page", 0)} for item in evidence[:3]],
        }
    ]
    return {
        "answer": answer,
        "keywords": keywords,
        "citations": citations,
        "flashcards": flashcards,
        "agent_trace": {"intent": "ask", "topic": topic, "retrieved_count": len(evidence)},
    }


def generate_node_detail(node_id: str, node_name: str, graph_context: dict, evidence: list[dict]) -> dict:
    graph_evidence = graph_context.get("evidence", []) if graph_context else []
    node = next((item for item in graph_context.get("nodes", []) if item.get("id") == node_id), {}) if graph_context else {}
    evidence_ids = set(node.get("evidence_ids", []))
    sources = [item for item in graph_evidence if item.get("evidence_id") in evidence_ids] or evidence[:5]
    analysis = compare_sources_for_node(node or {"evidence_ids": [item.get("evidence_id") for item in sources]}, sources)
    first = sources[0] if sources else {}
    quote = first.get("quote") or first.get("text", "")
    return {
        "node_id": node_id,
        "name": node_name,
        "definition": _clean_quote(quote, 120) if quote else "当前节点证据不足。",
        "detail": node.get("summary") or (_clean_quote(quote, 260) if quote else "可继续检索补充该节点证据。"),
        "overlap_analysis": analysis["overlap_analysis"],
        "complement_analysis": analysis["complement_analysis"],
        "sources": [_citation(item) for item in sources],
    }


def generate_markdown_report(topic: str, graph: dict, feedback_records: list[dict]) -> str:
    evidence = graph.get("evidence", [])
    integration = graph.get("integration", {})
    lines = [
        f"# 主题：{topic}",
        "",
        "## 1. 核心概念概述",
        graph.get("nodes", [{}])[0].get("summary", "证据不足。") if graph.get("nodes") else "证据不足。",
        "",
        "## 2. 跨教材知识图谱摘要",
        f"当前图谱包含 {len(graph.get('nodes', []))} 个节点、{len(graph.get('edges', []))} 条关系。",
        "",
        "## 3. 主要节点说明",
    ]
    for node in graph.get("nodes", []):
        if node.get("status") == "deleted":
            continue
        lines.append(f"- **{node.get('name')}**：{node.get('summary', '')}")
    lines += [
        "",
        "## 4. 跨教材重复知识点",
        integration.get("overlap_summary", "证据不足。"),
        "",
        "## 5. 跨教材互补知识点",
        integration.get("complement_summary", "证据不足。"),
        "",
        "## 6. 可能缺失或证据不足的部分",
        integration.get("missing_summary", "证据不足。"),
        "",
        "## 7. 教师反馈记录",
    ]
    if feedback_records:
        for record in feedback_records:
            lines.append(f"- {record.get('time', '')} [{record.get('action')}] {record.get('target_id')}: {record.get('comment', '')}")
    else:
        lines.append("暂无教师反馈。")
    compression = integration.get("compression", {})
    lines += [
        "",
        "## 8. 压缩比说明",
        f"原始证据字符数：{compression.get('original_chars', 0)}；整合字符数：{compression.get('integrated_chars', 0)}；压缩比：{compression.get('compression_ratio', 0)}。",
        "",
        "## 9. 教材引用来源",
    ]
    for item in evidence:
        lines.append(f"- {item.get('book')}，{item.get('chapter', '章节待识别')}，第 {item.get('page')} 页：{_clean_quote(item.get('quote', ''), 80)}")
    return "\n".join(lines)


def _citation(item: dict) -> dict:
    return {
        "book": item.get("book", ""),
        "chapter": item.get("chapter", "章节待识别"),
        "page": int(item.get("page", 0) or 0),
        "quote": _clean_quote(item.get("quote") or item.get("text", ""), 180),
    }


def _clean_quote(text: str, limit: int) -> str:
    return " ".join((text or "").split())[:limit]
