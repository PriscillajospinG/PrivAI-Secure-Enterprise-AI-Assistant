from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.core.llm_factory import get_llm
from app.services.document_service import get_relevant_documents

llm = get_llm()


def retrieval_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Retrieve context chunks and citations for current query."""
    query = state["query"]
    top_k = state.get("effective_top_k", state.get("top_k", settings.RETRIEVAL_TOP_K))
    docs = get_relevant_documents(query=query, top_k=top_k)

    context = []
    sources = []
    for doc in docs:
        content = (doc.page_content or "").strip()
        if len(content) < settings.RETRIEVAL_MIN_SOURCE_LENGTH:
            continue
        context.append(content)
        sources.append(
            {
                "source": doc.metadata.get("source_file", "unknown"),
                "chunk_id": str(doc.metadata.get("chunk_index", "")),
                "snippet": content[:240],
                "score": None,
            }
        )

    return {"context": context, "sources": sources}


def retrieval_retry_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Increase retrieval depth for one retry attempt."""
    attempts = state.get("attempts", 0) + 1
    effective_top_k = state.get("top_k", settings.RETRIEVAL_TOP_K) + (attempts * 2)
    return {"attempts": attempts, "effective_top_k": effective_top_k}


def analysis_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Evaluate whether retrieved context is sufficient to answer query."""
    query = state["query"]
    context = "\n".join(state["context"])

    if not context.strip():
        return {"analysis_sufficient": False, "confidence": 0.0}

    prompt = f"""
    You are a retrieval quality verifier.
    Determine whether the context is sufficient to answer the query.

    Query: {query}
    Context: {context}

    Return only one JSON line:
    {{"sufficient": true|false, "confidence": 0-1}}
    """

    response_msg = llm.invoke([SystemMessage(content=prompt)])
    content = response_msg.content.strip()

    sufficient = "true" in content.lower() or "yes" in content.lower()
    confidence = 0.7 if sufficient else 0.2
    if "confidence" in content.lower():
        try:
            confidence_text = content.split("confidence", 1)[1]
            digits = "".join(ch for ch in confidence_text if ch.isdigit() or ch == ".")
            if digits:
                confidence = max(0.0, min(1.0, float(digits)))
        except Exception:
            pass

    return {"analysis_sufficient": sufficient, "confidence": confidence}


def generation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate a grounded response for chat/search tasks."""
    query = state["query"]
    context = "\n".join(state["context"])

    prompt = f"""
    You are PrivAI, a strict enterprise assistant.
    Answer using only the provided context.

    Context: {context}
    User Query: {query}

    Requirements:
    1. If context is insufficient, respond exactly with: "I'm sorry, but I don't have information on that topic in the enterprise documents I've indexed."
    2. Keep response concise.
    3. Include one short section named "Sources" listing file names from citations.
    """

    response_msg = llm.invoke([HumanMessage(content=prompt)])
    return {"response": response_msg.content}


def fallback_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Return deterministic fallback when retrieval lacks relevant context."""
    return {
        "response": "I'm sorry, but I don't have information on that topic in the enterprise documents I've indexed.",
        "validation_result": "APPROVED: fallback response due to insufficient retrieval context.",
        "approved": True,
        "confidence": 0.0,
    }


def validation_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Validate grounding and assign final approval state."""
    query = state["query"]
    response = state["response"]
    context = "\n".join(state["context"])

    prompt = f"""
    Validate grounding quality.

    Context: {context}
    Query: {query}
    AI Response: {response}

    Output one line:
    APPROVED: <reason>
    or
    REJECTED: <reason>
    """

    validation_msg = llm.invoke([SystemMessage(content=prompt)])
    verdict = validation_msg.content.strip()
    approved = verdict.upper().startswith("APPROVED")
    return {"validation_result": verdict, "approved": approved}


def summarization_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Generate executive summary for retrieved documents."""
    context = "\n".join(state["context"])

    prompt = f"""
    You are an enterprise summarization assistant.
    Create a practical summary from this content.

    Document Content: {context}

    Include:
    1. A concise overview (3-5 sentences).
    2. Key points (bullet list).
    3. Important highlights or warnings.
    """

    response_msg = llm.invoke([SystemMessage(content=prompt)])
    return {"response": response_msg.content}


def extraction_agent(state: dict[str, Any]) -> dict[str, Any]:
    """Extract structured insights for contract and meeting tasks."""
    task_type = state.get("task_type", "analyze")
    context = "\n".join(state["context"])

    if task_type == "meeting":
        instruction = (
            "Create sections for Meeting Summary, Decisions, Action Items (owner + due date if available), and Risks/Blockers."
        )
    else:
        instruction = "Create sections for Key Clauses, Obligations, Risks, and Renewal/Termination terms."

    prompt = f"""
    You are an enterprise document analysis assistant.
    {instruction}

    Document Content: {context}

    Format the output clearly with headers.
    """

    response_msg = llm.invoke([SystemMessage(content=prompt)])
    return {"response": response_msg.content}
