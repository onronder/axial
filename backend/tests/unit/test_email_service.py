"""
Unit Tests for Email Service

Tests the EmailService class with mocked Resend API.
Validates fail-safe behavior and template rendering.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import os

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import services.email  # Ensure module is loaded for patching


class TestEmailServiceInitialization:
    """Tests for EmailService initialization."""
    
    def test_service_disabled_without_api_key(self):
        """Service should be disabled when RESEND_API_KEY is not set."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = None
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            # Re-import to apply mock
            from services.email import EmailService
            service = EmailService()
            
            assert service.enabled == False
    
    def test_service_enabled_with_api_key(self):
        """Service should be enabled when RESEND_API_KEY is set."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                from services.email import EmailService
                service = EmailService()
                
                # Service should set API key on resend module
                assert mock_resend.api_key == "re_test_key_123"

    def test_service_disabled_without_resend_dependency(self):
        """Service should disable when resend import fails."""
        import builtins
        import importlib

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "resend":
                raise ImportError("boom")
            return real_import(name, *args, **kwargs)

        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"

            with patch.object(builtins, "__import__", side_effect=fake_import):
                reloaded = importlib.reload(services.email)
                service = reloaded.EmailService()

                assert reloaded.resend is None
                assert service.enabled is False

            importlib.reload(services.email)

    def test_service_warns_when_templates_missing(self):
        """Service should handle missing templates directory."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"

            with patch('services.email.resend') as mock_resend, \
                 patch('services.email.TEMPLATES_DIR') as templates_dir:
                templates_dir.exists.return_value = False
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_123"})

                from services.email import EmailService
                service = EmailService()

                assert service.jinja_env is None


class TestEmailServiceSendIngestionComplete:
    """Tests for send_ingestion_complete method."""
    
    @pytest.fixture
    def mock_email_service(self):
        """Create a mocked EmailService instance."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_123"})
                
                from services.email import EmailService
                service = EmailService()
                service.enabled = True
                service.jinja_env = Mock()
                service.jinja_env.get_template = Mock(return_value=Mock(
                    render=Mock(return_value="<html>Test</html>")
                ))
                
                yield service, mock_resend
    
    def test_send_ingestion_complete_success(self, mock_email_service):
        """Should successfully send email with correct parameters."""
        service, mock_resend = mock_email_service
        
        result = service.send_ingestion_complete(
            to_email="user@example.com",
            name="John Doe",
            total_files=5
        )
        
        assert result == True
        mock_resend.Emails.send.assert_called_once()
        
        # Verify call parameters
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert call_args["to"] == ["user@example.com"]
        assert "🚀" in call_args["subject"]
        assert "Axio Hub" in call_args["from"]
    
    def test_send_ingestion_complete_disabled(self):
        """Should return False when service is disabled."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = None
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            from services.email import EmailService
            service = EmailService()
            service.enabled = False
            
            result = service.send_ingestion_complete(
                to_email="user@example.com",
                name="John",
                total_files=3
            )
            
            assert result == False
    
    def test_send_ingestion_complete_api_error_logged_not_raised(self, mock_email_service):
        """Should log error but not raise exception when API fails."""
        service, mock_resend = mock_email_service
        mock_resend.Emails.send.side_effect = Exception("API Error")
        
        # Should NOT raise exception
        result = service.send_ingestion_complete(
            to_email="user@example.com",
            name="John",
            total_files=3
        )
        
        assert result == False
    
    def test_send_ingestion_complete_uses_fallback_when_template_fails(self, mock_email_service):
        """Should use fallback HTML when template rendering fails."""
        service, mock_resend = mock_email_service
        service.jinja_env.get_template.side_effect = Exception("Template not found")
        
        result = service.send_ingestion_complete(
            to_email="user@example.com",
            name="John",
            total_files=3
        )
        
        # Should still send with fallback
        assert result == True
        call_args = mock_resend.Emails.send.call_args[0][0]
        assert "John" in call_args["html"]
        assert "3" in call_args["html"]


class TestEmailServiceTemplateRendering:
    """Tests for template rendering functionality."""
    
    def test_render_template_returns_none_without_jinja_env(self):
        """Should return None if jinja environment is not initialized."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            from services.email import EmailService
            service = EmailService()
            service.jinja_env = None
            
            result = service._render_template("test.html", name="John")
            
            assert result is None
    
    def test_render_template_handles_render_error(self):
        """Should return None and log error when render fails."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            from services.email import EmailService
            service = EmailService()
            service.jinja_env = Mock()
            service.jinja_env.get_template.side_effect = Exception("Not found")
            
            result = service._render_template("nonexistent.html", name="John")
            
            assert result is None


class TestEmailServiceWelcomeEmail:
    """Tests for send_welcome_email method."""
    
    def test_send_welcome_email_success(self):
        """Should successfully send welcome email."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_456"})
                
                from services.email import EmailService
                service = EmailService()
                service.enabled = True
                service.jinja_env = None  # Force fallback
                
                result = service.send_welcome_email(
                    to_email="newuser@example.com",
                    name="Jane"
                )
                
                assert result == True
                call_args = mock_resend.Emails.send.call_args[0][0]
                assert "Welcome" in call_args["subject"]
                assert "Jane" in call_args["html"]


class TestEmailServiceEdgeCases:
    """Edge case tests for EmailService."""
    
    def test_empty_email_address(self):
        """Should handle empty email address gracefully."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(side_effect=Exception("Invalid email"))
                
                from services.email import EmailService
                service = EmailService()
                service.enabled = True
                service.jinja_env = None
                
                result = service.send_ingestion_complete(
                    to_email="",
                    name="John",
                    total_files=3
                )
                
                assert result == False
    
    def test_special_characters_in_name(self):
        """Should handle special characters in name."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_789"})
                
                from services.email import EmailService
                service = EmailService()
                service.enabled = True
                service.jinja_env = None  # Force fallback
                
                result = service.send_ingestion_complete(
                    to_email="user@example.com",
                    name="<script>alert('xss')</script>",
                    total_files=3
                )
                
                # Should still work (HTML escaping in template)
                assert result == True
    
    def test_zero_files_processed(self):
        """Should handle zero files gracefully."""
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"
            
            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_000"})
                
                from services.email import EmailService
                service = EmailService()
                service.enabled = True
                service.jinja_env = None
                
                result = service.send_ingestion_complete(
                    to_email="user@example.com",
                    name="John",
                    total_files=0
                )
                
                assert result == True


class TestEmailServiceAdditionalNotifications:
    def _build_service(self, mock_resend):
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"

            mock_resend.Emails = Mock()
            mock_resend.Emails.send = Mock(return_value={"id": "email_999"})

            from services.email import EmailService
            service = EmailService()
            service.enabled = True
            service.jinja_env = None
            return service

    def test_send_ingestion_failed_fallback(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)

            result = service.send_ingestion_failed(
                to_email="user@example.com",
                name="Jane",
                filename="file.pdf",
                error_message="boom",
            )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "Ingestion Failed" in call_args["subject"]
            assert "boom" in call_args["html"]

    def test_send_retry_scheduled_fallback(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)

            result = service.send_retry_scheduled_email(
                to_email="user@example.com",
                name="Jane",
                task_name="Task A",
                next_retry_at="2026-01-01T00:00:00Z",
            )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "Retry Scheduled" in call_args["subject"]
            assert "Next retry" in call_args["html"]

    def test_send_retry_succeeded_fallback(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)

            result = service.send_retry_succeeded_email(
                to_email="user@example.com",
                name="Jane",
                task_name="Task A",
            )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "Retry Succeeded" in call_args["subject"]

    def test_send_permanently_failed_fallback(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)

            result = service.send_permanently_failed_email(
                to_email="user@example.com",
                name="Jane",
                task_name="Task A",
            )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "Task Failed" in call_args["subject"]

    def test_send_enterprise_inquiry_fallback(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)

            result = service.send_enterprise_inquiry(
                from_name="Alice",
                from_email="alice@example.com",
                company="Acme",
                team_size="100",
                message="Hello",
                user_id="user-1234567890",
            )

            assert result is True
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == ["sales@axiohub.io"]
            assert call_args["reply_to"] == "alice@example.com"


class TestEmailServiceDisabledPaths:
    def _build_service(self):
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"

            with patch('services.email.resend') as mock_resend:
                mock_resend.Emails = Mock()
                mock_resend.Emails.send = Mock(return_value={"id": "email_123"})

                from services.email import EmailService
                service = EmailService()
                service.enabled = False
                service.jinja_env = None
                return service

    def test_send_welcome_email_disabled(self):
        service = self._build_service()
        assert service.send_welcome_email("user@example.com", "Jane") is False

    def test_send_ingestion_failed_disabled(self):
        service = self._build_service()
        assert service.send_ingestion_failed("user@example.com", "Jane", "file.pdf", "boom") is False

    def test_send_retry_scheduled_disabled(self):
        service = self._build_service()
        assert service.send_retry_scheduled_email("user@example.com", "Jane", "Task", None) is False

    def test_send_retry_succeeded_disabled(self):
        service = self._build_service()
        assert service.send_retry_succeeded_email("user@example.com", "Jane", "Task") is False

    def test_send_permanently_failed_disabled(self):
        service = self._build_service()
        assert service.send_permanently_failed_email("user@example.com", "Jane", "Task") is False

    @pytest.mark.asyncio
    async def test_send_team_invite_disabled(self):
        service = self._build_service()
        assert await service.send_team_invite("user@example.com", "link", "Team") is False

    def test_send_enterprise_inquiry_disabled(self):
        service = self._build_service()
        assert service.send_enterprise_inquiry("Alice", "a@example.com", "Acme") is False


class TestEmailServiceExceptionPaths:
    def _build_service(self, mock_resend):
        with patch('services.email.settings') as mock_settings:
            mock_settings.RESEND_API_KEY = "re_test_key_123"
            mock_settings.EMAILS_FROM_EMAIL = "noreply@axiohub.io"
            mock_settings.APP_URL = "https://axiohub.io"

            mock_resend.Emails = Mock()
            mock_resend.Emails.send = Mock(side_effect=Exception("boom"))

            from services.email import EmailService
            service = EmailService()
            service.enabled = True
            service.jinja_env = None
            return service

    def test_send_welcome_email_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_welcome_email("user@example.com", "Jane") is False

    def test_send_ingestion_failed_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_ingestion_failed("user@example.com", "Jane", "file.pdf", "boom") is False

    def test_send_retry_scheduled_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_retry_scheduled_email("user@example.com", "Jane", "Task", None) is False

    def test_send_retry_succeeded_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_retry_succeeded_email("user@example.com", "Jane", "Task") is False

    def test_send_permanently_failed_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_permanently_failed_email("user@example.com", "Jane", "Task") is False

    @pytest.mark.asyncio
    async def test_send_team_invite_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert await service.send_team_invite("user@example.com", "link", "Team") is False

    def test_send_enterprise_inquiry_exception(self):
        with patch('services.email.resend') as mock_resend:
            service = self._build_service(mock_resend)
            assert service.send_enterprise_inquiry("Alice", "a@example.com", "Acme") is False
