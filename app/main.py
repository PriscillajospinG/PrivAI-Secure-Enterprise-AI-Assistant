import os
import shutil
import time
import json
from collections import OrderedDict, defaultdict, deque
from pathlib import Path
import logging
import asyncio

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging
from app.core.llm_factory import check_ollama_status
from app.schemas.chat import ErrorResponse, QueryRequest, QueryResponse, UploadResponse
from app.services.document_service import get_store_stats, index_documents
from app.services.graph_service import rag_graph
from app.services.response_formatter import format_answer, format_sources, format_validation_status
from scripts.evaluate_system import evaluate as run_evaluation_job

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME)

_rate_limiter_state: dict[str, deque[float]] = defaultdict(deque)
_runtime_stats = {
    "start_time": time.time(),
    "request_count": 0,
    "error_count": 0,
    "last_error": "",
    "latency_ms": deque(maxlen=500),
    "per_route": defaultdict(int),
    "cache_hits": 0,
    "cache_misses": 0,
}
_query_cache: OrderedDict[str, tuple[float, QueryResponse]] = OrderedDict()

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
os.makedirs(settings.EVALUATION_REPORT_DIR, exist_ok=True)
os.makedirs(Path(settings.EVALUATION_REPORT_DIR).parent, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(Path(settings.EVALUATION_REPORT_DIR).parent)), name="reports")


@app.on_event("startup")
async def startup_checks():
    logger.info("Starting up application and validating dependencies")
    await run_in_threadpool(get_store_stats)
    check_ollama_status()


@app.middleware("http")
async def simple_rate_limit(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    start = time.perf_counter()
    now = time.time()
    window_start = now - settings.RATE_LIMIT_WINDOW_SECONDS
    bucket = _rate_limiter_state[client_ip]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= settings.RATE_LIMIT_REQUESTS:
        _runtime_stats["error_count"] += 1
        _runtime_stats["last_error"] = "rate_limited"
        return JSONResponse(
            status_code=429,
            content=ErrorResponse(success=False, error="rate_limited", detail="Too many requests").model_dump(),
        )
    bucket.append(now)
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    _runtime_stats["request_count"] += 1
    _runtime_stats["latency_ms"].append(duration_ms)
    _runtime_stats["per_route"][request.url.path] += 1
    if response.status_code >= 500:
        _runtime_stats["error_count"] += 1
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(success=False, error="validation_error", detail=str(exc)).model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception):
    logger.exception("Unhandled exception: %s", exc)
    _runtime_stats["error_count"] += 1
    _runtime_stats["last_error"] = str(exc)
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


def _cache_key(request: QueryRequest) -> str:
    return json.dumps(
        {
            "query": request.query.strip(),
            "task_type": request.task_type.value,
            "top_k": request.top_k,
        },
        sort_keys=True,
    )


def _get_cached_response(key: str) -> QueryResponse | None:
    now = time.time()
    cached = _query_cache.get(key)
    if not cached:
        _runtime_stats["cache_misses"] += 1
        return None

    expires_at, payload = cached
    if expires_at < now:
        _query_cache.pop(key, None)
        _runtime_stats["cache_misses"] += 1
        return None

    _query_cache.move_to_end(key)
    _runtime_stats["cache_hits"] += 1
    return payload


def _set_cached_response(key: str, response: QueryResponse) -> None:
    _query_cache[key] = (time.time() + settings.QUERY_CACHE_TTL_SECONDS, response)
    _query_cache.move_to_end(key)
    while len(_query_cache) > settings.QUERY_CACHE_MAX_ENTRIES:
        _query_cache.popitem(last=False)


def _build_query_response(request: QueryRequest, result: dict, elapsed_ms: float, cache_hit: bool) -> QueryResponse:
    response = result.get("response")
    if not response:
        raise HTTPException(status_code=404, detail="No relevant data found.")

    approved = bool(result.get("approved", False))
    cleaned_sources = format_sources(result.get("sources", []))
    general_route_response = result.get("query_route") == "general"
    no_data_response = str(response).strip().lower().startswith("no relevant data found")
    if no_data_response or general_route_response:
        cleaned_sources = []

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
            "context_preview": [] if (no_data_response or general_route_response) else result.get("context", [])[:3],
        },
        metadata={
            "attempts": result.get("attempts", 0),
            "effective_top_k": result.get("effective_top_k", request.top_k),
            "validation_attempts": result.get("validation_attempts", 0),
            "retrieved_documents": len(result.get("context", [])),
            "latency_ms": round(elapsed_ms, 2),
            "cache_hit": cache_hit,
        },
    )


async def _run_query_workflow(request: QueryRequest, *, allow_cache: bool = True) -> QueryResponse:
    cache_key = _cache_key(request)
    if allow_cache:
        cached = _get_cached_response(cache_key)
        if cached is not None:
            cached_dump = cached.model_dump()
            cached_dump["metadata"]["cache_hit"] = True
            return QueryResponse.model_validate(cached_dump)

    initial_state = {
        "task_type": request.task_type.value,
        "query_route": "document",
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

    logger.info("Processing query task=%s query=%s", request.task_type.value, request.query[:120])
    start = time.perf_counter()
    try:
        result = await run_in_threadpool(rag_graph.invoke, initial_state)
    except Exception as exc:
        logger.exception("Query workflow failed: %s", exc)
        raise HTTPException(status_code=503, detail="Query processing failed. Please try again.") from exc

    elapsed_ms = (time.perf_counter() - start) * 1000
    payload = _build_query_response(request, result, elapsed_ms, False)
    _set_cached_response(cache_key, payload)
    return payload


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=True)}\n\n"

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


@app.get("/diagnostics")
async def diagnostics():
    ollama = check_ollama_status()
    vector_stats = get_store_stats()
    latencies = list(_runtime_stats["latency_ms"])
    avg_latency = round(sum(latencies) / len(latencies), 2) if latencies else 0.0

    return {
        "status": "healthy" if ollama.get("available") else "degraded",
        "uptime_seconds": round(time.time() - _runtime_stats["start_time"], 2),
        "requests": {
            "count": _runtime_stats["request_count"],
            "errors": _runtime_stats["error_count"],
            "avg_latency_ms": avg_latency,
            "route_counts": dict(_runtime_stats["per_route"]),
            "cache_hits": _runtime_stats["cache_hits"],
            "cache_misses": _runtime_stats["cache_misses"],
            "cache_entries": len(_query_cache),
        },
        "last_error": _runtime_stats["last_error"],
        "ollama": ollama,
        "vector_store": vector_stats,
        "config": {
            "retrieval_top_k": settings.RETRIEVAL_TOP_K,
            "chunk_size": settings.CHUNK_SIZE,
            "chunk_overlap": settings.CHUNK_OVERLAP,
            "llm_model": settings.LLM_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL,
        },
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

    logger.info("Indexing %s uploaded files", len(stored_paths))
    try:
        result = await run_in_threadpool(index_documents, stored_paths)
    except Exception as exc:
        logger.exception("Upload indexing failed: %s", exc)
        raise HTTPException(status_code=503, detail="Document indexing failed. Please retry or run reindex.") from exc

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
    logger.info("Starting full reindex operation")
    try:
        result = await run_in_threadpool(index_documents, None)
    except Exception as exc:
        logger.exception("Reindex failed: %s", exc)
        raise HTTPException(status_code=503, detail="Reindex failed due to vector store error.") from exc
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
    return await _run_query_workflow(request, allow_cache=True)


@app.post("/query/stream")
async def query_assistant_stream(request: QueryRequest):
    """Stream response tokens as SSE for live demo UX."""

    async def event_generator():
        try:
            yield _sse_event("status", {"phase": "started", "message": "Preparing query pipeline"})
            payload = await _run_query_workflow(request, allow_cache=True)
            payload_dict = payload.model_dump()
            text = payload_dict.get("result", {}).get("response", "")

            yield _sse_event(
                "status",
                {
                    "phase": "streaming",
                    "message": "Streaming response",
                    "metadata": payload_dict.get("metadata", {}),
                },
            )

            words = text.split(" ")
            for index, word in enumerate(words):
                token = word if index == len(words) - 1 else f"{word} "
                yield _sse_event("token", {"token": token})
                await asyncio.sleep(0.01)

            yield _sse_event("done", payload_dict)
        except HTTPException as exc:
            yield _sse_event("error", {"detail": exc.detail})
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Streaming query failed: %s", exc)
            yield _sse_event("error", {"detail": "Streaming failed."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/evaluation/run")
async def run_evaluation(request: Request):
    """Run evaluation job and persist charts/metrics under reports/evaluation."""
    base_url = str(request.base_url).rstrip("/")
    dataset_path = Path(settings.EVALUATION_DATASET_PATH)
    report_dir = Path(settings.EVALUATION_REPORT_DIR)
    if not dataset_path.exists():
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_path}")

    try:
        metrics = await run_in_threadpool(run_evaluation_job, base_url, dataset_path, report_dir)
    except Exception as exc:
        logger.exception("Evaluation run failed: %s", exc)
        raise HTTPException(status_code=503, detail="Evaluation failed.") from exc

    return {
        "success": True,
        "metrics": metrics,
        "artifacts": {
            "metrics": "/reports/evaluation/metrics.json",
            "confusion_matrix": "/reports/evaluation/confusion_matrix.png",
            "response_times": "/reports/evaluation/response_times.png",
            "metrics_bar_chart": "/reports/evaluation/metrics_bar_chart.png",
            "detailed_results": "/reports/evaluation/detailed_results.json",
        },
    }


@app.get("/evaluation/latest")
async def latest_evaluation():
    """Return latest persisted evaluation metrics and chart URLs."""
    metrics_path = Path(settings.EVALUATION_REPORT_DIR) / "metrics.json"
    if not metrics_path.exists():
        return {
            "available": False,
            "message": "No evaluation report found. Run /evaluation/run first.",
        }

    with metrics_path.open("r", encoding="utf-8") as handle:
        metrics = json.load(handle)

    return {
        "available": True,
        "metrics": metrics,
        "artifacts": {
            "confusion_matrix": "/reports/evaluation/confusion_matrix.png",
            "response_times": "/reports/evaluation/response_times.png",
            "metrics_bar_chart": "/reports/evaluation/metrics_bar_chart.png",
            "detailed_results": "/reports/evaluation/detailed_results.json",
            "metrics": "/reports/evaluation/metrics.json",
        },
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
