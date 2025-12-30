"""
Enterprise-Grade Document Processor Factory

Context-Aware RAG chunking with format-specific strategies.
Supports: Code files, Markdown, PDF/DOCX with metadata enrichment.

Author: Axio Hub Team
"""

import io
import os
import re
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# LangChain imports (text_splitter moved to langchain package in newer versions)
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    Language,
    MarkdownHeaderTextSplitter,
)

# Token counting
import tiktoken

logger = logging.getLogger(__name__)

# Initialize tiktoken encoder (OpenAI's cl100k_base)
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
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process document content and return chunks with metadata."""
        pass
    
    @staticmethod
    def count_tokens(text: str) -> int:
        """Count tokens using tiktoken cl100k_base encoder."""
        if TIKTOKEN_ENCODER:
            return len(TIKTOKEN_ENCODER.encode(text))
        return len(text) // 4  # Fallback approximation


# =============================================================================
# CODE PROCESSOR
# =============================================================================

class CodeProcessor(BaseProcessor):
    """
    Processor for source code files.
    
    Uses RecursiveCharacterTextSplitter.from_language() to preserve
    function and class boundaries. Hard limit of 2000 tokens per chunk.
    """
    
    # Map file extensions to LangChain Language enum
    LANGUAGE_MAP = {
        ".py": Language.PYTHON,
        ".js": Language.JS,
        ".jsx": Language.JS,
        ".ts": Language.TS,
        ".tsx": Language.TS,
        ".java": Language.JAVA,
        ".go": Language.GO,
        ".cpp": Language.CPP,
        ".c": Language.CPP,
        ".cs": Language.CSHARP,
        ".rb": Language.RUBY,
        ".php": Language.PHP,
        ".rs": Language.RUST,
        ".scala": Language.SCALA,
        ".swift": Language.SWIFT,
        ".kt": Language.KOTLIN,
    }
    
    # These don't have special language support, use generic
    GENERIC_CODE_EXTENSIONS = {".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".sql"}
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process code file with language-aware splitting."""
        ext = os.path.splitext(filename)[1].lower()
        
        # Decode content
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
        
        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="code")
        
        # Get language-specific splitter or generic
        language = self.LANGUAGE_MAP.get(ext)
        
        if language:
            splitter = RecursiveCharacterTextSplitter.from_language(
                language=language,
                chunk_size=1500,  # ~400 tokens target
                chunk_overlap=100,
            )
        else:
            # Generic code splitter for JSON, YAML, etc.
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1500,
                chunk_overlap=100,
                separators=["\n\n", "\n", " ", ""]
            )
        
        # Split text
        raw_chunks = splitter.split_text(text)
        
        # Build ProcessedChunks with metadata
        chunks = []
        total_tokens = 0
        lang_name = language.value if language else ext.lstrip(".")
        
        for i, chunk_text in enumerate(raw_chunks):
            token_count = self.count_tokens(chunk_text)
            total_tokens += token_count
            
            # Hard limit: if chunk exceeds 2000 tokens, force-split
            if token_count > 2000:
                sub_chunks = self._force_split(chunk_text, 1500)
                for j, sub_text in enumerate(sub_chunks):
                    sub_tokens = self.count_tokens(sub_text)
                    chunks.append(ProcessedChunk(
                        content=sub_text,
                        metadata={
                            "file_type": "code",
                            "language": lang_name,
                            "filename": filename,
                        },
                        token_count=sub_tokens,
                        chunk_index=len(chunks)
                    ))
            else:
                chunks.append(ProcessedChunk(
                    content=chunk_text,
                    metadata={
                        "file_type": "code",
                        "language": lang_name,
                        "filename": filename,
                    },
                    token_count=token_count,
                    chunk_index=i
                ))
        
        # Re-index after potential sub-splits
        for i, chunk in enumerate(chunks):
            chunk.chunk_index = i
        
        logger.info(f"[CodeProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(
            chunks=chunks,
            file_type="code",
            total_tokens=total_tokens,
            metadata={"language": lang_name}
        )
    
    def _force_split(self, text: str, max_chars: int) -> List[str]:
        """Force-split oversized text by character count."""
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]


# =============================================================================
# MARKDOWN PROCESSOR
# =============================================================================

class MarkdownProcessor(BaseProcessor):
    """
    Processor for Markdown files and web content.
    
    Strategy:
    1. Split by headers (#, ##, ###) first
    2. For each section, apply recursive character splitting
    3. Inject header path as context prefix
    """
    
    HEADERS_TO_SPLIT_ON = [
        ("#", "Header1"),
        ("##", "Header2"),
        ("###", "Header3"),
        ("####", "Header4"),
    ]
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process markdown with header-aware splitting."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
        
        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="markdown")
        
        # Step 1: Split by headers
        header_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=self.HEADERS_TO_SPLIT_ON,
            strip_headers=False
        )
        
        try:
            header_docs = header_splitter.split_text(text)
        except Exception as e:
            logger.warning(f"[MarkdownProcessor] Header splitting failed: {e}, using fallback")
            header_docs = None
        
        chunks = []
        total_tokens = 0
        
        if header_docs:
            # Process each header section
            content_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            for doc in header_docs:
                # Build header path from metadata
                header_path = self._build_header_path(doc.metadata)
                section_text = doc.page_content
                
                # Split section content
                section_chunks = content_splitter.split_text(section_text)
                
                for chunk_text in section_chunks:
                    # Context injection: prepend header path
                    if header_path:
                        contextualized = f"[Context: {header_path}]\n{chunk_text}"
                    else:
                        contextualized = chunk_text
                    
                    token_count = self.count_tokens(contextualized)
                    total_tokens += token_count
                    
                    chunks.append(ProcessedChunk(
                        content=contextualized,
                        metadata={
                            "file_type": "markdown",
                            "header_path": header_path,
                            "filename": filename,
                        },
                        token_count=token_count,
                        chunk_index=len(chunks)
                    ))
        else:
            # Fallback: simple recursive split
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150
            )
            raw_chunks = splitter.split_text(text)
            
            for i, chunk_text in enumerate(raw_chunks):
                token_count = self.count_tokens(chunk_text)
                total_tokens += token_count
                
                chunks.append(ProcessedChunk(
                    content=chunk_text,
                    metadata={
                        "file_type": "markdown",
                        "header_path": "",
                        "filename": filename,
                    },
                    token_count=token_count,
                    chunk_index=i
                ))
        
        logger.info(f"[MarkdownProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(
            chunks=chunks,
            file_type="markdown",
            total_tokens=total_tokens
        )
    
    def _build_header_path(self, metadata: Dict[str, Any]) -> str:
        """Build header path string from metadata."""
        parts = []
        for key in ["Header1", "Header2", "Header3", "Header4"]:
            if key in metadata and metadata[key]:
                # Clean header text (remove # symbols)
                header = metadata[key].strip().lstrip("#").strip()
                if header:
                    parts.append(header)
        return " > ".join(parts)


# =============================================================================
# PDF PROCESSOR
# =============================================================================

class PDFProcessor(BaseProcessor):
    """
    Processor for PDF documents.
    
    Uses PyMuPDF for fast, accurate text extraction.
    Cleans headers/footers, injects file/page context.
    """
    
    # Regex patterns for common headers/footers to remove
    NOISE_PATTERNS = [
        r"Page\s+\d+\s+(of|/)\s+\d+",  # Page 1 of 10
        r"^\d+\s*$",  # Lone page numbers
        r"CONFIDENTIAL",
        r"^\s*©.*$",  # Copyright notices
    ]
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process PDF with page-aware chunking."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("[PDFProcessor] PyMuPDF not installed, using fallback")
            return self._fallback_process(content, filename)
        
        # Extract text from PDF
        pages_text = []
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    # Clean the text
                    cleaned = self._clean_text(text)
                    if cleaned.strip():
                        pages_text.append((page_num, cleaned))
            doc.close()
        except Exception as e:
            logger.error(f"[PDFProcessor] PyMuPDF extraction failed: {e}")
            return self._fallback_process(content, filename)
        
        if not pages_text:
            return ProcessedDocument(chunks=[], file_type="pdf")
        
        # Chunk with sliding window
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = []
        total_tokens = 0
        
        for page_num, page_text in pages_text:
            page_chunks = splitter.split_text(page_text)
            
            for chunk_text in page_chunks:
                # Context injection: prepend file and page info
                contextualized = f"[File: {filename}] [Page: {page_num}]\n{chunk_text}"
                
                token_count = self.count_tokens(contextualized)
                total_tokens += token_count
                
                chunks.append(ProcessedChunk(
                    content=contextualized,
                    metadata={
                        "file_type": "pdf",
                        "page_number": page_num,
                        "filename": filename,
                    },
                    token_count=token_count,
                    chunk_index=len(chunks)
                ))
        
        logger.info(f"[PDFProcessor] {filename}: {len(chunks)} chunks from {len(pages_text)} pages")
        return ProcessedDocument(
            chunks=chunks,
            file_type="pdf",
            total_tokens=total_tokens,
            metadata={"total_pages": len(pages_text)}
        )
    
    def _clean_text(self, text: str) -> str:
        """Remove common headers, footers, and noise patterns."""
        lines = text.split("\n")
        cleaned_lines = []
        
        for line in lines:
            skip = False
            for pattern in self.NOISE_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    skip = True
                    break
            if not skip:
                cleaned_lines.append(line)
        
        return "\n".join(cleaned_lines)
    
    def _fallback_process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Fallback using pypdf if PyMuPDF is not available."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            full_text = ""
            for page in reader.pages:
                text = page.extract_text() or ""
                full_text += text + "\n\n"
        except Exception as e:
            logger.error(f"[PDFProcessor] pypdf fallback failed: {e}")
            return ProcessedDocument(chunks=[], file_type="pdf")
        
        # Simple chunking
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        raw_chunks = splitter.split_text(full_text)
        
        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(raw_chunks):
            contextualized = f"[File: {filename}]\n{chunk_text}"
            token_count = self.count_tokens(contextualized)
            total_tokens += token_count
            chunks.append(ProcessedChunk(
                content=contextualized,
                metadata={"file_type": "pdf", "filename": filename},
                token_count=token_count,
                chunk_index=i
            ))
        
        return ProcessedDocument(chunks=chunks, file_type="pdf", total_tokens=total_tokens)


# =============================================================================
# DOCX PROCESSOR
# =============================================================================

class DocxProcessor(BaseProcessor):
    """Processor for Word documents."""
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process DOCX with paragraph chunking."""
        try:
            import docx2txt
            text = docx2txt.process(io.BytesIO(content))
        except Exception as e:
            logger.error(f"[DocxProcessor] Extraction failed: {e}")
            return ProcessedDocument(chunks=[], file_type="docx")
        
        if not text or not text.strip():
            return ProcessedDocument(chunks=[], file_type="docx")
        
        # Chunk with context
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
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
    """Processor for plain text files."""
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process plain text with simple chunking."""
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
        
        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="text")
        
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
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
        
        logger.info(f"[PlainTextProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(chunks=chunks, file_type="text", total_tokens=total_tokens)


# =============================================================================
# DOCUMENT PROCESSOR FACTORY
# =============================================================================

class DocumentProcessorFactory:
    """
    Factory class that selects the appropriate processor based on file type.
    
    Usage:
        result = DocumentProcessorFactory.process(file_path, filename)
        chunks = result.chunks  # List[ProcessedChunk]
    """
    
    # Extension to processor mapping
    PROCESSOR_MAP = {
        # Code files
        ".py": CodeProcessor,
        ".js": CodeProcessor,
        ".jsx": CodeProcessor,
        ".ts": CodeProcessor,
        ".tsx": CodeProcessor,
        ".java": CodeProcessor,
        ".go": CodeProcessor,
        ".cpp": CodeProcessor,
        ".c": CodeProcessor,
        ".cs": CodeProcessor,
        ".rb": CodeProcessor,
        ".php": CodeProcessor,
        ".rs": CodeProcessor,
        ".scala": CodeProcessor,
        ".swift": CodeProcessor,
        ".kt": CodeProcessor,
        ".json": CodeProcessor,
        ".yaml": CodeProcessor,
        ".yml": CodeProcessor,
        ".toml": CodeProcessor,
        ".xml": CodeProcessor,
        ".html": CodeProcessor,
        ".css": CodeProcessor,
        ".sql": CodeProcessor,
        
        # Markdown
        ".md": MarkdownProcessor,
        ".markdown": MarkdownProcessor,
        
        # PDF
        ".pdf": PDFProcessor,
        
        # Word documents
        ".docx": DocxProcessor,
        ".doc": DocxProcessor,
        
        # Plain text
        ".txt": PlainTextProcessor,
        ".csv": PlainTextProcessor,
        ".log": PlainTextProcessor,
    }
    
    # MIME type fallback mapping
    MIME_MAP = {
        "application/pdf": PDFProcessor,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxProcessor,
        "application/msword": DocxProcessor,
        "text/markdown": MarkdownProcessor,
        "text/plain": PlainTextProcessor,
        "text/html": CodeProcessor,
        "application/json": CodeProcessor,
    }
    
    @classmethod
    def process(
        cls,
        file_path: str = None,
        filename: str = None,
        content: bytes = None,
        mime_type: str = None
    ) -> ProcessedDocument:
        """
        Process a document using the appropriate processor.
        
        Args:
            file_path: Path to file on disk (optional if content provided)
            filename: Original filename for extension detection
            content: Raw file bytes (optional if file_path provided)
            mime_type: MIME type for fallback detection
        
        Returns:
            ProcessedDocument with chunks and metadata
        """
        # Load content if file_path provided
        if file_path and not content:
            with open(file_path, "rb") as f:
                content = f.read()
        
        if not content:
            logger.error("[Factory] No content to process")
            return ProcessedDocument(chunks=[], file_type="unknown")
        
        # Determine processor
        filename = filename or (os.path.basename(file_path) if file_path else "unknown")
        ext = os.path.splitext(filename)[1].lower()
        
        processor_class = cls.PROCESSOR_MAP.get(ext)
        
        if not processor_class and mime_type:
            processor_class = cls.MIME_MAP.get(mime_type)
        
        if not processor_class:
            # Default to plain text
            logger.warning(f"[Factory] Unknown file type {ext}, using PlainTextProcessor")
            processor_class = PlainTextProcessor
        
        # Process
        processor = processor_class()
        result = processor.process(content, filename)
        
        logger.info(f"[Factory] Processed {filename}: {len(result.chunks)} chunks, type={result.file_type}")
        return result
    
    @classmethod
    def process_web_content(cls, html_content: str, url: str) -> ProcessedDocument:
        """
        Special method for processing web content (already converted to text/markdown).
        
        Args:
            html_content: Text content extracted from web page
            url: Source URL for metadata
        
        Returns:
            ProcessedDocument with chunks
        """
        processor = MarkdownProcessor()
        content_bytes = html_content.encode("utf-8")
        result = processor.process(content_bytes, url)
        
        # Add source URL to all chunk metadata
        for chunk in result.chunks:
            chunk.metadata["source_url"] = url
        
        return result


# =============================================================================
# LEGACY COMPATIBILITY - DocumentParser
# =============================================================================

class DocumentParser:
    """
    Legacy compatibility class.
    
    Maps to the old extract_text interface for backwards compatibility.
    New code should use DocumentProcessorFactory directly.
    """
    
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
        """Extract text from file bytes (legacy method)."""
        result = DocumentProcessorFactory.process(
            content=file_content,
            filename="document",
            mime_type=mime_type
        )
        # Combine all chunks into single text
        return "\n\n".join(chunk.content for chunk in result.chunks)
    
    @staticmethod
    def parse_file(file_path: str, filename: str = None) -> str:
        """Parse file and return combined text (legacy method)."""
        result = DocumentProcessorFactory.process(
            file_path=file_path,
            filename=filename or os.path.basename(file_path)
        )
        return "\n\n".join(chunk.content for chunk in result.chunks)
    
    @staticmethod
    def is_supported(mime_type: str) -> bool:
        """Check if MIME type is supported."""
        return mime_type.lower().strip() in DocumentParser.SUPPORTED_FORMATS
