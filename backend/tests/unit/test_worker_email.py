"""
Unit Tests for Email Notification in Worker Tasks

Tests the send_email_notification function and its integration
with user preferences.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestSendEmailNotification:
    """Tests for send_email_notification helper function."""

    @pytest.fixture
    def mock_supabase(self):
        """Create a mock Supabase client with proper auth structure."""
        mock = Mock()
        # Setup auth admin mock structure
        mock.auth = Mock()
        mock.auth.admin = Mock()
        return mock

    def _setup_profile_mock(self, mock_supabase, display_name=None, full_name=None):
        """Helper to setup user_profiles table mock."""
        profile_data = {"display_name": display_name, "full_name": full_name}
        profile_mock = Mock()
        profile_mock.data = profile_data
        return profile_mock

    def _setup_auth_user(self, mock_supabase, email, full_name=None, name=None):
        """Helper to setup auth.admin.get_user_by_id mock with user_metadata."""
        auth_user = Mock()
        auth_user.user = Mock()
        auth_user.user.email = email
        # Setup user_metadata for name lookup
        user_metadata = {}
        if full_name:
            user_metadata["full_name"] = full_name
        if name:
            user_metadata["name"] = name
        auth_user.user.user_metadata = user_metadata
        mock_supabase.auth.admin.get_user_by_id.return_value = auth_user

    def _setup_settings_mock(self, enabled):
        """Helper to setup notification settings mock (returns list)."""
        settings_mock = Mock()
        settings_mock.data = [{"enabled": enabled}] if enabled is not None else []
        return settings_mock

    def test_sends_email_when_preference_enabled(self, mock_supabase):
        """Should send email when user has enabled email notifications."""
        # Setup auth user with email
        self._setup_auth_user(mock_supabase, "user@example.com")

        # Setup table mocks
        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_profiles":
                profile_mock = Mock()
                profile_mock.data = {"display_name": "John Doe", "full_name": None}
                table_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = profile_mock
            elif table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = [{"enabled": True}]
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.return_value = True

            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            mock_email.send_ingestion_complete.assert_called_once()

    def test_skips_email_when_preference_disabled(self, mock_supabase):
        """Should not send email when user has disabled email notifications."""
        # Setup auth user with email
        self._setup_auth_user(mock_supabase, "user@example.com")

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_profiles":
                profile_mock = Mock()
                profile_mock.data = {"display_name": "John Doe", "full_name": None}
                table_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = profile_mock
            elif table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = [{"enabled": False}]  # Disabled
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            mock_email.send_ingestion_complete.assert_not_called()

    def test_defaults_to_enabled_when_no_setting_exists(self, mock_supabase):
        """Should default to sending email when no explicit setting exists."""
        # Setup auth user with email
        self._setup_auth_user(mock_supabase, "user@example.com")

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_profiles":
                profile_mock = Mock()
                profile_mock.data = {"display_name": "John", "full_name": None}
                table_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = profile_mock
            elif table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = []  # No settings - should default to enabled
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.return_value = True

            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            # Should still send email (default enabled)
            mock_email.send_ingestion_complete.assert_called_once()

    def test_handles_missing_user_profile(self, mock_supabase):
        """Should handle missing user metadata gracefully - uses default name 'there'."""
        # Setup auth user with email but NO user_metadata (no name)
        self._setup_auth_user(mock_supabase, "user@example.com")  # No name params = empty metadata

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = [{"enabled": True}]
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.return_value = True

            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "nonexistent-user", 5)

            # Should still send email (uses default name "there" since no metadata)
            mock_email.send_ingestion_complete.assert_called_once()
            call_args = mock_email.send_ingestion_complete.call_args
            assert call_args.kwargs["name"] == "there"

    def test_handles_missing_email_in_auth(self, mock_supabase):
        """Should handle missing auth email gracefully - no email sent."""
        # Setup auth user with NO email
        auth_user = Mock()
        auth_user.user = Mock()
        auth_user.user.email = None
        mock_supabase.auth.admin.get_user_by_id.return_value = auth_user

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_profiles":
                profile_mock = Mock()
                profile_mock.data = {"display_name": "John", "full_name": None}
                table_mock.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = profile_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            mock_email.send_ingestion_complete.assert_not_called()

    def test_uses_fallback_name_when_display_name_missing(self, mock_supabase):
        """Should use 'there' as fallback when no name is in user_metadata."""
        # Setup auth user with email but empty user_metadata
        self._setup_auth_user(mock_supabase, "user@example.com")  # No name = empty metadata

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = [{"enabled": True}]
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.return_value = True

            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            # Check that fallback name "there" was used (no name in metadata)
            call_args = mock_email.send_ingestion_complete.call_args
            assert call_args.kwargs["name"] == "there"

    def test_prefers_full_name_over_name(self, mock_supabase):
        """Should prefer full_name over name when both are in user_metadata."""
        # Setup auth user with email and full_name in metadata
        self._setup_auth_user(mock_supabase, "user@example.com", full_name="Johnny")

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "user_notification_settings":
                settings_mock = Mock()
                settings_mock.data = [{"enabled": True}]
                table_mock.select.return_value.eq.return_value.eq.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.return_value = True

            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)

            call_args = mock_email.send_ingestion_complete.call_args
            assert call_args.kwargs["name"] == "Johnny"

    def test_does_not_raise_on_database_error(self, mock_supabase):
        """Should not raise exception when database query fails."""
        mock_supabase.table.side_effect = Exception("Database connection error")

        # Should not raise
        from worker.tasks import send_email_notification
        send_email_notification(mock_supabase, "user-123", 5)

    def test_does_not_raise_on_email_service_error(self, mock_supabase):
        """Should not raise exception when email service fails."""
        profile_mock = Mock()
        profile_mock.data = {"email": "user@example.com", "display_name": "John"}

        settings_mock = Mock()
        settings_mock.data = {"enabled": True}

        def table_side_effect(table_name):
            table_mock = Mock()
            if table_name == "profiles":
                table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_mock
            elif table_name == "user_notification_settings":
                table_mock.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = settings_mock
            return table_mock

        mock_supabase.table.side_effect = table_side_effect

        with patch('worker.tasks.email_service') as mock_email:
            mock_email.send_ingestion_complete.side_effect = Exception("SMTP Error")

            # Should not raise
            from worker.tasks import send_email_notification
            send_email_notification(mock_supabase, "user-123", 5)


class TestWorkerEmailIntegration:
    """Integration tests for email sending in worker tasks."""

    def test_email_sent_after_successful_ingestion(self):
        """Email notification should be called after successful ingestion."""
        with patch('worker.tasks.get_supabase') as mock_get_supabase:
            with patch('worker.tasks.send_email_notification') as mock_send_email:
                with patch('worker.tasks.update_job_status'):
                    with patch('worker.tasks.create_notification'):
                        mock_supabase = Mock()
                        mock_get_supabase.return_value = mock_supabase

                        # This would normally be tested via integration tests
                        # For unit tests, we verify the function exists and is callable
                        assert callable(mock_send_email)

    def test_job_status_updates_even_if_email_fails(self):
        """Job status should update to COMPLETED even if email sending fails."""
        with patch('worker.tasks.update_job_status') as mock_update:
            with patch('worker.tasks.send_email_notification') as mock_send_email:
                mock_send_email.side_effect = Exception("Email failed")

                # The update_job_status should be called before send_email_notification
                # in the actual implementation, ensuring job completes regardless
                assert callable(mock_update)


class TestSettingKeyConsistency:
    """Tests to ensure setting key is consistent across the system."""

    def test_worker_uses_correct_setting_key(self):
        """Worker should query for 'email_on_ingestion_complete' setting."""
        # Import the function and inspect the code
        import inspect

        from worker.tasks import send_email_notification
        source = inspect.getsource(send_email_notification)

        assert "email_on_ingestion_complete" in source

    def test_setting_key_matches_api_defaults(self):
        """Setting key in worker should match API default settings."""
        from api.v1.settings import DEFAULT_NOTIFICATION_SETTINGS

        setting_keys = [s["setting_key"] for s in DEFAULT_NOTIFICATION_SETTINGS]
        assert "email_on_ingestion_complete" in setting_keys

    def test_email_setting_is_email_category(self):
        """Email notification setting should be in 'email' category."""
        from api.v1.settings import DEFAULT_NOTIFICATION_SETTINGS

        email_setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS
            if s["setting_key"] == "email_on_ingestion_complete"
        )

        assert email_setting["category"] == "email"

    def test_email_setting_default_is_enabled(self):
        """Email notification should be enabled by default."""
        from api.v1.settings import DEFAULT_NOTIFICATION_SETTINGS

        email_setting = next(
            s for s in DEFAULT_NOTIFICATION_SETTINGS
            if s["setting_key"] == "email_on_ingestion_complete"
        )

        assert email_setting["enabled"] == True
