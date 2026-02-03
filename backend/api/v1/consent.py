"""
KVKK 2026 Consent Management API Endpoints

Granular consent controls for AI learning and external agent access.
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


class ComplianceReport(BaseModel):
    """KVKK compliance report."""
    organization_id: str
    report_generated_at: str
    organization_consent: dict
    scope_overrides: int
    document_overrides: int
    total_documents: int
    compliance_status: str


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

    result = supabase.table("organization_consents")\
        .select("*")\
        .eq("organization_id", organization_id)\
        .maybe_single()\
        .execute()

    if not result.data:
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
        result = await manager.set_org_consent(
            organization_id=organization_id,
            consent_type=consent_type,
            allowed=payload.allowed,
            user_id=user_id,
            ip_address=ip_address,
        )

        return {
            "status": "success",
            "consent_type": payload.consent_type,
            "allowed": payload.allowed,
        }

    except Exception as e:
        logger.error(f"[Consent] Update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


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
    Generate KVKK compliance report.

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
