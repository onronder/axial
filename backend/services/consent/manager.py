"""
Consent Manager Service

Handles consent CRUD operations and policy evaluation.
Implements hierarchical consent with inheritance.
"""

import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConsentType(str, Enum):
    """Types of consent that can be granted."""
    AI_LEARNING = "ai_learning"  # Allow data to be used for AI training
    EXTERNAL_AGENTS = "external_agents"  # Allow external AI agents (MCP) to access


class ConsentLevel(str, Enum):
    """Levels at which consent can be configured."""
    ORGANIZATION = "organization"
    SCOPE = "scope"
    DOCUMENT = "document"


@dataclass
class ConsentDecision:
    """
    Result of consent evaluation.

    Attributes:
        allowed: Whether access is allowed
        level: The consent level that determined the decision
        consent_type: The type of consent evaluated
        inherited: Whether the decision was inherited from a parent level
        agent_specific: Whether this is agent-specific consent
    """
    allowed: bool
    level: ConsentLevel
    consent_type: ConsentType
    inherited: bool = False
    agent_specific: bool = False


class ConsentManager:
    """
    Consent management with hierarchical evaluation.

    Consent hierarchy (most specific wins):
    1. Document consent (if not inheriting from scope)
    2. Scope consent (if not inheriting from organization)
    3. Organization consent (always present)

    Usage:
        manager = ConsentManager()

        # Check if MCP agent can access a document
        decision = await manager.check_consent(
            organization_id="org-123",
            consent_type=ConsentType.EXTERNAL_AGENTS,
            document_id="doc-456",
            agent_id="agent-789",
        )
        if decision.allowed:
            # Proceed with access
        else:
            # Block access
    """

    # Cache TTL in seconds
    CACHE_TTL = 60

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_times: Dict[str, float] = {}

    async def check_consent(
        self,
        organization_id: str,
        consent_type: ConsentType,
        document_id: Optional[str] = None,
        scope_id: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> ConsentDecision:
        """
        Evaluate consent for a specific access request.

        Checks consent at document, scope, and organization levels,
        respecting inheritance settings.

        Args:
            organization_id: Organization context
            consent_type: Type of consent to check
            document_id: Optional document ID
            scope_id: Optional scope ID
            agent_id: Optional agent ID for agent-specific consent

        Returns:
            ConsentDecision with the evaluation result
        """
        # Check document level first (most specific)
        if document_id:
            doc_consent = await self._get_document_consent(document_id, organization_id)
            if doc_consent and not doc_consent.get("inherit_scope_consent", True):
                return self._evaluate_consent(
                    doc_consent,
                    consent_type,
                    agent_id,
                    ConsentLevel.DOCUMENT,
                )

        # Check scope level
        if scope_id:
            scope_consent = await self._get_scope_consent(scope_id, organization_id)
            if scope_consent and not scope_consent.get("inherit_org_consent", True):
                return self._evaluate_consent(
                    scope_consent,
                    consent_type,
                    agent_id,
                    ConsentLevel.SCOPE,
                )

        # Fall back to organization level
        org_consent = await self._get_org_consent(organization_id)
        return self._evaluate_consent(
            org_consent,
            consent_type,
            agent_id,
            ConsentLevel.ORGANIZATION,
            inherited=True,
        )

    def _evaluate_consent(
        self,
        consent_data: Optional[Dict[str, Any]],
        consent_type: ConsentType,
        agent_id: Optional[str],
        level: ConsentLevel,
        inherited: bool = False,
    ) -> ConsentDecision:
        """
        Evaluate consent based on consent data.

        Args:
            consent_data: Consent configuration from database
            consent_type: Type of consent to evaluate
            agent_id: Optional agent ID for agent-specific checks
            level: The consent level being evaluated
            inherited: Whether this is inherited consent

        Returns:
            ConsentDecision
        """
        if not consent_data:
            # No consent data = default deny
            return ConsentDecision(
                allowed=False,
                level=level,
                consent_type=consent_type,
                inherited=inherited,
            )

        # Check type-specific consent
        if consent_type == ConsentType.AI_LEARNING:
            allowed = consent_data.get("allow_ai_learning", False)
        elif consent_type == ConsentType.EXTERNAL_AGENTS:
            allowed = consent_data.get("allow_external_agents", False)
        else:
            allowed = False

        # Check agent-specific allowlist/blocklist
        agent_specific = False
        if agent_id and consent_type == ConsentType.EXTERNAL_AGENTS:
            blocked_agents = consent_data.get("blocked_agent_ids", [])
            allowed_agents = consent_data.get("allowed_agent_ids", [])

            if agent_id in blocked_agents:
                allowed = False
                agent_specific = True
            elif allowed_agents and agent_id not in allowed_agents:
                # If allowlist exists and agent not in it, deny
                allowed = False
                agent_specific = True
            elif agent_id in allowed_agents:
                allowed = True
                agent_specific = True

        return ConsentDecision(
            allowed=allowed,
            level=level,
            consent_type=consent_type,
            inherited=inherited,
            agent_specific=agent_specific,
        )

    async def _get_org_consent(self, organization_id: str) -> Optional[Dict[str, Any]]:
        """Get organization-level consent settings."""
        cache_key = f"org:{organization_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        from core.db import get_supabase
        supabase = get_supabase()

        result = supabase.table("organization_consents")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        data = result.data
        self._set_cached(cache_key, data)
        return data

    async def _get_scope_consent(
        self,
        scope_id: str,
        organization_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get scope-level consent settings."""
        cache_key = f"scope:{organization_id}:{scope_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        from core.db import get_supabase
        supabase = get_supabase()

        result = supabase.table("scope_consents")\
            .select("*")\
            .eq("scope_id", scope_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        data = result.data
        self._set_cached(cache_key, data)
        return data

    async def _get_document_consent(
        self,
        document_id: str,
        organization_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get document-level consent settings."""
        cache_key = f"doc:{organization_id}:{document_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        from core.db import get_supabase
        supabase = get_supabase()

        result = supabase.table("document_consents")\
            .select("*")\
            .eq("document_id", document_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        data = result.data
        self._set_cached(cache_key, data)
        return data

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None
        cache_time = self._cache_times.get(key, 0)
        if datetime.now(timezone.utc).timestamp() - cache_time > self.CACHE_TTL:
            del self._cache[key]
            del self._cache_times[key]
            return None
        return self._cache[key]

    def _set_cached(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value
        self._cache_times[key] = datetime.now(timezone.utc).timestamp()

    def invalidate_cache(
        self,
        organization_id: str,
        scope_id: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> None:
        """Invalidate cached consent data."""
        if document_id:
            key = f"doc:{organization_id}:{document_id}"
            self._cache.pop(key, None)
            self._cache_times.pop(key, None)
        elif scope_id:
            key = f"scope:{organization_id}:{scope_id}"
            self._cache.pop(key, None)
            self._cache_times.pop(key, None)
        else:
            key = f"org:{organization_id}"
            self._cache.pop(key, None)
            self._cache_times.pop(key, None)

    # =========================================================================
    # Consent Setting Methods
    # =========================================================================

    async def set_org_consent(
        self,
        organization_id: str,
        consent_type: ConsentType,
        allowed: bool,
        user_id: str,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set organization-level consent.

        Args:
            organization_id: Organization ID
            consent_type: Type of consent to set
            allowed: Whether to allow
            user_id: User making the change
            ip_address: Client IP for audit

        Returns:
            Updated consent settings
        """
        from core.db import get_supabase
        supabase = get_supabase()

        now = datetime.now(timezone.utc)

        # Build update data
        if consent_type == ConsentType.AI_LEARNING:
            update_data = {
                "allow_ai_learning": allowed,
                "ai_learning_consent_at": now.isoformat() if allowed else None,
                "ai_learning_consented_by": user_id if allowed else None,
            }
        else:
            update_data = {
                "allow_external_agents": allowed,
                "external_agents_consent_at": now.isoformat() if allowed else None,
                "external_agents_consented_by": user_id if allowed else None,
            }

        # Upsert
        result = supabase.table("organization_consents")\
            .upsert({
                "organization_id": organization_id,
                **update_data,
            })\
            .execute()

        # Audit log
        await self._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.ORGANIZATION,
            resource_id=organization_id,
            field_changed=consent_type.value,
            old_value=None,  # Would need to fetch old value
            new_value=allowed,
            changed_by=user_id,
            ip_address=ip_address,
        )

        # Invalidate cache
        self.invalidate_cache(organization_id)

        return result.data[0] if result.data else {}

    async def set_scope_consent(
        self,
        scope_id: str,
        organization_id: str,
        consent_type: ConsentType,
        allowed: bool,
        user_id: str,
        inherit_org_consent: bool = True,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set scope-level consent.

        Args:
            scope_id: Scope ID
            organization_id: Organization ID
            consent_type: Type of consent
            allowed: Whether to allow
            user_id: User making the change
            inherit_org_consent: Whether to inherit from org
            ip_address: Client IP for audit

        Returns:
            Updated consent settings
        """
        from core.db import get_supabase
        supabase = get_supabase()

        now = datetime.now(timezone.utc)

        # Build update data
        update_data = {
            "scope_id": scope_id,
            "organization_id": organization_id,
            "inherit_org_consent": inherit_org_consent,
            "consented_by": user_id,
            "consented_at": now.isoformat(),
        }

        if consent_type == ConsentType.AI_LEARNING:
            update_data["allow_ai_learning"] = allowed
        else:
            update_data["allow_external_agents"] = allowed

        # Upsert
        result = supabase.table("scope_consents")\
            .upsert(update_data, on_conflict="scope_id,organization_id")\
            .execute()

        # Audit log
        await self._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.SCOPE,
            resource_id=scope_id,
            field_changed=consent_type.value,
            old_value=None,
            new_value=allowed,
            changed_by=user_id,
            ip_address=ip_address,
        )

        # Invalidate cache
        self.invalidate_cache(organization_id, scope_id=scope_id)

        return result.data[0] if result.data else {}

    async def set_document_consent(
        self,
        document_id: str,
        organization_id: str,
        consent_type: ConsentType,
        allowed: bool,
        user_id: str,
        inherit_scope_consent: bool = True,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Set document-level consent.

        Args:
            document_id: Document ID
            organization_id: Organization ID
            consent_type: Type of consent
            allowed: Whether to allow
            user_id: User making the change
            inherit_scope_consent: Whether to inherit from scope
            ip_address: Client IP for audit

        Returns:
            Updated consent settings
        """
        from core.db import get_supabase
        supabase = get_supabase()

        # Build update data
        update_data = {
            "document_id": document_id,
            "organization_id": organization_id,
            "inherit_scope_consent": inherit_scope_consent,
        }

        if consent_type == ConsentType.AI_LEARNING:
            update_data["allow_ai_learning"] = allowed
        else:
            update_data["allow_external_agents"] = allowed

        # Upsert
        result = supabase.table("document_consents")\
            .upsert(update_data, on_conflict="document_id,organization_id")\
            .execute()

        # Audit log
        await self._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.DOCUMENT,
            resource_id=document_id,
            field_changed=consent_type.value,
            old_value=None,
            new_value=allowed,
            changed_by=user_id,
            ip_address=ip_address,
        )

        # Invalidate cache
        self.invalidate_cache(organization_id, document_id=document_id)

        return result.data[0] if result.data else {}

    async def _log_consent_change(
        self,
        organization_id: str,
        level: ConsentLevel,
        resource_id: str,
        field_changed: str,
        old_value: Any,
        new_value: Any,
        changed_by: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log consent change to audit table."""
        from core.db import get_supabase

        try:
            supabase = get_supabase()
            supabase.table("consent_audit_log").insert({
                "organization_id": organization_id,
                "consent_level": level.value,
                "resource_id": resource_id,
                "field_changed": field_changed,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }).execute()
        except Exception as e:
            logger.error(f"[Consent] Failed to log change: {e}")

    async def get_consent_audit_log(
        self,
        organization_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get consent change audit log for organization."""
        from core.db import get_supabase

        supabase = get_supabase()
        result = supabase.table("consent_audit_log")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .order("changed_at", desc=True)\
            .limit(limit)\
            .execute()

        return result.data or []

    async def generate_compliance_report(
        self,
        organization_id: str,
    ) -> Dict[str, Any]:
        """
        Generate compliance report (GDPR/CCPA/KVKK) for organization.

        Returns summary of consent settings across all levels.
        """
        from core.db import get_supabase

        supabase = get_supabase()

        # Get org consent
        org_consent = await self._get_org_consent(organization_id)

        # Get scope consents
        scope_result = supabase.table("scope_consents")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .execute()

        # Get document consents
        doc_result = supabase.table("document_consents")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .execute()

        # Count documents
        doc_count_result = supabase.table("documents")\
            .select("id", count="exact")\
            .eq("organization_id", organization_id)\
            .execute()

        return {
            "organization_id": organization_id,
            "report_generated_at": datetime.now(timezone.utc).isoformat(),
            "organization_consent": {
                "ai_learning": org_consent.get("allow_ai_learning", False) if org_consent else False,
                "external_agents": org_consent.get("allow_external_agents", False) if org_consent else False,
            },
            "scope_overrides": len(scope_result.data or []),
            "document_overrides": len(doc_result.data or []),
            "total_documents": doc_count_result.count or 0,
            "compliance_status": "compliant" if org_consent else "needs_review",
        }


# Singleton instance
consent_manager = ConsentManager()
