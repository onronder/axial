## Disambiguation Implementation Plan — Version 2.0

Incorporates Claude feedback: canonical URIs, first-class `scope_identities`, narrative identity documents, and explicit UX signals for ambiguity.

---

### 1) Canonical Scope URIs (Non-Negotiable “Law”)
- All connectors must emit `scope_id` using these exact URI formats:
  - GitHub: `github://{org}/{repo}@{branch}`
  - S3: `s3://{bucket}/{prefix}` (prefix may be empty but include trailing slash if representing a folder)
  - Box: `box://folder/{id}:{name}`
  - Dropbox: `dropbox://{namespace_id}/{root_path}`
  - Google Drive: `gdrive://{drive_id}:{name}` (for shared drives) or `gdrive://{drive_id}/{folder_id}:{name}`
  - Notion: `notion://{workspace_id}/{page_id}:{title}`
- Canonical URI builder (to be implemented in a shared utility, e.g., `backend/core/ingestion_utils.py` or `backend/services/scope_uri.py`) to prevent per-connector drift:
  ```python
  def build_scope_uri(
      source_type: str,
      *,
      org: str | None = None,
      repo: str | None = None,
      branch: str | None = None,
      bucket: str | None = None,
      prefix: str | None = None,
      folder_id: str | None = None,
      folder_name: str | None = None,
      namespace_id: str | None = None,
      root_path: str | None = None,
      drive_id: str | None = None,
      page_id: str | None = None,
      workspace_id: str | None = None,
      title: str | None = None,
  ) -> str:
      """Return canonical scope URI per connector, raising ValueError on missing pieces."""
  ```
- Enforce normalization rules inside the builder:
  - Lowercase connector prefixes; percent-encode spaces in names where applicable.
  - Strip duplicate slashes; ensure prefixes end with `/` when representing folders.
  - Validate branch defaults to `main` if absent (GitHub).
  - Preserve human-readable names in the URI suffix where defined (e.g., `:{name}`).

---

### 2) Data Model: `scope_identities` as a First-Class Table
- Purpose: Frontend lists “Active Sources”; backend enforces scope-level filtering and collision reporting.
- SQL migration (Postgres + Supabase, RLS-ready):
  ```sql
  CREATE TABLE scope_identities (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
      team_id UUID REFERENCES teams(id) ON DELETE CASCADE,

      -- Canonical scope identity
      scope_id TEXT NOT NULL,  -- canonical URI, e.g., github://org/repo@main
      scope_type TEXT NOT NULL, -- repository | bucket | folder | workspace | namespace
      scope_name TEXT NOT NULL, -- human-readable display
      provider TEXT NOT NULL,   -- github | s3 | box | dropbox | gdrive | notion
      scope_path TEXT,          -- optional subpath within the scope
      parent_scope_id TEXT,     -- optional for nested scopes

      -- State and lineage
      scope_version TEXT,       -- e.g., commit SHA, ingestion timestamp, etag
      first_ingested_at TIMESTAMPTZ DEFAULT now(),
      last_ingested_at TIMESTAMPTZ DEFAULT now(),
      document_count INTEGER DEFAULT 0,
      synthetic_document_id UUID, -- references documents(id) when created

      -- Optional narrative cache for UI speed
      summary_snippet TEXT,

      UNIQUE (user_id, scope_id)
  );

  -- Link documents to scopes (if column not present, add it)
  ALTER TABLE documents ADD COLUMN IF NOT EXISTS scope_id TEXT;
  CREATE INDEX IF NOT EXISTS idx_documents_scope_id ON documents(scope_id);

  -- Index for listing by team/user
  CREATE INDEX IF NOT EXISTS idx_scope_identities_team ON scope_identities(team_id, last_ingested_at DESC);

  -- RLS (supabase style)
  ALTER TABLE scope_identities ENABLE ROW LEVEL SECURITY;
  CREATE POLICY scope_identities_select ON scope_identities
    FOR SELECT USING (
      auth.uid() = user_id OR team_id IN (SELECT team_id FROM team_members WHERE user_id = auth.uid())
    );
  CREATE POLICY scope_identities_modify ON scope_identities
    FOR INSERT WITH CHECK (auth.uid() = user_id)
    USING (auth.uid() = user_id);
  CREATE POLICY scope_identities_update ON scope_identities
    FOR UPDATE USING (auth.uid() = user_id);
  ```
- Documents table remains backward compatible: `scope_id` also stored in `metadata` for existing code paths; relational column used for fast filtering and joins.

---

### 3) Identity Document (Narrative) Requirements
- One synthetic document per `scope_id`, stored in `documents` and referenced by `scope_identities.synthetic_document_id`.
- Content shape (textual narrative, not just stats):
  ```
  [SCOPE IDENTITY]
  Scope URI: <canonical scope_id>
  Name: <scope_name>
  Type: <scope_type> (repository | bucket | folder | workspace | namespace)
  Version: <scope_version or timestamp>
  Ingestion Window: <start → end timestamps>

  What this scope is:
  - One-sentence narrative (e.g., "Python backend using FastAPI and PostgreSQL, with CI in GitHub Actions.")

  Composition:
  - File counts and sizes by major type (code, docs, data)
  - Dominant languages / MIME types
  - Top directories or sections (depth 2–3 tree)

  Key modules / sections:
  - Bullet list of 5–10 notable paths with short descriptors

  Topics and systems:
  - 5–10 key topics (auth, billing, ETL, marketing, etc.)

  Guardrails:
  - Sensitivity hints (PII, secrets patterns) if detectors flagged any
  ```
- Generation point in pipeline:
  - After all chunking for a scope finishes, run an “identity synthesis” step inside the ingestion orchestrator (e.g., a post-hook in `backend/core/ingestion_utils.py` or per-connector job runner).
  - Inputs: inventory (paths, sizes, MIME), sample snippets (bounded), connector metadata.
  - Output: a single `SourceDocument` with `doc_kind="scope_identity"`, `is_scope_identity=true`, `scope_id` set, `embedding` optional (embed if short enough; otherwise store as text with searchable metadata).

---

### 4) Pipeline Integration Points
- Scope URI construction: use `build_scope_uri` in every connector before chunk emission; fail fast on malformed inputs.
- Chunk metadata: include `scope_id`, `scope_type`, `scope_name`, `scope_path`, `scope_version` in `document.metadata` and set `documents.scope_id`.
- Scope registration: upsert into `scope_identities` at ingestion start (to list “Active Sources” immediately) and update `last_ingested_at`, `document_count`, `synthetic_document_id` after identity doc creation.
- Identity document insertion: occurs in the ingestion finalize step (post-chunking) so it captures complete inventory stats.

---

### 5) Retrieval & Ambiguity UX Contracts
- Chat endpoint must surface collisions explicitly.
- Response schemas:
  - **200 OK (resolved scope or single-scope retrieval)**  
    ```json
    {
      "answer": "...",
      "sources": [{ "index": 1, "scope_id": "github://org/repo@main", "scope_name": "repo", ... }],
      "dominant_scope_id": "github://org/repo@main",
      "scopes_considered": ["github://org/repo@main"],
      "conversation_id": "...",
      "message_id": "..."
    }
    ```
  - **300 Multiple Choices (ambiguous, user should pick)**  
    ```json
    {
      "status": "multiple_scopes",
      "message": "Multiple plausible scopes match your query.",
      "candidate_scopes": [
        { "scope_id": "github://org/backend@main", "scope_name": "backend", "scope_type": "repository", "reason": "highest aggregate similarity" },
        { "scope_id": "s3://docs-bucket/current/", "scope_name": "Current Docs", "scope_type": "bucket", "reason": "contains matching manuals" }
      ],
      "request_id": "...",
      "conversation_id": "..."
    }
    ```
  - **400 Ambiguity (collision without safe auto-selection)**  
    ```json
    {
      "status": "ambiguous_scope",
      "message": "Context collides across scopes; please choose one.",
      "colliding_scopes": [
        { "scope_id": "github://org/backend@main", "scope_name": "backend", "top_docs": 4 },
        { "scope_id": "s3://docs-bucket/legacy/", "scope_name": "Legacy Manuals", "top_docs": 3 }
      ],
      "suggested_action": "Select a scope to continue",
      "request_id": "...",
      "conversation_id": "..."
    }
    ```
- Collision detection logic (chat service):
  - Group retrieved docs by `scope_id`.
  - If `len(unique_scopes) == 1`: proceed normally; include `dominant_scope_id`.
  - If >1: compute dominance ratio; if no scope ≥ threshold (e.g., 0.6 aggregate score), return 300/400 structure instead of blended answer.
  - Always return `candidate_scopes`/`colliding_scopes` with human-readable `scope_name` and `scope_type` for UI rendering.

---

### 6) Connector-Specific Notes (URI + identity hooks)
- GitHub: `github://{org}/{repo}@{branch}`; version = commit SHA; scope_path = subdir if partial ingest. Identity: derive languages from repo stats; include CI/CD hints if workflows exist.
- S3: `s3://{bucket}/{prefix}`; prefix normalized with trailing slash; version = ingestion timestamp or bucket etag; identity: MIME histogram, top prefixes.
- Box: `box://folder/{id}:{name}`; parent_scope_id allowed; identity: folder tree (depth ≤3) and file type counts.
- Dropbox: `dropbox://{namespace_id}/{root_path}`; identity: root path outline and doc types.
- Drive: `gdrive://{drive_id}:{name}` or with folder; identity: drive/folder outline, owners, doc types.
- Notion: `notion://{workspace_id}/{page_id}:{title}`; identity: page tree and database schemas (titles only for LLM prompt).

---

### 7) Migration & Rollout Steps
- Migration 1: add `scope_identities`, `documents.scope_id`, indexes, and RLS policies.
- Migration 2: retrofit connectors to use `build_scope_uri`; add validation tests.
- Migration 3: add identity synthesis step and link `synthetic_document_id`.
- Migration 4: update retrieval RPCs to accept `scope_id` filters and to return `scope_id` in results.
- Migration 5: implement collision handling responses (300/400) and UI contract.
- Migration 6: observability—log collisions, dominance ratios, and identity generation outcomes.

---

### 8) Minimal Test Matrix
- URI builder: unit tests per connector input → canonical URI string; invalid inputs raise `ValueError`.
- Ingestion: documents emitted with correct `scope_id`; `scope_identities` upserted; identity doc created and linked.
- Retrieval: RPC returns `scope_id`; chat returns 300/400 when collisions detected; single-scope path unchanged.
- RLS: ensure users cannot select/list scopes outside their team; `scope_identities` obey policies.
