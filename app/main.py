import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.schemas.chat import QueryRequest, QueryResponse, UploadResponse
from app.services.document_service import create_vector_store
from app.services.graph_service import rag_graph

app = FastAPI(title=settings.PROJECT_NAME)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure directories exist
os.makedirs(settings.DOCS_DIR, exist_ok=True)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload", response_model=UploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)):
    """Upload documents and refresh the vector store."""
    for file in files:
        file_path = os.path.join(settings.DOCS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    
    # Reload vector store after upload
    create_vector_store()
    
    return UploadResponse(
        message="Documents uploaded and indexed successfully.",
        file_count=len(files)
    )

@app.post("/query", response_model=QueryResponse)
async def query_assistant(request: QueryRequest):
    """Query the RAG pipeline with routing support for different task types."""
    try:
        # Run the LangGraph workflow
        initial_state = {
            "task_type": request.task_type,
            "query": request.query,
            "context": [],
            "analysis_sufficient": False,
            "response": "",
            "validation_result": "",
            "approved": False
        }
        
        result = rag_graph.invoke(initial_state)
        
        if not result.get("response"):
            raise HTTPException(status_code=404, detail="Assistant could not find relevant information.")
            
        return QueryResponse(
            query=request.query,
            response=result["response"],
            context=result["context"],
            validation=result["validation_result"],
            approved=result["approved"],
            task_type=result["task_type"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend static files (Disabled to avoid confusion with new React frontend)
# app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
