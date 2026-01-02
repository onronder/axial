"""
Email Service using Resend API

Provides fail-safe email sending for transactional notifications.
Errors are logged but never raised to callers - email is secondary to core functionality.
"""

import logging
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

try:
    import resend
except ImportError:
    resend = None

from core.config import settings

logger = logging.getLogger(__name__)

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class EmailService:
    """
    Resend-based email service for transactional notifications.
    
    All methods are fail-safe: errors are logged but never raised.
    This ensures email failures don't crash worker processes.
    """
    
    def __init__(self):
        self.api_key = settings.RESEND_API_KEY
        self.from_email = settings.EMAILS_FROM_EMAIL
        self.app_url = settings.APP_URL
        self.enabled = bool(self.api_key and resend)
        
        if self.enabled:
            resend.api_key = self.api_key
            logger.info("📧 EmailService initialized with Resend API")
        else:
            if not resend:
                logger.warning("📧 EmailService: resend package not installed")
            elif not self.api_key:
                logger.warning("📧 EmailService: RESEND_API_KEY not configured")
        
        # Initialize Jinja2 environment
        if TEMPLATES_DIR.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATES_DIR)),
                autoescape=True
            )
        else:
            self.jinja_env = None
            logger.warning(f"📧 EmailService: Templates directory not found at {TEMPLATES_DIR}")
    
    def _render_template(self, template_name: str, **context) -> Optional[str]:
        """Render an HTML template with context."""
        if not self.jinja_env:
            logger.error(f"📧 Cannot render template: Jinja environment not initialized")
            return None
        
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"📧 Failed to render template {template_name}: {e}")
            return None
    
    def send_ingestion_complete(
        self,
        to_email: str,
        name: str,
        total_files: int
    ) -> bool:
        """
        Send notification when document ingestion is complete.
        
        Args:
            to_email: Recipient email address
            name: User's display name
            total_files: Number of files processed
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("📧 Email not sent: service not enabled")
            return False
        
        try:
            # Render HTML template
            html_content = self._render_template(
                "ingestion_complete.html",
                name=name,
                total_files=total_files,
                app_url=self.app_url
            )
            
            if not html_content:
                # Fallback to plain text if template fails
                html_content = f"""
                <p>Hello {name},</p>
                <p>We've successfully processed <strong>{total_files} documents</strong>.</p>
                <p>Your AI assistant has digested this new information and is ready to answer your questions.</p>
                <p><a href="{self.app_url}/dashboard">Go to Dashboard</a></p>
                """
            
            # Send via Resend API
            params = {
                "from": f"Axio Hub <{self.from_email}>",
                "to": [to_email],
                "subject": "🚀 Your Knowledge Base is Ready!",
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"📧 Sent ingestion complete email to {to_email}, id={response.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            # CRITICAL: Log but never raise - email is secondary functionality
            logger.error(f"📧 Failed to send ingestion complete email to {to_email}: {e}")
            return False
    
    def send_welcome_email(self, to_email: str, name: str) -> bool:
        """
        Send welcome email to new users.
        
        Args:
            to_email: Recipient email address
            name: User's display name
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("📧 Email not sent: service not enabled")
            return False
        
        try:
            html_content = self._render_template(
                "welcome.html",
                name=name,
                app_url=self.app_url
            )
            
            if not html_content:
                html_content = f"""
                <p>Hello {name},</p>
                <p>Welcome to Axio Hub! Your AI-powered knowledge assistant is ready.</p>
                <p><a href="{self.app_url}/dashboard">Get Started</a></p>
                """
            
            params = {
                "from": f"Axio Hub <{self.from_email}>",
                "to": [to_email],
                "subject": "Welcome to Axio Hub! 🎉",
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"📧 Sent welcome email to {to_email}, id={response.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"📧 Failed to send welcome email to {to_email}: {e}")
            return False
    
    def send_ingestion_failed(
        self,
        to_email: str,
        name: str,
        filename: str,
        error_message: str
    ) -> bool:
        """
        Send notification when document ingestion fails.
        
        Args:
            to_email: Recipient email address
            name: User's display name
            filename: Name of the file that failed
            error_message: Error details (truncated for safety)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("📧 Email not sent: service not enabled")
            return False
        
        try:
            # Truncate error message for safety
            safe_error = str(error_message)[:500] if error_message else "Unknown error"
            
            html_content = self._render_template(
                "ingestion_failed.html",
                name=name,
                filename=filename,
                error_message=safe_error,
                app_url=self.app_url
            )
            
            if not html_content:
                # Fallback if template fails
                html_content = f"""
                <p>Hello {name},</p>
                <p>Processing failed for: {filename}</p>
                <p>Reason: {safe_error}</p>
                """
            
            params = {
                "from": f"Axio Hub <{self.from_email}>",
                "to": [to_email],
                "subject": f"⚠️ Ingestion Failed: {filename[:50]}",
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"📧 Sent ingestion failed email to {to_email}, id={response.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"📧 Failed to send ingestion failed email to {to_email}: {e}")
            return False


    async def send_team_invite(
        self,
        to_email: str,
        invite_link: str,
        team_name: str
    ) -> bool:
        """
        Sends a team invitation email.
        """
        if not self.enabled:
            logger.debug("📧 Email not sent: service not enabled")
            return False

        try:
            # Render HTML template using established helper
            # Note: User request allowed manual loading, but _render_template is safer/cleaner abstraction
            # checking if template exists is handled inside _render_template
            html_content = self._render_template(
                "team_invite.html",
                team_name=team_name,
                invite_link=invite_link,
                app_url=self.app_url
            )
            
            if not html_content:
                # Fallback to plain text if template fails
                html_content = f"""
                <p>Hello,</p>
                <p>You have been invited to join the team <strong>{team_name}</strong> on Axio Hub.</p>
                <p><a href="{invite_link}">Click here to join</a></p>
                """
            
            # Helper to wrap sync resend call if we wanted true async, but for now simple awaitable wrapper
            # Use self.send_email equivalent logic
            params = {
                "from": f"Axio Hub <{self.from_email}>",
                "to": [to_email],
                "subject": f"Invitation to join {team_name}",
                "html": html_content,
            }
            
            response = resend.Emails.send(params)
            logger.info(f"📧 Sent team invite to {to_email}, id={response.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"📧 Failed to send team invite to {to_email}: {e}")
            return False

    def send_enterprise_inquiry(
        self,
        from_name: str,
        from_email: str,
        company: str,
        team_size: str = "",
        message: str = "",
        user_id: str = ""
    ) -> bool:
        """
        Send enterprise inquiry email to sales team.
        
        Args:
            from_name: Name of the person inquiring
            from_email: Their email address
            company: Company name
            team_size: Expected team size
            message: Additional message
            user_id: Axio Hub user ID
        """
        if not self.enabled:
            logger.warning("📧 Email service not enabled - enterprise inquiry not sent")
            return False
        
        try:
            from datetime import datetime
            
            html_content = self._render_template(
                "enterprise_lead.html",
                name=from_name,
                user_email=from_email,
                company_name=company,
                team_size=team_size or "Not specified",
                message=message or "No additional message provided.",
                user_id=user_id[:8] + "..." if user_id else "Unknown",
                submitted_at=datetime.now().strftime("%Y-%m-%d %H:%M UTC")
            )
            
            if not html_content:
                # Fallback if template fails
                html_content = f"""
                <h2>New Enterprise Inquiry</h2>
                <p><strong>Name:</strong> {from_name}</p>
                <p><strong>Email:</strong> {from_email}</p>
                <p><strong>Company:</strong> {company}</p>
                <p><strong>Message:</strong> {message or 'None'}</p>
                """
            
            params = {
                "from": self.from_email,
                "to": ["sales@axiohub.io"],  # Send to sales team
                "reply_to": from_email,  # Reply goes to the person inquiring
                "subject": f"🏢 Enterprise Inquiry from {from_name} at {company}",
                "html": html_content
            }
            
            response = resend.Emails.send(params)
            logger.info(f"📧 Sent enterprise inquiry from {from_email}, id={response.get('id', 'unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"📧 Failed to send enterprise inquiry: {e}")
            return False


# Singleton instance for easy import
email_service = EmailService()

