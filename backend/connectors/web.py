import requests
from bs4 import BeautifulSoup
from typing import List, Any, Dict
from .base import BaseConnector, ConnectorDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

class WebConnector(BaseConnector):
    async def process(self, source: str, **kwargs) -> List[ConnectorDocument]:
        """
        Crawl a URL, clean HTML, and return chunks.
        source: URL string
        kwargs: can include 'metadata'
        """
        try:
            # Fake User-Agent to avoid 403 Forbidden on some sites
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            
            # Using sync requests for now (could be async with aiohttp later)
            response = requests.get(source, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove junk elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
                script.decompose()
                
            text = soup.get_text(separator='\n')
            
            # Basic cleaning to remove excess whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks_text = (phrase.strip() for line in lines for phrase in line.split("  "))
            clean_text = '\n'.join(chunk for chunk in chunks_text if chunk)
            
            if not clean_text:
                return []
                
            # Chunking (Applying same strategy as FileConnector for now)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            
            # Prepare metadata
            base_metadata = kwargs.get("metadata", {})
            base_metadata["source"] = "web"
            base_metadata["url"] = source
            
            docs = text_splitter.create_documents(
                texts=[clean_text],
                metadatas=[base_metadata]
            )
            
            return [ConnectorDocument(page_content=d.page_content, metadata=d.metadata) for d in docs]
            
        except Exception as e:
            raise ValueError(f"Failed to crawl URL {source}: {str(e)}")
