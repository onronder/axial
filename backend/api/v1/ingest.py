from fastapi import APIRouter, Depends, HTTPException, status
from models import IngestRequest, IngestResponse
from core.security import get_api_key
from core.db import get_supabase
from core.config import settings
import uuid
import datetime
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    payload: IngestRequest,
    api_key: str = Depends(get_api_key)
):
    supabase = get_supabase()
    
    # 1. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    # Create a LangChain Document to help with splitting if needed, or just split text
    # We want to preserve metadata for every chunk
    docs = text_splitter.create_documents(
        texts=[payload.content],
        metadatas=[{"filename": payload.filename, "client_id": payload.client_id, **(payload.metadata or {})}]
    )
    
    # 2. Embedding
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    # 3. Process and Upload Chunks
    # We'll batch this if it were huge, but for now a loop is fine or embedding multiple at once
    
    # Generate embeddings for all chunks at once for efficiency
    chunk_texts = [d.page_content for d in docs]
    try:
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}"
        )
        
    records = []
    parent_doc_id = str(uuid.uuid4()) # We might want a parent ID concept later, but for now just individual chunks
    
    for i, doc in enumerate(docs):
        records.append({
            "id": str(uuid.uuid4()),
            "client_id": payload.client_id,
            "content": doc.page_content,
            "metadata": doc.metadata,
            "embedding": chunk_embeddings[i],
            "created_at": datetime.datetime.now().isoformat()
        })
        
    try:
        # Insert into Supabase
        response = supabase.table("documents").insert(records).execute()
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document chunks: {str(e)}"
        )

    return IngestResponse(status="queued", doc_id=parent_doc_id)
