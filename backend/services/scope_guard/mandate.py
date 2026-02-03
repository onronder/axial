"""
Cryptographic Mandate Generation and Verification

Mandates are signed tokens that authorize specific actions.
They prevent replay attacks and ensure approval integrity.
"""

import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Mandate:
    """
    Cryptographic mandate for action authorization.

    A mandate binds together:
    - The action to be performed
    - The resource it operates on
    - The organization context
    - A unique nonce (prevents replay)
    - Expiration time
    - HMAC signature for integrity

    Attributes:
        action: The action type (e.g., "delete_scope")
        resource_id: ID of the resource to operate on
        organization_id: Organization context
        nonce: Unique 32-byte random value
        created_at: When the mandate was created
        expires_at: When the mandate expires
        signature: HMAC-SHA256 signature
    """
    action: str
    resource_id: str
    organization_id: str
    nonce: str
    created_at: str
    expires_at: str
    signature: str

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "action": self.action,
            "resource_id": self.resource_id,
            "organization_id": self.organization_id,
            "nonce": self.nonce,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Mandate':
        """Create from dictionary."""
        return cls(
            action=data["action"],
            resource_id=data["resource_id"],
            organization_id=data["organization_id"],
            nonce=data["nonce"],
            created_at=data["created_at"],
            expires_at=data["expires_at"],
            signature=data["signature"],
        )


class MandateGenerator:
    """
    Generator and verifier for cryptographic mandates.

    Uses HMAC-SHA256 with the organization's encryption key
    to create tamper-proof authorization tokens.
    """

    def __init__(self):
        self._signing_key: Optional[bytes] = None

    def _get_signing_key(self) -> bytes:
        """
        Get the signing key from configuration.

        Uses CHUNK_ENCRYPTION_KEY as the base for deriving
        the mandate signing key.
        """
        if self._signing_key is None:
            from core.config import settings

            if not settings.CHUNK_ENCRYPTION_KEY:
                raise RuntimeError(
                    "CHUNK_ENCRYPTION_KEY must be set for mandate signing"
                )

            # Derive signing key from encryption key
            # Use HKDF-like derivation for key separation
            base_key = settings.CHUNK_ENCRYPTION_KEY.encode()
            self._signing_key = hashlib.sha256(
                b"scope_guard_mandate:" + base_key
            ).digest()

        return self._signing_key

    def create(
        self,
        action: str,
        resource_id: str,
        organization_id: str,
        ttl_minutes: int = 30,
    ) -> Mandate:
        """
        Create a new cryptographic mandate.

        Args:
            action: Action type (e.g., "delete_scope")
            resource_id: Resource to operate on
            organization_id: Organization context
            ttl_minutes: Time-to-live in minutes

        Returns:
            Signed Mandate object
        """
        # Generate unique nonce
        nonce = secrets.token_hex(32)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=ttl_minutes)

        # Create mandate data
        mandate_data = {
            "action": action,
            "resource_id": resource_id,
            "organization_id": organization_id,
            "nonce": nonce,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }

        # Sign the mandate
        signature = self._compute_signature(mandate_data)

        logger.debug(
            f"[Mandate] Created for {action} on {resource_id[:8]}... "
            f"expires {expires_at.isoformat()}"
        )

        return Mandate(
            **mandate_data,
            signature=signature,
        )

    def verify(
        self,
        mandate: Mandate,
        expected_signature: str,
    ) -> bool:
        """
        Verify a mandate's signature.

        Args:
            mandate: The mandate to verify
            expected_signature: The signature to check against

        Returns:
            True if signature is valid, False otherwise
        """
        # Recompute signature
        mandate_data = {
            "action": mandate.action,
            "resource_id": mandate.resource_id,
            "organization_id": mandate.organization_id,
            "nonce": mandate.nonce,
            "created_at": mandate.created_at,
            "expires_at": mandate.expires_at,
        }

        computed = self._compute_signature(mandate_data)

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(computed, expected_signature)

    def verify_not_expired(self, mandate: Mandate) -> bool:
        """
        Check if a mandate has not expired.

        Args:
            mandate: The mandate to check

        Returns:
            True if mandate is still valid, False if expired
        """
        expires_at = datetime.fromisoformat(
            mandate.expires_at.replace("Z", "+00:00")
        )
        return expires_at > datetime.now(timezone.utc)

    def _compute_signature(self, mandate_data: dict) -> str:
        """
        Compute HMAC-SHA256 signature for mandate data.

        Args:
            mandate_data: Dictionary of mandate fields (without signature)

        Returns:
            Hex-encoded signature
        """
        signing_key = self._get_signing_key()

        # Canonical JSON serialization (sorted keys)
        message = json.dumps(mandate_data, sort_keys=True).encode()

        # HMAC-SHA256
        signature = hmac.new(
            signing_key,
            message,
            hashlib.sha256
        ).hexdigest()

        return signature


class MandateVerificationError(Exception):
    """Raised when mandate verification fails."""
    pass


def verify_mandate_or_raise(
    mandate_nonce: str,
    mandate_signature: str,
    expected_action: str,
    expected_resource_id: str,
    organization_id: str,
) -> None:
    """
    Verify a mandate or raise an error.

    Convenience function for use in API endpoints.

    Args:
        mandate_nonce: The mandate nonce
        mandate_signature: The mandate signature
        expected_action: Expected action type
        expected_resource_id: Expected resource ID
        organization_id: Organization context

    Raises:
        MandateVerificationError: If verification fails
    """
    from core.db import get_supabase

    supabase = get_supabase()

    # Look up approval by nonce
    result = supabase.table("action_approvals")\
        .select("*")\
        .eq("mandate_nonce", mandate_nonce)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result.data:
        raise MandateVerificationError("Mandate not found")

    approval = result.data

    # Verify signature
    if approval["mandate_signature"] != mandate_signature:
        raise MandateVerificationError("Invalid mandate signature")

    # Verify action matches
    if approval["action_type"] != expected_action:
        raise MandateVerificationError("Mandate action mismatch")

    # Verify resource matches
    if approval["resource_id"] != expected_resource_id:
        raise MandateVerificationError("Mandate resource mismatch")

    # Verify approved
    if approval["status"] != "approved":
        raise MandateVerificationError(
            f"Mandate not approved (status: {approval['status']})"
        )

    # Verify not expired
    expires_at = datetime.fromisoformat(
        approval["expires_at"].replace("Z", "+00:00")
    )
    if expires_at < datetime.now(timezone.utc):
        raise MandateVerificationError("Mandate has expired")

    # Verify not already executed
    if approval["executed_at"]:
        raise MandateVerificationError("Mandate already executed")
