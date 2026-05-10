from __future__ import annotations

from datetime import datetime

SUPPLEMENT_KEYWORDS = ("补充", "增加", "加入", "完善", "缺少", "不完整")


def compare_sources_for_node(node: dict, evidence_list: list[dict]) -> dict:
    evidence_ids = set(node.get("evidence_ids", []))
    related = [item for item in evidence_list if item.get("evidence_id") in evidence_ids]
    books = sorted({item.get("book", "") for item in related if item.get("book")})
    return {
        "books": books,
        "overlap_analysis": "多个教材均提及该知识点，说明它可能是跨教材共同核心内容。" if len(books) > 1 else "当前证据主要来自单本教材，跨教材重复证据有限。",
        "complement_analysis": "不同教材可从定义、机制、临床表现或病理变化等角度形成互补。" if len(books) > 1 else "当前互补分析证据不足，可继续检索其他教材。",
    }


def compute_overlap_complement(node: dict, evidence_list: list[dict]) -> dict:
    return compare_sources_for_node(node, evidence_list)


def compute_compression_ratio(original_evidence_texts: list[str], integrated_text: str) -> dict:
    original_chars = sum(len(text) for text in original_evidence_texts)
    integrated_chars = len(integrated_text)
    ratio = integrated_chars / original_chars if original_chars else 0
    return {
        "original_chars": original_chars,
        "integrated_chars": integrated_chars,
        "compression_ratio": round(ratio, 4),
    }


def summarize_integration(topic: str, evidence: list[dict], integrated_text: str = "") -> dict:
    books = sorted({item.get("book", "") for item in evidence if item.get("book")})
    compression = compute_compression_ratio([item.get("quote") or item.get("text", "") for item in evidence], integrated_text or topic)
    return {
        "overlap_summary": f"围绕“{topic}”，当前证据覆盖 {len(books)} 本教材；多书共同出现的内容可视为重点概念。",
        "complement_summary": "不同教材的片段可互补解释概念定义、机制、病理变化、诊断或防治方向。",
        "missing_summary": "未检索到证据的分支已标注为证据不足，建议继续补充教材或调整检索主题。",
        "compression": compression,
    }


def apply_teacher_feedback(graph_state: dict, feedback_action: dict) -> tuple[dict, dict]:
    graph = dict(graph_state)
    graph["nodes"] = [dict(node) for node in graph.get("nodes", [])]
    graph["edges"] = [dict(edge) for edge in graph.get("edges", [])]
    graph["feedback_records"] = list(graph.get("feedback_records", []))
    action = feedback_action.get("action", "keep")
    target_type = feedback_action.get("target_type", "node")
    target_id = feedback_action.get("target_id", "")
    before = None
    if target_type == "node":
        for node in graph["nodes"]:
            if node.get("id") == target_id:
                before = dict(node)
                if action == "delete":
                    node["status"] = "deleted"
                elif action in {"keep", "edit"}:
                    node["status"] = "updated"
                    if feedback_action.get("comment"):
                        node["teacher_note"] = feedback_action["comment"]
                elif action in {"split", "merge"}:
                    node["status"] = "highlighted"
                    node["teacher_note"] = feedback_action.get("comment", "")
                break
    else:
        for edge in graph["edges"]:
            if edge.get("id") == target_id:
                before = dict(edge)
                edge["status"] = "deleted" if action == "delete" else "updated"
                edge["teacher_note"] = feedback_action.get("comment", "")
                break
    after = None
    if target_type == "node":
        after = next((dict(node) for node in graph["nodes"] if node.get("id") == target_id), None)
    else:
        after = next((dict(edge) for edge in graph["edges"] if edge.get("id") == target_id), None)
    record = {
        "id": f"fb_{len(graph['feedback_records']) + 1:03d}",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "target_type": target_type,
        "target_id": target_id,
        "comment": feedback_action.get("comment", ""),
        "before": before,
        "after": after,
    }
    if target_type == "node" and action != "delete" and _should_retrieve_for_feedback(feedback_action.get("comment", "")):
        retrieval_record = _supplement_node_evidence(graph, target_id, feedback_action.get("comment", ""))
        record.update(retrieval_record)
        after = next((dict(node) for node in graph["nodes"] if node.get("id") == target_id), None)
        record["after"] = after

    graph["feedback_records"].append(record)
    return graph, record


def _should_retrieve_for_feedback(comment: str) -> bool:
    return bool(comment and any(keyword in comment for keyword in SUPPLEMENT_KEYWORDS))


def _supplement_node_evidence(graph: dict, target_id: str, comment: str) -> dict:
    node = next((item for item in graph.get("nodes", []) if item.get("id") == target_id), None)
    if not node:
        return {
            "retrieval_triggered": False,
            "added_evidence_count": 0,
            "warning": "目标节点不存在，已仅记录教师反馈",
        }

    query = _build_feedback_query(graph, node, comment)
    try:
        from .retrieval_agent import RetrievalAgent

        new_evidence = RetrievalAgent().search(query, top_k=3)
    except Exception:
        return {
            "retrieval_triggered": False,
            "added_evidence_count": 0,
            "warning": "检索失败，已仅记录教师反馈",
        }
    if not new_evidence:
        return {
            "retrieval_triggered": False,
            "added_evidence_count": 0,
            "warning": "检索失败，已仅记录教师反馈",
        }

    graph["evidence"] = list(graph.get("evidence", []))
    existing_ids = {item.get("evidence_id") for item in graph["evidence"]}
    existing_chunks = {item.get("chunk_id") for item in graph["evidence"] if item.get("chunk_id")}
    node["evidence_ids"] = list(node.get("evidence_ids", []))

    added_count = 0
    for item in new_evidence:
        if item.get("chunk_id") and item.get("chunk_id") in existing_chunks:
            evidence_id = next(
                (old.get("evidence_id") for old in graph["evidence"] if old.get("chunk_id") == item.get("chunk_id")),
                "",
            )
            if evidence_id and evidence_id not in node["evidence_ids"]:
                node["evidence_ids"].append(evidence_id)
            continue

        evidence_id = item.get("evidence_id") or _next_feedback_evidence_id(existing_ids)
        if evidence_id in existing_ids:
            evidence_id = _next_feedback_evidence_id(existing_ids)
        existing_ids.add(evidence_id)
        if item.get("chunk_id"):
            existing_chunks.add(item.get("chunk_id"))

        graph["evidence"].append(
            {
                "evidence_id": evidence_id,
                "book": item.get("book") or item.get("textbook", ""),
                "textbook": item.get("book") or item.get("textbook", ""),
                "source_file": item.get("source_file", ""),
                "chapter": item.get("chapter", ""),
                "page": int(item.get("page") or 0),
                "quote": item.get("quote") or item.get("text", "")[:260],
                "chunk_id": item.get("chunk_id", ""),
                "score": float(item.get("score") or 0.0),
            }
        )
        if evidence_id not in node["evidence_ids"]:
            node["evidence_ids"].append(evidence_id)
        added_count += 1

    if added_count > 0:
        supplement_note = "已根据教师反馈补充相关教材证据。"
        summary = str(node.get("summary") or "")
        if supplement_note not in summary:
            node["summary"] = f"{summary} {supplement_note}".strip()
        node["status"] = "updated"

    return {
        "retrieval_triggered": True,
        "added_evidence_count": added_count,
        "target_id": target_id,
    }


def _build_feedback_query(graph: dict, node: dict, comment: str) -> str:
    parts = [
        str(graph.get("topic") or ""),
        str(node.get("name") or ""),
        comment,
    ]
    return " ".join(part for part in parts if part).strip()


def _next_feedback_evidence_id(existing_ids: set) -> str:
    index = 1
    while True:
        evidence_id = f"ev_fb_{index:03d}"
        if evidence_id not in existing_ids:
            return evidence_id
        index += 1
