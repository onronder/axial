import builtins
import importlib
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from services.parsers import (
    CodeProcessor,
    MarkdownProcessor,
    PlainTextProcessor,
    CSVProcessor,
    HTMLProcessor,
    PDFProcessor,
    DocxProcessor,
    ImageProcessor,
    DocumentProcessorFactory,
    DocumentParser,
    BaseProcessor,
    OCRNotAvailableException,
)


def test_code_processor_processes_code():
    processor = CodeProcessor()
    result = processor.process(b"print('hi')\n", "test.py")
    assert result.file_type == "code"
    assert result.chunks


def test_code_processor_handles_decode_error():
    processor = CodeProcessor()
    result = processor.process(b"\xff", "bad.py")
    assert result.file_type == "code"


def test_code_processor_empty_content_returns_no_chunks():
    processor = CodeProcessor()
    result = processor.process(b"   ", "empty.py")
    assert result.chunks == []


def test_code_processor_uses_generic_splitter():
    processor = CodeProcessor()
    splitter = MagicMock()
    splitter.split_text.return_value = ["chunk"]

    with patch("services.parsers.RecursiveCharacterTextSplitter", return_value=splitter):
        result = processor.process(b"data", "config.json")

    assert result.chunks
    splitter.split_text.assert_called_once()


def test_markdown_processor_injects_context():
    processor = MarkdownProcessor()
    md = b"# Title\n\nContent here"
    result = processor.process(md, "readme.md")
    assert result.file_type == "markdown"
    assert any("[Context:" in chunk.content for chunk in result.chunks)


def test_markdown_processor_handles_decode_error():
    processor = MarkdownProcessor()
    result = processor.process(b"\xff", "bad.md")
    assert result.file_type == "markdown"


def test_markdown_processor_returns_empty_on_blank_input():
    processor = MarkdownProcessor()
    result = processor.process(b"   ", "empty.md")
    assert result.chunks == []


def test_markdown_processor_fallback_on_header_error():
    processor = MarkdownProcessor()
    md = b"# Title\n\nContent here"
    with patch("services.parsers.MarkdownHeaderTextSplitter.split_text", side_effect=Exception("boom")):
        result = processor.process(md, "readme.md")

    assert result.chunks


def test_code_processor_force_splits_large_chunk():
    processor = CodeProcessor()
    long_text = "a" * 5000

    splitter = MagicMock()
    splitter.split_text.return_value = [long_text]

    with patch("services.parsers.RecursiveCharacterTextSplitter.from_language", return_value=splitter), \
         patch.object(CodeProcessor, "count_tokens", return_value=3001):
        result = processor.process(long_text.encode("utf-8"), "test.py")

    assert len(result.chunks) > 1
    assert result.chunks[0].chunk_index == 0


def test_base_processor_count_tokens_fallback(monkeypatch):
    from services import parsers as parsers_module
    monkeypatch.setattr(parsers_module, "TIKTOKEN_ENCODER", None)
    assert parsers_module.BaseProcessor.count_tokens("abcd") == 1


def test_base_processor_process_placeholder():
    class Dummy(BaseProcessor):
        def process(self, content: bytes, filename: str):
            return super().process(content, filename)

    processor = Dummy()
    assert processor.process(b"data", "file.txt") is None


def test_parsers_import_handles_tiktoken_failure(monkeypatch):
    import services.parsers as parsers_module

    global CodeProcessor
    global MarkdownProcessor
    global PlainTextProcessor
    global PDFProcessor
    global DocxProcessor
    global DocumentProcessorFactory
    global DocumentParser

    def broken_encoder(_name):
        raise Exception("boom")

    original_encoder = parsers_module.tiktoken.get_encoding
    monkeypatch.setattr(parsers_module.tiktoken, "get_encoding", broken_encoder)
    reloaded = importlib.reload(parsers_module)
    assert reloaded.TIKTOKEN_ENCODER is None
    monkeypatch.setattr(reloaded.tiktoken, "get_encoding", original_encoder, raising=False)
    reloaded = importlib.reload(reloaded)

    CodeProcessor = reloaded.CodeProcessor
    MarkdownProcessor = reloaded.MarkdownProcessor
    PlainTextProcessor = reloaded.PlainTextProcessor
    PDFProcessor = reloaded.PDFProcessor
    DocxProcessor = reloaded.DocxProcessor
    DocumentProcessorFactory = reloaded.DocumentProcessorFactory
    DocumentParser = reloaded.DocumentParser


def test_pdf_processor_uses_llamaparse_when_available(monkeypatch):
    processor = PDFProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")
    expected = SimpleNamespace(chunks=["chunk"], file_type="pdf", total_tokens=100)

    with patch.object(processor, "_process_with_llamaparse", return_value=expected) as mock_llama, \
         patch.object(processor, "_process_with_pymupdf") as mock_pdf:
        result = processor.process(b"%PDF", "file.pdf")

    assert result is expected
    mock_llama.assert_called_once()
    mock_pdf.assert_not_called()


def test_pdf_processor_falls_back_on_llamaparse_error(monkeypatch):
    processor = PDFProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")
    fallback = SimpleNamespace(chunks=["chunk"], file_type="pdf", total_tokens=100, metadata={"text_length": 0})

    with patch.object(processor, "_process_with_llamaparse", side_effect=Exception("boom")) as mock_llama, \
         patch.object(processor, "_process_with_pymupdf", return_value=fallback) as mock_pdf:
        result = processor.process(b"%PDF", "file.pdf")

    assert result is fallback
    mock_llama.assert_called_once()
    mock_pdf.assert_called_once()


def test_pdf_processor_falls_back_when_no_api_key(monkeypatch):
    processor = PDFProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", None)
    fallback = SimpleNamespace(chunks=["chunk"], file_type="pdf", total_tokens=100, metadata={"text_length": 0})

    with patch.object(processor, "_process_with_llamaparse") as mock_llama, \
         patch.object(processor, "_process_with_pymupdf", return_value=fallback) as mock_pdf:
        result = processor.process(b"%PDF", "file.pdf")

    assert result is fallback
    mock_llama.assert_not_called()
    mock_pdf.assert_called_once()


def test_pdf_processor_falls_back_when_llamaparse_empty(monkeypatch):
    processor = PDFProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")
    empty = SimpleNamespace(chunks=[], file_type="pdf", total_tokens=0)
    fallback = SimpleNamespace(chunks=["chunk"], file_type="pdf", total_tokens=100, metadata={"text_length": 0})

    with patch.object(processor, "_process_with_llamaparse", return_value=empty) as mock_llama, \
         patch.object(processor, "_process_with_pymupdf", return_value=fallback) as mock_pdf:
        result = processor.process(b"%PDF", "file.pdf")

    assert result is fallback
    mock_llama.assert_called_once()
    mock_pdf.assert_called_once()


def test_pdf_processor_llamaparse_extracts_text(monkeypatch):
    processor = PDFProcessor()

    class FakeDoc:
        def __init__(self, text):
            self.text = text

    class FakeLlamaParse:
        def __init__(self, **_kwargs):
            pass

        def load_data(self, _path):
            return [FakeDoc("Hello world")]

    monkeypatch.setitem(sys.modules, "nest_asyncio", SimpleNamespace(apply=lambda: None))
    monkeypatch.setitem(sys.modules, "llama_parse", SimpleNamespace(LlamaParse=FakeLlamaParse))
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")

    result = processor._process_with_llamaparse(b"%PDF", "file.pdf")

    assert result.file_type == "pdf"
    assert result.metadata["parser"] == "llama_parse"
    assert result.chunks


def test_pdf_processor_llamaparse_handles_empty_docs(monkeypatch):
    processor = PDFProcessor()

    class FakeLlamaParse:
        def __init__(self, **_kwargs):
            pass

        def load_data(self, _path):
            return []

    monkeypatch.setitem(sys.modules, "nest_asyncio", SimpleNamespace(apply=lambda: None))
    monkeypatch.setitem(sys.modules, "llama_parse", SimpleNamespace(LlamaParse=FakeLlamaParse))
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")

    with patch.object(processor, "count_tokens", return_value=1):
        with patch("services.parsers.RecursiveCharacterTextSplitter.split_text", return_value=["chunk"]):
            with patch("services.parsers.logger"):
                with pytest.raises(ValueError):
                    processor._process_with_llamaparse(b"%PDF", "file.pdf")


def test_pdf_processor_llamaparse_import_error(monkeypatch):
    processor = PDFProcessor()
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "llama_parse":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError):
        processor._process_with_llamaparse(b"%PDF", "file.pdf")


def test_pdf_processor_llamaparse_empty_text_raises(monkeypatch):
    processor = PDFProcessor()

    class FakeDoc:
        text = "   "

    class FakeLlamaParse:
        def __init__(self, **_kwargs):
            pass

        def load_data(self, _path):
            return [FakeDoc()]

    monkeypatch.setitem(sys.modules, "nest_asyncio", SimpleNamespace(apply=lambda: None))
    monkeypatch.setitem(sys.modules, "llama_parse", SimpleNamespace(LlamaParse=FakeLlamaParse))
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")
    monkeypatch.setattr("services.parsers.os.remove", MagicMock(side_effect=Exception("rm")))

    with pytest.raises(ValueError):
        processor._process_with_llamaparse(b"%PDF", "file.pdf")


def test_pdf_processor_pymupdf_import_error(monkeypatch):
    processor = PDFProcessor()
    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    fallback = SimpleNamespace(chunks=["x"], file_type="pdf")
    with patch.object(processor, "_fallback_process", return_value=fallback):
        result = processor._process_with_pymupdf(b"%PDF", "file.pdf")

    assert result is fallback


def test_pdf_processor_pymupdf_success(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self._text = text

        def get_text(self, _mode):
            return self._text

    class FakeDoc:
        def __init__(self):
            self._pages = [FakePage("Page 1")]

        def __iter__(self):
            return iter(self._pages)

        def close(self):
            return None

    class FakeFitz:
        @staticmethod
        def open(*_args, **_kwargs):
            return FakeDoc()

    monkeypatch.setitem(sys.modules, "fitz", FakeFitz)
    processor = PDFProcessor()
    result = processor._process_with_pymupdf(b"%PDF", "file.pdf")

    assert result.file_type == "pdf"
    assert result.chunks
    assert result.metadata["parser"] == "pymupdf"


def test_pdf_processor_pymupdf_returns_empty_when_no_text(monkeypatch):
    class FakeDoc:
        def __iter__(self):
            return iter([])

        def close(self):
            return None

    class FakeFitz:
        @staticmethod
        def open(*_args, **_kwargs):
            return FakeDoc()

    monkeypatch.setitem(sys.modules, "fitz", FakeFitz)
    processor = PDFProcessor()
    result = processor._process_with_pymupdf(b"%PDF", "file.pdf")

    assert result.file_type == "pdf"
    assert result.chunks == []


def test_pdf_processor_clean_text_removes_noise():
    processor = PDFProcessor()
    cleaned = processor._clean_text("Page 1 of 2\nCONFIDENTIAL\nActual line")
    assert "CONFIDENTIAL" not in cleaned
    assert "Page 1" not in cleaned
    assert "Actual line" in cleaned


def test_docx_processor_handles_errors(monkeypatch):
    processor = DocxProcessor()
    module = SimpleNamespace(process=MagicMock(side_effect=Exception("fail")))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", None)
    # Mock OCR to also fail
    with patch.object(processor, "_process_with_embedded_image_ocr", side_effect=Exception("ocr fail")):
        result = processor.process(b"data", "file.docx")
    assert result.chunks == []


def test_docx_processor_processes_text(monkeypatch):
    processor = DocxProcessor()
    # Return enough text to pass threshold (50 tokens)
    long_text = "Hello world. " * 50  # ~150 words
    module = SimpleNamespace(process=MagicMock(return_value=long_text))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    result = processor.process(b"data", "file.docx")
    assert result.chunks
    assert result.metadata.get("parser") == "docx2txt"


def test_docx_processor_returns_empty_on_blank_text(monkeypatch):
    processor = DocxProcessor()
    module = SimpleNamespace(process=MagicMock(return_value="   "))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", None)
    # Mock OCR to return empty
    with patch.object(processor, "_process_with_embedded_image_ocr", 
                      return_value=SimpleNamespace(chunks=[], total_tokens=0)):
        result = processor.process(b"data", "file.docx")
    assert result.chunks == []


def test_docx_processor_triggers_ocr_on_low_content(monkeypatch):
    """Test that OCR is triggered when text extraction yields low content."""
    processor = DocxProcessor()
    # Return minimal text (below threshold)
    module = SimpleNamespace(process=MagicMock(return_value="short"))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", None)
    
    # Mock OCR to return good content
    ocr_result = SimpleNamespace(
        chunks=[SimpleNamespace(content="OCR text", metadata={}, token_count=100, chunk_index=0)],
        total_tokens=100,
        file_type="docx"
    )
    with patch.object(processor, "_process_with_embedded_image_ocr", return_value=ocr_result) as mock_ocr:
        result = processor.process(b"data", "file.docx")
    
    mock_ocr.assert_called_once()
    assert result.total_tokens == 100


def test_docx_processor_embedded_image_ocr(monkeypatch):
    """Test OCR of embedded images from DOCX."""
    import zipfile
    import io as io_module
    from PIL import Image
    
    processor = DocxProcessor()
    
    # Create a minimal DOCX (ZIP) with an embedded image
    docx_buffer = io_module.BytesIO()
    with zipfile.ZipFile(docx_buffer, 'w') as zf:
        # Create a simple test image
        img_buffer = io_module.BytesIO()
        img = Image.new('RGB', (100, 100), color='white')
        img.save(img_buffer, format='PNG')
        zf.writestr('word/media/image1.png', img_buffer.getvalue())
    
    docx_content = docx_buffer.getvalue()
    
    # Mock pytesseract
    mock_pytesseract = SimpleNamespace(image_to_string=MagicMock(return_value="Extracted OCR text from image"))
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor._process_with_embedded_image_ocr(docx_content, "test.docx")
    
    assert result.chunks
    assert "Extracted OCR text" in result.chunks[0].content


def test_docx_processor_skips_small_images(monkeypatch):
    """Test that small images (icons/bullets) are skipped."""
    import zipfile
    import io as io_module
    from PIL import Image
    
    processor = DocxProcessor()
    
    # Create a DOCX with a very small image (should be skipped)
    docx_buffer = io_module.BytesIO()
    with zipfile.ZipFile(docx_buffer, 'w') as zf:
        img_buffer = io_module.BytesIO()
        img = Image.new('RGB', (20, 20), color='white')  # Very small
        img.save(img_buffer, format='PNG')
        zf.writestr('word/media/image1.png', img_buffer.getvalue())
    
    docx_content = docx_buffer.getvalue()
    
    # Mock pytesseract (should not be called for small images)
    mock_pytesseract = SimpleNamespace(image_to_string=MagicMock(return_value="text"))
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor._process_with_embedded_image_ocr(docx_content, "test.docx")
    
    # Small images should be skipped, so no OCR text
    assert result.total_tokens == 0


def test_docx_processor_ocr_fallback_to_llamaparse(monkeypatch):
    """Test that LlamaParse is tried when OCR also fails."""
    processor = DocxProcessor()
    
    # Tier 1: Empty text
    module = SimpleNamespace(process=MagicMock(return_value=""))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    
    # Tier 2: OCR fails
    with patch.object(processor, "_process_with_embedded_image_ocr", 
                      return_value=SimpleNamespace(chunks=[], total_tokens=0)):
        # Tier 3: LlamaParse succeeds
        monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "test-key")
        llamaparse_result = SimpleNamespace(
            chunks=[SimpleNamespace(content="LlamaParse text", metadata={}, token_count=100, chunk_index=0)],
            total_tokens=100,
            file_type="docx"
        )
        
        with patch("services.parsers.LlamaParseProcessor") as mock_llama:
            mock_instance = MagicMock()
            mock_instance.process.return_value = llamaparse_result
            mock_llama.return_value = mock_instance
            
            with patch("services.parsers.LLAMAPARSE_CIRCUIT") as mock_circuit:
                mock_circuit.can_execute.return_value = (True, "closed")
                result = processor.process(b"data", "file.docx")
        
        assert result.total_tokens == 100


def test_docx_processor_clean_ocr_text():
    """Test OCR text cleaning."""
    processor = DocxProcessor()
    
    noisy_text = "\n\n\nHello  world.\n\n\n\n\n@#$%\nActual content here\n---"
    cleaned = processor._clean_ocr_text(noisy_text)
    
    assert "Hello world." in cleaned
    assert "Actual content here" in cleaned
    assert "\n\n\n\n" not in cleaned


def test_docx_processor_invalid_zip(monkeypatch):
    """Test handling of invalid DOCX (not a valid ZIP)."""
    from services.parsers import OCRNotAvailableException
    
    processor = DocxProcessor()
    mock_pytesseract = SimpleNamespace(image_to_string=MagicMock())
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    with pytest.raises(OCRNotAvailableException):
        processor._process_with_embedded_image_ocr(b"not a zip file", "invalid.docx")


def test_plain_text_processor_basic():
    processor = PlainTextProcessor()
    result = processor.process(b"hello world", "note.txt")
    assert result.file_type == "text"
    assert result.chunks


def test_plain_text_processor_handles_decode_error():
    processor = PlainTextProcessor()
    result = processor.process(b"\xff", "note.txt")
    assert result.chunks


def test_plain_text_processor_returns_empty_on_blank_text():
    processor = PlainTextProcessor()
    result = processor.process(b"   ", "note.txt")
    assert result.chunks == []


def test_factory_unsupported_extension():
    result = DocumentProcessorFactory.process(content=b"data", filename="file.numbers")
    assert result.file_type == "unsupported"
    assert result.metadata["unsupported_reason"] == "unsupported_extension"


def test_factory_binary_detection():
    result = DocumentProcessorFactory.process(content=b"\x00\x01\x02", filename="file.bin")
    assert result.file_type == "unsupported"
    assert result.metadata["unsupported_reason"] == "binary_content"


def test_factory_text_mime_fallback():
    result = DocumentProcessorFactory.process(content=b"hello", filename="file.unknown", mime_type="text/plain")
    assert result.file_type in {"text", "markdown", "code"}


def test_process_web_content_adds_source_url():
    result = DocumentProcessorFactory.process_web_content("Hello", "https://example.com")
    assert result.chunks
    assert result.chunks[0].metadata["source_url"] == "https://example.com"


def test_document_parser_extract_text():
    text = DocumentParser.extract_text(b"hello", "text/plain")
    assert "hello" in text


def test_document_parser_parse_file():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=True) as handle:
        handle.write("sample text")
        handle.flush()
        text = DocumentParser.parse_file(handle.name)
    assert "sample text" in text


def test_document_parser_is_supported():
    assert DocumentParser.is_supported("text/plain") is True
    assert DocumentParser.is_supported("application/unknown") is False


def test_markdown_builds_header_path():
    processor = MarkdownProcessor()
    metadata = {"Header1": "# Title", "Header2": "Section", "Header3": "Sub"}
    path = processor._build_header_path(metadata)
    assert path == "Title > Section > Sub"


def test_plain_text_processor_strips_null_bytes():
    processor = PlainTextProcessor()
    result = processor.process(b"hello\x00world", "note.txt")
    assert result.chunks
    assert "\x00" not in result.chunks[0].content


def test_csv_processor_structured_output():
    """Test CSV processing - skipped if pandas not installed."""
    try:
        import pandas  # noqa: F401
    except ImportError:
        pytest.skip("pandas not installed")
    processor = CSVProcessor()
    result = processor.process(b"name,value\nAlice,100", "test.csv")
    assert result.file_type == "csv"
    assert result.chunks
    assert "name:" in result.chunks[0].content.lower()


def test_html_processor_strips_tags():
    processor = HTMLProcessor()
    result = processor.process(b"<html><body><h1>Title</h1></body></html>", "page.html")
    assert result.file_type == "html"
    assert result.chunks
    assert "Title" in result.chunks[0].content


def test_factory_looks_like_binary():
    assert DocumentProcessorFactory._looks_like_binary(b"") is False


def test_factory_looks_like_binary_empty_sample():
    class DummyBytes:
        def __len__(self):
            return 1

        def __contains__(self, _needle):
            return False

        def __getitem__(self, _slice):
            if not isinstance(_slice, slice):
                raise IndexError
            return b""

    assert DocumentProcessorFactory._looks_like_binary(DummyBytes()) is False
    assert DocumentProcessorFactory._looks_like_binary(b"\x00\x01") is True
    assert DocumentProcessorFactory._looks_like_binary(b"normal text") is False
    assert DocumentProcessorFactory._looks_like_binary(bytes(range(1, 50))) is True


def test_factory_returns_unknown_for_missing_content():
    result = DocumentProcessorFactory.process(content=b"", filename="empty.txt")
    assert result.file_type == "unknown"


def test_factory_uses_text_mime_type_when_unknown_extension():
    result = DocumentProcessorFactory.process(content=b"hello", filename="file.unknown", mime_type="text/csv")
    # May return "unsupported" if pandas is not installed for CSV processing
    assert result.file_type in {"text", "csv", "unsupported"}


def test_factory_plain_text_when_not_binary():
    result = DocumentProcessorFactory.process(content=b"hello", filename="file.unknown")
    assert result.file_type == "text"


def test_factory_rejects_binary_plain_text():
    result = DocumentProcessorFactory.process(content=b"\x00binary", filename="file.txt")
    assert result.file_type == "unsupported"
    assert result.metadata["unsupported_reason"] == "binary_content"


def test_pdf_processor_fallback_processes_pages(monkeypatch):
    class FakePage:
        def __init__(self, text):
            self._text = text

        def extract_text(self):
            return self._text

    class FakeReader:
        def __init__(self, _stream):
            self.pages = [FakePage("Page 1"), FakePage("Page 2")]

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))
    processor = PDFProcessor()
    result = processor._fallback_process(b"%PDF", "file.pdf")
    assert result.chunks


def test_pdf_processor_pymupdf_falls_back_on_error(monkeypatch):
    class FakeFitz:
        @staticmethod
        def open(*_args, **_kwargs):
            raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "fitz", FakeFitz)
    processor = PDFProcessor()

    fallback = SimpleNamespace(chunks=["x"], file_type="pdf")
    with patch.object(processor, "_fallback_process", return_value=fallback):
        result = processor._process_with_pymupdf(b"%PDF", "file.pdf")

    assert result is fallback


def test_pdf_processor_fallback_handles_reader_error(monkeypatch):
    class FakeReader:
        def __init__(self, _stream):
            raise RuntimeError("boom")

    monkeypatch.setitem(sys.modules, "pypdf", SimpleNamespace(PdfReader=FakeReader))
    processor = PDFProcessor()
    result = processor._fallback_process(b"%PDF", "file.pdf")
    assert result.chunks == []


# =============================================================================
# IMAGE PROCESSOR TESTS
# =============================================================================

def test_image_processor_tesseract_success(monkeypatch):
    """Test ImageProcessor with successful Tesseract OCR."""
    from PIL import Image
    import io as io_module
    
    processor = ImageProcessor()
    
    # Create a test image
    img_buffer = io_module.BytesIO()
    img = Image.new('RGB', (100, 100), color='white')
    img.save(img_buffer, format='PNG')
    img_content = img_buffer.getvalue()
    
    # Mock pytesseract to return good text
    mock_pytesseract = SimpleNamespace(
        image_to_string=MagicMock(return_value="This is OCR extracted text from the image.")
    )
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor._process_with_tesseract(img_content, "test.png")
    
    assert result.chunks
    assert result.metadata.get("parser") == "tesseract_ocr"
    assert "OCR extracted text" in result.chunks[0].content


def test_image_processor_tesseract_empty_result(monkeypatch):
    """Test ImageProcessor when Tesseract returns empty text."""
    from PIL import Image
    import io as io_module
    
    processor = ImageProcessor()
    
    # Create a test image
    img_buffer = io_module.BytesIO()
    img = Image.new('RGB', (100, 100), color='white')
    img.save(img_buffer, format='PNG')
    img_content = img_buffer.getvalue()
    
    # Mock pytesseract to return empty text
    mock_pytesseract = SimpleNamespace(image_to_string=MagicMock(return_value="   "))
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor._process_with_tesseract(img_content, "test.png")
    
    assert result.chunks == []
    assert result.total_tokens == 0


def test_image_processor_fallback_to_llamaparse(monkeypatch):
    """Test ImageProcessor falls back to LlamaParse when Tesseract fails."""
    processor = ImageProcessor()
    
    # Tier 1: Tesseract fails
    with patch.object(processor, "_process_with_tesseract", 
                      return_value=SimpleNamespace(chunks=[], total_tokens=0)):
        # Tier 2: LlamaParse succeeds
        monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "test-key")
        llamaparse_result = SimpleNamespace(
            chunks=[SimpleNamespace(content="LlamaParse text", metadata={}, token_count=100, chunk_index=0)],
            total_tokens=100,
            file_type="image"
        )
        
        with patch("services.parsers.LlamaParseProcessor") as mock_llama:
            mock_instance = MagicMock()
            mock_instance.process.return_value = llamaparse_result
            mock_llama.return_value = mock_instance
            
            with patch("services.parsers.LLAMAPARSE_CIRCUIT") as mock_circuit:
                mock_circuit.can_execute.return_value = (True, "closed")
                result = processor.process(b"image data", "test.png")
        
        assert result.total_tokens == 100


def test_image_processor_ocr_not_available(monkeypatch):
    """Test ImageProcessor when OCR dependencies are missing."""
    processor = ImageProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", None)
    
    # Mock import error for pytesseract
    with patch.object(processor, "_process_with_tesseract", 
                      side_effect=OCRNotAvailableException("pytesseract not installed")):
        result = processor.process(b"image data", "test.png")
    
    assert result.chunks == []


def test_image_processor_handles_rgba_images(monkeypatch):
    """Test ImageProcessor handles RGBA images with transparency."""
    from PIL import Image
    import io as io_module
    
    processor = ImageProcessor()
    
    # Create a RGBA image with transparency
    img_buffer = io_module.BytesIO()
    img = Image.new('RGBA', (100, 100), color=(255, 255, 255, 128))
    img.save(img_buffer, format='PNG')
    img_content = img_buffer.getvalue()
    
    # Mock pytesseract
    mock_pytesseract = SimpleNamespace(
        image_to_string=MagicMock(return_value="Text from RGBA image")
    )
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor._process_with_tesseract(img_content, "test.png")
    
    assert result.chunks
    assert "Text from RGBA image" in result.chunks[0].content


def test_image_processor_clean_ocr_text():
    """Test ImageProcessor OCR text cleaning."""
    processor = ImageProcessor()
    
    noisy_text = "\n\n\n!@#\nActual text content\n---\n\n\n"
    cleaned = processor._clean_ocr_text(noisy_text)
    
    assert "Actual text content" in cleaned
    assert "\n\n\n" not in cleaned


def test_image_processor_full_flow(monkeypatch):
    """Test full ImageProcessor flow with local Tesseract success."""
    from PIL import Image
    import io as io_module
    
    processor = ImageProcessor()
    
    # Create a test image
    img_buffer = io_module.BytesIO()
    img = Image.new('RGB', (200, 200), color='white')
    img.save(img_buffer, format='JPEG')
    img_content = img_buffer.getvalue()
    
    # Mock pytesseract with enough text to pass threshold
    long_text = "This is extracted text from the image. " * 10
    mock_pytesseract = SimpleNamespace(image_to_string=MagicMock(return_value=long_text))
    monkeypatch.setitem(sys.modules, "pytesseract", mock_pytesseract)
    
    result = processor.process(img_content, "test.jpg")
    
    assert result.chunks
    assert result.file_type == "image"
    assert result.metadata.get("parser") == "tesseract_ocr"
