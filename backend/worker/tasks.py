"""
Celery Worker Tasks

Background tasks for heavy file processing (ingestion, parsing, embedding).
These run in a separate worker process to avoid blocking the FastAPI server.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from core.celery_app import celery_app
from core.db import get_supabase
from core.config import settings
from core.security import decrypt_token
from services.parsers import DocumentParser

logger = logging.getLogger(__name__)


# ============================================================
# INGESTION TASK
# ============================================================

@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    acks_late=True
)
def ingest_file_task(
    self,
    user_id: str,
    provider: str,
    item_ids: List[str],
    credentials: Dict[str, Any]
):
    """
    Background task to ingest files from a provider.
    
    This runs in a separate Celery worker process, so it:
    - Doesn't block the FastAPI server
    - Handles large files without memory issues (prefetch=1)
    - Retries automatically on failure
    
    Args:
        user_id: The user's ID for multi-tenancy
        provider: Provider type (e.g., 'google_drive')
        item_ids: List of file IDs to ingest
        credentials: Encrypted OAuth credentials
    """
    task_id = self.request.id
    logger.info(f"📥 [Worker:{task_id}] Starting ingestion for user {user_id}")
    logger.info(f"📥 [Worker:{task_id}] Provider: {provider}, Items: {len(item_ids)}")
    
    supabase = get_supabase()
    
    try:
        # 1. Decrypt credentials
        decrypted_creds = {}
        for key, value in credentials.items():
            if isinstance(value, str):
                decrypted_creds[key] = decrypt_token(value)
            else:
                decrypted_creds[key] = value
        
        # 2. Get connector and ingest
        from connectors.factory import get_connector
        connector = get_connector(provider)
        
        # Pass credentials to connector for this ingestion
        # Note: Connector needs to support credential injection
        docs = connector.ingest_sync(user_id, item_ids, decrypted_creds)
        
        if not docs:
            logger.warning(f"📥 [Worker:{task_id}] No content processed")
            return {"status": "skipped", "message": "No content processed"}
        
        # 3. Embed documents
        from langchain_openai import OpenAIEmbeddings
        embeddings_model = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.OPENAI_API_KEY
        )
        
        chunk_texts = [d.page_content for d in docs]
        chunk_embeddings = embeddings_model.embed_documents(chunk_texts)
        
        logger.info(f"📥 [Worker:{task_id}] Embedded {len(chunk_texts)} chunks")
        
        # 4. Map provider to source_type enum
        CONNECTOR_TYPE_TO_ENUM = {
            "google_drive": "drive",
            "drive": "drive",
            "notion": "notion",
            "file_upload": "file",
            "file": "file",
            "web": "web",
        }
        source_type_enum = CONNECTOR_TYPE_TO_ENUM.get(provider, "file")
        
        # 5. Group by source and store
        from collections import defaultdict
        grouped = defaultdict(list)
        for i, doc in enumerate(docs):
            key = doc.metadata.get('source_url') or doc.metadata.get('file_id') or "unknown"
            grouped[key].append((doc, chunk_embeddings[i]))
        
        results = []
        
        for key, pairs in grouped.items():
            first_doc = pairs[0][0]
            
            # Create Parent Document
            parent_doc_data = {
                "user_id": user_id,
                "title": first_doc.metadata.get('title', 'Untitled'),
                "source_type": source_type_enum,
                "source_url": first_doc.metadata.get('source_url'),
                "metadata": first_doc.metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            logger.info(f"📄 [Worker:{task_id}] Creating document: {parent_doc_data['title']}")
            
            p_res = supabase.table("documents").insert(parent_doc_data).execute()
            if not p_res.data:
                continue
            parent_id = p_res.data[0]['id']
            
            # Create Chunks
            chunk_records = []
            for idx, (doc, emb) in enumerate(pairs):
                chunk_records.append({
                    "document_id": parent_id,
                    "content": doc.page_content,
                    "embedding": emb,
                    "chunk_index": idx,
                    "created_at": datetime.utcnow().isoformat()
                })
            
            supabase.table("document_chunks").insert(chunk_records).execute()
            results.append(parent_id)
        
        logger.info(f"✅ [Worker:{task_id}] Ingestion complete: {len(results)} documents")
        return {"status": "success", "ingested_ids": results, "task_id": task_id}
        
    except Exception as e:
        logger.error(f"❌ [Worker:{task_id}] Ingestion failed: {e}")
        
        # Update document status to FAILED if we have a reference
        # (This would require tracking document IDs during processing)
        
        # Re-raise for Celery retry mechanism
        raise


@celery_app.task(bind=True)
def health_check_task(self):
    """Simple task to verify worker is running."""
    return {"status": "healthy", "task_id": self.request.id}
