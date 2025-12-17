import tempfile
import os
import shutil
from fastapi import UploadFile
from abc import ABC, abstractmethod
from unstructured.partition.auto import partition

class BaseParser(ABC):
    @abstractmethod
    async def parse(self, file: UploadFile) -> str:
        pass

class UnstructuredParser(BaseParser):
    async def parse(self, file: UploadFile) -> str:
        # Create a temporary file to save the uploaded stream
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        try:
            # Magic happens here: Unstructured detects file type and parses it
            elements = partition(filename=tmp_path)
            # Combine all text elements into one string
            text = "\n\n".join([str(el) for el in elements])
            return text
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

def get_parser(filename: str) -> BaseParser:
    # For now, we use Unstructured for everything.
    # In the future, we can switch based on extension (e.g., if filename.endswith('.pdf')...)
    return UnstructuredParser()