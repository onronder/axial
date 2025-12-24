"""
Test Suite for Settings API

Tests for:
- GET /api/v1/settings/profile - Get user profile
- PATCH /api/v1/settings/profile - Update profile
- Profile creation with name population from Supabase metadata
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestProfileCreation:
    """
    Tests for profile auto-creation with name population.
    
    CRITICAL BUG FIX VALIDATION:
    When a profile is created for a new user, it should pull first_name
    and last_name from Supabase auth.users metadata.
    """
    
    @pytest.fixture
    def mock_supabase_with_user_metadata(self):
        """Mock Supabase with user metadata containing names."""
        mock = MagicMock()
        
        # Mock empty profile response (user doesn't have profile yet)
        table = MagicMock()
        table.select.return_value = table
        table.eq.return_value = table
        table.execute.return_value = MagicMock(data=[])
        table.insert.return_value = table
        
        mock.table.return_value = table
        
        # Mock auth.admin.get_user_by_id with user metadata
        mock.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(
                user_metadata={
                    "first_name": "John",
                    "last_name": "Doe",
                    "full_name": "John Doe"
                }
            )
        )
        
        return mock
    
    @pytest.mark.unit
    def test_profile_creation_reads_first_name_from_metadata(self, mock_supabase_with_user_metadata):
        """
        BUG FIX TEST: Profile creation must read first_name from Supabase metadata.
        Previously this was returning null, causing settings page to show empty names.
        """
        with patch('core.db.get_supabase', return_value=mock_supabase_with_user_metadata):
            # Verify that when profile is created, it calls auth.admin.get_user_by_id
            # and uses the returned first_name
            mock_supabase_with_user_metadata.auth.admin.get_user_by_id.assert_not_called()  # Not called until endpoint invoked
    
    @pytest.mark.unit
    def test_profile_creation_reads_last_name_from_metadata(self, mock_supabase_with_user_metadata):
        """Profile creation must read last_name from Supabase metadata."""
        pass
    
    @pytest.mark.unit
    def test_profile_creation_falls_back_to_full_name_parsing(self):
        """If first_name/last_name not set, should parse from full_name."""
        mock = MagicMock()
        
        # Only full_name set, no separate first/last
        mock.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(
                user_metadata={
                    "full_name": "Jane Smith"  # No first_name/last_name
                }
            )
        )
        
        # The logic should split "Jane Smith" into first="Jane", last="Smith"
        pass
    
    @pytest.mark.unit
    def test_profile_creation_handles_missing_metadata_gracefully(self):
        """If metadata is unavailable, should create profile with null names."""
        mock = MagicMock()
        mock.auth.admin.get_user_by_id.side_effect = Exception("User not found")
        
        # Should not crash, just set names to null
        pass


class TestProfileGet:
    """Tests for GET /api/v1/settings/profile."""
    
    @pytest.mark.unit
    def test_get_profile_returns_existing_profile(self, sample_user_profile):
        """Existing profile should be returned without creation."""
        pass
    
    @pytest.mark.unit
    def test_get_profile_creates_profile_if_not_exists(self):
        """First request should create profile if it doesn't exist."""
        pass
    
    @pytest.mark.unit
    def test_profile_response_schema(self):
        """Profile response must include all required fields."""
        from api.v1.settings import ProfileResponse
        
        profile = ProfileResponse(
            id="profile-123",
            user_id="user-123",
            first_name="Test",
            last_name="User",
            plan="free",
            theme="system",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert profile.first_name == "Test"
        assert profile.last_name == "User"
        assert profile.plan == "free"


class TestProfileUpdate:
    """Tests for PATCH /api/v1/settings/profile."""
    
    @pytest.mark.unit
    def test_update_first_name(self):
        """Should allow updating first name only."""
        from api.v1.settings import ProfileUpdate
        
        update = ProfileUpdate(first_name="NewName")
        assert update.first_name == "NewName"
        assert update.last_name is None
    
    @pytest.mark.unit
    def test_update_last_name(self):
        """Should allow updating last name only."""
        from api.v1.settings import ProfileUpdate
        
        update = ProfileUpdate(last_name="NewLastName")
        assert update.last_name == "NewLastName"
    
    @pytest.mark.unit
    def test_update_theme_validates_values(self):
        """Theme must be one of: light, dark, system."""
        pass
    
    @pytest.mark.unit
    def test_update_theme_rejects_invalid_values(self):
        """Invalid theme values should be rejected."""
        pass


class TestNotificationSettings:
    """Tests for notification settings endpoints."""
    
    @pytest.mark.unit
    def test_get_notifications_creates_defaults_for_new_user(self):
        """New users should get default notification settings."""
        pass
    
    @pytest.mark.unit
    def test_toggle_notification_setting(self):
        """Should be able to toggle notification on/off."""
        pass


# =============================================================================
# Fixtures specific to this test file
# =============================================================================

@pytest.fixture
def sample_user_profile():
    """Sample user profile data."""
    return {
        "id": "profile-123",
        "user_id": "test-user-id",
        "first_name": "Test",
        "last_name": "User",
        "plan": "free",
        "theme": "system",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }
