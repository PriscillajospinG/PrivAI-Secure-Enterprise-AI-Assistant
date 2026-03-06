from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from app.services.agents import (
    retrieval_agent, 
    analysis_agent, 
    generation_agent, 
    validation_agent
)

class AgentState(TypedDict):
    query: str
    context: List[str]
    analysis_sufficient: bool
    response: str
    validation_result: str
    approved: bool

def human_approval_node(state: AgentState) -> Dict[str, Any]:
    """A placeholder for human approval. In a real system, this would wait for user input."""
    print("--- WAITING FOR HUMAN APPROVAL ---")
    # For this demo, we auto-approve but log that it stopped here.
    # In FastAPI, we can use state management to pause/resume.
    return {"approved": True}

def create_rag_graph():
    """Create and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieval_agent)
    workflow.add_node("analyze", analysis_agent)
    workflow.add_node("generate", generation_agent)
    workflow.add_node("validate", validation_agent)
    workflow.add_node("human_approval", human_approval_node)
    
    # Define edges
    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "analyze")
    
    # Conditional edge after analysis
    workflow.add_conditional_edges(
        "analyze",
        lambda x: "generate" if x["analysis_sufficient"] else END
    )
    
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", "human_approval")
    workflow.add_edge("human_approval", END)
    
    return workflow.compile()

# Global graph instance
rag_graph = create_rag_graph()
