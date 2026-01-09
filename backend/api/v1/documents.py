from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.rate_limit import limiter
from core.ingestion_utils import normalize_provider
from services.audit import log_document_delete
from api.v1.dependencies import validate_team_access
from services.cleanup import cleanup_service
from services.team_service import team_service

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
    # Documents only exist after successful ingestion, so default to completed
    indexing_status: str = "completed"
    size: Optional[int] = 0
    metadata: Dict[str, Any]


class DocumentStatsDTO(BaseModel):
    """Lightweight stats response for efficient dashboard loading."""
    total_documents: int
    last_updated: Optional[str] = None


class DocumentUpdate(BaseModel):
    """Request model for updating document metadata."""
    title: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DocumentChunkDTO(BaseModel):
    """Response model for document chunks."""
    id: str
    document_id: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any] = {}


# =============================================================================
# Stats Endpoint (Optimized for Onboarding Check)
# =============================================================================

@router.get("/documents/stats", response_model=DocumentStatsDTO)
@limiter.limit("100/minute")
async def get_document_stats(
    request: Request,
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

from fastapi import Response

@router.get("/documents", response_model=List[DocumentDTO])
@limiter.limit("60/minute")
async def list_documents(
    request: Request,
    response: Response,
    user_id: str = Depends(validate_team_access),  # Validates team access
    limit: int = 50,
    offset: int = 0,
    q: Optional[str] = None,
    include_failed: bool = True  # New param to include failed files
):
    supabase = get_supabase()
    
    try:
        # Build query for completed documents
        query = supabase.table("documents")\
            .select("*", count="exact")\
            .eq("user_id", user_id)
            
        # Apply search filter
        if q and q.strip():
            query = query.ilike("title", f"%{q.strip()}%")
            
        # Execute with pagination
        db_res = query\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        # Set pagination header
        if db_res.count is not None:
             response.headers["X-Total-Count"] = str(db_res.count)
            
        # Enrich completed documents with status
        docs = []
        for d in db_res.data:
            d["source_type"] = normalize_provider(d.get("source_type")) or d.get("source_type")
            d['status'] = d.get('status', 'indexed')
            d['indexing_status'] = 'completed'
            # Fallback for size if not top-level
            if 'size' not in d or d['size'] is None:
                meta = d.get('metadata') or {}
                d['size'] = meta.get('size') or meta.get('file_size') or meta.get('file_size_bytes') or 0
                
            docs.append(d)
        
        # Also fetch failed files from ingestion_file_status (not yet in documents)
        if include_failed:
            try:
                failed_query = supabase.table("ingestion_file_status")\
                    .select("*")\
                    .eq("user_id", user_id)\
                    .eq("status", "failed")\
                    .is_("document_id", "null")
                
                if q and q.strip():
                    failed_query = failed_query.ilike("filename", f"%{q.strip()}%")
                
                failed_res = failed_query\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .execute()
                
                failed_files = failed_res.data or []
                provider_map = {}
                job_ids = {str(f.get("job_id")) for f in failed_files if f.get("job_id")}
                if job_ids:
                    jobs_res = supabase.table("ingestion_jobs")\
                        .select("id, provider")\
                        .in_("id", list(job_ids))\
                        .execute()
                    for job in jobs_res.data or []:
                        provider_map[str(job["id"])] = normalize_provider(job.get("provider")) or job.get("provider")

                # Convert failed files to DocumentDTO format
                for f in failed_files:
                    provider = provider_map.get(str(f.get("job_id"))) or "file_upload"
                    docs.append({
                        "id": f["id"],
                        "title": f["filename"],
                        "source_type": provider,
                        "source_url": None,
                        "created_at": f["created_at"],
                        "status": "failed",
                        "indexing_status": "failed",
                        "size": f.get("file_size_bytes", 0),
                        "metadata": {
                            "error": f.get("error_message", "Unknown error"),
                            "job_id": str(f.get("job_id", ""))
                        }
                    })
            except Exception as failed_err:
                # Don't fail entire request if failed files query fails
                import logging
                logging.warning(f"Failed to fetch failed files: {failed_err}")
        
        # Sort combined list by created_at
        docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.delete("/documents/{doc_id}")
@limiter.limit("30/minute")
async def delete_document(
    doc_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    supabase = get_supabase()
    
    try:
        # RBAC Check: Viewers cannot delete documents
        team = await team_service.get_user_team(user_id)
        if team and team.get("user_role") == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Viewers cannot delete documents."
            )

        # First, get document info for audit log
        doc_response = supabase.table("documents")\
            .select("title")\
            .eq("id", doc_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_title = doc_response.data.get("title", "Unknown")
        
        # Delete using cleanup service (Atomic: Vector -> Storage -> DB)
        await cleanup_service.delete_single_document(doc_id, user_id)
            

        
        # Audit log (async, non-blocking)
        log_document_delete(background_tasks, user_id, doc_id, doc_title, request)
        
        return {"status": "success", "id": doc_id}
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


# =============================================================================
# Document Update Endpoint
# =============================================================================

@router.patch("/documents/{document_id}", response_model=DocumentDTO)
@limiter.limit("30/minute")
async def update_document(
    document_id: str,
    update: DocumentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user)
):
    """
    Update document metadata (title, description, tags).
    
    Only the document owner or team members with editor/admin role can update.
    """
    from services.audit import audit_logger
    
    supabase = get_supabase()
    
    try:
        # RBAC Check: Viewers cannot update documents
        team = await team_service.get_user_team(user_id)
        if team and team.get("user_role") == "viewer":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Viewers cannot update documents."
            )
        
        # Check document exists and user owns it
        doc_response = supabase.table("documents")\
            .select("*")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_response.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        old_doc = doc_response.data
        
        # Build update payload
        update_data = {}
        if update.title is not None:
            update_data["title"] = update.title
        
        # Store description and tags in metadata
        if update.description is not None or update.tags is not None:
            existing_metadata = old_doc.get("metadata", {}) or {}
            if update.description is not None:
                existing_metadata["description"] = update.description
            if update.tags is not None:
                existing_metadata["tags"] = update.tags
            update_data["metadata"] = existing_metadata
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update fields provided")
        
        # Perform update
        result = supabase.table("documents")\
            .update(update_data)\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Update failed")
        
        updated_doc = result.data[0]
        updated_doc["source_type"] = normalize_provider(updated_doc.get("source_type")) or updated_doc.get("source_type")
        
        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="document.update",
            resource_type="document",
            resource_id=document_id,
            details={
                "title": updated_doc.get("title"),
                "changes": list(update_data.keys())
            },
            request=request
        )
        
        # Return updated document
        updated_doc['status'] = updated_doc.get('status', 'indexed')
        updated_doc['indexing_status'] = 'completed'
        if 'size' not in updated_doc or updated_doc['size'] is None:
            meta = updated_doc.get('metadata') or {}
            updated_doc['size'] = meta.get('size') or meta.get('file_size') or 0
        
        return updated_doc
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")


# =============================================================================
# Document Chunks Endpoint (for debugging/display)
# =============================================================================

@router.get("/documents/{document_id}/chunks", response_model=List[DocumentChunkDTO])
@limiter.limit("30/minute")
async def get_document_chunks(
    document_id: str,
    request: Request,
    user_id: str = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """
    Get all chunks for a document.
    
    Useful for debugging and displaying document content breakdown.
    """
    supabase = get_supabase()
    
    try:
        # Verify document exists and user owns it
        doc_check = supabase.table("documents")\
            .select("id")\
            .eq("id", document_id)\
            .eq("user_id", user_id)\
            .single()\
            .execute()
        
        if not doc_check.data:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Fetch chunks
        chunks_response = supabase.table("document_chunks")\
            .select("id, document_id, content, chunk_index, metadata")\
            .eq("document_id", document_id)\
            .order("chunk_index", desc=False)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return chunks_response.data or []
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch chunks: {str(e)}")
