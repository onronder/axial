"""
Notion Connector

Connects to Notion API to fetch and sync pages and databases.
Updated to support Universal Connector Architecture (Sync Ingest).
"""

import logging
from typing import List, Optional, Dict, Any, Iterator, AsyncIterator
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, AuthenticationError
from .base import ConnectorItem
from core.db import get_supabase
from core.resilience import RATE_LIMIT_STATUS_CODES, with_retry_sync
import requests
from starlette.concurrency import run_in_threadpool
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)


class NotionConnector(EnhancedConnector):
    """
    Connector for Notion integration.
    Uses the unified ingestion interface for raw content delivery.
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.NOTION
    
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


    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for sync fetch."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Iterator[SourceDocument]:
        user_id = kwargs.get("user_id")
        if not item_ids:
            return iter(())

        # Resolve credentials (integration_id preferred; user_id fallback for API usage)
        if credentials and credentials.get("integration_id"):
            supabase = get_supabase()
            int_res = supabase.table("user_integrations").select("*").eq(
                "id", credentials["integration_id"]
            ).single().execute()
            if not int_res.data:
                raise AuthenticationError(f"Integration {credentials['integration_id']} not found")

            creds_data = OAuthTokenManager.get_valid_credentials(int_res.data, "notion")
            access_token = creds_data["access_token"]
        elif user_id:
            access_token = self._get_access_token(user_id)
        else:
            raise AuthenticationError("No credentials or user_id provided for Notion fetch")

        processed_ids = set()

        def ingest_page_recursive(page_id: str, depth: int = 0) -> Iterator[SourceDocument]:
            if page_id in processed_ids or depth > 10:
                return
            processed_ids.add(page_id)

            try:
                page = self._make_request("GET", f"pages/{page_id}", access_token)
                title = "Untitled"
                props = page.get("properties", {})
                for prop in props.values():
                    if prop.get("type") == "title" and prop.get("title"):
                        title = prop["title"][0].get("plain_text", "Untitled")
                        break

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
                        if block.get("type") == "child_page":
                            child_page_ids.append(block["id"])
                        elif block.get("type") == "child_database":
                            try:
                                db_pages = self._make_request(
                                    "POST",
                                    f"databases/{block['id']}/query",
                                    access_token,
                                    {"page_size": 100},
                                )
                                for db_page in db_pages.get("results", []):
                                    child_page_ids.append(db_page["id"])
                            except Exception as e:
                                logger.warning(
                                    "⚠️ [Notion] Failed to query database %s: %s",
                                    block["id"],
                                    e,
                                )

                    if not blocks_res.get("has_more"):
                        break
                    cursor = blocks_res.get("next_cursor")

                content = self._extract_text_from_blocks(all_blocks)
                if content.strip():
                    parent_id = (page.get("parent") or {}).get("page_id")
                    filename = f"{title}.md"
                    yield SourceDocument(
                        content=content,
                        metadata={
                            "source": "notion",
                            "title": title,
                            "page_id": page_id,
                            "source_url": page.get("url"),
                        },
                        source_type=SourceType.NOTION,
                        source_id=page_id,
                        filename=filename,
                        mime_type="text/markdown",
                        size_bytes=len(content.encode("utf-8")),
                        parent_id=parent_id,
                    )
                    logger.info(f"✅ [Notion] Fetched: {title}")

                for child_id in child_page_ids:
                    yield from ingest_page_recursive(child_id, depth + 1)

            except Exception as e:
                logger.error(f"❌ [Notion] Failed to fetch {page_id}: {e}")

        for page_id in item_ids:
            yield from ingest_page_recursive(page_id)

        logger.info("📥 [Notion] Completed fetch for %s initial item(s)", len(item_ids))
