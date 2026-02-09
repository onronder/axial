import base64
import hashlib
import os
import secrets
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")

CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
TENANT_ID = os.getenv("MICROSOFT_TENANT_ID", "common")
REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "https://axiohub.io/oauth/callback")

# Scopes for OneDrive + SharePoint smoke validation
SCOPES = os.getenv(
    "MICROSOFT_SCOPES_SMOKE",
    "Files.Read.All Sites.Read.All User.Read offline_access",
)


def generate_pkce_pair():
    """Generate PKCE code_verifier and code_challenge for OAuth 2.0."""
    # Generate a random code verifier (43-128 chars, base64url-safe)
    code_verifier = secrets.token_urlsafe(64)

    # Create code_challenge = base64url(sha256(code_verifier))
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")

    return code_verifier, code_challenge


def run_smoke_test() -> None:
    print("--- MICROSOFT GRAPH SMOKE TEST ---")

    if not CLIENT_ID or not CLIENT_SECRET:
        print("ERROR: MICROSOFT_CLIENT_ID or MICROSOFT_CLIENT_SECRET missing.")
        return

    # Generate PKCE pair (required by Microsoft for cross-origin flows)
    code_verifier, code_challenge = generate_pkce_pair()
    print(f"\n[PKCE] Generated code_verifier ({len(code_verifier)} chars)")

    # 1) Build login URL with PKCE
    base_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/authorize"
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": SCOPES,
        "state": "smoke_test_123",
        "prompt": "consent",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    auth_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    print("\n1) Open the following URL and log in:\n")
    print(auth_url)
    print("\nCopy the value of the ?code=... param from the redirect URL.")

    auth_code = input("\nPaste the code here: ").strip()
    if not auth_code:
        print("ERROR: No authorization code provided.")
        return

    # 2) Exchange code for token (include code_verifier for PKCE)
    print("\nRequesting token...")
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": CLIENT_ID,
        "scope": SCOPES,
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
        "client_secret": CLIENT_SECRET,
        "code_verifier": code_verifier,
    }

    try:
        response = requests.post(token_url, data=data, timeout=20)
    except requests.RequestException as exc:
        print(f"ERROR: Token request failed: {exc}")
        return

    if response.status_code != 200:
        print(f"ERROR: Token exchange failed: {response.status_code} - {response.text}")
        return

    tokens = response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        print("ERROR: Token exchange returned no access token.")
        return

    print("OK: Access token acquired.")
    headers = {"Authorization": f"Bearer {access_token}"}

    # 3) OneDrive check
    print("\nOneDrive Test (/me/drive)...")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/me/drive", headers=headers, timeout=20)
        if response.status_code == 200:
            drive_data = response.json()
            owner_name = (drive_data.get("owner") or {}).get("user", {}).get("displayName")
            print(f"OK: Drive owner: {owner_name}")
            print(f"Info: Drive type: {drive_data.get('driveType')}")
        else:
            print(f"ERROR: OneDrive request failed: {response.status_code} - {response.text}")
    except requests.RequestException as exc:
        print(f"ERROR: OneDrive request failed: {exc}")

    # 4) SharePoint check
    print("\nSharePoint Test (/sites/root)...")
    try:
        response = requests.get("https://graph.microsoft.com/v1.0/sites/root", headers=headers, timeout=20)
        if response.status_code == 200:
            site_data = response.json()
            print(f"OK: Site name: {site_data.get('displayName')}")
            print(f"Info: Site URL: {site_data.get('webUrl')}")
        else:
            print(
                "WARN: SharePoint may not be available for personal accounts: "
                f"{response.status_code} - {response.text}"
            )
    except requests.RequestException as exc:
        print(f"ERROR: SharePoint request failed: {exc}")

    print("\nDONE.")


if __name__ == "__main__":
    run_smoke_test()
