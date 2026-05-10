"""Graph workspace API routes - single book and integrated graph generation."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import (
    FeedbackRequest,
    FeedbackResponse,
    GraphUpdateRequest,
    GraphUpdateResponse,
    IntegratedGraphRequest,
    IntegratedGraphResponse,
    ReportExportRequest,
    ReportExportResponse,
    SingleBookGraphRequest,
    SingleBookGraphResponse,
)
from ..services import (
    feedback_service,
    graph_integrated_service,
    graph_single_book_service,
    graph_update_service,
    report_export_service,
)

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.post("/single", response_model=SingleBookGraphResponse)
def single_book_graph(request: SingleBookGraphRequest) -> SingleBookGraphResponse:
    """Generate a knowledge graph for a single textbook."""
    try:
        return graph_single_book_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"单本教材图谱生成失败：{exc}") from exc


@router.post("/integrated", response_model=IntegratedGraphResponse)
def integrated_graph(request: IntegratedGraphRequest) -> IntegratedGraphResponse:
    """Generate an integrated knowledge graph across multiple textbooks."""
    try:
        return graph_integrated_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"跨教材整合图谱生成失败：{exc}") from exc


@router.post("/update", response_model=GraphUpdateResponse)
def update_graph(request: GraphUpdateRequest) -> GraphUpdateResponse:
    """Update the current graph based on user instruction."""
    try:
        return graph_update_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"图谱更新失败：{exc}") from exc


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit teacher feedback on graph elements."""
    try:
        return feedback_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"教师反馈处理失败：{exc}") from exc


@router.post("/report/export", response_model=ReportExportResponse)
def export_report(request: ReportExportRequest) -> ReportExportResponse:
    """Export graph as markdown report."""
    try:
        return report_export_service(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"报告导出失败：{exc}") from exc