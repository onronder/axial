"""
Pytest Fixtures and Configuration

Provides shared fixtures for all tests including:
- Mock Supabase client
- Test user authentication
- API test client
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


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
        "source_type": "file",
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
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:3000")
