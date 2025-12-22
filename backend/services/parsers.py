"""
Unified Document Parser Service

Single source of truth for text extraction from various file formats.
Supports: PDF, DOCX, plain text, and more.
"""

import io
import logging

# Optional imports with graceful fallback
try:
    import docx2txt
    HAS_DOCX_SUPPORT = True
except ImportError:
    HAS_DOCX_SUPPORT = False
    docx2txt = None

try:
    from pypdf import PdfReader
    HAS_PDF_SUPPORT = True
except ImportError:
    HAS_PDF_SUPPORT = False
    PdfReader = None

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Centralized document parser that extracts text from various file formats.
    
    All connectors (Drive, Local, Web, etc.) should use this service
    instead of implementing their own parsing logic.
    
    Supported formats:
    - PDF (.pdf)
    - Word Documents (.docx, .doc)
    - Plain text (.txt, .md, .csv, etc.)
    """
    
    # MIME type to format mapping
    SUPPORTED_FORMATS = {
        # PDF
        'application/pdf': 'pdf',
        
        # Word Documents
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
        'application/msword': 'docx',
        
        # Plain text
        'text/plain': 'text',
        'text/markdown': 'text',
        'text/csv': 'text',
        'text/html': 'text',
        
        # Google Docs (already exported as text before reaching here)
        'application/vnd.google-apps.document': 'text',
    }
    
    @staticmethod
    def extract_text(file_content: bytes, mime_type: str) -> str:
        """
        Extract text content from file bytes based on MIME type.
        
        Args:
            file_content: Raw file bytes
            mime_type: MIME type of the file (e.g., 'application/pdf')
            
        Returns:
            Extracted text content, or empty string if extraction fails
        """
        try:
            # Normalize mime type
            mime_type = mime_type.lower().strip()
            
            # Determine format
            format_type = DocumentParser.SUPPORTED_FORMATS.get(mime_type)
            
            if format_type == 'pdf':
                return DocumentParser._extract_pdf(file_content)
            elif format_type == 'docx':
                return DocumentParser._extract_docx(file_content)
            elif format_type == 'text' or mime_type.startswith('text/'):
                return DocumentParser._extract_text(file_content)
            else:
                logger.warning(f"[DocumentParser] Unsupported MIME type: {mime_type}")
                return ""
                
        except Exception as e:
            logger.error(f"[DocumentParser] Error extracting text from {mime_type}: {e}")
            return ""
    
    @staticmethod
    def _extract_pdf(file_content: bytes) -> str:
        """Extract text from PDF bytes."""
        if not HAS_PDF_SUPPORT:
            logger.warning("[DocumentParser] pypdf not installed, skipping PDF file")
            return ""
        
        try:
            reader = PdfReader(io.BytesIO(file_content))
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    logger.warning(f"[DocumentParser] Error extracting page {page_num}: {e}")
                    continue
            
            result = "\n\n".join(text_parts)
            logger.info(f"[DocumentParser] ✅ Extracted PDF: {len(result)} chars from {len(reader.pages)} pages")
            return result
            
        except Exception as e:
            logger.error(f"[DocumentParser] PDF extraction failed: {e}")
            return ""
    
    @staticmethod
    def _extract_docx(file_content: bytes) -> str:
        """Extract text from Word document bytes."""
        if not HAS_DOCX_SUPPORT:
            logger.warning("[DocumentParser] docx2txt not installed, skipping DOCX file")
            return ""
        
        try:
            text = docx2txt.process(io.BytesIO(file_content))
            if text:
                logger.info(f"[DocumentParser] ✅ Extracted DOCX: {len(text)} chars")
                return text
            return ""
            
        except Exception as e:
            logger.error(f"[DocumentParser] DOCX extraction failed: {e}")
            return ""
    
    @staticmethod
    def _extract_text(file_content: bytes) -> str:
        """Extract text from plain text file bytes."""
        try:
            # Try UTF-8 first, then fallback with error handling
            try:
                text = file_content.decode('utf-8')
            except UnicodeDecodeError:
                text = file_content.decode('utf-8', errors='replace')
                logger.warning("[DocumentParser] Used fallback encoding for text file")
            
            logger.info(f"[DocumentParser] ✅ Extracted text: {len(text)} chars")
            return text
            
        except Exception as e:
            logger.error(f"[DocumentParser] Text extraction failed: {e}")
            return ""
    
    @staticmethod
    def is_supported(mime_type: str) -> bool:
        """Check if a MIME type is supported for text extraction."""
        mime_type = mime_type.lower().strip()
        return (
            mime_type in DocumentParser.SUPPORTED_FORMATS or 
            mime_type.startswith('text/')
        )
