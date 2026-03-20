import hashlib
import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Iterable

import chromadb
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings
from app.core.llm_factory import get_embeddings


logger = logging.getLogger(__name__)


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


def split_documents(documents):
    """Split documents into smaller chunks with consistent overlap."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = text_splitter.split_documents(documents)
    for idx, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = idx
    return chunks


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


def _reset_persist_directory() -> None:
    """Reset the persisted Chroma directory when corruption is detected."""
    chroma_dir = Path(settings.CHROMA_DIR)
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir, ignore_errors=True)
    chroma_dir.mkdir(parents=True, exist_ok=True)


def _sanitize_metadata_value(value):
    """Normalize metadata values to Chroma-supported primitive types."""
    if value is None:
        return ""
    if isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple, set, dict)):
        try:
            return json.dumps(value, ensure_ascii=True, sort_keys=True)
        except Exception:
            return str(value)
    return str(value)


def _sanitize_chunk_metadata(chunks) -> None:
    """Coerce metadata keys/values to predictable Chroma-safe shapes."""
    for idx, chunk in enumerate(chunks):
        raw_metadata = getattr(chunk, "metadata", {}) or {}
        normalized = {}
        for key, value in raw_metadata.items():
            normalized[str(key)] = _sanitize_metadata_value(value)
        normalized.setdefault("chunk_index", idx)
        normalized["chunk_index"] = int(normalized["chunk_index"])
        chunk.metadata = normalized


def _build_chunk_ids(chunks) -> list[str]:
    """Build deterministic string IDs and guarantee uniqueness per batch."""
    ids: list[str] = []
    used: set[str] = set()
    for chunk in chunks:
        source_hash = str(chunk.metadata.get("source_hash", ""))
        chunk_index = str(chunk.metadata.get("chunk_index", "0"))
        source_file = str(chunk.metadata.get("source_file", "unknown"))
        candidate = f"{source_file}:{source_hash}:{chunk_index}"
        if not source_hash:
            candidate = str(uuid.uuid4())
        if candidate in used:
            candidate = f"{candidate}:{uuid.uuid4()}"
        used.add(candidate)
        ids.append(str(candidate))
    return ids


def _create_vector_store() -> Chroma:
    embeddings = get_embeddings()
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.CHROMA_DIR)
    store = Chroma(
        client=client,
        collection_name=settings.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DIR,
    )
    # Force a lightweight read to detect malformed stores early.
    _ = store._collection.count()  # noqa: SLF001
    return store


def _is_corruption_error(exc: Exception) -> bool:
    message = str(exc).lower()
    markers = (
        "object of type 'int' has no len",
        "database disk image is malformed",
        "sqlite",
        "corrupt",
    )
    return any(marker in message for marker in markers)


def get_vector_store() -> Chroma:
    """Get or create the persistent Chroma vector store."""
    try:
        return _create_vector_store()
    except Exception as exc:
        if not _is_corruption_error(exc):
            raise
        logger.exception("Detected corrupted Chroma store. Resetting persist directory.")
        _reset_persist_directory()
        return _create_vector_store()


def index_documents(file_paths: list[str] | None = None) -> dict:
    """Incrementally index only requested documents and avoid full rebuild."""
    os.makedirs(settings.DOCS_DIR, exist_ok=True)

    paths = file_paths or _discover_documents()
    paths = [path for path in paths if Path(path).suffix.lower() in settings.allowed_extensions()]

    vector_store = get_vector_store()
    loaded_docs = load_documents(paths)
    if not loaded_docs:
        return {
            "indexed_chunks": 0,
            "indexed_files": [],
            "skipped_files": [os.path.basename(path) for path in paths],
        }

    chunks = split_documents(loaded_docs)
    _sanitize_chunk_metadata(chunks)
    ids = _build_chunk_ids(chunks)

    indexed_files = sorted({doc.metadata.get("source_file", "unknown") for doc in loaded_docs})
    for source_file in indexed_files:
        try:
            vector_store.delete(where={"source_file": source_file})
        except Exception:
            pass

    try:
        vector_store.add_documents(chunks, ids=ids)
    except Exception as exc:
        logger.exception("Failed to add documents to Chroma collection.")
        if not _is_corruption_error(exc):
            raise

        # Recovery path for corrupted/legacy store formats.
        _reset_persist_directory()
        vector_store = get_vector_store()
        all_docs = load_documents(_discover_documents())
        if not all_docs:
            raise
        all_chunks = split_documents(all_docs)
        _sanitize_chunk_metadata(all_chunks)
        all_ids = _build_chunk_ids(all_chunks)
        vector_store.add_documents(all_chunks, ids=all_ids)
        indexed_files = sorted({doc.metadata.get("source_file", "unknown") for doc in all_docs})
        chunks = all_chunks

    return {
        "indexed_chunks": len(chunks),
        "indexed_files": indexed_files,
        "skipped_files": [],
    }


def create_vector_store():
    """Backwards compatible helper for initial indexing flows."""
    return index_documents()


def get_relevant_documents(query: str, top_k: int | None = None):
    """Return documents with relevance scores for the query."""
    vector_store = get_vector_store()
    return vector_store.similarity_search_with_relevance_scores(query, k=top_k or settings.RETRIEVAL_TOP_K)


def get_store_stats() -> dict:
    """Return basic vector collection stats for health/debug endpoints."""
    try:
        vector_store = get_vector_store()
        count = vector_store._collection.count()  # noqa: SLF001
    except Exception:
        count = 0
    return {"collection": settings.COLLECTION_NAME, "document_chunks": count}
