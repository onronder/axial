from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from models import IngestResponse
from core.security import get_api_key
from core.db import get_supabase
from core.config import settings
from core.parsers import get_parser
import uuid
import datetime
import json
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    metadata: str = Form(...),
    api_key: str = Depends(get_api_key)
):
    supabase = get_supabase()
    
    # 0. Parse metadata JSON string
    try:
        meta_dict = json.loads(metadata)
    except Exception:
        meta_dict = {}

    # 1. Parse File Content (Universal Parser)
    try:
        parser = get_parser(file.filename)
        content = await parser.parse(file)
    except Exception as e:
        import traceback
        print(f"CRITICAL PARSING ERROR: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse file: {str(e)}"
        )

    if not content:
        return IngestResponse(status="skipped", doc_id="empty")

    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    docs = text_splitter.create_documents(
        texts=[content],
        metadatas=[{"filename": file.filename, **meta_dict}]
    )
    
    # 3. Embedding
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    chunk_texts = [d.page_content for d in docs]
    try:
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
    except Exception as e:
         raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate embeddings: {str(e)}"
        )
        
    records = []
    parent_doc_id = str(uuid.uuid4())
    
    for i, doc in enumerate(docs):
        records.append({
            "id": str(uuid.uuid4()),
            "client_id": meta_dict.get("client_id", "unknown"),
            "content": doc.page_content,
            "metadata": doc.metadata,
            "embedding": chunk_embeddings[i],
            "created_at": datetime.datetime.now().isoformat()
        })
        
    try:
        response = supabase.table("documents").insert(records).execute()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to insert into DB: {str(e)}"
        )

    return IngestResponse(status="queued", doc_id=parent_doc_id)