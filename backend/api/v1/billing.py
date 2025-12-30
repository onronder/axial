import httpx
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.team_service import team_service
from core.config import settings
from core.security import get_current_user
from models import User

router = APIRouter()
logger = logging.getLogger(__name__)

class CheckoutRequest(BaseModel):
    plan: str  # 'starter' or 'pro'
    interval: str = "month"

@router.post("/checkout")
async def create_checkout_session(
    data: CheckoutRequest,
    current_user: str = Depends(get_current_user)
):
    if not settings.POLAR_ACCESS_TOKEN:
        logger.error("Polar Access Token is missing")
        raise HTTPException(500, "Billing configuration error")

    # 1. Get User's Team
    team_member = await team_service.get_user_team_member(current_user)
    if not team_member:
        raise HTTPException(400, "User has no team")
    
    team_id = str(team_member.team_id)

    # 2. Select Product ID
    if data.plan == "starter":
        product_id = settings.POLAR_PRODUCT_ID_STARTER_MONTHLY
    elif data.plan == "pro":
        product_id = settings.POLAR_PRODUCT_ID_PRO_MONTHLY
    else:
        raise HTTPException(400, "Invalid plan selected")

    if not product_id:
        raise HTTPException(500, f"Product ID for {data.plan} not configured")

    # 3. Call Polar API Directly (No SDK)
    polar_url = "https://api.polar.sh/v1/checkouts/custom/"
    headers = {
        "Authorization": f"Bearer {settings.POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "product_id": product_id,
        "metadata": {"team_id": team_id}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(polar_url, json=payload, headers=headers)
            response.raise_for_status()
            checkout_data = response.json()
            return {"url": checkout_data["url"]}
        except httpx.HTTPStatusError as e:
            logger.error(f"Polar API Error: {e.response.text}")
            raise HTTPException(500, f"Billing Provider Error: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected Billing Error: {str(e)}")
            raise HTTPException(500, "Failed to initiate checkout")

@router.post("/portal")
async def create_portal_session(current_user: str = Depends(get_current_user)):
    # Direct link to Polar Customer Portal (simplest integration)
    return {"url": "https://polar.sh/settings"}
