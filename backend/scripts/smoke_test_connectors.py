#!/usr/bin/env python3
from __future__ import annotations

"""
Post-transition smoke tests for all OAuth connectors.

Tests each connector's OAuth configuration and API connectivity.
Requires valid access tokens to be provided interactively.

Usage:
    # Test all connectors
    python backend/scripts/smoke_test_connectors.py

    # Test a specific connector
    python backend/scripts/smoke_test_connectors.py --connector google
    python backend/scripts/smoke_test_connectors.py --connector microsoft
    python backend/scripts/smoke_test_connectors.py --connector notion
    python backend/scripts/smoke_test_connectors.py --connector dropbox
    python backend/scripts/smoke_test_connectors.py --connector github
    python backend/scripts/smoke_test_connectors.py --connector box

    # Non-interactive mode (config check only, no API calls)
    python backend/scripts/smoke_test_connectors.py --config-only
"""

import argparse
import base64
import hashlib
import os
import secrets
import sys
import urllib.parse
from pathlib import Path

try:
    import requests
except ImportError:
    print("ERROR: requests library required. Install with: pip install requests")
    sys.exit(1)

# Load .env
ROOT_DIR = Path(__file__).resolve().parents[2]
try:
    from dotenv import load_dotenv
    for env_path in [ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

TIMEOUT = 20  # seconds for HTTP requests


def ok(msg: str) -> None:
    print(f"  {GREEN}OK{RESET}   {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}FAIL{RESET} {msg}")


def warn(msg: str) -> None:
    print(f"  {YELLOW}WARN{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}INFO{RESET} {msg}")


# ---------------------------------------------------------------------------
# Config check helpers
# ---------------------------------------------------------------------------

def get_env(name: str) -> str | None:
    val = os.environ.get(name, "").strip()
    return val if val else None


def check_config(name: str, required_vars: list[str]) -> dict[str, str | None]:
    """Check if required env vars are set. Returns dict of var->value."""
    result = {}
    all_ok = True
    for var in required_vars:
        val = get_env(var)
        result[var] = val
        if val:
            # Mask secrets
            if "SECRET" in var:
                ok(f"{var} = {val[:4]}...{'*' * 8}")
            elif "REDIRECT" in var:
                ok(f"{var} = {val}")
            else:
                ok(f"{var} = {val[:8]}..." if len(val) > 12 else f"{var} = {val}")
        else:
            fail(f"{var} is not set")
            all_ok = False

    if all_ok:
        ok(f"{name} configuration complete")
    else:
        fail(f"{name} configuration incomplete — cannot run API tests")

    return result


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

def smoke_google(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Google Drive Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("Google Drive", [
        "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    # Build auth URL for manual flow
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        + urllib.parse.urlencode({
            "client_id": cfg["GOOGLE_CLIENT_ID"],
            "redirect_uri": cfg["GOOGLE_REDIRECT_URI"],
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/drive.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": "smoke_test",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    # Exchange code
    info("Exchanging code for token...")
    try:
        resp = requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": cfg["GOOGLE_CLIENT_ID"],
                "client_secret": cfg["GOOGLE_CLIENT_SECRET"],
                "redirect_uri": cfg["GOOGLE_REDIRECT_URI"],
                "grant_type": "authorization_code",
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code} - {resp.text[:200]}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    if access_token:
        ok("Access token acquired")
    else:
        fail("No access token in response")
        return False

    if refresh_token:
        ok("Refresh token acquired (production mode confirmed)")
    else:
        warn("No refresh token — app may still be in test mode")

    # Test Drive API
    info("Testing Drive API (list files)...")
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            "https://www.googleapis.com/drive/v3/files?pageSize=5&fields=files(id,name,mimeType)",
            headers=headers,
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            files = resp.json().get("files", [])
            ok(f"File listing works — {len(files)} files returned")
            for f in files[:3]:
                info(f"  {f.get('name')} ({f.get('mimeType')})")
        else:
            fail(f"File listing failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"Drive API request failed: {e}")

    return True


# ---------------------------------------------------------------------------
# Microsoft OneDrive / SharePoint
# ---------------------------------------------------------------------------

def smoke_microsoft(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Microsoft OneDrive / SharePoint Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("Microsoft", [
        "MICROSOFT_CLIENT_ID", "MICROSOFT_CLIENT_SECRET",
        "MICROSOFT_REDIRECT_URI", "MICROSOFT_TENANT_ID"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    tenant = cfg["MICROSOFT_TENANT_ID"]

    # Generate PKCE pair
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    info(f"PKCE code_verifier generated ({len(code_verifier)} chars)")

    scopes = "offline_access User.Read Files.Read.All Sites.Read.All"
    auth_url = (
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?"
        + urllib.parse.urlencode({
            "client_id": cfg["MICROSOFT_CLIENT_ID"],
            "response_type": "code",
            "redirect_uri": cfg["MICROSOFT_REDIRECT_URI"],
            "response_mode": "query",
            "scope": scopes,
            "state": "smoke_test",
            "prompt": "consent",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    info("Exchanging code for token (with PKCE)...")
    try:
        resp = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": cfg["MICROSOFT_CLIENT_ID"],
                "scope": scopes,
                "code": code,
                "redirect_uri": cfg["MICROSOFT_REDIRECT_URI"],
                "grant_type": "authorization_code",
                "client_secret": cfg["MICROSOFT_CLIENT_SECRET"],
                "code_verifier": code_verifier,
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code} - {resp.text[:200]}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        fail("No access token in response")
        return False
    ok("Access token acquired")

    if tokens.get("refresh_token"):
        ok("Refresh token acquired")

    headers = {"Authorization": f"Bearer {access_token}"}

    # OneDrive test
    info("Testing OneDrive (/me/drive)...")
    try:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/me/drive",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            drive = resp.json()
            owner = (drive.get("owner") or {}).get("user", {}).get("displayName", "unknown")
            ok(f"OneDrive works — owner: {owner}, type: {drive.get('driveType')}")
        else:
            fail(f"OneDrive failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"OneDrive request failed: {e}")

    # SharePoint test
    info("Testing SharePoint (/sites/root)...")
    try:
        resp = requests.get(
            "https://graph.microsoft.com/v1.0/sites/root",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            site = resp.json()
            ok(f"SharePoint works — site: {site.get('displayName')}")
        else:
            warn(f"SharePoint not available (may require org account): {resp.status_code}")
    except requests.RequestException as e:
        warn(f"SharePoint request failed: {e}")

    return True


# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------

def smoke_notion(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Notion Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("Notion", [
        "NOTION_CLIENT_ID", "NOTION_CLIENT_SECRET", "NOTION_REDIRECT_URI"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    auth_url = (
        "https://api.notion.com/v1/oauth/authorize?"
        + urllib.parse.urlencode({
            "client_id": cfg["NOTION_CLIENT_ID"],
            "response_type": "code",
            "redirect_uri": cfg["NOTION_REDIRECT_URI"],
            "owner": "user",
            "state": "smoke_test",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    info("Exchanging code for token...")
    # Notion uses Basic auth for token exchange
    auth_header = base64.b64encode(
        f"{cfg['NOTION_CLIENT_ID']}:{cfg['NOTION_CLIENT_SECRET']}".encode()
    ).decode()

    try:
        resp = requests.post(
            "https://api.notion.com/v1/oauth/token",
            headers={
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/json",
            },
            json={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": cfg["NOTION_REDIRECT_URI"],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code} - {resp.text[:200]}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        fail("No access token in response")
        return False
    ok("Access token acquired")

    workspace = tokens.get("workspace_name", "unknown")
    ok(f"Workspace: {workspace}")

    # Test search API
    info("Testing Notion search (listing pages)...")
    try:
        resp = requests.post(
            "https://api.notion.com/v1/search",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json",
            },
            json={"page_size": 5},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            ok(f"Search works — {len(results)} results returned")
            for r in results[:3]:
                obj_type = r.get("object", "?")
                title = "untitled"
                if obj_type == "page":
                    props = r.get("properties", {}).get("title", {}).get("title", [])
                    if props:
                        title = props[0].get("plain_text", "untitled")
                elif obj_type == "database":
                    title_list = r.get("title", [])
                    if title_list:
                        title = title_list[0].get("plain_text", "untitled")
                info(f"  [{obj_type}] {title}")
        else:
            fail(f"Search failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"Notion search request failed: {e}")

    return True


# ---------------------------------------------------------------------------
# Dropbox
# ---------------------------------------------------------------------------

def smoke_dropbox(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Dropbox Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("Dropbox", [
        "DROPBOX_CLIENT_ID", "DROPBOX_CLIENT_SECRET", "DROPBOX_REDIRECT_URI"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    auth_url = (
        "https://www.dropbox.com/oauth2/authorize?"
        + urllib.parse.urlencode({
            "client_id": cfg["DROPBOX_CLIENT_ID"],
            "redirect_uri": cfg["DROPBOX_REDIRECT_URI"],
            "response_type": "code",
            "token_access_type": "offline",
            "state": "smoke_test",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    info("Exchanging code for token...")
    try:
        resp = requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": cfg["DROPBOX_CLIENT_ID"],
                "client_secret": cfg["DROPBOX_CLIENT_SECRET"],
                "redirect_uri": cfg["DROPBOX_REDIRECT_URI"],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code} - {resp.text[:200]}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        fail("No access token in response")
        return False
    ok("Access token acquired")

    if tokens.get("refresh_token"):
        ok("Refresh token acquired")

    account_id = tokens.get("account_id", "unknown")
    team_id = tokens.get("team_id")
    if team_id:
        ok(f"Team account detected (team_id: {team_id})")
    else:
        info(f"Personal account (account_id: {account_id})")

    # Test file listing
    info("Testing Dropbox (list folder root)...")
    try:
        resp = requests.post(
            "https://api.dropboxapi.com/2/files/list_folder",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={"path": "", "limit": 5},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            entries = resp.json().get("entries", [])
            ok(f"File listing works — {len(entries)} entries returned")
            for e in entries[:3]:
                info(f"  [{e.get('.tag')}] {e.get('name')}")
        else:
            fail(f"File listing failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"Dropbox request failed: {e}")

    return True


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def smoke_github(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  GitHub Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("GitHub", [
        "GITHUB_CLIENT_ID", "GITHUB_CLIENT_SECRET", "GITHUB_REDIRECT_URI"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    auth_url = (
        "https://github.com/login/oauth/authorize?"
        + urllib.parse.urlencode({
            "client_id": cfg["GITHUB_CLIENT_ID"],
            "redirect_uri": cfg["GITHUB_REDIRECT_URI"],
            "scope": "repo read:org",
            "state": "smoke_test",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    info("Exchanging code for token...")
    try:
        resp = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            data={
                "client_id": cfg["GITHUB_CLIENT_ID"],
                "client_secret": cfg["GITHUB_CLIENT_SECRET"],
                "code": code,
                "redirect_uri": cfg["GITHUB_REDIRECT_URI"],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        fail(f"No access token in response: {tokens.get('error_description', tokens.get('error', 'unknown'))}")
        return False
    ok("Access token acquired (indefinite lifetime)")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    # Test user info
    info("Testing GitHub user endpoint...")
    try:
        resp = requests.get(
            "https://api.github.com/user",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            user = resp.json()
            ok(f"Authenticated as: {user.get('login')} ({user.get('name')})")
        else:
            fail(f"User endpoint failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"GitHub request failed: {e}")

    # Test repo listing
    info("Testing GitHub repo listing...")
    try:
        resp = requests.get(
            "https://api.github.com/user/repos?per_page=5&sort=updated",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            repos = resp.json()
            ok(f"Repo listing works — {len(repos)} repos returned")
            for r in repos[:3]:
                info(f"  {r.get('full_name')} ({'private' if r.get('private') else 'public'})")
        else:
            fail(f"Repo listing failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"GitHub request failed: {e}")

    # Check rate limit
    info("Checking rate limit...")
    try:
        resp = requests.get(
            "https://api.github.com/rate_limit",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            rate = resp.json().get("resources", {}).get("core", {})
            ok(f"Rate limit: {rate.get('remaining')}/{rate.get('limit')} remaining")
    except requests.RequestException:
        pass

    return True


# ---------------------------------------------------------------------------
# Box
# ---------------------------------------------------------------------------

def smoke_box(config_only: bool = False) -> bool:
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Box Smoke Test{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    cfg = check_config("Box", [
        "BOX_CLIENT_ID", "BOX_CLIENT_SECRET", "BOX_REDIRECT_URI"
    ])

    if not all(cfg.values()) or config_only:
        return all(cfg.values())

    auth_url = (
        "https://account.box.com/api/oauth2/authorize?"
        + urllib.parse.urlencode({
            "client_id": cfg["BOX_CLIENT_ID"],
            "redirect_uri": cfg["BOX_REDIRECT_URI"],
            "response_type": "code",
            "state": "smoke_test",
        })
    )

    print(f"\n  Open this URL and authorize:\n  {auth_url}\n")
    code = input("  Paste the authorization code: ").strip()
    if not code:
        fail("No code provided")
        return False

    info("Exchanging code for token...")
    try:
        resp = requests.post(
            "https://api.box.com/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": cfg["BOX_CLIENT_ID"],
                "client_secret": cfg["BOX_CLIENT_SECRET"],
            },
            timeout=TIMEOUT,
        )
    except requests.RequestException as e:
        fail(f"Token exchange request failed: {e}")
        return False

    if resp.status_code != 200:
        fail(f"Token exchange failed: {resp.status_code} - {resp.text[:200]}")
        return False

    tokens = resp.json()
    access_token = tokens.get("access_token")
    if not access_token:
        fail("No access token in response")
        return False
    ok("Access token acquired (60-min lifetime)")

    if tokens.get("refresh_token"):
        ok("Refresh token acquired (single-use rotation)")

    # Test user info
    info("Testing Box user endpoint...")
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        resp = requests.get(
            "https://api.box.com/2.0/users/me",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            user = resp.json()
            ok(f"Authenticated as: {user.get('name')} ({user.get('login')})")
            enterprise = user.get("enterprise")
            if enterprise:
                ok(f"Enterprise: {enterprise.get('name')}")
            else:
                info("Personal/free account (no enterprise)")
        else:
            fail(f"User endpoint failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"Box request failed: {e}")

    # Test file listing
    info("Testing Box file listing (root folder)...")
    try:
        resp = requests.get(
            "https://api.box.com/2.0/folders/0/items?limit=5",
            headers=headers, timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            entries = resp.json().get("entries", [])
            ok(f"File listing works — {len(entries)} items returned")
            for e in entries[:3]:
                info(f"  [{e.get('type')}] {e.get('name')}")
        else:
            fail(f"File listing failed: {resp.status_code}")
    except requests.RequestException as e:
        fail(f"Box request failed: {e}")

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CONNECTORS = {
    "google": smoke_google,
    "microsoft": smoke_microsoft,
    "notion": smoke_notion,
    "dropbox": smoke_dropbox,
    "github": smoke_github,
    "box": smoke_box,
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke test OAuth connectors for production readiness"
    )
    parser.add_argument(
        "--connector", "-c",
        choices=list(CONNECTORS.keys()),
        help="Test a specific connector (default: all)",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only check configuration, skip interactive OAuth tests",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Axial — OAuth Connector Smoke Tests{RESET}")
    if args.config_only:
        print(f"{YELLOW}  (Config check only — no API calls){RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}")

    results: dict[str, bool] = {}

    if args.connector:
        fn = CONNECTORS[args.connector]
        results[args.connector] = fn(config_only=args.config_only)
    else:
        for name, fn in CONNECTORS.items():
            results[name] = fn(config_only=args.config_only)

    # Summary
    print(f"\n{BOLD}{'=' * 60}{RESET}")
    print(f"{BOLD}  Summary{RESET}")
    print(f"{BOLD}{'=' * 60}{RESET}\n")

    for name, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")

    total_pass = sum(1 for v in results.values() if v)
    total = len(results)
    print(f"\n  {total_pass}/{total} connectors passed\n")

    return 0 if total_pass == total else 1


if __name__ == "__main__":
    sys.exit(main())
