from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from app.core.config import settings
from app.services.agents import (
    analysis_agent,
    extraction_agent,
    fallback_agent,
    generation_agent,
    retrieval_agent,
    retrieval_retry_agent,
    validation_agent,
    summarization_agent,
)


class AgentState(TypedDict):
    task_type: str  # chat, search, summarize, analyze, meeting
    query: str
    top_k: int
    effective_top_k: int
    attempts: int
    context: list[str]
    sources: list[dict[str, Any]]
    analysis_sufficient: bool
    confidence: float
    response: str
    validation_result: str
    approved: bool


def task_router(state: AgentState) -> str:
    """Routes the workflow based on task_type."""
    task = state.get("task_type", "chat")
    if task in {"chat", "search"}:
        return "chat"
    if task == "summarize":
        return "summarize"
    if task in {"analyze", "meeting"}:
        return "analyze"
    return "chat"


def retrieval_outcome_router(state: AgentState) -> str:
    has_context = bool(state.get("context"))
    attempts = state.get("attempts", 0)
    if has_context:
        return "has_context"
    if attempts < settings.RETRIEVAL_RETRY_LIMIT:
        return "retry"
    return "fallback"


def analysis_router(state: AgentState) -> str:
    return "generate" if state.get("analysis_sufficient") else "fallback"


def human_approval_node(state: AgentState) -> dict[str, Any]:
    """Production-ready default can be replaced with real HITL callback state."""
    approved = state.get("approved", False)
    if not approved:
        approved = state.get("validation_result", "").upper().startswith("APPROVED")
    return {"approved": approved}


def create_rag_graph():
    """Create and compile the LangGraph workflow with resilience and routing."""
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve", retrieval_agent)
    workflow.add_node("retry_retrieve", retrieval_retry_agent)
    workflow.add_node("analyze_context", analysis_agent)
    workflow.add_node("generate_chat", generation_agent)
    workflow.add_node("summarize", summarization_agent)
    workflow.add_node("extract", extraction_agent)
    workflow.add_node("fallback", fallback_agent)
    workflow.add_node("validate", validation_agent)
    workflow.add_node("human_approval", human_approval_node)

    workflow.set_entry_point("retrieve")

    workflow.add_conditional_edges(
        "retrieve",
        retrieval_outcome_router,
        {
            "has_context": "route_by_task",
            "retry": "retry_retrieve",
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
            "summarize": "summarize",
            "analyze": "extract",
        },
    )

    workflow.add_conditional_edges(
        "analyze_context",
        analysis_router,
        {"generate": "generate_chat", "fallback": "fallback"},
    )

    workflow.add_edge("generate_chat", "validate")
    workflow.add_edge("summarize", "validate")
    workflow.add_edge("extract", "validate")
    workflow.add_edge("fallback", "human_approval")
    workflow.add_edge("validate", "human_approval")
    workflow.add_edge("human_approval", END)

    return workflow.compile()


# Global graph instance
rag_graph = create_rag_graph()
