from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase

router = APIRouter()

class DocumentDTO(BaseModel):
    id: str
    title: str
    source_type: str
    source_url: Optional[str] = None
    created_at: str
    metadata: Dict[str, Any]

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
            
        return response.data
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
