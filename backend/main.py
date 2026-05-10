from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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
    HealthResponse,
    IndexBuildRequest,
    IndexBuildResponse,
    NodeDetailRequest,
    NodeDetailResponse,
    ReportExportRequest,
    ReportExportResponse,
    StatusResponse,
)
from .services import (
    ask_service,
    build_index_service,
    feedback_service,
    get_status,
    graph_build_service,
    graph_update_service,
    node_detail_service,
    report_export_service,
    run_chat,
)
# Import routers from the rag module (which contains both textbooks and rag routers)
from .routers.rag import textbooks_router, rag_router
from .routers.graph import router as graph_router


app = FastAPI(title="HealthPDF Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(textbooks_router)
app.include_router(rag_router)
app.include_router(graph_router)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.get("/api/status", response_model=StatusResponse)
def status() -> StatusResponse:
    return get_status()


@app.post("/api/index/build", response_model=IndexBuildResponse)
def index_build(request: IndexBuildRequest) -> IndexBuildResponse:
    try:
        return build_index_service(request)
    except Exception as exc:
        return IndexBuildResponse(success=False, message=f"索引构建失败：{exc}")


@app.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    try:
        return ask_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"知识小回答服务暂不可用：{exc}") from exc


@app.post("/api/graph/build", response_model=GraphBuildResponse)
def graph_build(request: GraphBuildRequest) -> GraphBuildResponse:
    try:
        return graph_build_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"图谱构建失败：{exc}") from exc


@app.post("/api/graph/update", response_model=GraphUpdateResponse)
def graph_update(request: GraphUpdateRequest) -> GraphUpdateResponse:
    try:
        return graph_update_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"图谱更新失败：{exc}") from exc


@app.post("/api/graph/node-detail", response_model=NodeDetailResponse)
def graph_node_detail(request: NodeDetailRequest) -> NodeDetailResponse:
    try:
        return node_detail_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"节点详情生成失败：{exc}") from exc


@app.post("/api/feedback", response_model=FeedbackResponse)
def feedback(request: FeedbackRequest) -> FeedbackResponse:
    try:
        return feedback_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"教师反馈处理失败：{exc}") from exc


@app.post("/api/report/export", response_model=ReportExportResponse)
def report_export(request: ReportExportRequest) -> ReportExportResponse:
    try:
        return report_export_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"报告导出失败：{exc}") from exc


# Backward-compatible endpoint for the earlier chat UI.
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return run_chat(request)
