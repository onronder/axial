import time
import os
import requests
import logging
import mimetypes
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

def send_to_backend(filepath):
    """Upload file via presigned URL flow and trigger ingestion."""
    filename = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"
    
    # Prepare metadata
    meta = {
        "source": "desktop_agent",
        "client_id": Config.CLIENT_ID,
        "filename": filename
    }
    
    headers = {
        "X-API-KEY": Config.API_KEY
        # Do NOT set Content-Type here, requests sets it to multipart/form-data automatically
    }
    
    try:
        upload_payload = {
            "filename": filename,
            "file_type": mime_type,
            "file_size": file_size,
        }
        upload_res = requests.post(
            f"{Config.BACKEND_URL}/uploads/upload-url",
            json=upload_payload,
            headers=headers,
            timeout=30,
        )
        upload_res.raise_for_status()
        upload_data = upload_res.json()

        signed_url = upload_data["upload_url"]
        storage_path = upload_data["storage_path"]

        with open(filepath, "rb") as f:
            put_headers = {"Content-Type": mime_type}
            put_res = requests.put(signed_url, data=f, headers=put_headers, timeout=300)
            put_res.raise_for_status()

        reference_payload = {
            "storage_path": storage_path,
            "filename": filename,
            "file_size": file_size,
            "metadata": meta,
        }
        response = requests.post(
            f"{Config.BACKEND_URL}/uploads/file/reference",
            json=reference_payload,
            headers=headers,
            timeout=30,
        )
        if response.status_code not in (200, 202):
            logger.error(f"Failed to send {filename}. Status: {response.status_code}")
            logger.error(f"Server Response: {response.text}")
        response.raise_for_status()
        logger.info(f"Successfully sent {filename}. Response: {response.json()}")
    except Exception as e:
        logger.error(f"Failed to send {filename}: {e}")

class FolderEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        if filename.startswith('.') or filename.endswith('.tmp'):
            return
            
        logger.info(f"New file detected: {filename}")
        time.sleep(1) # Wait for write to finish
        send_to_backend(event.src_path)

def main():
    if not os.path.exists(Config.WATCHED_FOLDER):
        os.makedirs(Config.WATCHED_FOLDER)
    
    event_handler = FolderEventHandler()
    observer = Observer()
    observer.schedule(event_handler, Config.WATCHED_FOLDER, recursive=False)
    
    logger.info(f"Agent started (Dumb Pipe Mode). Watching: {Config.WATCHED_FOLDER}")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
