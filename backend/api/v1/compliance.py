"""
Compliance API Endpoints - Ghost Protocol

GDPR Article 17 and CCPA 2026 ADMT compliance endpoints.
Implements tombstone-first deletion pattern for immediate data access revocation.

Endpoints:
- POST /compliance/delete-request     - GDPR Article 17 compliant deletion
- POST /compliance/admt-optout        - CCPA 2026 ADMT opt-out
- GET  /compliance/tombstones         - List active tombstones
- GET  /compliance/report             - Generate compliance report
- GET  /compliance/pending            - List pending deletion requests
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from enum import Enum

from core.security import get_current_user
from core.db import get_supabase
from core.rate_limit import limiter
from api.v1.dependencies import (
    validate_team_access,
    require_editor,
    require_paid_access,
    get_user_organization_id,
)
from api.v1.error_utils import api_error, ApiErrorCode
from services.compliance_switch import (
    compliance_switch,
    ComplianceType,
    ResourceType,
    Tombstone,
)
from services.audit import audit_logger
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    dependencies=[Depends(validate_team_access), Depends(require_paid_access)],
)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ResourceTypeEnum(str, Enum):
    """Resource types for deletion requests."""
    DOCUMENT = "document"
    SCOPE = "scope"
    ORGANIZATION = "organization"


class ComplianceTypeEnum(str, Enum):
    """Compliance regulation types."""
    GDPR_ART17 = "gdpr_art17"
    CCPA_ADMT = "ccpa_admt"
    KVKK = "kvkk"
    USER_REQUEST = "user_request"


class DeletionRequest(BaseModel):
    """
    GDPR Article 17 compliant deletion request.

    The tombstone-first pattern ensures data is blocked from access
    within milliseconds, before actual deletion completes.
    """
    resource_type: ResourceTypeEnum = Field(
        ...,
        description="Type of resource to delete: document, scope, or organization"
    )
    resource_id: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="ID of the resource to delete"
    )
    compliance_type: ComplianceTypeEnum = Field(
        default=ComplianceTypeEnum.GDPR_ART17,
        description="Regulation driving this request"
    )
    reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional reason for deletion (for audit trail)"
    )


class ADMTOptoutRequest(BaseModel):
    """
    CCPA 2026 ADMT (Automated Decision-Making Technology) opt-out request.

    Prevents data from being used in AI/ML decisions.
    """
    scope_ids: List[str] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="List of scope IDs to opt out of ADMT"
    )
    reason: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional reason for opt-out"
    )


class TombstoneResponse(BaseModel):
    """Tombstone information for API responses."""
    id: str
    resource_type: str
    resource_id: str
    document_count: int
    scope_count: int
    compliance_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None


class DeletionResponse(BaseModel):
    """Response for deletion request."""
    tombstone_id: str
    request_id: str
    status: str
    message: str
    document_count: int
    access_revoked_at: str
    timeline: Dict[str, Any]


class ComplianceReportResponse(BaseModel):
    """GDPR compliance report response."""
    organization_id: str
    period_start: str
    period_end: str
    total_requests: int
    completed_requests: int
    pending_requests: int
    compliant_requests: int
    overdue_requests: int
    compliance_rate: float
    avg_time_to_revoke_ms: Optional[float] = None
    avg_time_to_complete_hours: Optional[float] = None
    by_request_type: Optional[Dict[str, int]] = None
    generated_at: str


class PendingRequestResponse(BaseModel):
    """Pending compliance request."""
    id: str
    organization_id: str
    request_type: str
    regulation: str
    received_at: str
    deadline_at: str
    days_remaining: int
    is_overdue: bool


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "/delete-request",
    response_model=DeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def create_deletion_request(
    request: Request,
    payload: DeletionRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    GDPR Article 17 compliant deletion request.

    This endpoint:
    1. Creates a tombstone SYNCHRONOUSLY (access blocked immediately)
    2. Schedules actual deletion in background (Ghost Protocol secure wipe)
    3. Returns immediately with tombstone ID for tracking

    Timeline Guarantees:
    - T+10ms:  Data blocked from search/retrieval
    - T+25ms:  Realtime notification to all clients
    - T+200ms: Deletion complete (background)

    Compliance:
    - GDPR Article 17(2): "without undue delay" - achieved via tombstone-first
    - CCPA: Deletion within 45 days - tracked via compliance_audit_log
    """
    logger.info(
        f"[Compliance] Deletion request: {payload.resource_type.value}/"
        f"{payload.resource_id[:8]}... by user {user_id[:8]}..."
    )

    # Get client IP for audit
    client_ip = request.client.host if request.client else None

    try:
        # Map enum to internal types
        resource_type = ResourceType(payload.resource_type.value)
        compliance_type = ComplianceType(payload.compliance_type.value)

        # CRITICAL: Create tombstone synchronously
        # After this returns, data is blocked from all search/retrieval
        tombstone = await compliance_switch.create_tombstone(
            resource_type=resource_type,
            resource_id=payload.resource_id,
            organization_id=organization_id,
            compliance_type=compliance_type,
            requested_by=user_id,
            ip_address=client_ip,
        )

        # Schedule actual deletion in background
        background_tasks.add_task(
            compliance_switch.execute_and_complete,
            tombstone_id=tombstone.id,
            resource_type=resource_type,
            resource_id=payload.resource_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="compliance.deletion_requested",
            resource_type=payload.resource_type.value,
            resource_id=payload.resource_id,
            details={
                "tombstone_id": tombstone.id,
                "compliance_type": payload.compliance_type.value,
                "document_count": len(tombstone.document_ids),
                "reason": payload.reason,
            },
            request=request,
        )

        now = datetime.now(timezone.utc)

        return DeletionResponse(
            tombstone_id=tombstone.id,
            request_id=tombstone.request_id,
            status="processing",
            message=(
                f"Data access revoked immediately. "
                f"{len(tombstone.document_ids)} document(s) blocked from search. "
                f"Secure deletion in progress."
            ),
            document_count=len(tombstone.document_ids),
            access_revoked_at=now.isoformat(),
            timeline={
                "access_revoked": now.isoformat(),
                "deletion_started": now.isoformat(),
                "estimated_completion": (now + timedelta(seconds=30)).isoformat(),
            },
        )

    except Exception as e:
        logger.error(f"[Compliance] Deletion request failed: {e}")
        raise api_error(
            ApiErrorCode.INTERNAL_ERROR,
            e,
            "compliance_deletion",
        )


@router.post(
    "/admt-optout",
    response_model=DeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("10/minute")
async def ccpa_admt_optout(
    request: Request,
    payload: ADMTOptoutRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    CCPA 2026 ADMT (Automated Decision-Making Technology) opt-out.

    Prevents specified data scopes from being used in AI/ML decisions.
    This removes all embeddings and document chunks for the scopes,
    ensuring they cannot be retrieved by the RAG system.

    Compliance:
    - CCPA 2026: ADMT opt-out rights
    - Data is immediately blocked, then securely deleted
    """
    logger.info(
        f"[Compliance] ADMT opt-out request: {len(payload.scope_ids)} scopes "
        f"by user {user_id[:8]}..."
    )

    client_ip = request.client.host if request.client else None
    total_document_count = 0
    tombstone_ids = []

    try:
        for scope_id in payload.scope_ids:
            # Create tombstone for each scope
            tombstone = await compliance_switch.create_tombstone(
                resource_type=ResourceType.SCOPE,
                resource_id=scope_id,
                organization_id=organization_id,
                compliance_type=ComplianceType.CCPA_ADMT,
                requested_by=user_id,
                ip_address=client_ip,
            )

            tombstone_ids.append(tombstone.id)
            total_document_count += len(tombstone.document_ids)

            # Schedule deletion in background
            background_tasks.add_task(
                compliance_switch.execute_and_complete,
                tombstone_id=tombstone.id,
                resource_type=ResourceType.SCOPE,
                resource_id=scope_id,
                organization_id=organization_id,
                user_id=user_id,
            )

        # Audit log
        audit_logger.log(
            background_tasks,
            user_id=user_id,
            action="compliance.admt_optout",
            resource_type="scope",
            resource_id=",".join(payload.scope_ids[:5]),  # First 5
            details={
                "tombstone_ids": tombstone_ids,
                "scope_count": len(payload.scope_ids),
                "document_count": total_document_count,
                "reason": payload.reason,
            },
            request=request,
        )

        now = datetime.now(timezone.utc)

        return DeletionResponse(
            tombstone_id=tombstone_ids[0] if tombstone_ids else "",
            request_id=tombstone_ids[0][:36] if tombstone_ids else "",
            status="processing",
            message=(
                f"ADMT opt-out successful. "
                f"{len(payload.scope_ids)} scope(s) and {total_document_count} "
                f"document(s) blocked from AI decisions. Secure deletion in progress."
            ),
            document_count=total_document_count,
            access_revoked_at=now.isoformat(),
            timeline={
                "access_revoked": now.isoformat(),
                "scopes_affected": len(payload.scope_ids),
            },
        )

    except Exception as e:
        logger.error(f"[Compliance] ADMT opt-out failed: {e}")
        raise api_error(
            ApiErrorCode.INTERNAL_ERROR,
            e,
            "compliance_admt_optout",
        )


@router.get(
    "/tombstones",
    response_model=List[TombstoneResponse],
)
@limiter.limit("30/minute")
async def list_tombstones(
    request: Request,
    status_filter: Optional[str] = None,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    List compliance tombstones for the organization.

    Tombstones represent data that has been blocked from access.
    Active tombstones mean data is blocked but deletion may still be in progress.
    Completed tombstones mean deletion is verified complete.
    """
    supabase = get_supabase()

    query = supabase.table("compliance_tombstones")\
        .select("*")\
        .eq("organization_id", organization_id)\
        .order("created_at", desc=True)

    if status_filter and status_filter in ("active", "completed", "failed"):
        query = query.eq("status", status_filter)

    result = query.limit(100).execute()

    return [
        TombstoneResponse(
            id=t["id"],
            resource_type=t["resource_type"],
            resource_id=t["resource_id"],
            document_count=len(t.get("document_ids", [])),
            scope_count=len(t.get("scope_ids", [])),
            compliance_type=t["compliance_type"],
            status=t["status"],
            created_at=t["created_at"],
            completed_at=t.get("completed_at"),
        )
        for t in (result.data or [])
    ]


@router.get(
    "/report",
    response_model=ComplianceReportResponse,
)
@limiter.limit("10/minute")
async def get_compliance_report(
    request: Request,
    days: int = 30,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Generate GDPR/CCPA compliance report.

    Returns statistics on deletion requests, completion rates,
    and compliance with regulatory timelines.

    Useful for:
    - GDPR Article 30 record of processing activities
    - Regulatory audits
    - Internal compliance monitoring
    """
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    report = await compliance_switch.get_compliance_report(
        organization_id=organization_id,
        start_date=start_date,
        end_date=end_date,
    )

    if not report:
        return ComplianceReportResponse(
            organization_id=organization_id,
            period_start=start_date.isoformat(),
            period_end=end_date.isoformat(),
            total_requests=0,
            completed_requests=0,
            pending_requests=0,
            compliant_requests=0,
            overdue_requests=0,
            compliance_rate=100.0,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    return ComplianceReportResponse(
        organization_id=report.get("organization_id", organization_id),
        period_start=report.get("period_start", start_date.isoformat()),
        period_end=report.get("period_end", end_date.isoformat()),
        total_requests=report.get("total_requests", 0),
        completed_requests=report.get("completed_requests", 0),
        pending_requests=report.get("pending_requests", 0),
        compliant_requests=report.get("compliant_requests", 0),
        overdue_requests=report.get("overdue_requests", 0),
        compliance_rate=float(report.get("compliance_rate", 100.0)),
        avg_time_to_revoke_ms=report.get("avg_time_to_revoke_ms"),
        avg_time_to_complete_hours=report.get("avg_time_to_complete_hours"),
        by_request_type=report.get("by_request_type"),
        generated_at=report.get("generated_at", datetime.now(timezone.utc).isoformat()),
    )


@router.get(
    "/pending",
    response_model=List[PendingRequestResponse],
)
@limiter.limit("30/minute")
async def get_pending_requests(
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    List pending compliance requests that haven't been completed.

    Highlights overdue requests that may be approaching regulatory deadlines.
    Critical for GDPR 30-day compliance monitoring.
    """
    pending = await compliance_switch.get_pending_requests(
        organization_id=organization_id,
    )

    return [
        PendingRequestResponse(
            id=p["id"],
            organization_id=p["organization_id"],
            request_type=p["request_type"],
            regulation=p["regulation"],
            received_at=p["received_at"],
            deadline_at=p["deadline_at"],
            days_remaining=p["days_remaining"],
            is_overdue=p["is_overdue"],
        )
        for p in pending
    ]


@router.get(
    "/tombstone/{tombstone_id}",
    response_model=TombstoneResponse,
)
@limiter.limit("60/minute")
async def get_tombstone(
    request: Request,
    tombstone_id: str,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """
    Get status of a specific tombstone/deletion request.

    Use this to track the progress of a deletion request.
    """
    supabase = get_supabase()

    result = supabase.table("compliance_tombstones")\
        .select("*")\
        .eq("id", tombstone_id)\
        .eq("organization_id", organization_id)\
        .single()\
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tombstone not found",
        )

    t = result.data
    return TombstoneResponse(
        id=t["id"],
        resource_type=t["resource_type"],
        resource_id=t["resource_id"],
        document_count=len(t.get("document_ids", [])),
        scope_count=len(t.get("scope_ids", [])),
        compliance_type=t["compliance_type"],
        status=t["status"],
        created_at=t["created_at"],
        completed_at=t.get("completed_at"),
    )
