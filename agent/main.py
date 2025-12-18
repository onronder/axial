import time
import os
import requests
import logging
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

def send_to_backend(filepath):
    """Streams raw file to backend."""
    filename = os.path.basename(filepath)
    
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
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f, 'application/octet-stream')}
            data = {'metadata': json.dumps(meta)}
            
            response = requests.post(Config.BACKEND_URL, files=files, data=data, headers=headers, timeout=300)
            if response.status_code != 200:
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