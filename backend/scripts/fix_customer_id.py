"""
One-time script to fetch and update customer_id from Polar.

Run this in your backend environment:
python scripts/fix_customer_id.py
"""
import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

POLAR_ACCESS_TOKEN = os.getenv("POLAR_ACCESS_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

async def fix_customer_ids():
    """Fetch customer_id from Polar for all subscriptions missing it."""
    
    if not POLAR_ACCESS_TOKEN:
        print("ERROR: POLAR_ACCESS_TOKEN not set")
        return
    
    headers = {
        "Authorization": f"Bearer {POLAR_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Get all subscriptions with null customer_id
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    response = supabase.table("subscriptions").select("*").is_("customer_id", "null").execute()
    subscriptions = response.data
    
    print(f"Found {len(subscriptions)} subscriptions without customer_id")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for sub in subscriptions:
            polar_id = sub.get("polar_id")
            team_id = sub.get("team_id")
            
            if not polar_id:
                print(f"  Skipping team {team_id} - no polar_id")
                continue
            
            print(f"\nFetching customer_id for polar_id: {polar_id}")
            
            try:
                # Fetch subscription details from Polar
                response = await client.get(
                    f"https://api.polar.sh/v1/subscriptions/{polar_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    customer = data.get("customer", {})
                    customer_id = customer.get("id")
                    
                    if customer_id:
                        print(f"  Found customer_id: {customer_id}")
                        
                        # Update our database
                        supabase.table("subscriptions").update({
                            "customer_id": customer_id
                        }).eq("team_id", team_id).execute()
                        
                        print(f"  ✅ Updated team {team_id}")
                    else:
                        print(f"  ⚠️ No customer in subscription data")
                        print(f"  Response: {data}")
                else:
                    print(f"  ❌ Polar API error: {response.status_code}")
                    print(f"  Response: {response.text}")
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
    
    print("\n✅ Done!")

if __name__ == "__main__":
    asyncio.run(fix_customer_ids())
