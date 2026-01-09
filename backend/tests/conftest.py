"""
Pytest Fixtures and Configuration

Provides shared fixtures for all tests including:
- Mock Supabase client
- Test user authentication
- API test client
"""

import os
import sys

_TEST_ENV_VARS = {
    "ENVIRONMENT": "test",
    "SENTRY_DSN": "",
    "SUPABASE_URL": "http://localhost:54321",
    "SUPABASE_SECRET_KEY": "test-secret",
    "SUPABASE_JWT_SECRET": "test-jwt-secret-key-that-is-long-enough-for-hs256",
    "OPENAI_API_KEY": "test-openai-key",
    "ALLOWED_ORIGINS": "http://localhost:3000",
    # Valid Fernet key (must be 32 url-safe base64-encoded bytes)
    "ENCRYPTION_KEY": "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
}

for key, value in _TEST_ENV_VARS.items():
    os.environ.setdefault(key, value)

# Add backend to path early so module imports resolve during collection.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import asyncio
from uuid import uuid4

from services.ingestion_pipeline import IngestionPipeline
from connectors.enhanced import SourceDocument, SourceType


# =============================================================================
# Application Fixtures
# =============================================================================

@pytest.fixture
def app():
    """Create a test FastAPI application."""
    from main import app
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def authenticated_client(client):
    """Create a test client with authentication headers."""
    # Mock JWT token for testing
    test_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXItaWQiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20ifQ.test"
    client.headers["Authorization"] = f"Bearer {test_token}"
    return client


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    mock = Mock()
    
    # Mock table operations
    mock.table.return_value.select.return_value.execute.return_value.data = []
    mock.table.return_value.insert.return_value.execute.return_value.data = [{"id": "test-id"}]
    mock.table.return_value.update.return_value.execute.return_value.data = [{"id": "test-id"}]
    mock.table.return_value.delete.return_value.execute.return_value.data = []
    
    # Mock RPC calls
    mock.rpc.return_value.execute.return_value.data = []
    
    return mock


@pytest.fixture
def mock_openai_embeddings():
    """Create a mock OpenAI embeddings model."""
    mock = Mock()
    # Return a fake 1536-dimensional embedding
    mock.embed_query.return_value = [0.1] * 1536
    mock.embed_documents.return_value = [[0.1] * 1536]
    return mock


@pytest.fixture
def mock_user_id():
    """Return a test user ID."""
    return "test-user-123"


@pytest.fixture
def sample_document():
    """Return a sample document for testing."""
    return {
        "id": "doc-1",
        "user_id": "test-user-123",
        "title": "Test Document",
        "source_type": "file_upload",
        "source_url": None,
        "created_at": "2024-01-01T00:00:00Z",
        "status": "indexed",
        "content": "This is a test document with some content for testing purposes.",
        "metadata": {"filename": "test.txt"}
    }


@pytest.fixture
def sample_chunks():
    """Return sample document chunks for testing."""
    return [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "content": "This is the first chunk of content.",
            "chunk_index": 0,
            "embedding": [0.1] * 1536
        },
        {
            "id": "chunk-2",
            "document_id": "doc-1",
            "content": "This is the second chunk of content.",
            "chunk_index": 1,
            "embedding": [0.2] * 1536
        }
    ]


# =============================================================================
# Async Fixtures
# =============================================================================

@pytest.fixture
def mock_async_supabase():
    """Create an async mock Supabase client."""
    mock = AsyncMock()
    mock.table.return_value.select.return_value.execute = AsyncMock(return_value=Mock(data=[]))
    mock.rpc = AsyncMock(return_value=Mock(data=[]))
    return mock


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def mock_environment(monkeypatch):
    """Set up test environment variables."""
    for key, value in _TEST_ENV_VARS.items():
        monkeypatch.setenv(key, value)


# =============================================================================
# Ingestion Pipeline Fixtures
# =============================================================================

@pytest.fixture
def ingestion_pipeline():
    pipeline = IngestionPipeline(
        user_id=str(uuid4()),
        job_id=str(uuid4()),
        supabase_client=Mock()
    )
    pipeline._update_job_status = Mock()
    pipeline._update_job_total = Mock()
    pipeline._create_notification = Mock()
    pipeline._create_file_status = Mock(return_value="file-status-id")
    pipeline._update_file_status = Mock()
    pipeline._update_chunk_progress = Mock()
    pipeline._store_document = AsyncMock(return_value="doc-id")
    return pipeline


@pytest.fixture
def sample_source_document():
    return SourceDocument(
        content=b"sample content",
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="file-1",
        filename="sample.pdf",
        mime_type="application/pdf",
        size_bytes=100
    )


@pytest.fixture
def sample_text_document():
    return SourceDocument(
        content=b"sample text",
        metadata={},
        source_type=SourceType.FILE_UPLOAD,
        source_id="file-2",
        filename="sample.txt",
        mime_type="text/plain",
        size_bytes=50
    )


@pytest.fixture
def benchmark_documents():
    docs = []
    for i in range(10):
        docs.append(SourceDocument(
            content=f"content-{i}".encode(),
            metadata={"index": i},
            source_type=SourceType.FILE_UPLOAD,
            source_id=f"bench-{i}",
            filename=f"bench_{i}.txt",
            mime_type="text/plain",
            size_bytes=50
        ))
    return docs


@pytest.fixture
def mock_document_processor():
    mock_result = Mock()
    mock_result.file_type = "txt"
    mock_result.metadata = {}
    mock_result.chunks = [
        Mock(content="chunk-1", token_count=5, metadata={}),
        Mock(content="chunk-2", token_count=5, metadata={}),
        Mock(content="chunk-3", token_count=5, metadata={}),
    ]
    with patch("services.ingestion_pipeline.DocumentProcessorFactory") as mock_factory:
        mock_factory.process.return_value = mock_result
        yield mock_factory


@pytest.fixture
def mock_embeddings():
    async def _fake_embeddings(texts, token_counts=None):
        return [[0.1] * 1536 for _ in texts]

    with patch("services.ingestion_pipeline.get_embeddings", new=AsyncMock(side_effect=_fake_embeddings)):
        yield


@pytest.fixture
def mock_quota_check():
    with patch.object(IngestionPipeline, "_check_quota", new=AsyncMock(return_value={"allowed": True, "reason": ""})):
        yield


@pytest.fixture
def mock_quota_exceeded():
    with patch.object(IngestionPipeline, "_check_quota", new=AsyncMock(return_value={"allowed": False, "reason": "quota"})):
        yield


@pytest.fixture
def benchmark():
    def _run(fn):
        return fn()

    return _run
