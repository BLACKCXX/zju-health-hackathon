from __future__ import annotations

import time

from src.answer_report_agent import generate_ask_answer, generate_markdown_report, generate_node_detail
from src.chunker import pages_to_chunks
from src.config import get_llm_config, get_settings, has_api_key, list_pdf_files
from src.graph_agent import build_graph, update_graph
from src.integration_agent import apply_teacher_feedback
from src.parser_agent import build_chunks_from_textbooks
from src.retrieval_agent import RetrievalAgent
from src.router_agent import route_user_intent
from src.vector_store import VectorStore, get_saved_index_metadata

from .schemas import (
    AskRequest,
    AskResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    GraphBuildRequest,
    GraphBuildResponse,
    GraphUpdateRequest,
    GraphUpdateResponse,
    IndexBuildRequest,
    IndexBuildResponse,
    IntegratedGraphRequest,
    IntegratedGraphResponse,
    NodeDetailRequest,
    NodeDetailResponse,
    ReportExportRequest,
    ReportExportResponse,
    RetrievedChunk,
    RouteInfo,
    SingleBookGraphRequest,
    SingleBookGraphResponse,
    StatusResponse,
)


USAGE_NOTE = "本系统仅用于学习与信息辅助理解，不提供医学诊断，不能替代医生建议。"


def get_status() -> StatusResponse:
    settings = get_settings()
    index = get_saved_index_metadata(settings.index_file)
    return StatusResponse(
        api_configured=has_api_key("default"),
        textbook_dir_exists=settings.textbook_dir.exists(),
        pdf_count=len(list_pdf_files(settings.textbook_dir)),
        index_exists=bool(index.get("exists")),
        chunk_count=int(index.get("chunk_count", 0) or 0),
        retrieval_backend=settings.retrieval_backend,
        models={
            "default": get_llm_config("default")["model"],
            "router": get_llm_config("router")["model"],
            "graph": settings.graph_model,
            "summary": get_llm_config("summary")["model"],
        },
    )


def build_index_service(request: IndexBuildRequest) -> IndexBuildResponse:
    settings = get_settings()
    if settings.index_file.exists() and not request.force:
        index = get_saved_index_metadata(settings.index_file)
        return IndexBuildResponse(success=True, message="索引已存在，未重建。", pdf_count=len(list_pdf_files(settings.textbook_dir)), chunk_count=int(index.get("chunk_count", 0) or 0))
    if not settings.textbook_dir.exists() or not list_pdf_files(settings.textbook_dir):
        return IndexBuildResponse(success=False, message="未发现教材 PDF。", pdf_count=0, chunk_count=0)
    max_pages = request.max_pages_per_pdf if request.debug else None
    chunks, errors = build_chunks_from_textbooks(max_pages_per_pdf=max_pages)
    if not chunks:
        return IndexBuildResponse(success=False, message="未提取到可索引文本。", pdf_count=len(list_pdf_files(settings.textbook_dir)), chunk_count=0)
    store = VectorStore(settings.index_file)
    store.build_index(
        chunks,
        use_embedding=settings.retrieval_backend in {"hybrid", "embedding"},
        backend=settings.retrieval_backend,
        pdf_files=[path.name for path in list_pdf_files(settings.textbook_dir)],
        chunk_size=settings.chunk_size,
        overlap=settings.chunk_overlap,
    )
    store.save_index(settings.index_file)
    msg = f"索引构建完成，chunk 数量 {len(chunks)}。"
    if errors:
        msg += f" 有 {len(errors)} 个文件读取异常。"
    return IndexBuildResponse(success=True, message=msg, pdf_count=len(list_pdf_files(settings.textbook_dir)), chunk_count=len(chunks))


def ask_service(request: AskRequest) -> AskResponse:
    route = route_user_intent(request.question, current_mode="ask")
    if route["intent"] == "greeting":
        return AskResponse(
            answer="你好，我是 HealthPDF Agent，可以基于 7 本医学教材做带引用的小回答，也可以生成跨教材知识图谱。",
            keywords=[],
            citations=[],
            flashcards=[],
            agent_trace=route,
        )
    evidence = RetrievalAgent().search(request.question, top_k=request.top_k)
    payload = generate_ask_answer(request.question, evidence)
    return AskResponse(**payload)


def graph_build_service(request: GraphBuildRequest) -> GraphBuildResponse:
    evidence = RetrievalAgent().search_for_graph(request.topic, per_book_k=request.top_k_per_book, global_top_k=request.global_top_k)
    graph = build_graph(request.topic, evidence)
    integration = graph.get("integration", {})
    return GraphBuildResponse(
        topic=request.topic,
        graph=graph,
        evidence=graph.get("evidence", []),
        integration_summary=f"{integration.get('overlap_summary', '')} {integration.get('complement_summary', '')}".strip(),
        agent_trace={"intent": "graph_build", "topic": request.topic, "retrieved_count": len(evidence)},
    )


def graph_single_book_service(request: SingleBookGraphRequest) -> SingleBookGraphResponse:
    """Generate a knowledge graph for a single textbook."""
    from src.graph_agent import build_single_book_graph
    evidence = RetrievalAgent().search_for_single_book(request.textbook_id, request.chapter_id, top_k=request.top_k)
    graph = build_single_book_graph(request.textbook_id, request.chapter_id, evidence)
    return SingleBookGraphResponse(
        graph=graph,
        evidence=graph.get("evidence", []),
        agent_trace={"intent": "single_book_graph", "textbook_id": request.textbook_id, "retrieved_count": len(evidence)},
    )


def graph_integrated_service(request: IntegratedGraphRequest) -> IntegratedGraphResponse:
    """Generate an integrated knowledge graph across multiple textbooks."""
    from src.graph_agent import build_integrated_graph
    evidence = RetrievalAgent().search_for_integration(request.topic, request.textbook_ids, request.top_k_per_book, request.global_top_k)
    graph = build_integrated_graph(request.topic, request.textbook_ids, evidence)
    integration = graph.get("integration", {})
    return IntegratedGraphResponse(
        graph=graph,
        integration_summary=f"{integration.get('overlap_summary', '')} {integration.get('complement_summary', '')}".strip(),
        decisions=graph.get("decisions", []),
        evidence=graph.get("evidence", []),
    )


def graph_update_service(request: GraphUpdateRequest) -> GraphUpdateResponse:
    from src.graph_agent import apply_graph_instruction
    evidence = RetrievalAgent().search_for_graph(request.instruction, global_top_k=20)
    graph, patch = apply_graph_instruction(request.current_graph, request.instruction, evidence)
    return GraphUpdateResponse(
        graph=graph,
        patch=patch,
        feedback_record={"instruction": request.instruction, "retrieved_count": len(evidence)},
    )


def node_detail_service(request: NodeDetailRequest) -> NodeDetailResponse:
    evidence = RetrievalAgent().search_for_node_detail(request.node_name, request.graph_context)
    detail = generate_node_detail(request.node_id, request.node_name, request.graph_context, evidence)
    return NodeDetailResponse(**detail)


def feedback_service(request: FeedbackRequest) -> FeedbackResponse:
    graph, record = apply_teacher_feedback(request.graph, request.model_dump())
    return FeedbackResponse(success=True, updated_graph=graph, feedback_record=record)


def report_export_service(request: ReportExportRequest) -> ReportExportResponse:
    from src.answer_report_agent import generate_markdown_report
    graph = request.graph
    topic = graph.get("topic", "知识图谱")
    feedback_records = graph.get("feedback_records", [])
    markdown = generate_markdown_report(topic, graph, feedback_records)
    mode = graph.get("mode", "integrated")
    filename = f"{topic}_{'单本教材' if mode == 'single_book' else '跨教材整合'}报告.md"
    return ReportExportResponse(markdown=markdown, filename=filename)


def run_chat(request: ChatRequest) -> ChatResponse:
    answer = ask_service(AskRequest(question=request.message, top_k=request.top_k))
    chunks = [
        RetrievedChunk(
            source_file=citation.book,
            page=citation.page,
            text=citation.quote,
            match_type="evidence",
        )
        for citation in answer.citations
    ]
    return ChatResponse(
        answer=answer.answer,
        route_info=RouteInfo(intent="ask", need_pdf_search=True, search_keywords=answer.keywords),
        retrieved_chunks=chunks,
        usage_note=USAGE_NOTE,
    )
