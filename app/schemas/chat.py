from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    response: str
    context: List[str]
    validation: str
    approved: bool

class UploadResponse(BaseModel):
    message: str
    file_count: int
