"""
Google Drive Connector

Connects to Google Drive API to fetch and sync files.
Supports listing, ingestion, and background sync with chunking/embedding.
File parsing is delegated to the centralized DocumentParser service.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from langchain.text_splitter import RecursiveCharacterTextSplitter
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings
from services.parsers import DocumentParser
from core.security import decrypt_token, encrypt_token

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
    
    # Text splitter for chunking documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # =========================================================================
    # RICH EXPORT: Map Google Native types to structured formats
    # =========================================================================
    # Google Docs -> DOCX (preserves headers/formatting)
    # Google Sheets -> CSV (preserves row/column structure)
    # Google Slides -> PDF (preserves slide separation)
    EXPORT_MIME_TYPES = {
        "application/vnd.google-apps.document": {
            "export_mime": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "extension": ".docx",
        },
        "application/vnd.google-apps.spreadsheet": {
            "export_mime": "text/csv",
            "extension": ".csv",
        },
        "application/vnd.google-apps.presentation": {
            "export_mime": "application/pdf",
            "extension": ".pdf",
        },
    }
    
    # Supported MIME types (delegated to DocumentParser for actual extraction)
    SUPPORTED_MIME_TYPES = {
        'application/vnd.google-apps.document': 'gdoc',
        'application/vnd.google-apps.spreadsheet': 'gsheet',
        'application/vnd.google-apps.presentation': 'gslides',
        'text/plain': 'text',
        'text/markdown': 'text',
        'text/csv': 'text',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'docx',
        'application/pdf': 'pdf',
    }
    
    async def authorize(self, user_id: str) -> bool:
        """Check if user has connected Google Drive."""
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
        Handles token refresh if needed.
        Decrypts tokens before use (supports legacy plain-text tokens).
        """
        # Decrypt tokens (handles both encrypted and legacy plain-text)
        access_token = decrypt_token(integration['access_token']) if integration.get('access_token') else None
        refresh_token = decrypt_token(integration.get('refresh_token')) if integration.get('refresh_token') else None
        
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )
        
        # Refresh if expired
        if creds.expired or not creds.valid:
            if creds.refresh_token:
                logger.info(f"🔄 [DriveConnector] Token expired, refreshing...")
                creds.refresh(Request())
                
                # Update database with new encrypted token
                supabase = get_supabase()
                supabase.table("user_integrations").update({
                    "access_token": encrypt_token(creds.token),
                    "expires_at": creds.expiry.isoformat() if creds.expiry else None,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", integration["id"]).execute()
                
                logger.info(f"🔄 [DriveConnector] ✅ Token refreshed and saved")
            else:
                raise ValueError("Token expired and no refresh token available")
        
        return creds

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
        """List files and folders in Google Drive."""
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        
        query_parent = parent_id if parent_id else 'root'
        
        results = service.files().list(
            q=f"'{query_parent}' in parents and trashed=false",
            fields="files(id, name, mimeType, iconLink, thumbnailLink, size)",
            orderBy="folder,name"
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

    def ingest(self, config: Dict[str, Any]) -> List[ConnectorDocument]:
        """
        Synchronous ingestion with RICH EXPORT for Google native types.
        Config keys: 'credentials' (optional), 'item_ids', 'user_id'
        
        Returns documents with content_bytes (not text) so factory can process correctly.
        """
        user_id = config.get("user_id")
        item_ids = config.get("item_ids", [])
        credentials_data = config.get("credentials")
        
        logger.info(f"📥 [DriveConnector] Starting ingestion for {len(item_ids)} items")

        # 1. Hybrid Credential Resolution
        if credentials_data:
            # Worker case: Use passed decrypted credentials
            creds = Credentials(
                token=credentials_data.get('token') or credentials_data.get('access_token'),
                refresh_token=credentials_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        elif user_id:
            # API case: Fallback to DB lookup
            creds = self._get_credentials(user_id)
        else:
            raise ValueError("No credentials or user_id provided for Drive ingestion")

        # 2. Build Service & Process
        service = build('drive', 'v3', credentials=creds)
        documents = []

        for item_id in item_ids:
            try:
                # Fetch metadata
                file_meta = service.files().get(
                    fileId=item_id, 
                    fields="id, name, mimeType, webViewLink, size"
                ).execute()
                
                # Handle folders recursively
                if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                    folder_files = self._get_all_files_recursive(service, item_id)
                    logger.info(f"📁 [DriveConnector] Found {len(folder_files)} files in folder: {file_meta['name']}")
                    for f in folder_files:
                        content_bytes, export_mime, filename = self._download_file_content(service, f)
                        if content_bytes:
                            # Calculate accurate size from downloaded bytes (important for rich exports)
                            file_size = len(content_bytes)
                            
                            # Decode bytes to text for page_content
                            try:
                                text_content = content_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                text_content = content_bytes.decode('utf-8', errors='replace')
                            
                            documents.append(ConnectorDocument(
                                page_content=text_content,
                                metadata={
                                    "source": "google_drive",
                                    "title": filename,
                                    "source_url": f.get('webViewLink'),
                                    "file_id": f.get('id'),
                                    "mime_type": export_mime,  # CRITICAL: Use exported mime_type
                                    "file_size": file_size,    # CRITICAL: Store accurate size
                                    "size": file_size,         # Alias for frontend
                                }
                            ))
                else:
                    # Download Content (returns tuple now)
                    content_bytes, export_mime, filename = self._download_file_content(service, file_meta)
                    
                    if content_bytes:
                        # Calculate accurate size from downloaded bytes
                        file_size = len(content_bytes)
                        
                        # Decode bytes to text for page_content
                        try:
                            text_content = content_bytes.decode('utf-8')
                        except UnicodeDecodeError:
                            text_content = content_bytes.decode('utf-8', errors='replace')
                        
                        documents.append(ConnectorDocument(
                            page_content=text_content,
                            metadata={
                                "source": "google_drive",
                                "title": filename,
                                "source_url": file_meta.get('webViewLink'),
                                "file_id": file_meta.get('id'),
                                "mime_type": export_mime,  # CRITICAL: Use exported mime_type
                                "file_size": file_size,    # CRITICAL: Store accurate size
                                "size": file_size,         # Alias for frontend
                            }
                        ))
                        logger.info(f"✅ [Drive] Processed: {filename} (as {export_mime}, {file_size} bytes)")
            except Exception as e:
                logger.error(f"❌ [Drive] Failed to process {item_id}: {e}")
                continue

        logger.info(f"📥 [DriveConnector] Completed ingestion: {len(documents)} documents")
        return documents

    def _get_all_files_recursive(self, service, folder_id: str, max_depth: int = 10) -> List[dict]:
        """
        Recursively get all files within a folder and its subfolders.
        
        Args:
            service: Google Drive API service
            folder_id: The folder ID to search
            max_depth: Maximum recursion depth (prevents infinite loops)
            
        Returns:
            List of file metadata dicts (excludes folders)
        """
        if max_depth <= 0:
            logger.warning(f"⚠️ Max depth reached for folder {folder_id}")
            return []
            
        files = []
        page_token = None
        
        while True:
            try:
                results = service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="nextPageToken, files(id, name, mimeType, webViewLink)",
                    pageSize=100,
                    pageToken=page_token
                ).execute()
                
                items = results.get('files', [])
                
                for item in items:
                    if item['mimeType'] == 'application/vnd.google-apps.folder':
                        # Recurse into subfolder
                        subfolder_files = self._get_all_files_recursive(
                            service, item['id'], max_depth - 1
                        )
                        files.extend(subfolder_files)
                    else:
                        # It's a file, add if supported (including Google native types)
                        mime = item['mimeType']
                        if DocumentParser.is_supported(mime) or mime in self.EXPORT_MIME_TYPES:
                            files.append(item)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                logger.error(f"❌ Error listing folder {folder_id}: {e}")
                break
        
        return files

    def _download_file_content(self, service, file_meta: dict) -> tuple:
        """
        Download file content with RICH EXPORT for Google native types.
        
        Returns:
            Tuple of (content_bytes, export_mime_type, filename_with_ext)
            - content_bytes: Raw file bytes
            - export_mime_type: The MIME type of the exported format
            - filename_with_ext: Filename with correct extension
        
        Google Native Types:
        - Docs -> exported as DOCX (preserves headers/formatting)
        - Sheets -> exported as CSV (preserves structure)
        - Slides -> exported as PDF (preserves slides)
        """
        original_mime = file_meta['mimeType']
        file_name = file_meta.get('name', 'unknown')
        
        try:
            # ========== RICH EXPORT: Google Native Types ==========
            if original_mime in self.EXPORT_MIME_TYPES:
                export_config = self.EXPORT_MIME_TYPES[original_mime]
                export_mime = export_config["export_mime"]
                extension = export_config["extension"]
                
                # Export to rich format
                content_bytes = service.files().export_media(
                    fileId=file_meta['id'],
                    mimeType=export_mime
                ).execute()
                
                # Ensure filename has correct extension
                filename_with_ext = file_name
                if not file_name.endswith(extension):
                    filename_with_ext = f"{file_name}{extension}"
                
                logger.info(f"📄 [DriveConnector] Rich export {original_mime} → {export_mime}: {file_name}")
                return (content_bytes, export_mime, filename_with_ext)
            
            # ========== Standard Download: Non-Google Files ==========
            if DocumentParser.is_supported(original_mime):
                file_bytes = service.files().get_media(
                    fileId=file_meta['id']
                ).execute()
                
                logger.info(f"📄 [DriveConnector] Downloaded: {file_name} ({original_mime})")
                return (file_bytes, original_mime, file_name)
            
            # ========== Unsupported Type ==========
            logger.info(f"⏭️ Skipping unsupported type '{original_mime}': {file_name}")
            return (None, None, None)
                
        except Exception as e:
            logger.error(f"❌ Error downloading {file_name}: {e}")
            import traceback
            traceback.print_exc()
            return (None, None, None)

    async def sync(self, user_id: str, integration_id: str) -> dict:
        """
        Full sync operation: fetch files, chunk, embed, and store.
        
        Uses the correct relational schema:
        1. Insert parent document into `documents` table
        2. Insert chunks into `document_chunks` with FK to parent
        
        Args:
            user_id: The user's ID
            integration_id: The user_integrations record ID
            
        Returns:
            dict with sync statistics
        """
        logger.info(f"🔄 [DriveSync] Starting sync for user {user_id}, integration {integration_id}")
        
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
        
        # Import embedding service
        from services.embeddings import generate_embeddings_batch
        
        total_chunks = 0
        processed_files = 0
        errors = []
        
        # 4. Process each file
        for file_meta in files:
            try:
                logger.info(f"🔄 [DriveSync] Processing: {file_meta['name']} ({file_meta['mimeType']})")
                
                # Download content (uses DocumentParser internally)
                content = self._download_file_content(service, file_meta)
                if not content or not content.strip():
                    logger.warning(f"⚠️ [DriveSync] No content from: {file_meta['name']}")
                    continue
                
                # Chunk the content
                chunks = self.text_splitter.split_text(content)
                if not chunks:
                    logger.warning(f"⚠️ [DriveSync] No chunks from: {file_meta['name']}")
                    continue
                
                logger.info(f"🔄 [DriveSync] File '{file_meta['name']}': {len(chunks)} chunks")
                
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
                    "created_at": datetime.utcnow().isoformat()
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
                # =====================================================
                chunk_records = []
                for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
                    chunk_records.append({
                        "document_id": parent_doc_id,  # FK to documents
                        "content": chunk_text,
                        "embedding": embedding,
                        "chunk_index": i
                        # Note: NO user_id or metadata here - they live on parent document
                    })
                
                # Insert chunks
                if chunk_records:
                    chunk_res = supabase.table("document_chunks").insert(chunk_records).execute()
                    if chunk_res.data:
                        total_chunks += len(chunk_records)
                        processed_files += 1
                        logger.info(f"✅ [DriveSync] Inserted {len(chunk_records)} chunks for {file_meta['name']}")
                    else:
                        logger.error(f"❌ [DriveSync] Failed to insert chunks for {file_meta['name']}")
                        errors.append(f"Chunk insert failed: {file_meta['name']}")
                    
            except Exception as e:
                logger.error(f"❌ [DriveSync] Error processing {file_meta['name']}: {e}")
                errors.append(f"{file_meta['name']}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # 5. Update last_sync_at
        supabase.table("user_integrations").update({
            "last_sync_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", integration_id).execute()
        
        logger.info(f"🔄 [DriveSync] ✅ Sync complete: {processed_files} files, {total_chunks} chunks")
        if errors:
            logger.warning(f"🔄 [DriveSync] ⚠️ {len(errors)} errors: {errors}")
        
        return {
            "status": "success",
            "files_processed": processed_files,
            "chunks_created": total_chunks,
            "errors": errors
        }
