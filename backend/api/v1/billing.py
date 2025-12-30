from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.team_service import team_service
from core.config import settings
from core.security import get_current_user
from models import User
from polar import Polar

router = APIRouter()

class CheckoutRequest(BaseModel):
    plan: str  # 'starter' or 'pro'
    interval: str = "month"

@router.post("/checkout")
async def create_checkout_session(
    data: CheckoutRequest,
    user_id: str = Depends(get_current_user)
):
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(500, "Billing not configured")

    # 1. Get User's Team
    # Adapted: Pass user_id directly as get_current_user returns str
    team_member = await team_service.get_user_team_member(user_id)
    if not team_member:
        raise HTTPException(400, "User has no team")
    
    team_id = str(team_member.team_id)

    # 2. Select Product ID
    if data.plan == "starter":
        product_id = settings.POLAR_PRODUCT_ID_STARTER_MONTHLY
    elif data.plan == "pro":
        product_id = settings.POLAR_PRODUCT_ID_PRO_MONTHLY
    elif data.plan == "enterprise":
        product_id = settings.POLAR_PRODUCT_ID_ENTERPRISE
    else:
        raise HTTPException(400, "Invalid plan")

    if not product_id:
        raise HTTPException(500, "Plan product ID not configured")

    # 3. Create Checkout via Polar SDK
    client = Polar(access_token=settings.POLAR_ACCESS_TOKEN)
    try:
        checkout = client.checkouts.custom.create(
            product_id=product_id,
            metadata={"team_id": team_id}  # CRITICAL: Link payment to Team
        )
        return {"url": checkout.url}
    except Exception as e:
        raise HTTPException(500, f"Polar Error: {str(e)}")

@router.post("/portal")
async def create_portal_session(current_user: str = Depends(get_current_user)):
    # Simple redirect to Polar Customer Portal for now
    return {"url": "https://polar.sh/settings"}
