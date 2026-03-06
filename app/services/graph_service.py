from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from app.services.agents import (
    retrieval_agent, 
    analysis_agent, 
    generation_agent, 
    validation_agent,
    summarization_agent,
    extraction_agent
)

class AgentState(TypedDict):
    task_type: str # chat, summarize, analyze, meeting
    query: str
    context: List[str]
    analysis_sufficient: bool
    response: str
    validation_result: str
    approved: bool

def task_router(state: AgentState) -> str:
    """Routes the workflow based on task_type."""
    task = state.get("task_type", "chat")
    if task == "chat":
        return "chat"
    elif task == "summarize":
        return "summarize"
    else: # analyze or meeting
        return "analyze"

def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """A placeholder for human approval."""
    print("--- WAITING FOR HUMAN APPROVAL ---")
    return {"approved": True}

def create_rag_graph():
    """Create and compile the LangGraph workflow with conditional routing."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieval_agent)
    workflow.add_node("analyze_context", analysis_agent)
    workflow.add_node("generate_chat", generation_agent)
    workflow.add_node("summarize", summarization_agent)
    workflow.add_node("extract", extraction_agent)
    workflow.add_node("validate", validation_agent)
    workflow.add_node("human_approval", human_approval_node)
    
    # Define Entry and Routing
    workflow.set_entry_point("retrieve")
    
    # After retrieval, route based on task
    workflow.add_conditional_edges(
        "retrieve",
        task_router,
        {
            "chat": "analyze_context",
            "summarize": "summarize",
            "analyze": "extract"
        }
    )
    
    # Chat specific flow
    workflow.add_conditional_edges(
        "analyze_context",
        lambda x: "generate_chat" if x["analysis_sufficient"] else END
    )
    
    # All tasks merge back to validation and approval
    workflow.add_edge("generate_chat", "validate")
    workflow.add_edge("summarize", "validate")
    workflow.add_edge("extract", "validate")
    
    workflow.add_edge("validate", "human_approval")
    workflow.add_edge("human_approval", END)
    
    return workflow.compile()

# Global graph instance
rag_graph = create_rag_graph()
