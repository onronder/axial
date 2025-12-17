from abc import ABC, abstractmethod
from fastapi import UploadFile
import tempfile
import os
import shutil
from unstructured.partition.auto import partition

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file: UploadFile) -> str:
        """Parses an UploadFile and returns the extracted text."""
        pass

class UnstructuredParser(BaseParser):
    async def parse(self, file: UploadFile) -> str:
        # Save to a temporary file because unstructured needs a file path or file-like object
        suffix = os.path.splitext(file.filename)[1]
        # Create a temp file
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
            raise e
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def get_parser(filename: str) -> BaseParser:
    """Factory to return the appropriate parser based on filename/extension."""
    return UnstructuredParser()
