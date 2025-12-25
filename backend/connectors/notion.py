"""
Notion Connector

Connects to Notion API to fetch and sync pages and databases.
Updated to support Universal Connector Architecture (Sync Ingest).
"""

import logging
from typing import List, Optional, Dict, Any
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
        """List Notion pages (Async for UI)."""
        # Note: list_items is typically called from API, so DB lookup is acceptable here.
        access_token = self._get_access_token(user_id)
        items = []
        
        if parent_id:
            # Get children
            result = self._make_request("GET", f"blocks/{parent_id}/children", access_token)
            for block in result.get("results", []):
                if block["type"] in ["child_page", "child_database"]:
                    items.append(ConnectorItem(
                        id=block["id"],
                        name=block.get(block["type"], {}).get("title", "Untitled"),
                        type="folder" if block["type"] == "child_database" else "file",
                        mime_type="application/notion-page",
                        parent_id=parent_id
                    ))
        else:
            # Search all
            result = self._make_request("POST", "search", access_token, {"page_size": 100})
            for page in result.get("results", []):
                page_type = page.get("object", "page")
                title = "Untitled"
                # Try generic title extraction
                if page_type == "page":
                    props = page.get("properties", {})
                    for prop in props.values():
                        if prop.get("type") == "title" and prop.get("title"):
                            title = prop["title"][0].get("plain_text", "Untitled")
                            break
                elif page_type == "database":
                    title_arr = page.get("title", [])
                    if title_arr:
                        title = title_arr[0].get("plain_text", "Untitled")
                
                items.append(ConnectorItem(
                    id=page["id"],
                    name=title,
                    type="folder" if page_type == "database" else "file",
                    mime_type=f"application/notion-{page_type}",
                    icon=page.get("icon", {}).get("emoji"),
                    parent_id=page.get("parent", {}).get("page_id")
                ))
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
        
        for page_id in item_ids:
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
                cursor = None
                while True:
                    endpoint = f"blocks/{page_id}/children"
                    if cursor:
                        endpoint += f"?start_cursor={cursor}"
                    
                    blocks_res = self._make_request("GET", endpoint, access_token)
                    all_blocks.extend(blocks_res.get("results", []))
                    
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
                    
            except Exception as e:
                logger.error(f"❌ [Notion] Failed to ingest {page_id}: {e}")
                continue
                
        return documents
