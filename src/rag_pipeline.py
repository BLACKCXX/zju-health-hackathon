from __future__ import annotations

from pathlib import Path
import shutil

from .agents import AnswerAgent, PDFSearchAgent, plan_user_query
from .chunker import pages_to_chunks
from .config import get_embedding_config, get_llm_config, get_settings, has_api_key, list_pdf_files
from .pdf_loader import load_textbook_pages
from .prompts import MEDICAL_SAFETY_NOTICE
from .vector_store import VectorStore, get_saved_index_metadata


def get_environment_status() -> dict:
    settings = get_settings()
    pdf_files = list_pdf_files(settings.textbook_dir)
    index_status = get_index_status()
    answer_config = get_llm_config("answer")
    embedding_config = get_embedding_config()
    return {
        "api_configured": has_api_key("default"),
        "answer_api_configured": has_api_key("answer"),
        "answer_model": answer_config["model"],
        "embedding_model": embedding_config["model"],
        "embedding_configured": bool(embedding_config["api_key"]),
        "base_url": answer_config["base_url"],
        "retrieval_backend": settings.retrieval_backend,
        "textbook_dir": str(settings.textbook_dir),
        "textbook_dir_exists": settings.textbook_dir.exists(),
        "pdf_count": len(pdf_files),
        "upload_dir": str(settings.upload_dir),
        "index": index_status,
    }


def get_index_status() -> dict:
    settings = get_settings()
    try:
        return get_saved_index_metadata(settings.index_file)
    except Exception as exc:
        return {
            "exists": False,
            "chunk_count": 0,
            "built_at": None,
            "has_embedding": False,
            "has_tfidf": False,
            "embedding_model": "",
            "retrieval_backend": "",
            "pdf_files": [],
            "message": f"索引读取失败：{exc}",
        }


def build_textbook_index(
    backend: str | None = None,
    max_pages_per_pdf: int | None = None,
    source_dir: Path | None = None,
) -> dict:
    settings = get_settings()
    pdf_dir = source_dir or settings.textbook_dir
    pdf_files = list_pdf_files(pdf_dir)
    selected_backend = (backend or settings.retrieval_backend or "hybrid").lower()

    if not pdf_dir.exists():
        return {
            "ok": False,
            "message": "当前部署环境未发现教材 PDF，可使用普通聊天或上传 PDF 后构建临时索引。",
            "pdf_count": 0,
            "page_count": 0,
            "chunk_count": 0,
            "errors": [],
        }
    if not pdf_files:
        return {
            "ok": False,
            "message": "当前部署环境未发现教材 PDF，可使用普通聊天或上传 PDF 后构建临时索引。",
            "pdf_count": 0,
            "page_count": 0,
            "chunk_count": 0,
            "errors": [],
        }

    pages, errors = load_textbook_pages(pdf_dir, max_pages_per_pdf=max_pages_per_pdf)
    chunks = pages_to_chunks(pages, chunk_size=1000, overlap=150)
    if not chunks:
        return {
            "ok": False,
            "message": "PDF 已扫描，但未提取到可索引文本。请确认 PDF 是否为可复制文本或 OCR 后再试。",
            "pdf_count": len(pdf_files),
            "page_count": len(pages),
            "chunk_count": 0,
            "errors": errors,
        }

    store = VectorStore(settings.index_file)
    metadata = store.build_index(
        chunks,
        use_embedding=selected_backend in {"hybrid", "embedding"},
        backend=selected_backend,
        pdf_files=[path.name for path in pdf_files],
        chunk_size=1000,
        overlap=150,
    )
    store.save_index(settings.index_file)
    message = f"索引构建完成：{len(pdf_files)} 个 PDF，{len(pages)} 页，{len(chunks)} 个 chunk。"
    if metadata.get("embedding_warning"):
        message += f" {metadata['embedding_warning']}"
    return {
        "ok": True,
        "message": message,
        "pdf_count": len(pdf_files),
        "page_count": len(pages),
        "chunk_count": len(chunks),
        "has_embedding": store.has_embedding,
        "has_tfidf": store.has_tfidf,
        "metadata": metadata,
        "errors": errors,
    }


def save_uploaded_pdfs(files: list | None) -> dict:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    if not files:
        return {"ok": False, "message": "未选择上传 PDF。", "count": 0}
    saved = 0
    for file_obj in files:
        source = Path(getattr(file_obj, "name", str(file_obj)))
        if source.suffix.lower() != ".pdf" or not source.exists():
            continue
        target = settings.upload_dir / source.name
        shutil.copy2(source, target)
        saved += 1
    return {"ok": saved > 0, "message": f"已保存 {saved} 个 PDF 到 uploads/。", "count": saved}


def build_uploaded_index(files: list | None, backend: str | None = None, max_pages_per_pdf: int | None = None) -> dict:
    upload_result = save_uploaded_pdfs(files)
    if not upload_result["ok"]:
        return {**upload_result, "pdf_count": 0, "page_count": 0, "chunk_count": 0, "errors": []}
    settings = get_settings()
    return build_textbook_index(backend=backend, max_pages_per_pdf=max_pages_per_pdf, source_dir=settings.upload_dir)


def answer_question(
    user_query: str,
    history: list[dict] | None = None,
    top_k: int = 5,
    force_pdf_search: bool = True,
    debug: bool = False,
) -> dict:
    query = user_query.strip()
    if not query:
        return {"answer": "请输入问题。", "contexts": [], "used_pdf_search": False, "query_plan": {}}

    query_plan = plan_user_query(query, history=history)
    if query_plan.get("intent") == "greeting":
        return {
            "answer": AnswerAgent().answer_greeting(),
            "contexts": [],
            "used_pdf_search": False,
            "query_plan": query_plan,
        }

    if force_pdf_search and query_plan.get("intent") != "non_medical_question":
        query_plan["need_pdf_search"] = True

    answer_agent = AnswerAgent()
    if not query_plan.get("need_pdf_search"):
        return {
            "answer": answer_agent.answer_with_plan(query, query_plan, [], history=history),
            "contexts": [],
            "used_pdf_search": False,
            "query_plan": query_plan,
        }

    settings = get_settings()
    if not settings.index_file.exists():
        answer = answer_agent.answer_with_plan(query, query_plan, [], history=history, index_missing=True)
        return {
            "answer": answer,
            "contexts": [],
            "used_pdf_search": False,
            "query_plan": query_plan,
            "warning": "当前未检测到教材索引，可先构建索引；本次可基于通用模型知识做非诊断性解释。",
        }

    try:
        store = VectorStore.load_index(settings.index_file)
        contexts = PDFSearchAgent(store).search(query_plan, query, top_k=top_k)
    except Exception as exc:
        return {
            "answer": (
                f"教材索引读取或检索失败：{exc}\n\n"
                "本次回答未使用教材检索结果。\n\n"
                f"医学安全提示：{MEDICAL_SAFETY_NOTICE}"
            ),
            "contexts": [],
            "used_pdf_search": False,
            "query_plan": query_plan,
        }

    reliable_contexts = contexts if contexts and contexts[0].get("score", 0) > 0 else []
    answer = answer_agent.answer_with_plan(query, query_plan, reliable_contexts, history=history)
    return {
        "answer": answer,
        "contexts": contexts,
        "used_pdf_search": bool(reliable_contexts),
        "query_plan": query_plan,
    }
