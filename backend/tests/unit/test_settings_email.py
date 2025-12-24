"""
Unit Tests for Settings API Email Preferences

Tests the notification settings endpoints for email preference management.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from api.v1.settings import (
    DEFAULT_NOTIFICATION_SETTINGS,
    NotificationSettingUpdate,
    NotificationSettingResponse
)


class TestDefaultNotificationSettings:
    """Tests for DEFAULT_NOTIFICATION_SETTINGS configuration."""
    
    def test_email_on_ingestion_complete_exists(self):
        """Default settings should include email_on_ingestion_complete."""
        setting_keys = [s["setting_key"] for s in DEFAULT_NOTIFICATION_SETTINGS]
        assert "email_on_ingestion_complete" in setting_keys
    
    def test_email_on_ingestion_complete_is_email_category(self):
        """email_on_ingestion_complete should be in 'email' category."""
        setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS 
            if s["setting_key"] == "email_on_ingestion_complete"
        )
        assert setting["category"] == "email"
    
    def test_email_on_ingestion_complete_enabled_by_default(self):
        """email_on_ingestion_complete should be enabled by default."""
        setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS 
            if s["setting_key"] == "email_on_ingestion_complete"
        )
        assert setting["enabled"] == True
    
    def test_email_on_ingestion_complete_has_label(self):
        """email_on_ingestion_complete should have a user-friendly label."""
        setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS 
            if s["setting_key"] == "email_on_ingestion_complete"
        )
        assert setting["setting_label"]
        assert len(setting["setting_label"]) > 5
    
    def test_email_on_ingestion_complete_has_description(self):
        """email_on_ingestion_complete should have a description."""
        setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS 
            if s["setting_key"] == "email_on_ingestion_complete"
        )
        assert setting["setting_description"]
    
    def test_all_default_settings_have_required_fields(self):
        """All default settings should have required fields."""
        required_fields = ["setting_key", "setting_label", "category", "enabled"]
        
        for setting in DEFAULT_NOTIFICATION_SETTINGS:
            for field in required_fields:
                assert field in setting, f"Setting {setting.get('setting_key', 'unknown')} missing field {field}"
    
    def test_settings_have_unique_keys(self):
        """All setting keys should be unique."""
        keys = [s["setting_key"] for s in DEFAULT_NOTIFICATION_SETTINGS]
        assert len(keys) == len(set(keys))
    
    def test_valid_categories(self):
        """All settings should have valid categories."""
        valid_categories = ["email", "system"]
        for setting in DEFAULT_NOTIFICATION_SETTINGS:
            assert setting["category"] in valid_categories


class TestNotificationSettingModels:
    """Tests for Pydantic models."""
    
    def test_notification_setting_update_valid(self):
        """NotificationSettingUpdate should accept valid data."""
        update = NotificationSettingUpdate(
            setting_key="email_on_ingestion_complete",
            enabled=False
        )
        assert update.setting_key == "email_on_ingestion_complete"
        assert update.enabled == False
    
    def test_notification_setting_response_valid(self):
        """NotificationSettingResponse should accept valid data."""
        response = NotificationSettingResponse(
            id="123",
            setting_key="test",
            setting_label="Test Label",
            setting_description="Test description",
            category="email",
            enabled=True
        )
        assert response.setting_key == "test"
        assert response.enabled == True


class TestGetNotificationSettingsEndpoint:
    """Tests for GET /settings/notifications endpoint."""
    
    @pytest.mark.asyncio
    async def test_returns_existing_settings(self):
        """Should return existing settings when they exist."""
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [
            {
                "id": "123",
                "setting_key": "email_on_ingestion_complete",
                "setting_label": "Ingestion Complete Emails",
                "setting_description": "Receive email when processing finishes",
                "category": "email",
                "enabled": False
            }
        ]
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import get_notification_settings
            
            result = await get_notification_settings(user_id="user-123")
            
            assert len(result) == 1
            assert result[0]["setting_key"] == "email_on_ingestion_complete"
            assert result[0]["enabled"] == False
    
    @pytest.mark.asyncio
    async def test_creates_defaults_when_no_settings_exist(self):
        """Should create default settings when user has none."""
        mock_supabase = Mock()
        
        # First call: no existing settings
        mock_empty_response = Mock()
        mock_empty_response.data = []
        
        # Second call: insert returns new settings
        mock_insert_response = Mock()
        mock_insert_response.data = DEFAULT_NOTIFICATION_SETTINGS
        
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_empty_response
        mock_supabase.table.return_value.insert.return_value.execute.return_value = mock_insert_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import get_notification_settings
            
            result = await get_notification_settings(user_id="new-user")
            
            # Should have called insert
            mock_supabase.table.return_value.insert.assert_called_once()


class TestUpdateNotificationSettingsEndpoint:
    """Tests for PATCH /settings/notifications endpoint."""
    
    @pytest.mark.asyncio
    async def test_updates_existing_setting(self):
        """Should update an existing notification setting."""
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{
            "id": "123",
            "setting_key": "email_on_ingestion_complete",
            "setting_label": "Ingestion Complete Emails",
            "setting_description": "Receive email when processing finishes",
            "category": "email",
            "enabled": False
        }]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import update_notification_setting
            
            payload = NotificationSettingUpdate(
                setting_key="email_on_ingestion_complete",
                enabled=False
            )
            
            result = await update_notification_setting(payload=payload, user_id="user-123")
            
            assert result["enabled"] == False
    
    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_setting(self):
        """Should return 404 when setting doesn't exist."""
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []  # No matching setting
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import update_notification_setting
            from fastapi import HTTPException
            
            payload = NotificationSettingUpdate(
                setting_key="nonexistent_setting",
                enabled=True
            )
            
            with pytest.raises(HTTPException) as exc_info:
                await update_notification_setting(payload=payload, user_id="user-123")
            
            assert exc_info.value.status_code == 404


class TestSettingsSecurityAndIsolation:
    """Tests for security and user isolation."""
    
    @pytest.mark.asyncio
    async def test_settings_filtered_by_user_id(self):
        """Settings queries should filter by user_id."""
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = []
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import get_notification_settings
            
            await get_notification_settings(user_id="user-123")
            
            # Verify eq was called with user_id
            mock_supabase.table.return_value.select.return_value.eq.assert_called_with("user_id", "user-123")
    
    @pytest.mark.asyncio
    async def test_update_filtered_by_user_id(self):
        """Update should filter by user_id to prevent unauthorized access."""
        mock_supabase = Mock()
        mock_response = Mock()
        mock_response.data = [{"id": "123", "setting_key": "test", "setting_label": "Test", "category": "email", "enabled": True}]
        mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = mock_response
        
        with patch('api.v1.settings.get_supabase', return_value=mock_supabase):
            from api.v1.settings import update_notification_setting
            
            payload = NotificationSettingUpdate(setting_key="test", enabled=True)
            await update_notification_setting(payload=payload, user_id="user-123")
            
            # Should have called eq with user_id
            calls = mock_supabase.table.return_value.update.return_value.eq.call_args_list
            user_id_filtered = any(
                call[0] == ("user_id", "user-123") for call in calls
            )
            assert user_id_filtered
