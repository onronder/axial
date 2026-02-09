"""
Pytest Fixtures and Configuration

Provides shared fixtures for all tests including:
- Mock Supabase client
- Test user authentication
- API test client
- Rate limiter bypass for testing
"""

import os
import sys

_TEST_ENV_VARS = {
    "ENVIRONMENT": "test",
    "SENTRY_DSN": "",
    "REDIS_URL": "redis://localhost:6379/0",
    "SUPABASE_URL": "http://localhost:54321",
    "SUPABASE_SECRET_KEY": (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJpc3MiOiJ0ZXN0Iiwicm9sZSI6ImFub24ifQ."
        "dGVzdC1zaWduYXR1cmU"
    ),
    "SUPABASE_JWT_SECRET": "test-jwt-secret-key-that-is-long-enough-for-hs256",
    "OPENAI_API_KEY": "test-openai-key",
    "ALLOWED_ORIGINS": "http://localhost:3000",
    # Valid Fernet key (must be 32 url-safe base64-encoded bytes)
    "ENCRYPTION_KEY": "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY=",
    # Ghost Protocol: Chunk content encryption key (valid Fernet key)
    "CHUNK_ENCRYPTION_KEY": "LGNy0DAbgvEq4Tvl-d3DN6EFkhiSbpN5mq0zZ3XEN2w=",
    "CELERY_TASK_ALWAYS_EAGER": "1",
}

for key, value in _TEST_ENV_VARS.items():
    os.environ[key] = value

# Add backend to path early so module imports resolve during collection.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

# =============================================================================
# Rate Limiter Bypass - MUST be applied before importing rate-limited modules
# =============================================================================

def _noop_decorator(*args, **kwargs):
    """No-op decorator that passes through the function unchanged."""
    def decorator(func):
        return func
    # Handle both @limiter.limit("10/minute") and direct usage
    if len(args) == 1 and callable(args[0]):
        return args[0]
    return decorator


class _NoopLimiter:
    """Mock limiter that does nothing - for testing rate-limited endpoints."""
    def limit(self, *args, **kwargs):
        return _noop_decorator

    def shared_limit(self, *args, **kwargs):
        return _noop_decorator

    def exempt(self, func):
        return func


# Patch the rate limiter before any other imports use it
_mock_limiter = _NoopLimiter()
_mock_rate_limit_module = type(sys)('core.rate_limit')
_mock_rate_limit_module.limiter = _mock_limiter
_mock_rate_limit_module.RATE_LIMITS = {}

# Add the real functions that tests might import
def get_user_id_or_ip(request):
    """Mock implementation for testing."""
    user = getattr(getattr(request, 'state', None), 'user', None)
    if user and hasattr(user, 'id'):
        return f"user:{user.id}"
    return "127.0.0.1"

def rate_limit_exceeded_handler(request, exc):
    """Mock handler for rate limit exceeded."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit_exceeded", "detail": "Too many requests."},
        headers={"Retry-After": "60"}
    )

_mock_rate_limit_module.get_user_id_or_ip = get_user_id_or_ip
_mock_rate_limit_module.rate_limit_exceeded_handler = rate_limit_exceeded_handler

sys.modules['core.rate_limit'] = _mock_rate_limit_module


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


@pytest.fixture
def benchmark():
    def _run(fn):
        return fn()

    return _run


# =============================================================================
# Request/Response Fixtures
# =============================================================================

@pytest.fixture
def mock_request():
    """Create a mock Starlette Request for testing endpoints with rate limiters."""
    from starlette.requests import Request

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 12345),
        "app": None,
    }
    return Request(scope=scope)


@pytest.fixture
def mock_request_factory():
    """Factory fixture to create mock requests with different paths/methods."""
    from starlette.requests import Request

    def _create_request(
        method: str = "GET",
        path: str = "/",
        headers: list = None,
        query_string: bytes = b""
    ):
        scope = {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": query_string,
            "headers": headers or [],
            "server": ("testserver", 80),
            "client": ("127.0.0.1", 12345),
            "app": None,
        }
        return Request(scope=scope)

    return _create_request
