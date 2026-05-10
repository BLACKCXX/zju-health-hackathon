from __future__ import annotations

import json
import re

from .llm_client import NO_API_KEY_MESSAGE, call_llm
from .prompts import ROUTER_FEW_SHOT_EXAMPLES, ROUTER_SYSTEM_PROMPT


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

    llm_route = _route_with_llm(query, current_mode=current_mode, current_graph_state=current_graph_state)
    if llm_route:
        return llm_route

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


def _route_with_llm(user_query: str, current_mode: str = "ask", current_graph_state: dict | None = None) -> dict | None:
    examples_text = json.dumps(ROUTER_FEW_SHOT_EXAMPLES, ensure_ascii=False, indent=2)
    messages = [
        {
            "role": "system",
            "content": (
                f"{ROUTER_SYSTEM_PROMPT}\n\n"
                "下面是 few-shot 意图分类示例。请学习输出字段，但最终返回仍必须是一个 JSON 对象。\n"
                f"{examples_text}\n\n"
                "兼容要求：返回字段至少包含 intent、topic、keywords、need_retrieval、reason。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "user_query": user_query,
                    "current_mode": current_mode,
                    "has_current_graph": bool(current_graph_state),
                },
                ensure_ascii=False,
            ),
        },
    ]
    response = call_llm(messages, role="router", temperature=0.1)
    if response == NO_API_KEY_MESSAGE or response.startswith("模型调用失败"):
        return None
    payload = _extract_json(response)
    if not payload:
        return None
    return _normalize_llm_route(payload, user_query, current_mode, current_graph_state)


def _normalize_llm_route(payload: dict, user_query: str, current_mode: str, current_graph_state: dict | None) -> dict:
    raw_intent = str(payload.get("intent") or "").strip()
    intent_map = {
        "chat": "greeting",
        "ask": "ask",
        "graph_integrated": "graph_build",
        "graph_single": "graph_build",
        "graph_update": "graph_update",
        "report": "report",
        "greeting": "greeting",
    }
    intent = intent_map.get(raw_intent, raw_intent)
    if intent not in {"greeting", "ask", "graph_build", "graph_update", "report", "unknown"}:
        intent = "graph_update" if current_mode == "graph" and current_graph_state else "ask"

    keywords = payload.get("keywords") or payload.get("search_keywords") or extract_keywords(user_query)
    if isinstance(keywords, str):
        keywords = [item for item in re.split(r"[,，、\s]+", keywords) if item]
    if not isinstance(keywords, list):
        keywords = extract_keywords(user_query)

    topic = payload.get("topic")
    if topic is None:
        topic = ""
    topic = str(topic).strip() or (str(keywords[0]) if keywords else user_query[:24])

    need_retrieval = payload.get("need_retrieval", payload.get("need_pdf_search", intent not in {"greeting", "unknown"}))
    route = {
        "intent": intent,
        "topic": topic,
        "keywords": [str(item) for item in keywords[:8]],
        "need_retrieval": bool(need_retrieval),
        "reason": str(payload.get("reason") or "few-shot router LLM plan with rule fallback."),
    }
    for key in ("answer_focus", "graph_mode", "graph_operation"):
        if key in payload:
            route[key] = payload[key]
    return route


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        payload = json.loads(text)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


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
