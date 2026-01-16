"""
Google Drive Connector

Connects to Google Drive API to fetch and sync files.
Supports listing, ingestion, and background sync with chunking/embedding.
File parsing is delegated to the centralized DocumentParser service.
"""

import logging
from typing import List, Optional, Dict, Any, Iterator, AsyncIterator
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from starlette.concurrency import run_in_threadpool
from connectors.enhanced import EnhancedConnector, SourceDocument, SourceType, AuthenticationError
from connectors.base import BaseConnector, ConnectorAuthError, ConnectorRateLimitError, ConnectorTransientError, RemoteFile
from core.db import get_supabase
from core.config import settings
from core.scopes import build_scope_uri
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError
from connectors.limits import connector_fetch_limit
from core.resilience import with_google_retry

logger = logging.getLogger(__name__)


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

    @with_google_retry(max_attempts=3)
    def _drive_get(self, service, **kwargs):
        with connector_fetch_limit("google_drive"):
            try:
                return service.files().get(**kwargs).execute()
            except Exception as exc:
                raise ConnectorTransientError(str(exc)) from exc

    @with_google_retry(max_attempts=3)
    def _drive_list(self, service, **kwargs):
        with connector_fetch_limit("google_drive"):
            try:
                return service.files().list(**kwargs).execute()
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

    def _get_all_files_recursive(self, service, parent_id: str) -> Iterator[Dict]:
        """
        Recursively fetch all files in a folder (Generator).
        Yields file metadata objects.
        """
        query = f"'{parent_id}' in parents and trashed=false"
        
        # Paginator for large folders
        page_token = None
        while True:
            try:
                results = self._drive_list(
                    service,
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, webViewLink, size)",
                    pageSize=1000,
                    pageToken=page_token,
                )
                
                files = results.get('files', [])
                for f in files:
                    if f['mimeType'] == 'application/vnd.google-apps.folder':
                        # Recurse
                        yield from self._get_all_files_recursive(service, f['id'])
                    else:
                        yield f
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"❌ [Drive] Error listing folder {parent_id}: {e}")
                break
    
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

    async def list_files(self, config: Dict[str, Any], since: Optional[str] = None) -> List[RemoteFile]:
        """Async wrapper for listing items using config."""
        user_id = config.get("user_id")
        parent_id = config.get("parent_id")
        return await run_in_threadpool(self._list_files_sync, user_id, parent_id)

    def _list_files_sync(self, user_id: str, parent_id: Optional[str] = None) -> List[RemoteFile]:
        """Synchronous implementation of list_files."""
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        
        query_parent = parent_id if parent_id else 'root'
        
        results = self._drive_list(
            service,
            q=f"'{query_parent}' in parents and trashed=false",
            fields="files(id, name, mimeType, iconLink, thumbnailLink, size)",
            orderBy="folder,name",
            pageSize=1000,
        )

        files = results.get('files', [])
        items: List[RemoteFile] = []
        for f in files:
            is_folder = f['mimeType'] == 'application/vnd.google-apps.folder'
            items.append(
                RemoteFile(
                    id=f["id"],
                    name=f["name"],
                    mime_type=f["mimeType"],
                    size=int(f.get("size") or 0) if not is_folder else None,
                    modified_at=None,
                    parent_id=query_parent,
                    web_view_url=f.get("webViewLink"),
                )
            )
        return items




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
        user_id = kwargs.get("user_id") or credentials.get("user_id") if credentials else None
        if not item_ids:
            return iter(())

        logger.info(f"📥 [DriveConnector] Fetching {len(item_ids)} item(s)")

        # Resolve credentials (integration_id preferred; user_id fallback for API usage)
        if credentials and credentials.get("integration_id"):
            supabase = get_supabase()
            int_res = supabase.table("user_integrations").select("*").eq(
                "id", credentials["integration_id"]
            ).single().execute()
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
                file_meta = self._drive_get(
                    service,
                    fileId=item_id,
                    fields="id, name, mimeType, webViewLink, size",
                )
                
                # Generate scope_id using canonical URI builder
                scope_id = build_scope_uri("google_drive", {"folder_id": item_id})

                if file_meta["mimeType"] == "application/vnd.google-apps.folder":
                    folder_files = list(self._get_all_files_recursive(service, item_id))
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
        file_meta: Dict[str, Any],
        parent_id: Optional[str],
        scope_id: str,
    ) -> Optional[SourceDocument]:
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

    def fetch_file_content(self, file_id: str, config: Dict[str, Any]) -> bytes:
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
            ).single().execute()
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

        # Get file metadata first
        file_meta = self._drive_get(
            service,
            fileId=file_id,
            fields="id, name, mimeType",
        )

        content_bytes, _, _ = self._download_file_content(service, file_meta)
        if not content_bytes:
            raise ConnectorTransientError(f"Failed to download file {file_id}")

        return content_bytes
