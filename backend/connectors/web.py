from typing import List, Optional
from .base import BaseConnector, ConnectorDocument, ConnectorItem
import requests
from bs4 import BeautifulSoup

class WebConnector(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        # Web connector is public/open, always authorized
        return True

    async def list_items(self, user_id: str, parent_id: Optional[str] = None) -> List[ConnectorItem]:
        # MVP: Web connector is stateless, the user provides the URL at ingest time.
        # Future: Could list perviously crawled URLs from DB.
        return []

    async def ingest(self, user_id: str, item_ids: List[str]) -> List[ConnectorDocument]:
        # For Web, 'item_ids' are actually URLs
        documents = []
        for url in item_ids:
            try:
                # Basic scraping MVP
                resp = requests.get(url, timeout=10)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Simple extraction
                title = soup.title.string if soup.title else url
                
                # Remove scripts and styles
                for script in soup(["script", "style"]):
                    script.decompose()
                    
                text = soup.get_text()
                
                # Clean whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                if text:
                    documents.append(ConnectorDocument(
                        page_content=text,
                        metadata={
                            "source": "web",
                            "title": title,
                            "source_url": url,
                        }
                    ))
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                
        return documents
