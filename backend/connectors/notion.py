"""
Notion Connector

Connects to Notion API to fetch and sync pages and databases.
Updated to support Universal Connector Architecture (Sync Ingest).
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.resilience import with_retry_sync
import requests

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
        """Check if user has connected their Notion account."""
        supabase = get_supabase()
        connector_def_id = self._get_connector_definition_id()
        res = supabase.table("user_integrations").select("id").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()
        return len(res.data) > 0
    
    def _get_access_token(self, user_id: str) -> str:
        """Get the Notion access token for a user (DB Lookup)."""
        from core.security import decrypt_token
        
        supabase = get_supabase()
        connector_def_id = self._get_connector_definition_id()
        res = supabase.table("user_integrations").select("access_token").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()
        
        if not res.data:
            raise ValueError("Notion not connected for this user.")
        
        encrypted_token = res.data[0]["access_token"]
        if encrypted_token:
            # Decrypt the token before use
            return decrypt_token(encrypted_token)
        raise ValueError("No access token found for Notion integration.")
    
    def _get_headers(self, access_token: str) -> Dict[str, str]:
        """Get headers for Notion API requests."""
        return {
            "Authorization": f"Bearer {access_token}",
            "Notion-Version": self.NOTION_API_VERSION,
            "Content-Type": "application/json"
        }
    
    @with_retry_sync(max_attempts=3)
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
        
        response.raise_for_status()
        return response.json()
    
    async def list_items(
        self,
        user_id: str,
        parent_id: Optional[str] = None
    ) -> List[ConnectorItem]:
        """
        List Notion pages with proper folder structure.
        
        - If parent_id is None or "root": Return TOP-LEVEL pages only (parent.type = "workspace")
        - If parent_id is a Page ID: Return child pages/databases of that page
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
        """Helper to convert blocks to markdown text."""
        text_parts = []
        for block in blocks:
            block_type = block.get("type")
            # Handle common text blocks
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

    def ingest(self, config: Dict[str, Any]) -> List[ConnectorDocument]:
        """
        Synchronous ingestion for Worker.
        Config keys: 'user_id', 'item_ids', 'credentials' (optional)
        
        Recursively ingests pages and their child pages.
        """
        user_id = config.get("user_id")
        item_ids = config.get("item_ids", [])
        credentials_data = config.get("credentials")
        
        # 1. Hybrid Credential Resolution
        if credentials_data and credentials_data.get("access_token"):
            # Worker case: Use passed token
            access_token = credentials_data["access_token"]
        elif user_id:
            # API case: Fallback to DB
            access_token = self._get_access_token(user_id)
        else:
            raise ValueError("No credentials or user_id provided for Notion ingestion")

        documents = []
        processed_ids = set()  # Prevent infinite loops from circular references
        
        def ingest_page_recursive(page_id: str, depth: int = 0):
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
                    documents.append(ConnectorDocument(
                        page_content=content,
                        metadata={
                            "source": "notion",
                            "title": title,
                            "page_id": page_id,
                            "source_url": page.get("url"),
                        }
                    ))
                    logger.info(f"✅ [Notion] Ingested: {title}")
                
                # Recursively process child pages
                for child_id in child_page_ids:
                    ingest_page_recursive(child_id, depth + 1)
                    
            except Exception as e:
                logger.error(f"❌ [Notion] Failed to ingest {page_id}: {e}")
        
        # Process all requested pages
        for page_id in item_ids:
            ingest_page_recursive(page_id)
                
        logger.info(f"📥 [Notion] Completed ingestion: {len(documents)} documents from {len(item_ids)} initial items")
        return documents

    async def sync(self, user_id: str, integration_id: str) -> dict:
        """
        Full sync operation: fetch ALL pages/databases and ingest them.
        
        Args:
            user_id: The user's ID
            integration_id: The user_integrations record ID (unused but required by interface)
            
        Returns:
            dict with sync statistics
        """
        logger.info(f"🔄 [NotionSync] Starting sync for user {user_id}")
        
        try:
            # 1. Fetch all accessible pages (using empty parent_id = recursive search)
            # Actually list_items only does one level, but ingest is recursive.
            # We want to start ingestion from ROOT pages.
            
            root_items = await self.list_items(user_id, parent_id="root")
            root_ids = [item.id for item in root_items]
            
            if not root_ids:
                logger.info("🔄 [NotionSync] No root pages found to sync")
                return {"status": "success", "files_processed": 0, "chunks_created": 0}
            
            logger.info(f"🔄 [NotionSync] Found {len(root_ids)} root items to sync")
            
            # 2. Re-use ingest method (synchronous)
            # Note: The worker already wraps this in async, so calling it directly is fine 
            # or we can wrap it if needed. ingest is sync, so we just call it.
            
            config = {
                "user_id": user_id,
                "item_ids": root_ids
            }
            
            # Ingest returns list of documents. We need to persist them using Embedding Service 
            # similar to DriveConnector.sync. 
            # Wait, `ingest` in NotionConnector returns `ConnectorDocument` objects but DOES NOT save to DB?
            # Checking `ingest` method... yes, it returns `documents`.
            # We need to implement the saving logic here or refactor `ingest` to save.
            # `DriveConnector.sync` implements saving logic completely separately from `ingest`.
            # Let's implement full sync logic here similar to DriveConnector.
            
            documents = self.ingest(config)
            
            if not documents:
                 return {"status": "success", "files_processed": 0, "chunks_created": 0}

            # 3. Chunk and Embed (using centralized service)
            from core.db import get_supabase
            from services.embeddings import generate_embeddings_batch
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            
            supabase = get_supabase()
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            total_chunks = 0
            processed_docs = 0
            errors = []
            
            for doc in documents:
                try:
                    # Insert Parent Document
                    parent_doc_data = {
                        "user_id": user_id,
                        "title": doc.metadata.get("title", "Untitled"),
                        "source_type": "notion",
                        "source_url": doc.metadata.get("source_url"),
                        "metadata": {
                            "page_id": doc.metadata.get("page_id"),
                            "source": "notion"
                        },
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    doc_res = supabase.table("documents").insert(parent_doc_data).execute()
                    if not doc_res.data:
                         continue
                    
                    parent_doc_id = doc_res.data[0]['id']
                    
                    # Chunk
                    chunks = text_splitter.split_text(doc.page_content)
                    if not chunks:
                        continue
                        
                    # Embed
                    embeddings = generate_embeddings_batch(chunks)
                    
                    # Insert Chunks
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
                        supabase.table("document_chunks").insert(chunk_records).execute()
                        total_chunks += len(chunk_records)
                        processed_docs += 1
                        
                except Exception as e:
                    logger.error(f"❌ [NotionSync] Error saving {doc.metadata.get('title')}: {e}")
                    errors.append(str(e))
            
            # 4. Update Integration Status
            supabase.table("user_integrations").update({
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", integration_id).execute()
            
            return {
                "status": "success",
                "files_processed": processed_docs,
                "chunks_created": total_chunks,
                "errors": errors
            }

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error(f"❌ [NotionSync] Authentication failed: {e}")
                # We can't update status='error' due to schema, but we raise specific message
                raise Exception("Integration requires reconnection (Token Expired/Revoked)") from e
            logger.error(f"❌ [NotionSync] HTTP Error: {e}")
            raise e
        except Exception as e:
            logger.error(f"❌ [NotionSync] Sync failed: {e}")
            raise e

