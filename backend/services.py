from __future__ import annotations

from pathlib import Path
import shutil
import time

from fastapi import UploadFile

from src.chunker import pages_to_chunks
from src.config import get_settings, list_pdf_files
from src.pdf_loader import load_textbook_pages
from src.rag_pipeline import answer_question, get_environment_status, get_index_status
from src.vector_store import VectorStore

from .schemas import (
    BuildIndexRequest,
    BuildIndexResponse,
    ChatRequest,
    ChatResponse,
    IndexStatusResponse,
    RetrievedChunk,
    RouteInfo,
    SystemStatus,
    UploadPdfResponse,
)


USAGE_NOTE = "本系统仅用于学习与信息辅助理解，不提供医学诊断，不能替代医生建议。"


def get_status() -> SystemStatus:
    status = get_environment_status()
    index = status.get("index", {})
    return SystemStatus(
        api_configured=bool(status.get("answer_api_configured") or status.get("api_configured")),
        answer_model=status.get("answer_model", ""),
        embedding_model=status.get("embedding_model", ""),
        textbook_dir_exists=bool(status.get("textbook_dir_exists")),
        pdf_count=int(status.get("pdf_count", 0)),
        index_exists=bool(index.get("exists")),
        chunk_count=int(index.get("chunk_count", 0) or 0),
        has_embedding=bool(index.get("has_embedding")),
        has_tfidf=bool(index.get("has_tfidf")),
        created_at=index.get("built_at") or index.get("created_at") or "",
    )


def get_index_status_response() -> IndexStatusResponse:
    index = get_index_status()
    return IndexStatusResponse(
        index_exists=bool(index.get("exists")),
        chunk_count=int(index.get("chunk_count", 0) or 0),
        has_embedding=bool(index.get("has_embedding")),
        has_tfidf=bool(index.get("has_tfidf")),
        created_at=index.get("built_at") or index.get("created_at") or "",
        embedding_model=index.get("embedding_model", ""),
        retrieval_backend=index.get("retrieval_backend", ""),
        pdf_files=list(index.get("pdf_files") or []),
    )


def run_chat(request: ChatRequest) -> ChatResponse:
    history = [item.model_dump() for item in request.history]
    result = answer_question(
        user_query=request.message,
        history=history,
        top_k=request.top_k,
        force_pdf_search=request.force_pdf_search,
    )
    route_info = RouteInfo(**_normalize_route_info(result.get("query_plan", {})))
    chunks = [_normalize_chunk(item) for item in result.get("contexts", [])]
    return ChatResponse(
        answer=str(result.get("answer", "")),
        route_info=route_info,
        retrieved_chunks=chunks,
        usage_note=str(result.get("warning") or USAGE_NOTE),
    )


def build_index(request: BuildIndexRequest) -> BuildIndexResponse:
    settings = get_settings()
    start = time.time()
    if settings.index_file.exists() and not request.force:
        status = get_index_status_response()
        return BuildIndexResponse(
            success=True,
            message="索引已存在，未重建；如需重建请开启 force。",
            pdf_count=len(list_pdf_files(settings.textbook_dir)),
            chunk_count=status.chunk_count,
            has_embedding=bool(status.has_embedding),
            has_tfidf=bool(status.has_tfidf),
            elapsed_sec=round(time.time() - start, 2),
        )

    if request.chunk_size <= request.overlap:
        return BuildIndexResponse(
            success=False,
            message="chunk_size 必须大于 overlap。",
            elapsed_sec=round(time.time() - start, 2),
        )

    pdf_files = list_pdf_files(settings.textbook_dir)
    if not settings.textbook_dir.exists() or not pdf_files:
        return BuildIndexResponse(
            success=False,
            message="当前部署环境未发现教材 PDF，可使用普通聊天或上传 PDF 后构建临时索引。",
            elapsed_sec=round(time.time() - start, 2),
        )

    max_pages = request.max_pages_per_pdf if request.debug else None
    pages, errors = load_textbook_pages(settings.textbook_dir, max_pages_per_pdf=max_pages)
    chunks = pages_to_chunks(pages, chunk_size=request.chunk_size, overlap=request.overlap)
    if not chunks:
        return BuildIndexResponse(
            success=False,
            message="PDF 已扫描，但未提取到可索引文本。",
            pdf_count=len(pdf_files),
            elapsed_sec=round(time.time() - start, 2),
        )

    store = VectorStore(settings.index_file)
    metadata = store.build_index(
        chunks,
        use_embedding=request.backend in {"hybrid", "embedding"},
        backend=request.backend,
        pdf_files=[path.name for path in pdf_files],
        chunk_size=request.chunk_size,
        overlap=request.overlap,
    )
    store.save_index(settings.index_file)
    warning = metadata.get("embedding_warning", "")
    if errors:
        warning = (warning + " " if warning else "") + f"{len(errors)} 个 PDF 读取异常，已跳过。"

    return BuildIndexResponse(
        success=True,
        message=f"索引构建完成：{len(pdf_files)} 个 PDF，{len(chunks)} 个 chunk。",
        pdf_count=len(pdf_files),
        chunk_count=len(chunks),
        has_embedding=store.has_embedding,
        has_tfidf=store.has_tfidf,
        elapsed_sec=round(time.time() - start, 2),
        warning=warning,
    )


async def save_uploaded_pdfs(files: list[UploadFile]) -> UploadPdfResponse:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    saved: list[str] = []
    for upload in files:
        filename = Path(upload.filename or "").name
        if not filename.lower().endswith(".pdf"):
            continue
        target = settings.upload_dir / filename
        with target.open("wb") as output:
            shutil.copyfileobj(upload.file, output)
        saved.append(filename)
    if not saved:
        return UploadPdfResponse(success=False, message="未保存文件：请上传 PDF 文件。", files=[])
    return UploadPdfResponse(success=True, message=f"已保存 {len(saved)} 个 PDF 到 uploads/。", files=saved)


def _normalize_route_info(plan: dict) -> dict:
    return {
        "intent": str(plan.get("intent") or "unknown"),
        "need_pdf_search": bool(plan.get("need_pdf_search")),
        "user_emotion_reply": str(plan.get("user_emotion_reply") or ""),
        "search_keywords": list(plan.get("search_keywords") or []),
        "expanded_query": str(plan.get("expanded_query") or ""),
        "answer_focus": str(plan.get("answer_focus") or ""),
        "conversation_goal": str(plan.get("conversation_goal") or ""),
    }


def _normalize_chunk(item: dict) -> RetrievedChunk:
    return RetrievedChunk(
        source_file=str(item.get("source_file") or ""),
        page=int(item.get("page") or 0),
        chunk_id=str(item.get("chunk_id") or ""),
        score=float(item.get("score") or 0.0),
        match_type=str(item.get("match_type") or ""),
        text=str(item.get("text") or ""),
    )
