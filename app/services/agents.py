import json
import logging
from typing import Any

from app.core.config import settings
from app.services.generation_service import (
    build_extraction_prompt,
    build_general_prompt,
    build_grounded_qa_prompt,
    build_structured_response,
    build_summary_prompt,
    build_validation_prompt,
    invoke_llm_with_retry,
)
from app.services.retrieval_service import retrieve_ranked_context
from app.services.validation_service import compute_confidence

logger = logging.getLogger(__name__)

GENERAL_QUERY_KEYWORDS = {
    "hello",
    "hi",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
    "how are you",
    "who are you",
    "what can you do",
    "thanks",
    "thank you",
}

DOCUMENT_QUERY_HINTS = {
    "policy",
    "leave",
    "reimbursement",
    "contract",
    "meeting",
    "document",
    "clause",
    "compliance",
    "hr",
    "security",
    "procedure",
    "guideline",
    "benefits",
    "work hours",
}


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


def classify_query_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Classify whether query should use general chat path or document-grounded RAG."""
    task_type = state.get("task_type", "chat")
    if task_type in {"search", "summarize", "analyze", "meeting"}:
        return {"query_route": "document"}

    query = " ".join(str(state.get("query", "")).lower().split())
    if not query:
        return {"query_route": "general"}

    if any(keyword in query for keyword in GENERAL_QUERY_KEYWORDS):
        return {"query_route": "general"}

    if any(hint in query for hint in DOCUMENT_QUERY_HINTS):
        return {"query_route": "document"}

    # Simple heuristic: brief social questions should not go through RAG.
    if len(query.split()) <= 4 and "?" not in query:
        return {"query_route": "general"}

    return {"query_route": "document"}


def general_conversation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Handle open-ended conversational queries without document retrieval."""
    query = state.get("query", "")
    prompt = build_general_prompt(query)
    response_text = invoke_llm_with_retry(prompt, system=True)
    logger.info("General conversation route selected")
    return {
        "response": response_text,
        "structured_output": None,
        "sources": [],
        "analysis_sufficient": True,
        "validation_result": "APPROVED: general conversation route.",
        "approved": True,
        "confidence": 0.85,
        "query_route": "general",
    }


def retrieval_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve context chunks with source metadata and relevance scores."""
    query = state["query"]
    top_k = state.get("effective_top_k", state.get("top_k", settings.RETRIEVAL_TOP_K))
    context, sources = retrieve_ranked_context(query=query, top_k=top_k)
    logger.info("Retrieved %s context chunks (top_k=%s)", len(context), top_k)
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
    prompt = build_grounded_qa_prompt(query=query, context=context)
    response_text = invoke_llm_with_retry(prompt, system=False)
    logger.info("Generated grounded response")
    return {"response": response_text, "structured_output": None}


def summarization_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate structured summary from context only."""
    context = "\n\n".join(state.get("context", []))
    if not context.strip():
        structured = _default_structured_output("summarize")
        return {
            "response": "No relevant document content was found.",
            "structured_output": structured,
        }

    prompt = build_summary_prompt(context)
    response_text = invoke_llm_with_retry(prompt, system=True)
    parsed = _extract_json_object(response_text)
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
    logger.info("Generated summarization output")
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

    prompt, required_keys = build_extraction_prompt(context=context, task_type=task_type)
    response_text = invoke_llm_with_retry(prompt, system=True)
    parsed = _extract_json_object(response_text)

    structured: dict[str, list[str]] = {}
    for key in required_keys:
        structured[key] = _normalize_list(parsed.get(key))

    logger.info("Generated structured extraction for task=%s", task_type)

    return {
        "response": build_structured_response(structured),
        "structured_output": structured,
    }


def fallback_agent(state: dict[str, Any]) -> dict[str, Any]:
    task_type = state.get("task_type", "chat")
    fallback_text = "No relevant data found."
    logger.warning("Fallback agent triggered for task=%s", task_type)
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

    # General-route and deterministic fallback validation should not call validator LLM.
    if state.get("query_route") == "general":
        return {
            "validation_result": "APPROVED: general conversation route.",
            "approved": True,
            "confidence": float(state.get("confidence", 0.85)),
            "should_regenerate": False,
        }

    if response.strip().lower() in {"no relevant data found.", "information not found in provided context."}:
        return {
            "validation_result": "APPROVED: no relevant grounded context available.",
            "approved": True,
            "confidence": 0.0,
            "should_regenerate": False,
        }

    prompt = build_validation_prompt(query=query, context=context, answer=response, task_type=task_type)
    verdict = invoke_llm_with_retry(prompt, system=True).strip()
    approved = verdict.upper().startswith("APPROVED")
    confidence = compute_confidence(state.get("sources", []), approved)
    logger.info("Validation completed approved=%s confidence=%.2f", approved, confidence)

    return {
        "validation_result": verdict,
        "approved": approved,
        "confidence": confidence,
        "should_regenerate": (not approved),
    }


def validation_retry_agent(state: dict[str, Any]) -> dict[str, Any]:
    retries = state.get("validation_attempts", 0) + 1
    return {"validation_attempts": retries}
