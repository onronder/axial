import sys
from unittest.mock import MagicMock, patch, AsyncMock

# Mock resend module if not available
try:
    import resend
except ImportError:
    resend = MagicMock()
    sys.modules["resend"] = resend

import pytest
from services.email import EmailService

@pytest.mark.asyncio
async def test_send_team_invite_success():
    service = EmailService()
    service.enabled = True
    
    # Mock template rendering to return a string
    service._render_template = MagicMock(return_value="<html>Mock Invite</html>")
    
    # Mock resend.Emails.send
    with patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "msg_123"}
        
        result = await service.send_team_invite(
            "test@example.com", 
            "http://invite.link", 
            "MyTeam"
        )
            
    assert result is True
    # Verify render was called with correct context
    service._render_template.assert_called_with(
        "team_invite.html", 
        team_name="MyTeam", 
        invite_link="http://invite.link",
        app_url=service.app_url
    )
    # Verify resend was called
    mock_send.assert_called_once()
    call_args = mock_send.call_args[0][0]
    assert call_args["to"] == ["test@example.com"]
    assert "MyTeam" in call_args["subject"]
    assert call_args["html"] == "<html>Mock Invite</html>"

@pytest.mark.asyncio
async def test_send_team_invite_template_fallback():
    service = EmailService()
    service.enabled = True
    
    # Simulate render failure (returns None)
    service._render_template = MagicMock(return_value=None)
    
    with patch("resend.Emails.send") as mock_send:
        mock_send.return_value = {"id": "msg_123"}
        
        result = await service.send_team_invite("test@example.com", "link", "Team")
            
    assert result is True
    # Verify fallback text was used
    call_args = mock_send.call_args[0][0]
    assert "click here to join" in call_args["html"].lower()

@pytest.mark.asyncio
async def test_send_team_invite_exception_handling():
    service = EmailService()
    service.enabled = True
    
    service._render_template = MagicMock(return_value="content")
    
    # Simulate Resend API failure
    with patch("resend.Emails.send", side_effect=Exception("API Error")):
        result = await service.send_team_invite("test@example.com", "link", "Team")
        
    assert result is False
