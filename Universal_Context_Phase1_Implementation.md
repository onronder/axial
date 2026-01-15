## Universal Context Architecture — Phase 1 (Steps 1–3) Implementation Report

This document records the exact changes implemented for Phase 1: **Database migration**, **canonical scope URI utility**, and **ingestion integration**. No chat/retrieval logic was modified.

---

### Step 1 — Database Migration (Schema)

**File created**
- `supabase/migrations/20260116000004_scope_identities.sql`

**DDL summary**
- New table `scope_identities` with canonical URI as primary key.
- RLS enabled with select/insert/update/delete policies restricted to `user_id = auth.uid()`.
- Added `documents.scope_id` column, foreign key to `scope_identities(id)` with `ON DELETE CASCADE`.
- Added BTREE index on `documents(scope_id)`.

**Full SQL**
```
-- Migration: Add scope_identities table and scope_id on documents

-- 1) Create scope_identities table
CREATE TABLE IF NOT EXISTS scope_identities (
    id TEXT PRIMARY KEY, -- Canonical URI (e.g., github://org/repo@main)
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    summary TEXT,
    file_tree TEXT,
    last_ingested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- 2) Enable RLS and policies
ALTER TABLE scope_identities ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scope_identities_select_own"
ON scope_identities FOR SELECT
USING (user_id = auth.uid());

CREATE POLICY "scope_identities_insert_own"
ON scope_identities FOR INSERT
WITH CHECK (user_id = auth.uid());

CREATE POLICY "scope_identities_update_own"
ON scope_identities FOR UPDATE
USING (user_id = auth.uid());

CREATE POLICY "scope_identities_delete_own"
ON scope_identities FOR DELETE
USING (user_id = auth.uid());

-- 3) Add scope_id to documents with FK + index
ALTER TABLE documents ADD COLUMN IF NOT EXISTS scope_id TEXT;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'documents_scope_id_fkey'
    ) THEN
        ALTER TABLE documents
            ADD CONSTRAINT documents_scope_id_fkey
            FOREIGN KEY (scope_id)
            REFERENCES scope_identities(id)
            ON DELETE CASCADE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_documents_scope_id ON documents(scope_id);
```

---

### Step 2 — Canonical Scope Utility (The Law)

**File created**
- `backend/core/scopes.py`

**Public API**
- `build_scope_uri(source_type: str, metadata: dict) -> str`
  - Enforces canonical URI formats for GitHub, S3, Box, Dropbox, Google Drive, Notion, Web.
  - Raises `ValueError` when required metadata fields are missing.

**Implementation details**
- Normalizes `source_type` (lowercase, underscores).
- Pulls required identifiers from `metadata` with `_require` helper.
- S3 prefix normalization:
  - Uses `prefix` if provided.
  - Falls back to deriving prefix from `key`/`object_key` (folder portion).
  - Returns `s3://{bucket}/` when prefix is empty.
- Web scope:
  - Extracts domain from `url`/`source_url`.
  - Accepts bare domains by prepending `https://` for parsing.
- File upload scope (internal):
  - `file_upload://{storage_path}` for completeness of ingestion flow.

**Full file content**
```
"""
Scope URI helpers.

Enforces canonical scope_id formats across connectors.
"""

from __future__ import annotations

from typing import Any, Dict
from urllib.parse import urlparse


def _require(metadata: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = metadata.get(key)
        if value:
            return str(value)
    raise ValueError(f"Missing required metadata field(s): {', '.join(keys)}")


def _normalize_source_type(source_type: str) -> str:
    if not source_type:
        raise ValueError("source_type is required")
    return str(source_type).strip().lower().replace(" ", "_").replace("-", "_")


def _normalize_path(value: str) -> str:
    return str(value or "").strip().strip("/")


def _extract_domain(url: str) -> str:
    if not url:
        raise ValueError("Missing required metadata field(s): url")
    parsed = urlparse(url)
    if not parsed.netloc:
        parsed = urlparse(f"https://{url}")
    if not parsed.netloc:
        raise ValueError(f"Invalid URL for web scope: {url}")
    return parsed.netloc.lower()


def build_scope_uri(source_type: str, metadata: Dict[str, Any]) -> str:
    """
    Build a canonical scope URI for a given source type.

    Supported formats:
    - GitHub: github://{org}/{repo}@{branch}
    - S3: s3://{bucket}/{prefix}
    - Box: box://folder/{folder_id}:{folder_name}
    - Dropbox: dropbox://{namespace_id}/{path}
    - Google Drive: gdrive://{drive_id}/{folder_id}:{name}
    - Notion: notion://{workspace_id}/{page_id}:{title}
    - Web: web://{domain}
    """
    metadata = metadata or {}
    source_type = _normalize_source_type(source_type)

    if source_type == "github":
        repository = metadata.get("repository") or metadata.get("repo")
        if repository and "/" in repository:
            org, repo = repository.split("/", 1)
        else:
            org = _require(metadata, "org", "owner")
            repo = repository or _require(metadata, "repo", "repo_name", "name")
        branch = metadata.get("branch") or metadata.get("ref") or metadata.get("default_branch") or "main"
        return f"github://{org}/{repo}@{branch}"

    if source_type == "s3":
        bucket = _require(metadata, "bucket", "bucket_name")
        prefix = metadata.get("prefix")
        if prefix is None:
            key = metadata.get("key") or metadata.get("object_key")
            prefix = _normalize_path(key.rsplit("/", 1)[0]) if key and "/" in key else ""
        prefix = _normalize_path(prefix)
        if prefix:
            return f"s3://{bucket}/{prefix}"
        return f"s3://{bucket}/"

    if source_type == "box":
        folder_id = _require(metadata, "folder_id", "parent_id")
        folder_name = _require(metadata, "folder_name", "parent_name", "root_folder_name")
        return f"box://folder/{folder_id}:{folder_name}"

    if source_type == "dropbox":
        namespace_id = _require(metadata, "namespace_id")
        path = _require(metadata, "path", "path_display", "path_lower")
        path = _normalize_path(path)
        return f"dropbox://{namespace_id}/{path}"

    if source_type in {"google_drive", "gdrive"}:
        drive_id = _require(metadata, "drive_id", "shared_drive_id")
        folder_id = _require(metadata, "folder_id", "parent_id")
        name = _require(metadata, "name", "folder_name")
        return f"gdrive://{drive_id}/{folder_id}:{name}"

    if source_type == "notion":
        workspace_id = _require(metadata, "workspace_id")
        page_id = _require(metadata, "page_id", "id")
        title = _require(metadata, "title", "name")
        return f"notion://{workspace_id}/{page_id}:{title}"

    if source_type == "web":
        url = metadata.get("url") or metadata.get("source_url")
        domain = _extract_domain(url)
        return f"web://{domain}"

    if source_type == "file_upload":
        storage_path = _require(metadata, "storage_path")
        return f"file_upload://{storage_path}"

    raise ValueError(f"Unsupported source_type for scope URI: {source_type}")
```

---

### Step 3 — Ingestion Pipeline Integration

#### 3.1 Ingestion utility: scope generation hook

**File updated**
- `backend/core/ingestion_utils.py`

**Change summary**
- Added `ensure_scope_id()` which injects a canonical `scope_id` into metadata using `build_scope_uri` when missing.

**Modified section**
```
from typing import Optional, Dict, Any

from core.scopes import build_scope_uri

...

def ensure_scope_id(source_type: Optional[str], metadata: Dict[str, Any]) -> str:
    """
    Ensure metadata contains a canonical scope_id, generating it if missing.
    """
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be a dict")
    scope_id = metadata.get("scope_id")
    if scope_id:
        return str(scope_id)
    normalized_source_type = normalize_source_type(source_type) or source_type
    scope_id = build_scope_uri(str(normalized_source_type or ""), metadata)
    metadata["scope_id"] = scope_id
    return scope_id
```

#### 3.2 Unified ingest dispatch: scope passed to file task

**File updated**
- `backend/worker/tasks.py`

**Change summary**
- Unified ingestion now computes `scope_id` for each `SourceDocument` using `ensure_scope_id`.
- `process_file_task` signature now requires `scope_id`.
- `process_file_task` injects `scope_id` into metadata before parsing/embedding.
- `ingest_document_batched` writes `scope_id` to `documents` table (new column).

**Modified sections (key excerpts)**
```
from core.ingestion_utils import normalize_provider, normalize_source_type, ensure_scope_id
```

```
doc_metadata = doc.metadata or {}
...
scope_id = ensure_scope_id(doc_source_type, doc_metadata)

file_data = {
    ...
    "scope_id": scope_id,
    ...
    "metadata": doc_metadata,
}

process_file_task.s(
    ...
    scope_id=scope_id,
    ...
)
```

```
def process_file_task(
    self,
    user_id: str,
    job_id: str,
    file_data: Dict[str, Any],
    file_status_id: str,
    connector_type: str,
    scope_id: str,
    plan_code: Optional[str] = None,
):
    ...
    metadata = file_data.get("metadata") or {}
    if not isinstance(metadata, dict):
        metadata = {}
    if not scope_id:
        raise ValueError("scope_id is required for ingestion")
    metadata["scope_id"] = scope_id
```

```
def ingest_document_batched(...):
    ...
    metadata = metadata or {}
    scope_id = metadata.get("scope_id")
    doc_data = {
        ...
        "metadata": metadata,
        "scope_id": scope_id,
        ...
    }
```

---

### Test Updates (to satisfy new required `scope_id`)

**Files updated**
- `backend/tests/unit/test_worker_tasks_pipeline.py`
- `backend/tests/unit/test_worker_tasks_missing.py`
- `backend/tests/unit/test_worker_tasks_additional.py`
- `backend/tests/unit/test_worker_progress.py`
- `backend/tests/unit/test_unified_ingest_task.py`

**What changed**
- Added `scope_id` argument to all direct calls of `process_file_task`.
- Ensured `SourceDocument.metadata` in test fixtures contains minimum identifiers required by `build_scope_uri` (e.g., `storage_path` for file uploads, drive metadata for GDrive, workspace/page for Notion).

**Examples**
```
scope_id = "file_upload://file.txt"
result = tasks.process_file_task._orig_run.__func__(
    task, "user-1", "job-1", file_data, "status-1", "file_upload", scope_id
)
```

```
yield SourceDocument(
    content=b"PDF content",
    metadata={"storage_path": storage_path},
    source_type=SourceType.FILE_UPLOAD,
    ...
)
```

```
metadata={
    "file_id": file_id,
    "drive_id": "drive-1",
    "folder_id": "folder-1",
    "name": f"{file_id}.txt",
}
```

---

### Constraints Observed
- Only Steps 1–3 were implemented.
- No chat/RAG retrieval logic was changed.
- No connector logic was rewritten; scope URIs are enforced at ingestion time via metadata.

---

### Rationale and Design Notes

- **Canonical URI primary key**: Using the URI itself as `scope_identities.id` prevents duplicate representations of the same scope and makes collision handling deterministic.
- **RLS ownership**: Policies mirror existing patterns (`user_id = auth.uid()`) to avoid cross-tenant leakage while keeping worker/service-role access unblocked by default patterns.
- **Foreign key on `documents.scope_id`**: Maintains referential integrity and enables cascade cleanup when a scope is removed.
- **Metadata-first scope injection**: Ensures downstream systems (parsers, chunkers, embedders) receive consistent scope context without altering connector interfaces.
- **Centralized scope builder**: Eliminates connector-specific drift and supports strict enforcement by raising `ValueError` on malformed metadata.

---

### Diagrams

**Data model (schema-level)**
```
scope_identities
  id (TEXT, PK, canonical URI)
  user_id (UUID)
  type (TEXT)
  attributes (JSONB)
  summary (TEXT)
  file_tree (TEXT)
  last_ingested_at (TIMESTAMPTZ)
  created_at / updated_at

documents
  id (UUID)
  ...
  scope_id (TEXT, FK -> scope_identities.id, ON DELETE CASCADE)
  metadata (JSONB with scope_id)
```

**Ingestion flow (Phase 1 scope injection)**
```
Connector -> SourceDocument(metadata)
             |
             v
     ensure_scope_id()  --> scope_id injected into metadata
             |
             v
process_file_task(scope_id, metadata)
             |
             v
ingest_document_batched() -> documents.scope_id set
```

---

### Rollout Checklist (Phase 1)

- [ ] Apply migration `20260116000004_scope_identities.sql` to staging.
- [ ] Verify `scope_identities` table exists with RLS enabled and policies active.
- [ ] Verify `documents.scope_id` column exists and FK constraint is enforced.
- [ ] Backfill plan for existing documents (if needed) documented separately.
- [ ] Deploy backend with `build_scope_uri` + `ensure_scope_id`.
- [ ] Validate ingestion on one connector per type (GitHub, S3, Box, Drive, Notion, Web, File Upload).
- [ ] Confirm scope_id is present in `documents` rows and metadata.
- [ ] Run unit tests for worker ingestion pipeline.
- [ ] Monitor ingestion errors for `ValueError` (missing metadata fields).

---

### Known Gaps / Future Steps (Out of Scope for Phase 1)

- No scope identity document generation (Step 4+).
- No retrieval-time filtering or ambiguity handling (chat layer unchanged).
- No UI integration for listing scopes.

---

### Operational Notes

- **Backfill strategy (optional)**: If existing documents predate scope_id, decide whether to:
  - (a) leave scope_id NULL and handle in retrieval later, or
  - (b) run a backfill job that maps metadata to canonical URIs.
- **Monitoring**: Watch for ingestion failures due to missing metadata required by `build_scope_uri` (e.g., missing `workspace_id` for Notion).

---

### Files Touched (Index)
- `supabase/migrations/20260116000004_scope_identities.sql` (new)
- `backend/core/scopes.py` (new)
- `backend/core/ingestion_utils.py` (updated)
- `backend/worker/tasks.py` (updated)
- `backend/tests/unit/test_worker_tasks_pipeline.py` (updated)
- `backend/tests/unit/test_worker_tasks_missing.py` (updated)
- `backend/tests/unit/test_worker_tasks_additional.py` (updated)
- `backend/tests/unit/test_worker_progress.py` (updated)
- `backend/tests/unit/test_unified_ingest_task.py` (updated)

---

## Phase 2 — Connector Compliance & Identity Synthesis (Steps 4–6)

### Step 4 — Connector Compliance Updates

**GitHub (`backend/connectors/github.py`)**
- Injected `branch` into metadata for both single-file and folder expansion yields.
- Ensures `build_scope_uri` has `repository` + `branch` consistently.

**S3 (`backend/connectors/s3.py`)**
- Injected normalized `prefix` into metadata for every `SourceDocument`.
- Ensures `build_scope_uri` has `bucket` + `prefix` even when item IDs are keys.

**Box (`backend/connectors/box.py`)**
- Added folder-name resolution with caching to guarantee `folder_name` for scope URIs.
- Injected `folder_id` + `folder_name` into metadata for every file.

### Step 5 — Identity Service

**File created**
- `backend/services/scope_identity.py`

**What it does**
- Computes file statistics and extensions.
- Builds a bounded ASCII tree (max depth 3, max children 10).
- Creates the narrative identity card text.
- Updates `scope_identities` with summary, file_tree, attributes, and timestamps.
- Upserts an identity document into `documents` + `document_chunks` with embeddings.

### Step 6 — Worker Integration

**File updated**
- `backend/worker/tasks.py`

**Integration point**
- `finalize_job_task` now synthesizes identity cards after all documents in a job are completed and before the job status is set to completed.
- Documents are gathered via `ingestion_file_status` → `documents` lookup and grouped by `scope_id`.

### Phase 2 Files Touched (Index)
- `backend/connectors/github.py` (updated)
- `backend/connectors/s3.py` (updated)
- `backend/connectors/box.py` (updated)
- `backend/services/scope_identity.py` (new)
- `backend/worker/tasks.py` (updated)

---

## Phase 3 — Retrieval & Chat Intelligence (Steps 7–9)

### Step 7 — Scope-Aware Hybrid Search

**Migration created**
- `supabase/migrations/20260116000005_hybrid_search_scoped.sql`

**What changed**
- `hybrid_search` function now returns `scope_id` column for each chunk.
- New `hybrid_search_scoped` function accepts `filter_scope_ids TEXT[]` for explicit scope filtering.
- Both functions include `scope_id` in semantic and keyword result CTEs.

**Key SQL excerpt**
```sql
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    document_id UUID,
    chunk_index INT,
    source_type TEXT,
    scope_id TEXT,           -- NEW: Canonical scope URI
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
-- ... implementation includes d.scope_id in all CTEs
```

**Service created**
- `backend/services/scope_analysis.py`

**Public API**
- `analyze_scope_distribution(docs) -> ScopeAnalysisResult`
  - Groups documents by `scope_id`
  - Calculates dominance ratio: `primary_scope_count / total_scoped_docs`
  - Returns classification: `DOMINANT (≥85%)`, `CONTESTED (60-84%)`, `FRAGMENTED (<60%)`, `EMPTY`
- `get_scope_candidates_for_clarification(analysis) -> List[dict]`
  - Extracts candidate scopes for HTTP 300 response
- `filter_docs_by_scope(docs, scope_id) -> List[dict]`
  - Filters documents to single scope

**Classification thresholds (configurable)**
```python
DOMINANCE_THRESHOLD = 0.85  # ≥85% = DOMINANT
CONTESTED_THRESHOLD = 0.60  # 60-84% = CONTESTED, <60% = FRAGMENTED
MIN_SCORE_FOR_ANALYSIS = 0.3  # Ignore low-relevance docs
```

**Search API updated**
- `backend/api/v1/search.py`

**Changes**
- Added optional `scope_ids` filter parameter
- Added `include_scope_analysis` parameter
- Response includes `ScopeAnalysis` with distribution stats

---

### Step 8 — Dominance Guard (Chat Intelligence)

**File updated**
- `backend/api/v1/chat.py`

**New request/response models**
```python
class ChatRequest(BaseModel):
    # ... existing fields ...
    scope_id: Optional[str] = Field(None, description="Explicit scope selection")

class ClarificationResponse(BaseModel):
    action: str = "clarify_scope"
    message: str
    candidates: List[ScopeCandidate]
    query: str

class ScopeContext(BaseModel):
    scope_id: str
    scope_name: Optional[str]
    scope_type: Optional[str]
    dominance_ratio: float
    classification: str

class ChatResponse(BaseModel):
    # ... existing fields ...
    scope_context: Optional[ScopeContext] = None  # NEW
```

**Dominance Guard flow (Step 9 in chat endpoint)**
```
Retrieve docs
    │
    ▼
analyze_scope_distribution(docs)
    │
    ├─ DOMINANT (≥85%) ──────► Filter to primary scope
    │                          └─► Proceed with scoped prompt + footnote
    │
    ├─ CONTESTED (60-84%) ───► Proceed with all docs
    │                          └─► Add scope footnote
    │
    └─ FRAGMENTED (<60%) ────► Return HTTP 300
                               └─► ClarificationResponse with candidates
```

**HTTP 300 Response format**
```json
{
  "action": "clarify_scope",
  "message": "I found relevant information across multiple sources...",
  "candidates": [
    {"id": "github://org/repo@main", "summary": "Backend API...", "type": "github_repo"},
    {"id": "s3://bucket/docs/", "summary": "Product manuals...", "type": "s3_bucket"}
  ],
  "query": "original user query"
}
```

---

### Step 9 — Scoped System Prompt

**Prompt templates**

Standard prompt (unchanged for non-scoped queries):
```
SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant...
## KNOWLEDGE BASE CONTEXT:
{context}
"""
```

Scoped prompt (used when scope is identified):
```
SCOPED_SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant...

## SCOPE CONTEXT
You are answering questions specifically about:
{scope_identity}

## Your Role
- Answer questions using ONLY the provided context documents from this scope
- When citing, mention the source is from "{scope_name}" when relevant
...

## KNOWLEDGE BASE CONTEXT (from {scope_name}):
{context}
"""
```

**Identity injection helpers**
```python
def fetch_scope_identity(supabase, scope_id, user_id) -> Optional[dict]:
    """Fetch scope identity from scope_identities table."""

def build_scope_identity_context(scope_identity) -> str:
    """Build human-readable scope context for prompt injection."""

def extract_scope_name(scope_id) -> str:
    """Extract readable name from canonical URI."""
```

**Response footnote (for DOMINANT/CONTESTED)**
```
{answer}

---
*Answered based on context from **{scope_name}**.*
```

---

### Phase 3 Files Touched (Index)
- `supabase/migrations/20260116000005_hybrid_search_scoped.sql` (new)
- `backend/services/scope_analysis.py` (new)
- `backend/api/v1/search.py` (updated)
- `backend/api/v1/chat.py` (updated)

---

### Phase 3 Rollout Checklist

- [ ] Apply migration `20260116000005_hybrid_search_scoped.sql` to staging
- [ ] Verify `hybrid_search` returns `scope_id` in results
- [ ] Verify `hybrid_search_scoped` filters correctly
- [ ] Test scope analysis with multi-scope retrieval
- [ ] Test HTTP 300 response for FRAGMENTED classification
- [ ] Test scoped prompt injection for DOMINANT/CONTESTED
- [ ] Verify footnote appears in responses
- [ ] Test explicit `scope_id` parameter in ChatRequest
- [ ] Monitor clarification rate (target: 10-15% of queries)

---

### Phase 3 Design Decisions

1. **HTTP 300 for clarification**: Using 300 Multiple Choices (not 200 with flag) ensures frontend must explicitly handle ambiguity. This prevents silent UX degradation.

2. **85% dominance threshold**: Aggressive threshold minimizes user friction. Only truly fragmented queries (3+ competing scopes) trigger clarification.

3. **Scope footnote vs. inline**: Footnote approach keeps answer clean while maintaining transparency. Users see scope context without cognitive overhead.

4. **Fallback to standard search**: If `hybrid_search_scoped` fails, system falls back to `match_documents`. Scope analysis degrades gracefully.

5. **No sticky scope in Phase 3**: Conversation-level scope memory deferred to Phase 4 to reduce initial complexity.

---

### Known Limitations (Phase 3)

- No automatic scope locking across conversation turns
- No UI components for scope selection (frontend work needed)
- No scope-level re-ranking by hints/languages (Phase 4)
- Identity documents may be stale if ingestion runs before synthesis

---

### Metrics to Monitor

| Metric | Target | Measurement |
|--------|--------|-------------|
| DOMINANT classification rate | 60-70% | `scope_analysis.classification == "dominant"` |
| CONTESTED classification rate | 15-25% | `scope_analysis.classification == "contested"` |
| FRAGMENTED (clarification) rate | 10-15% | HTTP 300 responses |
| Scoped retrieval latency (P95) | <300ms | Time from search to response |
| Scope identity hit rate | >90% | `fetch_scope_identity` returns data |

---

## Phase 4 — Frontend UI (Steps 10–12)

### Step 10 — Type Definitions

**File updated**
- `frontend-new/types/index.ts`

**New types added**
```typescript
// Scope context metadata returned by the backend
export interface ScopeContext {
    scope_id: string;
    scope_name?: string;
    scope_type?: string;
    dominance_ratio: number;
    classification: 'dominant' | 'contested' | 'explicit' | string;
}

// Scope candidate for clarification response (HTTP 300)
export interface ScopeCandidate {
    id: string;
    summary?: string;
    type: string;
}

// Clarification response from backend (HTTP 300)
export interface ClarificationResponse {
    action: 'clarify_scope';
    message: string;
    candidates: ScopeCandidate[];
    query: string;
}

// Extended message type with scope awareness
export interface Message {
    id: string;
    role: 'user' | 'assistant' | 'system' | 'clarification';
    content: string;
    // ... existing fields ...
    scope_context?: ScopeContext;
    candidates?: ScopeCandidate[];
    original_query?: string;
}
```

---

### Step 11 — Chat Utilities (HTTP 300 Handling)

**File updated**
- `frontend-new/lib/chat-utils.ts`

**New capabilities**
- `sendChatRequest()` - Non-streaming chat with HTTP 300 handling
- `streamChatResponse()` - Updated to yield `clarification` events
- Scope utility functions: `getScopeIcon()`, `getScopeTypeName()`, `extractScopeName()`

**ChatPayload extended**
```typescript
export interface ChatPayload {
    query: string;
    conversation_id: string | null;
    history: { role: string; content: string }[];
    model: ModelId;
    scope_id?: string;  // NEW: explicit scope selection
}
```

**StreamEvent extended**
```typescript
export type StreamEvent =
    | { type: 'token'; content: string }
    | { type: 'sources'; sources: unknown[] }
    | { type: 'scope_context'; scope_context: ScopeContext }  // NEW
    | { type: 'done'; message_id?: string }
    | { type: 'error'; message: string }
    | { type: 'clarification'; data: ClarificationResponse };  // NEW
```

**HTTP 300 handling in streamChatResponse**
```typescript
// Handle HTTP 300 Multiple Choices (clarification needed)
if (response.status === 300) {
    const clarification = await response.json() as ClarificationResponse;
    yield { type: 'clarification', data: clarification };
    return;
}
```

---

### Step 12 — UI Components

**New file: `frontend-new/components/chat/ClarificationCard.tsx`**

Displays when the backend returns HTTP 300 (Multiple Choices).

**Features**
- Amber-themed card with "Multiple contexts found" header
- Lists scope candidates with type-specific icons
- GitHub, S3, Box, Dropbox, Google Drive, Notion, Web icons
- Loading state when user selects a scope
- "Search all sources" fallback option

**Component structure**
```typescript
interface ClarificationCardProps {
    message: string;
    candidates: ScopeCandidate[];
    onSelectScope: (scopeId: string) => void;
    isLoading?: boolean;
    className?: string;
}
```

**New file: `frontend-new/components/chat/ScopeBadge.tsx`**

Displays scope context information on responses.

**Variants**
- `inline` - Compact badge for message headers
- `footer` - Full footer with scope details and confidence

**Component structure**
```typescript
interface ScopeBadgeProps {
    scopeContext: ScopeContext;
    variant?: "inline" | "footer";
    className?: string;
}
```

---

### Step 13 — Chat Page Integration

**File updated**
- `frontend-new/app/dashboard/chat/[chatId]/page.tsx`

**New state**
```typescript
const [isResending, setIsResending] = useState(false);
const [currentScopeId, setCurrentScopeId] = useState<string | null>(null);
```

**Updated message handling**
- `handleSendMessage(content, scopeId?)` - Now accepts optional scope
- Handles `clarification` event from stream
- Adds clarification messages to chat state

**New handler: `handleSelectScope`**
```typescript
const handleSelectScope = useCallback(async (scopeId: string, originalQuery: string) => {
    setIsResending(true);
    // Remove clarification message
    setMessages(prev => prev.filter(m => m.role !== 'clarification'));
    // Set sticky scope
    if (scopeId !== '__all__') setCurrentScopeId(scopeId);
    // Re-send with scope
    await handleSendMessage(originalQuery, scopeId);
    setIsResending(false);
}, [handleSendMessage]);
```

**Sticky scope behavior**
- `currentScopeId` persists across messages in conversation
- Automatically passed to subsequent queries
- Cleared on new conversation

**File updated**
- `frontend-new/components/chat/ChatArea.tsx`

**New props**
```typescript
interface ChatAreaProps {
    // ... existing props ...
    onSelectScope?: (scopeId: string, originalQuery: string) => void;
    isResending?: boolean;
}
```

**Clarification rendering**
```typescript
if (message.role === 'clarification' && message.candidates) {
    return (
        <ClarificationCard
            message={message.content}
            candidates={message.candidates}
            onSelectScope={(scopeId) => onSelectScope?.(scopeId, message.original_query)}
            isLoading={isResending}
        />
    );
}
```

---

### Phase 4 Files Touched (Index)

- `frontend-new/types/index.ts` (updated)
- `frontend-new/lib/chat-utils.ts` (updated)
- `frontend-new/hooks/useChatHistory.tsx` (updated)
- `frontend-new/components/chat/ClarificationCard.tsx` (new)
- `frontend-new/components/chat/ScopeBadge.tsx` (new)
- `frontend-new/components/chat/ChatArea.tsx` (updated)
- `frontend-new/app/dashboard/chat/[chatId]/page.tsx` (updated)

---

### Phase 4 Rollout Checklist

- [ ] Build frontend-new with no TypeScript errors
- [ ] Test clarification card renders on HTTP 300
- [ ] Test scope selection triggers re-query with scope_id
- [ ] Test "search all" option works
- [ ] Test sticky scope persists across messages
- [ ] Verify scope icons display correctly for each type
- [ ] Test loading state on ClarificationCard during re-send
- [ ] Verify MessageBubble still renders normally
- [ ] Test scope_context in streaming response

---

### Phase 4 UX Flow

```
User Query
    │
    ▼
Backend returns HTTP 300
    │
    ▼
┌────────────────────────────────────┐
│  🟡 Multiple contexts found        │
│                                    │
│  I found info in multiple sources. │
│  Please select one:                │
│                                    │
│  ┌────────────────────────────┐   │
│  │ 🐙 project-alpha           │   │
│  │    GitHub Repository       │   │
│  │    Backend API codebase... │   │
│  └────────────────────────────┘   │
│                                    │
│  ┌────────────────────────────┐   │
│  │ 📁 legacy-docs             │   │
│  │    S3 Bucket               │   │
│  │    Old product manuals...  │   │
│  └────────────────────────────┘   │
│                                    │
│  or search all sources             │
└────────────────────────────────────┘
    │
    ▼ (User clicks)
    │
Re-send query with scope_id
    │
    ▼
Normal response + scope footnote
```

---

### Phase 4 Design Decisions

1. **Clarification as message**: Treating clarification as a special message type (`role: 'clarification'`) keeps the chat flow natural. Users see it inline, not as a modal.

2. **Amber theming**: Clarification cards use amber colors to signal "action needed" without being alarming (red) or dismissive (gray).

3. **Sticky scope**: Once a scope is selected, it persists for the conversation. This implements the "conversation continuity" requirement from Phase 3 design.

4. **"Search all" fallback**: Users can bypass scope selection entirely. This respects user autonomy and handles edge cases.

5. **Loading on selection**: Shows immediate feedback when user clicks a scope, preventing double-clicks.

---

### Known Limitations (Phase 4)

- Sticky scope not persisted to database (session-only)
- No visual indicator of active scope in chat header
- ScopeBadge component created but not integrated into MessageBubble
- No scope filtering UI for manual scope selection before query

---

### Future Enhancements (Phase 5+)

1. **Scope selector in chat input**: Allow users to pre-select scope before querying
2. **Scope persistence**: Store `preferred_scope_id` in conversation metadata
3. **Scope indicator**: Show active scope badge in chat header
4. **Scope switching**: Allow changing scope mid-conversation
5. **Scope favorites**: Let users pin frequently-used scopes
