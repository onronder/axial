import httpx
import os
import asyncio
from dotenv import load_dotenv

# Load env from root
load_dotenv(".env")

async def verify_polar():
    token = os.getenv("POLAR_ACCESS_TOKEN")
    if not token:
        print("❌ POLAR_ACCESS_TOKEN not found in .env")
        return

    print(f"🔑 Testing with token: {token[:4]}...{token[-4:]}")

    url = "https://api.polar.sh/v1/products?is_archived=false"
    headers = {
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient() as client:
        try:
            print(f"🌐 Requesting: {url}")
            response = await client.get(url, headers=headers, follow_redirects=True)
            
            print(f"✅ Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                print(f"📦 Found {len(items)} products:")
                for item in items:
                    name = item.get("name")
                    price_info = item.get("prices", [{}])[0]
                    amount = price_info.get("price_amount", 0)
                    currency = price_info.get("price_currency", "usd")
                    print(f"   - {name} (ID: {item.get('id')}): {amount/100} {currency.upper()}")
            else:
                print(f"❌ Error Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    asyncio.run(verify_polar())
