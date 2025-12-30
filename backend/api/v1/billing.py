import httpx
import logging
from typing import List, Optional
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

class PlanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    price_amount: int
    price_currency: str
    interval: str
    type: str # 'starter', 'pro'

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """
    Fetches live pricing plans directly from Polar.sh
    """
    if not settings.POLAR_ACCESS_TOKEN:
        logger.warning("Polar token missing, returning empty plans.")
        return []

    polar_url = "https://api.polar.sh/v1/products?is_archived=false"
    headers = {
        "Authorization": f"Bearer {settings.POLAR_ACCESS_TOKEN}",
    }

    async with httpx.AsyncClient() as client:
        try:
            # 1. Get all products from Polar organization
            response = await client.get(polar_url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Polar API returned {response.status_code}: {response.text}")
                return []
                
            data = response.json()
            items = data.get("items", [])

            # 2. Map and Filter based on our Configured IDs
            plans = []
            target_ids = {
                settings.POLAR_PRODUCT_ID_STARTER_MONTHLY: "starter",
                settings.POLAR_PRODUCT_ID_PRO_MONTHLY: "pro"
            }

            for item in items:
                p_id = item.get("id")
                if p_id in target_ids:
                    # Extract price
                    prices = item.get("prices", [])
                    if not prices:
                        continue
                    
                    price_obj = prices[0]
                    
                    plans.append({
                        "id": p_id,
                        "name": item.get("name"),
                        "description": item.get("description", ""),
                        "price_amount": price_obj.get("price_amount", 0),
                        "price_currency": price_obj.get("price_currency", "usd"),
                        "interval": price_obj.get("recurring_interval", "month"),
                        "type": target_ids[p_id]
                    })
            
            # Sort: Starter first, then Pro
            plans.sort(key=lambda x: 0 if x['type'] == 'starter' else 1)
            
            return plans

        except Exception as e:
            logger.error(f"Failed to fetch plans from Polar: {e}")
            return []

@router.post("/checkout")
async def create_checkout_session(
    data: CheckoutRequest,
    current_user_id: str = Depends(get_current_user)
):
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(500, "Billing not configured")

    # 1. Get User's Team
    team_member = await team_service.get_user_team_member(current_user_id)
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

    # 3. Call Polar API Directly
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
            return {"url": response.json()["url"]}
        except Exception as e:
            logger.error(f"Checkout Error: {e}")
            raise HTTPException(500, "Failed to initiate checkout")

@router.post("/portal")
async def create_portal_session(current_user_id: str = Depends(get_current_user)):
    return {"url": "https://polar.sh/settings"}
