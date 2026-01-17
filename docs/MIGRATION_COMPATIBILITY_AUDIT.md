# Migration Compatibility Audit Document

**Version**: 1.0  
**Date**: January 17, 2026  
**Purpose**: Systematic verification of all database functions, table schemas, and API compatibility after recent migrations

---

## Table of Contents

1. [Audit Scope](#1-audit-scope)
2. [RPC Function Registry](#2-rpc-function-registry)
3. [Backend RPC Callers](#3-backend-rpc-callers)
4. [Table Schema Changes](#4-table-schema-changes)
5. [RLS Policy Changes](#5-rls-policy-changes)
6. [Verification Checklist](#6-verification-checklist)
7. [Findings](#7-findings)

---

## 1. Audit Scope

### 1.1 Migrations Under Review

| Migration | Date | Description |
|-----------|------|-------------|
| `20260116000004_scope_identities.sql` | Jan 16 | Created scope_identities table |
| `20260116000005_hybrid_search_scoped.sql` | Jan 16 | Added scope-aware hybrid search |
| `20260117000000_scope_identities_composite_key.sql` | Jan 17 | Changed PK to (user_id, id) |
| `20260118000000_add_organization_id_scopes.sql` | Jan 18 | Added organization_id, changed PK to (org_id, id) |
| `20260118000001_hybrid_search_org_scoped.sql` | Jan 18 | Changed filter_user_id to filter_org_id |
| `20260201000000_llm_quota_and_identity_lock.sql` | Feb 01 | Added LLM quota, identity locking |
| `20260216100000_add_scope_identity_status.sql` | Feb 16 | Added status column |
| `20260216120000_org_based_rls_policies.sql` | Feb 16 | Org-based RLS policies |
| `20260216130000_atomic_scope_quota_check.sql` | Feb 16 | Atomic scope quota RPC |
| `20260216140000_fix_scope_quota_rpc.sql` | Feb 16 | Fixed quota check order |
| `20260216150000_org_conversations_rls.sql` | Feb 16 | Conversations RLS |
| `20260216160000_security_definer_search_path.sql` | Feb 16 | Security fixes |
| `20260217120000_fix_identity_upsert_and_purge.sql` | Feb 17 | Fixed upsert and purge |
| `20260217123000_ingestion_file_status_org_scope.sql` | Feb 17 | Org-scoped file status |
| `20260217124000_exclude_identity_from_search.sql` | Feb 17 | Exclude identity docs |
| `20260217140000_fix_identity_source_types.sql` | Feb 17 | Fixed source types |
| `20260218120000_hybrid_search_identity_triple_check.sql` | Feb 18 | Triple identity exclusion |
| `20260220000000_fix_get_effective_plan_v3.sql` | Feb 20 | Fixed get_effective_plan |
| `20260220000001_sync_user_profiles_plan.sql` | Feb 20 | Sync user profiles |

### 1.2 Backend Files to Verify

- `backend/api/v1/chat.py`
- `backend/api/v1/search.py`
- `backend/api/v1/documents.py`
- `backend/api/v1/integrations.py`
- `backend/api/v1/jobs.py`
- `backend/api/v1/uploads.py`
- `backend/api/v1/dependencies.py`
- `backend/services/team_service.py`
- `backend/services/cleanup.py`
- `backend/services/scope_identity.py`
- `backend/services/guardrails.py`
- `backend/worker/tasks.py`
- `backend/worker/periodic_tasks.py`

---

## 2. RPC Function Registry

### 2.1 Search Functions

| Function | Latest Migration | Current Signature |
|----------|------------------|-------------------|
| `hybrid_search` | `20260218120000` | `(query_text TEXT, query_embedding VECTOR(1536), match_count INT DEFAULT 10, filter_org_id UUID DEFAULT NULL, vector_weight FLOAT DEFAULT 0.7, keyword_weight FLOAT DEFAULT 0.3, similarity_threshold FLOAT DEFAULT 0.25)` |
| `hybrid_search_scoped` | `20260218120000` | `(query_text TEXT, query_embedding VECTOR(1536), match_count INT DEFAULT 10, filter_org_id UUID DEFAULT NULL, filter_scope_ids TEXT[] DEFAULT NULL, vector_weight FLOAT DEFAULT 0.7, keyword_weight FLOAT DEFAULT 0.3, similarity_threshold FLOAT DEFAULT 0.25)` |
| `match_documents` | `20260218120000` | `(query_embedding VECTOR(1536), match_threshold FLOAT DEFAULT 0.5, match_count INT DEFAULT 5, filter_org_id UUID DEFAULT NULL)` |

### 2.2 Plan & Team Functions

| Function | Latest Migration | Current Signature |
|----------|------------------|-------------------|
| `get_effective_plan` | `20260220000000` | `(target_user_id UUID) → TEXT` |
| `get_user_team_data` | `20260216160000` | `(p_user_id UUID) → JSONB` |
| `is_org_member` | `20260216140000` | `(org_id UUID, user_uuid UUID) → BOOLEAN` |
| `is_team_owner` | `20260108125000` | `(p_team_id UUID, p_user_id UUID) → BOOLEAN` |
| `is_team_member` | `20260108125000` | `(p_team_id UUID, p_user_id UUID) → BOOLEAN` |
| `is_team_member_of_owner` | `20260108125000` | `(p_owner_id UUID, p_member_user_id UUID) → BOOLEAN` |

### 2.3 Ingestion & Document Functions

| Function | Latest Migration | Current Signature |
|----------|------------------|-------------------|
| `try_create_scope_placeholder` | `20260216140000` | `(p_organization_id UUID, p_user_id UUID, p_scope_id TEXT, p_source_type TEXT, p_max_scopes INTEGER) → TEXT` |
| `upsert_scope_identity_document` | `20260217120000` | `(p_scope_id TEXT, p_organization_id UUID, p_user_id UUID, p_type TEXT, p_summary TEXT, p_file_tree TEXT, p_attributes JSONB, p_last_ingested_at TIMESTAMPTZ, p_doc_title TEXT, p_source_id TEXT, p_metadata JSONB, p_file_size_bytes INT, p_chunk_content TEXT, p_chunk_embedding TEXT) → UUID` |
| `purge_organization` | `20260217120000` | `(p_organization_id UUID, p_owner_id UUID) → JSONB` |
| `increment_crawl_counter` | `20251226103800` | `(p_crawl_id UUID, p_field TEXT) → VOID` |
| `recalculate_user_usage` | `20260216160000` | `(target_user_id UUID) → VOID` |

### 2.4 Trigger Functions (Internal)

| Function | Latest Migration | Purpose |
|----------|------------------|---------|
| `handle_new_user` | `20251230000000` | Auth sync trigger |
| `create_personal_team` | `20251228000000` | Auto-create team for new users |
| `update_documents_updated_at` | `20260109101500` | Timestamp trigger |
| `update_sync_state_timestamp` | `20251226103800` | Sync state trigger |
| `update_failed_tasks_updated_at` | `20260105220000` | Failed tasks trigger |

---

## 3. Backend RPC Callers

### 3.1 Search RPC Calls

| File:Line | RPC Function | Parameters Sent |
|-----------|--------------|-----------------|
| `chat.py:1118` | `hybrid_search_scoped` | `{query_text, query_embedding, match_count, filter_org_id, filter_scope_ids, similarity_threshold}` |
| `chat.py:1128` | `hybrid_search_scoped` | `{query_text, query_embedding, match_count, filter_org_id, filter_scope_ids, vector_weight, keyword_weight, similarity_threshold}` |
| `chat.py:1140` | `hybrid_search` | `{query_text, query_embedding, match_count, filter_org_id, vector_weight, keyword_weight, similarity_threshold}` |
| `search.py:103` | `hybrid_search_scoped` | `{query_text, query_embedding, match_count, filter_org_id, filter_scope_ids, similarity_threshold}` |
| `search.py:113` | `hybrid_search` | `{query_text, query_embedding, match_count, filter_org_id, similarity_threshold}` |
| `guardrails.py:256` | `match_documents` | `{query_embedding, match_threshold, match_count, filter_org_id}` |

### 3.2 Plan & Team RPC Calls

| File:Line | RPC Function | Parameters Sent |
|-----------|--------------|-----------------|
| `team_service.py:109` | `get_effective_plan` | `{"p_user_id": user_id}` |
| `team_service.py:143` | `get_user_team_data` | `{"p_user_id": user_id}` |

### 3.3 Ingestion RPC Calls

| File:Line | RPC Function | Parameters Sent |
|-----------|--------------|-----------------|
| `tasks.py:188` | `try_create_scope_placeholder` | `{p_organization_id, p_user_id, p_scope_id, p_source_type, p_max_scopes}` |
| `scope_identity.py:305` | `upsert_scope_identity_document` | All 14 params |
| `cleanup.py:109` | `purge_organization` | `{p_organization_id, p_owner_id}` |
| `tasks.py:3373+` | `increment_crawl_counter` | `{p_crawl_id, p_field}` |

---

## 4. Table Schema Changes

### 4.1 New Tables

| Migration | Table | Primary Key |
|-----------|-------|-------------|
| `20260116000004` | `scope_identities` | Initially `id` |
| `20260117000000` | - | Changed to `(user_id, id)` |
| `20260118000000` | - | Changed to `(organization_id, id)` |

### 4.2 Column Additions

| Migration | Table | Column | Type | Nullable | Default |
|-----------|-------|--------|------|----------|---------|
| `20251231120000` | `documents` | `team_id` | UUID | YES | NULL |
| `20260116000004` | `documents` | `scope_id` | TEXT | YES | NULL |
| `20260118000000` | `documents` | `organization_id` | UUID | NO | - |
| `20260118000000` | `scope_identities` | `organization_id` | UUID | NO | - |
| `20260118000000` | `ingestion_jobs` | `organization_id` | UUID | YES | NULL |
| `20260216100000` | `scope_identities` | `status` | TEXT | YES | 'placeholder' |
| `20260201000000` | `org_usage` | `llm_tokens_used` | BIGINT | NO | 0 |
| `20260201000000` | `teams` | `llm_token_balance` | BIGINT | YES | NULL |

### 4.3 Foreign Key Changes

| Migration | Constraint | Definition |
|-----------|------------|------------|
| `20260116000004` | `documents_scope_id_fkey` | `documents(scope_id) → scope_identities(id)` |
| `20260117000000` | `documents_scope_id_fkey` | `documents(user_id, scope_id) → scope_identities(user_id, id)` |
| `20260118000000` | `documents_scope_id_fkey` | `documents(organization_id, scope_id) → scope_identities(organization_id, id)` |

---

## 5. RLS Policy Changes

### 5.1 Documents RLS

| Policy | Migration | Access Pattern |
|--------|-----------|----------------|
| OLD | pre-20260216 | `user_id = auth.uid()` |
| NEW | `20260216120000` | `is_org_member(organization_id, auth.uid())` |

### 5.2 Scope Identities RLS

| Policy | Migration | Access Pattern |
|--------|-----------|----------------|
| OLD | `20260116000004` | `user_id = auth.uid()` |
| NEW | `20260216120000` | `is_org_member(organization_id, auth.uid())` |

### 5.3 Ingestion Jobs RLS

| Policy | Migration | Access Pattern |
|--------|-----------|----------------|
| OLD | pre-20260216 | `user_id = auth.uid()` |
| NEW | `20260216120000` | `is_org_member(organization_id, auth.uid())` |

### 5.4 Conversations RLS

| Policy | Migration | Access Pattern |
|--------|-----------|----------------|
| Conditional | `20260216120000` | If `organization_id` exists → org-based, else → user-based |

---

## 6. Verification Checklist

### 6.1 RPC Parameter Compatibility

| ID | Function | Check | Status |
|----|----------|-------|--------|
| RPC-01 | `get_effective_plan` | Param name matches (`target_user_id` vs `p_user_id`) | ❌ MISMATCH |
| RPC-02 | `get_user_team_data` | Param name matches | ✅ OK |
| RPC-03 | `hybrid_search` | All params compatible | ✅ OK |
| RPC-04 | `hybrid_search_scoped` | All params compatible | ✅ OK |
| RPC-05 | `match_documents` | All params compatible | ✅ OK |
| RPC-06 | `try_create_scope_placeholder` | All params compatible | ✅ OK |
| RPC-07 | `upsert_scope_identity_document` | All 14 params match | ✅ OK |
| RPC-08 | `purge_organization` | Both params present | ✅ OK |
| RPC-09 | `increment_crawl_counter` | All params compatible | ✅ OK |

### 6.2 Table Column Compatibility

| ID | Table | Check | Status |
|----|-------|-------|--------|
| TBL-01 | `documents` | `organization_id` NOT NULL enforced | ✅ OK |
| TBL-02 | `documents` | `scope_id` FK works with composite key | ✅ OK |
| TBL-03 | `scope_identities` | `status` column exists | ✅ OK |
| TBL-04 | `ingestion_jobs` | `organization_id` populated | ✅ OK |
| TBL-05 | `conversations` | Check if `organization_id` column exists | ✅ OK |

### 6.3 RLS Policy Compatibility

| ID | Table | Check | Status |
|----|-------|-------|--------|
| RLS-01 | `documents` | Solo users pass `is_org_member` check | ❌ FAIL |
| RLS-02 | `scope_identities` | Solo users pass `is_org_member` check | ❌ FAIL |
| RLS-03 | `conversations` | Correct policy applied | ❌ FAIL (solo) |
| RLS-04 | `ingestion_jobs` | `organization_id` column check works | ❌ FAIL (solo) |

### 6.4 Data Migration Completeness

| ID | Check | Status |
|----|-------|--------|
| DATA-01 | All existing `documents` have `organization_id` | ✅ OK (backfilled) |
| DATA-02 | All existing `scope_identities` have `organization_id` | ✅ OK (backfilled) |
| DATA-03 | Solo users have `teams` row for RLS | ❌ FAIL |
| DATA-04 | `source_type` values consistent (`identity` vs `scope_identity`) | ⚠️ INCONSISTENT |

### 6.5 Backend Code Compatibility

| ID | File | Check | Status |
|----|------|-------|--------|
| CODE-01 | `dependencies.py` | `get_user_organization_id` resolves correctly | ⚠️ PARTIAL |
| CODE-02 | `team_service.py` | `get_organization_id` fallback safe | ⚠️ PARTIAL |
| CODE-03 | `cleanup.py` | `purge_organization` params correct | ✅ OK |
| CODE-04 | `scope_identity.py` | `upsert_scope_identity_document` params correct | ✅ OK |
| CODE-05 | `tasks.py` | `_ensure_scope_identity_placeholder` params correct | ✅ OK |

---

## 7. Findings

### 7.1 Confirmed Issues

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| **ISSUE-001** | 🔴 CRITICAL | `get_effective_plan` RPC parameter mismatch: Function expects `target_user_id` but backend sends `p_user_id` | ✅ FIXED (20260221000001) |
| **ISSUE-002** | 🔴 CRITICAL | Solo users with `organization_id = user_id` fail RLS: `is_org_member(user_id, user_id)` returns FALSE because no `teams` row exists with `id = user_id` | ✅ FIXED (20260221000000) |
| **ISSUE-003** | 🟡 MEDIUM | `source_type` data inconsistency: Some identity docs have `'scope_identity'` (from old migration), others have `'identity'` (from newer migration) | ✅ FIXED (20260221000002) |

### 7.2 Potential Issues

| ID | Severity | Description | Status |
|----|----------|-------------|--------|
| **POT-001** | 🟡 MEDIUM | Conversations with `organization_id = user_id` will fail RLS for solo users without team rows | ✅ FIXED by ISSUE-002 fix |
| **POT-002** | 🟢 LOW | `ingest_document_with_chunks` RPC referenced in tests but not production code (deprecated) | CONFIRMED SAFE |
| **POT-003** | 🟢 LOW | `delete_document_with_chunks` and `search_similar_chunks` RPCs not used in backend | CONFIRMED SAFE |

### 7.3 Issue Details

#### ISSUE-001: `get_effective_plan` Parameter Mismatch

**Migration Signature (20260220000000):**
```sql
CREATE OR REPLACE FUNCTION public.get_effective_plan(target_user_id UUID)
```

**Backend Call (team_service.py:109-111):**
```python
response = supabase.rpc(
    "get_effective_plan", 
    {"p_user_id": user_id}  # ❌ WRONG - should be "target_user_id"
)
```

**Impact:** Every call to `get_effective_plan` may fail or return unexpected results because PostgreSQL RPC calls via PostgREST require exact parameter name matching.

**Fix Required:** Change backend to send `{"target_user_id": user_id}`

---

#### ISSUE-002: Solo User RLS Failure

**Root Cause:**

1. Migration `20260118000000` backfills `organization_id = user_id` for users without teams:
```sql
UPDATE scope_identities SET organization_id = user_id WHERE organization_id IS NULL;
UPDATE documents SET organization_id = user_id WHERE organization_id IS NULL;
```

2. `get_user_organization_id` in `dependencies.py` returns `user_id` when no team found:
```python
# For solo users (no team), use user_id as organization_id
return user_id
```

3. RLS policies call `is_org_member(organization_id, auth.uid())`:
```sql
IF EXISTS (
    SELECT 1 FROM public.teams 
    WHERE id = org_id       -- ❌ No team exists with id = user_id
    AND owner_id = user_uuid
) THEN RETURN TRUE;
```

**Impact:** Solo users (users without teams) cannot access their own documents because:
- `organization_id = user_id` (e.g., `abc-123-user-uuid`)
- `is_org_member('abc-123-user-uuid', 'abc-123-user-uuid')` checks `teams.id = 'abc-123-user-uuid'`
- No such team exists (team IDs are auto-generated, not equal to user IDs)
- RLS denies access

**Affected Tables:**
- `documents` 
- `scope_identities`
- `conversations`
- `ingestion_jobs`

**Fix Required:** Either:
1. Create team rows with `id = owner_id` for solo users (data fix), OR
2. Modify `is_org_member` to handle solo user case (schema fix), OR
3. Fix `get_user_organization_id` to always return a valid team_id (code fix)

---

#### ISSUE-003: Source Type Inconsistency

**History:**
- Migration `20260201000000`: Sets `source_type = 'scope_identity'`
- Migration `20260217120000`: Sets `source_type = 'identity'`
- Migration `20260217140000`: Attempts to fix existing records

**Current State:**
- Hybrid search filters exclude BOTH `'identity'` AND `'scope_identity'` ✅
- Backend document list excludes BOTH ✅
- Data inconsistency exists but is handled

**Fix:** Migration `20260217140000` should have fully standardized all records.

---

### 7.4 Verification Results Summary

| Check ID | Description | Result |
|----------|-------------|--------|
| RPC-01 | `get_effective_plan` param | ❌ MISMATCH |
| RPC-02 | `get_user_team_data` param | ✅ OK (`p_user_id`) |
| RPC-03 | `hybrid_search` params | ✅ OK |
| RPC-04 | `hybrid_search_scoped` params | ✅ OK |
| RPC-05 | `match_documents` params | ✅ OK |
| RPC-06 | `try_create_scope_placeholder` params | ✅ OK |
| RPC-07 | `upsert_scope_identity_document` params | ✅ OK |
| RPC-08 | `purge_organization` params | ✅ OK |
| RPC-09 | `increment_crawl_counter` params | ✅ OK |
| TBL-01 | `documents.organization_id` NOT NULL | ✅ OK |
| TBL-02 | `documents.scope_id` FK | ✅ OK |
| TBL-03 | `scope_identities.status` exists | ✅ OK |
| TBL-04 | `ingestion_jobs.organization_id` populated | ✅ OK |
| TBL-05 | `conversations.organization_id` exists | ✅ OK |
| RLS-01 | Solo users pass documents RLS | ❌ FAIL |
| RLS-02 | Solo users pass scope_identities RLS | ❌ FAIL |
| RLS-03 | Conversations RLS correct | ❌ FAIL (solo users) |
| RLS-04 | Ingestion jobs RLS correct | ❌ FAIL (solo users) |
| DATA-01 | All documents have org_id | ✅ OK (backfilled) |
| DATA-02 | All scope_identities have org_id | ✅ OK (backfilled) |
| DATA-03 | Solo users have teams row | ❌ FAIL (not guaranteed) |
| DATA-04 | source_type consistency | ⚠️ INCONSISTENT |
| CODE-01 | `get_user_organization_id` safe | ⚠️ PARTIAL |
| CODE-02 | `team_service.get_organization_id` safe | ⚠️ PARTIAL |
| CODE-03 | `cleanup.py` params | ✅ OK |
| CODE-04 | `scope_identity.py` params | ✅ OK |
| CODE-05 | `tasks.py` params | ✅ OK |

### 7.5 Recommended Fixes

| Priority | Issue | Fix Type | Description |
|----------|-------|----------|-------------|
| P0 | ISSUE-001 | Code Fix | Change `team_service.py` to send `{"target_user_id": user_id}` |
| P0 | ISSUE-002 | Schema Fix | Modify `is_org_member` to return TRUE when `org_id = user_uuid` (self-ownership) |
| P1 | ISSUE-003 | Data Fix | Run SQL to standardize all `source_type = 'scope_identity'` to `'identity'` |

---

## Appendix A: Verification Execution Log

**2026-01-17 - Audit Execution**

| Time | Step | Result |
|------|------|--------|
| - | Extracted all RPC functions from migrations | 57 function definitions found |
| - | Extracted all backend RPC callers | 21 call sites found |
| - | Verified `get_effective_plan` signature | ❌ MISMATCH FOUND |
| - | Verified `get_user_team_data` signature | ✅ OK |
| - | Verified search functions signatures | ✅ OK |
| - | Verified ingestion functions signatures | ✅ OK |
| - | Analyzed `is_org_member` logic | ❌ SOLO USER BUG FOUND |
| - | Checked `conversations.organization_id` | ✅ Column exists |
| - | Checked `source_type` values | ⚠️ INCONSISTENCY FOUND |
| - | Verified legacy RPCs not used | ✅ SAFE |

---

## Appendix B: Test Queries

### B1. Check Solo User Team Existence
```sql
-- Find users without teams
SELECT u.id, u.email
FROM auth.users u
LEFT JOIN teams t ON t.owner_id = u.id
LEFT JOIN team_members tm ON tm.member_user_id = u.id
WHERE t.id IS NULL AND tm.team_id IS NULL;
```

### B2. Check Documents Without organization_id
```sql
SELECT COUNT(*) FROM documents WHERE organization_id IS NULL;
```

### B3. Check Scope Identities PK
```sql
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'scope_identities'::regclass AND contype = 'p';
```

---

## Appendix B: Proposed Fixes

### B1. Fix ISSUE-001: `get_effective_plan` Parameter Name

**Option A: Fix Backend Code (Recommended)**

File: `backend/services/team_service.py`

```python
# Change from:
response = supabase.rpc(
    "get_effective_plan", 
    {"p_user_id": user_id}
).execute()

# Change to:
response = supabase.rpc(
    "get_effective_plan", 
    {"target_user_id": user_id}
).execute()
```

**Option B: Fix Database Function**

Create migration to rename parameter:
```sql
CREATE OR REPLACE FUNCTION public.get_effective_plan(p_user_id UUID)
-- Rest of function body unchanged
```

### B2. Fix ISSUE-002: Solo User RLS Failure

**Option A: Modify `is_org_member` Function (Recommended)**

Add self-ownership check:
```sql
CREATE OR REPLACE FUNCTION public.is_org_member(
    org_id UUID,
    user_uuid UUID
) RETURNS BOOLEAN AS $$
BEGIN
    -- NEW: Self-ownership check for solo users
    -- If org_id equals user_uuid, user is accessing their own data
    IF org_id = user_uuid THEN
        RETURN TRUE;
    END IF;
    
    -- Check 1: Is user the team/org owner?
    IF EXISTS (
        SELECT 1 FROM public.teams 
        WHERE id = org_id 
        AND owner_id = user_uuid
    ) THEN
        RETURN TRUE;
    END IF;
    
    -- Check 2: Is user an active team member?
    IF EXISTS (
        SELECT 1 FROM public.team_members 
        WHERE team_id = org_id 
        AND member_user_id = user_uuid
        AND status != 'removed'
    ) THEN
        RETURN TRUE;
    END IF;
    
    RETURN FALSE;
END;
$$ LANGUAGE plpgsql 
   SECURITY DEFINER
   SET search_path = public;
```

**Option B: Fix Data - Create Team Rows for Solo Users**

```sql
-- Create teams for users who have documents but no team
INSERT INTO teams (id, name, owner_id, created_at, updated_at)
SELECT DISTINCT 
    d.organization_id,  -- Use existing org_id as team_id
    'Personal Team',
    d.user_id,
    NOW(),
    NOW()
FROM documents d
LEFT JOIN teams t ON t.id = d.organization_id
WHERE t.id IS NULL
  AND d.organization_id = d.user_id  -- Solo user fallback pattern
ON CONFLICT (id) DO NOTHING;

-- Also create team_members entries
INSERT INTO team_members (team_id, owner_user_id, member_user_id, role, status, email)
SELECT 
    t.id,
    t.owner_id,
    t.owner_id,
    'admin',
    'active',
    u.email
FROM teams t
JOIN auth.users u ON u.id = t.owner_id
LEFT JOIN team_members tm ON tm.team_id = t.id AND tm.member_user_id = t.owner_id
WHERE tm.id IS NULL
ON CONFLICT DO NOTHING;
```

### B3. Fix ISSUE-003: Source Type Inconsistency

```sql
-- Standardize all identity documents to 'identity'
UPDATE documents 
SET source_type = 'identity',
    updated_at = NOW()
WHERE source_type = 'scope_identity';
```

---

## Appendix C: Test Queries

### C1. Find Users Affected by ISSUE-002
```sql
SELECT DISTINCT d.user_id, d.organization_id
FROM documents d
LEFT JOIN teams t ON t.id = d.organization_id
WHERE t.id IS NULL
  AND d.organization_id = d.user_id;
```

### C2. Count Documents with Each source_type
```sql
SELECT source_type, COUNT(*) 
FROM documents 
WHERE source_type IN ('identity', 'scope_identity')
GROUP BY source_type;
```

### C3. Verify get_effective_plan Works
```sql
SELECT get_effective_plan('your-user-uuid-here'::uuid);
```

---

## Appendix D: Implementation Details of Fixes

### D1. ISSUE-001 Fix: get_effective_plan Parameter (20260221000001)

**Problem**: The `get_effective_plan` RPC function expected a parameter named `target_user_id`, but the backend code in `team_service.py` was sending `p_user_id`.

**Solution**: Migration `20260221000001_fix_get_effective_plan_param.sql` recreates the function with the correct parameter name `p_user_id`.

**Files Changed**:
- `supabase/migrations/20260221000001_fix_get_effective_plan_param.sql` (NEW)

**Verification**:
```sql
-- Should work without error
SELECT get_effective_plan('00000000-0000-0000-0000-000000000000'::uuid);
```

### D2. ISSUE-002 Fix: Solo User RLS (20260221000000)

**Problem**: Solo users (those without a team) have their data stored with `organization_id = user_id`. However, the `is_org_member(org_id, user_id)` function returned FALSE for this case because it only checked for team membership, not self-ownership.

**Solution**: Migration `20260221000000_fix_org_member_solo_users.sql` modifies `is_org_member` to handle the "self-ownership" case where `org_id = user_uuid`.

**Key Logic**:
```sql
IF org_id = user_uuid THEN
    RETURN TRUE;  -- Solo user accessing own data
END IF;
```

**Files Changed**:
- `supabase/migrations/20260221000000_fix_org_member_solo_users.sql` (NEW)

**Verification**:
```sql
-- Should return TRUE (solo user self-access)
SELECT is_org_member('11111111-1111-1111-1111-111111111111'::uuid, 
                     '11111111-1111-1111-1111-111111111111'::uuid);

-- Should return FALSE (different users)
SELECT is_org_member('11111111-1111-1111-1111-111111111111'::uuid,
                     '22222222-2222-2222-2222-222222222222'::uuid);
```

### D3. ISSUE-003 Fix: source_type Standardization (20260221000002)

**Problem**: Historical migrations created identity documents with inconsistent `source_type` values:
- `20260201000000`: Used `'scope_identity'`
- `20260217120000`: Used `'identity'`

**Solution**: Migration `20260221000002_standardize_identity_source_type.sql`:
1. Updates all existing `source_type='scope_identity'` documents to `'identity'`
2. Updates `upsert_scope_identity_document` RPC to always use `'identity'`

**Files Changed**:
- `supabase/migrations/20260221000002_standardize_identity_source_type.sql` (NEW)

**Verification**:
```sql
-- Should return 0
SELECT COUNT(*) FROM documents WHERE source_type = 'scope_identity';
```

### D4. Integration Tests

New integration tests were added to verify all fixes work correctly:

- `backend/tests/integration/test_migration_fixes.sql` - SQL-based tests for Supabase SQL Editor
- `backend/tests/integration/test_migration_fixes_py.py` - Python pytest integration tests

**Run Python Tests**:
```bash
cd backend
pytest tests/integration/test_migration_fixes_py.py -v
```

---

*Document maintained by: Migration Audit System*
*Last updated: 2026-01-17*
*Audit executed by: AI Assistant*
