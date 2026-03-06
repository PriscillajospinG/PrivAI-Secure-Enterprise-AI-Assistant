# PrivAI – Secure Enterprise AI Knowledge Assistant

PrivAI is a privacy-first, full-stack RAG (Retrieval-Augmented Generation) application designed for secure enterprise document intelligence. It runs entirely on your local infrastructure using Ollama, ensuring that sensitive company knowledge never leaves the organization.

## 🚀 Key Features

- **Privacy-First Architecture**: Zero external API calls. All processing happens locally.
- **Advanced RAG Engine**: Integrated with ChromaDB and LangChain for precise document retrieval.
- **Agentic Workflows**: Orchestrated by LangGraph with specialized AI agents:
  - **AI Chat (RAG)**: Conversational search over policies, manuals, and data.
  - **AI Summarizer**: Intelligent condensation of large reports and documents.
  - **AI Analyzer**: Automated extraction of risks, clauses, and terms from legal contracts.
  - **AI Meeting Intel**: Generates action items and summaries from transcripts.
- **Modern React Interface**: A premium, tabbed dashboard with real-time feedback.
- **Human-in-the-Loop**: Mandatory approval step to ensure AI accuracy and safety.

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed:

1.  **Ollama**: Download and install from [ollama.com](https://ollama.com/).
    - Pull the required models:
      ```bash
      ollama pull llama3
      ollama pull nomic-embed-text
      ```
2.  **Python 3.9+**: For the FastAPI backend.
3.  **Node.js & NPM**: For the React frontend.

## 📦 Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd PrivAI-Secure-Enterprise-AI-Assistant
```

### 2. Backend Setup (FastAPI)
```bash
# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python -m app.main
```
The backend will run at `http://localhost:8000`.

### 3. Frontend Setup (React + Vite)
Open a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```
The frontend will be available at `http://localhost:5173`.

## 📖 How to Use

1.  **Upload Knowledge**: Go to the **Document Manager** tab and upload your PDFs or text files (example files are provided in `data/docs/`).
2.  **Ask Questions**: Use the **AI Chat** to query your documents. Notice the status bar showing the agentic progress (Retrieval -> Analysis -> Generation).
3.  **Perform Analysis**:
    - Switch to **Summarizer** for quick highlights.
    - Use **Contract Analyzer** for legal reviews.
    - Use **Meeting Intel** for transcript processing.
4.  **Approve Responses**: Every AI response must be reviewed and approved in the UI before it is finalized, ensuring a human remains in control.

## 📂 Project Structure

- `app/`: FastAPI backend implementation.
  - `core/`: Configuration and LLM logic.
  - `services/`: LangGraph orchestration, agents, and RAG service.
  - `schemas/`: Pydantic models for API validation.
- `frontend/`: Modern React dashboard (TypeScript, Tailwind CSS).
- `data/`: Local storage for documents and ChromaDB vector store.
- `requirements.txt`: Backend dependencies.

## 🛡️ Enterprise-Grade Roadmap

- **Authentication**: Integration with LDAP/SSO.
- **Fine-Tuning**: Support for domain-specific local models.
- **Observability**: Real-time agent monitoring and token usage tracking.
- **Access Control**: Document-level permissions for multi-department use.

---
*Built with ❤️ for Privacy and Security.*