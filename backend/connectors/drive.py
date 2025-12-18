import os
from typing import List
from google.oauth2 import service_account
from googleapiclient.discovery import build
from .base import BaseConnector, ConnectorDocument

class DriveConnector(BaseConnector):
    def __init__(self):
        self.creds_path = "credentials/service_account.json"
        if not os.path.exists(self.creds_path):
            print(f"WARNING: Service Account JSON not found at {self.creds_path}")
            self.creds = None
        else:
            self.creds = service_account.Credentials.from_service_account_file(
                self.creds_path, scopes=['https://www.googleapis.com/auth/drive.readonly']
            )

    async def process(self, source: str, **kwargs) -> List[ConnectorDocument]:
        if not self.creds:
            raise ValueError("Service Account credentials missing in backend/credentials/service_account.json")

        service = build('drive', 'v3', credentials=self.creds)
        documents = []

        try:
            # 1. Get File Metadata (check if exists and get type)
            try:
                file_meta = service.files().get(fileId=source, fields="id, name, mimeType, webViewLink").execute()
            except Exception:
                raise ValueError(f"Drive ID not found or not shared with Service Account: {source}")

            # 2. Determine items to process
            items_to_process = []
            if file_meta['mimeType'] == 'application/vnd.google-apps.folder':
                # List files in folder
                results = service.files().list(
                    q=f"'{source}' in parents and trashed=false",
                    fields="files(id, name, mimeType, webViewLink)"
                ).execute()
                items_to_process = results.get('files', [])
            else:
                # It's a single file
                items_to_process = [file_meta]

            # 3. Process Items
            for item in items_to_process:
                content = ""
                try:
                    if item['mimeType'] == 'application/vnd.google-apps.document':
                        content = service.files().export_media(fileId=item['id'], mimeType='text/plain').execute().decode('utf-8')
                    elif 'text' in item['mimeType']:
                        content = service.files().get_media(fileId=item['id']).execute().decode('utf-8')
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
