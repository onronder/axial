"""
Billing API Router

Endpoints for subscription management, checkout, and billing history.
Integrates with Polar.sh for payment processing.
"""
import httpx
import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from services.team_service import team_service
from core.config import settings
from core.security import get_current_user
from core.db import get_supabase

router = APIRouter()
logger = logging.getLogger(__name__)


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
    order_id: str
    amount: int  # in cents
    currency: str
    status: str
    created_at: str
    product_name: str
    invoice_url: Optional[str] = None


class SubscriptionResponse(BaseModel):
    id: str
    status: str
    plan_name: str
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False


class PortalResponse(BaseModel):
    url: str


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_polar_headers() -> dict:
    """Get authorization headers for Polar API calls."""
    return {
        "Authorization": f"Bearer {settings.POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }


async def get_team_subscription_id(team_id: str) -> Optional[str]:
    """Get Polar subscription ID from our database."""
    supabase = get_supabase()
    response = supabase.table("subscriptions").select(
        "polar_id"
    ).eq("team_id", team_id).limit(1).execute()
    
    if response.data and response.data[0].get("polar_id"):
        return response.data[0]["polar_id"]
    return None


# ============================================================
# PLANS ENDPOINT
# ============================================================

@router.get("/plans", response_model=List[PlanResponse])
async def list_plans():
    """
    Fetch available plans from Polar.
    Returns pricing information for Starter, Pro, and Enterprise plans.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        logger.warning("[Billing] Polar token not configured")
        return []

    polar_url = "https://api.polar.sh/v1/products?is_archived=false"
    
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            response = await client.get(polar_url, headers=get_polar_headers())
            
            if response.status_code != 200:
                logger.error(f"[Billing] Polar API Error: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            items = data.get("items", [])
            plans = []
            
            # Map Polar Product IDs to plan types
            product_mapping = {
                settings.POLAR_PRODUCT_ID_STARTER_MONTHLY: "starter",
                settings.POLAR_PRODUCT_ID_PRO_MONTHLY: "pro",
            }
            
            # Add enterprise if configured
            if hasattr(settings, 'POLAR_PRODUCT_ID_ENTERPRISE') and settings.POLAR_PRODUCT_ID_ENTERPRISE:
                product_mapping[settings.POLAR_PRODUCT_ID_ENTERPRISE] = "enterprise"

            for item in items:
                product_id = item.get("id")
                if product_id in product_mapping:
                    prices = item.get("prices", [])
                    if not prices:
                        continue
                    
                    # Get the first (primary) price
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
            
            # Sort: starter first, then pro, then enterprise
            order = {"starter": 0, "pro": 1, "enterprise": 2}
            plans.sort(key=lambda x: order.get(x.type, 99))
            
            logger.info(f"[Billing] Fetched {len(plans)} plans from Polar")
            return plans
            
        except httpx.TimeoutException:
            logger.error("[Billing] Polar API timeout")
            return []
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
    Returns a URL to redirect the user to Polar's checkout page.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")

    # Get user's team
    team_member = await team_service.get_user_team_member(current_user_id)
    if not team_member:
        raise HTTPException(status_code=400, detail="User has no team")
    
    team_id = str(team_member.team_id)
    
    # Map plan to product ID
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
                "https://api.polar.sh/v1/checkouts/custom/",
                json={
                    "product_id": product_id,
                    "success_url": f"{settings.APP_URL}/settings?tab=billing&checkout=success",
                    "metadata": {"team_id": team_id}
                },
                headers=get_polar_headers()
            )
            response.raise_for_status()
            checkout_data = response.json()
            
            logger.info(f"[Billing] Created checkout for team {team_id[:8]}... - plan: {data.plan}")
            return {"url": checkout_data["url"]}
            
        except httpx.HTTPStatusError as e:
            logger.error(f"[Billing] Checkout creation failed: {e.response.text}")
            raise HTTPException(status_code=500, detail="Failed to create checkout session")
        except Exception as e:
            logger.error(f"[Billing] Checkout error: {e}")
            raise HTTPException(status_code=500, detail="Failed to create checkout session")


# ============================================================
# CUSTOMER PORTAL ENDPOINT
# ============================================================

@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(current_user_id: str = Depends(get_current_user)):
    """
    Create a Polar customer portal session for subscription management.
    
    Note: Polar uses a shared portal at polar.sh/settings for customers.
    For a more integrated experience, we redirect to the organization's
    Polar page where customers can manage their subscriptions.
    """
    # Polar currently doesn't have a dedicated customer portal API like Stripe.
    # The best option is to redirect customers to polar.sh where they can manage
    # their subscriptions by logging in with the same email.
    
    # The correct URL is the purchases page where customers can see their subscriptions
    portal_url = "https://polar.sh/~"  # User's dashboard after login
    
    logger.info(f"[Billing] Portal redirect for user {current_user_id[:8]}...")
    return PortalResponse(url=portal_url)


# ============================================================
# SUBSCRIPTION STATUS ENDPOINT
# ============================================================

@router.get("/subscription", response_model=Optional[SubscriptionResponse])
async def get_current_subscription(current_user_id: str = Depends(get_current_user)):
    """
    Get the current user's subscription details from our database.
    """
    try:
        # Get user's team
        team_member = await team_service.get_user_team_member(current_user_id)
        if not team_member:
            return None
        
        team_id = str(team_member.team_id)
        
        # Get subscription from our database
        supabase = get_supabase()
        response = supabase.table("subscriptions").select(
            "polar_id, status, plan_type, created_at, updated_at"
        ).eq("team_id", team_id).limit(1).execute()
        
        if not response.data:
            return None
        
        sub = response.data[0]
        
        return SubscriptionResponse(
            id=sub.get("polar_id", ""),
            status=sub.get("status", "inactive"),
            plan_name=sub.get("plan_type", "free"),
            current_period_start=sub.get("created_at"),
            current_period_end=None,  # Would need to fetch from Polar
            cancel_at_period_end=False
        )
        
    except Exception as e:
        logger.error(f"[Billing] Failed to get subscription: {e}")
        return None


# ============================================================
# BILLING HISTORY / INVOICES ENDPOINT
# ============================================================

@router.get("/invoices", response_model=List[InvoiceResponse])
async def get_billing_history(current_user_id: str = Depends(get_current_user)):
    """
    Get billing history (orders) from Polar.
    
    Uses the Polar Orders API to fetch past purchases for the customer.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        return []
    
    try:
        # Get user's team and subscription info
        team_member = await team_service.get_user_team_member(current_user_id)
        if not team_member:
            return []
        
        team_id = str(team_member.team_id)
        
        # Get subscription from our database to find customer context
        supabase = get_supabase()
        sub_response = supabase.table("subscriptions").select(
            "polar_id"
        ).eq("team_id", team_id).limit(1).execute()
        
        if not sub_response.data or not sub_response.data[0].get("polar_id"):
            # No subscription record = no billing history
            return []
        
        polar_subscription_id = sub_response.data[0]["polar_id"]
        
        # Fetch orders from Polar using subscription ID
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get orders associated with this subscription
            orders_url = f"https://api.polar.sh/v1/orders?subscription_id={polar_subscription_id}"
            
            response = await client.get(orders_url, headers=get_polar_headers())
            
            if response.status_code != 200:
                logger.warning(f"[Billing] Failed to fetch orders: {response.status_code}")
                # Fallback: Try getting subscription details instead
                return await _get_orders_fallback(polar_subscription_id)
            
            orders_data = response.json()
            items = orders_data.get("items", [])
            
            invoices = []
            for item in items:
                # Extract product name from the order
                product = item.get("product", {})
                product_name = product.get("name", "Subscription")
                
                invoices.append(InvoiceResponse(
                    id=item.get("id", ""),
                    order_id=item.get("id", ""),
                    amount=item.get("total_amount", 0),
                    currency=item.get("currency", "usd"),
                    status=item.get("status", "unknown"),
                    created_at=item.get("created_at", ""),
                    product_name=product_name,
                    invoice_url=item.get("invoice_url")  # May need to generate
                ))
            
            # Sort by date descending (most recent first)
            invoices.sort(key=lambda x: x.created_at, reverse=True)
            
            logger.info(f"[Billing] Fetched {len(invoices)} orders for team {team_id[:8]}...")
            return invoices
            
    except Exception as e:
        logger.error(f"[Billing] Failed to fetch billing history: {e}")
        return []


async def _get_orders_fallback(subscription_id: str) -> List[InvoiceResponse]:
    """
    Fallback method to get order info from subscription details.
    Used when direct orders query fails.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            sub_url = f"https://api.polar.sh/v1/subscriptions/{subscription_id}"
            response = await client.get(sub_url, headers=get_polar_headers())
            
            if response.status_code != 200:
                return []
            
            sub_data = response.json()
            product = sub_data.get("product", {})
            
            # Create a single "invoice" from subscription data
            prices = product.get("prices", [{}])
            price = prices[0] if prices else {}
            
            return [InvoiceResponse(
                id=subscription_id,
                order_id=subscription_id,
                amount=price.get("price_amount", 0),
                currency=price.get("price_currency", "usd"),
                status=sub_data.get("status", "active"),
                created_at=sub_data.get("created_at", ""),
                product_name=product.get("name", "Subscription"),
                invoice_url=None
            )]
            
    except Exception as e:
        logger.error(f"[Billing] Orders fallback failed: {e}")
        return []


# ============================================================
# INVOICE/RECEIPT DOWNLOAD ENDPOINT
# ============================================================

@router.post("/invoices/{order_id}/generate")
async def generate_invoice(
    order_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Trigger invoice generation for an order.
    
    Polar requires generating an invoice before it can be downloaded.
    This is a two-step process: generate (POST) then retrieve (GET).
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Generate the invoice
            generate_url = f"https://api.polar.sh/v1/orders/{order_id}/invoice"
            response = await client.post(generate_url, headers=get_polar_headers())
            
            if response.status_code == 202:
                # Invoice generation scheduled
                logger.info(f"[Billing] Invoice generation scheduled for order {order_id}")
                return {"status": "generating", "message": "Invoice generation started. Please wait a moment."}
            elif response.status_code == 200:
                # Invoice already exists
                return {"status": "ready", "message": "Invoice is ready for download."}
            else:
                logger.error(f"[Billing] Invoice generation failed: {response.text}")
                raise HTTPException(status_code=400, detail="Failed to generate invoice")
                
    except httpx.HTTPError as e:
        logger.error(f"[Billing] Invoice generation HTTP error: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate invoice")


@router.get("/invoices/{order_id}/download")
async def download_invoice(
    order_id: str,
    current_user_id: str = Depends(get_current_user)
):
    """
    Get the invoice/receipt download URL for an order.
    
    Returns a URL to download the PDF invoice.
    If invoice hasn't been generated, returns instructions to generate it first.
    """
    if not settings.POLAR_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Billing not configured")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to get the invoice
            invoice_url = f"https://api.polar.sh/v1/orders/{order_id}/invoice"
            response = await client.get(invoice_url, headers=get_polar_headers())
            
            if response.status_code == 200:
                invoice_data = response.json()
                download_url = invoice_data.get("url")
                
                if download_url:
                    logger.info(f"[Billing] Invoice download URL retrieved for order {order_id}")
                    return {"url": download_url}
                else:
                    # Invoice exists but no URL - try to get from response
                    return {"url": invoice_data.get("invoice_url", f"https://polar.sh/purchases")}
                    
            elif response.status_code == 404:
                # Invoice not generated yet
                return {
                    "error": "not_generated",
                    "message": "Invoice not yet generated. Please generate it first.",
                    "generate_url": f"/billing/invoices/{order_id}/generate"
                }
            else:
                logger.warning(f"[Billing] Invoice retrieval failed: {response.status_code}")
                # Fallback to Polar purchases page
                return {"url": "https://polar.sh/~"}
                
    except Exception as e:
        logger.error(f"[Billing] Invoice download failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve invoice")
