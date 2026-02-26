#!/usr/bin/env python3
from __future__ import annotations

"""
Validate OAuth connector configuration for production readiness.

Checks all 6 OAuth connectors (Google Drive, Notion, Microsoft, Dropbox,
GitHub, Box) and reports configuration issues that would prevent a
successful production go-live.

Usage:
    python backend/scripts/validate_production_oauth.py
    # Or from backend directory:
    python scripts/validate_production_oauth.py
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path so we can import settings
script_dir = Path(__file__).resolve().parent
backend_dir = script_dir.parent
project_root = backend_dir.parent

# Try loading .env from project root
try:
    from dotenv import load_dotenv

    for env_path in [project_root / ".env", backend_dir / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            break
except ImportError:
    pass  # python-dotenv not installed, rely on actual env vars


# ---------------------------------------------------------------------------
# Connector definitions
# ---------------------------------------------------------------------------

CONNECTORS = {
    "Google Drive": {
        "priority": "CRITICAL",
        "backend_vars": {
            "GOOGLE_CLIENT_ID": {"required": True},
            "GOOGLE_CLIENT_SECRET": {"required": True, "secret": True},
            "GOOGLE_REDIRECT_URI": {"required": True, "is_uri": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_GOOGLE_CLIENT_ID": {"must_match": "GOOGLE_CLIENT_ID"},
            "NEXT_PUBLIC_GOOGLE_REDIRECT_URI": {"must_match": "GOOGLE_REDIRECT_URI"},
        },
        "notes": [
            "Test-mode refresh tokens expire after 7 days — publish app ASAP",
            "App must be verified by Google to remove 'unverified app' warning",
            "Scope needed: drive.readonly",
        ],
    },
    "Microsoft (OneDrive/SharePoint)": {
        "priority": "HIGH",
        "backend_vars": {
            "MICROSOFT_CLIENT_ID": {"required": True},
            "MICROSOFT_CLIENT_SECRET": {"required": True, "secret": True},
            "MICROSOFT_REDIRECT_URI": {"required": True, "is_uri": True},
            "MICROSOFT_TENANT_ID": {"required": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_MICROSOFT_CLIENT_ID": {"must_match": "MICROSOFT_CLIENT_ID"},
            "NEXT_PUBLIC_MICROSOFT_REDIRECT_URI": {"must_match": "MICROSOFT_REDIRECT_URI"},
            "NEXT_PUBLIC_MICROSOFT_TENANT_ID": {"must_match": "MICROSOFT_TENANT_ID"},
        },
        "notes": [
            "Publisher verification removes 'unverified' warning",
            "Enterprise tenants may need admin consent",
            "PKCE flow is used — ensure code_verifier logic works in production",
        ],
    },
    "Notion": {
        "priority": "HIGH",
        "backend_vars": {
            "NOTION_CLIENT_ID": {"required": True},
            "NOTION_CLIENT_SECRET": {"required": True, "secret": True},
            "NOTION_REDIRECT_URI": {"required": True, "is_uri": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_NOTION_CLIENT_ID": {"must_match": "NOTION_CLIENT_ID"},
            "NEXT_PUBLIC_NOTION_REDIRECT_URI": {"must_match": "NOTION_REDIRECT_URI"},
        },
        "notes": [
            "Must switch from Internal to Public integration for external users",
            "Public integrations get new client ID/secret after Notion approval",
            "Notion tokens are long-lived — no refresh token needed",
        ],
    },
    "Box": {
        "priority": "MEDIUM",
        "backend_vars": {
            "BOX_CLIENT_ID": {"required": True},
            "BOX_CLIENT_SECRET": {"required": True, "secret": True},
            "BOX_REDIRECT_URI": {"required": True, "is_uri": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_BOX_CLIENT_ID": {"must_match": "BOX_CLIENT_ID"},
        },
        "notes": [
            "Enterprise admin must authorize the app via Admin Console",
            "Box uses single-use refresh tokens — rotation must work correctly",
            "Access tokens expire after 60 minutes",
        ],
    },
    "Dropbox": {
        "priority": "LOW",
        "backend_vars": {
            "DROPBOX_CLIENT_ID": {"required": True},
            "DROPBOX_CLIENT_SECRET": {"required": True, "secret": True},
            "DROPBOX_REDIRECT_URI": {"required": True, "is_uri": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_DROPBOX_CLIENT_ID": {"must_match": "DROPBOX_CLIENT_ID"},
        },
        "notes": [
            "Development status supports up to 500 linked users",
            "Apply for production when approaching 500-user limit",
            "Team accounts use root_namespace_id for file access",
        ],
    },
    "GitHub": {
        "priority": "LOW",
        "backend_vars": {
            "GITHUB_CLIENT_ID": {"required": True},
            "GITHUB_CLIENT_SECRET": {"required": True, "secret": True},
            "GITHUB_REDIRECT_URI": {"required": True, "is_uri": True},
        },
        "frontend_vars": {
            "NEXT_PUBLIC_GITHUB_CLIENT_ID": {"must_match": "GITHUB_CLIENT_ID"},
        },
        "notes": [
            "GitHub has no test/production mode distinction",
            "Rate limit: 5,000 requests/hour per authenticated user",
            "Tokens have indefinite lifetime — no refresh needed",
        ],
    },
}


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def check_var_set(name: str) -> str | None:
    """Return the env var value or None."""
    val = os.environ.get(name, "").strip()
    return val if val else None


def is_production_uri(uri: str) -> bool:
    """Check if a redirect URI points to a production domain (not localhost)."""
    parsed = urlparse(uri)
    hostname = parsed.hostname or ""
    return (
        hostname not in ("localhost", "127.0.0.1", "0.0.0.0")
        and parsed.scheme == "https"
    )


def validate_connector(name: str, spec: dict) -> ValidationResult:
    result = ValidationResult()

    # Backend variables
    for var_name, rules in spec["backend_vars"].items():
        value = check_var_set(var_name)

        if rules.get("required") and not value:
            result.errors.append(f"  {var_name} is not set")
            continue

        if value:
            result.passed.append(f"  {var_name} is set")

            if rules.get("is_uri"):
                if not is_production_uri(value):
                    result.warnings.append(
                        f"  {var_name} = {value} — not a production URI (expected https://)"
                    )
                elif "/oauth/callback" not in value:
                    result.warnings.append(
                        f"  {var_name} = {value} — missing /oauth/callback path"
                    )
                else:
                    result.passed.append(f"  {var_name} points to production")

            if rules.get("secret") and value and len(value) < 10:
                result.warnings.append(
                    f"  {var_name} looks too short for a secret ({len(value)} chars)"
                )

    # Frontend variables
    for var_name, rules in spec.get("frontend_vars", {}).items():
        value = check_var_set(var_name)
        must_match = rules.get("must_match")

        if not value:
            result.warnings.append(
                f"  {var_name} is not set (frontend auto-derives from window.origin if missing)"
            )
        elif must_match:
            backend_val = check_var_set(must_match)
            if backend_val and value != backend_val:
                result.errors.append(
                    f"  {var_name} ({value}) does not match {must_match} ({backend_val})"
                )
            elif backend_val:
                result.passed.append(f"  {var_name} matches {must_match}")

    return result


def validate_global() -> ValidationResult:
    """Check global production settings."""
    result = ValidationResult()

    env = os.environ.get("ENVIRONMENT", "development")
    if env != "production":
        result.warnings.append(
            f"  ENVIRONMENT={env} — should be 'production' for go-live"
        )
    else:
        result.passed.append("  ENVIRONMENT=production")

    app_url = os.environ.get("APP_URL", "")
    if app_url and "localhost" not in app_url:
        result.passed.append(f"  APP_URL={app_url}")
    elif app_url:
        result.warnings.append(f"  APP_URL={app_url} — still points to localhost")

    origins = os.environ.get("ALLOWED_ORIGINS", "")
    if not origins:
        result.warnings.append(
            "  ALLOWED_ORIGINS is empty — backend will only allow configured frontend"
        )

    enc_key = check_var_set("CHUNK_ENCRYPTION_KEY")
    if not enc_key:
        result.errors.append(
            "  CHUNK_ENCRYPTION_KEY is not set — required for production"
        )
    else:
        result.passed.append("  CHUNK_ENCRYPTION_KEY is set")

    return result


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def main() -> int:
    print(f"\n{BOLD}{'=' * 70}{RESET}")
    print(f"{BOLD}  Axial — OAuth Production Readiness Validator{RESET}")
    print(f"{BOLD}{'=' * 70}{RESET}\n")

    total_errors = 0
    total_warnings = 0

    # Global checks
    print(f"{CYAN}{BOLD}[GLOBAL] Production Environment{RESET}")
    global_result = validate_global()
    total_errors += len(global_result.errors)
    total_warnings += len(global_result.warnings)

    for msg in global_result.errors:
        print(f"  {RED}FAIL{RESET} {msg}")
    for msg in global_result.warnings:
        print(f"  {YELLOW}WARN{RESET} {msg}")
    for msg in global_result.passed:
        print(f"  {GREEN}OK{RESET}   {msg}")
    print()

    # Per-connector checks (sorted by priority)
    sorted_connectors = sorted(
        CONNECTORS.items(), key=lambda x: PRIORITY_ORDER.get(x[1]["priority"], 99)
    )

    for name, spec in sorted_connectors:
        priority = spec["priority"]
        print(f"{CYAN}{BOLD}[{priority}] {name}{RESET}")

        result = validate_connector(name, spec)
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)

        for msg in result.errors:
            print(f"  {RED}FAIL{RESET} {msg}")
        for msg in result.warnings:
            print(f"  {YELLOW}WARN{RESET} {msg}")
        for msg in result.passed:
            print(f"  {GREEN}OK{RESET}   {msg}")

        # Show notes
        if spec.get("notes"):
            for note in spec["notes"]:
                print(f"  {BOLD}NOTE{RESET} {note}")

        print()

    # Summary
    print(f"{BOLD}{'=' * 70}{RESET}")
    if total_errors == 0 and total_warnings == 0:
        print(f"{GREEN}{BOLD}  ALL CHECKS PASSED — ready for production go-live{RESET}")
    elif total_errors == 0:
        print(
            f"{YELLOW}{BOLD}  {total_warnings} warning(s), 0 errors — review warnings before go-live{RESET}"
        )
    else:
        print(
            f"{RED}{BOLD}  {total_errors} error(s), {total_warnings} warning(s) — fix errors before go-live{RESET}"
        )
    print(f"{BOLD}{'=' * 70}{RESET}\n")

    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
