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
    DocumentProcessorFactory,
    DocumentParser,
    BaseProcessor,
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
    expected = SimpleNamespace(chunks=["chunk"], file_type="pdf")
    local = SimpleNamespace(chunks=[], file_type="pdf", metadata={"text_length": 0})

    with patch.object(processor, "_process_with_llamaparse", return_value=expected) as mock_llama, \
         patch.object(processor, "_process_with_pymupdf", return_value=local) as mock_pdf:
        result = processor.process(b"%PDF", "file.pdf")

    assert result is expected
    mock_llama.assert_called_once()
    mock_pdf.assert_called_once()


def test_pdf_processor_falls_back_on_llamaparse_error(monkeypatch):
    processor = PDFProcessor()
    monkeypatch.setattr("core.config.settings.LLAMA_CLOUD_API_KEY", "key")
    fallback = SimpleNamespace(chunks=["chunk"], file_type="pdf", metadata={"text_length": 0})

    with patch.object(processor, "_process_with_llamaparse", side_effect=Exception("boom")) as mock_llama, \
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
    result = processor.process(b"data", "file.docx")
    assert result.chunks == []


def test_docx_processor_processes_text(monkeypatch):
    processor = DocxProcessor()
    module = SimpleNamespace(process=MagicMock(return_value="Hello world"))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    result = processor.process(b"data", "file.docx")
    assert result.chunks


def test_docx_processor_returns_empty_on_blank_text(monkeypatch):
    processor = DocxProcessor()
    module = SimpleNamespace(process=MagicMock(return_value="   "))
    monkeypatch.setitem(sys.modules, "docx2txt", module)
    result = processor.process(b"data", "file.docx")
    assert result.chunks == []


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
    assert result.file_type in {"text", "csv"}


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
