"""
Notion Connector

Connects to Notion API to fetch and sync pages and databases.
Updated to support Universal Connector Architecture (Sync Ingest).
"""

import logging
from typing import List, Optional, Dict, Any, Iterator, AsyncIterator
from datetime import datetime, timezone
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings
from core.db_utils import delete_rows_with_retry, insert_rows_with_retry
from core.hashing import compute_content_hash
from core.resilience import RATE_LIMIT_STATUS_CODES, with_retry_sync
import requests
from starlette.concurrency import run_in_threadpool
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """
    Connector for Notion integration.
    Updated to support Universal Connector Architecture (Sync Ingest).
    """
    
    NOTION_API_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"
    
    def _get_connector_definition_id(self) -> str:
        """Get the connector_definition_id for notion from the database."""
        supabase = get_supabase()
        res = supabase.table("connector_definitions").select("id").eq(
            "type", "notion"
        ).single().execute()
        if not res.data:
            raise ValueError("Notion connector definition not found in database")
        return res.data["id"]
    
    async def authorize(self, user_id: str) -> bool:
        """Async wrapper for authorization check."""
        return await run_in_threadpool(self._authorize_implementation, user_id)

    def _authorize_implementation(self, user_id: str) -> bool:
        """Synchronous implementation of authorize."""
        supabase = get_supabase()
        connector_def_id = self._get_connector_definition_id()
        res = supabase.table("user_integrations").select("id").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()
        return len(res.data) > 0
    
    def _get_access_token(self, user_id: str) -> str:
        """Get the Notion access token for a user with automatic refresh."""
        supabase = get_supabase()
        connector_def_id = self._get_connector_definition_id()
        
        res = supabase.table("user_integrations").select("*").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()
        
        if not res.data:
            raise ValueError("Notion not connected for this user.")
        
        try:
            # Use centralized token manager
            creds_data = OAuthTokenManager.get_valid_credentials(
                res.data[0],
                'notion'
            )
            return creds_data['access_token']
        
        except TokenRefreshError as e:
            raise ValueError("Integration requires reconnection") from e
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get headers for Notion API requests."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": self.NOTION_API_VERSION,
            "Content-Type": "application/json"
        }
    
    @with_retry_sync(max_attempts=3, min_wait=1, max_wait=10, use_retryable=True, jitter=True)
    def _make_request(
        self,
        method: str,
        endpoint: str,
        access_token: str,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make a request to the Notion API with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        headers = self._get_headers(access_token)
        
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=json_data,
            timeout=30
        )

        if response.status_code in RATE_LIMIT_STATUS_CODES:
            logger.warning(f"⚠️ [Notion] Rate limit response {response.status_code} for {endpoint}")
            if response.status_code == 429:
                try:
                    from core.metrics import retry_total
                    retry_total.labels("notion", "rate_limit").inc()
                except Exception:
                    pass

        response.raise_for_status()
        return response.json()
    


    async def list_items(
        self,
        user_id: str,
        parent_id: Optional[str] = None
    ) -> List[ConnectorItem]:
        """Async wrapper for listing items."""
        return await run_in_threadpool(self._list_items_implementation, user_id, parent_id)

    def _list_items_implementation(
        self,
        user_id: str,
        parent_id: Optional[str] = None
    ) -> List[ConnectorItem]:
        """
        List Notion pages with proper folder structure (Synchronous).
        """
        access_token = self._get_access_token(user_id)
        items = []
        
        # Handle "root" string as None
        if parent_id == "root":
            parent_id = None
        
        if parent_id:
            # Get children of a specific page
            try:
                result = self._make_request("GET", f"blocks/{parent_id}/children", access_token)
                for block in result.get("results", []):
                    block_type = block.get("type")
                    
                    # Only include child pages and databases
                    if block_type == "child_page":
                        title = block.get("child_page", {}).get("title", "Untitled")
                        items.append(ConnectorItem(
                            id=block["id"],
                            name=title,
                            type="folder",  # Pages can contain sub-pages, so treat as folder
                            mime_type="application/vnd.notion.page",
                            parent_id=parent_id
                        ))
                    elif block_type == "child_database":
                        title = block.get("child_database", {}).get("title", "Untitled Database")
                        items.append(ConnectorItem(
                            id=block["id"],
                            name=title,
                            type="folder",
                            mime_type="application/vnd.notion.database",
                            parent_id=parent_id
                        ))
            except Exception as e:
                logger.error(f"Failed to get children for {parent_id}: {e}")
        else:
            # Get TOP-LEVEL pages only (no parent or parent is workspace)
            result = self._make_request("POST", "search", access_token, {
                "page_size": 100,
                "filter": {"property": "object", "value": "page"}
            })
            
            for page in result.get("results", []):
                # Check if this is a top-level page (parent type is workspace)
                parent_info = page.get("parent", {})
                parent_type = parent_info.get("type")
                
                # Only include pages that are directly in the workspace (top-level)
                if parent_type != "workspace":
                    continue
                
                # Extract title
                title = "Untitled"
                props = page.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title" and prop.get("title"):
                        title_arr = prop.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "Untitled")
                        break
                
                # Get icon emoji if available
                icon = None
                icon_data = page.get("icon")
                if icon_data and icon_data.get("type") == "emoji":
                    icon = icon_data.get("emoji")
                
                items.append(ConnectorItem(
                    id=page["id"],
                    name=title,
                    type="folder",  # All pages can have children, so treat as folders
                    mime_type="application/vnd.notion.page",
                    icon=icon,
                    parent_id=None
                ))
            
            # Also get top-level databases
            db_result = self._make_request("POST", "search", access_token, {
                "page_size": 100,
                "filter": {"property": "object", "value": "database"}
            })
            
            for db in db_result.get("results", []):
                parent_info = db.get("parent", {})
                parent_type = parent_info.get("type")
                
                if parent_type != "workspace":
                    continue
                
                title = "Untitled Database"
                title_arr = db.get("title", [])
                if title_arr:
                    title = title_arr[0].get("plain_text", "Untitled Database")
                
                icon = None
                icon_data = db.get("icon")
                if icon_data and icon_data.get("type") == "emoji":
                    icon = icon_data.get("emoji")
                
                items.append(ConnectorItem(
                    id=db["id"],
                    name=title,
                    type="folder",
                    mime_type="application/vnd.notion.database",
                    icon=icon,
                    parent_id=None
                ))
        
        logger.info(f"📄 [Notion] list_items(parent={parent_id}): Found {len(items)} items")
        return items


    def _extract_text_from_blocks(self, blocks: List[Dict]) -> str:
        # ... existing helper ...
        text_parts = []
        for block in blocks:
            block_type = block.get("type")
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                             "bulleted_list_item", "numbered_list_item", "quote", "callout", "toggle"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                if text:
                    if block_type == "heading_1":
                        text = f"\n# {text}\n"
                    elif block_type == "heading_2":
                        text = f"\n## {text}\n"
                    elif block_type == "heading_3":
                        text = f"\n### {text}\n"
                    elif block_type in ["bulleted_list_item", "numbered_list_item"]:
                        text = f"• {text}"
                    elif block_type == "quote":
                        text = f"> {text}"
                    text_parts.append(text)
            elif block_type == "code":
                code = "".join([t.get("plain_text", "") for t in block.get("code", {}).get("rich_text", [])])
                lang = block.get("code", {}).get("language", "")
                text_parts.append(f"\n```{lang}\n{code}\n```\n")
            elif block_type == "divider":
                text_parts.append("\n---\n")
        
        return "\n".join(text_parts)


    async def ingest(self, config: Dict[str, Any]) -> "AsyncIterator[ConnectorDocument]":
        """Async wrapper for ingestion (Streaming)."""
        from starlette.concurrency import iterate_in_threadpool
        return iterate_in_threadpool(self._ingest_implementation(config))

    def _ingest_implementation(self, config: Dict[str, Any]) -> "Iterator[ConnectorDocument]":
        """
        Synchronous ingestion for Worker (Generator).
        """
        user_id = config.get("user_id")
        item_ids = config.get("item_ids", [])
        credentials_data = config.get("credentials")
        
        # 1. Hybrid Credential Resolution with Token Refresh
        if credentials_data and credentials_data.get('integration_id'):
            # Worker case: Fetch integration and refresh token if needed
            supabase = get_supabase()
            int_res = supabase.table("user_integrations").select("*").eq(
                "id", credentials_data['integration_id']
            ).single().execute()
            
            if not int_res.data:
                raise ValueError(f"Integration {credentials_data['integration_id']} not found")
            
            # Use token manager for automatic refresh
            creds_data = OAuthTokenManager.get_valid_credentials(
                int_res.data,
                'notion'
            )
            access_token = creds_data['access_token']
        elif credentials_data and credentials_data.get("access_token"):
            # Legacy: Use passed token (fallback)
            access_token = credentials_data["access_token"]
        elif user_id:
            # API case: Fallback to DB lookup (already has refresh)
            access_token = self._get_access_token(user_id)
        else:
            raise ValueError("No credentials or user_id provided for Notion ingestion")

        processed_ids = set()  # Prevent infinite loops from circular references
        
        def ingest_page_recursive(page_id: str, depth: int = 0) -> "Iterator[ConnectorDocument]":
            """Recursively ingest a page and its children."""
            if page_id in processed_ids or depth > 10:  # Max depth to prevent runaway recursion
                return
            processed_ids.add(page_id)
            
            try:
                # Get Page Title
                page = self._make_request("GET", f"pages/{page_id}", access_token)
                title = "Untitled"
                # Extract title logic
                props = page.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title" and prop.get("title"):
                        title = prop["title"][0].get("plain_text", "Untitled")
                        break

                # Get Blocks (Content) - Paginated fetch
                all_blocks = []
                child_page_ids = []
                cursor = None
                
                while True:
                    endpoint = f"blocks/{page_id}/children"
                    if cursor:
                        endpoint += f"?start_cursor={cursor}"
                    
                    blocks_res = self._make_request("GET", endpoint, access_token)
                    
                    for block in blocks_res.get("results", []):
                        all_blocks.append(block)
                        # Collect child page IDs for recursive processing
                        if block.get("type") == "child_page":
                            child_page_ids.append(block["id"])
                        elif block.get("type") == "child_database":
                            # For databases, fetch all pages inside
                            try:
                                db_pages = self._make_request("POST", f"databases/{block['id']}/query", access_token, {"page_size": 100})
                                for db_page in db_pages.get("results", []):
                                    child_page_ids.append(db_page["id"])
                            except Exception as e:
                                logger.warning(f"⚠️ [Notion] Failed to query database {block['id']}: {e}")
                    
                    if not blocks_res.get("has_more"):
                        break
                    cursor = blocks_res.get("next_cursor")
                
                content = self._extract_text_from_blocks(all_blocks)
                
                if content.strip():
                    doc = ConnectorDocument(
                        page_content=content,
                        metadata={
                            "source": "notion",
                            "title": title,
                            "page_id": page_id,
                            "source_url": page.get("url"),
                        }
                    )
                    logger.info(f"✅ [Notion] Ingested: {title}")
                    yield doc
                
                # Recursively process child pages
                for child_id in child_page_ids:
                    yield from ingest_page_recursive(child_id, depth + 1)
                    
            except Exception as e:
                logger.error(f"❌ [Notion] Failed to ingest {page_id}: {e}")
        
        # Process all requested pages
        for page_id in item_ids:
            yield from ingest_page_recursive(page_id)
                
        logger.info(f"📥 [Notion] Completed ingestion stream for {len(item_ids)} initial items")

    async def sync(self, user_id: str, integration_id: str) -> dict:
        """Async wrapper for sync."""
        return await run_in_threadpool(self._sync_implementation, user_id, integration_id)

    def _sync_implementation(self, user_id: str, integration_id: str) -> dict:
        """
        Full sync operation: fetch ALL pages/databases and ingest them.
        """
        logger.info(f"🔄 [NotionSync] Starting sync for user {user_id}")
        
        try:
            # 1. Fetch all accessible pages (using empty parent_id = recursive search)
            # Use the synchronous implementation!
            root_items = self._list_items_implementation(user_id, parent_id="root")
            root_ids = [item.id for item in root_items]
            
            if not root_ids:
                logger.info("🔄 [NotionSync] No root pages found to sync")
                return {"status": "success", "files_processed": 0, "chunks_created": 0}
            
            logger.info(f"🔄 [NotionSync] Found {len(root_ids)} root items to sync")
            
            # 2. Ingest synchronously
            config = {
                "user_id": user_id,
                "item_ids": root_ids
            }
            
            documents = self._ingest_implementation(config)
            
            if not documents:
                 return {"status": "success", "files_processed": 0, "chunks_created": 0}

            # 3. Chunk and Embed (using centralized service)
            from core.db import get_supabase
            from services.embeddings import generate_embeddings_batch_sync
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            from worker.tasks import create_file_status, update_file_status
            
            supabase = get_supabase()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            # Create ingestion job for progress tracking
            job_id = None
            if documents:
                job_result = supabase.table("ingestion_jobs").insert({
                    "user_id": user_id,
                    "provider": "notion",
                    "total_files": len(documents),
                    "processed_files": 0,
                    "status": "processing",
                    "message": f"Syncing {len(documents)} pages from Notion",
                    "status_message": f"Syncing {len(documents)} pages from Notion"
                }).execute()
                if job_result.data:
                    job_id = job_result.data[0]["id"]
                    logger.info(f"🔄 [NotionSync] Created job {job_id} for tracking")
            
            total_chunks = 0
            processed_docs = 0
            errors = []
            
            for doc in documents:
                doc_title = doc.metadata.get("title", "Untitled")
                file_status_id = None
                
                # Create file status record for tracking
                if job_id:
                    file_status_id = create_file_status(supabase, job_id, user_id, doc_title, 
                        len(doc.page_content.encode('utf-8')))
                
                try:
                    # Status: Processing
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="parsing", progress=20, message="Extracting content...")
                    
                    # Insert Parent Document
                    content_bytes = doc.page_content.encode("utf-8", errors="ignore")
                    if len(content_bytes) > settings.MAX_FILE_SIZE:
                        if file_status_id:
                            update_file_status(
                                supabase,
                                file_status_id,
                                status="failed",
                                progress=0,
                                message=f"File exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
                                error="File too large",
                            )
                        continue
                    content_hash = compute_content_hash(content_bytes)
                    parent_doc_data = {
                        "user_id": user_id,
                        "title": doc_title,
                        "source_type": "notion",
                        "source_url": doc.metadata.get("source_url"),
                        "file_size_bytes": len(content_bytes),
                        "content_hash": content_hash,
                        "metadata": {
                            "page_id": doc.metadata.get("page_id"),
                            "source": "notion"
                        },
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }

                    existing_doc_id = None
                    if content_hash:
                        existing = supabase.table("documents").select("id").eq("user_id", user_id).eq(
                            "title", doc_title
                        ).eq("content_hash", content_hash).limit(1).execute()
                        if existing.data:
                            existing_doc_id = existing.data[0]["id"]

                    if existing_doc_id:
                        delete_rows_with_retry(
                            supabase,
                            "document_chunks",
                            "document_id",
                            existing_doc_id,
                            context=f"notion_sync replace doc_id={existing_doc_id}",
                        )
                        update_data = {**parent_doc_data, "updated_at": datetime.now(timezone.utc).isoformat()}
                        update_data.pop("created_at", None)
                        supabase.table("documents").update(update_data).eq("id", existing_doc_id).execute()
                        parent_doc_id = existing_doc_id
                    else:
                        doc_res = supabase.table("documents").insert(parent_doc_data).execute()
                        if not doc_res.data:
                            if file_status_id:
                                update_file_status(supabase, file_status_id,
                                    status="failed", progress=0, error="Failed to create document")
                            continue
                        parent_doc_id = doc_res.data[0]['id']
                    
                    # Chunk
                    chunks = text_splitter.split_text(doc.page_content)
                    if not chunks:
                        if file_status_id:
                            update_file_status(supabase, file_status_id,
                                status="skipped", progress=100, message="No content")
                        continue
                    
                    # Status: Embedding
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="embedding", progress=50, message=f"Embedding {len(chunks)} chunks...",
                            chunks_total=len(chunks))
                        
                    # Embed
                    embeddings = generate_embeddings_batch_sync(chunks)
                    
                    # Status: Indexing
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="indexing", progress=75, message="Saving to database...")
                    
                    # Insert Chunks in batches to prevent DB timeout
                    DB_BATCH_SIZE = max(1, min(settings.CHUNK_INSERT_BATCH_SIZE, 200))
                    chunk_records = []
                    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                        if embedding is None:
                            continue
                        chunk_records.append({
                            "document_id": parent_doc_id,
                            "content": chunk_text,
                            "embedding": embedding,
                            "chunk_index": i
                        })
                    
                    if chunk_records:
                        inserted_count = 0
                        for batch_start in range(0, len(chunk_records), DB_BATCH_SIZE):
                            batch = chunk_records[batch_start:batch_start + DB_BATCH_SIZE]
                            try:
                                insert_rows_with_retry(
                                    supabase,
                                    "document_chunks",
                                    batch,
                                    context=f"notion_sync doc={doc.get('id', 'unknown')} batch={batch_start // DB_BATCH_SIZE + 1}",
                                )
                                inserted_count += len(batch)
                            except Exception as batch_err:
                                logger.error(f"❌ [NotionSync] Batch insert failed: {batch_err}")
                                continue
                        
                        if inserted_count > 0:
                            total_chunks += inserted_count
                            processed_docs += 1
                            
                            # Status: Completed
                            if file_status_id:
                                update_file_status(supabase, file_status_id,
                                    status="completed", progress=100, message="Complete",
                                    chunks_processed=inserted_count, document_id=str(parent_doc_id))
                            
                            # Update job progress
                            if job_id:
                                supabase.table("ingestion_jobs").update({
                                    "processed_files": processed_docs,
                                    "message": f"Processed {processed_docs}/{len(documents)} pages",
                                    "status_message": f"Processed {processed_docs}/{len(documents)} pages"
                                }).eq("id", job_id).execute()
                        else:
                            if file_status_id:
                                update_file_status(supabase, file_status_id,
                                    status="failed", progress=0, error="No chunks inserted")
                        
                except Exception as e:
                    logger.error(f"❌ [NotionSync] Error saving {doc_title}: {e}")
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="failed", progress=0, error=str(e))
                    errors.append(str(e))
            
            # 4. Update job to completed
            if job_id:
                final_status = "completed" if processed_docs > 0 else "failed"
                supabase.table("ingestion_jobs").update({
                    "status": final_status,
                    "processed_files": processed_docs,
                    "progress": 100,
                    "message": f"Synced {processed_docs} pages, {total_chunks} chunks",
                    "status_message": f"Synced {processed_docs} pages, {total_chunks} chunks"
                }).eq("id", job_id).execute()
            
            # 5. Update Integration Status
            supabase.table("user_integrations").update({
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", integration_id).execute()
            
            return {
                "status": "success",
                "files_processed": processed_docs,
                "chunks_created": total_chunks,
                "errors": errors,
                "job_id": job_id
            }

        except requests.exceptions.HTTPError as e:
            # ... existing error handling ...
            if e.response.status_code == 401:
                logger.error(f"❌ [NotionSync] Authentication failed: {e}")
                raise Exception("Integration requires reconnection (Token Expired/Revoked)") from e
            logger.error(f"❌ [NotionSync] HTTP Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ [NotionSync] Sync failed: {e}")
            # Mark job as failed if exists
            if 'job_id' in locals() and job_id:
                supabase.table("ingestion_jobs").update({
                    "status": "failed",
                    "error_message": str(e)
                }).eq("id", job_id).execute()
            raise e
