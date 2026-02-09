"""
Microsoft Graph Connector

Unified connector for OneDrive and SharePoint via Microsoft Graph API.
Supports OAuth token refresh, delta sync, and streaming downloads.
"""

from __future__ import annotations

import io
import logging
import time
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from typing import Any

import requests
from starlette.concurrency import run_in_threadpool

from connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorRateLimitError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import (
    EnhancedConnector,
    ItemNotFoundError,
    SourceDocument,
    SourceType,
)
from connectors.limits import connector_fetch_limit
from connectors.utils import load_integration
from core.scopes import build_scope_uri
from core.sync import SyncManager
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_RETRIES = 3


class MicrosoftGraphConnector(EnhancedConnector, BaseConnector):
    """
    Unified Microsoft Graph connector.

    target_type: "onedrive" or "sharepoint"
    """

    def __init__(self, target_type: str = "onedrive") -> None:
        self.target_type = target_type

    @property
    def connector_type(self) -> SourceType:
        if self.target_type == "sharepoint":
            return SourceType.SHAREPOINT
        return SourceType.ONEDRIVE

    def validate_config(self, config: dict) -> bool:
        if not isinstance(config, dict):
            return False

        target_type = (config.get("target_type") or self.target_type or "").strip().lower()
        if target_type not in {"onedrive", "sharepoint"}:
            return False

        access_token = config.get("access_token")
        integration_id = config.get("integration_id")
        user_id = config.get("user_id")
        return not (not access_token and not integration_id and not user_id)

    async def list_files(
        self, config: dict[str, Any], since: datetime | None = None
    ) -> list[RemoteFile]:
        return await run_in_threadpool(self._list_files_sync, config, since)

    def iter_files_sync(self, config: dict[str, Any], since: datetime | None = None) -> Iterator[RemoteFile]:
        resolved = self._resolve_config(config)
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid Microsoft Graph configuration")

        drive_id, site_id = self._resolve_drive_id(resolved)
        resolved.setdefault("drive_id", drive_id)
        if site_id:
            resolved.setdefault("site_id", site_id)

        parent_id = resolved.get("parent_id")

        if parent_id is None:
            yield from self._list_recursive_items(resolved, since)
            return

        yield from self._list_children_items(resolved, parent_id)

    def _list_files_sync(self, config: dict[str, Any], since: datetime | None = None) -> list[RemoteFile]:
        return list(self.iter_files_sync(config, since))

    def fetch_file_content(self, file_id: str, config: dict) -> bytes:
        resolved = self._resolve_config(config)
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid Microsoft Graph configuration")

        drive_id, _site_id = self._resolve_drive_id(resolved)
        resolved.setdefault("drive_id", drive_id)

        item = self._get_item(resolved, file_id)
        if item.get("folder"):
            raise ItemNotFoundError(f"Graph item is a folder: {file_id}")

        return self._download_content(resolved, file_id)

    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> AsyncIterator[SourceDocument]:
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs,
    ) -> Iterator[SourceDocument]:
        """
        Fetch documents from OneDrive/SharePoint for ingestion pipeline.

        Scope ID Format: onedrive://{drive_id}/{item_id} or sharepoint://{drive_id}/{item_id}
        """
        if not item_ids:
            return iter(())

        resolved = self._resolve_config(credentials or {})
        if not self.validate_config(resolved):
            raise ConnectorAuthError("Invalid Microsoft Graph configuration")

        drive_id, site_id = self._resolve_drive_id(resolved)
        resolved.setdefault("drive_id", drive_id)
        if site_id:
            resolved.setdefault("site_id", site_id)

        target_type = resolved.get("target_type", self.target_type)

        for item_id in item_ids:
            # Generate scope_id using canonical URI builder
            scope_id = build_scope_uri(target_type, {"drive_id": drive_id, "item_id": item_id})

            if item_id in (None, "root"):
                yield from self._walk_folder(resolved, "root", scope_id)
                continue

            item = self._get_item(resolved, item_id)
            if item.get("folder"):
                yield from self._walk_folder(resolved, item_id, scope_id)
            else:
                yield self._build_source_document(resolved, item, scope_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_config(self, config: dict) -> dict:
        resolved = dict(config or {})
        resolved.setdefault("target_type", self.target_type)

        if resolved.get("access_token"):
            return resolved

        integration = self._load_integration(resolved)

        # Check if integration needs reconnection
        if integration.get("status") == "reconnection_required":
            raise ConnectorAuthError(
                integration.get("status_message", "Please reconnect your Microsoft account.")
            )

        try:
            creds = OAuthTokenManager.get_valid_credentials(integration, resolved["target_type"])
        except TokenRefreshError as exc:
            raise ConnectorAuthError("Microsoft integration requires reconnection") from exc
        resolved["access_token"] = creds.get("access_token")
        resolved["refresh_token"] = creds.get("refresh_token")
        resolved["expires_at"] = creds.get("expires_at")
        resolved["integration_id"] = creds.get("integration_id") or integration.get("id")

        if not resolved.get("access_token"):
            raise ConnectorAuthError("Microsoft access token missing")

        credentials = integration.get("credentials") or {}
        if credentials.get("drive_id"):
            resolved.setdefault("drive_id", credentials["drive_id"])
        if credentials.get("site_id"):
            resolved.setdefault("site_id", credentials["site_id"])

        return resolved

    def _load_integration(self, config: dict) -> dict[str, Any]:
        """Load integration record from database using shared utility."""
        # Microsoft uses dynamic target_type (onedrive or sharepoint)
        connector_type = config.get("target_type", self.target_type)
        return load_integration(
            connector_type,
            integration_id=config.get("integration_id"),
            user_id=config.get("user_id"),
        )

    def _resolve_drive_id(self, config: dict) -> tuple[str, str | None]:
        drive_id = config.get("drive_id")
        site_id = config.get("site_id")
        if drive_id:
            return drive_id, site_id

        if config.get("target_type") == "onedrive":
            data = self._get_json(config, f"{GRAPH_BASE_URL}/me/drive")
            drive_id = data.get("id")
            if not drive_id:
                raise ConnectorAuthError("Unable to resolve OneDrive ID")
            return drive_id, None

        if not site_id:
            site = self._get_json(config, f"{GRAPH_BASE_URL}/sites/root")
            site_id = site.get("id")
            if not site_id:
                raise ConnectorAuthError("Unable to resolve SharePoint site ID")

        drive = self._get_json(config, f"{GRAPH_BASE_URL}/sites/{site_id}/drive")
        drive_id = drive.get("id")
        if not drive_id:
            raise ConnectorAuthError("Unable to resolve SharePoint drive ID")

        return drive_id, site_id

    def _list_recursive_items(self, config: dict, since: datetime | None) -> Iterator[RemoteFile]:
        drive_id = config["drive_id"]
        delta_token = self._get_delta_token(config, since)

        items, delta_link = self._delta_listing(config, drive_id, delta_token)
        for item in items:
            remote = self._item_to_remote(item, include_folders=False)
            if remote:
                yield remote

        if delta_link and config.get("user_id"):
            manager = SyncManager(config["user_id"], config.get("provider") or config.get("target_type", self.target_type))
            manager.update_state(last_cursor=delta_link)

    def _list_children_items(self, config: dict, parent_id: str) -> Iterator[RemoteFile]:
        drive_id = config["drive_id"]
        for item in self._list_children(config, drive_id, parent_id):
            remote = self._item_to_remote(item, include_folders=True)
            if remote:
                yield remote

    def _walk_folder(self, config: dict, folder_id: str, scope_id: str) -> Iterator[SourceDocument]:
        drive_id = config["drive_id"]
        stack = [folder_id]

        while stack:
            current = stack.pop()
            for item in self._list_children(config, drive_id, current):
                if item.get("folder"):
                    stack.append(item["id"])
                    continue
                yield self._build_source_document(config, item, scope_id)

    def _list_children(self, config: dict, drive_id: str, parent_id: str) -> Iterator[dict]:
        if parent_id in (None, "root"):
            url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root/children"
        else:
            url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{parent_id}/children"

        for item in self._paged_items(config, url):
            yield item

    def _delta_listing(self, config: dict, drive_id: str, delta_token: str | None) -> tuple[list[dict], str | None]:
        if delta_token and delta_token.startswith("http"):
            url = delta_token
            params = None
        else:
            url = f"{GRAPH_BASE_URL}/drives/{drive_id}/root/delta"
            params = {"token": delta_token} if delta_token else None

        items: list[dict] = []
        delta_link: str | None = None

        while url:
            data = self._get_json(config, url, params=params)
            items.extend(data.get("value", []))
            delta_link = data.get("@odata.deltaLink") or delta_link
            next_link = data.get("@odata.nextLink")
            url = next_link
            params = None

        # Filter out deleted entries
        filtered = [item for item in items if not item.get("deleted")]
        return filtered, delta_link

    def _get_delta_token(self, config: dict, since: datetime | None) -> str | None:
        if isinstance(since, str):
            return since
        delta_token = config.get("delta_token")
        if delta_token:
            return delta_token
        user_id = config.get("user_id")
        if not user_id:
            return None
        manager = SyncManager(user_id, config.get("provider") or config.get("target_type", self.target_type))
        state = manager.get_state()
        return state.last_cursor if state else None

    def _item_to_remote(self, item: dict, include_folders: bool) -> RemoteFile | None:
        item_id = item.get("id")
        if not item_id:
            return None

        is_folder = bool(item.get("folder"))
        if is_folder and not include_folders:
            return None

        mime_type = None
        size = None
        if is_folder:
            mime_type = "inode/directory"
        else:
            file_meta = item.get("file") or {}
            mime_type = file_meta.get("mimeType")
            size = item.get("size")

        return RemoteFile(
            id=item_id,
            name=item.get("name") or item_id,
            mime_type=mime_type,
            size=size,
            modified_at=self._parse_datetime(item.get("lastModifiedDateTime")),
            parent_id=(item.get("parentReference") or {}).get("id"),
            web_view_url=item.get("webUrl"),
        )

    def _build_source_document(self, config: dict, item: dict, scope_id: str) -> SourceDocument:
        content = self._download_content(config, item["id"])
        filename = item.get("name") or item["id"]
        mime_type = (item.get("file") or {}).get("mimeType") or "application/octet-stream"
        size_bytes = item.get("size") or len(content)
        parent_id = (item.get("parentReference") or {}).get("id")

        return SourceDocument(
            content=content,
            metadata={
                "source": config.get("target_type", self.target_type),
                "drive_id": config.get("drive_id"),
                "site_id": config.get("site_id"),
                "web_url": item.get("webUrl"),
                "modified_at": item.get("lastModifiedDateTime"),
                "size": item.get("size"),
                "scope_id": scope_id,  # CRITICAL: Required for FK compliance
            },
            source_type=self.connector_type,
            source_id=item["id"],
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            parent_id=parent_id,
        )

    def _get_item(self, config: dict, item_id: str) -> dict:
        drive_id = config["drive_id"]
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}"
        return self._get_json(config, url)

    def _download_content(self, config: dict, item_id: str) -> bytes:
        drive_id = config["drive_id"]
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/content"
        headers = self._auth_headers(config)

        with connector_fetch_limit(config.get("target_type", self.target_type)):
            response = self._request_with_retry("GET", url, headers=headers, stream=True, allow_redirects=False)

        if response.status_code in {301, 302, 303, 307, 308}:
            location = response.headers.get("Location")
            if not location:
                raise ConnectorTransientError("Missing redirect location for download")
            response.close()
            response = self._request_with_retry("GET", location, headers={}, stream=True)

        if response.status_code == 404:
            raise ItemNotFoundError(f"Graph item not found: {item_id}")

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise ConnectorTransientError(str(exc)) from exc

        buffer = io.BytesIO()
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                buffer.write(chunk)
        response.close()
        return buffer.getvalue()

    def _paged_items(self, config: dict, url: str) -> Iterator[dict]:
        while url:
            data = self._get_json(config, url)
            for item in data.get("value", []):
                yield item
            url = data.get("@odata.nextLink")

    def _get_json(self, config: dict, url: str, params: dict | None = None) -> dict:
        headers = self._auth_headers(config)
        with connector_fetch_limit(config.get("target_type", self.target_type)):
            response = self._request_with_retry("GET", url, headers=headers, params=params)
        if response.status_code == 404:
            detail = response.text[:500]
            response.close()
            raise ConnectorTransientError(f"Microsoft Graph resource not found: {detail}")
        if response.status_code >= 400:
            detail = response.text[:500]
            response.close()
            raise ConnectorTransientError(f"Microsoft Graph request failed: {detail}")
        try:
            return response.json()
        except ValueError as exc:
            raise ConnectorTransientError("Invalid JSON response from Microsoft Graph") from exc

    def _auth_headers(self, config: dict) -> dict:
        return {
            "Authorization": f"Bearer {config.get('access_token')}",
            "Accept": "application/json",
        }

    def _request_with_retry(
        self,
        method: str,
        url: str,
        headers: dict | None = None,
        params: dict | None = None,
        stream: bool = False,
        allow_redirects: bool = True,
    ) -> requests.Response:
        headers = headers or {}
        attempt = 0

        while True:
            try:
                response = requests.request(
                    method,
                    url,
                    headers=headers,
                    params=params,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                    stream=stream,
                    allow_redirects=allow_redirects,
                )
            except requests.RequestException as exc:
                raise ConnectorTransientError(str(exc)) from exc

            if response.status_code == 429:
                if attempt >= MAX_RETRIES:
                    raise ConnectorRateLimitError("Microsoft Graph rate limit exceeded")
                retry_after = response.headers.get("Retry-After")
                retry_after_ms = response.headers.get("x-ms-retry-after-ms")
                delay = 1
                if retry_after:
                    try:
                        delay = int(retry_after)
                    except ValueError:
                        delay = 1
                elif retry_after_ms:
                    try:
                        delay = max(1, int(retry_after_ms) // 1000)
                    except ValueError:
                        delay = 1
                response.close()
                logger.warning("⏳ [Graph] Rate limited, retrying in %ss", delay)
                time.sleep(delay)
                attempt += 1
                continue

            if response.status_code in {401, 403}:
                detail = response.text[:500]
                response.close()
                raise ConnectorAuthError(f"Microsoft Graph auth failed: {detail}")

            if response.status_code >= 500:
                detail = response.text[:500]
                response.close()
                raise ConnectorTransientError(f"Microsoft Graph error: {detail}")

            return response

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            if value.endswith("Z"):
                value = value.replace("Z", "+00:00")
            return datetime.fromisoformat(value)
        except ValueError:
            return None
