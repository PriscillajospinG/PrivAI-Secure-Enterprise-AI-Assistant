import os
import chromadb
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import hashlib
import os
from pathlib import Path
from typing import Iterable

import chromadb
from langchain_community.document_loaders import PyPDFLoader, TextLoader
def load_documents(directory_path: str):
    """Load PDF and TXT documents from the specified directory."""

    # Load PDF files
    pdf_loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    # Load Text files

def _file_hash(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_single_document(file_path: str):
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(file_path).load()
    if suffix == ".txt":
        return TextLoader(file_path, autodetect_encoding=True).load()
    return []


def load_documents(file_paths: Iterable[str]):
    """Load supported documents and attach metadata required for citations."""
    all_docs = []
    for path in file_paths:
        loaded = _load_single_document(path)
        if not loaded:
            continue
        source_file = os.path.basename(path)
        source_hash = _file_hash(path)
        for index, doc in enumerate(loaded):
            doc.metadata = {
                **doc.metadata,
                "source_file": source_file,
                "source_path": path,
                "source_hash": source_hash,
                "source_doc_index": index,
            }
            all_docs.append(doc)
    return all_docs
        chunk_overlap=settings.CHUNK_OVERLAP

    )
    return text_splitter.split_documents(documents)

def create_vector_store():
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    embeddings = get_embeddings()
    chunks = text_splitter.split_documents(documents)
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = idx
    return chunks
    # Ensure the storage directory exists

def _discover_documents() -> list[str]:
    docs_dir = Path(settings.DOCS_DIR)
    if not docs_dir.exists():
        return []

    allowed = settings.allowed_extensions()
    files = []
    for file in docs_dir.iterdir():
        if file.is_file() and file.suffix.lower() in allowed:
            files.append(str(file))
    return sorted(files)


def get_vector_store() -> Chroma:
    """Get or create the persistent Chroma vector store."""
    
        client = chromadb.PersistentClient(
    client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    return Chroma(
        client=client,
        collection_name=settings.COLLECTION_NAME,
        embedding_function=embeddings,
    )


def index_documents(file_paths: list[str] | None = None) -> dict:
    """Incrementally index only requested documents and avoid full rebuild."""
    os.makedirs(settings.DOCS_DIR, exist_ok=True)

    paths = file_paths or _discover_documents()
    paths = [path for path in paths if Path(path).suffix.lower() in settings.allowed_extensions()]

    vector_store = get_vector_store()
    loaded_docs = load_documents(paths)
    if not loaded_docs:
        return {"indexed_chunks": 0, "indexed_files": [], "skipped_files": [os.path.basename(p) for p in paths]}

    chunks = split_documents(loaded_docs)
    ids = []
    for chunk in chunks:
        source_hash = chunk.metadata.get("source_hash", "")
        chunk_index = chunk.metadata.get("chunk_index", 0)
        source_file = chunk.metadata.get("source_file", "unknown")
        ids.append(f"{source_file}:{source_hash}:{chunk_index}")

    indexed_files = sorted({doc.metadata.get("source_file", "unknown") for doc in loaded_docs})
    for source_file in indexed_files:
        try:
            vector_store.delete(where={"source_file": source_file})
        except Exception:
            # Collection may be empty on first run.
            pass

    vector_store.add_documents(chunks, ids=ids)
    return {
        "indexed_chunks": len(chunks),
        "indexed_files": indexed_files,
        "skipped_files": [],
    }


def create_vector_store():
    """Backwards compatible helper for initial indexing flows."""
    return index_documents()


def get_relevant_documents(query: str, top_k: int | None = None):
    """Return documents for query with a configurable top-k."""
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": top_k or settings.RETRIEVAL_TOP_K})
    return retriever.invoke(query)


def get_store_stats() -> dict:
    """Return basic vector collection stats for health/debug endpoints."""
    try:
        vector_store = get_vector_store()
        count = vector_store._collection.count()  # noqa: SLF001
    except Exception:
        count = 0
    return {"collection": settings.COLLECTION_NAME, "document_chunks": count}
