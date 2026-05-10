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
from src.textbook_store import TextbookStore

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
    GraphExpandRequest,
    GraphExpandResponse,
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
    """Generate a knowledge graph for a single textbook.

    If chapter_id is provided, generates graph for that specific chapter.
    Otherwise builds a top-level graph with textbook as center node and
    its parsed chapters as level-1 nodes.
    """
    store = TextbookStore()
    textbook_data = store.load(request.textbook_id)
    book_title = textbook_data.get("title", request.textbook_id) if textbook_data else request.textbook_id
    chapters = textbook_data.get("chapters", []) if textbook_data else []

    topic = book_title

    # If a specific chapter is requested, use RAG to build a focused graph
    if request.chapter_id and chapters:
        selected_ch = next((c for c in chapters if c.get("chapter_id") == request.chapter_id), None)
        if selected_ch:
            topic = selected_ch.get("title", request.chapter_id)
            evidence = RetrievalAgent().search(f"{book_title} {topic}", top_k=request.top_k or 20)
            graph = build_graph(topic, evidence)
            # Add chapter info to the root node
            if graph.get("nodes"):
                graph["nodes"][0]["chapter"] = topic
                graph["nodes"][0]["page"] = selected_ch.get("page_start", 0)
        else:
            evidence = RetrievalAgent().search(f"教材:{book_title} {request.chapter_id}", top_k=request.top_k or 20)
            graph = build_graph(topic, evidence)
    elif chapters:
        # Build graph from parsed chapter structure
        graph = _build_graph_from_chapters(book_title, chapters, request.textbook_id)
    else:
        evidence = RetrievalAgent().search(f"教材:{topic}", top_k=request.top_k or 20)
        graph = build_graph(topic, evidence)

    graph["mode"] = "single_book"
    graph["textbook_id"] = request.textbook_id
    return SingleBookGraphResponse(
        graph=graph,
        evidence=graph.get("evidence", []),
        agent_trace={"intent": "single_book_graph", "textbook_id": request.textbook_id, "chapter_id": request.chapter_id, "retrieved_count": len(graph.get("evidence", []))},
    )


def _build_graph_from_chapters(book_title: str, chapters: list, textbook_id: str) -> dict:
    """Build a graph with book as center node and chapters as level-1 nodes."""
    from src.graph_agent import _graph_evidence

    nodes = []
    edges = []
    graph_evidence = []

    # Root node: the textbook itself
    root_id = "node_001"
    nodes.append({
        "id": root_id,
        "name": book_title,
        "type": "book",
        "level": 0,
        "summary": f"医学教材：{book_title}，共 {len(chapters)} 个章节",
        "book_sources": [book_title],
        "evidence_ids": [],
        "confidence": 0.95,
        "status": "normal",
        "expandable": True,
        "expanded": False,
        "x": None,
        "y": None,
    })

    # Level-1 nodes: each chapter
    for idx, ch in enumerate(chapters[:30], start=2):  # limit to 30 chapters
        node_id = f"node_{idx:03d}"
        ch_title = ch.get("title", f"章节{idx - 1}")
        page_start = ch.get("page_start", 0)
        page_end = ch.get("page_end", page_start)
        char_count = ch.get("char_count", 0)

        nodes.append({
            "id": node_id,
            "name": ch_title,
            "type": "chapter",
            "level": 1,
            "summary": f"{ch_title}，第 {page_start}-{page_end} 页，字数 {char_count}",
            "book_sources": [book_title],
            "evidence_ids": [],
            "confidence": 0.85,
            "status": "normal",
            "chapter": ch_title,
            "page": page_start,
            "expandable": True,
            "expanded": False,
            "x": None,
            "y": None,
        })

        edges.append({
            "id": f"edge_{idx - 1:03d}",
            "source": root_id,
            "target": node_id,
            "relation": "contains",
            "label": "章节",
            "summary": f"{book_title} 包含 {ch_title}",
            "evidence_ids": [],
            "confidence": 0.9,
            "status": "normal",
        })

    # Compute integration
    from src.integration_agent import summarize_integration
    integrated_text = "；".join(n.get("name", "") for n in nodes)
    return {
        "topic": book_title,
        "nodes": nodes,
        "edges": edges,
        "evidence": graph_evidence,
        "integration": summarize_integration(book_title, graph_evidence, integrated_text),
        "feedback_records": [],
        "mode": "single_book",
        "textbook_id": textbook_id,
    }


def graph_integrated_service(request: IntegratedGraphRequest) -> IntegratedGraphResponse:
    """Generate an integrated knowledge graph across multiple textbooks."""
    evidence = RetrievalAgent().search_for_graph(request.topic, per_book_k=request.top_k_per_book, global_top_k=request.global_top_k)
    graph = build_graph(request.topic, evidence)
    graph["mode"] = "integrated"
    integration = graph.get("integration", {})
    return IntegratedGraphResponse(
        graph=graph,
        integration_summary=f"{integration.get('overlap_summary', '')} {integration.get('complement_summary', '')}".strip(),
        decisions=graph.get("decisions", []),
        evidence=graph.get("evidence", []),
    )


def graph_update_service(request: GraphUpdateRequest) -> GraphUpdateResponse:
    from src.graph_agent import update_graph as do_update
    topic = request.current_graph.get("topic", "知识图谱")
    evidence = RetrievalAgent().search_for_graph(request.instruction, global_top_k=20)
    graph, patch = do_update(topic, request.instruction, request.current_graph, evidence)
    return GraphUpdateResponse(
        graph=graph,
        patch=patch,
        feedback_record={"instruction": request.instruction, "retrieved_count": len(evidence)},
    )


def graph_expand_service(request: GraphExpandRequest) -> GraphExpandResponse:
    """Expand a specific node in the graph.

    For a chapter node: look up chapter content and expand sub-topics.
    For a book node: show all chapter nodes.
    For a concept node: use RAG to find related concepts.
    """
    graph = dict(request.current_graph)
    graph["nodes"] = [dict(n) for n in graph.get("nodes", [])]
    graph["edges"] = [dict(e) for e in graph.get("edges", [])]

    target_node = next((n for n in graph["nodes"] if n.get("id") == request.node_id), None)
    if not target_node:
        return GraphExpandResponse(graph=graph, patch={"added_nodes": [], "added_edges": [], "updated_nodes": []})

    added_nodes = []
    added_edges = []
    topic = graph.get("topic", "")
    textbook_id = graph.get("textbook_id", "")

    node_type = target_node.get("type", "")
    node_name = target_node.get("name", "")

    if node_type == "book":
        # Book node: already expanded in single_book mode, no further expansion
        return GraphExpandResponse(graph=graph, patch={"added_nodes": [], "added_edges": [], "updated_nodes": []})

    if node_type == "chapter":
        # Chapter node: expand to show sub-topics from RAG
        book_title = target_node.get("book_sources", [topic])[0] if target_node.get("book_sources") else topic
        search_query = f"{book_title} {node_name}"
        evidence = RetrievalAgent().search(search_query, top_k=15)
        sub_nodes = _build_concept_nodes_from_evidence(node_name, evidence, start_idx=len(graph["nodes"]) + 1)
        for sn in sub_nodes:
            sn["expandable"] = True
            sn["expanded"] = False
            added_nodes.append(sn)
            added_edges.append({
                "id": f"edge_{len(graph['edges']) + len(added_edges) + 1:03d}",
                "source": request.node_id,
                "target": sn["id"],
                "relation": "contains",
                "label": "包含",
                "summary": f"{node_name} 包含 {sn['name']}",
                "evidence_ids": sn.get("evidence_ids", []),
                "confidence": sn.get("confidence", 0.8),
                "status": "added",
            })
        # Mark current node as expanded
        for n in graph["nodes"]:
            if n["id"] == request.node_id:
                n["expanded"] = True
                break

    else:
        # Concept node: expand to show related concepts
        evidence = RetrievalAgent().search(node_name, top_k=10)
        sub_nodes = _build_concept_nodes_from_evidence(node_name, evidence, start_idx=len(graph["nodes"]) + 1)
        for sn in sub_nodes:
            sn["expandable"] = True
            sn["expanded"] = False
            added_nodes.append(sn)
            added_edges.append({
                "id": f"edge_{len(graph['edges']) + len(added_edges) + 1:03d}",
                "source": request.node_id,
                "target": sn["id"],
                "relation": "related_to",
                "label": "相关",
                "summary": f"{node_name} 相关概念",
                "evidence_ids": sn.get("evidence_ids", []),
                "confidence": sn.get("confidence", 0.75),
                "status": "added",
            })
        for n in graph["nodes"]:
            if n["id"] == request.node_id:
                n["expanded"] = True
                break

    graph["nodes"].extend(added_nodes)
    graph["edges"].extend(added_edges)
    patch = {
        "added_nodes": added_nodes,
        "added_edges": added_edges,
        "updated_nodes": [target_node],
    }
    return GraphExpandResponse(graph=graph, patch=patch)


def _build_concept_nodes_from_evidence(parent_name: str, evidence: list, start_idx: int) -> list[dict]:
    """Build concept nodes from RAG evidence."""
    from src.graph_agent import _extract_concepts, _graph_evidence

    concepts_data = _extract_concepts(parent_name, evidence)
    nodes = []
    for idx, concept in enumerate(concepts_data[:8], start=start_idx):
        nodes.append({
            "id": f"node_{idx:03d}",
            "name": concept.get("name", ""),
            "type": concept.get("type", "concept"),
            "level": 2,
            "summary": concept.get("summary", "")[:200],
            "book_sources": concept.get("books", []),
            "evidence_ids": concept.get("evidence_ids", []),
            "confidence": concept.get("confidence", 0.75),
            "status": "added",
            "x": None,
            "y": None,
        })
    return nodes


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
