"""
Google Drive Connector

Connects to Google Drive API to fetch and sync files.
Supports listing, ingestion, and background sync with chunking/embedding.
"""

import logging
from typing import List, Optional
from datetime import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from langchain_text_splitters import RecursiveCharacterTextSplitter
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings

logger = logging.getLogger(__name__)


class DriveConnector(BaseConnector):
    """
    Google Drive connector with full sync capabilities.
    
    Supports:
    - OAuth token refresh
    - File listing with folder expansion
    - Background sync with chunking and embedding
    """
    
    # Text splitter for chunking documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
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
        """
        creds = Credentials(
            token=integration['access_token'],
            refresh_token=integration.get('refresh_token'),
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
                
                # Update database with new token
                supabase = get_supabase()
                supabase.table("user_integrations").update({
                    "access_token": creds.token,
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
            fields="files(id, name, mimeType, iconLink, thumbnailLink)",
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

    async def ingest(self, user_id: str, item_ids: List[str]) -> List[ConnectorDocument]:
        """Download and parse selected files from Drive."""
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        documents = []

        for item_id in item_ids:
            try:
                file_meta = service.files().get(
                    fileId=item_id, 
                    fields="id, name, mimeType, webViewLink"
                ).execute()
                
                items_to_process = []
                if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                    results = service.files().list(
                        q=f"'{item_id}' in parents and trashed=false",
                        fields="files(id, name, mimeType, webViewLink)"
                    ).execute()
                    items_to_process = results.get('files', [])
                else:
                    items_to_process = [file_meta]

                for item in items_to_process:
                    content = self._download_file_content(service, item)
                    if content and content.strip():
                        documents.append(ConnectorDocument(
                            page_content=content,
                            metadata={
                                "source": "google_drive",
                                "title": item['name'],
                                "source_url": item.get('webViewLink', ''),
                                "file_id": item['id']
                            }
                        ))

            except Exception as e:
                logger.error(f"Error processing item {item_id}: {e}")
                continue

        return documents

    def _download_file_content(self, service, file_meta: dict) -> Optional[str]:
        """Download file content based on MIME type."""
        mime_type = file_meta['mimeType']
        
        try:
            if mime_type == 'application/vnd.google-apps.document':
                return service.files().export_media(
                    fileId=file_meta['id'], 
                    mimeType='text/plain'
                ).execute().decode('utf-8')
            elif 'text' in mime_type:
                return service.files().get_media(
                    fileId=file_meta['id']
                ).execute().decode('utf-8')
            elif mime_type == 'application/pdf':
                logger.info(f"Skipping PDF: {file_meta['name']}")
                return None
            else:
                logger.info(f"Skipping unsupported type: {mime_type}")
                return None
        except Exception as e:
            logger.error(f"Error downloading {file_meta['name']}: {e}")
            return None

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
        
        # 3. List files (limit to 10 text/gdoc files for safety)
        results = service.files().list(
            q="(mimeType='application/vnd.google-apps.document' or mimeType contains 'text/') and trashed=false",
            fields="files(id, name, mimeType, webViewLink)",
            pageSize=10
        ).execute()
        
        files = results.get('files', [])
        logger.info(f"🔄 [DriveSync] Found {len(files)} files to process")
        
        # Import embedding service
        from services.embeddings import generate_embeddings_batch
        
        total_chunks = 0
        processed_files = 0
        
        # 4. Process each file
        for file_meta in files:
            try:
                # Download content
                content = self._download_file_content(service, file_meta)
                if not content or not content.strip():
                    continue
                
                # Chunk the content
                chunks = self.text_splitter.split_text(content)
                if not chunks:
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
                    logger.error(f"🔄 [DriveSync] Failed to create parent document for {file_meta['name']}")
                    continue
                
                parent_doc_id = doc_res.data[0]['id']
                logger.info(f"🔄 [DriveSync] Created parent document: {parent_doc_id}")
                
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
                    supabase.table("document_chunks").insert(chunk_records).execute()
                    total_chunks += len(chunk_records)
                    processed_files += 1
                    
            except Exception as e:
                logger.error(f"🔄 [DriveSync] Error processing {file_meta['name']}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 5. Update last_sync_at
        supabase.table("user_integrations").update({
            "last_sync_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }).eq("id", integration_id).execute()
        
        logger.info(f"🔄 [DriveSync] ✅ Sync complete: {processed_files} files, {total_chunks} chunks")
        
        return {
            "status": "success",
            "files_processed": processed_files,
            "chunks_created": total_chunks
        }
