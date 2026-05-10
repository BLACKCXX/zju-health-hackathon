from __future__ import annotations

from typing import Any

from openai import OpenAI

from .config import get_llm_config


NO_API_KEY_MESSAGE = "请先在项目根目录 .env 中配置 DEFAULT_API_KEY，或配置对应 Agent 的 API_KEY。"


def call_llm(
    messages: list[dict[str, str]],
    role: str = "answer",
    temperature: float = 0.3,
) -> str:
    llm_config = get_llm_config(role)
    api_key = llm_config["api_key"]
    base_url = llm_config["base_url"]
    model = llm_config["model"]

    if not api_key:
        return NO_API_KEY_MESSAGE

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
        )
        content: Any = response.choices[0].message.content
        if isinstance(content, str) and content.strip():
            return content.strip()
        return "模型返回为空，请稍后重试。"
    except Exception as exc:
        return f"模型调用失败：{exc}"
