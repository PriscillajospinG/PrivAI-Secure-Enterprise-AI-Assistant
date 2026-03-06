import os
from typing import List
from langchain_community.document_loaders import PyPDFLoader, TextLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from app.core.config import settings
from app.core.llm_factory import get_embeddings

def load_documents(directory_path: str):
    """Load PDF and TXT documents from the specified directory."""
    # Load PDF files
    pdf_loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    # Load Text files
    txt_loader = DirectoryLoader(directory_path, glob="**/*.txt", loader_cls=TextLoader)
    
    docs = pdf_loader.load() + txt_loader.load()
    return docs

def split_documents(documents):
    """Split documents into smaller chunks."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP
    )
    return text_splitter.split_documents(documents)

def create_vector_store():
    """Load documents, split them, and create a Chroma vector store."""
    embeddings = get_embeddings()
    
    # Ensure the storage directory exists
    os.makedirs(settings.DOCS_DIR, exist_ok=True)
    os.makedirs(settings.CHROMA_DIR, exist_ok=True)
    
    raw_docs = load_documents(settings.DOCS_DIR)
    if not raw_docs:
        print("No documents found in data/docs. Initializing empty vector store.")
        return Chroma(
            collection_name=settings.COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=settings.CHROMA_DIR
        )
        
    chunks = split_documents(raw_docs)
    
    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=settings.COLLECTION_NAME,
        persist_directory=settings.CHROMA_DIR
    )
    return vector_store

def get_vector_store():
    """Get the existing Chroma vector store."""
    embeddings = get_embeddings()
    return Chroma(
        collection_name=settings.COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=settings.CHROMA_DIR
    )
