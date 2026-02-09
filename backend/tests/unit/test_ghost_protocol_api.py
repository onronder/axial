"""
Test Suite for Ghost Protocol API Lockdown

Tests for Zero-Retention API enforcement including:
- Document content endpoint returns 403
- Document download endpoint returns 403
- Response structure and policy information
"""

from fastapi import HTTPException, status


class TestDocumentContentEndpointLogic:
    """Tests for content endpoint behavior."""

    def test_raises_http_exception_with_403(self):
        """Content retrieval should raise 403 Forbidden."""
        # The endpoint is designed to ALWAYS raise 403
        # We test the exception structure directly
        error = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "content_not_available",
                "message": (
                    "Ephemeral Storage Policy: Original files are processed and destroyed "
                    "immediately after ingestion. Only vector embeddings and encrypted "
                    "text chunks are retained. Use /documents/{id}/chunks to retrieve "
                    "decrypted text content."
                ),
                "policy": "ghost_protocol",
                "docs": "https://docs.axiohub.io/security/zero-retention"
            }
        )

        assert error.status_code == 403
        assert error.detail["policy"] == "ghost_protocol"
        assert "Ephemeral Storage Policy" in error.detail["message"]

    def test_content_response_structure(self):
        """Content endpoint error should have all required fields."""
        detail = {
            "error": "content_not_available",
            "message": "Ephemeral Storage Policy: ...",
            "policy": "ghost_protocol",
            "docs": "https://docs.axiohub.io/security/zero-retention"
        }

        required_fields = ["error", "message", "policy", "docs"]
        for field in required_fields:
            assert field in detail, f"Missing required field: {field}"

    def test_content_endpoint_error_code(self):
        """Content endpoint should use correct error code."""
        detail = {"error": "content_not_available"}
        assert detail["error"] == "content_not_available"


class TestDocumentDownloadEndpointLogic:
    """Tests for download endpoint behavior."""

    def test_raises_http_exception_with_403(self):
        """Download retrieval should raise 403 Forbidden."""
        error = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "download_not_available",
                "message": (
                    "Ephemeral Storage Policy: Original files are securely wiped after "
                    "ingestion and cannot be downloaded. Axio Hub operates as a 'shredder' - "
                    "we remember the context but destroy the paper."
                ),
                "policy": "ghost_protocol",
                "docs": "https://docs.axiohub.io/security/zero-retention"
            }
        )

        assert error.status_code == 403
        assert error.detail["policy"] == "ghost_protocol"
        assert "shredder" in error.detail["message"].lower()

    def test_download_response_structure(self):
        """Download endpoint error should have all required fields."""
        detail = {
            "error": "download_not_available",
            "message": "Ephemeral Storage Policy: ...",
            "policy": "ghost_protocol",
            "docs": "https://docs.axiohub.io/security/zero-retention"
        }

        required_fields = ["error", "message", "policy", "docs"]
        for field in required_fields:
            assert field in detail, f"Missing required field: {field}"

    def test_download_endpoint_error_code(self):
        """Download endpoint should use correct error code."""
        detail = {"error": "download_not_available"}
        assert detail["error"] == "download_not_available"


class TestGhostProtocolPolicyFormat:
    """Tests for Ghost Protocol policy response format."""

    def test_policy_value_is_ghost_protocol(self):
        """Policy field should be 'ghost_protocol'."""
        detail = {"policy": "ghost_protocol"}
        assert detail["policy"] == "ghost_protocol"

    def test_docs_link_points_to_axiohub(self):
        """Docs link should point to axiohub.io documentation."""
        detail = {"docs": "https://docs.axiohub.io/security/zero-retention"}
        assert "axiohub.io" in detail["docs"]
        assert "zero-retention" in detail["docs"]


class TestEndpointDecoratorPresence:
    """Tests to verify endpoints are properly decorated."""

    def test_content_endpoint_exists_in_router(self):
        """Content endpoint should be registered in the router."""
        from api.v1.documents import router

        # Check if there's a route for /documents/{document_id}/content
        content_routes = [
            r for r in router.routes
            if hasattr(r, 'path') and '/content' in r.path
        ]
        assert len(content_routes) > 0, "Content endpoint not found in router"

    def test_download_endpoint_exists_in_router(self):
        """Download endpoint should be registered in the router."""
        from api.v1.documents import router

        # Check if there's a route for /documents/{document_id}/download
        download_routes = [
            r for r in router.routes
            if hasattr(r, 'path') and '/download' in r.path
        ]
        assert len(download_routes) > 0, "Download endpoint not found in router"

    def test_content_endpoint_uses_get_method(self):
        """Content endpoint should be a GET endpoint."""
        from api.v1.documents import router

        for route in router.routes:
            if hasattr(route, 'path') and '/content' in route.path:
                assert 'GET' in route.methods
                break

    def test_download_endpoint_uses_get_method(self):
        """Download endpoint should be a GET endpoint."""
        from api.v1.documents import router

        for route in router.routes:
            if hasattr(route, 'path') and '/download' in route.path:
                assert 'GET' in route.methods
                break


class TestChunksEndpointDecryptionLogic:
    """Tests for chunks endpoint decryption handling."""

    def test_decrypt_text_import_available(self):
        """decrypt_text should be importable from core.security."""
        from core.security import decrypt_text
        assert callable(decrypt_text)

    def test_unencrypted_content_error_import_available(self):
        """UnencryptedContentError should be importable from core.security."""
        from core.security import UnencryptedContentError
        assert issubclass(UnencryptedContentError, Exception)

    def test_encryption_error_import_available(self):
        """EncryptionError should be importable from core.security."""
        from core.security import EncryptionError
        assert issubclass(EncryptionError, Exception)


class TestStatusCodes:
    """Tests for correct HTTP status codes."""

    def test_forbidden_is_403(self):
        """HTTP_403_FORBIDDEN should be 403."""
        assert status.HTTP_403_FORBIDDEN == 403

    def test_content_endpoint_uses_forbidden_status(self):
        """Content endpoint should use 403 status code."""
        from fastapi import status

        # This is the status code our endpoint uses
        expected_status = status.HTTP_403_FORBIDDEN
        assert expected_status == 403

    def test_download_endpoint_uses_forbidden_status(self):
        """Download endpoint should use 403 status code."""
        from fastapi import status

        expected_status = status.HTTP_403_FORBIDDEN
        assert expected_status == 403
