"""
Enterprise-Grade Document Processor Factory

Context-Aware RAG chunking with format-specific strategies.
Supports: Code files, Markdown, PDF/DOCX/PPTX, CSV/Excel with metadata enrichment.
Implements "Router Pattern" for intelligent parsing selection.

Author: Axio Hub Team
"""

import io
import os
import re
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# LangChain imports
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language,
    MarkdownHeaderTextSplitter,
)

# Token counting
import tiktoken

# Third-party parsers
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

logger = logging.getLogger(__name__)
LLAMAPARSE_LOCK = threading.Lock()

# Initialize tiktoken encoder
try:
    TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
except Exception:
    TIKTOKEN_ENCODER = None
    logger.warning("tiktoken encoder not available")


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ProcessedChunk:
    """A single processed chunk with content and metadata."""
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    token_count: int = 0
    chunk_index: int = 0


@dataclass
class ProcessedDocument:
    """Result of processing a document."""
    chunks: List[ProcessedChunk]
    file_type: str
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# BASE PROCESSOR
# =============================================================================

class BaseProcessor(ABC):
    """Abstract base class for document processors."""
    
    @abstractmethod
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        """
        Process document content and return chunks with metadata.
        Prioritize file_path for memory efficiency if available.
        """
        pass
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Count tokens using tiktoken cl100k_base encoder."""
        if TIKTOKEN_ENCODER:
            return len(TIKTOKEN_ENCODER.encode(text))
        return len(text) // 4  # Fallback approximation

    def _load_content(self, content: Optional[bytes], file_path: Optional[str]) -> bytes:
        """Helper to ensure content is loaded as bytes."""
        if content is not None:
            return content
        if file_path:
            with open(file_path, "rb") as f:
                return f.read()
        raise ValueError("No content or file_path provided")


# =============================================================================
# TABLE PROCESSOR (CSV/Excel)
# =============================================================================

class TableProcessor(BaseProcessor):
    """
    Processor for structured tabular data (CSV, Excel).
    Efficiently processes large files using Pandas on disk.
    """
    
    MAX_ROWS = 5000

    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        if not pd:
            logger.error("[TableProcessor] Pandas not installed")
            return ProcessedDocument(chunks=[], file_type="table_error")

        ext = os.path.splitext(filename)[1].lower()

        try:
            # Determine source (file path preferred for memory efficiency)
            source = file_path if file_path else io.BytesIO(content)

            if ext == ".csv":
                df = pd.read_csv(source, nrows=self.MAX_ROWS)
            elif ext in [".xlsx", ".xls"]:
                df = pd.read_excel(source, nrows=self.MAX_ROWS)
            else:
                return ProcessedDocument(chunks=[], file_type="unsupported_table")

            # Drop empty rows/cols
            df.dropna(how='all', inplace=True)
            df.fillna("", inplace=True)

            # Convert to text representation
            text_rows = []
            columns = df.columns.tolist()

            for idx, row in df.iterrows():
                row_parts = []
                for col in columns:
                    val = str(row[col]).strip()
                    if val:
                        row_parts.append(f"{col}: {val}")
                if row_parts:
                    text_rows.append(f"Row {idx+1}: " + " | ".join(row_parts))

            full_text = "\n".join(text_rows)

            # Chunking
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=150,
                separators=["\n"]
            )
            raw_chunks = splitter.split_text(full_text)

            chunks = []
            total_tokens = 0

            for i, chunk_text in enumerate(raw_chunks):
                contextualized = f"[File: {filename}] [Type: {ext.lstrip('.')}]\n{chunk_text}"
                token_count = self.count_tokens(contextualized)
                total_tokens += token_count

                chunks.append(ProcessedChunk(
                    content=contextualized,
                    metadata={
                        "file_type": "table",
                        "format": ext,
                        "filename": filename,
                        "rows": len(df)
                    },
                    token_count=token_count,
                    chunk_index=i
                ))

            logger.info(f"[TableProcessor] {filename}: {len(chunks)} chunks from {len(df)} rows")
            return ProcessedDocument(
                chunks=chunks,
                file_type="table",
                total_tokens=total_tokens,
                metadata={"rows": len(df), "columns": len(columns)}
            )

        except Exception as e:
            logger.error(f"[TableProcessor] Failed to process {filename}: {e}")
            return ProcessedDocument(chunks=[], file_type="table_error")


# =============================================================================
# PRESENTATION PROCESSOR (PPTX)
# =============================================================================

class PresentationProcessor(BaseProcessor):
    """Processor for PowerPoint presentations."""

    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        if not Presentation:
            logger.error("[PresentationProcessor] python-pptx not installed")
            return ProcessedDocument(chunks=[], file_type="pptx_error")

        try:
            source = file_path if file_path else io.BytesIO(content)
            prs = Presentation(source)
            chunks = []
            total_tokens = 0

            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

            for i, slide in enumerate(prs.slides):
                slide_num = i + 1
                slide_text = []

                if slide.shapes.title and slide.shapes.title.text:
                    slide_text.append(f"Title: {slide.shapes.title.text}")

                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        if shape == slide.shapes.title:
                            continue
                        slide_text.append(shape.text)

                full_slide_text = "\n".join(slide_text)
                if not full_slide_text.strip():
                    continue

                slide_chunks = splitter.split_text(full_slide_text)

                for chunk_text in slide_chunks:
                    contextualized = f"[File: {filename}] [Slide: {slide_num}]\n{chunk_text}"
                    token_count = self.count_tokens(contextualized)
                    total_tokens += token_count

                    chunks.append(ProcessedChunk(
                        content=contextualized,
                        metadata={
                            "file_type": "presentation",
                            "filename": filename,
                            "slide_number": slide_num
                        },
                        token_count=token_count,
                        chunk_index=len(chunks)
                    ))

            logger.info(f"[PresentationProcessor] {filename}: {len(chunks)} chunks from {len(prs.slides)} slides")
            return ProcessedDocument(
                chunks=chunks,
                file_type="presentation",
                total_tokens=total_tokens,
                metadata={"total_slides": len(prs.slides)}
            )

        except Exception as e:
            logger.error(f"[PresentationProcessor] Failed: {e}")
            return ProcessedDocument(chunks=[], file_type="pptx_error")


# =============================================================================
# CODE PROCESSOR
# =============================================================================

class CodeProcessor(BaseProcessor):
    """Processor for source code files."""

    LANGUAGE_MAP = {
        ".py": Language.PYTHON, ".js": Language.JS, ".jsx": Language.JS,
        ".ts": Language.TS, ".tsx": Language.TS, ".java": Language.JAVA,
        ".go": Language.GO, ".cpp": Language.CPP, ".c": Language.CPP,
        ".cs": Language.CSHARP, ".rb": Language.RUBY, ".php": Language.PHP,
        ".rs": Language.RUST, ".scala": Language.SCALA, ".swift": Language.SWIFT,
        ".kt": Language.KOTLIN,
    }
    
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        ext = os.path.splitext(filename)[1].lower()
        content_bytes = self._load_content(content, file_path)
        
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("utf-8", errors="replace")
        
        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="code")
        
        language = self.LANGUAGE_MAP.get(ext)
        if language:
            splitter = RecursiveCharacterTextSplitter.from_language(language=language, chunk_size=1500, chunk_overlap=100)
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=100, separators=["\n\n", "\n", " ", ""])
        
        raw_chunks = splitter.split_text(text)
        chunks = []
        total_tokens = 0
        lang_name = language.value if language else ext.lstrip(".")
        
        for i, chunk_text in enumerate(raw_chunks):
            token_count = self.count_tokens(chunk_text)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=chunk_text,
                metadata={"file_type": "code", "language": lang_name, "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))
        
        logger.info(f"[CodeProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(
            chunks=chunks, file_type="code", total_tokens=total_tokens, metadata={"language": lang_name}
        )


# =============================================================================
# MARKDOWN PROCESSOR
# =============================================================================

class MarkdownProcessor(BaseProcessor):
    """Processor for Markdown files."""
    
    HEADERS_TO_SPLIT_ON = [("#", "Header1"), ("##", "Header2"), ("###", "Header3")]
    
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        content_bytes = self._load_content(content, file_path)
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("utf-8", errors="replace")
        
        header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self.HEADERS_TO_SPLIT_ON, strip_headers=False)
        try:
            header_docs = header_splitter.split_text(text)
        except Exception:
            header_docs = None
        
        chunks = []
        total_tokens = 0
        
        if header_docs:
            content_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            for doc in header_docs:
                header_path = self._build_header_path(doc.metadata)
                section_chunks = content_splitter.split_text(doc.page_content)
                for chunk_text in section_chunks:
                    contextualized = f"[Context: {header_path}]\n{chunk_text}" if header_path else chunk_text
                    token_count = self.count_tokens(contextualized)
                    total_tokens += token_count
                    chunks.append(ProcessedChunk(
                        content=contextualized,
                        metadata={"file_type": "markdown", "header_path": header_path, "filename": filename},
                        token_count=token_count,
                        chunk_index=len(chunks)
                    ))
        else:
            splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
            raw_chunks = splitter.split_text(text)
            for i, chunk_text in enumerate(raw_chunks):
                token_count = self.count_tokens(chunk_text)
                total_tokens += token_count
                chunks.append(ProcessedChunk(
                    content=chunk_text,
                    metadata={"file_type": "markdown", "filename": filename},
                    token_count=token_count,
                    chunk_index=i
                ))
        
        logger.info(f"[MarkdownProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(chunks=chunks, file_type="markdown", total_tokens=total_tokens)

    def _build_header_path(self, metadata: Dict[str, Any]) -> str:
        parts = []
        for key in ["Header1", "Header2", "Header3"]:
            if key in metadata and metadata[key]:
                parts.append(metadata[key].strip().lstrip("#").strip())
        return " > ".join(parts)


# =============================================================================
# PDF PROCESSOR
# =============================================================================

class PDFProcessor(BaseProcessor):
    """
    Processor for PDF documents with OCR Fallback and file-path support.
    """
    
    NOISE_PATTERNS = [r"Page\s+\d+\s+(of|/)\s+\d+", r"^\d+\s*$", r"CONFIDENTIAL", r"^\s*©.*$"]
    
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        from core.config import settings
        
        # 1. Try Local (PyMuPDF supports file path directly)
        local_result = self._process_with_pymupdf(content, filename, file_path)

        # 2. Check Text Density
        text_density = local_result.metadata.get("text_density", 0)
        is_scanned = text_density < 50

        if is_scanned and settings.LLAMA_CLOUD_API_KEY:
            logger.info(f"[PDFProcessor] Low text density ({text_density:.1f}). Fallback to LlamaParse.")
            try:
                cloud_result = self._process_with_llamaparse(content, filename, file_path)
                if cloud_result and cloud_result.chunks:
                    return cloud_result
            except Exception as e:
                logger.warning(f"[PDFProcessor] LlamaParse fallback failed: {e}. Keeping local result.")
        
        return local_result
    
    def _process_with_llamaparse(self, content: Optional[bytes], filename: str, file_path: Optional[str]) -> ProcessedDocument:
        import tempfile
        try:
            import nest_asyncio
            nest_asyncio.apply()
            from llama_parse import LlamaParse
        except ImportError:
            raise ImportError("llama-parse not installed")
        
        from core.config import settings
        
        # Ensure we have a file path for LlamaParse
        temp_path = None
        target_path = file_path
        
        if not target_path:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                tf.write(content)
                target_path = tf.name
                temp_path = target_path
        
        try:
            with LLAMAPARSE_LOCK:
                parser = LlamaParse(
                    api_key=settings.LLAMA_CLOUD_API_KEY,
                    result_type="markdown",
                    verbose=False,
                    language="en",
                )
                documents = parser.load_data(target_path)
            
            full_text = "\n\n".join([doc.text for doc in documents])
            if not full_text.strip():
                raise ValueError("Empty result from LlamaParse")

        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        raw_chunks = splitter.split_text(full_text)
        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(raw_chunks):
            contextualized = f"[File: {filename}] [Parser: LlamaParse]\n{chunk_text}"
            token_count = self.count_tokens(contextualized)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=contextualized,
                metadata={"file_type": "pdf", "parser": "llama_parse", "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))

        logger.info(f"[PDFProcessor] LlamaParse: {filename}: {len(chunks)} chunks")
        return ProcessedDocument(
            chunks=chunks, file_type="pdf", total_tokens=total_tokens, metadata={"parser": "llama_parse"}
        )
    
    def _process_with_pymupdf(self, content: Optional[bytes], filename: str, file_path: Optional[str]) -> ProcessedDocument:
        try:
            import fitz
        except ImportError:
            return ProcessedDocument(chunks=[], file_type="pdf_error")
        
        pages_text = []
        total_chars = 0
        doc = None
        try:
            if file_path:
                doc = fitz.open(file_path)
            elif content:
                doc = fitz.open(stream=content, filetype="pdf")
            else:
                return ProcessedDocument(chunks=[], file_type="pdf_error")

            num_pages = len(doc)
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                total_chars += len(text)
                cleaned = self._clean_text(text)
                if cleaned.strip():
                    pages_text.append((page_num, cleaned))
            doc.close()
        except Exception as e:
            logger.error(f"[PDFProcessor] PyMuPDF failed: {e}")
            return ProcessedDocument(chunks=[], file_type="pdf_error")
        
        text_density = total_chars / max(1, num_pages)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = []
        total_tokens = 0
        
        for page_num, page_text in pages_text:
            page_chunks = splitter.split_text(page_text)
            for chunk_text in page_chunks:
                contextualized = f"[File: {filename}] [Page: {page_num}]\n{chunk_text}"
                token_count = self.count_tokens(contextualized)
                total_tokens += token_count
                chunks.append(ProcessedChunk(
                    content=contextualized,
                    metadata={"file_type": "pdf", "parser": "pymupdf", "page_number": page_num, "filename": filename},
                    token_count=token_count,
                    chunk_index=len(chunks)
                ))
        
        logger.info(f"[PDFProcessor] PyMuPDF: {filename}, Density={text_density:.1f}")
        return ProcessedDocument(
            chunks=chunks, file_type="pdf", total_tokens=total_tokens,
            metadata={"parser": "pymupdf", "text_density": text_density}
        )

    def _clean_text(self, text: str) -> str:
        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            if not any(re.search(p, line, re.IGNORECASE) for p in self.NOISE_PATTERNS):
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)


# =============================================================================
# DOCX PROCESSOR
# =============================================================================

class DocxProcessor(BaseProcessor):
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        try:
            import docx2txt
            source = file_path if file_path else io.BytesIO(content)
            text = docx2txt.process(source)
        except Exception:
            return ProcessedDocument(chunks=[], file_type="docx_error")
        
        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="docx")

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        raw_chunks = splitter.split_text(text)
        chunks = []
        total_tokens = 0

        for i, chunk_text in enumerate(raw_chunks):
            contextualized = f"[File: {filename}]\n{chunk_text}"
            token_count = self.count_tokens(contextualized)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=contextualized,
                metadata={"file_type": "docx", "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))

        logger.info(f"[DocxProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(chunks=chunks, file_type="docx", total_tokens=total_tokens)


# =============================================================================
# PLAIN TEXT PROCESSOR
# =============================================================================

class PlainTextProcessor(BaseProcessor):
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        content_bytes = self._load_content(content, file_path)
        try:
            text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            text = content_bytes.decode("utf-8", errors="replace")
        text = text.replace("\x00", "")
        
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        raw_chunks = splitter.split_text(text)
        chunks = []
        total_tokens = 0

        for i, chunk_text in enumerate(raw_chunks):
            token_count = self.count_tokens(chunk_text)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=chunk_text,
                metadata={"file_type": "text", "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))
        return ProcessedDocument(chunks=chunks, file_type="text", total_tokens=total_tokens)


# =============================================================================
# LLAMAPARSE PROCESSOR (Fallback)
# =============================================================================

class LlamaParseProcessor(BaseProcessor):
    """Processor for complex or legacy files (DOC, XLS, MSG)."""
    
    def process(self, content: Optional[bytes], filename: str, file_path: Optional[str] = None) -> ProcessedDocument:
        from core.config import settings
        if not settings.LLAMA_CLOUD_API_KEY:
            return ProcessedDocument(chunks=[], file_type="missing_api_key")

        import tempfile
        try:
            import nest_asyncio
            nest_asyncio.apply()
            from llama_parse import LlamaParse
        except ImportError:
            return ProcessedDocument(chunks=[], file_type="library_missing")

        temp_path = None
        target_path = file_path

        if not target_path:
            ext = os.path.splitext(filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
                tf.write(content)
                target_path = tf.name
                temp_path = target_path

        try:
            with LLAMAPARSE_LOCK:
                parser = LlamaParse(
                    api_key=settings.LLAMA_CLOUD_API_KEY,
                    result_type="markdown",
                    verbose=False,
                    language="en",
                )
                documents = parser.load_data(target_path)

            full_text = "\n\n".join([doc.text for doc in documents])

        except Exception as e:
            logger.error(f"[LlamaParseProcessor] Failed {filename}: {e}")
            return ProcessedDocument(chunks=[], file_type="parse_error")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        raw_chunks = splitter.split_text(full_text)
        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(raw_chunks):
            contextualized = f"[File: {filename}]\n{chunk_text}"
            token_count = self.count_tokens(contextualized)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=contextualized,
                metadata={"file_type": "legacy_office", "parser": "llama_parse", "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))

        logger.info(f"[LlamaParseProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(chunks=chunks, file_type="legacy_office", total_tokens=total_tokens)


# =============================================================================
# FACTORY
# =============================================================================

class DocumentProcessorFactory:
    """Factory to select the best processor."""
    
    PROCESSOR_MAP = {
        # Group A (Local/Fast)
        ".py": CodeProcessor, ".js": CodeProcessor, ".ts": CodeProcessor, ".java": CodeProcessor,
        ".json": CodeProcessor, ".xml": CodeProcessor, ".html": CodeProcessor, ".yaml": CodeProcessor,
        ".md": MarkdownProcessor,
        ".docx": DocxProcessor,
        ".txt": PlainTextProcessor,
        
        # Group A (Structured)
        ".csv": TableProcessor,
        ".xlsx": TableProcessor,
        ".pptx": PresentationProcessor,
        
        # Group B (Complex/Paid)
        ".doc": LlamaParseProcessor,
        ".xls": LlamaParseProcessor,
        ".msg": LlamaParseProcessor,
        
        # Hybrid
        ".pdf": PDFProcessor,
    }
    
    MIME_MAP = {
        "application/pdf": PDFProcessor,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxProcessor,
        "application/msword": DocxProcessor,
        "text/markdown": MarkdownProcessor,
        "text/plain": PlainTextProcessor,
        "text/html": CodeProcessor,
        "application/json": CodeProcessor,
    }

    UNSUPPORTED_EXTENSIONS = {
        ".numbers",
        ".key",
        ".pages",
    }
    
    @classmethod
    def process(cls, file_path: str = None, filename: str = None, content: bytes = None, mime_type: str = None):
        # NOTE: We DO NOT read content here to avoid memory spikes.
        # Processors are responsible for reading if they need bytes, preferring file_path.
        
        if not file_path and not content:
            return ProcessedDocument(chunks=[], file_type="unknown")

        filename = filename or (os.path.basename(file_path) if file_path else "unknown")
        ext = os.path.splitext(filename)[1].lower()
        
        processor_class = cls.PROCESSOR_MAP.get(ext)
        
        if not processor_class and mime_type:
            processor_class = cls.MIME_MAP.get(mime_type)

        if not processor_class:
            if ext in cls.UNSUPPORTED_EXTENSIONS:
                logger.warning(f"[Factory] Unsupported file type {ext}")
                return ProcessedDocument(chunks=[], file_type="unsupported", metadata={"unsupported_reason": "unsupported_extension"})

            # Check binary (needs content read if no file_path, but be careful)
            is_binary = False
            if content:
                is_binary = cls._looks_like_binary(content)
            elif file_path:
                # Read small chunk to check binary
                with open(file_path, "rb") as f:
                    head = f.read(1024)
                is_binary = cls._looks_like_binary(head)

            if is_binary:
                return ProcessedDocument(chunks=[], file_type="binary_skip")

            processor_class = PlainTextProcessor
        
        # Double check binary for PlainText
        if processor_class == PlainTextProcessor:
             # Same check as above
             is_binary = False
             if content:
                 is_binary = cls._looks_like_binary(content)
             elif file_path:
                 with open(file_path, "rb") as f:
                     head = f.read(1024)
                 is_binary = cls._looks_like_binary(head)

             if is_binary:
                 return ProcessedDocument(chunks=[], file_type="binary_skip")

        processor = processor_class()
        return processor.process(content, filename, file_path)

    @staticmethod
    def _looks_like_binary(content: bytes) -> bool:
        if not content: return False
        if b"\x00" in content: return True
        return False

    @classmethod
    def process_web_content(cls, html_content: str, url: str) -> ProcessedDocument:
        processor = MarkdownProcessor()
        return processor.process(html_content.encode("utf-8"), url)


class DocumentParser:
    """Legacy compatibility class."""
    
    SUPPORTED_FORMATS = {
        'application/pdf': 'pdf',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'docx',
        'text/plain': 'text',
        'text/markdown': 'text',
        'text/csv': 'text',
        'text/html': 'text',
    }
    
    @staticmethod
    def extract_text(file_content: bytes, mime_type: str) -> str:
        result = DocumentProcessorFactory.process(content=file_content, filename="document", mime_type=mime_type)
        return "\n\n".join(chunk.content for chunk in result.chunks)
    
    @staticmethod
    def parse_file(file_path: str, filename: str = None) -> str:
        result = DocumentProcessorFactory.process(file_path=file_path, filename=filename or os.path.basename(file_path))
        return "\n\n".join(chunk.content for chunk in result.chunks)
    
    @staticmethod
    def is_supported(mime_type: str) -> bool:
        return mime_type.lower().strip() in DocumentParser.SUPPORTED_FORMATS
