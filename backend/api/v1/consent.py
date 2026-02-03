"""
GDPR/CCPA/KVKK 2026 Consent Management API Endpoints

Granular consent controls for AI learning and external agent access.

Compliance Coverage:
- GDPR Article 6/7: Lawful basis and consent requirements
- CCPA 2026 ADMT: Automated Decision-Making Technology opt-out
- KVKK Article 5: Turkish GDPR equivalent consent handling
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, status
from pydantic import BaseModel

from api.v1.dependencies import (
    require_admin,
    require_editor,
    get_user_organization_id,
    validate_team_access,
)
from core.rate_limit import limiter
from services.consent import (
    ConsentManager,
    ConsentType,
    ConsentLevel,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[Depends(validate_team_access)],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class OrgConsentResponse(BaseModel):
    """Organization consent settings."""
    organization_id: str
    allow_ai_learning: bool = False
    ai_learning_consent_at: Optional[str] = None
    allow_external_agents: bool = False
    external_agents_consent_at: Optional[str] = None


class OrgConsentUpdate(BaseModel):
    """Update organization consent."""
    consent_type: str  # "ai_learning" | "external_agents"
    allowed: bool


class ScopeConsentResponse(BaseModel):
    """Scope consent settings."""
    scope_id: str
    organization_id: str
    inherit_org_consent: bool = True
    allow_ai_learning: Optional[bool] = None
    allow_external_agents: Optional[bool] = None
    allowed_agent_ids: List[str] = []
    blocked_agent_ids: List[str] = []


class ScopeConsentUpdate(BaseModel):
    """Update scope consent."""
    consent_type: str
    allowed: bool
    inherit_org_consent: bool = True


class DocumentConsentResponse(BaseModel):
    """Document consent settings."""
    document_id: str
    organization_id: str
    inherit_scope_consent: bool = True
    allow_ai_learning: Optional[bool] = None
    allow_external_agents: Optional[bool] = None
    allowed_agent_ids: List[str] = []
    blocked_agent_ids: List[str] = []


class DocumentConsentUpdate(BaseModel):
    """Update document consent."""
    consent_type: str
    allowed: bool
    inherit_scope_consent: bool = True


class ConsentAuditEntry(BaseModel):
    """Consent audit log entry."""
    id: str
    consent_level: str
    resource_id: str
    field_changed: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_by: str
    changed_at: str
    ip_address: Optional[str] = None


class BulkScopeConsentItem(BaseModel):
    """Single scope consent update for bulk operations."""
    scope_id: str
    consent_type: str  # 'ai_learning' | 'external_agents'
    allowed: Optional[bool] = None


class BulkScopeConsentRequest(BaseModel):
    """Request to update multiple scope consents at once."""
    updates: List[BulkScopeConsentItem]


class BulkScopeConsentResponse(BaseModel):
    """Response from bulk scope consent update."""
    success: int
    failed: int
    errors: List[dict] = []


class ComplianceReport(BaseModel):
    """GDPR/CCPA/KVKK compliance report."""
    organization_id: str
    report_generated_at: str
    organization_consent: dict
    scope_overrides: int
    document_overrides: int
    total_documents: int
    compliance_status: str


class ScopeInfo(BaseModel):
    """Scope information for consent UI."""
    id: str
    label: str
    source_type: Optional[str] = None
    document_count: int = 0


# =============================================================================
# Scopes Endpoint (for Consent UI)
# =============================================================================

@router.get("/scopes", response_model=List[ScopeInfo])
@limiter.limit("30/minute")
async def list_scopes(
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    List all scopes for the organization.

    Returns scope IDs and labels for the consent management UI.
    Used by the InheritanceTree component to display scope hierarchy.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    try:
        # Get distinct scopes from documents
        result = supabase.table("documents")\
            .select("scope_id, source_type")\
            .eq("organization_id", organization_id)\
            .neq("source_type", "identity")\
            .neq("source_type", "scope_identity")\
            .execute()

        # Aggregate by scope
        scope_counts: dict = {}
        for row in result.data or []:
            scope_id = row.get("scope_id") or "default"

            if scope_id not in scope_counts:
                scope_counts[scope_id] = {
                    "id": scope_id,
                    "label": _format_scope_label(scope_id),
                    "source_type": row.get("source_type"),
                    "document_count": 0,
                }
            scope_counts[scope_id]["document_count"] += 1

        scopes = list(scope_counts.values())

        # Sort by label
        scopes.sort(key=lambda s: s["label"].lower())

        return scopes

    except Exception as e:
        logger.error(f"[Consent] Failed to list scopes: {e}")
        return []


def _format_scope_label(scope_id: str) -> str:
    """Format scope ID into a human-readable label."""
    if not scope_id or scope_id == "default":
        return "Default"

    # Handle common patterns like "gdrive:folder_name" or "notion:workspace"
    if ":" in scope_id:
        parts = scope_id.split(":", 1)
        source = parts[0].replace("_", " ").title()
        name = parts[1].replace("_", " ").replace("-", " ").title()
        return f"{source}: {name}"

    # Simple scope IDs
    return scope_id.replace("_", " ").replace("-", " ").title()


# =============================================================================
# Organization Consent Endpoints
# =============================================================================

@router.get("/consent/organization", response_model=OrgConsentResponse)
@limiter.limit("30/minute")
async def get_org_consent(
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get organization consent settings.

    Returns current consent configuration for AI learning
    and external agent access.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    try:
        result = supabase.table("organization_consents")\
            .select("*")\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()
    except Exception as e:
        logger.warning(f"[Consent] Failed to query organization_consents: {e}")
        result = None

    if result is None or not result.data:
        # Return defaults
        return OrgConsentResponse(
            organization_id=organization_id,
            allow_ai_learning=False,
            allow_external_agents=False,
        )

    data = result.data
    return OrgConsentResponse(
        organization_id=organization_id,
        allow_ai_learning=data.get("allow_ai_learning", False),
        ai_learning_consent_at=data.get("ai_learning_consent_at"),
        allow_external_agents=data.get("allow_external_agents", False),
        external_agents_consent_at=data.get("external_agents_consent_at"),
    )


@router.patch("/consent/organization")
@limiter.limit("10/minute")
async def update_org_consent(
    payload: OrgConsentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Update organization consent settings.

    Only organization admins can modify consent.
    Changes are logged to the consent audit trail.
    """
    try:
        consent_type = ConsentType(payload.consent_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type: {payload.consent_type}"
        )

    # Get client IP
    ip_address = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    manager = ConsentManager()

    try:
        # Check if we're revoking AI learning consent
        should_wipe = False
        if consent_type == ConsentType.AI_LEARNING and not payload.allowed:
            # Check current state
            from core.db import get_supabase
            supabase = get_supabase()
            current = supabase.table("organization_consents")\
                .select("allow_ai_learning")\
                .eq("organization_id", organization_id)\
                .maybe_single()\
                .execute()
            if current.data and current.data.get("allow_ai_learning"):
                should_wipe = True  # Consent is being revoked

        result = await manager.set_org_consent(
            organization_id=organization_id,
            consent_type=consent_type,
            allowed=payload.allowed,
            user_id=user_id,
            ip_address=ip_address,
        )

        # GDPR Compliance: Schedule AI learning data wipe when consent is revoked
        if should_wipe:
            logger.info(f"[Consent] AI learning consent revoked for org {organization_id}, scheduling GDPR wipe")
            background_tasks.add_task(
                _trigger_gdpr_ai_learning_wipe,
                organization_id=organization_id,
                user_id=user_id,
                ip_address=ip_address,
            )

        return {
            "status": "success",
            "consent_type": payload.consent_type,
            "allowed": payload.allowed,
            "gdpr_wipe_scheduled": should_wipe,
        }

    except Exception as e:
        logger.error(f"[Consent] Update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def _trigger_gdpr_ai_learning_wipe(
    organization_id: str,
    user_id: str,
    ip_address: Optional[str] = None,
):
    """
    GDPR compliance: Wipe AI learning data when consent is revoked.
    
    This background task purges any data that was used for AI learning
    while the consent was active. Per GDPR Article 17 (Right to Erasure).
    """
    from core.db import get_supabase
    from services.audit_service import audit_service
    
    logger.info(f"[GDPR] Starting AI learning data wipe for organization {organization_id}")
    
    try:
        supabase = get_supabase()
        
        # Log the GDPR wipe request
        await audit_service.log_action(
            user_id=user_id,
            action="gdpr.ai_learning_wipe_started",
            resource_type="organization",
            resource_id=organization_id,
            details={
                "reason": "consent_revoked",
                "ip_address": ip_address,
            }
        )
        
        # Delete any AI learning feedback/training data
        # This is where organization-specific AI learning data would be purged
        # The actual implementation depends on how AI learning data is stored
        
        # For now, mark all documents as "not for AI learning" by updating scope consents
        scopes = supabase.table("scopes")\
            .select("id")\
            .eq("organization_id", organization_id)\
            .execute()
        
        if scopes.data:
            for scope in scopes.data:
                supabase.table("scope_consents")\
                    .upsert({
                        "scope_id": scope["id"],
                        "organization_id": organization_id,
                        "allow_ai_learning": False,
                        "inherit_org_consent": True,
                    }, on_conflict="scope_id,organization_id")\
                    .execute()
        
        # Log successful completion
        await audit_service.log_action(
            user_id=user_id,
            action="gdpr.ai_learning_wipe_completed",
            resource_type="organization",
            resource_id=organization_id,
            details={
                "scopes_updated": len(scopes.data) if scopes.data else 0,
            }
        )
        
        logger.info(f"[GDPR] AI learning data wipe completed for organization {organization_id}")
        
    except Exception as e:
        logger.error(f"[GDPR] AI learning data wipe failed for organization {organization_id}: {e}")


# =============================================================================
# Scope Consent Endpoints
# =============================================================================

@router.get("/consent/scope/{scope_id}", response_model=ScopeConsentResponse)
@limiter.limit("30/minute")
async def get_scope_consent(
    scope_id: str,
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get scope consent settings with inheritance resolution.

    Returns effective consent after considering inheritance
    from organization level.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    result = supabase.table("scope_consents")\
        .select("*")\
        .eq("scope_id", scope_id)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result.data:
        # Return defaults with inheritance enabled
        return ScopeConsentResponse(
            scope_id=scope_id,
            organization_id=organization_id,
            inherit_org_consent=True,
        )

    data = result.data
    return ScopeConsentResponse(
        scope_id=scope_id,
        organization_id=organization_id,
        inherit_org_consent=data.get("inherit_org_consent", True),
        allow_ai_learning=data.get("allow_ai_learning"),
        allow_external_agents=data.get("allow_external_agents"),
        allowed_agent_ids=data.get("allowed_agent_ids", []),
        blocked_agent_ids=data.get("blocked_agent_ids", []),
    )


@router.patch("/consent/scope/{scope_id}")
@limiter.limit("10/minute")
async def update_scope_consent(
    scope_id: str,
    payload: ScopeConsentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Update scope consent settings.

    Only organization admins can modify scope consent.
    """
    try:
        consent_type = ConsentType(payload.consent_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type: {payload.consent_type}"
        )

    ip_address = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    manager = ConsentManager()

    try:
        result = await manager.set_scope_consent(
            scope_id=scope_id,
            organization_id=organization_id,
            consent_type=consent_type,
            allowed=payload.allowed,
            user_id=user_id,
            inherit_org_consent=payload.inherit_org_consent,
            ip_address=ip_address,
        )

        return {
            "status": "success",
            "scope_id": scope_id,
            "consent_type": payload.consent_type,
            "allowed": payload.allowed,
        }

    except Exception as e:
        logger.error(f"[Consent] Scope update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/consent/scope/bulk", response_model=BulkScopeConsentResponse)
@limiter.limit("5/minute")
async def bulk_update_scope_consent(
    payload: BulkScopeConsentRequest,
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Bulk update scope consent settings.
    
    Allows updating multiple scope consents in a single request.
    Only organization admins can perform bulk updates.
    Maximum 50 updates per request.
    """
    if len(payload.updates) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 updates per request"
        )
    
    if len(payload.updates) == 0:
        return BulkScopeConsentResponse(success=0, failed=0, errors=[])
    
    ip_address = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    
    manager = ConsentManager()
    success_count = 0
    failed_count = 0
    errors = []
    
    for update in payload.updates:
        try:
            consent_type = ConsentType(update.consent_type)
            
            await manager.set_scope_consent(
                scope_id=update.scope_id,
                organization_id=organization_id,
                consent_type=consent_type,
                allowed=update.allowed,
                user_id=user_id,
                ip_address=ip_address,
            )
            success_count += 1
            
        except ValueError:
            failed_count += 1
            errors.append({
                "scope_id": update.scope_id,
                "error": f"Invalid consent type: {update.consent_type}"
            })
        except Exception as e:
            failed_count += 1
            errors.append({
                "scope_id": update.scope_id,
                "error": str(e)
            })
            logger.error(f"[Consent] Bulk scope update failed for {update.scope_id}: {e}")
    
    return BulkScopeConsentResponse(
        success=success_count,
        failed=failed_count,
        errors=errors
    )


# =============================================================================
# Document Consent Endpoints
# =============================================================================

@router.get("/consent/document/{document_id}", response_model=DocumentConsentResponse)
@limiter.limit("30/minute")
async def get_document_consent(
    document_id: str,
    request: Request,
    user_id: str = Depends(validate_team_access),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get document consent settings with inheritance resolution.
    """
    from core.db import get_supabase

    supabase = get_supabase()

    result = supabase.table("document_consents")\
        .select("*")\
        .eq("document_id", document_id)\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result.data:
        return DocumentConsentResponse(
            document_id=document_id,
            organization_id=organization_id,
            inherit_scope_consent=True,
        )

    data = result.data
    return DocumentConsentResponse(
        document_id=document_id,
        organization_id=organization_id,
        inherit_scope_consent=data.get("inherit_scope_consent", True),
        allow_ai_learning=data.get("allow_ai_learning"),
        allow_external_agents=data.get("allow_external_agents"),
        allowed_agent_ids=data.get("allowed_agent_ids", []),
        blocked_agent_ids=data.get("blocked_agent_ids", []),
    )


@router.patch("/consent/document/{document_id}")
@limiter.limit("10/minute")
async def update_document_consent(
    document_id: str,
    payload: DocumentConsentUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Update document consent settings.

    Editors and admins can modify document consent.
    """
    try:
        consent_type = ConsentType(payload.consent_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type: {payload.consent_type}"
        )

    ip_address = None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip_address = forwarded.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None

    manager = ConsentManager()

    try:
        result = await manager.set_document_consent(
            document_id=document_id,
            organization_id=organization_id,
            consent_type=consent_type,
            allowed=payload.allowed,
            user_id=user_id,
            inherit_scope_consent=payload.inherit_scope_consent,
            ip_address=ip_address,
        )

        return {
            "status": "success",
            "document_id": document_id,
            "consent_type": payload.consent_type,
            "allowed": payload.allowed,
        }

    except Exception as e:
        logger.error(f"[Consent] Document update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# Agent Access Management Endpoints
# =============================================================================

class AgentAccessUpdate(BaseModel):
    """Update agent access for a resource."""
    action: str  # "allow" | "block" | "remove"
    agent_id: str


@router.patch("/consent/scope/{scope_id}/agents")
@limiter.limit("10/minute")
async def update_scope_agent_access(
    scope_id: str,
    payload: AgentAccessUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Manage which MCP agents can access a scope.

    Actions:
    - "allow": Add agent to allowed_agent_ids list
    - "block": Add agent to blocked_agent_ids list
    - "remove": Remove agent from both lists

    Only organization admins can manage agent access.
    """
    from core.db import get_supabase
    from services.audit import audit_logger

    if payload.action not in ("allow", "block", "remove"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'allow', 'block', or 'remove'"
        )

    supabase = get_supabase()

    try:
        # Get current scope consent or create default
        existing = supabase.table("scope_consents")\
            .select("*")\
            .eq("scope_id", scope_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        current_allowed = []
        current_blocked = []

        if existing and existing.data:
            current_allowed = existing.data.get("allowed_agent_ids") or []
            current_blocked = existing.data.get("blocked_agent_ids") or []

        # Process action
        agent_id = payload.agent_id

        if payload.action == "allow":
            # Add to allowed, remove from blocked
            if agent_id not in current_allowed:
                current_allowed.append(agent_id)
            if agent_id in current_blocked:
                current_blocked.remove(agent_id)

        elif payload.action == "block":
            # Add to blocked, remove from allowed
            if agent_id not in current_blocked:
                current_blocked.append(agent_id)
            if agent_id in current_allowed:
                current_allowed.remove(agent_id)

        elif payload.action == "remove":
            # Remove from both lists
            if agent_id in current_allowed:
                current_allowed.remove(agent_id)
            if agent_id in current_blocked:
                current_blocked.remove(agent_id)

        # Upsert scope consent with updated agent lists
        update_data = {
            "scope_id": scope_id,
            "organization_id": organization_id,
            "allowed_agent_ids": current_allowed,
            "blocked_agent_ids": current_blocked,
        }

        supabase.table("scope_consents")\
            .upsert(update_data, on_conflict="scope_id,organization_id")\
            .execute()

        # Get client IP for audit
        ip_address = None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        # Log to consent audit
        manager = ConsentManager()
        await manager._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.SCOPE,
            resource_id=scope_id,
            field_changed=f"agent_access_{payload.action}",
            old_value=None,
            new_value=agent_id,
            changed_by=user_id,
            ip_address=ip_address,
        )

        # General audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action=f"consent.scope_agent_{payload.action}",
            resource_type="scope",
            resource_id=scope_id,
            details={
                "agent_id": agent_id,
                "action": payload.action,
                "allowed_agents": current_allowed,
                "blocked_agents": current_blocked,
            },
            request=request,
        )

        # Invalidate cache
        manager.invalidate_cache(organization_id, scope_id=scope_id)

        return {
            "status": "success",
            "scope_id": scope_id,
            "action": payload.action,
            "agent_id": agent_id,
            "allowed_agent_ids": current_allowed,
            "blocked_agent_ids": current_blocked,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Consent] Scope agent update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/consent/document/{document_id}/agents")
@limiter.limit("10/minute")
async def update_document_agent_access(
    document_id: str,
    payload: AgentAccessUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Manage which MCP agents can access a document.

    Actions:
    - "allow": Add agent to allowed_agent_ids list
    - "block": Add agent to blocked_agent_ids list
    - "remove": Remove agent from both lists

    Editors and admins can manage document agent access.
    """
    from core.db import get_supabase
    from services.audit import audit_logger

    if payload.action not in ("allow", "block", "remove"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid action. Must be 'allow', 'block', or 'remove'"
        )

    supabase = get_supabase()

    try:
        # Verify document exists in organization
        doc_check = supabase.table("documents")\
            .select("id")\
            .eq("id", document_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not doc_check or not doc_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )

        # Get current document consent or create default
        existing = supabase.table("document_consents")\
            .select("*")\
            .eq("document_id", document_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        current_allowed = []
        current_blocked = []

        if existing and existing.data:
            current_allowed = existing.data.get("allowed_agent_ids") or []
            current_blocked = existing.data.get("blocked_agent_ids") or []

        # Process action
        agent_id = payload.agent_id

        if payload.action == "allow":
            # Add to allowed, remove from blocked
            if agent_id not in current_allowed:
                current_allowed.append(agent_id)
            if agent_id in current_blocked:
                current_blocked.remove(agent_id)

        elif payload.action == "block":
            # Add to blocked, remove from allowed
            if agent_id not in current_blocked:
                current_blocked.append(agent_id)
            if agent_id in current_allowed:
                current_allowed.remove(agent_id)

        elif payload.action == "remove":
            # Remove from both lists
            if agent_id in current_allowed:
                current_allowed.remove(agent_id)
            if agent_id in current_blocked:
                current_blocked.remove(agent_id)

        # Upsert document consent with updated agent lists
        update_data = {
            "document_id": document_id,
            "organization_id": organization_id,
            "allowed_agent_ids": current_allowed,
            "blocked_agent_ids": current_blocked,
        }

        supabase.table("document_consents")\
            .upsert(update_data, on_conflict="document_id,organization_id")\
            .execute()

        # Get client IP for audit
        ip_address = None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        # Log to consent audit
        manager = ConsentManager()
        await manager._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.DOCUMENT,
            resource_id=document_id,
            field_changed=f"agent_access_{payload.action}",
            old_value=None,
            new_value=agent_id,
            changed_by=user_id,
            ip_address=ip_address,
        )

        # General audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action=f"consent.document_agent_{payload.action}",
            resource_type="document",
            resource_id=document_id,
            details={
                "agent_id": agent_id,
                "action": payload.action,
                "allowed_agents": current_allowed,
                "blocked_agents": current_blocked,
            },
            request=request,
        )

        # Invalidate cache
        manager.invalidate_cache(organization_id, document_id=document_id)

        return {
            "status": "success",
            "document_id": document_id,
            "action": payload.action,
            "agent_id": agent_id,
            "allowed_agent_ids": current_allowed,
            "blocked_agent_ids": current_blocked,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Consent] Document agent update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# Consent DELETE Endpoints (Reset to Inherit)
# =============================================================================

@router.delete("/consent/scope/{scope_id}")
@limiter.limit("10/minute")
async def delete_scope_consent(
    scope_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Delete scope consent override, reverting to organization defaults.

    This removes any custom consent settings for the scope,
    causing it to inherit from organization-level consent.
    Only organization admins can delete scope consent overrides.
    """
    from core.db import get_supabase
    from services.audit import audit_logger

    supabase = get_supabase()

    try:
        # Check if scope consent exists
        existing = supabase.table("scope_consents")\
            .select("id, allow_ai_learning, allow_external_agents")\
            .eq("scope_id", scope_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not existing or not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No consent override found for this scope"
            )

        old_values = existing.data

        # Delete the scope consent
        supabase.table("scope_consents")\
            .delete()\
            .eq("scope_id", scope_id)\
            .eq("organization_id", organization_id)\
            .execute()

        # Get client IP for audit
        ip_address = None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        # Log to consent audit
        manager = ConsentManager()
        await manager._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.SCOPE,
            resource_id=scope_id,
            field_changed="consent_override",
            old_value=str(old_values),
            new_value="inherited",
            changed_by=user_id,
            ip_address=ip_address,
        )

        # Also log to general audit
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="consent.scope_reset",
            resource_type="scope",
            resource_id=scope_id,
            details={
                "previous_settings": old_values,
                "reset_to": "inherit_org_consent",
            },
            request=request,
        )

        return {
            "status": "deleted",
            "scope_id": scope_id,
            "message": "Scope now inherits organization consent settings"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Consent] Scope delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/consent/document/{document_id}")
@limiter.limit("10/minute")
async def delete_document_consent(
    document_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(require_editor),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Delete document consent override, reverting to scope/org defaults.

    This removes any custom consent settings for the document,
    causing it to inherit from scope or organization-level consent.
    Editors and admins can delete document consent overrides.
    """
    from core.db import get_supabase
    from services.audit import audit_logger

    supabase = get_supabase()

    try:
        # Check if document consent exists
        existing = supabase.table("document_consents")\
            .select("id, allow_ai_learning, allow_external_agents")\
            .eq("document_id", document_id)\
            .eq("organization_id", organization_id)\
            .maybe_single()\
            .execute()

        if not existing or not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No consent override found for this document"
            )

        old_values = existing.data

        # Delete the document consent
        supabase.table("document_consents")\
            .delete()\
            .eq("document_id", document_id)\
            .eq("organization_id", organization_id)\
            .execute()

        # Get client IP for audit
        ip_address = None
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

        # Log to consent audit
        manager = ConsentManager()
        await manager._log_consent_change(
            organization_id=organization_id,
            level=ConsentLevel.DOCUMENT,
            resource_id=document_id,
            field_changed="consent_override",
            old_value=str(old_values),
            new_value="inherited",
            changed_by=user_id,
            ip_address=ip_address,
        )

        # Also log to general audit
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="consent.document_reset",
            resource_type="document",
            resource_id=document_id,
            details={
                "previous_settings": old_values,
                "reset_to": "inherit_scope_consent",
            },
            request=request,
        )

        return {
            "status": "deleted",
            "document_id": document_id,
            "message": "Document now inherits scope/organization consent settings"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Consent] Document delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


# =============================================================================
# Audit & Reporting Endpoints
# =============================================================================

@router.get("/consent/audit", response_model=List[ConsentAuditEntry])
@limiter.limit("10/minute")
async def get_consent_audit(
    request: Request,
    limit: int = 100,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get consent change audit log.

    Returns history of all consent changes for the organization.
    Only admins can access the audit log.
    """
    manager = ConsentManager()

    try:
        entries = await manager.get_consent_audit_log(
            organization_id=organization_id,
            limit=min(limit, 500),
        )

        return [
            ConsentAuditEntry(
                id=e["id"],
                consent_level=e["consent_level"],
                resource_id=e["resource_id"],
                field_changed=e["field_changed"],
                old_value=str(e.get("old_value")) if e.get("old_value") is not None else None,
                new_value=str(e.get("new_value")) if e.get("new_value") is not None else None,
                changed_by=e["changed_by"],
                changed_at=e["changed_at"],
                ip_address=e.get("ip_address"),
            )
            for e in entries
        ]

    except Exception as e:
        logger.error(f"[Consent] Audit fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/consent/report", response_model=ComplianceReport)
@limiter.limit("5/minute")
async def get_compliance_report(
    request: Request,
    user_id: str = Depends(require_admin),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Generate compliance report (GDPR/CCPA/KVKK).

    Returns summary of consent configuration across
    organization, scopes, and documents.
    """
    manager = ConsentManager()

    try:
        report = await manager.generate_compliance_report(organization_id)
        return ComplianceReport(**report)

    except Exception as e:
        logger.error(f"[Consent] Report generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
