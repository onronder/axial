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
    PDFProcessor,
    DocxProcessor,
    TableProcessor,
    PresentationProcessor,
    DocumentProcessorFactory,
    DocumentParser,
    BaseProcessor,
)


# --- Code Processor Tests ---

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


# --- Markdown Processor Tests ---

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


# --- Table Processor Tests ---

def test_table_processor_csv():
    csv_content = b"col1,col2\nval1,val2\nval3,val4"
    with patch("services.parsers.pd") as mock_pd:
        mock_df = MagicMock()
        mock_df.iterrows.return_value = [
            (0, {"col1": "val1", "col2": "val2"}),
            (1, {"col1": "val3", "col2": "val4"})
        ]
        mock_df.columns.tolist.return_value = ["col1", "col2"]
        mock_df.__len__.return_value = 2
        mock_pd.read_csv.return_value = mock_df

        processor = TableProcessor()
        result = processor.process(csv_content, "data.csv")

        assert result.file_type == "table"
        assert result.metadata["rows"] == 2
        assert len(result.chunks) > 0
        assert "col1: val1" in result.chunks[0].content


def test_table_processor_missing_pandas():
    with patch("services.parsers.pd", None):
        processor = TableProcessor()
        result = processor.process(b"data", "file.csv")
        assert result.file_type == "table_error"


# --- Presentation Processor Tests ---

def test_presentation_processor():
    with patch("services.parsers.Presentation") as mock_prs:
        slide_mock = MagicMock()
        # Mock shapes iteration
        shape_mock = MagicMock()
        shape_mock.text = "Slide Content"

        # Configure the 'shapes' attribute of the slide
        # It needs to be iterable (yielding shape_mock) AND have a 'title' attribute
        shapes_collection = MagicMock()
        shapes_collection.__iter__.return_value = [shape_mock]
        shapes_collection.title.text = "Slide Title"

        slide_mock.shapes = shapes_collection

        mock_prs.return_value.slides = [slide_mock]

        processor = PresentationProcessor()
        result = processor.process(b"pkzip...", "slides.pptx")

        assert result.file_type == "presentation"
        assert "Slide Title" in result.chunks[0].content
        assert "Slide: 1" in result.chunks[0].content


def test_presentation_processor_missing_library():
    with patch("services.parsers.Presentation", None):
        processor = PresentationProcessor()
        result = processor.process(b"data", "file.pptx")
        assert result.file_type == "pptx_error"


# --- PDF Processor Tests ---

def test_pdf_processor_pymupdf_success():
    class FakePage:
        def get_text(self, mode):
            return "This is a normal PDF with plenty of text content to pass the density check."

    class FakeDoc:
        def __init__(self):
            self._pages = [FakePage()]
        def __iter__(self): return iter(self._pages)
        def __len__(self): return 1
        def close(self): pass

    # Use patch.dict for sys.modules because fitz is imported inside the method
    with patch.dict(sys.modules, {"fitz": MagicMock(open=MagicMock(return_value=FakeDoc()))}):
        processor = PDFProcessor()
        result = processor.process(b"%PDF", "file.pdf")

        assert result.file_type == "pdf"
        assert result.metadata["parser"] == "pymupdf"


def test_pdf_processor_ocr_fallback():
    # Mock PyMuPDF to return very little text (scanned)
    class FakePage:
        def get_text(self, mode):
            return "Scan" # Very low density

    class FakeDoc:
        def __init__(self):
            self._pages = [FakePage()]
        def __iter__(self): return iter(self._pages)
        def __len__(self): return 1
        def close(self): pass

    # Mock LlamaParse
    llama_result = SimpleNamespace(chunks=[SimpleNamespace(content="OCR Content", metadata={}, token_count=10, chunk_index=0)], file_type="pdf", total_tokens=10, metadata={"parser": "llama_parse"})

    with patch.dict(sys.modules, {"fitz": MagicMock(open=MagicMock(return_value=FakeDoc()))}):
        with patch("core.config.settings.LLAMA_CLOUD_API_KEY", "valid_key"):
            with patch.object(PDFProcessor, "_process_with_llamaparse", return_value=llama_result) as mock_llama:

                processor = PDFProcessor()
                result = processor.process(b"%PDF", "scanned.pdf")

                mock_llama.assert_called_once()
                assert result.metadata["parser"] == "llama_parse"


def test_pdf_processor_no_fallback_without_key():
    # Mock PyMuPDF to return scan
    class FakePage:
        def get_text(self, mode): return "Scan"

    class FakeDoc:
        def __init__(self): self._pages = [FakePage()]
        def __iter__(self): return iter(self._pages)
        def __len__(self): return 1
        def close(self): pass

    with patch.dict(sys.modules, {"fitz": MagicMock(open=MagicMock(return_value=FakeDoc()))}):
        with patch("core.config.settings.LLAMA_CLOUD_API_KEY", None):

            processor = PDFProcessor()
            result = processor.process(b"%PDF", "scanned.pdf")

            # Should stay with pymupdf result despite low density
            assert result.metadata["parser"] == "pymupdf"


# --- Factory Tests ---

def test_factory_routes_pptx():
    with patch("services.parsers.PresentationProcessor.process") as mock_process:
        DocumentProcessorFactory.process(content=b"data", filename="deck.pptx")
        mock_process.assert_called_once()

def test_factory_routes_csv():
    with patch("services.parsers.TableProcessor.process") as mock_process:
        DocumentProcessorFactory.process(content=b"data", filename="sheet.csv")
        mock_process.assert_called_once()

def test_factory_binary_detection_skips_text():
    # If we pass binary content as .txt, it should skip
    result = DocumentProcessorFactory.process(content=b"\x00\x01\x02", filename="file.txt")
    assert result.file_type == "binary_skip"

def test_factory_explicit_unsupported():
    # .key is in UNSUPPORTED_EXTENSIONS
    result = DocumentProcessorFactory.process(content=b"data", filename="pres.key")
    assert result.file_type == "unsupported"


# --- Legacy Compatibility Tests ---

def test_document_parser_legacy_interface():
    # Ensure the wrapper still works
    with patch("services.parsers.DocumentProcessorFactory.process") as mock_factory:
        mock_factory.return_value = SimpleNamespace(
            chunks=[SimpleNamespace(content="Chunk 1"), SimpleNamespace(content="Chunk 2")]
        )
        text = DocumentParser.extract_text(b"data", "text/plain")
        assert text == "Chunk 1\n\nChunk 2"
