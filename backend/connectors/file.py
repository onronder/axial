from typing import List, Any
from fastapi import UploadFile
from .base import BaseConnector, ConnectorDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tempfile
import os
import shutil
from unstructured.partition.auto import partition

class FileConnector(BaseConnector):
    async def authorize(self, user_id: str) -> bool:
        return True

    async def list_items(self, user_id: str, parent_id: Any = None) -> List[Any]:
        return []

    async def ingest(self, user_id: str, item_ids: List[str]) -> List[ConnectorDocument]:
        raise NotImplementedError("FileConnector uses process() with UploadFile, not ingest() with IDs.")

    async def process(self, source: UploadFile, **kwargs) -> List[ConnectorDocument]:
        """
        Process an UploadFile: Parse content and chunk it.
        kwargs can contain 'metadata' dict to merge.
        """
        # 1. Parse File
        content = await self._parse_file(source)
        
        if not content:
            return []

        # 2. Chunk Content
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Prepare metadata
        base_metadata = kwargs.get("metadata", {})
        base_metadata["filename"] = source.filename
        
        docs = text_splitter.create_documents(
            texts=[content],
            metadatas=[base_metadata]
        )
        
        # 3. Convert to ConnectorDocument
        connector_docs = []
        for doc in docs:
            connector_docs.append(ConnectorDocument(
                page_content=doc.page_content,
                metadata=doc.metadata
            ))
            
        return connector_docs

    async def _parse_file(self, file: UploadFile) -> str:
        """
        Internal method to parse file using unstructured.
        Logic moved from core/parsers.py
        """
        # Save to a temporary file because unstructured needs a file path
        suffix = os.path.splitext(file.filename)[1]
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            tmp_path = tmp_file.name

        try:
            # Partition the file (auto-detects format)
            elements = partition(filename=tmp_path)
            # Join element text
            text = "\n\n".join([str(el) for el in elements])
            return text
        except Exception as e:
            print(f"Error parsing file {file.filename}: {e}")
            raise e
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
