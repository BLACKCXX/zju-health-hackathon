from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    message: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=10)
    force_pdf_search: bool = True


class RouteInfo(BaseModel):
    intent: str = "unknown"
    need_pdf_search: bool = False
    user_emotion_reply: str | None = ""
    search_keywords: list[str] = Field(default_factory=list)
    expanded_query: str | None = ""
    answer_focus: str | None = ""
    conversation_goal: str | None = ""


class RetrievedChunk(BaseModel):
    source_file: str
    page: int
    chunk_id: str | None = ""
    score: float | None = 0.0
    match_type: str | None = ""
    text: str


class ChatResponse(BaseModel):
    answer: str
    route_info: RouteInfo
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    usage_note: str = ""


class SystemStatus(BaseModel):
    api_configured: bool
    answer_model: str | None = ""
    embedding_model: str | None = ""
    textbook_dir_exists: bool
    pdf_count: int
    index_exists: bool
    chunk_count: int | None = 0
    has_embedding: bool | None = False
    has_tfidf: bool | None = False
    created_at: str | None = ""


class BuildIndexRequest(BaseModel):
    backend: Literal["tfidf", "hybrid", "embedding"] = "hybrid"
    force: bool = True
    debug: bool = False
    max_pages_per_pdf: int | None = Field(default=50, ge=1)
    chunk_size: int = Field(default=1000, ge=300, le=3000)
    overlap: int = Field(default=150, ge=0, le=1000)


class BuildIndexResponse(BaseModel):
    success: bool
    message: str
    pdf_count: int = 0
    chunk_count: int = 0
    has_embedding: bool = False
    has_tfidf: bool = False
    elapsed_sec: float = 0.0
    warning: str | None = ""


class IndexStatusResponse(BaseModel):
    index_exists: bool
    chunk_count: int = 0
    has_embedding: bool = False
    has_tfidf: bool = False
    created_at: str | None = ""
    embedding_model: str | None = ""
    retrieval_backend: str | None = ""
    pdf_files: list[str] = Field(default_factory=list)


class UploadPdfResponse(BaseModel):
    success: bool
    message: str
    files: list[str] = Field(default_factory=list)
