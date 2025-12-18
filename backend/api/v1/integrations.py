from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core.security import get_current_user
from core.db import get_supabase
from core.config import settings
from google_auth_oauthlib.flow import Flow
from datetime import datetime, timedelta
import json

router = APIRouter()

class ExchangeRequest(BaseModel):
    code: str

@router.post("/integrations/google/exchange")
async def exchange_google_token(
    request: ExchangeRequest,
    user_id: str = Depends(get_current_user)
):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
         raise HTTPException(status_code=500, detail="Google credentials not configured")

    # 1. Exchange Code for Tokens
    try:
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
            redirect_uri=settings.GOOGLE_REDIRECT_URI
        )
        
        flow.fetch_token(code=request.code)
        creds = flow.credentials
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")

    # 2. Store in Supabase
    supabase = get_supabase()
    
    expires_at = (datetime.utcnow() + timedelta(seconds=creds.expiry.timestamp() - datetime.now().timestamp() if creds.expiry else 3600)).isoformat()
    
    data = {
        "user_id": user_id,
        "provider": "google_drive",
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "expires_at": expires_at,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # We rely on an upsert logic. Assuming 'user_id' + 'provider' is unique key or similar constraint.
    # If standard Supabase, we might need a unique constraint or primary key on (user_id, provider).
    # Trying upsert on conflict.
    
    try:
        # Check if exists to determine insert/update or just upsert if unique constraint exists
        # To be safe, we'll try to delete existing for this provider/user and insert new, 
        # or assume there's a unique constraint on (user_id, provider).
        # Let's try upsert assuming a unique constraint exists.
        
        res = supabase.table("user_integrations").upsert(data, on_conflict="user_id,provider").execute()
        
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {"status": "success", "provider": "google_drive"}
