from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str
    task_type: Optional[str] = "chat"

class QueryResponse(BaseModel):
    query: str
    response: str
    context: List[str]
    validation: str
    approved: bool
    task_type: str

class UploadResponse(BaseModel):
    message: str
    file_count: int
