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
    """Analyzes the context and determines if it's sufficient to answer the query."""
    print("--- ANALYZING CONTEXT ---")
    query = state["query"]
    context = "\n".join(state["context"])
    
    prompt = f"""
    Evaluate the following context based on the user's query.
    Is there enough information to provide a helpful and accurate answer?
    Query: {query}
    Context: {context}
    
    Respond with 'YES' if sufficient, otherwise 'NO'.
    """
    
    response = llm.invoke([SystemMessage(content=prompt)])
    is_sufficient = "YES" in response.upper()
    
    return {"analysis_sufficient": is_sufficient}

def generation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Generates a response based on the query and retrieved context."""
    print("--- GENERATING RESPONSE ---")
    query = state["query"]
    context = "\n".join(state["context"])
    
    prompt = f"""
    Use the following retrieved context to answer the user's query. 
    If you don't know the answer based on the context, just say you don't know.
    Context: {context}
    User Query: {query}
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return {"response": response}

def validation_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the quality and accuracy of the generated response."""
    print("--- VALIDATING RESPONSE ---")
    query = state["query"]
    response = state["response"]
    
    prompt = f"""
    Review the following AI response for accuracy and professionalism.
    Query: {query}
    AI Response: {response}
    
    Is this response high quality and accurate?
    Respond with 'APPROVED' if good, otherwise suggest improvements.
    """
    
    validation = llm.invoke([SystemMessage(content=prompt)])
    return {"validation_result": validation}
