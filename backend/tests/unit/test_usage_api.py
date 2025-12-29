"""
Test Suite for Usage API Endpoint

Production-grade tests for:
- GET /api/v1/usage - User usage statistics
- GET /api/v1/plans - Available plans (public)

These tests ensure accurate usage reporting for frontend progress bars
and quota enforcement.
"""

import pytest
from unittest.mock import patch, Mock, AsyncMock
from uuid import uuid4, UUID

from pydantic import BaseModel
from core.quotas import QUOTA_LIMITS, PlanLimits, format_bytes


# Test UUID - must be valid UUID format for endpoint tests
TEST_USER_UUID = "12345678-1234-5678-1234-567812345678"


class TestUsageResponseModel:
    """Tests for usage response schema validation."""
    
    @pytest.mark.unit
    def test_usage_response_has_required_fields(self):
        """Usage response must have plan, files, storage, features, model_tier."""
        from api.v1.usage import UsageResponse, UsageCount, StorageUsage, FeatureAccess
        
        response = UsageResponse(
            plan="free",
            files=UsageCount(used=3, limit=5, percent=60.0),
            storage=StorageUsage(
                used_bytes=25_000_000,
                used_display="25 MB",
                limit_bytes=52_428_800,
                limit_display="50 MB",
                percent=47.7
            ),
            features=FeatureAccess(
                web_crawl=False,
                team=False,
                premium_models=False
            ),
            model_tier="basic",
            subscription_status="active"
        )
        
        assert response.plan == "free"
        assert response.files.used == 3
        assert response.files.limit == 5
        assert response.storage.used_bytes == 25_000_000
        assert response.features.web_crawl is False
        assert response.model_tier == "basic"
        assert response.subscription_status == "active"
    
    @pytest.mark.unit
    def test_usage_count_percentage_calculation(self):
        """UsageCount percent should be 0-100 scale."""
        from api.v1.usage import UsageCount
        
        count = UsageCount(used=4, limit=5, percent=80.0)
        assert count.percent == 80.0
        
        # At limit
        at_limit = UsageCount(used=5, limit=5, percent=100.0)
        assert at_limit.percent == 100.0
    
    @pytest.mark.unit
    def test_storage_usage_has_display_strings(self):
        """StorageUsage must include human-readable display strings."""
        from api.v1.usage import StorageUsage
        
        storage = StorageUsage(
            used_bytes=104_857_600,  # 100 MB
            used_display="100 MB",
            limit_bytes=2_147_483_648,  # 2 GB
            limit_display="2 GB",
            percent=4.9
        )
        
        assert "MB" in storage.used_display
        assert "GB" in storage.limit_display


class TestUsageEndpointWithMocks:
    """Tests for GET /api/v1/usage endpoint using mocks."""
    
    @pytest.fixture
    def mock_usage_with_limits_free(self):
        """Create a mock UsageWithLimits response for free plan."""
        mock = Mock()
        mock.usage = Mock()
        mock.usage.files = 4
        mock.usage.storage_bytes = 45_000_000
        mock.usage.storage_display = "45 MB"
        mock.usage.storage_display = "45 MB"
        mock.usage.plan = "free"
        mock.usage.subscription_status = "active"
        mock.limits = QUOTA_LIMITS["free"]
        return mock
    
    @pytest.fixture
    def mock_usage_with_limits_pro(self):
        """Create a mock UsageWithLimits response for pro plan."""
        mock = Mock()
        mock.usage = Mock()
        mock.usage.files = 50
        mock.usage.storage_bytes = 500_000_000
        mock.usage.storage_display = "500 MB"
        mock.usage.storage_display = "500 MB"
        mock.usage.plan = "pro"
        mock.usage.subscription_status = "active"
        mock.limits = QUOTA_LIMITS["pro"]
        return mock
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_returns_correct_structure(self, mock_usage_with_limits_free):
        """GET /usage should return properly structured response."""
        from api.v1.usage import get_usage, UsageResponse
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_usage_with_limits_free
            
            result = await get_usage(user_id=TEST_USER_UUID)
            
            assert isinstance(result, UsageResponse)
            assert result.plan == "free"
            assert result.files.used == 4
            assert result.files.limit == 5
            assert result.storage.used_bytes == 45_000_000
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_calculates_percentages(self, mock_usage_with_limits_free):
        """Percentages should be calculated correctly."""
        from api.v1.usage import get_usage
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_usage_with_limits_free
            
            result = await get_usage(user_id=TEST_USER_UUID)
            
            # 4/5 files = 80%
            assert result.files.percent == 80.0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_caps_percentage_at_100(self):
        """Percentages should be capped at 100% even if over limit."""
        from api.v1.usage import get_usage
        
        # User over their limit
        mock_over_limit = Mock()
        mock_over_limit.usage = Mock()
        mock_over_limit.usage.files = 10  # Over the 5 file limit
        mock_over_limit.usage.storage_bytes = 100_000_000  # Over 50MB limit
        mock_over_limit.usage.storage_display = "100 MB"
        mock_over_limit.usage.storage_display = "100 MB"
        mock_over_limit.usage.plan = "free"
        mock_over_limit.usage.subscription_status = "active"
        mock_over_limit.limits = QUOTA_LIMITS["free"]
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_over_limit
            
            result = await get_usage(user_id=TEST_USER_UUID)
            
            # Should be capped at 100
            assert result.files.percent == 100.0
            assert result.storage.percent == 100.0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_feature_flags_free_plan(self, mock_usage_with_limits_free):
        """Free plan should have limited features."""
        from api.v1.usage import get_usage
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_usage_with_limits_free
            
            result = await get_usage(user_id=TEST_USER_UUID)
            
            assert result.features.web_crawl is False
            assert result.features.team is False
            assert result.features.premium_models is False
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_feature_flags_pro_plan(self, mock_usage_with_limits_pro):
        """Pro plan should have more features."""
        from api.v1.usage import get_usage
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_usage_with_limits_pro
            
            result = await get_usage(user_id=TEST_USER_UUID)
            
            assert result.plan == "pro"
            assert result.features.web_crawl is True
            assert result.features.premium_models is True
            assert result.model_tier == "hybrid"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_endpoint_error_handling(self):
        """Usage endpoint should handle errors gracefully."""
        from api.v1.usage import get_usage
        from fastapi import HTTPException
        
        with patch("api.v1.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = Exception("Database connection failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_usage(user_id=TEST_USER_UUID)
            
            assert exc_info.value.status_code == 500
            assert "Failed to fetch usage" in exc_info.value.detail


class TestPlansEndpoint:
    """Tests for GET /api/v1/plans endpoint."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plans_endpoint_returns_all_plans(self):
        """GET /plans should return all available plans."""
        from api.v1.usage import get_plans
        
        result = await get_plans()
        
        assert "plans" in result.model_dump()
        plans = result.plans
        
        # Should have all 4 plans
        assert "free" in plans
        assert "starter" in plans
        assert "pro" in plans
        assert "enterprise" in plans
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plans_endpoint_includes_limits(self):
        """Each plan should include its limits."""
        from api.v1.usage import get_plans
        
        result = await get_plans()
        
        free_plan = result.plans["free"]
        assert "max_files" in free_plan
        assert "model_tier" in free_plan
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plans_endpoint_has_human_readable_storage(self):
        """Plans should include human-readable storage limits."""
        from api.v1.usage import get_plans
        
        result = await get_plans()
        
        # Check that max_storage is formatted (e.g., "50 MB", not just bytes)
        free_plan = result.plans["free"]
        if "max_storage" in free_plan:
            assert any(unit in free_plan["max_storage"] for unit in ["B", "KB", "MB", "GB"])


class TestUsageServiceWithMocks:
    """Tests for the usage service layer with properly mocked dependencies."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_user_usage_returns_usage_object(self):
        """get_user_usage should return UserUsage object."""
        from services.usage import get_user_usage, UserUsage
        
        mock_supabase = Mock()
        
        # Mock profile lookup - chained calls need proper setup
        profile_mock = Mock()
        profile_mock.data = {"plan": "starter", "subscription_status": "trialing"}
        mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_mock
        
        # Mock documents lookup
        docs_mock = Mock()
        docs_mock.data = [
            {"id": "doc-1", "file_size_bytes": 1_000_000},
            {"id": "doc-2", "file_size_bytes": 2_000_000},
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = docs_mock
        
        with patch("services.usage.get_supabase", return_value=mock_supabase):
            result = await get_user_usage(uuid4())
            
            assert isinstance(result, UserUsage)
            assert result.files == 2
            assert result.storage_bytes == 3_000_000
            assert result.plan == "starter"
            assert result.subscription_status == "trialing"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_can_upload_allows_within_limits(self):
        """check_can_upload should allow uploads within limits."""
        from services.usage import check_can_upload, UserUsage, UsageWithLimits
        
        mock_usage_with_limits = UsageWithLimits(
            usage=UserUsage(
                user_id="test-user-123",
                files=3,
                storage_bytes=20_000_000,
                storage_display="20 MB",
                plan="free",
                subscription_status="active"
            ),
            limits=QUOTA_LIMITS["free"],
            files_remaining=2,
            storage_remaining_bytes=32_428_800,
            storage_remaining_display="32 MB",
            at_file_limit=False,
            at_storage_limit=False
        )
        
        with patch("services.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_usage_with_limits
            
            # Upload a 5MB file
            result = await check_can_upload(uuid4(), file_size_bytes=5_000_000)
            
            assert result["allowed"] is True
            assert result["reason"] is None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_can_upload_blocks_over_file_limit(self):
        """check_can_upload should block when file limit exceeded."""
        from services.usage import check_can_upload, UserUsage, UsageWithLimits
        
        mock_at_limit = UsageWithLimits(
            usage=UserUsage(
                user_id="test-user-123",
                files=5,  # At limit
                storage_bytes=20_000_000,
                storage_display="20 MB",
                plan="free",
                subscription_status="active"
            ),
            limits=QUOTA_LIMITS["free"],
            files_remaining=0,
            storage_remaining_bytes=32_428_800,
            storage_remaining_display="32 MB",
            at_file_limit=True,
            at_storage_limit=False
        )
        
        with patch("services.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_at_limit
            
            result = await check_can_upload(uuid4(), file_size_bytes=1_000_000)
            
            assert result["allowed"] is False
            assert "limit" in result["reason"].lower()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_check_can_upload_blocks_over_storage_limit(self):
        """check_can_upload should block when storage limit exceeded."""
        from services.usage import check_can_upload, UserUsage, UsageWithLimits
        
        mock_near_limit = UsageWithLimits(
            usage=UserUsage(
                user_id="test-user-123",
                files=3,
                storage_bytes=50_000_000,  # Almost at 50MB limit
                storage_display="50 MB",
                plan="free",
                subscription_status="active"
            ),
            limits=QUOTA_LIMITS["free"],
            files_remaining=2,
            storage_remaining_bytes=2_428_800,  # ~2.4 MB remaining
            storage_remaining_display="2 MB",
            at_file_limit=False,
            at_storage_limit=False
        )
        
        with patch("services.usage.get_user_usage_with_limits", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_near_limit
            
            # Try to upload 5MB (exceeds remaining)
            result = await check_can_upload(uuid4(), file_size_bytes=5_000_000)
            
            assert result["allowed"] is False
            assert "storage" in result["reason"].lower()


class TestFormatBytes:
    """Tests for format_bytes utility function."""
    
    @pytest.mark.unit
    def test_format_bytes_bytes(self):
        """Small values should display as bytes."""
        assert format_bytes(500) == "500 B"
    
    @pytest.mark.unit
    def test_format_bytes_kilobytes(self):
        """KB values should use KB unit."""
        result = format_bytes(2048)
        assert "KB" in result
    
    @pytest.mark.unit
    def test_format_bytes_megabytes(self):
        """MB values should use MB unit."""
        result = format_bytes(50 * 1024 * 1024)
        assert "MB" in result
    
    @pytest.mark.unit
    def test_format_bytes_gigabytes(self):
        """GB values should use GB unit."""
        result = format_bytes(2 * 1024 * 1024 * 1024)
        assert "GB" in result
    
    @pytest.mark.unit
    def test_format_bytes_zero(self):
        """Zero bytes should display correctly."""
        assert format_bytes(0) == "0 B"


class TestPlanLimitsConsistency:
    """Tests to ensure all plans have valid limits."""
    
    @pytest.mark.unit
    def test_all_plans_have_positive_file_limits(self):
        """Every plan should have positive max_files."""
        for plan_name, limits in QUOTA_LIMITS.items():
            if plan_name == "none":
                continue
            assert limits.max_files > 0, f"Plan {plan_name} has invalid max_files"
    
    @pytest.mark.unit
    def test_all_plans_have_positive_storage_limits(self):
        """Every plan should have positive max_storage_bytes."""
        for plan_name, limits in QUOTA_LIMITS.items():
            if plan_name == "none":
                continue
            assert limits.max_storage_bytes > 0, f"Plan {plan_name} has invalid max_storage_bytes"
    
    @pytest.mark.unit
    def test_higher_plans_have_higher_limits(self):
        """Higher tier plans should have more generous limits."""
        assert QUOTA_LIMITS["starter"].max_files > QUOTA_LIMITS["free"].max_files
        assert QUOTA_LIMITS["pro"].max_files > QUOTA_LIMITS["starter"].max_files
        assert QUOTA_LIMITS["enterprise"].max_files > QUOTA_LIMITS["pro"].max_files
        
        assert QUOTA_LIMITS["starter"].max_storage_bytes > QUOTA_LIMITS["free"].max_storage_bytes
        assert QUOTA_LIMITS["pro"].max_storage_bytes > QUOTA_LIMITS["starter"].max_storage_bytes
        assert QUOTA_LIMITS["enterprise"].max_storage_bytes > QUOTA_LIMITS["pro"].max_storage_bytes
    
    @pytest.mark.unit
    def test_web_crawl_only_on_paid_plans(self):
        """Web crawl should only be available on Pro and Enterprise."""
        assert QUOTA_LIMITS["free"].allow_web_crawl is False
        assert QUOTA_LIMITS["starter"].allow_web_crawl is False
        assert QUOTA_LIMITS["pro"].allow_web_crawl is True
        assert QUOTA_LIMITS["enterprise"].allow_web_crawl is True
    
    @pytest.mark.unit
    def test_model_tier_progression(self):
        """Model tiers should progress with plan level."""
        assert QUOTA_LIMITS["free"].model_tier == ModelTier.BASIC
        assert QUOTA_LIMITS["starter"].model_tier == ModelTier.BASIC
        assert QUOTA_LIMITS["pro"].model_tier == ModelTier.HYBRID
        assert QUOTA_LIMITS["enterprise"].model_tier == ModelTier.PREMIUM
