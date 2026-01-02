import asyncio
import httpx
import os
import sys
from dotenv import load_dotenv

# Load env vars
load_dotenv()

# Add backend directory to path (parent of tests)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from core.config import settings

async def debug_polar():
    print("🔍 Debugging Polar Starter Plan...")
    
    token = settings.POLAR_ACCESS_TOKEN
    starter_id = settings.POLAR_PRODUCT_ID_STARTER_MONTHLY
    
    print(f"🔑 Configured Token (Last 4): ...{token[-4:] if token else 'None'}")
    print(f"🆔 Configured Starter ID: {starter_id}")
    
    if not token:
        print("❌ Error: POLAR_ACCESS_TOKEN not found in environment.")
        return

    url = "https://api.polar.sh/v1/products?is_archived=false"
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            print(f"🌐 Fetching products from {url}...")
            response = await client.get(url, headers=headers)
            print(f"   -> Final URL: {response.url}")
            
            if response.status_code != 200:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                return
                
            data = response.json()
            items = data.get("items", [])
            print(f"📦 Found {len(items)} products total.")
            
            starter_found = False
            for item in items:
                p_id = item.get("id")
                name = item.get("name")
                prices = item.get("prices", [])
                
                # Check if this is the configured starter product
                is_target = (p_id == starter_id)
                
                if is_target:
                    starter_found = True
                    print("\n✅ MATCH FOUND: Configured Starter Product")
                elif "starter" in name.lower():
                    print("\n⚠️ POTENTIAL MATCH: Product with 'starter' in name (but diff ID)")
                else:
                    continue # Skip unrelated products to reduce noise
                
                print(f"   - Name: {name}")
                print(f"   - ID: {p_id}")
                print(f"   - Prices Count: {len(prices)}")
                for i, price in enumerate(prices):
                    amt = price.get("price_amount")
                    currency = price.get("price_currency")
                    interval = price.get("recurring_interval")
                    print(f"     💲 Price [{i}]: {amt} {currency} ({interval})")
                    
            if not starter_found:
                print(f"\n❌ ERROR: Content of POLAR_PRODUCT_ID_STARTER_MONTHLY ({starter_id}) was NOT found in the API response list.")
                print("   Double check that the ID in .env matches the ID in Polar.")

        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(debug_polar())
