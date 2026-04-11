"""
Google Drive Connector

Connects to Google Drive API to fetch and sync files.
Supports listing, ingestion, and background sync with chunking/embedding.
File parsing is delegated to the centralized DocumentParser service.
"""

import logging
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, timezone
from typing import Any

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.concurrency import run_in_threadpool

from connectors.base import (
    BaseConnector,
    ConnectorAuthError,
    ConnectorTransientError,
    RemoteFile,
)
from connectors.enhanced import (
    AuthenticationError,
    EnhancedConnector,
    SourceDocument,
    SourceType,
)
from connectors.limits import connector_fetch_limit
from core.config import settings
from core.db import get_supabase
from core.resilience import google_drive_breaker, with_google_retry
from core.scopes import build_scope_uri
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)
SHARED_DRIVE_PREFIX = "shared_drive"


class DriveConnector(EnhancedConnector, BaseConnector):
    """
    Google Drive connector for unified ingestion.

    Supports:
    - OAuth token refresh
    - File listing with folder expansion
    - Multiple file formats via DocumentProcessorFactory
    """

    @property
    def connector_type(self) -> SourceType:
        return SourceType.GOOGLE_DRIVE

    @staticmethod
    def _normalize_since(since: datetime | str | None) -> datetime | None:
        if since is None:
            return None

        if isinstance(since, datetime):
            return since if since.tzinfo else since.replace(tzinfo=timezone.utc)

        if isinstance(since, str):
            normalized = since.strip()
            if not normalized:
                return None
            if normalized.endswith("Z"):
                normalized = normalized[:-1] + "+00:00"
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

        raise ValueError(f"Unsupported since value: {since!r}")

    @staticmethod
    def _format_drive_timestamp(value: datetime) -> str:
        return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _parse_drive_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _encode_shared_drive_item_id(drive_id: str, item_id: str = "root") -> str:
        return f"{SHARED_DRIVE_PREFIX}:{drive_id}:{item_id}"

    @staticmethod
    def _decode_shared_drive_item_id(item_id: str | None) -> tuple[str, str] | None:
        if not item_id or not item_id.startswith(f"{SHARED_DRIVE_PREFIX}:"):
            return None
        parts = item_id.split(":", 2)
        if len(parts) != 3:
            return None
        _, drive_id, raw_item_id = parts
        return drive_id, raw_item_id

    def _build_drive_list_kwargs(
        self,
        q: str,
        fields: str,
        *,
        page_token: str | None = None,
        shared_drive_id: str | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "q": q,
            "fields": fields,
            "orderBy": "folder,name",
            "pageSize": 1000,
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            kwargs["pageToken"] = page_token
        if shared_drive_id:
            kwargs["corpora"] = "drive"
            kwargs["driveId"] = shared_drive_id
        return kwargs

    @staticmethod
    def _build_drive_get_kwargs(file_id: str, fields: str) -> dict[str, Any]:
        return {
            "fileId": file_id,
            "fields": fields,
            "supportsAllDrives": True,
        }

    @with_google_retry(max_attempts=3)
    def _drive_get(self, service, **kwargs):
        with google_drive_breaker, connector_fetch_limit("google_drive"):
            try:
                kwargs.setdefault("supportsAllDrives", True)
                return service.files().get(**kwargs).execute()
            except Exception as exc:
                raise ConnectorTransientError(str(exc)) from exc

    @with_google_retry(max_attempts=3)
    def _drive_list(self, service, **kwargs):
        with google_drive_breaker, connector_fetch_limit("google_drive"):
            try:
                kwargs.setdefault("supportsAllDrives", True)
                kwargs.setdefault("includeItemsFromAllDrives", True)
                return service.files().list(**kwargs).execute()
            except Exception as exc:
                raise ConnectorTransientError(str(exc)) from exc

    @with_google_retry(max_attempts=3)
    def _drive_list_shared_drives(self, service, **kwargs):
        with google_drive_breaker, connector_fetch_limit("google_drive"):
            try:
                return service.drives().list(**kwargs).execute()
            except Exception as exc:
                raise ConnectorTransientError(str(exc)) from exc

    def _download_file_content(self, service, file_meta):
        """
        Download file content using chunked streaming with memory-safe buffering.
        Returns (content_bytes, export_mime_type, filename).

        Uses SpooledTemporaryFile for memory safety:
        - Files < 10MB: buffered in RAM (fast)
        - Files > 10MB: automatically spilled to disk (safe)
        - Prevents OOM crashes on large file downloads
        """
        import tempfile

        from googleapiclient.http import MediaIoBaseDownload

        # 10MB threshold: small files stay in RAM, large files go to disk
        MAX_MEM_SIZE = 10 * 1024 * 1024

        file_id = file_meta['id']
        mime_type = file_meta.get('mimeType')
        name = file_meta.get('name')

        # 1. Handle Google Native formats (Export)
        if mime_type in self.EXPORT_MIME_TYPES:
            export_info = self.EXPORT_MIME_TYPES[mime_type]
            export_mime = export_info['export_mime']
            ext = export_info['extension']
            filename = f"{name}{ext}"

            try:
                with connector_fetch_limit("google_drive"):
                    request = service.files().export_media(fileId=file_id, mimeType=export_mime)
                    # SpooledTemporaryFile: RAM < 10MB < Disk
                    with tempfile.SpooledTemporaryFile(max_size=MAX_MEM_SIZE, mode='w+b') as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                            if status:
                                logger.debug(f"📥 [Drive] Export progress {name}: {int(status.progress() * 100)}%")
                        fh.seek(0)
                        content = fh.read()
                return content, export_mime, filename
            except Exception as e:
                logger.warning(f"⚠️ [Drive] Export failed for {name}: {e}")
                raise ConnectorTransientError(str(e)) from e

        # 2. Handle Folders (skip)
        elif mime_type == 'application/vnd.google-apps.folder':
            return None, None, None

        # 3. Handle Binary files (Direct Download with streaming)
        else:
            try:
                with connector_fetch_limit("google_drive"):
                    request = service.files().get_media(fileId=file_id)
                    # SpooledTemporaryFile: RAM < 10MB < Disk (prevents OOM on large files)
                    with tempfile.SpooledTemporaryFile(max_size=MAX_MEM_SIZE, mode='w+b') as fh:
                        downloader = MediaIoBaseDownload(fh, request)
                        done = False
                        while not done:
                            status, done = downloader.next_chunk()
                            if status:
                                logger.debug(f"📥 [Drive] Download progress {name}: {int(status.progress() * 100)}%")
                        fh.seek(0)
                        content = fh.read()
                return content, mime_type, name
            except Exception as e:
                logger.warning(f"⚠️ [Drive] Download failed for {name}: {e}")
                raise ConnectorTransientError(str(e)) from e

    def _list_shared_drives(self, service) -> list[dict[str, Any]]:
        drives: list[dict[str, Any]] = []
        page_token: str | None = None

        while True:
            results = self._drive_list_shared_drives(
                service,
                pageSize=100,
                fields="nextPageToken, drives(id, name)",
                pageToken=page_token,
            )
            drives.extend(results.get("drives", []))
            page_token = results.get("nextPageToken")
            if not page_token:
                break

        drives.sort(key=lambda drive: (drive.get("name") or "").lower())
        return drives

    def _list_drive_children(
        self,
        service,
        parent_id: str,
        *,
        since: datetime | str | None = None,
        shared_drive_id: str | None = None,
    ) -> list[dict[str, Any]]:
        since_dt = self._normalize_since(since)
        fields = "nextPageToken, files(id, name, mimeType, iconLink, thumbnailLink, size, webViewLink, modifiedTime)"

        def build_query(parent_ref: str) -> str:
            query = f"'{parent_ref}' in parents and trashed=false"
            if since_dt:
                query += f" and modifiedTime > '{self._format_drive_timestamp(since_dt)}'"
            return query

        queries = [build_query(parent_id)]
        if shared_drive_id and parent_id == "root":
            queries.append(build_query(shared_drive_id))

        for idx, query in enumerate(queries):
            collected: list[dict[str, Any]] = []
            page_token: str | None = None
            while True:
                results = self._drive_list(
                    service,
                    **self._build_drive_list_kwargs(
                        query,
                        fields,
                        page_token=page_token,
                        shared_drive_id=shared_drive_id,
                    ),
                )
                collected.extend(results.get("files", []))
                page_token = results.get("nextPageToken")
                if not page_token:
                    break

            if collected or idx == len(queries) - 1:
                return collected

        return []

    def _get_all_files_recursive(
        self,
        service,
        parent_id: str,
        *,
        shared_drive_id: str | None = None,
    ) -> Iterator[dict]:
        """
        Recursively fetch all files in a folder (Generator).
        Yields file metadata objects.
        """
        try:
            files = self._list_drive_children(
                service,
                parent_id,
                shared_drive_id=shared_drive_id,
            )
        except Exception as e:
            logger.error(f"❌ [Drive] Error listing folder {parent_id}: {e}")
            return

        for f in files:
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                yield from self._get_all_files_recursive(service, f['id'], shared_drive_id=shared_drive_id)
            else:
                yield f

    # =========================================================================
    # EXPORT FORMAT: Map Google Native types to text formats for ingestion
    # =========================================================================
    # Google Docs -> Plain text
    # Google Sheets -> CSV
    # Google Slides -> Plain text
    EXPORT_MIME_TYPES = {
        "application/vnd.google-apps.document": {
            "export_mime": "text/plain",
            "extension": ".txt",
        },
        "application/vnd.google-apps.spreadsheet": {
            "export_mime": "text/csv",
            "extension": ".csv",
        },
        "application/vnd.google-apps.presentation": {
            "export_mime": "text/plain",
            "extension": ".txt",
        },
    }


    async def authorize(self, user_id: str) -> bool:
        """Async wrapper for authorization check."""
        return await run_in_threadpool(self._authorize_implementation, user_id)

    def validate_config(self, config: dict) -> bool:
        return bool(config.get("user_id") or config.get("integration_id"))

    def _authorize_implementation(self, user_id: str) -> bool:
        """Synchronous implementation of authorize."""
        supabase = get_supabase()

        # Lookup connector definition
        def_res = supabase.table("connector_definitions").select("id").eq("type", "google_drive").single().execute()
        if not def_res.data:
            return False

        connector_def_id = def_res.data["id"]

        # Check for user integration
        res = supabase.table("user_integrations").select("id").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()

        return len(res.data) > 0

    def _get_credentials_by_integration(self, integration: dict) -> Credentials:
        """
        Build Google credentials from an integration record.
        Uses centralized token manager for automatic refresh.
        """
        # Check integration status first - fail early if reconnection required
        status = integration.get("status", "active")
        if status == "reconnection_required":
            status_message = integration.get("status_message", "Please reconnect your Google Drive account.")
            logger.warning(f"⚠️ [Drive] Integration {integration.get('id')} requires reconnection")
            raise ValueError(f"Integration requires reconnection: {status_message}")

        try:
            # Use centralized token manager for automatic refresh
            creds_data = OAuthTokenManager.get_valid_credentials(
                integration,
                'google_drive'
            )

            # Build Google credentials with refreshed token
            creds = Credentials(
                token=creds_data['access_token'],
                refresh_token=creds_data['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/drive.readonly'],
                quota_project_id=None
            )

            return creds

        except TokenRefreshError as e:
            logger.error(f"❌ Token refresh failed: {e}")
            raise ValueError("Integration requires reconnection (Token Expired/Revoked)") from e

    def _get_credentials(self, user_id: str) -> Credentials:
        """
        Get Google credentials for a user by looking up their integration.
        """
        supabase = get_supabase()

        # Lookup connector definition
        def_res = supabase.table("connector_definitions").select("id").eq("type", "google_drive").single().execute()
        if not def_res.data:
            raise ValueError("google_drive connector not found in definitions")

        connector_def_id = def_res.data["id"]

        # Get user integration
        res = supabase.table("user_integrations").select("*").eq(
            "user_id", user_id
        ).eq("connector_definition_id", connector_def_id).execute()

        if not res.data:
            raise ValueError("Google Drive not connected for this user.")

        return self._get_credentials_by_integration(res.data[0])

    async def list_files(self, config: dict[str, Any], since: datetime | str | None = None) -> list[RemoteFile]:
        """Async wrapper for listing items using config."""
        user_id = config.get("user_id")
        parent_id = config.get("parent_id")
        return await run_in_threadpool(self._list_files_sync, user_id, parent_id, since)

    def _list_files_sync(
        self,
        user_id: str,
        parent_id: str | None = None,
        since: datetime | str | None = None,
    ) -> list[RemoteFile]:
        """Synchronous implementation of list_files."""
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        since_dt = self._normalize_since(since)
        decoded_parent = self._decode_shared_drive_item_id(parent_id)
        shared_drive_id: str | None = None

        if decoded_parent:
            shared_drive_id, raw_parent_id = decoded_parent
            query_parent = "root" if raw_parent_id == "root" else raw_parent_id
        else:
            query_parent = parent_id if parent_id else 'root'

        files = self._list_drive_children(
            service,
            query_parent,
            since=since_dt,
            shared_drive_id=shared_drive_id,
        )
        items: list[RemoteFile] = []
        for f in files:
            is_folder = f['mimeType'] == 'application/vnd.google-apps.folder'
            item_id = f["id"]
            if shared_drive_id:
                item_id = self._encode_shared_drive_item_id(shared_drive_id, f["id"])
            items.append(
                RemoteFile(
                    id=item_id,
                    name=f["name"],
                    mime_type=f["mimeType"],
                    size=int(f.get("size") or 0) if not is_folder else None,
                    modified_at=self._parse_drive_timestamp(f.get("modifiedTime")),
                    parent_id=parent_id or "root",
                    web_view_url=f.get("webViewLink"),
                )
            )

        if parent_id is None and since_dt is None:
            for drive in self._list_shared_drives(service):
                items.append(
                    RemoteFile(
                        id=self._encode_shared_drive_item_id(drive["id"], "root"),
                        name=drive["name"],
                        mime_type="application/vnd.google-apps.folder",
                        size=None,
                        modified_at=None,
                        parent_id="root",
                        web_view_url=None,
                    )
                )
        return items




    async def fetch_documents(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs
    ) -> AsyncIterator[SourceDocument]:
        """Async wrapper for sync fetch."""
        for doc in self.fetch_documents_sync(item_ids, credentials, **kwargs):
            yield doc

    def fetch_documents_sync(
        self,
        item_ids: list[str],
        credentials: dict[str, Any] | None = None,
        **kwargs
    ) -> Iterator[SourceDocument]:
        user_id = kwargs.get("user_id") or credentials.get("user_id") if credentials else None
        if not item_ids:
            return iter(())

        logger.info(f"📥 [DriveConnector] Fetching {len(item_ids)} item(s)")

        # Resolve credentials (integration_id preferred; user_id fallback for API usage)
        if credentials and credentials.get("integration_id"):
            supabase = get_supabase()
            int_res = supabase.table("user_integrations").select("*").eq(
                "id", credentials["integration_id"]
            ).maybe_single().execute()
            if not int_res.data:
                raise AuthenticationError(f"Integration {credentials['integration_id']} not found")

            creds_data = OAuthTokenManager.get_valid_credentials(int_res.data, "google_drive")
            creds = Credentials(
                token=creds_data["access_token"],
                refresh_token=creds_data["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
        elif user_id:
            creds = self._get_credentials(user_id)
        else:
            raise AuthenticationError("No credentials or user_id provided for Drive fetch")

        service = build("drive", "v3", credentials=creds)

        for item_id in item_ids:
            try:
                shared_drive_context = self._decode_shared_drive_item_id(item_id)
                shared_drive_id: str | None = None
                raw_item_id = item_id
                if shared_drive_context:
                    shared_drive_id, raw_item_id = shared_drive_context

                if shared_drive_id and raw_item_id == "root":
                    scope_id = build_scope_uri("google_drive", {"folder_id": shared_drive_id})
                    folder_files = list(self._get_all_files_recursive(service, "root", shared_drive_id=shared_drive_id))
                    logger.info(
                        "📁 [DriveConnector] Found %s file(s) in shared drive %s",
                        len(folder_files),
                        shared_drive_id,
                    )
                    for f in folder_files:
                        doc = self._build_source_document(service, f, parent_id=item_id, scope_id=scope_id)
                        if doc:
                            yield doc
                    continue

                file_meta = self._drive_get(
                    service,
                    **self._build_drive_get_kwargs(
                        raw_item_id,
                        "id, name, mimeType, webViewLink, size, modifiedTime",
                    ),
                )

                # Generate scope_id using canonical URI builder
                scope_id = build_scope_uri("google_drive", {"folder_id": shared_drive_id or raw_item_id})

                if file_meta["mimeType"] == "application/vnd.google-apps.folder":
                    folder_files = list(self._get_all_files_recursive(service, raw_item_id, shared_drive_id=shared_drive_id))
                    logger.info(
                        "📁 [DriveConnector] Found %s file(s) in folder %s",
                        len(folder_files),
                        file_meta["name"],
                    )
                    for f in folder_files:
                        doc = self._build_source_document(service, f, parent_id=item_id, scope_id=scope_id)
                        if doc:
                            yield doc
                else:
                    doc = self._build_source_document(service, file_meta, parent_id=None, scope_id=scope_id)
                    if doc:
                        yield doc
            except Exception as e:
                logger.error(f"❌ [Drive] Failed to process {item_id}: {e}")
                continue

        logger.info("📥 [DriveConnector] Fetch stream ended")

    def _build_source_document(
        self,
        service,
        file_meta: dict[str, Any],
        parent_id: str | None,
        scope_id: str,
    ) -> SourceDocument | None:
        content_bytes, export_mime, filename = self._download_file_content(service, file_meta)
        if not content_bytes:
            return None

        file_size = len(content_bytes)
        source_url = file_meta.get("webViewLink")
        file_id = file_meta.get("id")

        return SourceDocument(
            content=content_bytes,
            metadata={
                "source": "google_drive",
                "title": filename,
                "source_url": source_url,
                "file_id": file_id,
                "mime_type": export_mime,
                "file_size": file_size,
                "size": file_size,
                "scope_id": scope_id,  # CRITICAL: Required for FK compliance
            },
            source_type=SourceType.GOOGLE_DRIVE,
            source_id=file_id or "unknown",
            filename=filename,
            mime_type=export_mime or "application/octet-stream",
            size_bytes=file_size,
            parent_id=parent_id,
        )

    def fetch_file_content(self, file_id: str, config: dict[str, Any]) -> bytes:
        """
        Fetch raw file bytes for a given Drive file ID.
        Required by BaseConnector interface.
        """
        user_id = config.get("user_id")
        integration_id = config.get("integration_id")

        # Resolve credentials
        if integration_id:
            supabase = get_supabase()
            int_res = supabase.table("user_integrations").select("*").eq(
                "id", integration_id
            ).maybe_single().execute()
            if not int_res.data:
                raise ConnectorAuthError(f"Integration {integration_id} not found")

            creds_data = OAuthTokenManager.get_valid_credentials(int_res.data, "google_drive")
            creds = Credentials(
                token=creds_data["access_token"],
                refresh_token=creds_data["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=["https://www.googleapis.com/auth/drive.readonly"],
            )
        elif user_id:
            creds = self._get_credentials(user_id)
        else:
            raise ConnectorAuthError("No user_id or integration_id in config")

        service = build("drive", "v3", credentials=creds)

        shared_drive_context = self._decode_shared_drive_item_id(file_id)
        raw_file_id = shared_drive_context[1] if shared_drive_context else file_id
        if raw_file_id == "root":
            raise ConnectorTransientError("Cannot download shared drive root as a file")

        # Get file metadata first
        file_meta = self._drive_get(
            service,
            **self._build_drive_get_kwargs(raw_file_id, "id, name, mimeType"),
        )

        content_bytes, _, _ = self._download_file_content(service, file_meta)
        if not content_bytes:
            raise ConnectorTransientError(f"Failed to download file {file_id}")

        return content_bytes
