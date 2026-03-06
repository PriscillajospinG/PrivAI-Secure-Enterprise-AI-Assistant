# PrivAI – Secure Enterprise AI Assistant

PrivAI is a privacy-first, RAG-based AI assistant designed for secure enterprise document querying. It runs entirely locally using Ollama, ensuring that sensitive company data never leaves your infrastructure.

## Key Features
- **Privacy-First**: No external API calls. Everything runs locally.
- **Local LLM**: Integrated with Ollama (Llama3, Mistral, etc.).
- **RAG Architecture**: Uses ChromaDB for efficient vector search.
- **Agentic Workflow**: Managed by LangGraph with task-based routing.
- **Multi-Capability Knowledge Assistant**:
  - **AI Chat (RAG)**: Query policies, manuals, and internal guides.
  - **AI Summarizer**: Condense large reports and policy files.
  - **AI Analyzer**: Extract terms, risks, and clauses from contracts.
  - **AI Meeting Intel**: Generate action items and summaries from transcripts.
- **Human-in-the-Loop**: Mandatory approval step for all AI outputs.
- **Premium Dashboard**: Modern interface with tabbed tool navigation.


## Prerequisites
1. **Ollama**: Install [Ollama](https://ollama.com/) and download the required models:
   ```bash
   ollama pull llama3
   ollama pull nomic-embed-text
   ```
2. **Python**: Ensure Python 3.9+ is installed.

## Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd PrivAI-Secure-Enterprise-AI-Assistant
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

## Running the Project
1. Start the FastAPI backend from the root directory:
   ```bash
   python -m app.main
   ```
   *Note: Using `python -m app.main` ensures that absolute imports are resolved correctly.*
2. Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

## Folder Structure
- `app/`: Backend implementation (FastAPI, LangChain, LangGraph).
- `data/`: Local storage for documents and vector database.
- `static/`: Frontend assets (HTML, CSS, JS).
- `requirements.txt`: Python dependencies.

## Enterprise Improvements
- **Security**: Implement JWT authentication and Role-Based Access Control (RBAC).
- **Scalability**: Move ChromaDB to a containerized service (e.g., Qdrant or Milvus).
- **Monitoring**: Add logging (ELK stack) and observability for agent performance.
- **Refinement**: Improve the Validation Agent with specific enterprise guidelines and compliance checks.