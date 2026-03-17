from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    CHAT = "chat"
    SEARCH = "search"
    SUMMARIZE = "summarize"
    ANALYZE = "analyze"
    MEETING = "meeting"


class SourceCitation(BaseModel):
    source: str = "unknown"
    chunk_id: str = ""
    page_number: int | None = None
    score: float | None = None
    snippet: str = ""


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    task_type: TaskType = TaskType.CHAT
    top_k: int = Field(default=4, ge=1, le=20)


class QueryResult(BaseModel):
    query: str
    task_type: TaskType
    response: str
    approved: bool
    validation: str
    confidence: float = 0.0
    structured_output: dict[str, Any] | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    context_preview: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    success: Literal[True]
    result: QueryResult
    metadata: dict[str, Any] = Field(default_factory=dict)


class UploadResult(BaseModel):
    uploaded_files: list[str] = Field(default_factory=list)
    indexed_chunks: int = 0
    skipped_files: list[str] = Field(default_factory=list)


class UploadResponse(BaseModel):
    success: Literal[True]
    result: UploadResult
    metadata: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    success: Literal[False]
    error: str
    detail: str | None = None
