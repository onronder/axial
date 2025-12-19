import os
from typing import List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .base import BaseConnector, ConnectorDocument, ConnectorItem
from core.db import get_supabase
from core.config import settings

class DriveConnector(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        supabase = get_supabase()
        res = supabase.table("user_integrations").select("id").eq("user_id", user_id).eq("provider", "google_drive").execute()
        return len(res.data) > 0

    def _get_credentials(self, user_id: str) -> Credentials:
        supabase = get_supabase()
        res = supabase.table("user_integrations").select("*").eq("user_id", user_id).eq("provider", "google_drive").execute()
        
        if not res.data:
             raise ValueError("Google Drive not connected for this user.")
             
        integration = res.data[0]
        return Credentials(
            token=integration['access_token'],
            refresh_token=integration.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        
        # If parent_id is None, start at 'root' but we might optionally handle 'sharedWithMe' later
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
        creds = self._get_credentials(user_id)
        service = build('drive', 'v3', credentials=creds)
        documents = []

        for item_id in item_ids:
            try:
                file_meta = service.files().get(fileId=item_id, fields="id, name, mimeType, webViewLink").execute()
                
                # Recursive Folder Support Could Go Here (MVP: Flat List selection usually implies Files, but if Folder selected we could recurse)
                # For this step, we assume the UI passes specific files or we flatten folders. 
                # Let's handle simple single-level file or folder expansion.

                items_to_process = []
                if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                     # Simple shallow expansion for MVP (Deep recursion risks timeout)
                    results = service.files().list(
                        q=f"'{item_id}' in parents and trashed=false",
                        fields="files(id, name, mimeType, webViewLink)"
                    ).execute()
                    items_to_process = results.get('files', [])
                else:
                    items_to_process = [file_meta]

                for item in items_to_process:
                    content = ""
                    try:
                        if item['mimeType'] == 'application/vnd.google-apps.document':
                            content = service.files().export_media(fileId=item['id'], mimeType='text/plain').execute().decode('utf-8')
                        elif 'text' in item['mimeType']:
                            content = service.files().get_media(fileId=item['id']).execute().decode('utf-8')
                        elif item['mimeType'] == 'application/pdf':
                            print(f"Skipping PDF for MVP: {item['name']}")
                            continue
                        else:
                            print(f"Skipping unsupported type: {item['mimeType']}")
                            continue # Skip
                        
                        if content.strip():
                            documents.append(ConnectorDocument(
                                page_content=content,
                                metadata={
                                    "source": "drive",
                                    "title": item['name'],
                                    "source_url": item.get('webViewLink', ''),
                                    "file_id": item['id']
                                }
                            ))
                    except Exception as e:
                        print(f"Error reading file {item['name']}: {e}")
                        continue

            except Exception as e:
                print(f"Error processing item {item_id}: {e}")
                continue

        return documents
