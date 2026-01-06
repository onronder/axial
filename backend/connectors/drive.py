"""
Google Drive Connector

Connects to Google Drive API to fetch and sync files.
Supports listing, ingestion, and background sync with chunking/embedding.
File parsing is delegated to the centralized DocumentParser service.
"""

import logging
import base64
from typing import List, Optional, Dict, Any, Iterator, AsyncIterator
from datetime import datetime, timezone
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from langchain_text_splitters import RecursiveCharacterTextSplitter
from starlette.concurrency import run_in_threadpool
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings
from services.parsers import DocumentParser
from core.security import decrypt_token
from services.oauth_token_manager import OAuthTokenManager, TokenRefreshError

logger = logging.getLogger(__name__)


class DriveConnector(BaseConnector):
    """
    Google Drive connector with full sync capabilities.
    
    Supports:
    - OAuth token refresh
    - File listing with folder expansion
    - Background sync with chunking and embedding
    - Multiple file formats via DocumentParser service
    """
    
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
                return None, None, None

        # 2. Handle Folders (skip)
        elif mime_type == 'application/vnd.google-apps.folder':
            return None, None, None
            
        # 3. Handle Binary files (Direct Download with streaming)
        else:
            try:
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
                return None, None, None
                return None, None, None

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
                results = service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, webViewLink, size)",
                    pageSize=1000,
                    pageToken=page_token
                ).execute()
                
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
    
    # Text splitter for chunking documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # =========================================================================
    # EXPORT FORMAT: Map Google Native types to text formats for RAG
    # =========================================================================
    # IMPORTANT: We export to TEXT formats, not binary (DOCX/PDF), because:
    # 1. The connector decodes content to UTF-8 text for ConnectorDocument
    # 2. Binary formats (DOCX, PDF) get corrupted by UTF-8 decode
    # 3. For RAG, we need the text content anyway
    # 
    # Google Docs -> Plain text (clean, no formatting)
    # Google Sheets -> CSV (row/column structure preserved)
    # Google Slides -> Plain text (extracted text from slides)
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
    
    # Supported MIME types for ingestion
    SUPPORTED_MIME_TYPES = {
        # Google native types -> exported as text
        'application/vnd.google-apps.document': 'gdoc',
        'application/vnd.google-apps.spreadsheet': 'gsheet',
        'application/vnd.google-apps.presentation': 'gslides',
        # Text formats -> directly compatible (UTF-8 safe)
        'text/plain': 'text',
        'text/markdown': 'text',
        'text/csv': 'text',
        'text/html': 'text',
        'application/json': 'text',
        'application/xml': 'text',
        'text/xml': 'text',
        # Binary formats -> need base64 encoding
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'docx',
        'application/pdf': 'pdf',
    }
    
    # Binary MIME types that cannot be decoded as UTF-8
    # These must be base64 encoded when passed through ConnectorDocument
    BINARY_MIME_TYPES = {
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/msword',
        'application/pdf',
    }
    
    async def authorize(self, user_id: str) -> bool:
        """Async wrapper for authorization check."""
        return await run_in_threadpool(self._authorize_implementation, user_id)

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

    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        """Async wrapper for listing items."""
        return await run_in_threadpool(self._list_items_implementation, user_id, parent_id)

    def _list_items_implementation(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        """Synchronous implementation of list_items."""
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        
        query_parent = parent_id if parent_id else 'root'
        
        results = service.files().list(
            q=f"'{query_parent}' in parents and trashed=false",
            fields="files(id, name, mimeType, iconLink, thumbnailLink, size)",
            orderBy="folder,name",
            pageSize=1000
        ).execute()

        files = results.get('files', [])
        items = []
        for f in files:
            is_folder = f['mimeType'] == 'application/vnd.google-apps.folder'
            items.append(ConnectorItem(
                id=f['id'],
                name=f['name'],
                type='folder' if is_folder else 'file',
                mime_type=f['mimeType'],
                icon=f.get('iconLink'),
                parent_id=query_parent
            ))
        return items




    async def ingest(self, config: Dict[str, Any]) -> "AsyncIterator[ConnectorDocument]":
        """
        Async wrapper for ingestion (Streaming).
        """
        from starlette.concurrency import iterate_in_threadpool
        return iterate_in_threadpool(self._ingest_implementation(config))

    def _ingest_implementation(self, config: Dict[str, Any]) -> "Iterator[ConnectorDocument]":
        """
        Synchronous ingestion implementation (Generator).
        """
        try:
            yield from self._ingest_logic(config)
        except Exception as e:
            logger.error(f"❌ [Drive] Ingest failed: {e}")
            raise e

    def _ingest_logic(self, config: Dict[str, Any]) -> "Iterator[ConnectorDocument]":
        # Original ingest logic goes here to keep try/except clean
        user_id = config.get("user_id")
        item_ids = config.get("item_ids", [])
        credentials_data = config.get("credentials")
        
        logger.info(f"📥 [DriveConnector] Starting ingestion for {len(item_ids)} items")

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
                'google_drive'
            )
            
            creds = Credentials(
                token=creds_data['access_token'],
                refresh_token=creds_data['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        elif credentials_data:
            # Legacy: Use passed decrypted credentials (fallback)
            creds = Credentials(
                token=credentials_data.get('token') or credentials_data.get('access_token'),
                refresh_token=credentials_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        elif user_id:
            # API case: Fallback to DB lookup (already has refresh)
            creds = self._get_credentials(user_id)
        else:
            raise ValueError("No credentials or user_id provided for Drive ingestion")

        # 2. Build Service & Process
        service = build('drive', 'v3', credentials=creds)
        # No documents list - we yield!

        for item_id in item_ids:
            try:
                # Fetch metadata
                file_meta = service.files().get(
                    fileId=item_id, 
                    fields="id, name, mimeType, webViewLink, size"
                ).execute()
                
                # Handle folders recursively
                if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                    # Convert generator to list so we can count and iterate
                    folder_files = list(self._get_all_files_recursive(service, item_id))
                    logger.info(f"📁 [DriveConnector] Found {len(folder_files)} files in folder: {file_meta['name']}")
                    
                    for f in folder_files:
                        try:
                            content_bytes, export_mime, filename = self._download_file_content(service, f)
                            if content_bytes:
                                file_size = len(content_bytes)
                                
                                # Check if binary or text
                                if export_mime in self.BINARY_MIME_TYPES:
                                    # Binary: Encode as base64 string
                                    text_content = base64.b64encode(content_bytes).decode('ascii')
                                else:
                                    # Text: Decode UTF-8
                                    try:
                                        text_content = content_bytes.decode('utf-8')
                                    except UnicodeDecodeError:
                                        text_content = content_bytes.decode('utf-8', errors='replace')
                                    
                                    # Remove null bytes that break PostgreSQL
                                    text_content = text_content.replace('\x00', '')
                                
                                yield ConnectorDocument(
                                    page_content=text_content,
                                    metadata={
                                        "source": "google_drive",
                                        "title": filename,
                                        "source_url": f.get('webViewLink'),
                                        "file_id": f.get('id'),
                                        "mime_type": export_mime,
                                        "file_size": file_size,
                                        "size": file_size,
                                    }
                                )
                        except Exception as e:
                             logger.error(f"❌ [Drive] Failed to process file in folder {f.get('name')}: {e}")
                             continue

                else:
                    # Download Content
                    content_bytes, export_mime, filename = self._download_file_content(service, file_meta)
                    
                    if content_bytes:
                        file_size = len(content_bytes)
                        
                        # Check if binary or text
                        if export_mime in self.BINARY_MIME_TYPES:
                            # Binary: Encode as base64 string
                            text_content = base64.b64encode(content_bytes).decode('ascii')
                        else:
                            # Text: Decode UTF-8
                            try:
                                text_content = content_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                text_content = content_bytes.decode('utf-8', errors='replace')
                            
                            # Remove null bytes that break PostgreSQL
                            text_content = text_content.replace('\x00', '')
                        
                        yield ConnectorDocument(
                            page_content=text_content,
                            metadata={
                                "source": "google_drive",
                                "title": filename,
                                "source_url": file_meta.get('webViewLink'),
                                "file_id": file_meta.get('id'),
                                "mime_type": export_mime,
                                "file_size": file_size,
                                "size": file_size,
                            }
                        )
                        logger.info(f"✅ [Drive] Processed: {filename} (as {export_mime}, {file_size} bytes)")
            except Exception as e:
                logger.error(f"❌ [Drive] Failed to process {item_id}: {e}")
                continue

        logger.info(f"📥 [DriveConnector] Ingestion stream ended")

    async def sync(self, user_id: str, integration_id: str) -> dict:
        """Async wrapper for sync."""
        return await run_in_threadpool(self._sync_implementation, user_id, integration_id)

    def _sync_implementation(self, user_id: str, integration_id: str) -> dict:
        """
        Synchronous full sync operation.
        """
        logger.info(f"🔄 [DriveSync] Starting sync for user {user_id}, integration {integration_id}")
        
        try:
            supabase = get_supabase()
            
            # 1. Fetch the integration record
            int_res = supabase.table("user_integrations").select("*").eq("id", integration_id).single().execute()
            if not int_res.data:
                raise ValueError(f"Integration {integration_id} not found")
            
            integration = int_res.data
            
            # 2. Initialize Google Drive service
            creds = self._get_credentials_by_integration(integration)
            service = build('drive', 'v3', credentials=creds)
            
            # 3. List files - include DOCX and PDF in query
            supported_mimes = [
                "mimeType='application/vnd.google-apps.document'",
                "mimeType contains 'text/'",
                "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'",
                "mimeType='application/pdf'"
            ]
            query = f"({' or '.join(supported_mimes)}) and trashed=false"
            
            results = service.files().list(
                q=query,
                fields="files(id, name, mimeType, webViewLink)",
                pageSize=20  # Increased limit to get more files
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"🔄 [DriveSync] Found {len(files)} files to process")
            
            # Import required services
            from services.embeddings import generate_embeddings_batch
            from worker.tasks import create_file_status, update_file_status
            
            # Create ingestion job for progress tracking
            job_id = None
            if files:
                job_result = supabase.table("ingestion_jobs").insert({
                    "user_id": user_id,
                    "provider": "drive",
                    "total_files": len(files),
                    "processed_files": 0,
                    "status": "processing",
                    "status_message": f"Syncing {len(files)} files from Google Drive"
                }).execute()
                if job_result.data:
                    job_id = job_result.data[0]["id"]
                    logger.info(f"🔄 [DriveSync] Created job {job_id} for tracking")
            
            total_chunks = 0
            processed_files = 0
            errors = []
            
            # 4. Process each file
            for file_meta in files:
                filename = file_meta['name']
                file_status_id = None
                
                # Create file status record for tracking
                if job_id:
                    file_status_id = create_file_status(supabase, job_id, user_id, filename, 0)
                
                try:
                    logger.info(f"🔄 [DriveSync] Processing: {filename} ({file_meta['mimeType']})")
                    
                    # Status: Uploading/Downloading
                    if file_status_id:
                        update_file_status(supabase, file_status_id, 
                            status="uploading", progress=10, message="Downloading from Drive...")
                    
                    # Download content (uses DocumentParser internally)
                    # FIX: Unpack tuple (content_bytes, mime_type, filename)
                    content_tuple = self._download_file_content(service, file_meta)
                    if not content_tuple or not content_tuple[0]:
                        logger.warning(f"⚠️ [DriveSync] No content from: {filename}")
                        if file_status_id:
                            update_file_status(supabase, file_status_id,
                                status="completed", progress=100, message="No content (empty)")
                        continue
                        
                    content_bytes, _, _ = content_tuple
                    
                    # Status: Processing
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="processing", progress=25, message="Extracting content...")
                    
                    # FIX: Decode bytes to string
                    try:
                        content = content_bytes.decode('utf-8')
                    except UnicodeDecodeError:
                        content = content_bytes.decode('utf-8', errors='replace')
                    
                    # CRITICAL: Remove null bytes that break PostgreSQL text fields
                    # Error: '22P05' - '\u0000 cannot be converted to text'
                    content = content.replace('\x00', '')
                        
                    if not content or not content.strip():
                        logger.warning(f"⚠️ [DriveSync] No content from: {filename}")
                        if file_status_id:
                            update_file_status(supabase, file_status_id,
                                status="completed", progress=100, message="No content (empty)")
                        continue
                    
                    # Chunk the content
                    chunks = self.text_splitter.split_text(content)
                    if not chunks:
                        logger.warning(f"⚠️ [DriveSync] No chunks from: {filename}")
                        if file_status_id:
                            update_file_status(supabase, file_status_id,
                                status="completed", progress=100, message="No chunks extracted")
                        continue
                    
                    logger.info(f"🔄 [DriveSync] File '{filename}': {len(chunks)} chunks")
                    
                    # Status: Embedding
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="embedding", progress=50, message=f"Generating embeddings for {len(chunks)} chunks...",
                            chunks_total=len(chunks))
                    
                    # Generate embeddings in batch
                    embeddings = generate_embeddings_batch(chunks)
                    
                    # =====================================================
                    # STEP A: Insert Parent Document into `documents` table
                    # =====================================================
                    parent_doc_data = {
                        "user_id": user_id,
                        "title": file_meta['name'],
                        "source_type": "drive",  # Matches the enum value
                        "source_url": file_meta.get('webViewLink', ''),
                        "metadata": {
                            "file_id": file_meta['id'],
                            "mime_type": file_meta.get('mimeType', 'unknown')
                        },
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    doc_res = supabase.table("documents").insert(parent_doc_data).execute()
                    if not doc_res.data:
                        logger.error(f"❌ [DriveSync] Failed to create parent document for {file_meta['name']}")
                        errors.append(f"DB insert failed: {file_meta['name']}")
                        continue
                    
                    parent_doc_id = doc_res.data[0]['id']
                    logger.info(f"✅ [DriveSync] Created parent document: {parent_doc_id}")
                    
                    # =====================================================
                    # STEP B: Insert Chunks into `document_chunks` table
                    # BATCHED: Insert 50 chunks at a time to prevent DB timeouts
                    # =====================================================
                    DB_BATCH_SIZE = 50
                    chunk_records = []
                    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                        if embedding is None:
                            logger.warning(f"⚠️ [DriveSync] Skipping empty chunk {i} for {file_meta['name']}")
                            continue
                            
                        chunk_records.append({
                            "document_id": parent_doc_id,  # FK to documents
                            "content": chunk_text,
                            "embedding": embedding,
                            "chunk_index": i
                            # Note: NO user_id or metadata here - they live on parent document
                        })
                    
                    # Insert chunks in batches to prevent statement timeout
                    if chunk_records:
                        inserted_count = 0
                        for batch_start in range(0, len(chunk_records), DB_BATCH_SIZE):
                            batch = chunk_records[batch_start:batch_start + DB_BATCH_SIZE]
                            try:
                                chunk_res = supabase.table("document_chunks").insert(batch).execute()
                                if chunk_res.data:
                                    inserted_count += len(batch)
                                    logger.debug(f"📦 [DriveSync] Inserted batch {batch_start//DB_BATCH_SIZE + 1}: {len(batch)} chunks")
                            except Exception as batch_err:
                                logger.error(f"❌ [DriveSync] Batch insert failed for {filename}: {batch_err}")
                                continue
                        
                        if inserted_count > 0:
                            total_chunks += inserted_count
                            processed_files += 1
                            
                            # Status: Completed
                            if file_status_id:
                                update_file_status(supabase, file_status_id,
                                    status="completed", progress=100, message="Complete",
                                    chunks_processed=inserted_count, document_id=str(parent_doc_id))
                            
                            # Update job progress
                            if job_id:
                                supabase.table("ingestion_jobs").update({
                                    "processed_files": processed_files,
                                    "status_message": f"Processed {processed_files}/{len(files)} files"
                                }).eq("id", job_id).execute()
                            
                            logger.info(f"✅ [DriveSync] Inserted {inserted_count} chunks for {filename}")
                        else:
                            if file_status_id:
                                update_file_status(supabase, file_status_id,
                                    status="failed", progress=0, error="No chunks inserted")
                            logger.error(f"❌ [DriveSync] Failed to insert any chunks for {filename}")
                            errors.append(f"Chunk insert failed: {filename}")
                        
                except Exception as e:
                    logger.error(f"❌ [DriveSync] Error processing {filename}: {e}")
                    if file_status_id:
                        update_file_status(supabase, file_status_id,
                            status="failed", progress=0, error=str(e))
                    errors.append(f"{filename}: {str(e)}")
                    # Don't fail the whole sync for one file
                    continue
            
            # 5. Update job to completed
            if job_id:
                final_status = "completed" if processed_files > 0 else "failed"
                supabase.table("ingestion_jobs").update({
                    "status": final_status,
                    "processed_files": processed_files,
                    "progress": 100,
                    "status_message": f"Synced {processed_files} files, {total_chunks} chunks"
                }).eq("id", job_id).execute()
            
            # 6. Update last_sync_at
            supabase.table("user_integrations").update({
                "last_sync_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", integration_id).execute()
            
            logger.info(f"🔄 [DriveSync] ✅ Sync complete: {processed_files} files, {total_chunks} chunks")
            if errors:
                logger.warning(f"🔄 [DriveSync] ⚠️ {len(errors)} errors: {errors}")
            
            return {
                "status": "success",
                "files_processed": processed_files,
                "chunks_created": total_chunks,
                "errors": errors,
                "job_id": job_id
            }
        except Exception as e:
            logger.error(f"❌ [DriveSync] Sync failed globally: {e}")
            # Mark job as failed if exists
            if 'job_id' in locals() and job_id:
                supabase.table("ingestion_jobs").update({
                    "status": "failed",
                    "error_message": str(e)
                }).eq("id", job_id).execute()
            raise e
