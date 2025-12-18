import os
from typing import List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from .base import BaseConnector, ConnectorDocument
from core.db import get_supabase
from core.config import settings

class DriveConnector(BaseConnector):
    def __init__(self):
        pass

    async def process(self, source: str, **kwargs) -> List[ConnectorDocument]:
        user_id = kwargs.get('user_id')
        if not user_id:
            raise ValueError("user_id is required for Drive Connector")

        # 1. Fetch Credentials from DB
        supabase = get_supabase()
        res = supabase.table("user_integrations").select("*").eq("user_id", user_id).eq("provider", "google_drive").execute()
        
        if not res.data:
             raise ValueError("Google Drive not connected for this user. Please connect in settings.")
             
        integration = res.data[0]
        
        # 2. Build Credentials Object
        creds = Credentials(
            token=integration['access_token'],
            refresh_token=integration.get('refresh_token'),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=['https://www.googleapis.com/auth/drive.readonly']
        )

        service = build('drive', 'v3', credentials=creds)
        documents = []

        try:
            # 3. Get File Metadata
            try:
                # Support both file_id and folder_id logic remains similar
                file_meta = service.files().get(fileId=source, fields="id, name, mimeType, webViewLink").execute()
            except Exception:
                raise ValueError(f"Drive ID not found or access denied: {source}")

            # 4. Determine items to process
            items_to_process = []
            if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                results = service.files().list(
                    q=f"'{source}' in parents and trashed=false",
                    fields="files(id, name, mimeType, webViewLink)"
                ).execute()
                items_to_process = results.get('files', [])
            else:
                items_to_process = [file_meta]

            # 5. Process Items
            for item in items_to_process:
                content = ""
                try:
                    if item['mimeType'] == 'application/vnd.google-apps.document':
                        content = service.files().export_media(fileId=item['id'], mimeType='text/plain').execute().decode('utf-8')
                    elif 'text' in item['mimeType']:
                        content = service.files().get_media(fileId=item['id']).execute().decode('utf-8')
                    elif item['mimeType'] == 'application/pdf':
                         # MVP: Skip PDF binary download for now unless we add pdf parsing
                         # Typically unrelated to OAuth change, but good to note.
                         print(f"Skipping PDF for MVP: {item['name']}")
                         continue
                    else:
                        print(f"Skipping unsupported type: {item['mimeType']} ({item['name']})")
                        continue
                    
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
            raise ValueError(f"Drive API Error: {str(e)}")

        return documents
