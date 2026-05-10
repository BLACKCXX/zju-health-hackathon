from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    message: str = "HealthPDF Agent backend is running"


class StatusResponse(BaseModel):
    api_configured: bool
    textbook_dir_exists: bool
    pdf_count: int
    index_exists: bool
    chunk_count: int
    retrieval_backend: str
    models: dict[str, str]


class IndexBuildRequest(BaseModel):
    force: bool = False
    debug: bool = False
    max_pages_per_pdf: int | None = 50


class IndexBuildResponse(BaseModel):
    success: bool
    message: str
    pdf_count: int = 0
    chunk_count: int = 0


# Textbook management schemas
class TextbookSummary(BaseModel):
    textbook_id: str
    filename: str
    title: str
    format: str
    total_pages: int = 0
    total_chars: int = 0
    chapter_count: int = 0
    parse_status: str = "pending"
    error: str = ""
    indexed: bool = False


class TextbookDetail(BaseModel):
    textbook_id: str
    filename: str
    title: str
    format: str
    total_pages: int = 0
    total_chars: int = 0
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    parse_status: str = "pending"
    error: str = ""


class TextbookUploadResponse(BaseModel):
    success: bool
    message: str
    files: list[str] = Field(default_factory=list)


class TextbookParseRequest(BaseModel):
    filenames: list[str] = Field(default_factory=list)


class TextbookParseResponse(BaseModel):
    success: bool
    message: str
    textbooks: list[TextbookSummary] = Field(default_factory=list)
    errors: list[dict[str, str]] = Field(default_factory=list)


# RAG schemas
class RAGIndexRequest(BaseModel):
    source: Literal["uploads", "textbooks", "all"] = "all"
    force: bool = False
    chunk_size: int = 700
    chunk_overlap: int = 80
    backend: Literal["faiss", "tfidf", "hybrid"] = "hybrid"


class RAGIndexResponse(BaseModel):
    success: bool
    message: str
    textbook_count: int = 0
    chunk_count: int = 0
    embedding_model: str = ""
    backend: str = "hybrid"
    fallback: bool = False
    errors: list[dict[str, str]] = Field(default_factory=list)


class RAGQueryRequest(BaseModel):
    question: str
    top_k: int = Field(default=5, ge=1, le=20)


class RAGCitation(BaseModel):
    textbook: str = ""
    chapter: str = "章节待识别"
    page: int = 0
    relevance_score: float = 0.0
    quote: str = ""


class SourceChunk(BaseModel):
    chunk_id: str = ""
    textbook: str = ""
    chapter: str = ""
    page_start: int = 0
    page_end: int = 0
    text: str = ""
    relevance_score: float = 0.0


class RAGQueryResponse(BaseModel):
    answer: str
    citations: list[RAGCitation] = Field(default_factory=list)
    source_chunks: list[SourceChunk] = Field(default_factory=list)


class RAGStatusResponse(BaseModel):
    indexed: bool = False
    textbook_count: int = 0
    chunk_count: int = 0
    embedding_model: str = ""
    backend: str = "hybrid"
    fallback_backend: str = ""
    created_at: str = ""


class Citation(BaseModel):
    book: str = ""
    chapter: str = "章节待识别"
    page: int = 0
    quote: str = ""


class Flashcard(BaseModel):
    title: str
    definition: str
    key_points: list[str] = Field(default_factory=list)
    related_terms: list[str] = Field(default_factory=list)
    source_refs: list[dict[str, Any]] = Field(default_factory=list)


class AskRequest(BaseModel):
    question: str
    top_k: int = Field(default=8, ge=1, le=30)


class AskResponse(BaseModel):
    answer: str
    keywords: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    flashcards: list[Flashcard] = Field(default_factory=list)
    agent_trace: dict[str, Any] = Field(default_factory=dict)


class GraphBuildRequest(BaseModel):
    topic: str
    top_k_per_book: int = Field(default=5, ge=1, le=20)
    global_top_k: int = Field(default=30, ge=1, le=80)


class GraphBuildResponse(BaseModel):
    topic: str
    graph: dict[str, Any]
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    integration_summary: str = ""
    agent_trace: dict[str, Any] = Field(default_factory=dict)


class SingleBookGraphRequest(BaseModel):
    textbook_id: str
    chapter_id: str | None = None
    top_k: int = Field(default=20, ge=1, le=50)


class SingleBookGraphResponse(BaseModel):
    graph: dict[str, Any]
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    agent_trace: dict[str, Any] = Field(default_factory=dict)


class IntegratedGraphRequest(BaseModel):
    topic: str
    textbook_ids: list[str] = Field(default_factory=list)
    top_k_per_book: int = Field(default=5, ge=1, le=20)
    global_top_k: int = Field(default=30, ge=1, le=80)


class IntegratedGraphResponse(BaseModel):
    graph: dict[str, Any]
    integration_summary: str = ""
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class GraphUpdateRequest(BaseModel):
    instruction: str
    current_graph: dict[str, Any]


class GraphUpdateResponse(BaseModel):
    graph: dict[str, Any]
    patch: dict[str, Any]
    feedback_record: dict[str, Any] = Field(default_factory=dict)


class NodeDetailRequest(BaseModel):
    node_id: str
    node_name: str
    graph_context: dict[str, Any]


class NodeDetailResponse(BaseModel):
    node_id: str
    name: str
    definition: str
    detail: str
    overlap_analysis: str
    complement_analysis: str
    sources: list[dict[str, Any]] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    action: Literal["keep", "delete", "split", "merge", "edit"]
    target_type: Literal["node", "edge", "decision"]
    target_id: str
    comment: str = ""
    graph: dict[str, Any]


class FeedbackResponse(BaseModel):
    success: bool
    updated_graph: dict[str, Any]
    feedback_record: dict[str, Any]


class ReportExportRequest(BaseModel):
    graph: dict[str, Any]
    format: Literal["markdown"] = "markdown"


class ReportExportResponse(BaseModel):
    markdown: str
    filename: str


# Backward-compatible chat models.
class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = 5
    force_pdf_search: bool = True


class RouteInfo(BaseModel):
    intent: str = "unknown"
    need_pdf_search: bool = False
    search_keywords: list[str] = Field(default_factory=list)
    expanded_query: str = ""
    answer_focus: str = ""


class RetrievedChunk(BaseModel):
    source_file: str
    page: int
    chunk_id: str = ""
    score: float = 0
    match_type: str = ""
    text: str = ""


class ChatResponse(BaseModel):
    answer: str
    route_info: RouteInfo
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    usage_note: str = ""
