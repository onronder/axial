"""
Unit Tests for S3 API Endpoint

Tests enterprise gate enforcement and API behavior.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Note: These tests use mocking since we can't import the full app easily
# In a real test environment, you'd use TestClient with the FastAPI app


class TestS3EnterpriseGate:
    """Test S3 Enterprise Gate enforcement."""

    @pytest.mark.unit
    def test_enterprise_plans_defined(self):
        """Verify enterprise plans are defined in the endpoint."""
        # Import the constant from integrations module
        from api.v1.integrations import ENTERPRISE_PLANS
        
        assert "enterprise" in ENTERPRISE_PLANS
        assert "enterprise_small" in ENTERPRISE_PLANS
        assert "enterprise_medium" in ENTERPRISE_PLANS
        assert "enterprise_large" in ENTERPRISE_PLANS

    @pytest.mark.unit
    def test_non_enterprise_plans_excluded(self):
        """Non-enterprise plans should NOT be in the set."""
        from api.v1.integrations import ENTERPRISE_PLANS
        
        assert "free" not in ENTERPRISE_PLANS
        assert "starter" not in ENTERPRISE_PLANS
        assert "pro" not in ENTERPRISE_PLANS

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_blocks_free_plan(self):
        """Free plan users should be blocked with 403."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="free"  # Non-enterprise plan
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "ENTERPRISE_REQUIRED"
        assert exc_info.value.detail["current_plan"] == "free"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_blocks_starter_plan(self):
        """Starter plan users should be blocked with 403."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="starter"
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "ENTERPRISE_REQUIRED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_blocks_pro_plan(self):
        """Pro plan users should be blocked with 403."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="pro"
            )
        
        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["error"] == "ENTERPRISE_REQUIRED"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_allows_enterprise_plan(self):
        """Enterprise plan users should be allowed."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        from connectors.s3 import S3Connector
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        # Mock dependencies
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(
            data=[{"id": "integration-id"}]
        )
        
        mock_connector = MagicMock()
        mock_connector._verify_access.return_value = {"status": "connected"}
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector), \
             patch("api.v1.integrations.encrypt_token", return_value="encrypted"), \
             patch("api.v1.integrations.audit_logger"):
            result = await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="enterprise"  # Enterprise plan
            )
        
        assert result["status"] == "success"
        assert result["provider"] == "s3"
        assert result["bucket"] == "test-bucket"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_allows_enterprise_medium_plan(self):
        """Enterprise medium plan users should be allowed."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(
            data=[{"id": "integration-id"}]
        )
        
        mock_connector = MagicMock()
        mock_connector._verify_access.return_value = {"status": "connected"}
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector), \
             patch("api.v1.integrations.encrypt_token", return_value="encrypted"), \
             patch("api.v1.integrations.audit_logger"):
            result = await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="enterprise_medium"
            )
        
        assert result["status"] == "success"


class TestS3ConnectRequestValidation:
    """Test S3ConnectRequest Pydantic validation."""

    @pytest.mark.unit
    def test_valid_request(self):
        """Valid request should pass validation."""
        from api.v1.integrations import S3ConnectRequest
        
        request = S3ConnectRequest(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            bucket_name="my-bucket",
            prefix="documents/"
        )
        
        assert request.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert request.bucket_name == "my-bucket"

    @pytest.mark.unit
    def test_default_region(self):
        """Region should default to us-east-1."""
        from api.v1.integrations import S3ConnectRequest
        
        request = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            bucket_name="my-bucket",
            prefix="documents/"
        )
        
        assert request.region == "us-east-1"

    @pytest.mark.unit
    def test_prefix_required(self):
        """Prefix should be required."""
        from api.v1.integrations import S3ConnectRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            S3ConnectRequest(
                access_key_id="A" * 20,
                secret_access_key="B" * 40,
                bucket_name="my-bucket",
                # Missing prefix
            )
        
        errors = exc_info.value.errors()
        assert any("prefix" in str(e) for e in errors)

    @pytest.mark.unit
    def test_bucket_name_pattern(self):
        """Bucket name should match S3 pattern."""
        from api.v1.integrations import S3ConnectRequest
        from pydantic import ValidationError
        
        # Valid bucket names
        valid_names = ["my-bucket", "bucket123", "a.bucket.name"]
        for name in valid_names:
            request = S3ConnectRequest(
                access_key_id="A" * 20,
                secret_access_key="B" * 40,
                bucket_name=name,
                prefix="docs/"
            )
            assert request.bucket_name == name

    @pytest.mark.unit
    def test_credentials_min_length(self):
        """Credentials should have minimum length."""
        from api.v1.integrations import S3ConnectRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            S3ConnectRequest(
                access_key_id="short",  # Too short
                secret_access_key="B" * 40,
                bucket_name="my-bucket",
                prefix="docs/"
            )


class TestS3ConnectErrorHandling:
    """Test S3 connect endpoint error handling."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_handles_auth_error(self):
        """Should return 401 for authentication errors."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        from connectors.base import ConnectorAuthError
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        
        mock_connector = MagicMock()
        mock_connector._verify_access.side_effect = ConnectorAuthError("Invalid credentials")
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector):
            with pytest.raises(HTTPException) as exc_info:
                await connect_s3(
                    request=request,
                    body=body,
                    user_id="user-123",
                    plan="enterprise"
                )
        
        assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_handles_transient_error(self):
        """Should return 503 for transient errors."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        from connectors.base import ConnectorTransientError
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        
        mock_connector = MagicMock()
        mock_connector._verify_access.side_effect = ConnectorTransientError("Network error")
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector):
            with pytest.raises(HTTPException) as exc_info:
                await connect_s3(
                    request=request,
                    body=body,
                    user_id="user-123",
                    plan="enterprise"
                )
        
        assert exc_info.value.status_code == 503

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_connect_s3_handles_missing_connector_definition(self):
        """Should return 500 if S3 connector not configured."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data=None  # No connector definition
        )
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase):
            with pytest.raises(HTTPException) as exc_info:
                await connect_s3(
                    request=request,
                    body=body,
                    user_id="user-123",
                    plan="enterprise"
                )
        
        assert exc_info.value.status_code == 500
        assert "not configured" in exc_info.value.detail


class TestS3ConnectCredentialStorage:
    """Test credential encryption and storage."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_credentials_are_encrypted(self):
        """Credentials should be encrypted before storage."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = Mock(
            data=[{"id": "integration-id"}]
        )
        
        mock_connector = MagicMock()
        mock_connector._verify_access.return_value = {"status": "connected"}
        
        encrypt_calls = []
        def track_encrypt(value):
            encrypt_calls.append(value)
            return f"encrypted_{value[:8]}"
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector), \
             patch("api.v1.integrations.encrypt_token", side_effect=track_encrypt), \
             patch("api.v1.integrations.audit_logger"):
            await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="enterprise"
            )
        
        # Verify encrypt was called for access_key and secret_key
        assert len(encrypt_calls) == 2
        assert "AKIAIOSFODNN7EXAMPLE" in encrypt_calls
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" in encrypt_calls

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_non_sensitive_fields_not_encrypted(self):
        """Region, bucket, prefix should NOT be encrypted."""
        from api.v1.integrations import connect_s3, S3ConnectRequest
        
        request = Mock()
        body = S3ConnectRequest(
            access_key_id="A" * 20,
            secret_access_key="B" * 40,
            region="us-east-1",
            bucket_name="test-bucket",
            prefix="documents/"
        )
        
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = Mock(
            data={"id": "connector-def-id"}
        )
        
        upsert_data = None
        def capture_upsert(data, **kwargs):
            nonlocal upsert_data
            upsert_data = data
            return Mock(execute=lambda: Mock(data=[{"id": "integration-id"}]))
        
        mock_supabase.table.return_value.upsert.side_effect = capture_upsert
        
        mock_connector = MagicMock()
        mock_connector._verify_access.return_value = {"status": "connected"}
        
        with patch("api.v1.integrations.get_supabase", return_value=mock_supabase), \
             patch("api.v1.integrations.S3Connector", return_value=mock_connector), \
             patch("api.v1.integrations.encrypt_token", return_value="encrypted"), \
             patch("api.v1.integrations.audit_logger"):
            await connect_s3(
                request=request,
                body=body,
                user_id="user-123",
                plan="enterprise"
            )
        
        # Verify non-sensitive fields are stored as-is
        credentials = upsert_data["credentials"]
        assert credentials["region"] == "us-east-1"
        assert credentials["bucket_name"] == "test-bucket"
        assert credentials["prefix"] == "documents/"
