from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    BuildIndexRequest,
    BuildIndexResponse,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    IndexStatusResponse,
    SystemStatus,
    UploadPdfResponse,
)
from .services import build_index, get_index_status_response, get_status, run_chat, save_uploaded_pdfs


app = FastAPI(title="HealthPDF Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", message="HealthPDF Agent backend is running")


@app.get("/api/status", response_model=SystemStatus)
def status() -> SystemStatus:
    return get_status()


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return run_chat(request)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"聊天服务暂不可用：{exc}") from exc


@app.post("/api/build-index", response_model=BuildIndexResponse)
def build_index_api(request: BuildIndexRequest) -> BuildIndexResponse:
    try:
        return build_index(request)
    except Exception as exc:
        return BuildIndexResponse(success=False, message=f"索引构建失败：{exc}")


@app.get("/api/index-status", response_model=IndexStatusResponse)
def index_status() -> IndexStatusResponse:
    return get_index_status_response()


@app.post("/api/upload-pdf", response_model=UploadPdfResponse)
async def upload_pdf(files: list[UploadFile] = File(...)) -> UploadPdfResponse:
    try:
        return await save_uploaded_pdfs(files)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 上传失败：{exc}") from exc
