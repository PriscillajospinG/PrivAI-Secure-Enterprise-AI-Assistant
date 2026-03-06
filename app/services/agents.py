from typing import List, Dict, Any
from langchain_core.messages import HumanMessage, SystemMessage
from app.core.llm_factory import get_llm
from app.services.document_service import get_vector_store

llm = get_llm()

def retrieval_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Retrieves relevant documents based on the query."""
    print("--- RETRIEVING DOCUMENTS ---")
    query = state["query"]
    vector_store = get_vector_store()
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(query)
    
    return {"context": [doc.page_content for doc in docs]}

def analysis_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Strictly analyzes if the context contains the answer to the query."""
    print("--- ANALYZING CONTEXT FOR RELEVANCE ---")
    query = state["query"]
    context = "\n".join(state["context"])
    
    prompt = f"""
    Evaluate if the following context EXPLICITLY contains information to answer the user's query.
    
    Query: {query}
    Context: {context}
    
    RULES:
    1. Only respond with 'YES' if the answer is directly supported by the context.
    2. If the context is empty or unrelated, respond with 'NO'.
    3. Do not use outside knowledge.
    
    Respond with 'YES' or 'NO' only.
    """
    
    response_msg = llm.invoke([SystemMessage(content=prompt)])
    is_sufficient = "YES" in response_msg.content.upper()
    
    return {"analysis_sufficient": is_sufficient}

def generation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a response ONLY from the provided context."""
    print("--- GENERATING STRICT RESPONSE ---")
    query = state["query"]
    context = "\n".join(state["context"])
    
    prompt = f"""
    You are a strict Enterprise AI Assistant. Use ONLY the provided context to answer the query.
    
    Context: {context}
    User Query: {query}
    
    STRICT RULES:
    1. If the answer is not in the context, say: "I'm sorry, but I don't have information on that topic in the enterprise documents I've indexed."
    2. Do NOT mention your internal knowledge or guess.
    3. Be concise and professional.
    """
    
    response_msg = llm.invoke([HumanMessage(content=prompt)])
    return {"response": response_msg.content}

def validation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validates that the response used only the provided context."""
    print("--- VALIDATING CONTEXT ADHERENCE ---")
    query = state["query"]
    response = state["response"]
    context = "\n".join(state["context"])
    
    prompt = f"""
    Review the following AI response against the provided context and query.
    
    Context: {context}
    Query: {query}
    AI Response: {response}
    
    Is the AI response strictly derived from the context? 
    Does it correctly refuse to answer if the context was insufficient?
    
    Respond with 'APPROVED' if it followed the strict rules, otherwise explain the violation.
    """
    
    validation_msg = llm.invoke([SystemMessage(content=prompt)])
    return {"validation_result": validation_msg.content}
