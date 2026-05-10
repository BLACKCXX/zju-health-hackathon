"""VLM-based Table of Contents parser for PDF textbooks.

Falls back to VLM when PyMuPDF get_toc() fails or produces garbled titles.
Only renders the first 20-40 pages (suspected TOC pages) to minimize API calls
and cost.

VLM config priority:
  api_key: VLM_API_KEY > DEFAULT_API_KEY > MODELSCOPE_API_KEY > OPENAI_API_KEY
  base_url: VLM_BASE_URL > DEFAULT_BASE_URL > MODELSCOPE_BASE_URL > OPENAI_BASE_URL
  model: VLM_MODEL (default: Qwen/Qwen2.5-VL-7B-Instruct)
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

import fitz


def _get_model_config() -> dict[str, str]:
    """Get VLM model configuration from environment.

    Priority:
      api_key: VLM_API_KEY > DEFAULT_API_KEY > MODELSCOPE_API_KEY > OPENAI_API_KEY
      base_url: VLM_BASE_URL > DEFAULT_BASE_URL > MODELSCOPE_BASE_URL > OPENAI_BASE_URL
      model: VLM_MODEL (default: Qwen/Qwen2.5-VL-7B-Instruct)
    """
    # api_key: try VLM_API_KEY first, then DEFAULT_API_KEY
    api_key = (
        os.getenv("VLM_API_KEY")
        or os.getenv("DEFAULT_API_KEY")
        or os.getenv("MODELSCOPE_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    placeholders = {"your_modelscope_sdk_token_here", "your_modelscope_token_here", "your_api_key_here"}
    if api_key.lower() in placeholders:
        api_key = ""

    # base_url: try VLM_BASE_URL first, then DEFAULT_BASE_URL
    base_url = (
        os.getenv("VLM_BASE_URL")
        or os.getenv("DEFAULT_BASE_URL")
        or os.getenv("MODELSCOPE_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api-inference.modelscope.cn/v1/"
    )
    # Normalize: strip trailing slash
    base_url = base_url.rstrip("/")

    model = os.getenv("VLM_MODEL") or "Qwen/Qwen2.5-VL-7B-Instruct"

    return {
        "api_key": api_key,
        "model": model,
        "base_url": base_url,
    }


def _render_pages_as_images(doc: fitz.Document, start: int = 0, count: int = 30) -> list[str]:
    """Render PDF pages as base64-encoded PNG images.

    Args:
        doc: PyMuPDF document
        start: page index to start from (0-indexed)
        count: number of pages to render

    Returns:
        List of base64-encoded PNG image strings
    """
    images = []
    for i in range(start, min(start + count, len(doc))):
        page = doc[i]
        # Use moderate resolution (1.5x zoom for readability)
        mat = fitz.Matrix(1.5, 1.5)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        images.append(img_b64)
    return images


def _call_vlm_toc(images: list[str], prompt: str, api_key: str, model: str, base_url: str) -> str:
    """Call VLM API with TOC page images to extract chapter structure."""
    import httpx

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
        }
    ]

    for img_b64 in images:
        messages[0]["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            }
        )

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 4000,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    endpoint = f"{base_url}/chat/completions"
    with httpx.Client(timeout=120.0) as client:
        response = client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]


def _parse_vlm_json_response(content: str) -> dict[str, Any] | None:
    """Extract JSON from VLM response, handling markdown code blocks."""
    json_str = None
    if "```json" in content:
        m = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        if m:
            json_str = m.group(1)
    elif "```" in content:
        m = re.search(r"```\s*(\{.*?\})\s*```", content, re.DOTALL)
        if m:
            json_str = m.group(1)
    else:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            json_str = m.group(0)

    if json_str:
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    return None


PROMPT_TEMPLATE = """你是一个医学教材目录识别专家。

请仔细看这些PDF页面（来自医学教材的目录页），提取其中的章节目录结构。

要求：
1. 识别所有章节标题（一级大章节如"第一章 绪论"、二级小节如"第一节 概述"）
2. 一级标题 level=1，二级标题 level=2
3. page_start 是该章节内容开始的页码（从1开始，与PDF页码一致）
4. 只输出你能确定的章节标题，不确定的不要编造
5. 每个章节必须同时有 title 和 page_start

输出格式（必须是有效的 JSON，不要包含其他文字）：
{
  "toc": [
    {"level": 1, "title": "第一章 绪论", "page_start": 1},
    {"level": 2, "title": "第一节 概述", "page_start": 3}
  ]
}

请开始识别："""


def extract_toc_from_pdf(pdf_path: Path, max_toc_pages: int = 30) -> dict[str, Any] | None:
    """Extract table of contents from PDF using VLM.

    Args:
        pdf_path: Path to the PDF file
        max_toc_pages: Maximum number of pages to render for VLM (default 30)

    Returns:
        Dict with "toc" key containing list of chapter entries, or None if failed.
        Each entry: {"level": int, "title": str, "page_start": int}
    """
    api_config = _get_model_config()
    if not api_config["api_key"]:
        return None

    try:
        with fitz.open(pdf_path) as doc:
            images = _render_pages_as_images(doc, start=0, count=max_toc_pages)

        if not images:
            return None

        content = _call_vlm_toc(
            images,
            PROMPT_TEMPLATE,
            api_config["api_key"],
            api_config["model"],
            api_config["base_url"],
        )

        result = _parse_vlm_json_response(content)
        return result

    except Exception:
        return None


def is_toc_garbled(toc: list) -> bool:
    """Check if a TOC has garbled/invalid titles."""
    if not toc:
        return True

    garbled_count = 0
    for entry in toc:
        title = entry.get("title", "")
        if len(title) < 4:
            garbled_count += 1
            continue
        if "" in title or "\x00" in title:
            garbled_count += 1
            continue
        cjk_chars = re.findall(r"[一-鿿]", title)
        if len(cjk_chars) < 2 and len(title) > 5:
            garbled_count += 1

    if len(toc) >= 3 and garbled_count / len(toc) > 0.6:
        return True
    if garbled_count >= 3:
        return True

    return False