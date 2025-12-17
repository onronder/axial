import time
import os
import requests
import logging
import random
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

def extract_text(filepath):
    """Extracts text from PDF or TXT files."""
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    try:
        content = ""
        if ext == '.pdf':
            if PyPDF2:
                with open(filepath, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            content += extracted + "\n"
            else:
                logger.error("PyPDF2 not installed, cannot extract PDF.")
                return None
        elif ext == '.txt':
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            return None
        
        return content.strip()
    except Exception as e:
        logger.error(f"Error extracting text from {filepath}: {e}")
        return None

def send_to_backend(filename, content, max_retries=5):
    """
    Sends extracted content to the backend with exponential backoff.
    """
    payload = {
        "client_id": Config.CLIENT_ID,
        "filename": filename,
        "content": content,
        "metadata": {"source": "desktop_agent"}
    }
    headers = {
        "X-API-KEY": Config.API_KEY,
        "Content-Type": "application/json"
    }
    
    retry_delay = 1  # Start with 1 second
    
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(Config.BACKEND_URL, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"Successfully sent {filename}. Response: {response.json()}")
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Attempt {attempt}/{max_retries} failed to send {filename}: {e}")
            
            if attempt < max_retries:
                # Exponential backoff with jitter
                sleep_time = retry_delay + random.uniform(0, 1)
                logger.info(f"Retrying in {sleep_time:.2f} seconds...")
                time.sleep(sleep_time)
                retry_delay *= 2
            else:
                logger.error(f"Max retries reached. Failed to send {filename}.")
                return False

class FolderEventHandler(FileSystemEventHandler):
    """Handles file system events."""
    def on_created(self, event):
        if event.is_directory:
            return
        
        filename = os.path.basename(event.src_path)
        
        # Ignore temp files
        if filename.startswith('~') or filename.startswith('.') or filename.endswith('.tmp'):
            return
            
        logger.info(f"New file detected: {filename}")
        
        # Allow some time for file write to complete (debounce/finish writing)
        time.sleep(1)
        
        content = extract_text(event.src_path)
        if content:
            logger.info(f"Extracted {len(content)} characters from {filename}")
            send_to_backend(filename, content)
        else:
            logger.warning(f"No content extracted or unsupported file type: {filename}")

def main():
    if not os.path.exists(Config.WATCHED_FOLDER):
        os.makedirs(Config.WATCHED_FOLDER)
        logger.info(f"Created watched folder: {Config.WATCHED_FOLDER}")
    
    event_handler = FolderEventHandler()
    observer = Observer()
    observer.schedule(event_handler, Config.WATCHED_FOLDER, recursive=False)
    
    logger.info(f"Agent started. Watching: {Config.WATCHED_FOLDER}")
    logger.info("Press Ctrl+C to stop.")
    
    # Compilation Note:
    # To compile this script with PyInstaller:
    # 1. Install pyinstaller: pip install pyinstaller
    # 2. Run: pyinstaller --onefile --name agent --hidden-import=config agent/main.py
    # 3. Use --add-data if config.py needs to be bundled differently or rely on env vars in the wild.
    
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("Agent stopped.")
    observer.join()

if __name__ == "__main__":
    main()
