# Usage Dashboard - V2 Feature Scope

**Created:** January 21, 2026  
**Status:** Planned for V2  
**Priority:** Medium  

---

## Overview

Create a comprehensive Usage Dashboard where users can see their usage, tasks they perform, token spending, and activity history.

---

## Current State Analysis

### Data Already Being Tracked

| Data Type | Location | Currently Exposed via API |
|-----------|----------|---------------------------|
| **Files Count** | `documents` table (calculated) | ✅ `GET /usage` |
| **Storage Bytes** | `documents.file_size_bytes` | ✅ `GET /usage` |
| **LLM Tokens Used** | `org_usage.llm_tokens_used` | ❌ Not exposed |
| **LLM Token Balance** | `teams.llm_token_balance` | ❌ Not exposed |
| **Ingestion Jobs** | `ingestion_jobs` table | ✅ `GET /jobs` |
| **Job File Details** | `ingestion_file_status` table | ✅ `GET /jobs/{id}/files` |
| **Connected Sources** | `documents` by provider | ❌ Not aggregated |

### Existing Infrastructure

- **Backend Service:** `backend/services/usage.py` - Contains `get_org_llm_balance()`, `record_llm_usage()`, `check_llm_quota()`
- **Usage API:** `backend/api/v1/usage.py` - Exposes file/storage usage
- **Jobs API:** `backend/api/v1/jobs.py` - Exposes job history
- **Frontend Hook:** `frontend-new/hooks/useUsage.ts` - Singleton pattern for usage data
- **Billing Settings:** `frontend-new/components/settings/BillingSettings.tsx` - Shows plan info

### Database Tables

```sql
-- Existing tables with usage data:
org_usage (
    org_id UUID,
    llm_tokens_used BIGINT,  -- Total LLM tokens consumed
    ...
)

teams (
    id UUID,
    llm_token_balance BIGINT,  -- Optional prepaid balance override
    ...
)

ingestion_jobs (
    id UUID,
    user_id UUID,
    organization_id UUID,
    provider TEXT,
    total_files INT,
    processed_files INT,
    failed_files INT,
    status TEXT,
    created_at TIMESTAMPTZ,
    ...
)
```

---

## Proposed Dashboard Features

### 1. Summary Cards (Quick Glance)

```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ 📄 Files     │ │ 💾 Storage   │ │ 🤖 AI Tokens │ │ 🔌 Sources   │
│ 45 / 50      │ │ 48MB / 100MB │ │ 850K / 1M    │ │ 5 connected  │
│ ████████░░   │ │ ████████░░   │ │ ████████░░   │ │              │
│ 90%          │ │ 48%          │ │ 85%          │ │              │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### 2. LLM Token Usage Section

- Current balance remaining
- Usage this billing period
- Limit by plan:
  - Starter: 1M tokens/month
  - Pro: 10M tokens/month
  - Enterprise: 100M tokens/month

### 3. Activity History (Recent Jobs)

```
┌────────────────────────────────────────────────────────────────┐
│ Recent Activity                                                │
├────────────────────────────────────────────────────────────────┤
│ 🟢 Google Drive  │ 12 files │ Completed │ 2 hours ago         │
│ 🟢 Dropbox       │ 8 files  │ Completed │ Yesterday           │
│ 🔴 Web Crawl     │ 3 files  │ Failed    │ 3 days ago          │
│ 🟢 YouTube       │ 1 file   │ Completed │ 1 week ago          │
└────────────────────────────────────────────────────────────────┘
```

### 4. Data Sources Breakdown

```
Documents by Source:
├── Google Drive: 25 files (15 MB)
├── Dropbox: 12 files (8 MB)
├── Web Crawl: 5 files (2 MB)
└── Upload: 3 files (23 MB)
```

### 5. (Future) Usage Over Time Chart

- Daily/weekly token consumption
- Storage growth over time
- Requires new `llm_usage_log` table for historical data

---

## Implementation Plan

### Backend Changes

#### 1. New LLM Usage Endpoint

**File:** `backend/api/v1/usage.py`

```python
class LLMUsageResponse(BaseModel):
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    percent_used: float
    has_balance_override: bool
    plan: str

@router.get("/usage/llm", response_model=LLMUsageResponse)
async def get_llm_usage(
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Get LLM token usage for the organization."""
    from services.usage import get_org_llm_balance
    from services.team_service import team_service
    
    plan = await team_service.get_effective_plan(user_id)
    balance_info = await get_org_llm_balance(organization_id, plan)
    
    return LLMUsageResponse(
        tokens_used=balance_info.get("tokens_used", 0),
        tokens_limit=balance_info.get("limit", 0),
        tokens_remaining=balance_info.get("balance", 0),
        percent_used=min(100.0, (balance_info["tokens_used"] / balance_info["limit"] * 100)) if balance_info.get("limit") else 0,
        has_balance_override=balance_info.get("source") == "balance_override",
        plan=plan or "free"
    )
```

#### 2. Source Breakdown Endpoint

**File:** `backend/api/v1/usage.py`

```python
class SourceBreakdown(BaseModel):
    source_type: str
    file_count: int
    storage_bytes: int
    storage_display: str

class SourcesResponse(BaseModel):
    sources: list[SourceBreakdown]
    total_sources: int

@router.get("/usage/sources", response_model=SourcesResponse)
async def get_source_breakdown(
    request: Request,
    user_id: str = Depends(get_current_user),
    organization_id: str = Depends(get_user_organization_id),
):
    """Get document count and storage by source type."""
    supabase = get_supabase()
    
    # Query documents grouped by source_type
    response = supabase.table("documents")\
        .select("source_type, file_size_bytes")\
        .eq("organization_id", organization_id)\
        .neq("source_type", "identity")\
        .neq("source_type", "scope_identity")\
        .execute()
    
    # Aggregate by source_type
    breakdown = {}
    for doc in response.data or []:
        source = doc.get("source_type", "unknown")
        if source not in breakdown:
            breakdown[source] = {"count": 0, "bytes": 0}
        breakdown[source]["count"] += 1
        breakdown[source]["bytes"] += doc.get("file_size_bytes", 0) or 0
    
    sources = [
        SourceBreakdown(
            source_type=source,
            file_count=data["count"],
            storage_bytes=data["bytes"],
            storage_display=format_bytes(data["bytes"])
        )
        for source, data in sorted(breakdown.items(), key=lambda x: x[1]["count"], reverse=True)
    ]
    
    return SourcesResponse(
        sources=sources,
        total_sources=len(sources)
    )
```

### Frontend Changes

#### 1. New Component

**File:** `frontend-new/components/settings/UsageDashboard.tsx`

Component structure:
- Summary cards (files, storage, LLM tokens, sources)
- LLM usage progress bar with details
- Recent activity table (from `/jobs` endpoint)
- Source breakdown list

#### 2. Settings Layout Update

**File:** `frontend-new/app/dashboard/settings/layout.tsx`

Add navigation item:
```typescript
{ name: "Usage", path: "/dashboard/settings/usage", icon: BarChart3 },
```

#### 3. New Page

**File:** `frontend-new/app/dashboard/settings/usage/page.tsx`

```typescript
"use client";
import { UsageDashboard } from "@/components/settings/UsageDashboard";

export default function UsagePage() {
    return <UsageDashboard />;
}
```

### Database Changes (Optional - For Historical Charts)

```sql
-- Migration: Add LLM usage log for historical tracking
CREATE TABLE llm_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    tokens_used INT NOT NULL,
    provider TEXT,  -- 'anthropic', 'openai', etc.
    model TEXT,     -- 'claude-3-opus', 'gpt-4o', etc.
    operation TEXT, -- 'chat', 'embedding', etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_llm_usage_log_org_date ON llm_usage_log(org_id, created_at DESC);

-- RLS
ALTER TABLE llm_usage_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own org usage"
    ON llm_usage_log FOR SELECT
    USING (org_id IN (
        SELECT organization_id FROM user_profiles WHERE user_id = auth.uid()
    ));
```

---

## Effort Estimation

| Task | Estimated Time |
|------|----------------|
| Backend: LLM usage endpoint | 1 hour |
| Backend: Source breakdown endpoint | 1 hour |
| Frontend: UsageDashboard component | 4-5 hours |
| Frontend: Route & navigation | 30 min |
| Testing & polish | 2 hours |
| **Total** | **8-10 hours** |

### Optional Enhancements

| Task | Estimated Time |
|------|----------------|
| Historical usage chart | +3 hours |
| Database migration for usage log | +1 hour |
| Update `record_llm_usage()` to log history | +1 hour |

---

## Dependencies

- Existing `useUsage()` hook
- Existing `/jobs` API endpoint
- Chart library (recharts already in dependencies)

---

## Notes

- The DLQ Dashboard (`DLQDashboard.tsx`) at `/dashboard/settings/failed-tasks` provides a good reference for the table/card patterns
- Consider merging some usage info into the existing Billing page, or keep separate for cleaner UX
- LLM token limits by plan are defined in `backend/core/quotas.py` (QUOTA_LIMITS)
