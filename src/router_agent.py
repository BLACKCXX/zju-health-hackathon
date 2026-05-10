from __future__ import annotations

import re


GREETINGS = {"你好", "hello", "hi", "你是谁", "介绍一下你自己"}


def route_user_intent(user_query: str, current_mode: str = "ask", current_graph_state: dict | None = None) -> dict:
    query = user_query.strip()
    lower = query.lower()
    if lower in GREETINGS or query in GREETINGS:
        return {
            "intent": "greeting",
            "topic": "",
            "keywords": [],
            "need_retrieval": False,
            "reason": "普通问候，不需要检索教材。",
        }
    if "报告" in query or "导出" in query:
        intent = "report"
    elif current_mode == "graph" and current_graph_state:
        intent = "graph_update"
    elif "图谱" in query or "知识图谱" in query:
        intent = "graph_build"
    else:
        intent = "ask" if current_mode == "ask" else "graph_build"
    keywords = extract_keywords(query)
    topic = keywords[0] if keywords else query[:24]
    return {
        "intent": intent,
        "topic": topic,
        "keywords": keywords,
        "need_retrieval": intent not in {"greeting", "unknown"},
        "reason": "需要基于教材证据生成回答或图谱。",
    }


def extract_keywords(text: str) -> list[str]:
    candidates = re.findall(r"[\u4e00-\u9fa5A-Za-z0-9]{2,}", text)
    stop = {"什么是", "请问", "解释", "相关", "有哪些", "为什么", "如何", "可以", "一下"}
    result: list[str] = []
    for item in candidates:
        if item in stop:
            continue
        if item not in result:
            result.append(item)
    return result[:8]
