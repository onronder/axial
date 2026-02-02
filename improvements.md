# AxioHub Improvements & Enhancement Plan

> **Document Version:** 1.0
> **Created:** February 2026
> **Status:** Implementation Ready
> **Target:** Enterprise-Grade Production System

---

## Executive Summary

This document provides a comprehensive, codebase-aligned implementation plan for enhancing AxioHub from its current production-ready state to an enterprise-grade platform. The plan is organized by priority and includes detailed specifications, code examples, and implementation timelines.

### Key Findings from Architecture Review

| Category | Status | Notes |
|----------|--------|-------|
| **GDPR Anonymization UI** | ✅ Already Implemented | Full UI in GeneralSettings.tsx (lines 282-503) |
| **Audit Logs Admin UI** | ✅ Already Implemented | Full page at /dashboard/settings/audit-logs |
| **Web Crawl Cancel** | ✅ Already Implemented | Full UI in URLCrawlerInput.tsx (lines 183-262) |
| **Invoice Download** | ⚠️ Minor Enhancement | Backend exists, frontend needs download button |
| **Repository Pattern** | 🔄 Recommended | Improves testability and maintainability |
| **API Versioning** | 🔄 Recommended | Backward compatibility for v2+ |
| **Rate Limiting** | 🔄 Recommended | Plan-based dynamic limits |
| **Distributed Tracing** | 🔄 Recommended | OpenTelemetry integration |

---

## Table of Contents

1. [Priority 1: Minor Gaps](#priority-1-minor-gaps)
2. [Priority 2: Architectural Enhancements](#priority-2-architectural-enhancements)
3. [Priority 3: Nice-to-Have Features](#priority-3-nice-to-have-features)
4. [Implementation Timeline](#implementation-timeline)
5. [Risk Assessment](#risk-assessment)

---

## Priority 1: Minor Gaps

### 1.1 Invoice Download Enhancement

**Current State:** Backend endpoint exists, frontend displays `invoice_url` from API but lacks explicit download button.

**Backend Endpoint (Already Exists):**
```
GET /api/v1/billing/invoices/{order_id}/download
Rate Limit: 20/minute
Authentication: validate_team_access
```

**Response:**
```json
{
  "url": "https://polar.sh/invoices/inv-xxx.pdf"
}
// OR
{
  "status": "generating",
  "message": "Invoice is being generated..."
}
```

**Frontend Enhancement Required:**

**File:** `/frontend-new/components/settings/BillingSettings.tsx`

**Add State:**
```typescript
const [downloadingId, setDownloadingId] = useState<string | null>(null);
```

**Add Handler:**
```typescript
const handleDownloadInvoice = async (orderId: string) => {
  try {
    setDownloadingId(orderId);
    const response = await api.get(`/billing/invoices/${orderId}/download`);

    if (response.data?.url) {
      window.open(response.data.url, "_blank", "noopener,noreferrer");
      toast({ title: "Opening invoice...", variant: "default" });
    } else if (response.data?.status === "generating") {
      toast({
        title: "Invoice generating",
        description: "Please try again in a few seconds.",
        variant: "default"
      });
    }
  } catch (error) {
    toast({
      title: "Download failed",
      description: "Could not download invoice.",
      variant: "destructive"
    });
  } finally {
    setDownloadingId(null);
  }
};
```

**Update Invoice Row (around line 524):**
```typescript
<Button
  variant="ghost"
  size="sm"
  onClick={() => handleDownloadInvoice(invoice.id)}
  disabled={downloadingId === invoice.id}
  className="gap-2"
>
  {downloadingId === invoice.id ? (
    <Spinner className="h-4 w-4 animate-spin" />
  ) : (
    <>
      <Download className="h-4 w-4" />
      Download
    </>
  )}
</Button>
```

**Import Required:**
```typescript
import { Download } from "lucide-react";
```

**Effort:** 1-2 hours
**Risk:** Low
**Testing:** Manual verification + existing BillingSettings.test.tsx patterns

---

### 1.2 Already Implemented Features (Verification Complete)

#### GDPR Anonymization UI ✅

**Location:** `/frontend-new/components/settings/GeneralSettings.tsx` (lines 282-503)

**Features Implemented:**
- Amber/warning color scheme for privacy context
- Two-state dialog (form + success display)
- Confirmation input requiring "ANONYMIZE"
- Reason dropdown (4 options)
- Detailed results breakdown with status indicators
- Toast notifications for success/error

**Backend Endpoint:** `POST /settings/profile/me/anonymize`

**No action required.**

#### Audit Logs Admin UI ✅

**Location:** `/frontend-new/app/dashboard/settings/audit-logs/page.tsx`

**Features Implemented:**
- Table display with 12+ action types
- Icon and color mapping per action
- Date range filtering (1d, 7d, 30d, 90d, all-time)
- Action type filtering
- Resource type filtering
- Client-side search
- CSV export
- Pagination
- Stats dashboard (total, success, failed, GDPR)

**No action required.**

#### Web Crawl Cancel ✅

**Location:** `/frontend-new/components/data-sources/URLCrawlerInput.tsx` (lines 183-262)

**Features Implemented:**
- Cancel button with destructive styling
- Loading state during cancellation
- Toast notifications
- Progress context unregistration
- State persistence across navigation

**Backend Endpoint:** `DELETE /integrations/web/crawl/{config_id}`

**No action required.**

---

## Priority 2: Architectural Enhancements

### 2.1 Repository Pattern Implementation

**Purpose:** Improve testability, maintainability, and enable database abstraction.

**Current State:**
- Services directly call `get_supabase()` and access tables via fluent API
- Query logic scattered across 22+ service files
- Difficult to mock for unit testing
- No centralized data access patterns

**Proposed Architecture:**
```
API Layer (FastAPI routes)
    ↓
Service Layer (Business logic)
    ↓
Repository Layer (Data access abstraction)  ← NEW
    ↓
Supabase Client (Database driver)
```

#### Directory Structure

```
backend/
├── core/
│   └── repositories/
│       ├── __init__.py           # Factory + dependency injection
│       ├── base.py               # Abstract Repository[T] interface
│       ├── exceptions.py         # Repository-specific exceptions
│       ├── team.py               # TeamRepository interface
│       ├── subscription.py       # SubscriptionRepository interface
│       ├── user.py               # UserProfileRepository interface
│       ├── feedback.py           # FeedbackRepository interface
│       ├── document.py           # DocumentRepository interface
│       └── impl/
│           ├── supabase_team.py
│           ├── supabase_subscription.py
│           ├── supabase_user.py
│           ├── supabase_feedback.py
│           └── supabase_document.py
```

#### Base Repository Interface

```python
# core/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar('T')

class Repository(ABC, Generic[T]):
    """Abstract base repository for all data access."""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by primary key."""
        pass

    @abstractmethod
    async def list(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """List entities with optional filters."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity and return with ID."""
        pass

    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> Optional[T]:
        """Update entity and return updated version."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity, return True if successful."""
        pass
```

#### Team Repository Example

```python
# core/repositories/team.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class TeamEntity:
    """Domain model for Team."""
    id: str
    name: str
    owner_id: str
    slug: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class TeamMemberEntity:
    """Domain model for TeamMember."""
    id: str
    team_id: str
    email: str
    role: str  # owner, admin, editor, viewer
    status: str  # active, pending, removed
    member_user_id: Optional[str] = None
    name: Optional[str] = None
    joined_at: Optional[datetime] = None

class TeamRepository(Repository[TeamEntity]):
    """Specialized repository for team data access."""

    @abstractmethod
    async def get_by_owner(self, owner_id: str) -> Optional[TeamEntity]:
        """Get team owned by specific user."""
        pass

    @abstractmethod
    async def get_effective_plan(self, user_id: str) -> str:
        """Get effective plan for user (uses RPC for efficiency)."""
        pass

    @abstractmethod
    async def get_members(
        self,
        team_id: str,
        status: Optional[str] = None
    ) -> List[TeamMemberEntity]:
        """Get team members with optional status filter."""
        pass

    @abstractmethod
    async def add_member(
        self,
        team_id: str,
        email: str,
        role: str
    ) -> TeamMemberEntity:
        """Add member to team."""
        pass

    @abstractmethod
    async def get_user_team(self, user_id: str) -> Optional[TeamEntity]:
        """Get user's team via membership."""
        pass
```

#### Supabase Implementation

```python
# core/repositories/impl/supabase_team.py
from typing import Optional, List
from core.db import get_supabase
from core.repositories.team import TeamRepository, TeamEntity, TeamMemberEntity
from core.resilience import is_retryable_error
import logging

logger = logging.getLogger(__name__)

class SupabaseTeamRepository(TeamRepository):
    """Supabase implementation of TeamRepository."""

    def __init__(self, supabase=None):
        self._supabase = supabase

    @property
    def client(self):
        if self._supabase is None:
            self._supabase = get_supabase()
        return self._supabase

    async def get_by_id(self, team_id: str) -> Optional[TeamEntity]:
        try:
            response = self.client.table("teams").select(
                "id, name, slug, owner_id, created_at, updated_at"
            ).eq("id", team_id).single().execute()

            return self._map_to_entity(response.data) if response.data else None
        except Exception as e:
            logger.error(f"[TeamRepository] get_by_id failed: {e}")
            return None

    async def get_effective_plan(self, user_id: str) -> str:
        """Uses RPC for efficient plan lookup."""
        try:
            response = self.client.rpc(
                "get_effective_plan",
                {"p_user_id": user_id}
            ).execute()

            if response.data:
                return str(response.data)
        except Exception as e:
            logger.warning(f"[TeamRepository] RPC failed, using fallback: {e}")

        # Fallback to sequential queries
        return await self._get_effective_plan_fallback(user_id)

    async def _get_effective_plan_fallback(self, user_id: str) -> str:
        """Fallback when RPC unavailable."""
        # 1. Get team membership
        member = self.client.table("team_members").select(
            "team_id"
        ).eq("member_user_id", user_id).neq("status", "removed").limit(1).execute()

        if not member.data:
            return "free"

        team_id = member.data[0]["team_id"]

        # 2. Get team owner
        team = self.client.table("teams").select(
            "owner_id"
        ).eq("id", team_id).single().execute()

        if not team.data:
            return "free"

        owner_id = team.data["owner_id"]

        # 3. Get owner's subscription
        sub = self.client.table("subscriptions").select(
            "plan_type, status"
        ).eq("team_id", team_id).limit(1).execute()

        if sub.data and sub.data[0].get("status") == "active":
            return sub.data[0].get("plan_type", "free")

        return "free"

    def _map_to_entity(self, data: dict) -> TeamEntity:
        from datetime import datetime
        return TeamEntity(
            id=data["id"],
            name=data["name"],
            owner_id=data["owner_id"],
            slug=data.get("slug"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None
        )
```

#### Dependency Injection

```python
# core/repositories/__init__.py
from typing import Type, Dict
from core.repositories.team import TeamRepository
from core.repositories.impl.supabase_team import SupabaseTeamRepository

class RepositoryFactory:
    """Factory for creating repository instances."""

    _implementations: Dict[Type, Type] = {
        TeamRepository: SupabaseTeamRepository,
        # Add more as implemented
    }

    @classmethod
    def create(cls, interface: Type) -> object:
        impl_class = cls._implementations.get(interface)
        if impl_class is None:
            raise ValueError(f"No implementation for {interface}")
        return impl_class()

    @classmethod
    def register(cls, interface: Type, implementation: Type):
        """Register custom implementation (for testing)."""
        cls._implementations[interface] = implementation

# FastAPI dependency
def get_team_repository() -> TeamRepository:
    return RepositoryFactory.create(TeamRepository)
```

#### Usage in API Routes

```python
# api/v1/team.py
from fastapi import Depends
from core.repositories import get_team_repository
from core.repositories.team import TeamRepository

@router.get("/team")
async def get_team(
    current_user: str = Depends(get_current_user),
    team_repo: TeamRepository = Depends(get_team_repository)
):
    team = await team_repo.get_user_team(current_user)
    if not team:
        raise HTTPException(404, "Team not found")
    return team
```

#### Migration Strategy

**Phase 1 (Week 1-2):** Create interfaces and Supabase implementations
**Phase 2 (Week 3-4):** Refactor services to use repositories (parallel with existing)
**Phase 3 (Week 5):** Testing, validation, cleanup

**Effort:** 3-4 weeks
**Risk:** Low (non-breaking, parallel implementation)

---

### 2.2 API Versioning Strategy

**Purpose:** Enable backward compatibility for future API versions.

**Current State:** Single version at `/api/v1/`

**Proposed Strategy:** URL-based versioning with deprecation support

#### Directory Structure

```
backend/
├── api/
│   ├── v1/                    # Current (maintained)
│   │   ├── __init__.py
│   │   ├── chat.py
│   │   └── ...
│   ├── v2/                    # Future version
│   │   ├── __init__.py
│   │   └── ...
│   └── common/                # Shared utilities
│       ├── __init__.py
│       ├── pagination.py
│       └── responses.py
```

#### Version Router Configuration

```python
# main.py
from api.v1 import router as v1_router
# from api.v2 import router as v2_router  # Future

app.include_router(v1_router, prefix="/api/v1")
# app.include_router(v2_router, prefix="/api/v2")  # Future
```

#### Deprecation Headers Middleware

```python
# core/versioning.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

DEPRECATION_SCHEDULE = {
    "/api/v1/legacy-endpoint": {
        "deprecated_at": "2026-03-01",
        "sunset_at": "2026-06-01",
        "replacement": "/api/v2/new-endpoint"
    }
}

class VersioningMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        path = request.url.path
        if path in DEPRECATION_SCHEDULE:
            info = DEPRECATION_SCHEDULE[path]
            response.headers["Deprecation"] = info["deprecated_at"]
            response.headers["Sunset"] = info["sunset_at"]
            response.headers["Link"] = f'<{info["replacement"]}>; rel="successor-version"'

        return response
```

#### Version Negotiation (Optional)

```python
# For Accept header-based versioning
def get_api_version(request: Request) -> str:
    accept = request.headers.get("Accept", "")
    if "application/vnd.axiohub.v2+json" in accept:
        return "v2"
    return "v1"
```

**Effort:** 1-2 weeks
**Risk:** Low

---

### 2.3 Feature-Specific Rate Limits

**Purpose:** Plan-based dynamic rate limiting with Redis backend.

**Current State:**
- IP-based rate limiting via SlowAPI
- Static limits per endpoint
- In-memory storage (lost on restart)

**Proposed Enhancement:**

#### Plan-Based Rate Limit Tiers

```python
# core/rate_limits.py
PLAN_RATE_LIMITS = {
    "free": {
        "chat": "10/minute",
        "search": "5/minute",
        "documents_list": "20/minute",
        "documents_download": "2/minute",
        "ingest": "2/minute",
        "team_actions": "5/minute",
        "daily_total": 100,
    },
    "starter": {
        "chat": "50/minute",
        "search": "20/minute",
        "documents_list": "60/minute",
        "documents_download": "5/minute",
        "ingest": "10/minute",
        "team_actions": "20/minute",
        "daily_total": 2000,
    },
    "pro": {
        "chat": "100/minute",
        "search": "50/minute",
        "documents_list": "100/minute",
        "documents_download": "20/minute",
        "ingest": "50/minute",
        "team_actions": "50/minute",
        "daily_total": 10000,
    },
    "enterprise_small": {
        "chat": "200/minute",
        "search": "100/minute",
        "documents_list": "200/minute",
        "documents_download": "50/minute",
        "ingest": "100/minute",
        "team_actions": "100/minute",
        "daily_total": 50000,
    },
    "enterprise_medium": {
        "chat": "500/minute",
        "search": "250/minute",
        "documents_list": "500/minute",
        "documents_download": "100/minute",
        "ingest": "250/minute",
        "team_actions": "250/minute",
        "daily_total": 150000,
    },
    "enterprise_large": {
        "chat": "1000/minute",
        "search": "500/minute",
        "documents_list": "1000/minute",
        "documents_download": "200/minute",
        "ingest": "500/minute",
        "team_actions": "500/minute",
        "daily_total": 500000,
    },
}
```

#### Redis Rate Limiter

```python
# core/redis_rate_limiter.py
import redis
import time
import uuid
from typing import Tuple, Dict, Any

class RedisRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
        feature: str = "default"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Sliding window rate limiting.

        Returns: (is_allowed, metadata)
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = f"rl:sliding:{feature}:{key}"

        # Remove expired entries
        self.redis.zremrangebyscore(redis_key, 0, window_start)

        # Count current window
        current_count = self.redis.zcard(redis_key)

        if current_count >= limit:
            oldest = self.redis.zrange(redis_key, 0, 0, withscores=True)
            retry_after = oldest[0][1] + window_seconds - now if oldest else window_seconds

            return False, {
                "current_count": current_count,
                "remaining": 0,
                "retry_after": max(1, int(retry_after) + 1)
            }

        # Add current request
        self.redis.zadd(redis_key, {str(uuid.uuid4()): now})
        self.redis.expire(redis_key, window_seconds + 10)

        return True, {
            "current_count": current_count + 1,
            "remaining": limit - current_count - 1,
            "retry_after": 0
        }

    async def get_plan_limits(self, user_id: str) -> dict:
        """Fetch and cache user's plan rate limits."""
        cache_key = f"plan:cache:{user_id}"
        plan = self.redis.get(cache_key)

        if not plan:
            from services.team_service import team_service
            plan = await team_service.get_effective_plan(user_id)
            self.redis.setex(cache_key, 3600, plan)  # 1 hour cache
        else:
            plan = plan.decode('utf-8')

        return PLAN_RATE_LIMITS.get(plan, PLAN_RATE_LIMITS["free"])
```

#### Plan-Aware Decorator

```python
# core/rate_limit.py
from functools import wraps

def plan_rate_limit(feature: str = "default"):
    """Decorator for plan-based rate limiting."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, request: Request = None, **kwargs):
            user_id = getattr(request.state, 'user_id', None)

            if not user_id:
                # Fall back to IP-based for unauthenticated
                return await func(*args, request=request, **kwargs)

            limiter = request.app.state.redis_limiter
            plan_limits = await limiter.get_plan_limits(user_id)

            # Parse limit string (e.g., "50/minute")
            limit_str = plan_limits.get(feature, "50/minute")
            limit = int(limit_str.split("/")[0])

            is_allowed, metadata = await limiter.is_allowed(
                key=f"user:{user_id}",
                limit=limit,
                window_seconds=60,
                feature=feature
            )

            if not is_allowed:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for {feature}",
                    headers={"Retry-After": str(metadata["retry_after"])}
                )

            # Add headers to response
            request.state.rate_limit_remaining = metadata["remaining"]

            return await func(*args, request=request, **kwargs)
        return wrapper
    return decorator
```

#### Usage in Routes

```python
@router.post("/chat")
@plan_rate_limit("chat")
async def chat_endpoint(
    request: Request,
    body: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    # Rate limit already applied by decorator
    ...
```

**Effort:** 2-3 weeks
**Risk:** Medium (requires Redis dependency)

---

### 2.4 Distributed Tracing (OpenTelemetry)

**Purpose:** End-to-end request tracing across API and Celery workers.

**Current State:**
- X-Request-ID for HTTP requests only
- No trace propagation to Celery tasks
- Sentry for error tracking (not linked to worker tasks)

**Proposed Solution:** OpenTelemetry with Jaeger backend

#### New Dependencies

```txt
# requirements.txt additions
opentelemetry-api==1.21.0
opentelemetry-sdk==1.21.0
opentelemetry-exporter-jaeger==1.21.0
opentelemetry-instrumentation-fastapi==0.42b0
opentelemetry-instrumentation-celery==0.42b0
opentelemetry-instrumentation-redis==0.42b0
```

#### Configuration Module

```python
# core/tracing_otel.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from core.config import settings
import logging

logger = logging.getLogger(__name__)

def init_otel_tracing(app=None):
    """Initialize OpenTelemetry tracing."""
    if not settings.OTEL_TRACING_ENABLED:
        logger.info("OpenTelemetry tracing disabled")
        return

    # Configure tracer provider
    provider = TracerProvider()

    # Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.JAEGER_AGENT_HOST,
        agent_port=settings.JAEGER_AGENT_PORT,
    )

    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(provider)

    # Set propagator (W3C Trace Context + B3 for compatibility)
    set_global_textmap(B3MultiFormat())

    # Auto-instrument FastAPI
    if app:
        FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument Celery
    CeleryInstrumentor().instrument()

    logger.info("✅ OpenTelemetry tracing initialized")

def get_tracer(name: str) -> trace.Tracer:
    """Get tracer instance for manual instrumentation."""
    return trace.get_tracer(name)

def get_current_span() -> trace.Span:
    """Get current active span."""
    return trace.get_current_span()
```

#### Task Dispatch with Trace Propagation

```python
# In route handlers (e.g., uploads.py)
from core.tracing_otel import get_current_span
from opentelemetry.propagate import inject

# Get current span context
span = get_current_span()
ctx = span.get_span_context()

# Prepare headers for Celery
headers = {}
inject(headers)  # Injects traceparent, tracestate

# Dispatch task with trace context
task = unified_ingest_task.apply_async(
    kwargs={
        "user_id": user_id,
        "job_id": job_id,
        "connector_type": provider,
        "item_ids": [body.storage_path],
        "credentials": None,
        "plan_code": plan_code,
    },
    headers=headers  # Trace context propagated
)
```

#### Configuration Settings

```python
# core/config.py additions
OTEL_TRACING_ENABLED: bool = False  # Feature flag
OTEL_SAMPLING_RATE: float = 0.1     # 10% sampling
JAEGER_AGENT_HOST: str = "localhost"
JAEGER_AGENT_PORT: int = 6831
```

#### Docker Compose (Development)

```yaml
# docker-compose.yml additions
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "6831:6831/udp"
      - "16686:16686"  # Web UI
    environment:
      - COLLECTOR_OTLP_ENABLED=true
```

**Effort:** 4-6 weeks
**Risk:** Medium (new infrastructure dependency)

---

### 2.5 Database Partitioning Strategy

**Purpose:** Scale document_chunks table beyond 100M rows.

**Current State:** Single table with HNSW index on embeddings

**Trigger:** When `document_chunks` exceeds 50M rows

#### Partitioning Strategy

```sql
-- Create partitioned table (future migration)
CREATE TABLE document_chunks_partitioned (
    id UUID NOT NULL,
    document_id UUID NOT NULL,
    content TEXT,
    content_encrypted TEXT,
    embedding vector(1536),
    chunk_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT now(),
    organization_id UUID NOT NULL  -- Partition key
) PARTITION BY HASH (organization_id);

-- Create partitions (16 partitions for distribution)
CREATE TABLE document_chunks_p0 PARTITION OF document_chunks_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 0);
CREATE TABLE document_chunks_p1 PARTITION OF document_chunks_partitioned
    FOR VALUES WITH (MODULUS 16, REMAINDER 1);
-- ... repeat for p2-p15

-- Create indexes on each partition
CREATE INDEX idx_chunks_p0_embedding ON document_chunks_p0
    USING hnsw (embedding vector_cosine_ops);
```

#### Migration Path

1. **Phase 1:** Add `organization_id` to document_chunks (already exists via document join)
2. **Phase 2:** Create new partitioned table
3. **Phase 3:** Migrate data in batches (off-peak hours)
4. **Phase 4:** Swap table names, update indexes
5. **Phase 5:** Drop old table

**Trigger Metrics:**
- Row count > 50M
- Query latency > 200ms p95
- Index size > 50GB

**Effort:** 2-3 weeks (when triggered)
**Risk:** High (requires maintenance window)

---

## Priority 3: Nice-to-Have Features

### 3.1 Service Mesh (Istio/Linkerd)

**Purpose:** Advanced traffic management, mTLS, observability

**When to Consider:**
- Multiple backend services (currently monolithic)
- Need for canary deployments
- Zero-trust security requirements

**Effort:** 6-8 weeks
**Prerequisite:** Kubernetes deployment

### 3.2 Blue/Green Deployments

**Purpose:** Zero-downtime deployments with instant rollback

**Current State:** Railway handles deployments

**Implementation Options:**
- Railway native (preferred for current infrastructure)
- Kubernetes with Ingress controller
- AWS ECS with ALB target groups

**Effort:** 2-3 weeks

### 3.3 Canary Releases for Frontend

**Purpose:** Gradual rollout of frontend changes

**Implementation:**
```typescript
// Feature flag service integration
const useFeatureFlag = (flag: string, userId: string) => {
  // Check if user is in canary cohort (e.g., 10%)
  const hash = hashCode(userId + flag);
  return hash % 100 < CANARY_PERCENTAGE;
};
```

**Effort:** 1-2 weeks

### 3.4 Granular Caching (Per-Feature TTL)

**Purpose:** Optimize performance with feature-specific cache policies

**Implementation:**
```python
# core/caching.py
CACHE_TTL = {
    "user_profile": 3600,      # 1 hour
    "team_members": 300,       # 5 minutes
    "plan_info": 1800,         # 30 minutes
    "connector_status": 60,    # 1 minute
    "search_results": 120,     # 2 minutes
    "document_stats": 600,     # 10 minutes
}

class CacheService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_or_set(
        self,
        key: str,
        feature: str,
        factory: Callable
    ) -> Any:
        cached = await self.redis.get(key)
        if cached:
            return json.loads(cached)

        value = await factory()
        ttl = CACHE_TTL.get(feature, 300)
        await self.redis.setex(key, ttl, json.dumps(value))
        return value
```

**Effort:** 1-2 weeks

---

## Implementation Timeline

### Quarter 1 (Months 1-3)

| Week | Task | Priority | Effort |
|------|------|----------|--------|
| 1 | Invoice Download Enhancement | P1 | 2 hours |
| 1-2 | Repository Pattern - Interfaces | P2 | 1 week |
| 3-4 | Repository Pattern - Implementations | P2 | 2 weeks |
| 5-6 | API Versioning Setup | P2 | 2 weeks |
| 7-8 | Rate Limiting - Redis Integration | P2 | 2 weeks |
| 9-10 | Rate Limiting - Plan-based Limits | P2 | 2 weeks |
| 11-12 | Testing & Stabilization | All | 2 weeks |

### Quarter 2 (Months 4-6)

| Week | Task | Priority | Effort |
|------|------|----------|--------|
| 1-2 | OpenTelemetry Setup | P2 | 2 weeks |
| 3-4 | Trace Propagation (API → Worker) | P2 | 2 weeks |
| 5-6 | Jaeger Dashboard & Alerts | P2 | 2 weeks |
| 7-8 | Granular Caching | P3 | 2 weeks |
| 9-10 | Canary Releases (Frontend) | P3 | 2 weeks |
| 11-12 | Documentation & Training | All | 2 weeks |

### Future (As Needed)

- Database Partitioning: When document_chunks > 50M rows
- Service Mesh: When moving to microservices
- Blue/Green: When zero-downtime is critical

---

## Risk Assessment

| Enhancement | Risk Level | Mitigation |
|-------------|------------|------------|
| Invoice Download | 🟢 Low | Minimal change, existing patterns |
| Repository Pattern | 🟢 Low | Parallel implementation, gradual migration |
| API Versioning | 🟢 Low | Additive change, no breaking changes |
| Rate Limiting | 🟡 Medium | Redis dependency, thorough testing |
| Distributed Tracing | 🟡 Medium | New infrastructure, sampling to limit overhead |
| Database Partitioning | 🔴 High | Requires maintenance window, data migration |

---

## Success Metrics

### Performance
- API latency p95 < 200ms (maintain current)
- Worker task completion p95 < 30s (maintain current)
- Rate limit overhead < 5ms per request

### Reliability
- 99.9% API uptime (maintain current)
- Zero data loss during migrations
- < 5 minute MTTR for rollbacks

### Developer Experience
- 90% test coverage for repositories
- < 2 hour time to trace production issues (with distributed tracing)
- Clear API versioning documentation

---

## Conclusion

AxioHub is already a production-ready, enterprise-grade platform. The enhancements in this document focus on:

1. **Immediate Value (P1):** Minor UI wiring (1 item remaining)
2. **Architectural Foundation (P2):** Repository pattern, rate limiting, tracing
3. **Future Scalability (P3):** Caching, deployments, partitioning

The phased approach ensures minimal risk while progressively improving testability, observability, and scalability.

---

*Document maintained by the AxioHub Engineering Team*
