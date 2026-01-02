"""
Billing API Router - Production Grade

Integrates with Polar.sh for:
- Plan listing with real prices
- Checkout session creation
- Customer Portal session (pre-authenticated)
- Subscription management
- Order/Invoice history

Polar API Reference:
- POST /v1/customer-sessions - Create authenticated portal session
- GET /v1/subscriptions/?customer_id={id} - List customer subscriptions
- GET /v1/orders/?customer_id={id} - List customer orders
- GET /v1/customers/{id} - Get customer details
"""
import httpx
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.team_service import team_service
from core.config import settings
from core.security import get_current_user
from core.db import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)

POLAR_API_BASE = "https://api.polar.sh/v1"


# ============================================================
# MODELS
# ============================================================

class CheckoutRequest(BaseModel):
    plan: str  # 'starter', 'pro', or 'enterprise'
    interval: str = "month"


class PlanResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = ""
    price_amount: int  # in cents
    price_currency: str
    interval: str
    type: str  # 'starter', 'pro', 'enterprise'


class InvoiceResponse(BaseModel):
    id: str
    amount: int  # in cents
    currency: str
    status: str
    created_at: str
    product_name: str
    invoice_url: Optional[str] = None


class SubscriptionDetailResponse(BaseModel):
    id: str
    status: str
    plan_name: str
    price_amount: int
    price_currency: str
    interval: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


class PortalResponse(BaseModel):
    url: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_polar_headers() -> dict:
    """Authorization headers for Polar Core API."""
    return {
        "Authorization": f"Bearer {settings.POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


async def get_customer_id_for_user(user_id: str) -> Optional[str]:
    """
    Get Polar customer_id for a user.
    
    Strategy:
    1. Check our subscriptions table for stored customer_id
    2. If not found, try to find customer by email via Polar API
    """
    try:
        # Get user's team
        team_member = await team_service.get_user_team_member(user_id)
        if not team_member:
            return None
        
        team_id = str(team_member.team_id)
        
        # Check our database first
        supabase = get_supabase()
        sub_response = supabase.table("subscriptions").select(
            "customer_id, polar_id"
        ).eq("team_id", team_id).limit(1).execute()
        
        if sub_response.data and sub_response.data[0].get("customer_id"):
            return sub_response.data[0]["customer_id"]
        
        # If no customer_id but we have polar_id, fetch from Polar
        if sub_response.data and sub_response.data[0].get("polar_id"):
            polar_sub_id = sub_response.data[0]["polar_id"]
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{POLAR_API_BASE}/subscriptions/{polar_sub_id}",
                    headers=get_polar_headers()
                )
                if response.status_code == 200:
                    sub_data = response.json()
                    customer_id = sub_data.get("customer", {}).get("id")
                    if customer_id:
                        # Cache it in our database
                        supabase.table("subscriptions").update({
                            "customer_id": customer_id
                        }).eq("team_id", team_id).execute()
                        return customer_id
        
        return None
        
    except Exception as e:
        logger.error(f"[Billing] Failed to get customer_id: {e}")
        return None


# ============================================================
# PLANS ENDPOINT
# ============================================================

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """
    Fetch available plans from Polar with real prices.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        logger.warning("[Billing] Polar token not configured")
        return []

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(
                f"{POLAR_API_BASE}/products?is_archived=false",
                headers=get_polar_headers()
            )
            
            if response.status_code != 200:
                logger.error(f"[Billing] Polar API Error: {response.status_code}")
                return []
            
            data = response.json()
            items = data.get("items", [])
            plans = []
            
            # Map Polar Product IDs to plan types
            product_mapping = {
                settings.POLAR_PRODUCT_ID_STARTER_MONTHLY: "starter",
                settings.POLAR_PRODUCT_ID_PRO_MONTHLY: "pro",
            }
            
            if hasattr(settings, 'POLAR_PRODUCT_ID_ENTERPRISE') and settings.POLAR_PRODUCT_ID_ENTERPRISE:
                product_mapping[settings.POLAR_PRODUCT_ID_ENTERPRISE] = "enterprise"

            for item in items:
                product_id = item.get("id")
                if product_id in product_mapping:
                    prices = item.get("prices", [])
                    if not prices:
                        continue
                    
                    price = prices[0]
                    plans.append(PlanResponse(
                        id=product_id,
                        name=item.get("name", ""),
                        description=item.get("description", ""),
                        price_amount=price.get("price_amount", 0),
                        price_currency=price.get("price_currency", "usd"),
                        interval=price.get("recurring_interval", "month"),
                        type=product_mapping[product_id]
                    ))
            
            # Sort: starter, pro, enterprise
            order = {"starter": 0, "pro": 1, "enterprise": 2}
            plans.sort(key=lambda x: order.get(x.type, 99))
            
            return plans
            
        except Exception as e:
            logger.error(f"[Billing] Failed to fetch plans: {e}")
            return []


# ============================================================
# CHECKOUT ENDPOINT
# ============================================================

@router.post("/checkout")
async def create_checkout_session(
    data: CheckoutRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Create a Polar checkout session for plan upgrade.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")

    team_member = await team_service.get_user_team_member(current_user_id)
    if not team_member:
        raise HTTPException(status_code=400, detail="User has no team")
    
    team_id = str(team_member.team_id)
    
    product_map = {
        "starter": getattr(settings, 'POLAR_PRODUCT_ID_STARTER_MONTHLY', None),
        "pro": getattr(settings, 'POLAR_PRODUCT_ID_PRO_MONTHLY', None),
        "enterprise": getattr(settings, 'POLAR_PRODUCT_ID_ENTERPRISE', None),
    }
    
    product_id = product_map.get(data.plan)
    if not product_id:
        raise HTTPException(status_code=400, detail=f"Invalid plan: {data.plan}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{POLAR_API_BASE}/checkouts/custom/",
                json={
                    "product_id": product_id,
                    "success_url": f"{settings.APP_URL}/settings?tab=billing&checkout=success",
                    "metadata": {"team_id": team_id}
                },
                headers=get_polar_headers()
            )
            response.raise_for_status()
            return {"url": response.json()["url"]}
            
        except Exception as e:
            logger.error(f"[Billing] Checkout error: {e}")
            raise HTTPException(status_code=500, detail="Failed to create checkout")


# ============================================================
# CUSTOMER PORTAL ENDPOINT
# ============================================================

@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(current_user_id: str = Depends(get_current_user)):
    """
    Create a Polar Customer Portal session.
    
    Uses POST /v1/customer-sessions with customer_id to get a 
    pre-authenticated customer_portal_url.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")
    
    try:
        customer_id = await get_customer_id_for_user(current_user_id)
        
        if not customer_id:
            logger.warning(f"[Billing] No customer_id for user {current_user_id[:8]}...")
            raise HTTPException(
                status_code=400, 
                detail="No subscription found. Please subscribe first."
            )
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                f"{POLAR_API_BASE}/customer-sessions",
                json={
                    "customer_id": customer_id,
                    "return_url": f"{settings.APP_URL}/settings?tab=billing"
                },
                headers=get_polar_headers()
            )
            
            if response.status_code in [200, 201]:
                session_data = response.json()
                portal_url = session_data.get("customer_portal_url")
                
                if portal_url:
                    logger.info(f"[Billing] Portal session created for {current_user_id[:8]}...")
                    return PortalResponse(url=portal_url)
            
            logger.error(f"[Billing] Customer session failed: {response.status_code} - {response.text}")
            raise HTTPException(status_code=500, detail="Failed to create portal session")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Billing] Portal error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


# ============================================================
# SUBSCRIPTION STATUS ENDPOINT  
# ============================================================

@router.get("/subscription", response_model=Optional[SubscriptionDetailResponse])
async def get_current_subscription(current_user_id: str = Depends(get_current_user)):
    """
    Get current subscription details from Polar.
    
    Uses GET /v1/subscriptions/?customer_id={id}
    """
    if not settings.POLAR_ACCESS_TOKEN:
        return None
    
    try:
        customer_id = await get_customer_id_for_user(current_user_id)
        
        if not customer_id:
            return None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{POLAR_API_BASE}/subscriptions/",
                params={"customer_id": customer_id, "active": True},
                headers=get_polar_headers()
            )
            
            if response.status_code != 200:
                logger.warning(f"[Billing] Subscription fetch failed: {response.status_code}")
                return None
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return None
            
            # Get first active subscription
            sub = items[0]
            product = sub.get("product", {})
            prices = product.get("prices", [{}])
            price = prices[0] if prices else {}
            
            return SubscriptionDetailResponse(
                id=sub.get("id", ""),
                status=sub.get("status", "unknown"),
                plan_name=product.get("name", "Unknown"),
                price_amount=price.get("price_amount", 0),
                price_currency=price.get("price_currency", "usd"),
                interval=price.get("recurring_interval", "month"),
                current_period_start=sub.get("current_period_start"),
                current_period_end=sub.get("current_period_end"),
                cancel_at_period_end=sub.get("cancel_at_period_end", False)
            )
            
    except Exception as e:
        logger.error(f"[Billing] Subscription error: {e}")
        return None


# ============================================================
# BILLING HISTORY / ORDERS ENDPOINT
# ============================================================

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_billing_history(current_user_id: str = Depends(get_current_user)):
    """
    Get billing history (orders) from Polar.
    
    Uses GET /v1/orders/?customer_id={id}
    """
    if not settings.POLAR_ACCESS_TOKEN:
        return []
    
    try:
        customer_id = await get_customer_id_for_user(current_user_id)
        
        if not customer_id:
            return []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{POLAR_API_BASE}/orders/",
                params={"customer_id": customer_id},
                headers=get_polar_headers()
            )
            
            if response.status_code != 200:
                logger.warning(f"[Billing] Orders fetch failed: {response.status_code}")
                return []
            
            data = response.json()
            items = data.get("items", [])
            
            invoices = []
            for item in items:
                product = item.get("product", {})
                
                invoices.append(InvoiceResponse(
                    id=item.get("id", ""),
                    amount=item.get("amount", 0),
                    currency=item.get("currency", "usd"),
                    status=item.get("status", "unknown"),
                    created_at=item.get("created_at", ""),
                    product_name=product.get("name", "Subscription"),
                    invoice_url=item.get("invoice_url")
                ))
            
            # Sort by date (most recent first)
            invoices.sort(key=lambda x: x.created_at, reverse=True)
            return invoices
            
    except Exception as e:
        logger.error(f"[Billing] Orders error: {e}")
        return []


# ============================================================
# INVOICE DOWNLOAD ENDPOINT
# ============================================================

@router.get("/invoices/{order_id}/download")
async def download_invoice(
    order_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Get invoice download URL for an order.
    
    Uses GET /v1/orders/{id}/invoice
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First try to get the invoice
            response = await client.get(
                f"{POLAR_API_BASE}/orders/{order_id}/invoice",
                headers=get_polar_headers()
            )
            
            if response.status_code == 200:
                invoice_data = response.json()
                return {"url": invoice_data.get("url")}
            
            elif response.status_code == 404:
                # Invoice not generated, generate it
                gen_response = await client.post(
                    f"{POLAR_API_BASE}/orders/{order_id}/invoice",
                    headers=get_polar_headers()
                )
                
                if gen_response.status_code == 202:
                    return {
                        "status": "generating",
                        "message": "Invoice is being generated. Please try again in a few seconds."
                    }
                    
            raise HTTPException(status_code=404, detail="Invoice not found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Billing] Invoice download error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get invoice")


# ============================================================
# ADMIN: FIX CUSTOMER_ID FOR EXISTING SUBSCRIPTIONS
# ============================================================

@router.post("/fix-customer-id")
async def fix_customer_id(current_user_id: str = Depends(get_current_user)):
    """
    Fetch and update customer_id from Polar for the current user's subscription.
    
    This is needed for subscriptions created before customer_id was stored.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")
    
    try:
        team_member = await team_service.get_user_team_member(current_user_id)
        if not team_member:
            raise HTTPException(status_code=400, detail="No team found")
        
        team_id = str(team_member.team_id)
        
        supabase = get_supabase()
        sub_response = supabase.table("subscriptions").select(
            "polar_id, customer_id"
        ).eq("team_id", team_id).limit(1).execute()
        
        if not sub_response.data:
            raise HTTPException(status_code=400, detail="No subscription found")
        
        sub = sub_response.data[0]
        polar_id = sub.get("polar_id")
        
        if not polar_id:
            raise HTTPException(status_code=400, detail="No Polar subscription ID")
        
        # Already has customer_id?
        if sub.get("customer_id"):
            return {"status": "ok", "customer_id": sub["customer_id"], "message": "Already has customer_id"}
        
        # Fetch from Polar
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{POLAR_API_BASE}/subscriptions/{polar_id}",
                headers=get_polar_headers()
            )
            
            logger.info(f"[Billing] Polar subscription response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                customer = data.get("customer", {})
                customer_id = customer.get("id")
                
                if customer_id:
                    # Update database
                    supabase.table("subscriptions").update({
                        "customer_id": customer_id
                    }).eq("team_id", team_id).execute()
                    
                    logger.info(f"[Billing] Updated customer_id for team {team_id}: {customer_id}")
                    return {"status": "ok", "customer_id": customer_id, "message": "Fixed!"}
                else:
                    return {"status": "error", "message": "No customer in subscription data", "data": data}
            else:
                return {
                    "status": "error", 
                    "message": f"Polar API error: {response.status_code}",
                    "response": response.text
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Billing] Fix customer_id error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# ENTERPRISE INQUIRY ENDPOINT
# ============================================================

class EnterpriseInquiryRequest(BaseModel):
    name: str
    email: str
    company: str
    message: str = ""
    team_size: str = ""


@router.post("/enterprise-inquiry")
async def submit_enterprise_inquiry(
    data: EnterpriseInquiryRequest,
    current_user_id: str = Depends(get_current_user)
):
    """
    Submit an enterprise inquiry - sends email to sales team via Resend.
    """
    try:
        # Import email service
        from services.email import email_service
        
        # Send email to sales
        success = email_service.send_enterprise_inquiry(
            from_name=data.name,
            from_email=data.email,
            company=data.company,
            team_size=data.team_size,
            message=data.message,
            user_id=current_user_id
        )
        
        if success:
            logger.info(f"[Billing] Enterprise inquiry sent from {data.email}")
            return {"status": "ok", "message": "Your inquiry has been sent. We'll get back to you shortly!"}
        else:
            logger.warning(f"[Billing] Failed to send enterprise inquiry from {data.email}")
            return {"status": "ok", "message": "Thank you for your interest! We'll contact you soon."}
            
    except Exception as e:
        logger.error(f"[Billing] Enterprise inquiry error: {e}")
        # Don't fail the request - just log it
        return {"status": "ok", "message": "Thank you for your interest! We'll contact you soon."}
