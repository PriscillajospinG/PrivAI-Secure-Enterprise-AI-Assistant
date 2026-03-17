import json
import os
from statistics import mean
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.services.document_service import get_relevant_documents

llm = get_llm()


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return {}
    return {}


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        cleaned = [str(item).strip() for item in value if str(item).strip()]
        return cleaned if cleaned else ["Not present in document"]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["Not present in document"]


def _default_structured_output(task_type: str) -> dict[str, Any]:
    if task_type == "meeting":
        return {
            "meeting_summary": ["Not present in document"],
            "key_decisions": ["Not present in document"],
            "action_items": ["Not present in document"],
            "risks_blockers": ["Not present in document"],
        }
    if task_type == "summarize":
        return {
            "overview": ["Not present in document"],
            "key_points": ["Not present in document"],
            "highlights": ["Not present in document"],
        }
    return {
        "key_clauses": ["Not present in document"],
        "obligations": ["Not present in document"],
        "risks": ["Not present in document"],
        "termination_terms": ["Not present in document"],
    }


def _compute_confidence(sources: list[dict[str, Any]], approved: bool) -> float:
    numeric_scores = [float(source.get("score")) for source in sources if source.get("score") is not None]
    retrieval_factor = max(0.0, min(1.0, mean(numeric_scores))) if numeric_scores else 0.2
    source_factor = min(len(sources) / 4.0, 1.0)
    validation_factor = 1.0 if approved else 0.2
    confidence = (0.6 * retrieval_factor) + (0.25 * source_factor) + (0.15 * validation_factor)
    return round(max(0.0, min(1.0, confidence)), 2)


def retrieval_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve context chunks with source metadata and relevance scores."""
    query = state["query"]
    top_k = state.get("effective_top_k", state.get("top_k", settings.RETRIEVAL_TOP_K))
    docs_with_scores = get_relevant_documents(query=query, top_k=top_k)

    context: list[str] = []
    sources: list[dict[str, Any]] = []
    for doc, score in docs_with_scores:
        content = (doc.page_content or "").strip()
        if len(content) < settings.RETRIEVAL_MIN_SOURCE_LENGTH:
            continue

        page_raw = doc.metadata.get("page")
        page_number = None
        if isinstance(page_raw, int):
            page_number = page_raw + 1 if page_raw >= 0 else None

        raw_source = doc.metadata.get("source_file") or doc.metadata.get("source") or "unknown"
        source_name = os.path.basename(str(raw_source)) or "unknown"
        chunk_id = doc.metadata.get("chunk_index")
        if chunk_id is None:
            chunk_id = doc.metadata.get("source_doc_index", len(context))

        context.append(content)
        sources.append(
            {
                "source": source_name,
                "chunk_id": str(chunk_id),
                "page_number": page_number,
                "score": round(float(score), 4) if score is not None else None,
                "snippet": content[:240],
            }
        )

    return {"context": context, "sources": sources}


def retrieval_retry_agent(state: dict[str, Any]) -> dict[str, Any]:
    attempts = state.get("attempts", 0) + 1
    effective_top_k = state.get("top_k", settings.RETRIEVAL_TOP_K) + (attempts * 2)
    return {"attempts": attempts, "effective_top_k": effective_top_k}


def analysis_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Check whether the retrieved context can support an answer."""
    context = state.get("context", [])
    sources = state.get("sources", [])
    if not context:
        return {"analysis_sufficient": False}

    strong_sources = [source for source in sources if (source.get("score") or 0) >= 0.2]
    return {"analysis_sufficient": bool(strong_sources)}


def generation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate grounded Q&A answer strictly from retrieved context."""
    query = state["query"]
    context = "\n\n".join(state.get("context", []))
    sources = ", ".join(sorted({source.get("source", "unknown") for source in state.get("sources", [])}))

    prompt = f"""
You are PrivAI, a strict enterprise assistant.
Answer only using the provided context.
If information is not present, respond exactly: "Information not found in provided context."
Do not infer, invent, or add external facts.

User Query: {query}
Context:
{context}

Return concise text answer followed by a line:
Sources: {sources if sources else 'Not available'}
"""
    response_msg = llm.invoke([HumanMessage(content=prompt)])
    return {"response": response_msg.content, "structured_output": None}


def summarization_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate structured summary from context only."""
    context = "\n\n".join(state.get("context", []))
    if not context.strip():
        structured = _default_structured_output("summarize")
        return {
            "response": "No relevant document content was found.",
            "structured_output": structured,
        }

    prompt = f"""
You are a strict summarization assistant.
Use only the provided context.
If a section cannot be found, set it to "Not present in document".

Context:
{context}

Return only valid JSON with this schema:
{{
  "overview": ["..."],
  "key_points": ["..."],
  "highlights": ["..."]
}}
"""
    response_msg = llm.invoke([SystemMessage(content=prompt)])
    parsed = _extract_json_object(response_msg.content)
    structured = {
        "overview": _normalize_list(parsed.get("overview")),
        "key_points": _normalize_list(parsed.get("key_points")),
        "highlights": _normalize_list(parsed.get("highlights")),
    }

    response = "\n".join(
        [
            "Overview:",
            f"- {structured['overview'][0]}",
            "",
            "Key Points:",
            *[f"- {item}" for item in structured["key_points"]],
            "",
            "Highlights:",
            *[f"- {item}" for item in structured["highlights"]],
        ]
    )
    return {"response": response, "structured_output": structured}


def extraction_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Extract strict structured contract or meeting insights."""
    task_type = state.get("task_type", "analyze")
    context = "\n\n".join(state.get("context", []))
    if not context.strip():
        return {
            "response": "No relevant document context was retrieved.",
            "structured_output": _default_structured_output(task_type),
        }

    if task_type == "meeting":
        schema = """{
  "meeting_summary": ["exact statement from context"],
  "key_decisions": ["exact statement from context"],
  "action_items": ["exact statement from context"],
  "risks_blockers": ["exact statement from context"]
}"""
        required_keys = ["meeting_summary", "key_decisions", "action_items", "risks_blockers"]
    else:
        schema = """{
  "key_clauses": ["exact statement from context"],
  "obligations": ["exact statement from context"],
  "risks": ["exact statement from context"],
  "termination_terms": ["exact statement from context"]
}"""
        required_keys = ["key_clauses", "obligations", "risks", "termination_terms"]

    prompt = f"""
You are a strict enterprise contract and compliance extraction assistant.
Extract only information explicitly present in the provided context.
Never infer or invent clauses, risks, obligations, or terms.
When a section is absent, return exactly "Not present in document" for that section.
When possible, use exact text spans copied from the context.

Context:
{context}

Return only valid JSON matching this schema:
{schema}
"""
    response_msg = llm.invoke([SystemMessage(content=prompt)])
    parsed = _extract_json_object(response_msg.content)

    structured: dict[str, list[str]] = {}
    for key in required_keys:
        structured[key] = _normalize_list(parsed.get(key))

    pretty_lines = []
    for key in required_keys:
        title = key.replace("_", " ").title()
        pretty_lines.append(f"{title}:")
        for item in structured[key]:
            pretty_lines.append(f"- {item}")
        pretty_lines.append("")

    return {
        "response": "\n".join(pretty_lines).strip(),
        "structured_output": structured,
    }


def fallback_agent(state: dict[str, Any]) -> dict[str, Any]:
    task_type = state.get("task_type", "chat")
    fallback_text = "Information not found in provided context."
    return {
        "response": fallback_text,
        "structured_output": _default_structured_output(task_type) if task_type in {"summarize", "analyze", "meeting"} else None,
        "validation_result": "APPROVED: deterministic fallback due to missing retrieval context.",
        "approved": True,
        "confidence": 0.0,
    }


def validation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Validate grounding and structure; compute confidence."""
    query = state.get("query", "")
    response = state.get("response", "")
    context = "\n\n".join(state.get("context", []))
    task_type = state.get("task_type", "chat")

    structure_rule = ""
    if task_type in {"analyze", "meeting", "summarize"}:
        structure_rule = "Also verify that the answer follows required structured extraction sections and avoids hallucinated sections."

    prompt = f"""
You are a grounding validator.
Check whether the answer is fully supported by provided context and contains no hallucinations.
{structure_rule}

Query: {query}
Context:
{context}
Answer:
{response}

Return exactly one line:
APPROVED: <reason>
or
REJECTED: <reason>
"""
    validation_msg = llm.invoke([SystemMessage(content=prompt)])
    verdict = validation_msg.content.strip()
    approved = verdict.upper().startswith("APPROVED")
    confidence = _compute_confidence(state.get("sources", []), approved)

    return {
        "validation_result": verdict,
        "approved": approved,
        "confidence": confidence,
        "should_regenerate": (not approved),
    }


def validation_retry_agent(state: dict[str, Any]) -> dict[str, Any]:
    retries = state.get("validation_attempts", 0) + 1
    return {"validation_attempts": retries}
