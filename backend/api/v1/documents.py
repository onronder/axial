from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class DocumentDTO(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: Optional[str] = None
    created_at: str
    status: str = "indexed"
    metadata: Dict[str, Any]


class DocumentStatsDTO(BaseModel):
    """Lightweight stats response for efficient dashboard loading."""
    total_documents: int
    last_updated: Optional[str] = None


# =============================================================================
# Stats Endpoint (Optimized for Onboarding Check)
# =============================================================================

@router.get("/documents/stats", response_model=DocumentStatsDTO)
async def get_document_stats(
    user_id: str = Depends(get_current_user)
):
    """
    Get lightweight document statistics for the current user.
    
    Uses efficient count query - O(1) performance instead of O(n) data transfer.
    Used by frontend to check if user needs onboarding.
    """
    supabase = get_supabase()
    
    try:
        # Use count query - only fetches count, not actual data
        count_response = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .execute()
        
        total = count_response.count if count_response.count is not None else 0
        
        # Get last updated (most recent document)
        last_updated = None
        if total > 0:
            latest_response = supabase.table("documents")\
                .select("created_at")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(1)\
                .execute()
            
            if latest_response.data:
                last_updated = latest_response.data[0].get("created_at")
        
        return DocumentStatsDTO(
            total_documents=total,
            last_updated=last_updated
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")



# =============================================================================
# Document CRUD Endpoints
# =============================================================================

@router.get("/documents", response_model=List[DocumentDTO])
async def list_documents(
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    supabase = get_supabase()
    
    try:
        # Fetch documents for user
        # Note: Order by created_at desc
        response = supabase.table("documents")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        # Enrich with status if not present in DB
        docs = []
        for d in response.data:
            d['status'] = d.get('status', 'indexed')
            docs.append(d)
            
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    try:
        # Verify ownership / delete
        # Postgres RLS should handle ownership, but explicit check is good practice
        # Delete parent. Cascade in DB handles chunks.
        response = supabase.table("documents")\
            .delete()\
            .eq("id", doc_id)\
            .eq("user_id", user_id)\
            .execute()
            
        # Supabase returns the deleted record if successful
        if not response.data:
             raise HTTPException(status_code=404, detail="Document not found or access denied")
             
        return {"status": "success", "id": doc_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
