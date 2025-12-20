"""
Notion Connector

Connects to Notion API to fetch and sync pages and databases.
"""

import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings
from core.resilience import with_retry_sync

logger = logging.getLogger(__name__)


class NotionConnector(BaseConnector):
    """
    Connector for Notion integration.
    
    Supports:
    - Listing pages and databases
    - Ingesting page content as plain text
    - Incremental sync using Notion's last_edited_time
    """
    
    NOTION_API_VERSION = "2022-06-28"
    BASE_URL = "https://api.notion.com/v1"
    
    async def authorize(self, user_id: str) -> bool:
        """Check if user has connected their Notion account."""
        supabase = get_supabase()
        res = supabase.table("user_integrations").select("id").eq(
            "user_id", user_id
        ).eq("provider", "notion").execute()
        return len(res.data) > 0
    
    def _get_access_token(self, user_id: str) -> str:
        """Get the Notion access token for a user."""
        supabase = get_supabase()
        res = supabase.table("user_integrations").select("access_token").eq(
            "user_id", user_id
        ).eq("provider", "notion").execute()
        
        if not res.data:
            raise ValueError("Notion not connected for this user.")
        
        return res.data[0]["access_token"]
    
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
        import requests
        
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
        List Notion pages and databases.
        
        If parent_id is None, searches all accessible pages.
        If parent_id is provided, lists children of that page/database.
        """
        access_token = self._get_access_token(user_id)
        items = []
        
        if parent_id:
            # Get children of a specific block/page
            result = self._make_request(
                "GET",
                f"blocks/{parent_id}/children",
                access_token
            )
            
            for block in result.get("results", []):
                if block["type"] in ["child_page", "child_database"]:
                    items.append(ConnectorItem(
                        id=block["id"],
                        name=block.get(block["type"], {}).get("title", "Untitled"),
                        type="folder" if block["type"] == "child_database" else "file",
                        mime_type="application/notion-page",
                        icon=None,
                        parent_id=parent_id
                    ))
        else:
            # Search all pages
            result = self._make_request(
                "POST",
                "search",
                access_token,
                {"page_size": 100}
            )
            
            for page in result.get("results", []):
                page_type = page.get("object", "page")
                
                # Extract title
                title = "Untitled"
                if page_type == "page":
                    props = page.get("properties", {})
                    if "title" in props:
                        title_prop = props["title"]
                        if title_prop.get("title"):
                            title = title_prop["title"][0].get("plain_text", "Untitled")
                    elif "Name" in props:
                        name_prop = props["Name"]
                        if name_prop.get("title"):
                            title = name_prop["title"][0].get("plain_text", "Untitled")
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
        """Extract plain text from Notion blocks."""
        text_parts = []
        
        for block in blocks:
            block_type = block.get("type")
            
            if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                             "bulleted_list_item", "numbered_list_item", "quote",
                             "callout", "toggle"]:
                rich_text = block.get(block_type, {}).get("rich_text", [])
                text = "".join([t.get("plain_text", "") for t in rich_text])
                
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
                
                if text:
                    text_parts.append(text)
            
            elif block_type == "code":
                code_text = block.get("code", {}).get("rich_text", [])
                code = "".join([t.get("plain_text", "") for t in code_text])
                lang = block.get("code", {}).get("language", "")
                text_parts.append(f"\n```{lang}\n{code}\n```\n")
            
            elif block_type == "divider":
                text_parts.append("\n---\n")
        
        return "\n".join(text_parts)
    
    async def ingest(
        self,
        user_id: str,
        item_ids: List[str]
    ) -> List[ConnectorDocument]:
        """Ingest Notion pages as documents."""
        access_token = self._get_access_token(user_id)
        documents = []
        
        for page_id in item_ids:
            try:
                # Get page metadata
                page = self._make_request("GET", f"pages/{page_id}", access_token)
                
                # Extract title
                title = "Untitled"
                props = page.get("properties", {})
                for prop_name, prop_value in props.items():
                    if prop_value.get("type") == "title":
                        title_arr = prop_value.get("title", [])
                        if title_arr:
                            title = title_arr[0].get("plain_text", "Untitled")
                        break
                
                # Get page content (blocks)
                all_blocks = []
                has_more = True
                start_cursor = None
                
                while has_more:
                    endpoint = f"blocks/{page_id}/children"
                    if start_cursor:
                        endpoint += f"?start_cursor={start_cursor}"
                    
                    blocks_result = self._make_request("GET", endpoint, access_token)
                    all_blocks.extend(blocks_result.get("results", []))
                    
                    has_more = blocks_result.get("has_more", False)
                    start_cursor = blocks_result.get("next_cursor")
                
                # Convert blocks to text
                content = self._extract_text_from_blocks(all_blocks)
                
                if content.strip():
                    documents.append(ConnectorDocument(
                        page_content=content,
                        metadata={
                            "source": "notion",
                            "title": title,
                            "page_id": page_id,
                            "source_url": page.get("url", ""),
                            "last_edited_time": page.get("last_edited_time", ""),
                            "created_time": page.get("created_time", "")
                        }
                    ))
                    logger.info(f"📄 [Notion] Ingested page: {title}")
                else:
                    logger.warning(f"📄 [Notion] Skipped empty page: {title}")
                    
            except Exception as e:
                logger.error(f"📄 [Notion] Failed to ingest page {page_id}: {e}")
                continue
        
        return documents
