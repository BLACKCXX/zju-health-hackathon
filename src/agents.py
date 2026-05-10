from __future__ import annotations

import json
import re
from typing import Any

from .config import get_settings
from .llm_client import NO_API_KEY_MESSAGE, call_llm
from .prompts import ANSWER_SYSTEM_PROMPT, DIRECT_CHAT_SYSTEM_PROMPT, MEDICAL_SAFETY_NOTICE, ROUTER_SYSTEM_PROMPT
from .vector_store import VectorStore


GREETING_PATTERNS = {
    "你好",
    "hello",
    "hi",
    "你是谁",
    "介绍一下你自己",
    "帮我看看你能做什么",
    "你能做什么",
}

MEDICAL_KEYWORDS = {
    "医学",
    "健康",
    "疾病",
    "症状",
    "诊断",
    "治疗",
    "用药",
    "病理",
    "生理",
    "解剖",
    "组织胚胎",
    "微生物",
    "病毒",
    "细菌",
    "感染",
    "传染",
    "免疫",
    "细胞",
    "器官",
    "神经",
    "心脏",
    "血液",
    "肿瘤",
    "炎症",
    "代谢",
    "内分泌",
    "营养",
    "疫苗",
    "临床",
    "肝炎",
    "休克",
    "病理生理学",
}

SYMPTOM_KEYWORDS = {
    "疼",
    "疼痛",
    "痛",
    "肿",
    "肿胀",
    "发热",
    "发烧",
    "咳嗽",
    "腹泻",
    "拉肚子",
    "恶心",
    "呕吐",
    "头晕",
    "胸闷",
    "乏力",
    "皮疹",
    "出血",
    "麻木",
}

FALLBACK_EXPANSIONS = {
    "肩膀": ["肩部", "肩关节", "肩胛区"],
    "肿胀": ["水肿", "肿大", "肿块", "局部隆起", "炎性肿胀"],
    "疼痛": ["痛", "疼", "刺痛", "胀痛", "压痛"],
    "发热": ["发烧", "体温升高", "高热", "低热"],
    "咳嗽": ["咳", "干咳", "咳痰"],
    "腹泻": ["拉肚子", "稀便", "水样便"],
    "炎症": ["炎性反应", "渗出", "充血", "水肿"],
    "感染": ["细菌感染", "病毒感染", "病原体"],
    "外伤": ["损伤", "扭伤", "撞击", "挫伤"],
}


def plan_user_query(user_query: str, history: list[dict] | None = None) -> dict:
    return RouterAgent().plan_user_query(user_query, history=history)


class RouterAgent:
    def plan_user_query(self, user_query: str, history: list[dict] | None = None) -> dict:
        query = user_query.strip()
        if self._is_greeting(query):
            return {
                "intent": "greeting",
                "need_pdf_search": False,
                "user_emotion_reply": "",
                "search_keywords": [],
                "expanded_query": query,
                "answer_focus": "介绍 HealthPDF Agent 的教材检索和带引用回答能力。",
                "conversation_goal": "友好说明系统能力，引导用户提出医学教材问题。",
            }

        fallback_plan = self._fallback_plan(query)
        if fallback_plan["intent"] in {"symptom_question", "non_medical_question"}:
            return fallback_plan

        llm_plan = self._plan_with_llm(query, history=history)
        if llm_plan:
            return self._normalize_plan(llm_plan, fallback_plan)
        return fallback_plan

    def should_search_pdf(self, query: str, force_pdf_search: bool = True) -> bool:
        plan = self.plan_user_query(query)
        if plan["intent"] == "greeting":
            return False
        return bool(force_pdf_search or plan.get("need_pdf_search"))

    def _plan_with_llm(self, query: str, history: list[dict] | None = None) -> dict | None:
        recent_history = (history or [])[-6:]
        messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(
                    {"user_query": query, "recent_history": recent_history},
                    ensure_ascii=False,
                ),
            },
        ]
        response = call_llm(messages, role="router", temperature=0.1)
        if response == NO_API_KEY_MESSAGE or response.startswith("模型调用失败"):
            return None
        return _extract_json(response)

    def _fallback_plan(self, query: str) -> dict:
        keywords = self._expand_keywords(query)
        is_symptom = any(word in query for word in SYMPTOM_KEYWORDS)
        is_medical = is_symptom or any(word in query for word in MEDICAL_KEYWORDS)
        if is_symptom:
            intent = "symptom_question"
            need_pdf_search = True
            emotion = "先别太紧张，单凭一句描述不能判断具体疾病，但可以从教材知识中梳理可能相关方向。"
            focus = "不能仅凭一句话判断具体疾病；基于教材解释可能方向；提醒补充持续时间、严重程度、诱因、伴随症状；必要时就医。"
            goal = "安抚用户，提供非诊断性解释和就医边界。"
        elif is_medical:
            intent = "study_question"
            need_pdf_search = True
            emotion = ""
            focus = "围绕教材概念、机制、分类或传播途径给出结构化解释。"
            goal = "帮助用户学习医学教材知识，并给出可追溯引用。"
        else:
            intent = "non_medical_question"
            need_pdf_search = False
            emotion = ""
            focus = "简短回答，并提示系统主要面向医学教材问答。"
            goal = "完成普通对话或引导到教材问题。"

        expanded_query = " ".join(dict.fromkeys([query, *keywords, "医学教材", "机制", "病理", "生理"]))
        return {
            "intent": intent,
            "need_pdf_search": need_pdf_search,
            "user_emotion_reply": emotion,
            "search_keywords": keywords,
            "expanded_query": expanded_query,
            "answer_focus": focus,
            "conversation_goal": goal,
        }

    def _normalize_plan(self, llm_plan: dict, fallback_plan: dict) -> dict:
        intent = str(llm_plan.get("intent") or fallback_plan["intent"])
        allowed = {"greeting", "medical_question", "symptom_question", "study_question", "non_medical_question", "unknown"}
        if intent not in allowed:
            intent = fallback_plan["intent"]
        keywords = llm_plan.get("search_keywords") or fallback_plan["search_keywords"]
        if isinstance(keywords, str):
            keywords = [item.strip() for item in re.split(r"[,，、\s]+", keywords) if item.strip()]
        if not isinstance(keywords, list):
            keywords = fallback_plan["search_keywords"]
        return {
            "intent": intent,
            "need_pdf_search": bool(llm_plan.get("need_pdf_search", fallback_plan["need_pdf_search"])),
            "user_emotion_reply": str(llm_plan.get("user_emotion_reply") or fallback_plan["user_emotion_reply"]),
            "search_keywords": [str(item) for item in keywords[:12]],
            "expanded_query": str(llm_plan.get("expanded_query") or fallback_plan["expanded_query"]),
            "answer_focus": str(llm_plan.get("answer_focus") or fallback_plan["answer_focus"]),
            "conversation_goal": str(llm_plan.get("conversation_goal") or fallback_plan["conversation_goal"]),
        }

    @staticmethod
    def _is_greeting(query: str) -> bool:
        normalized = query.strip().lower()
        if normalized in GREETING_PATTERNS:
            return True
        return len(normalized) <= 12 and any(pattern in normalized for pattern in GREETING_PATTERNS)

    @staticmethod
    def _expand_keywords(query: str) -> list[str]:
        keywords: list[str] = []
        for key, values in FALLBACK_EXPANSIONS.items():
            if key in query:
                keywords.append(key)
                keywords.extend(values)
        for word in MEDICAL_KEYWORDS | SYMPTOM_KEYWORDS:
            if word in query and word not in keywords:
                keywords.append(word)
        return keywords[:12]


class PDFSearchAgent:
    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def search(self, query_plan: dict, original_query: str, top_k: int = 5) -> list[dict]:
        settings = get_settings()
        backend = (settings.retrieval_backend or self.store.metadata.get("retrieval_backend") or "hybrid").lower()
        expanded_query = query_plan.get("expanded_query") or original_query
        keywords = query_plan.get("search_keywords") or []
        if backend == "tfidf":
            return self.store.search_tfidf(" ".join([original_query, expanded_query, " ".join(keywords)]), top_k=top_k)
        if backend == "embedding":
            results = self.store.search_embedding(expanded_query, top_k=top_k, match_type="embedding_expanded")
            return results or self.store.search_tfidf(expanded_query, top_k=top_k, match_type="tfidf_fallback")
        return self.store.search_hybrid(original_query, expanded_query, keywords, top_k=top_k)


class AnswerAgent:
    def answer_greeting(self) -> str:
        return (
            "你好，我是 HealthPDF Agent，可以先理解你的问题意图，再检索本地医学教材 PDF，"
            "最后生成带引用来源的结构化回答。你可以问医学学习问题，也可以描述症状让我做非诊断性的教材知识解释。"
        )

    def answer_with_plan(
        self,
        query: str,
        query_plan: dict,
        contexts: list[dict],
        history: list[dict] | None = None,
        index_missing: bool = False,
    ) -> str:
        if query_plan.get("intent") == "greeting":
            return self.answer_greeting()

        context_text = self._format_contexts(contexts)
        no_context_notice = ""
        if index_missing:
            no_context_notice = "当前未检测到教材索引，可先构建索引；本次可基于通用模型知识做非诊断性解释。"
        elif not contexts:
            no_context_notice = "当前教材片段中没有找到足够依据。本次回答未使用教材检索结果。"

        if query_plan.get("intent") == "symptom_question":
            format_instruction = """请按以下格式回答：
一、简要回应
二、可能相关方向
三、教材依据
四、建议补充的信息
五、引用来源
六、医学安全提示"""
        else:
            format_instruction = """请按以下格式回答：
一、简要回答
二、教材依据
三、详细解释
四、引用来源
五、医学安全提示"""

        messages = [
            {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"用户问题：{query}\n\n"
                    f"Query Plan：{json.dumps(query_plan, ensure_ascii=False)}\n\n"
                    f"无教材依据提示：{no_context_notice}\n\n"
                    f"检索到的教材片段：\n{context_text or '无'}\n\n"
                    f"回答重点：{query_plan.get('answer_focus', '')}\n\n"
                    f"{format_instruction}\n\n"
                    "引用来源只能列出检索片段中真实存在的文件名和页码。"
                ),
            },
        ]
        answer = call_llm(messages, role="answer", temperature=0.25)
        if answer == NO_API_KEY_MESSAGE:
            return self._no_key_fallback(query_plan, contexts, index_missing=index_missing)
        return answer

    def answer_directly(self, query: str) -> str:
        messages = [
            {"role": "system", "content": DIRECT_CHAT_SYSTEM_PROMPT},
            {"role": "user", "content": f"用户问题：{query}\n请简洁回答。"},
        ]
        answer = call_llm(messages, role="answer", temperature=0.3)
        if answer == NO_API_KEY_MESSAGE:
            return f"{NO_API_KEY_MESSAGE}\n\n本次回答未使用教材检索结果。\n\n医学安全提示：{MEDICAL_SAFETY_NOTICE}"
        return answer

    def _no_key_fallback(self, query_plan: dict, contexts: list[dict], index_missing: bool = False) -> str:
        if query_plan.get("intent") == "symptom_question":
            prefix = query_plan.get("user_emotion_reply") or "先别太紧张，单凭一句描述不能判断具体疾病。"
            return (
                f"{NO_API_KEY_MESSAGE}\n\n"
                f"一、简要回应\n{prefix}\n\n"
                "二、可能相关方向\n模型未配置，暂不能生成完整解释；可先配置 API key 后重试。\n\n"
                "三、教材依据\n"
                + ("当前未检测到教材索引。" if index_missing else self._brief_sources(contexts))
                + "\n\n四、建议补充的信息\n请补充持续时间、严重程度、诱因、是否外伤、是否发热或活动受限等信息。\n\n"
                "五、引用来源\n"
                + self._brief_sources(contexts)
                + f"\n\n六、医学安全提示\n{MEDICAL_SAFETY_NOTICE}"
            )
        return (
            f"{NO_API_KEY_MESSAGE}\n\n"
            "本次回答未使用模型生成。"
            f"\n\n医学安全提示：{MEDICAL_SAFETY_NOTICE}"
        )

    @staticmethod
    def _format_contexts(contexts: list[dict]) -> str:
        blocks: list[str] = []
        for index, item in enumerate(contexts, start=1):
            blocks.append(
                f"[{index}] 文件名：{item.get('source_file')}；页码：{item.get('page')}；"
                f"chunk_id：{item.get('chunk_id')}；相似度：{item.get('score', 0):.4f}；"
                f"命中方式：{item.get('match_type', '')}\n{item.get('text', '')}"
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _brief_sources(contexts: list[dict]) -> str:
        if not contexts:
            return "本次回答未使用教材检索结果。"
        seen: set[tuple[str, int]] = set()
        lines: list[str] = []
        for item in contexts:
            key = (item.get("source_file", ""), int(item.get("page", 0)))
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"- {key[0]}，第 {key[1]} 页")
        return "\n".join(lines) if lines else "本次回答未使用教材检索结果。"


class SummaryAgent:
    def summarize(self, text: str) -> str:
        messages = [
            {"role": "system", "content": "你是 Summary Agent，请用简洁中文总结输入内容。"},
            {"role": "user", "content": text},
        ]
        return call_llm(messages, role="summary", temperature=0.2)


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    try:
        payload: Any = json.loads(text)
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
