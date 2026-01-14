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
import tempfile
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

# LangChain imports (text_splitter moved to langchain package in newer versions)
# LangChain imports (text_splitter moved to langchain_text_splitters)
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    Language,
    MarkdownHeaderTextSplitter,
)

# Token counting
import tiktoken

logger = logging.getLogger(__name__)
LLAMAPARSE_LOCK = threading.Lock()
try:
    from core.metrics import pdf_scan_detection_total, llamaparse_fallback_total
except Exception:
    pdf_scan_detection_total = None
    llamaparse_fallback_total = None

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
    
    Supports two parsing modes:
    1. LlamaParse (Advanced): OCR-enabled, table extraction, premium parsing
       - Activated when LLAMA_CLOUD_API_KEY is set
    2. PyMuPDF (Standard): Fast, accurate text extraction
       - Used as fallback or when no API key
    """
    
    # Regex patterns for common headers/footers to remove
    NOISE_PATTERNS = [
        r"Page\s+\d+\s+(of|/)\s+\d+",  # Page 1 of 10
        r"^\d+\s*$",  # Lone page numbers
        r"CONFIDENTIAL",
        r"^\s*©.*$",  # Copyright notices
    ]
    
    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process PDF with quality-first routing and local fallback."""
        from core.config import settings

        if settings.LLAMA_CLOUD_API_KEY:
            logger.info(f"[PDFProcessor] Quality-first LlamaParse for {filename}")
            if llamaparse_fallback_total:
                llamaparse_fallback_total.labels("pdf_quality_first").inc()
            try:
                result = self._process_with_llamaparse(content, filename)
                if result and result.chunks:
                    if pdf_scan_detection_total:
                        pdf_scan_detection_total.labels("llamaparse_success").inc()
                    return result
                logger.warning(
                    f"[PDFProcessor] LlamaParse returned no chunks for {filename}, falling back to PyMuPDF"
                )
                if pdf_scan_detection_total:
                    pdf_scan_detection_total.labels("llamaparse_empty_fallback").inc()
            except Exception as e:
                logger.warning(
                    f"[PDFProcessor] LlamaParse failed for {filename}: {e}, falling back to PyMuPDF"
                )
                if pdf_scan_detection_total:
                    pdf_scan_detection_total.labels("llamaparse_error_fallback").inc()
        else:
            logger.info(
                f"[PDFProcessor] No LLAMA_CLOUD_API_KEY configured, using PyMuPDF for {filename}"
            )
            if pdf_scan_detection_total:
                pdf_scan_detection_total.labels("local_no_api_key").inc()

        return self._process_with_pymupdf(content, filename)

    SCANNED_TEXT_THRESHOLD = 150

    def _is_likely_scanned(self, text_length: int) -> bool:
        """Heuristic: very low extracted text likely indicates scanned PDF."""
        return text_length < self.SCANNED_TEXT_THRESHOLD
    
    def _process_with_llamaparse(self, content: bytes, filename: str) -> ProcessedDocument:
        """
        Process PDF using LlamaParse for advanced OCR and table extraction.
        
        LlamaParse provides:
        - OCR for scanned documents
        - Table detection and extraction
        - Better handling of complex layouts
        """
        import tempfile
        import os
        
        # Import LlamaParse with nest_asyncio for async compatibility
        try:
            import nest_asyncio
            nest_asyncio.apply()
            from llama_parse import LlamaParse
        except ImportError:
            raise ImportError("llama-parse package not installed")
        
        from core.config import settings
        
        logger.info(f"[PDFProcessor] Using LlamaParse for {filename}")
        
        # Write content to temp file (LlamaParse needs file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
            tf.write(content)
            tf_path = tf.name
        
        try:
            # Initialize LlamaParse with OCR settings
            # NOTE: Serialize LlamaParse calls to avoid anyio/gevent conflicts.
            with LLAMAPARSE_LOCK:
                parser = LlamaParse(
                    api_key=settings.LLAMA_CLOUD_API_KEY,
                    result_type="markdown",  # Get structured markdown output
                    verbose=False,
                    language="en",
                )
                
                # Parse the document (synchronous call)
                documents = parser.load_data(tf_path)
            
            if not documents:
                raise ValueError("LlamaParse returned no documents")
            
            # Combine all document text
            full_text = "\n\n".join([doc.text for doc in documents])
            
            if not full_text.strip():
                raise ValueError("LlamaParse returned empty text")
            
            logger.info(f"[PDFProcessor] LlamaParse extracted {len(full_text)} chars from {filename}")
            
        finally:
            # Always cleanup temp file
            try:
                os.remove(tf_path)
            except:
                pass
        
        # Chunk the extracted text (use MarkdownProcessor for markdown output)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
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
                metadata={
                    "file_type": "pdf",
                    "parser": "llama_parse",
                    "filename": filename,
                },
                token_count=token_count,
                chunk_index=i
            ))
        
        logger.info(f"[PDFProcessor] LlamaParse: {filename}: {len(chunks)} chunks")
        return ProcessedDocument(
            chunks=chunks,
            file_type="pdf",
            total_tokens=total_tokens,
            metadata={"parser": "llama_parse"}
        )
    
    def _process_with_pymupdf(self, content: bytes, filename: str) -> ProcessedDocument:
        """Process PDF with PyMuPDF (standard mode)."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("[PDFProcessor] PyMuPDF not installed, using fallback")
            return self._fallback_process(content, filename)
        
        # Extract text from PDF
        pages_text = []
        total_chars = 0
        try:
            doc = fitz.open(stream=content, filetype="pdf")
            for page_num, page in enumerate(doc, start=1):
                text = page.get_text("text")
                if text.strip():
                    # Clean the text
                    cleaned = self._clean_text(text)
                    if cleaned.strip():
                        pages_text.append((page_num, cleaned))
                        total_chars += len(cleaned)
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
                        "parser": "pymupdf",
                        "page_number": page_num,
                        "filename": filename,
                    },
                    token_count=token_count,
                    chunk_index=len(chunks)
                ))
        
        logger.info(f"[PDFProcessor] PyMuPDF: {filename}: {len(chunks)} chunks from {len(pages_text)} pages")
        return ProcessedDocument(
            chunks=chunks,
            file_type="pdf",
            total_tokens=total_tokens,
            metadata={"total_pages": len(pages_text), "parser": "pymupdf", "text_length": total_chars}
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
# HTML PROCESSOR
# =============================================================================

class HTMLProcessor(BaseProcessor):
    """Processor for HTML files (strip tags, keep readable text)."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")

        if not text.strip():
            return ProcessedDocument(chunks=[], file_type="html")

        try:
            from bs4 import BeautifulSoup
        except ImportError as exc:
            logger.error(f"[HTMLProcessor] Missing dependency: {exc}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "missing_dependency"},
            )

        soup = BeautifulSoup(text, "html.parser")
        extracted = soup.get_text(separator="\n")
        extracted = re.sub(r"\n{3,}", "\n\n", extracted).strip()

        if not extracted:
            return ProcessedDocument(chunks=[], file_type="html")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        raw_chunks = splitter.split_text(extracted)

        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(raw_chunks):
            token_count = self.count_tokens(chunk_text)
            total_tokens += token_count
            chunks.append(
                ProcessedChunk(
                    content=chunk_text,
                    metadata={"file_type": "html", "filename": filename},
                    token_count=token_count,
                    chunk_index=i,
                )
            )

        logger.info(f"[HTMLProcessor] {filename}: {len(chunks)} chunks")
        return ProcessedDocument(chunks=chunks, file_type="html", total_tokens=total_tokens)


# =============================================================================
# CSV PROCESSOR
# =============================================================================

class CSVProcessor(BaseProcessor):
    """Processor for CSV/TSV files with structured row output."""

    CHUNK_SIZE = 500

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        from core.config import settings

        if len(content) > settings.MAX_STRUCTURED_FILE_SIZE:
            logger.warning(f"[CSVProcessor] File too large for CSV parsing: {filename}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "file_too_large"},
            )

        try:
            import pandas as pd
        except ImportError as exc:
            logger.error(f"[CSVProcessor] Missing dependency: {exc}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "missing_dependency"},
            )

        delimiter = "\t" if filename.lower().endswith(".tsv") else ","
        chunks = []
        total_tokens = 0

        try:
            df_iter = pd.read_csv(
                io.BytesIO(content),
                chunksize=self.CHUNK_SIZE,
                encoding="utf-8",
                on_bad_lines="skip",
                sep=delimiter,
            )

            for chunk_idx, df_chunk in enumerate(df_iter):
                text_rows = []
                for _idx, row in df_chunk.iterrows():
                    row_text = " | ".join(
                        f"{col}: {val}"
                        for col, val in row.items()
                        if pd.notna(val)
                    )
                    if row_text:
                        text_rows.append(row_text)

                if not text_rows:
                    continue

                start_row = chunk_idx * self.CHUNK_SIZE + 1
                end_row = start_row + len(df_chunk) - 1
                chunk_text = (
                    f"[File: {filename}] [Rows: {start_row}-{end_row}]\n"
                    + "\n".join(text_rows)
                )

                token_count = self.count_tokens(chunk_text)
                total_tokens += token_count
                chunks.append(
                    ProcessedChunk(
                        content=chunk_text,
                        metadata={
                            "file_type": "csv",
                            "row_range": f"{start_row}-{end_row}",
                            "filename": filename,
                        },
                        token_count=token_count,
                        chunk_index=len(chunks),
                    )
                )

        except Exception as exc:
            logger.error(f"[CSVProcessor] Failed to parse {filename}: {exc}")
            return ProcessedDocument(chunks=[], file_type="csv")

        logger.info(f"[CSVProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(chunks=chunks, file_type="csv", total_tokens=total_tokens)


# =============================================================================
# EXCEL PROCESSOR
# =============================================================================

class ExcelProcessor(BaseProcessor):
    """Processor for XLSX files using streaming read_only mode."""

    CHUNK_SIZE = 200

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        from core.config import settings

        if len(content) > settings.MAX_STRUCTURED_FILE_SIZE:
            logger.warning(f"[ExcelProcessor] File too large for XLSX parsing: {filename}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "file_too_large"},
            )

        try:
            import openpyxl
        except ImportError as exc:
            logger.error(f"[ExcelProcessor] Missing dependency: {exc}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "missing_dependency"},
            )

        chunks = []
        total_tokens = 0

        try:
            workbook = openpyxl.load_workbook(
                io.BytesIO(content),
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            logger.error(f"[ExcelProcessor] Failed to load workbook {filename}: {exc}")
            return ProcessedDocument(chunks=[], file_type="xlsx")

        try:
            for sheet in workbook.worksheets:
                row_iter = sheet.iter_rows(values_only=True)
                header = None
                buffer = []
                start_row = 1
                current_row = 0

                for row in row_iter:
                    current_row += 1
                    if header is None:
                        header = [
                            (str(cell).strip() if cell is not None else f"Column {idx + 1}")
                            for idx, cell in enumerate(row)
                        ]
                        start_row = current_row + 1
                        continue

                    values = []
                    for idx, cell in enumerate(row):
                        if cell is None:
                            continue
                        label = header[idx] if idx < len(header) else f"Column {idx + 1}"
                        values.append(f"{label}: {cell}")

                    if values:
                        buffer.append(" | ".join(values))

                    if len(buffer) >= self.CHUNK_SIZE:
                        end_row = current_row
                        chunk_text = (
                            f"[File: {filename}] [Sheet: {sheet.title}] [Rows: {start_row}-{end_row}]\n"
                            + "\n".join(buffer)
                        )
                        token_count = self.count_tokens(chunk_text)
                        total_tokens += token_count
                        chunks.append(
                            ProcessedChunk(
                                content=chunk_text,
                                metadata={
                                    "file_type": "xlsx",
                                    "sheet": sheet.title,
                                    "row_range": f"{start_row}-{end_row}",
                                    "filename": filename,
                                },
                                token_count=token_count,
                                chunk_index=len(chunks),
                            )
                        )
                        buffer = []
                        start_row = end_row + 1

                if buffer:
                    end_row = current_row
                    chunk_text = (
                        f"[File: {filename}] [Sheet: {sheet.title}] [Rows: {start_row}-{end_row}]\n"
                        + "\n".join(buffer)
                    )
                    token_count = self.count_tokens(chunk_text)
                    total_tokens += token_count
                    chunks.append(
                        ProcessedChunk(
                            content=chunk_text,
                            metadata={
                                "file_type": "xlsx",
                                "sheet": sheet.title,
                                "row_range": f"{start_row}-{end_row}",
                                "filename": filename,
                            },
                            token_count=token_count,
                            chunk_index=len(chunks),
                        )
                    )

        finally:
            try:
                workbook.close()
            except Exception:
                pass

        logger.info(f"[ExcelProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(chunks=chunks, file_type="xlsx", total_tokens=total_tokens)


# =============================================================================
# PPTX PROCESSOR
# =============================================================================

class PPTXProcessor(BaseProcessor):
    """Processor for PPTX files using python-pptx."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        try:
            from pptx import Presentation
        except ImportError as exc:
            logger.error(f"[PPTXProcessor] Missing dependency: {exc}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "missing_dependency"},
            )

        chunks = []
        total_tokens = 0

        try:
            presentation = Presentation(io.BytesIO(content))
        except Exception as exc:
            logger.error(f"[PPTXProcessor] Failed to load {filename}: {exc}")
            return ProcessedDocument(chunks=[], file_type="pptx")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        for slide_index, slide in enumerate(presentation.slides, start=1):
            slide_texts = []
            for shape in slide.shapes:
                if getattr(shape, "has_text_frame", False):
                    text = shape.text_frame.text or ""
                    if text.strip():
                        slide_texts.append(text.strip())

            if getattr(slide, "has_notes_slide", False) and slide.notes_slide:
                notes = slide.notes_slide.notes_text_frame.text or ""
                if notes.strip():
                    slide_texts.append(f"[Notes]\n{notes.strip()}")

            if not slide_texts:
                continue

            slide_text = "\n".join(slide_texts)
            for chunk_text in splitter.split_text(slide_text):
                token_count = self.count_tokens(chunk_text)
                total_tokens += token_count
                chunks.append(
                    ProcessedChunk(
                        content=chunk_text,
                        metadata={
                            "file_type": "pptx",
                            "slide_number": slide_index,
                            "filename": filename,
                        },
                        token_count=token_count,
                        chunk_index=len(chunks),
                    )
                )

        if not chunks:
            from core.config import settings

            if settings.LLAMA_CLOUD_API_KEY:
                if llamaparse_fallback_total:
                    llamaparse_fallback_total.labels("pptx").inc()
                return LlamaParseProcessor(file_type="pptx").process(content, filename)

        logger.info(f"[PPTXProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(chunks=chunks, file_type="pptx", total_tokens=total_tokens)


# =============================================================================
# EMAIL PROCESSOR
# =============================================================================

class EmailProcessor(BaseProcessor):
    """Processor for .eml and .msg email files."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        ext = os.path.splitext(filename)[1].lower()
        text = ""

        if ext == ".eml":
            try:
                from email import policy
                from email.parser import BytesParser
            except ImportError as exc:
                logger.error(f"[EmailProcessor] Missing dependency: {exc}")
                return ProcessedDocument(
                    chunks=[],
                    file_type="unsupported",
                    metadata={"unsupported_reason": "missing_dependency"},
                )

            msg = BytesParser(policy=policy.default).parsebytes(content)
            text = self._email_to_text(msg)
        elif ext == ".msg":
            try:
                import extract_msg
            except ImportError as exc:
                logger.error(f"[EmailProcessor] Missing dependency: {exc}")
                return ProcessedDocument(
                    chunks=[],
                    file_type="unsupported",
                    metadata={"unsupported_reason": "missing_dependency"},
                )

            with tempfile.NamedTemporaryFile(delete=False, suffix=".msg") as tmp:
                tmp.write(content)
                tmp_path = tmp.name
            try:
                msg = extract_msg.Message(tmp_path)
                msg.process()
                text = self._msg_to_text(msg)
            finally:
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        else:
            return ProcessedDocument(chunks=[], file_type="email")

        if not text.strip():
            from core.config import settings

            if settings.LLAMA_CLOUD_API_KEY:
                if llamaparse_fallback_total:
                    llamaparse_fallback_total.labels("email").inc()
                return LlamaParseProcessor(file_type="email").process(content, filename)
            return ProcessedDocument(chunks=[], file_type="email")

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=150,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(splitter.split_text(text)):
            token_count = self.count_tokens(chunk_text)
            total_tokens += token_count
            chunks.append(
                ProcessedChunk(
                    content=chunk_text,
                    metadata={"file_type": "email", "filename": filename},
                    token_count=token_count,
                    chunk_index=i,
                )
            )

        logger.info(f"[EmailProcessor] {filename}: {len(chunks)} chunks, {total_tokens} tokens")
        return ProcessedDocument(chunks=chunks, file_type="email", total_tokens=total_tokens)

    def _email_to_text(self, msg) -> str:
        parts = [
            f"Subject: {msg.get('subject', '')}",
            f"From: {msg.get('from', '')}",
            f"To: {msg.get('to', '')}",
            f"Date: {msg.get('date', '')}",
        ]

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body = part.get_content()
                    break
                if content_type == "text/html" and not body:
                    body = part.get_content()
        else:
            body = msg.get_content()

        if body:
            body_text = body
            if "<html" in body.lower():
                try:
                    from bs4 import BeautifulSoup
                    body_text = BeautifulSoup(body, "html.parser").get_text(separator="\n")
                except Exception:
                    body_text = body
            parts.append("Body:\n" + body_text.strip())

        return "\n".join(p for p in parts if p)

    def _msg_to_text(self, msg) -> str:
        parts = [
            f"Subject: {getattr(msg, 'subject', '')}",
            f"From: {getattr(msg, 'sender', '')}",
            f"To: {getattr(msg, 'to', '')}",
            f"Date: {getattr(msg, 'date', '')}",
        ]
        body = getattr(msg, "body", "") or ""
        if body:
            parts.append("Body:\n" + body.strip())
        return "\n".join(p for p in parts if p)


# =============================================================================
# LLAMAPARSE PROCESSOR
# =============================================================================

class LlamaParseProcessor(BaseProcessor):
    """Generic LlamaParse processor for legacy, binary, or image files."""

    def __init__(self, file_type: str = "llamaparse"):
        self.file_type = file_type

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        from core.config import settings

        if not settings.LLAMA_CLOUD_API_KEY:
            logger.warning(f"[LlamaParseProcessor] LlamaParse not configured for {filename}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "llamaparse_unavailable"},
            )

        try:
            import nest_asyncio
            nest_asyncio.apply()
            from llama_parse import LlamaParse
        except ImportError as exc:
            logger.error(f"[LlamaParseProcessor] Missing dependency: {exc}")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "llamaparse_missing_dependency"},
            )

        suffix = os.path.splitext(filename)[1] or ".bin"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(content)
            tf_path = tf.name

        try:
            with LLAMAPARSE_LOCK:
                parser = LlamaParse(
                    api_key=settings.LLAMA_CLOUD_API_KEY,
                    result_type="markdown",
                    verbose=False,
                )
                documents = parser.load_data(tf_path)
        finally:
            try:
                os.remove(tf_path)
            except Exception:
                pass

        if not documents:
            return ProcessedDocument(chunks=[], file_type=self.file_type)

        full_text = "\n\n".join([doc.text for doc in documents if getattr(doc, "text", None)])
        if not full_text.strip():
            return ProcessedDocument(chunks=[], file_type=self.file_type)

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        raw_chunks = splitter.split_text(full_text)

        chunks = []
        total_tokens = 0
        for i, chunk_text in enumerate(raw_chunks):
            contextualized = f"[File: {filename}]\n{chunk_text}"
            token_count = self.count_tokens(contextualized)
            total_tokens += token_count
            chunks.append(
                ProcessedChunk(
                    content=contextualized,
                    metadata={
                        "file_type": self.file_type,
                        "parser": "llama_parse",
                        "filename": filename,
                    },
                    token_count=token_count,
                    chunk_index=i,
                )
            )

        return ProcessedDocument(
            chunks=chunks,
            file_type=self.file_type,
            total_tokens=total_tokens,
            metadata={"parser": "llama_parse"},
        )


# =============================================================================
# LEGACY OFFICE PROCESSOR
# =============================================================================

class LegacyOfficeProcessor(BaseProcessor):
    """Processor for legacy Office formats routed to LlamaParse."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        ext = os.path.splitext(filename)[1].lower().lstrip(".") or "legacy_office"
        return LlamaParseProcessor(file_type=ext).process(content, filename)


# =============================================================================
# IMAGE PROCESSOR
# =============================================================================

class ImageProcessor(BaseProcessor):
    """Processor for images routed to LlamaParse OCR."""

    def process(self, content: bytes, filename: str) -> ProcessedDocument:
        return LlamaParseProcessor(file_type="image").process(content, filename)


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
        
        # Remove null bytes that cannot be stored in Postgres text
        text = text.replace("\x00", "")
        
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
        ".ini": CodeProcessor,
        ".conf": CodeProcessor,
        ".config": CodeProcessor,
        ".sh": CodeProcessor,
        ".dockerfile": CodeProcessor,
        ".html": HTMLProcessor,
        ".css": CodeProcessor,
        ".sql": CodeProcessor,
        
        # Markdown
        ".md": MarkdownProcessor,
        ".markdown": MarkdownProcessor,
        
        # PDF
        ".pdf": PDFProcessor,
        
        # Word documents
        ".docx": DocxProcessor,
        ".doc": LegacyOfficeProcessor,

        # Spreadsheets
        ".csv": CSVProcessor,
        ".tsv": CSVProcessor,
        ".xlsx": ExcelProcessor,
        ".xls": LegacyOfficeProcessor,

        # Presentations
        ".pptx": PPTXProcessor,
        ".ppt": LegacyOfficeProcessor,

        # Rich text / email
        ".rtf": LegacyOfficeProcessor,
        ".msg": EmailProcessor,
        ".eml": EmailProcessor,

        # Images (OCR)
        ".jpg": ImageProcessor,
        ".jpeg": ImageProcessor,
        ".png": ImageProcessor,
        ".tiff": ImageProcessor,
        ".bmp": ImageProcessor,
        
        # Plain text
        ".txt": PlainTextProcessor,
        ".log": PlainTextProcessor,
    }
    
    # MIME type fallback mapping
    MIME_MAP = {
        "application/pdf": PDFProcessor,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": DocxProcessor,
        "application/msword": LegacyOfficeProcessor,
        "text/markdown": MarkdownProcessor,
        "text/plain": PlainTextProcessor,
        "text/html": HTMLProcessor,
        "text/csv": CSVProcessor,
        "application/json": CodeProcessor,
        "application/xml": CodeProcessor,
        "text/xml": CodeProcessor,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ExcelProcessor,
        "application/vnd.ms-excel": LegacyOfficeProcessor,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": PPTXProcessor,
        "application/vnd.ms-powerpoint": LegacyOfficeProcessor,
        "message/rfc822": EmailProcessor,
        "application/vnd.ms-outlook": EmailProcessor,
        "application/rtf": LegacyOfficeProcessor,
        "image/jpeg": ImageProcessor,
        "image/jpg": ImageProcessor,
        "image/png": ImageProcessor,
        "image/tiff": ImageProcessor,
        "image/bmp": ImageProcessor,
    }

    # Explicitly unsupported (binary) extensions to avoid unsafe parsing
    UNSUPPORTED_EXTENSIONS = {
        ".numbers",
        ".key",
    }

    TEXT_MIME_TYPES = {
        "text/plain",
        "text/markdown",
        "text/csv",
        "text/html",
        "text/xml",
        "application/json",
        "application/xml",
        "application/xhtml+xml",
        "application/x-yaml",
    }

    @staticmethod
    def _looks_like_binary(content: bytes) -> bool:
        if not content:
            return False
        if b"\x00" in content:
            return True
        sample = content[:2048]
        if not sample:
            return False
        non_text = 0
        for byte in sample:
            if byte < 9 or (14 <= byte < 32) or byte == 127:
                non_text += 1
        return (non_text / len(sample)) > 0.30
    
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
        if not ext and filename and filename.lower() == "dockerfile":
            ext = ".dockerfile"
        
        processor_class = cls.PROCESSOR_MAP.get(ext)
        
        if not processor_class and mime_type:
            processor_class = cls.MIME_MAP.get(mime_type)
        
        if not processor_class:
            if ext in cls.UNSUPPORTED_EXTENSIONS:
                logger.warning(f"[Factory] Unsupported file type {ext}, skipping parse")
                return ProcessedDocument(
                    chunks=[],
                    file_type="unsupported",
                    metadata={"unsupported_reason": "unsupported_extension"}
                )
            if mime_type and (mime_type.startswith("text/") or mime_type in cls.TEXT_MIME_TYPES):
                processor_class = PlainTextProcessor
            elif not cls._looks_like_binary(content):
                processor_class = PlainTextProcessor
            else:
                logger.warning(f"[Factory] Binary content detected for {ext}, skipping parse")
                return ProcessedDocument(
                    chunks=[],
                    file_type="unsupported",
                    metadata={"unsupported_reason": "binary_content"}
                )

        if processor_class is PlainTextProcessor and cls._looks_like_binary(content):
            logger.warning(f"[Factory] Binary content detected for {ext}, skipping plain text parse")
            return ProcessedDocument(
                chunks=[],
                file_type="unsupported",
                metadata={"unsupported_reason": "binary_content"}
            )
        
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
# ROUTING HELPERS
# =============================================================================

def route_file(file_size: int, extension: str) -> str:
    """Route structured files based on size limits (no heavy queue yet)."""
    from core.config import settings

    if extension in {".csv", ".tsv", ".xlsx"}:
        if file_size > settings.MAX_STRUCTURED_FILE_SIZE:
            return "skipped_file_too_large"
    return "queues.parsing"


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
        'application/msword': 'doc',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
        'application/vnd.ms-excel': 'xls',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
        'application/vnd.ms-powerpoint': 'ppt',
        'text/plain': 'text',
        'text/markdown': 'text',
        'text/csv': 'text',
        'text/html': 'text',
        'application/xml': 'text',
        'text/xml': 'text',
        'message/rfc822': 'email',
        'application/vnd.ms-outlook': 'email',
        'application/rtf': 'rtf',
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
