from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from ..schemas import (
    TextbookUploadResponse,
    TextbookParseRequest,
    TextbookParseResponse,
    TextbookSummary,
    TextbookDetail,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGCitation,
    SourceChunk,
    RAGStatusResponse,
)
from src.config import get_settings
from src.document_parser import generate_textbook_id, parse_document
from src.parser_agent import build_chunks_from_parsed_textbooks
from src.textbook_store import TextbookStore
from src.vector_store import VectorStore, get_saved_index_metadata
from src.retrieval_agent import RetrievalAgent


textbooks_router = APIRouter(prefix="/api/textbooks", tags=["textbooks"])
rag_router = APIRouter(prefix="/api/rag", tags=["rag"])


@textbooks_router.post("/upload", response_model=TextbookUploadResponse)
async def upload_textbooks(files: list[UploadFile] = File(...)) -> TextbookUploadResponse:
    """Upload textbook files (PDF, MD, TXT, DOCX)."""
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    for file in files:
        if not file.filename:
            continue
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".pdf", ".md", ".txt", ".docx"}:
            continue
        dest = settings.upload_dir / file.filename
        try:
            with open(dest, "wb") as f:
                content = await file.read()
                f.write(content)
            saved.append(file.filename)
        except Exception:
            pass

    if not saved:
        return TextbookUploadResponse(success=False, message="未保存任何文件", files=[])
    return TextbookUploadResponse(success=True, message=f"已保存 {len(saved)} 个文件", files=saved)


@textbooks_router.get("", response_model=list[TextbookSummary])
def list_textbooks() -> list[TextbookSummary]:
    """List all discovered textbooks (from uploads and textbooks dir)."""
    settings = get_settings()
    store = TextbookStore()
    summaries = []
    seen_ids = set()

    def make_summary(path: Path, stored_data: dict | None) -> TextbookSummary:
        tid = generate_textbook_id(path.name)
        return TextbookSummary(
            textbook_id=tid,
            filename=path.name,
            title=stored_data.get("title", path.stem) if stored_data else path.stem,
            format=path.suffix[1:],
            total_pages=stored_data.get("total_pages", 0) if stored_data else 0,
            total_chars=stored_data.get("total_chars", 0) if stored_data else 0,
            chapter_count=len(stored_data.get("chapters", [])) if stored_data else 0,
            parse_status=stored_data.get("parse_status", "pending") if stored_data else "pending",
            error=stored_data.get("error", "") if stored_data else "",
            indexed=False,
        )

    if settings.textbook_dir.exists():
        for ext in ["*.pdf", "*.md", "*.txt", "*.docx"]:
            for path in settings.textbook_dir.glob(ext):
                tid = generate_textbook_id(path.name)
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                stored = store.load(tid)
                summaries.append(make_summary(path, stored))

    if settings.upload_dir.exists():
        for ext in ["*.pdf", "*.md", "*.txt", "*.docx"]:
            for path in settings.upload_dir.glob(ext):
                tid = generate_textbook_id(path.name)
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                stored = store.load(tid)
                summaries.append(make_summary(path, stored))

    return summaries


@textbooks_router.post("/parse", response_model=TextbookParseResponse)
def parse_textbooks(request: TextbookParseRequest) -> TextbookParseResponse:
    """Parse textbook files and extract chapter structure. Auto-triggers RAG index build."""
    settings = get_settings()
    store = TextbookStore()
    results = []
    errors = []

    for fname in request.filenames:
        path = settings.upload_dir / fname
        if not path.exists():
            path = settings.textbook_dir / fname
        if not path.exists():
            errors.append({"filename": fname, "error": "File not found"})
            continue

        # Use stable textbook_id based on filename
        textbook_id = generate_textbook_id(fname)
        result = parse_document(path)
        result["textbook_id"] = textbook_id

        if result["parse_status"] == "failed":
            errors.append({"filename": fname, "error": result.get("error", "Unknown error")})
        else:
            store.save(result)
            results.append(result)

    if not results:
        return TextbookParseResponse(
            success=False,
            message="未成功解析任何教材",
            textbooks=[],
            errors=errors,
        )

    # Auto-trigger RAG index build for parsed textbooks
    textbook_ids = [r["textbook_id"] for r in results]
    index_result = _auto_build_index_for_textbooks(textbook_ids)

    summaries = [
        TextbookSummary(
            textbook_id=r["textbook_id"],
            filename=r["filename"],
            title=r.get("title", r["filename"]),
            format=r.get("format", ""),
            total_pages=r.get("total_pages", 0),
            total_chars=r.get("total_chars", 0),
            chapter_count=len(r.get("chapters", [])),
            parse_status=r.get("parse_status", "completed"),
            error=r.get("error", ""),
        )
        for r in results
    ]

    message = f"成功解析 {len(results)} 本教材"
    if index_result.get("success"):
        message += f"，已自动构建索引（{index_result.get('chunk_count', 0)} chunks）"
    elif index_result.get("warning"):
        message += f"，索引警告：{index_result['warning']}"

    return TextbookParseResponse(
        success=True,
        message=message,
        textbooks=summaries,
        errors=errors,
    )


def _auto_build_index_for_textbooks(textbook_ids: list[str]) -> dict:
    """Build or update RAG index for specific textbooks."""
    settings = get_settings()
    store = TextbookStore()
    errors = []

    # Load all parsed textbooks
    all_textbooks = store.list_all()
    if not all_textbooks:
        return {"success": False, "warning": "未找到已解析教材"}

    # Get chunks for these textbooks
    chunks, chunk_errors = build_chunks_from_parsed_textbooks(textbook_ids, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap)
    errors.extend(chunk_errors)

    if not chunks:
        return {"success": False, "warning": "未能从教材提取 chunks"}

    # Build index
    index_path = settings.index_dir / "healthpdf_index.pkl"
    vs = VectorStore(index_path)

    # Try to load existing index and merge
    try:
        existing = VectorStore.load_index(index_path)
        # Merge chunks
        existing_ids = {c["chunk_id"] for c in existing.chunks}
        new_chunks = [c for c in chunks if c["chunk_id"] not in existing_ids]
        all_chunks = existing.chunks + new_chunks
    except Exception:
        all_chunks = chunks

    # Rebuild with all chunks
    metadata = vs.build_index(
        all_chunks,
        use_embedding=settings.retrieval_backend in {"hybrid", "faiss", "embedding"},
        backend=settings.retrieval_backend,
        pdf_files=[t["filename"] for t in all_textbooks],
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    vs.save_index(index_path)

    return {
        "success": True,
        "chunk_count": len(all_chunks),
        "warning": metadata.get("embedding_warning", ""),
    }


@textbooks_router.get("/{textbook_id}", response_model=TextbookDetail)
def get_textbook(textbook_id: str) -> TextbookDetail:
    """Get detailed textbook structure including chapters."""
    store = TextbookStore()
    data = store.load(textbook_id)
    if not data:
        raise HTTPException(status_code=404, detail=f"Textbook {textbook_id} not found")
    return TextbookDetail(
        textbook_id=data["textbook_id"],
        filename=data["filename"],
        title=data.get("title", data["filename"]),
        format=data.get("format", ""),
        total_pages=data.get("total_pages", 0),
        total_chars=data.get("total_chars", 0),
        chapters=data.get("chapters", []),
        parse_status=data.get("parse_status", "completed"),
        error=data.get("error", ""),
    )


@rag_router.post("/index", response_model=RAGIndexResponse)
def build_rag_index(request: RAGIndexRequest) -> RAGIndexResponse:
    """Build RAG index from parsed textbooks."""
    settings = get_settings()
    store = TextbookStore()
    errors = []

    if request.source == "uploads":
        source_dirs = [settings.upload_dir]
    elif request.source == "textbooks":
        source_dirs = [settings.textbook_dir]
    else:
        source_dirs = [settings.upload_dir, settings.textbook_dir]

    all_textbooks = store.list_all()
    if not all_textbooks:
        # Discover and parse from source dirs
        from src.parser_agent import parse_textbook_files
        for src_dir in source_dirs:
            if not src_dir.exists():
                continue
            texs, errs = parse_textbook_files(src_dir)
            for t in texs:
                store.save(t)
            errors.extend(errs)
        all_textbooks = store.list_all()

    if not all_textbooks:
        return RAGIndexResponse(
            success=False,
            message="未发现可索引的教材",
            textbook_count=0,
            chunk_count=0,
            embedding_model=settings.embedding_model,
            backend=request.backend,
            fallback=False,
            errors=[{"error": str(e)} for e in errors],
        )

    textbook_ids = [t["textbook_id"] for t in all_textbooks]
    chunks, chunk_errors = build_chunks_from_parsed_textbooks(
        textbook_ids,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
    )
    errors.extend(chunk_errors)

    if not chunks:
        return RAGIndexResponse(
            success=False,
            message="未能从教材中提取到可索引文本",
            textbook_count=len(all_textbooks),
            chunk_count=0,
            embedding_model=settings.embedding_model,
            backend=request.backend,
            fallback=False,
            errors=errors,
        )

    index_path = settings.index_dir / "healthpdf_index.pkl"
    vs = VectorStore(index_path)

    use_embedding = request.backend in {"hybrid", "faiss", "embedding"}
    metadata = vs.build_index(
        chunks,
        use_embedding=use_embedding,
        backend=request.backend,
        pdf_files=[t["filename"] for t in all_textbooks],
        chunk_size=request.chunk_size,
        overlap=request.chunk_overlap,
    )
    vs.save_index(index_path)

    fallback = bool(metadata.get("embedding_warning"))

    return RAGIndexResponse(
        success=True,
        message=f"索引构建完成：{len(all_textbooks)} 本教材，{len(chunks)} 个 chunk",
        textbook_count=len(all_textbooks),
        chunk_count=len(chunks),
        embedding_model=settings.embedding_model,
        backend=request.backend,
        fallback=fallback,
        errors=errors,
    )


@rag_router.get("/status", response_model=RAGStatusResponse)
def rag_status() -> RAGStatusResponse:
    """Get RAG index status."""
    settings = get_settings()
    try:
        meta = get_saved_index_metadata(settings.index_file)
        return RAGStatusResponse(
            indexed=meta.get("exists", False),
            textbook_count=len(meta.get("pdf_files", [])),
            chunk_count=meta.get("chunk_count", 0),
            embedding_model=meta.get("embedding_model", settings.embedding_model),
            backend=meta.get("retrieval_backend", settings.retrieval_backend),
            fallback_backend="tfidf" if meta.get("embedding_warning") else "",
            created_at=meta.get("created_at", ""),
        )
    except Exception:
        return RAGStatusResponse(indexed=False)


@rag_router.post("/query", response_model=RAGQueryResponse)
def rag_query(request: RAGQueryRequest) -> RAGQueryResponse:
    """Query RAG with a question and get answer with citations."""
    if not request.question.strip():
        return RAGQueryResponse(answer="请输入问题。", citations=[], source_chunks=[])

    retrieval = RetrievalAgent()
    evidence = retrieval.search(request.question, top_k=request.top_k)

    if not evidence:
        return RAGQueryResponse(
            answer="当前知识库中未找到相关信息",
            citations=[],
            source_chunks=[],
        )

    citations = []
    source_chunks = []

    for item in evidence:
        citation = RAGCitation(
            textbook=item.get("book", ""),
            chapter=item.get("chapter", "章节待识别"),
            page=int(item.get("page") or 0),
            relevance_score=float(item.get("score", 0.0)),
            quote=item.get("quote", "")[:300],
        )
        citations.append(citation)

        chunk = SourceChunk(
            chunk_id=item.get("chunk_id", ""),
            textbook=item.get("book", ""),
            chapter=item.get("chapter", ""),
            page_start=int(item.get("page", 0)),
            page_end=int(item.get("page", 0)),
            text=item.get("text", "")[:500],
            relevance_score=float(item.get("score", 0.0)),
        )
        source_chunks.append(chunk)

    try:
        from src.answer_report_agent import generate_ask_answer
        result = generate_ask_answer(request.question, evidence)
        answer = result.get("answer", "")
        if not answer:
            answer = _build_answer_from_citations(request.question, citations)
    except Exception:
        answer = _build_answer_from_citations(request.question, citations)

    return RAGQueryResponse(
        answer=answer,
        citations=citations,
        source_chunks=source_chunks,
    )


def _build_answer_from_citations(question: str, citations: list[RAGCitation]) -> str:
    """Build a simple answer from citations when LLM is unavailable."""
    if not citations:
        return "当前知识库中未找到相关信息"

    lines = [f"根据检索到的教材内容，回答如下：\n"]

    for i, c in enumerate(citations[:3], 1):
        lines.append(f"[{i}] [{c.textbook}, {c.chapter}, 第 {c.page} 页]")
        if c.quote:
            lines.append(f"    \"{c.quote[:150]}...\"")

    lines.append(f"\n请注意，以上内容均来自上述引用来源。")

    return "\n".join(lines)
