from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.security import get_api_key
from core.db import get_supabase
from core.config import settings
from langchain_openai import OpenAIEmbeddings

router = APIRouter()

class SearchRequest(BaseModel):
    query: str
    limit: int = 5
    threshold: float = 0.2

class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]

@router.post("/search", response_model=SearchResponse)
async def search_documents(
    payload: SearchRequest,
    api_key: str = Depends(get_api_key)
):
    supabase = get_supabase()
    
    # 1. Embed Query
    embeddings_model = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )
    
    try:
        query_vector = embeddings_model.embed_query(payload.query)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate query embedding: {str(e)}"
        )
        
    # 2. Execute Vector Search RPC
    try:
        response = supabase.rpc("match_documents", {
            "query_embedding": query_vector,
            "match_threshold": payload.threshold,
            "match_count": payload.limit
        }).execute()
        
        # response.data contains the list of documents
        matches = response.data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(e)}"
        )
        
    return SearchResponse(results=matches)
