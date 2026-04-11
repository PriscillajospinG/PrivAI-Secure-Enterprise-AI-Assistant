import os
import re
from collections import Counter
from typing import Any

from app.core.config import settings
from app.services.document_service import get_collection_count
from app.services.document_service import get_relevant_documents

_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _lexical_overlap_score(query: str, text: str) -> float:
    q_tokens = _tokenize(query)
    t_tokens = _tokenize(text)
    if not q_tokens or not t_tokens:
        return 0.0

    q_counter = Counter(q_tokens)
    t_counter = Counter(t_tokens)
    overlap = sum(min(q_counter[token], t_counter[token]) for token in q_counter)
    return overlap / max(len(q_tokens), 1)


def retrieve_ranked_context(query: str, top_k: int) -> tuple[list[str], list[dict[str, Any]]]:
    candidate_k = max(top_k, top_k * settings.RETRIEVAL_CANDIDATE_MULTIPLIER)
    collection_count = get_collection_count()
    if collection_count > 0:
        candidate_k = min(candidate_k, collection_count)
    docs_with_scores = get_relevant_documents(query=query, top_k=candidate_k)

    ranked_items: list[tuple[float, str, dict[str, Any]]] = []
    for doc, score in docs_with_scores:
        content = (doc.page_content or "").strip()
        if len(content) < settings.RETRIEVAL_MIN_SOURCE_LENGTH:
            continue

        vector_score = float(score) if score is not None else 0.0
        lexical_score = _lexical_overlap_score(query, content)
        blended_score = (0.75 * vector_score) + (0.25 * lexical_score)

        if blended_score < settings.RERANK_MIN_SCORE:
            continue

        page_raw = doc.metadata.get("page")
        page_number = page_raw + 1 if isinstance(page_raw, int) and page_raw >= 0 else None

        raw_source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
        source_name = os.path.basename(str(raw_source)) or "unknown"
        chunk_id = doc.metadata.get("chunk_index")
        if chunk_id is None:
            chunk_id = doc.metadata.get("source_doc_index", 0)

        metadata = {
            "source": source_name,
            "chunk_id": str(chunk_id),
            "page_number": page_number,
            "score": round(blended_score, 4),
            "vector_score": round(vector_score, 4),
            "lexical_score": round(lexical_score, 4),
            "snippet": content[:240],
        }
        ranked_items.append((blended_score, content, metadata))

    ranked_items.sort(key=lambda item: item[0], reverse=True)
    selected = ranked_items[:top_k]

    context = [item[1] for item in selected]
    sources = [item[2] for item in selected]
    return context, sources
