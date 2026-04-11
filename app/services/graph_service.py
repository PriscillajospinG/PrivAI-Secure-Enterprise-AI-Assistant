from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.services.agents import (
    analysis_agent,
    classify_query_agent,
    extraction_agent,
    fallback_agent,
    general_conversation_agent,
    generation_agent,
    retrieval_agent,
    retrieval_retry_agent,
    summarization_agent,
    validation_agent,
    validation_retry_agent,
)


class AgentState(TypedDict):
    task_type: str
    query_route: str
    query: str
    top_k: int
    effective_top_k: int
    attempts: int
    validation_attempts: int
    context: list[str]
    sources: list[dict[str, Any]]
    analysis_sufficient: bool
    confidence: float
    response: str
    structured_output: dict[str, Any] | None
    validation_result: str
    approved: bool
    should_regenerate: bool


def task_router(state: AgentState) -> str:
    task = state.get("task_type", "chat")
    if task == "chat":
        return "chat"
    if task == "search":
        return "search"
    if task == "summarize":
        return "summarize"
    if task == "analyze":
        return "analyze"
    if task == "meeting":
        return "meeting"
    return "chat"


def query_route_router(state: AgentState) -> str:
    return "general" if state.get("query_route") == "general" else "document"


def retrieval_outcome_router(state: AgentState) -> str:
    has_context = bool(state.get("context"))
    attempts = state.get("attempts", 0)
    if has_context:
        return "has_context"
    if attempts < settings.RETRIEVAL_RETRY_LIMIT:
        return "retry"
    if state.get("task_type") in {"chat", "search"}:
        return "general_fallback"
    return "fallback"


def analysis_router(state: AgentState) -> str:
    if state.get("analysis_sufficient"):
        return "generate"
    if state.get("task_type") in {"chat", "search"}:
        return "general_fallback"
    return "fallback"


def validation_router(state: AgentState) -> str:
    if state.get("approved"):
        return "approved"
    if state.get("validation_attempts", 0) < settings.VALIDATION_RETRY_LIMIT:
        return "retry"
    return "fallback"


def regeneration_router(state: AgentState) -> str:
    task = state.get("task_type", "chat")
    if task in {"chat", "search"}:
        return "chat"
    if task == "summarize":
        return "summarize"
    if task == "meeting":
        return "extract_meeting"
    if task == "analyze":
        return "extract_contract"
    return "chat"


def human_approval_node(state: AgentState) -> dict[str, Any]:
    approved = state.get("approved", False)
    if not approved:
        approved = state.get("validation_result", "").upper().startswith("APPROVED")
    return {"approved": approved}


def create_rag_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("classify_query", classify_query_agent)
    workflow.add_node("general_response", general_conversation_agent)
    workflow.add_node("retrieve", retrieval_agent)
    workflow.add_node("retry_retrieve", retrieval_retry_agent)
    workflow.add_node("analyze_context", analysis_agent)
    workflow.add_node("generate_chat", generation_agent)
    workflow.add_node("summarize", summarization_agent)
    workflow.add_node("extract_contract", extraction_agent)
    workflow.add_node("extract_meeting", extraction_agent)
    workflow.add_node("fallback", fallback_agent)
    workflow.add_node("validate", validation_agent)
    workflow.add_node("retry_validate", validation_retry_agent)
    workflow.add_node("retry_dispatch", lambda state: state)
    workflow.add_node("human_approval", human_approval_node)

    workflow.set_entry_point("classify_query")

    workflow.add_conditional_edges(
        "classify_query",
        query_route_router,
        {
            "general": "general_response",
            "document": "retrieve",
        },
    )

    workflow.add_conditional_edges(
        "retrieve",
        retrieval_outcome_router,
        {
            "has_context": "route_by_task",
            "retry": "retry_retrieve",
            "general_fallback": "general_response",
            "fallback": "fallback",
        },
    )

    workflow.add_node("route_by_task", lambda state: state)
    workflow.add_edge("retry_retrieve", "retrieve")

    workflow.add_conditional_edges(
        "route_by_task",
        task_router,
        {
            "chat": "analyze_context",
            "search": "analyze_context",
            "summarize": "summarize",
            "analyze": "extract_contract",
            "meeting": "extract_meeting",
        },
    )

    workflow.add_conditional_edges(
        "analyze_context",
        analysis_router,
        {
            "generate": "generate_chat",
            "general_fallback": "general_response",
            "fallback": "fallback",
        },
    )

    workflow.add_edge("generate_chat", "validate")
    workflow.add_edge("summarize", "validate")
    workflow.add_edge("extract_contract", "validate")
    workflow.add_edge("extract_meeting", "validate")

    workflow.add_conditional_edges(
        "validate",
        validation_router,
        {
            "approved": "human_approval",
            "retry": "retry_validate",
            "fallback": "fallback",
        },
    )

    workflow.add_edge("retry_validate", "retry_dispatch")
    workflow.add_conditional_edges(
        "retry_dispatch",
        regeneration_router,
        {
            "chat": "generate_chat",
            "summarize": "summarize",
            "extract_contract": "extract_contract",
            "extract_meeting": "extract_meeting",
        },
    )

    workflow.add_edge("fallback", "validate")
    workflow.add_edge("general_response", "validate")
    workflow.add_edge("human_approval", END)

    return workflow.compile()


rag_graph = create_rag_graph()
