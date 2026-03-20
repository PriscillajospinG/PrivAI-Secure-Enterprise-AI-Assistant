import os
import shutil
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.llm_factory import check_ollama_status
from app.schemas.chat import ErrorResponse, QueryRequest, QueryResponse, UploadResponse
from app.services.document_service import get_store_stats, index_documents
from app.services.graph_service import rag_graph
from app.services.response_formatter import format_answer, format_sources, format_validation_status

app = FastAPI(title=settings.PROJECT_NAME)

_rate_limiter_state: dict[str, deque[float]] = defaultdict(deque)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs(settings.DOCS_DIR, exist_ok=True)
os.makedirs(settings.CHROMA_DIR, exist_ok=True)


@app.on_event("startup")
async def startup_checks():
    await run_in_threadpool(get_store_stats)
    check_ollama_status()


@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS
    bucket = _rate_limiter_state[client_ip]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_REQUESTS:
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(success=False, error="rate_limited", detail="Too many requests").model_dump(),
        )
    bucket.append(now)
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(success=False, error="validation_error", detail=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            success=False,
            error="internal_server_error",
            detail=str(exc) if settings.APP_ENV != "production" else "An internal error occurred.",
        ).model_dump(),
    )


def _safe_filename(filename: str) -> str:
    base = os.path.basename(filename or "")
    safe = "".join(ch for ch in base if ch.isalnum() or ch in {"-", "_", "."}).strip(".")
    if not safe:
        safe = f"upload_{int(time.time() * 1000)}.txt"
    return safe


def _validate_extension(filename: str) -> bool:
    return Path(filename).suffix.lower() in settings.allowed_extensions()

@app.get("/health")
async def health_check():
    ollama = check_ollama_status()
    vector_stats = get_store_stats()
    return {
        "status": "healthy" if ollama.get("available") else "degraded",
        "ollama": ollama,
        "vector_store": vector_stats,
        "environment": settings.APP_ENV,
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)):
    """Upload documents and incrementally index supported files."""
    if len(files) > settings.MAX_UPLOAD_FILES:
        raise HTTPException(status_code=400, detail=f"Too many files. Max allowed is {settings.MAX_UPLOAD_FILES}.")

    stored_paths: list[str] = []
    uploaded_names: list[str] = []
    skipped_files: list[str] = []

    for file in files:
        safe_name = _safe_filename(file.filename)
        if not _validate_extension(safe_name):
            skipped_files.append(file.filename)
            continue

        file_path = os.path.join(settings.DOCS_DIR, safe_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        stored_paths.append(file_path)
        uploaded_names.append(safe_name)

    result = await run_in_threadpool(index_documents, stored_paths)

    return UploadResponse(
        success=True,
        result={
            "uploaded_files": uploaded_names,
            "indexed_chunks": result["indexed_chunks"],
            "skipped_files": skipped_files,
        },
        metadata={"indexed_files": result["indexed_files"]},
    )


@app.post("/reindex", response_model=UploadResponse)
async def reindex_documents():
    """Re-index all supported documents in data/docs to refresh metadata."""
    result = await run_in_threadpool(index_documents, None)
    return UploadResponse(
        success=True,
        result={
            "uploaded_files": result["indexed_files"],
            "indexed_chunks": result["indexed_chunks"],
            "skipped_files": result["skipped_files"],
        },
        metadata={"indexed_files": result["indexed_files"], "reindexed": True},
    )

@app.post("/query", response_model=QueryResponse)
async def query_assistant(request: QueryRequest):
    """Query the RAG pipeline with LangGraph orchestration."""
    initial_state = {
        "task_type": request.task_type.value,
        "query": request.query,
        "top_k": request.top_k,
        "effective_top_k": request.top_k,
        "attempts": 0,
        "validation_attempts": 0,
        "context": [],
        "sources": [],
        "analysis_sufficient": False,
        "confidence": 0.0,
        "response": "",
        "structured_output": None,
        "validation_result": "",
        "approved": False,
        "should_regenerate": False,
    }

    result = await run_in_threadpool(rag_graph.invoke, initial_state)

    response = result.get("response")
    if not response:
        raise HTTPException(status_code=404, detail="Assistant could not find relevant information.")

    approved = bool(result.get("approved", False))
    cleaned_sources = format_sources(result.get("sources", []))
    formatted_answer = format_answer(
        query=request.query,
        response=response,
        structured_output=result.get("structured_output"),
    )
    validation_status = format_validation_status(approved)

    return QueryResponse(
        success=True,
        result={
            "query": request.query,
            "task_type": request.task_type,
            "response": formatted_answer,
            "approved": approved,
            "validation": result.get("validation_result", ""),
            "validation_status": validation_status,
            "confidence": float(result.get("confidence", 0.0)),
            "structured_output": result.get("structured_output"),
            "sources": cleaned_sources,
            "context_preview": result.get("context", [])[:3],
        },
        metadata={
            "attempts": result.get("attempts", 0),
            "effective_top_k": result.get("effective_top_k", request.top_k),
            "validation_attempts": result.get("validation_attempts", 0),
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
