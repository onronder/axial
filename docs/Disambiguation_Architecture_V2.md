# Universal Context Disambiguation Architecture V2.0
## Production-Ready Blueprint with Performance Optimizations

**Version:** 2.0  
**Date:** January 15, 2026  
**Authors:** Principal AI Solutions Architect (Strategic Vision) + Senior Performance Engineer (Technical Feedback)  
**Status:** Refined for Implementation

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 15, 2026 | Claude | Initial strategic analysis, UX flows, canonical URIs |
| 1.1 | Jan 15, 2026 | Codex | Performance critique, generated columns, dominance ratio, sticky scope |
| **2.0** | Jan 15, 2026 | Merged | Unified blueprint with all refinements |

---

## Executive Summary

This document merges the strategic UX vision (V1.0) with critical performance and friction-reduction feedback (V1.1) into a production-ready architecture. The key enhancements in V2.0 are:

1. **Dominance Guard**: Silent assumption when one scope dominates (≥85%) — no user friction
2. **Sticky Scope Sessions**: Conversation-level scope memory to prevent repeated clarifications
3. **Generated Columns**: Zero-JOIN retrieval path via denormalized `scope_id` column
4. **Rich Identity Metadata**: Machine-readable scope profiles for intelligent re-ranking

---

## 1. Problem Restatement (Unchanged from V1)

### The Context Flattening Failure

Current RAG retrieval (`backend/api/v1/chat.py` Step 8/9) selects top-N vectors by similarity and sends mixed scopes directly to generation. No grouping or filtering by source identity leads to **cross-project contamination**.

**The Heat Pump Paradox Example:**
- User query: *"How do I configure authentication?"*
- Retrieved: Python backend code + 5-year-old PDF manual + marketing brochure + React hooks
- Result: Incoherent answer mixing deprecated instructions with current code and sales language

### Root Cause (Three Levels)

| Level | Current State | Required State |
|-------|--------------|----------------|
| **Ingestion** | `source_type` only | `scope_id` + `scope_type` + `scope_hints` |
| **Storage** | JSONB metadata, no indexing | Generated column + B-tree index |
| **Retrieval** | Filter by `user_id` only | Filter by `scope_id`, group-by-scope aggregation |

---

## 2. Universal Scope Taxonomy (Refined)

### 2.1 Canonical Scope Identifiers

| Connector | Scope Type | Canonical Format | Example |
|-----------|------------|------------------|---------|
| **GitHub** | `repository` | `github://{owner}/{repo}@{branch}` | `github://acme/backend-v2@main` |
| **S3** | `bucket_prefix` | `s3://{bucket}/{prefix}` | `s3://docs-bucket/manuals/current/` |
| **Box** | `box_folder` | `box://{folder_id}:{folder_name}` | `box://12345:Marketing 2024` |
| **Dropbox** | `dropbox_folder` | `dropbox://{namespace_id}/{path}` | `dropbox://ns789/Team/Engineering` |
| **Drive** | `drive_folder` | `gdrive://{drive_id}/{folder_id}:{name}` | `gdrive://0AG/abc:Product Docs` |
| **Notion** | `notion_space` | `notion://{workspace_id}/{page_id}:{title}` | `notion://ws1/pg2:Engineering Wiki` |

### 2.2 Unified Scope Metadata Schema (V2 Enhanced)

```typescript
interface ScopeMetadata {
  // === CORE IDENTIFIERS (Required) ===
  scope_type: "repository" | "bucket_prefix" | "box_folder" | "dropbox_folder" | "drive_folder" | "notion_space";
  scope_id: string;           // Canonical URI (e.g., "github://acme/backend@main")
  scope_name: string;         // Human-readable (e.g., "Backend V2")
  
  // === HIERARCHICAL CONTEXT ===
  scope_path?: string;        // Path within scope (e.g., "/src/auth/")
  parent_scope_id?: string;   // For nested scopes (monorepos, subfolder structures)
  
  // === VERSION TRACKING (NEW in V2) ===
  scope_version?: string;     // Git SHA, timestamp, or sync marker
  scope_last_sync?: string;   // ISO timestamp of last successful sync
  
  // === SEMANTIC HINTS (NEW in V2 - Critical for Re-ranking) ===
  scope_hints: string[];      // Keywords: ["python", "authentication", "microservices"]
  scope_content_type: "source_code" | "documentation" | "data" | "marketing" | "mixed";
  primary_languages?: string[]; // ["python", "typescript"] for code repos
  
  // === STATISTICS (For Identity Document) ===
  file_count?: number;
  total_size_bytes?: number;
}
```

### 2.3 Why `scope_hints` Matters (Codex Insight)

The `scope_hints` field enables **semantic re-ranking** without reading document content:

| Scenario | Without Hints | With Hints |
|----------|---------------|------------|
| Query: "Python config" | All scopes equal | Boost scopes with `["python"]` hint |
| Query: "Authentication setup" | Random mix | Prefer `["authentication", "auth"]` hints |
| Query: "2024 marketing materials" | S3/Box equal | Boost `["marketing", "2024"]` hints |

**Generation Strategy:**
- **GitHub**: Extract from file extensions, directory names, README keywords
- **S3/Box/Drive**: Extract from filenames, folder names, MIME type clusters
- **Notion**: Extract from page titles, database column names

---

## 3. The Dominance Guard (V2 Key Innovation)

### 3.1 The Friction Problem (Codex Critique)

V1 proposed asking for clarification whenever multiple scopes appeared. This creates **unnecessary friction** when one scope clearly dominates.

### 3.2 The Dominance Heuristic Solution

```
DECISION FLOWCHART: Scope Collision Handling

┌─────────────────────────────────────────────────────────────┐
│                  Retrieve Top-N Documents                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Group by scope_id, calculate dominance ratio         │
│         dominance_ratio = count(primary_scope) / total       │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │  ≥ 0.85    │   │ 0.60-0.84  │   │  < 0.60    │
     │ DOMINANT   │   │ CONTESTED  │   │ FRAGMENTED │
     └────────────┘   └────────────┘   └────────────┘
              │               │               │
              ▼               ▼               ▼
     ┌────────────┐   ┌────────────┐   ┌────────────┐
     │  SILENT    │   │ ANNOTATED  │   │  CLARIFY   │
     │  ASSUME    │   │  ANSWER    │   │   REQUEST  │
     │            │   │            │   │            │
     │ Answer from│   │ Answer with│   │ List scopes│
     │ primary    │   │ "Based on  │   │ and ask    │
     │ scope only │   │ [Scope]"   │   │ user to    │
     │            │   │ footnote   │   │ choose     │
     │ + footnote │   │            │   │            │
     │ "Answered  │   │ + show     │   │            │
     │ based on   │   │ secondary  │   │            │
     │ [Scope]"   │   │ sources    │   │            │
     └────────────┘   └────────────┘   └────────────┘
```

### 3.3 Dominance Ratio Thresholds

| Ratio | Classification | User Experience | System Behavior |
|-------|----------------|-----------------|-----------------|
| **≥ 0.85** | DOMINANT | No friction | Use primary scope only, add footnote |
| **0.60 - 0.84** | CONTESTED | Minimal friction | Answer from primary, show secondary sources explicitly |
| **< 0.60** | FRAGMENTED | Clarification | Ask user to select scope or search all |

### 3.4 Dominance Analysis Logic (V2 Refined)

```
ALGORITHM: analyze_scope_dominance(retrieved_docs)

INPUT: List of documents with scope_id and relevance_score
OUTPUT: DominanceAnalysis {
  primary_scope: string | null,
  dominance_ratio: float,
  classification: "DOMINANT" | "CONTESTED" | "FRAGMENTED",
  secondary_scopes: List[{scope_id, count, aggregate_score}],
  recommended_action: "SILENT_ASSUME" | "ANNOTATED_ANSWER" | "CLARIFY"
}

STEPS:
1. Filter to high-relevance docs (score ≥ 0.5) — ignore low-quality noise
2. Group remaining docs by scope_id
3. For each scope, compute:
   - doc_count: number of documents
   - aggregate_score: sum of individual scores (or weighted by position)
4. Sort scopes by aggregate_score DESC
5. Calculate dominance_ratio = primary_scope.doc_count / total_high_relevance_docs
6. Apply threshold rules:
   - If dominance_ratio ≥ 0.85 → DOMINANT → SILENT_ASSUME
   - If dominance_ratio ∈ [0.60, 0.85) → CONTESTED → ANNOTATED_ANSWER
   - If dominance_ratio < 0.60 → FRAGMENTED → CLARIFY
7. If sticky_scope is set in conversation AND sticky_scope in top-3 scopes:
   - Override to SILENT_ASSUME with sticky_scope as primary
```

### 3.5 User-Facing Footnotes

**DOMINANT (Silent Assume):**
```
[Answer content here...]

---
ℹ️ *Answered based on context from **Backend V2** (GitHub repository).*
```

**CONTESTED (Annotated Answer):**
```
Based on **Backend V2**:
[Primary answer content...]

---
📎 *Also found in: Product Manual (S3), Engineering Wiki (Notion)*
*Would you like information from these sources as well?*
```

**FRAGMENTED (Clarification Request):**
```
I found relevant information across multiple sources:

1. **Backend V2** (GitHub) - Python microservices code
2. **Product Manual** (S3) - Configuration documentation  
3. **Engineering Wiki** (Notion) - Internal setup guides

Which source would you like me to focus on? Or I can search all and clearly attribute each piece of information.
```

---

## 4. Sticky Scope: Conversation Continuity (V2 New Feature)

### 4.1 The Problem

If a user clarifies "I mean the Backend V2 repo" in message 3, message 4 should NOT ask again.

### 4.2 Solution: Conversation-Level Scope Memory

```
CONVERSATION STATE MODEL:

conversations table (existing):
  + preferred_scope_id: TEXT (nullable)
  + scope_locked_at: TIMESTAMPTZ (nullable)
  + scope_lock_reason: TEXT (nullable)  -- "user_explicit" | "dominance_auto" | "api_param"

SCOPE LOCKING TRIGGERS:
1. User explicitly selects scope from clarification options → scope_lock_reason = "user_explicit"
2. DOMINANT classification 3x in a row → scope_lock_reason = "dominance_auto"
3. API call includes scope_id parameter → scope_lock_reason = "api_param"

SCOPE UNLOCKING TRIGGERS:
1. User says "search all sources" or "forget scope" → clear preferred_scope_id
2. New ingestion job completes for user → soft-unlock (keep but don't force)
3. Conversation idle > 24 hours → auto-clear on next message
```

### 4.3 Chat Flow with Sticky Scope

```
MESSAGE PROCESSING FLOW:

1. Receive user message
2. Check conversation.preferred_scope_id:
   - If SET and scope exists → filter retrieval to this scope ONLY
   - If SET but scope deleted → clear and proceed normally
   - If NULL → proceed with full retrieval + dominance analysis
3. After retrieval:
   - If scope was locked → skip dominance analysis, use locked scope
   - If not locked → run dominance analysis
     - If DOMINANT for 3rd consecutive time → auto-lock to primary scope
4. Generate response with appropriate footnote
5. If user selects scope from clarification → UPDATE conversation SET preferred_scope_id = selected
```

### 4.4 API Extension for Scope Control

```
POST /api/v1/chat

Request Body (V2 Extended):
{
  "query": "How do I configure OAuth?",
  "conversation_id": "uuid",
  "scope_id": "github://acme/backend@main",  // NEW: Optional explicit scope
  "scope_mode": "strict" | "prefer" | "auto"  // NEW: How to apply scope_id
}

scope_mode behaviors:
- "strict": ONLY search this scope, error if no results
- "prefer": Search this scope first, fall back to all if no results  
- "auto": Ignore scope_id, use dominance analysis (default)

Response Body (V2 Extended):
{
  "answer": "...",
  "sources": [...],
  "scope_context": {                          // NEW: Scope transparency
    "primary_scope_id": "github://acme/backend@main",
    "primary_scope_name": "Backend V2",
    "dominance_ratio": 0.92,
    "classification": "DOMINANT",
    "secondary_scopes": ["s3://docs/manual/"],
    "scope_locked": true,
    "lock_reason": "user_explicit"
  }
}
```

---

## 5. Identity Documents (V2 Machine-Readable Format)

### 5.1 Purpose

Identity Documents serve as **scope-level summaries** for:
1. Answering "What's in this repo?" queries without retrieving all chunks
2. Providing scope metadata for dominance re-ranking
3. Enabling scope-level semantic search (find relevant scopes before documents)

### 5.2 Identity Document Schema (V2 Structured)

```
IDENTITY DOCUMENT STRUCTURE:

{
  // === IDENTIFICATION ===
  "doc_kind": "scope_identity",           // Marker for special handling
  "is_scope_identity": true,              // Boolean flag for filtering
  "scope_id": "github://acme/backend@main",
  "scope_name": "Backend V2",
  "scope_type": "repository",
  
  // === VERSION & FRESHNESS ===
  "scope_version": "abc123def",           // Git SHA or sync timestamp
  "generated_at": "2026-01-15T12:00:00Z",
  "valid_until": "2026-01-22T12:00:00Z",  // TTL for refresh
  "document_count": 342,                   // Docs in this scope
  
  // === STATISTICAL PROFILE ===
  "statistics": {
    "file_count": 127,
    "total_size_bytes": 4521984,
    "file_types": {
      ".py": 89,
      ".md": 12,
      ".yaml": 8,
      ".json": 18
    },
    "avg_doc_size_bytes": 35606
  },
  
  // === SEMANTIC PROFILE (For Re-ranking) ===
  "semantic": {
    "content_type": "source_code",
    "primary_languages": ["python"],
    "detected_frameworks": ["fastapi", "celery", "sqlalchemy"],
    "key_topics": ["authentication", "REST API", "background tasks", "database"],
    "hints": ["python", "backend", "microservices", "oauth", "celery", "fastapi"]
  },
  
  // === STRUCTURAL MAP ===
  "structure": {
    "top_directories": [
      {"path": "/api/", "file_count": 24, "purpose": "REST endpoints"},
      {"path": "/core/", "file_count": 18, "purpose": "Core utilities"},
      {"path": "/services/", "file_count": 31, "purpose": "Business logic"},
      {"path": "/worker/", "file_count": 8, "purpose": "Background tasks"}
    ],
    "directory_tree": "api/\n  v1/\n    chat.py\n    ...\ncore/\n  config.py\n  ...",
    "key_files": [
      {"path": "README.md", "role": "documentation"},
      {"path": "api/v1/chat.py", "role": "main_endpoint"},
      {"path": "core/config.py", "role": "configuration"}
    ]
  },
  
  // === HUMAN SUMMARY (Optional, LLM-generated) ===
  "summary": {
    "description": "Python FastAPI backend for the Axial platform with OAuth2 authentication, Celery background workers, and PostgreSQL database integration.",
    "generated_by": "gpt-4o-mini",
    "generated_at": "2026-01-15T12:05:00Z"
  }
}
```

### 5.3 Identity Document Storage Options

**Option A: Separate Table (Recommended)**

```sql
CREATE TABLE scope_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    team_id UUID REFERENCES teams(id) ON DELETE CASCADE,
    
    -- Core Identity
    scope_id TEXT NOT NULL,
    scope_name TEXT NOT NULL,
    scope_type TEXT NOT NULL,
    scope_version TEXT,
    
    -- Statistics (denormalized for fast access)
    file_count INTEGER DEFAULT 0,
    document_count INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    file_types JSONB DEFAULT '{}',
    
    -- Semantic Profile (V2 - Critical for re-ranking)
    content_type TEXT,                    -- source_code, documentation, data, mixed
    primary_languages TEXT[],             -- ["python", "typescript"]
    hints TEXT[],                         -- Searchable keywords
    key_topics TEXT[],                    -- Major themes
    
    -- Structure
    top_directories JSONB DEFAULT '[]',
    directory_tree TEXT,
    key_files JSONB DEFAULT '[]',
    
    -- Summary
    description TEXT,
    summary_generated_by TEXT,
    summary_generated_at TIMESTAMPTZ,
    
    -- Lifecycle
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,              -- TTL for refresh
    
    -- Embedding (for scope-level semantic search)
    embedding VECTOR(1536),
    
    CONSTRAINT unique_user_scope UNIQUE(user_id, scope_id)
);

-- Indexes for fast lookup
CREATE INDEX idx_scope_identities_user ON scope_identities(user_id);
CREATE INDEX idx_scope_identities_team ON scope_identities(team_id) WHERE team_id IS NOT NULL;
CREATE INDEX idx_scope_identities_type ON scope_identities(scope_type);
CREATE INDEX idx_scope_identities_hints ON scope_identities USING GIN(hints);
CREATE INDEX idx_scope_identities_languages ON scope_identities USING GIN(primary_languages);
```

**Option B: Store in Documents Table (Alternative)**

```sql
-- Mark identity docs with special fields
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS doc_kind TEXT DEFAULT 'content',
ADD COLUMN IF NOT EXISTS is_scope_identity BOOLEAN DEFAULT FALSE;

-- Index for fast identity doc lookup
CREATE INDEX idx_documents_identity ON documents(user_id, scope_id)
WHERE is_scope_identity = TRUE;
```

### 5.4 Identity Document Generation Triggers

| Trigger | Action | Generation Strategy |
|---------|--------|---------------------|
| Ingestion job completes | Create/Update identity | Heuristic (fast) |
| User explicitly requests | Regenerate identity | Heuristic + optional LLM |
| Identity TTL expires | Refresh if scope changed | Delta update or full regenerate |
| Scope deletion | Delete identity | Cascade delete |

---

## 6. Database Schema (V2 Optimized)

### 6.1 Performance-First Design (Codex Feedback Integrated)

**The Problem:** Joining `documents` with `scope_identities` on every vector search is slow.

**The Solution:** Denormalize `scope_id` as a **generated column** on `documents` for zero-JOIN retrieval.

### 6.2 Documents Table Enhancement

```sql
-- Migration: Add scope_id as indexed column
-- File: supabase/migrations/20260116000000_add_scope_columns.sql

-- Step 1: Add scope_id column (nullable initially for backfill)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS scope_id TEXT;

-- Step 2: Add scope_type column
ALTER TABLE documents  
ADD COLUMN IF NOT EXISTS scope_type TEXT;

-- Step 3: Add scope_name column (for display without JOIN)
ALTER TABLE documents
ADD COLUMN IF NOT EXISTS scope_name TEXT;

-- Step 4: Create composite index for scoped retrieval (CRITICAL for performance)
CREATE INDEX IF NOT EXISTS idx_documents_user_scope
ON documents(user_id, scope_id)
WHERE scope_id IS NOT NULL;

-- Step 5: Create partial index for team-based scoped retrieval
CREATE INDEX IF NOT EXISTS idx_documents_team_scope
ON documents(team_id, scope_id)
WHERE team_id IS NOT NULL AND scope_id IS NOT NULL;

-- Step 6: Add index on scope_type for filtered queries
CREATE INDEX IF NOT EXISTS idx_documents_scope_type
ON documents(user_id, scope_type)
WHERE scope_type IS NOT NULL;

COMMENT ON COLUMN documents.scope_id IS 'Canonical scope URI (e.g., github://owner/repo@branch). Denormalized for zero-JOIN retrieval.';
COMMENT ON COLUMN documents.scope_type IS 'Scope classification (repository, bucket_prefix, box_folder, etc.)';
COMMENT ON COLUMN documents.scope_name IS 'Human-readable scope name for display without JOIN.';
```

### 6.3 Conversations Table Enhancement (Sticky Scope)

```sql
-- Migration: Add scope tracking to conversations
-- File: supabase/migrations/20260116000001_conversation_scope.sql

ALTER TABLE conversations
ADD COLUMN IF NOT EXISTS preferred_scope_id TEXT,
ADD COLUMN IF NOT EXISTS scope_locked_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS scope_lock_reason TEXT;

-- Constraint for valid lock reasons
ALTER TABLE conversations
ADD CONSTRAINT valid_scope_lock_reason 
CHECK (scope_lock_reason IS NULL OR scope_lock_reason IN ('user_explicit', 'dominance_auto', 'api_param'));

CREATE INDEX IF NOT EXISTS idx_conversations_scope
ON conversations(user_id, preferred_scope_id)
WHERE preferred_scope_id IS NOT NULL;

COMMENT ON COLUMN conversations.preferred_scope_id IS 'Sticky scope for conversation continuity. Set via user selection or auto-lock.';
COMMENT ON COLUMN conversations.scope_lock_reason IS 'How the scope was locked: user_explicit, dominance_auto, or api_param.';
```

### 6.4 Backfill Strategy

```sql
-- Migration: Backfill scope_id from existing metadata
-- File: supabase/migrations/20260116000002_backfill_scopes.sql
-- IMPORTANT: Run in batches during low-traffic periods

-- GitHub documents
UPDATE documents
SET 
    scope_id = CONCAT('github://', metadata->>'repository', '@main'),
    scope_type = 'repository',
    scope_name = COALESCE(
        (metadata->>'repository')::text,
        'Unknown Repository'
    )
WHERE source_type = 'github'
  AND scope_id IS NULL
  AND metadata ? 'repository';

-- S3 documents (already have canonical s3:// format in source_id)
UPDATE documents
SET 
    scope_id = CASE 
        WHEN source_id LIKE 's3://%' THEN 
            -- Extract bucket/prefix from s3://bucket/prefix/file.pdf
            regexp_replace(source_id, '^(s3://[^/]+/[^/]*/?).*$', '\1')
        ELSE NULL
    END,
    scope_type = 'bucket_prefix',
    scope_name = COALESCE(metadata->>'bucket', 'S3 Bucket')
WHERE source_type = 's3'
  AND scope_id IS NULL;

-- Box documents
UPDATE documents
SET 
    scope_id = CONCAT('box://', COALESCE(metadata->>'parent_id', 'root')),
    scope_type = 'box_folder',
    scope_name = 'Box Folder'  -- Would need folder name lookup
WHERE source_type = 'box'
  AND scope_id IS NULL;

-- Google Drive documents
UPDATE documents
SET 
    scope_id = CONCAT('gdrive://', COALESCE(metadata->>'parent_id', metadata->>'file_id', 'root')),
    scope_type = 'drive_folder',
    scope_name = 'Google Drive'
WHERE source_type = 'google_drive'
  AND scope_id IS NULL;

-- Dropbox documents
UPDATE documents
SET 
    scope_id = CONCAT('dropbox://', COALESCE(metadata->>'dropbox_id', metadata->>'path', 'root')),
    scope_type = 'dropbox_folder',
    scope_name = 'Dropbox Folder'
WHERE source_type = 'dropbox'
  AND scope_id IS NULL;

-- Notion documents
UPDATE documents
SET 
    scope_id = CONCAT('notion://', COALESCE(metadata->>'page_id', 'root')),
    scope_type = 'notion_space',
    scope_name = COALESCE(metadata->>'title', 'Notion Page')
WHERE source_type = 'notion'
  AND scope_id IS NULL;
```

### 6.5 Enhanced hybrid_search_scoped Function

```sql
-- Migration: Scope-aware hybrid search
-- File: supabase/migrations/20260116000003_hybrid_search_scoped.sql

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,      -- Optional: restrict to specific scopes
    filter_scope_types TEXT[] DEFAULT NULL,    -- Optional: restrict to scope types
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
    scope_id TEXT,
    scope_type TEXT,
    scope_name TEXT,
    title TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH semantic_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text,
            d.scope_id,
            d.scope_type,
            d.scope_name,
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND (filter_scope_types IS NULL OR d.scope_type = ANY(filter_scope_types))
          AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
        ORDER BY dc.embedding <=> query_embedding
        LIMIT match_count * 3
    ),
    keyword_results AS (
        SELECT 
            dc.id,
            dc.content,
            dc.document_id,
            dc.chunk_index,
            d.source_type::text,
            d.scope_id,
            d.scope_type,
            d.scope_name,
            d.title,
            d.metadata,
            ts_rank_cd(
                to_tsvector('english', dc.content), 
                plainto_tsquery('english', query_text),
                32
            )::FLOAT as score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(
                    to_tsvector('english', dc.content),
                    plainto_tsquery('english', query_text),
                    32
                ) DESC
            ) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
          AND (filter_scope_types IS NULL OR d.scope_type = ANY(filter_scope_types))
          AND to_tsvector('english', dc.content) @@ plainto_tsquery('english', query_text)
        ORDER BY score DESC
        LIMIT match_count * 3
    ),
    combined AS (
        SELECT 
            COALESCE(s.id, k.id) as id,
            COALESCE(s.content, k.content) as content,
            COALESCE(s.document_id, k.document_id) as document_id,
            COALESCE(s.chunk_index, k.chunk_index) as chunk_index,
            COALESCE(s.source_type, k.source_type) as source_type,
            COALESCE(s.scope_id, k.scope_id) as scope_id,
            COALESCE(s.scope_type, k.scope_type) as scope_type,
            COALESCE(s.scope_name, k.scope_name) as scope_name,
            COALESCE(s.title, k.title) as title,
            COALESCE(s.metadata, k.metadata) as metadata,
            COALESCE(s.score, 0)::FLOAT as vector_score,
            COALESCE(k.score, 0)::FLOAT as keyword_score,
            (
                vector_weight * COALESCE(1.0 / (60 + s.rank), 0) + 
                keyword_weight * COALESCE(1.0 / (60 + k.rank), 0)
            )::FLOAT as combined_score
        FROM semantic_results s
        FULL OUTER JOIN keyword_results k ON s.id = k.id
    )
    SELECT 
        c.id,
        c.content,
        c.document_id,
        c.chunk_index,
        c.source_type,
        c.scope_id,
        c.scope_type,
        c.scope_name,
        c.title,
        c.metadata,
        c.vector_score,
        c.keyword_score,
        c.combined_score
    FROM combined c
    ORDER BY c.combined_score DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;
```

---

## 7. Implementation Roadmap (V2 Sequenced)

### Phase 0: Schema Foundation (3-5 Days)
**Goal:** Database changes with zero downtime

| Task | Priority | Risk | Notes |
|------|----------|------|-------|
| Add `scope_id`, `scope_type`, `scope_name` columns | P0 | Low | ALTER TABLE, nullable |
| Create indexes | P0 | Low | CONCURRENTLY |
| Create `scope_identities` table | P0 | Low | New table |
| Add conversation scope columns | P0 | Low | ALTER TABLE |

### Phase 1: Ingestion Tagging (1 Week)
**Goal:** All new documents get scope metadata

| Task | Priority | Risk | Notes |
|------|----------|------|-------|
| GitHub connector scope injection | P0 | Low | Add to `_build_source_document` |
| S3 connector scope injection | P0 | Low | Extract from prefix |
| Box connector scope injection | P0 | Low | Use folder hierarchy |
| Dropbox connector scope injection | P0 | Low | Use namespace + path |
| Drive connector scope injection | P0 | Low | Use drive/folder IDs |
| Notion connector scope injection | P0 | Low | Use workspace + page |
| Worker task: persist scope to documents | P0 | Medium | Update INSERT logic |
| Backfill existing documents | P1 | Medium | Run in batches |

### Phase 2: Identity Documents (1 Week)
**Goal:** Scope-level summaries for navigation

| Task | Priority | Risk | Notes |
|------|----------|------|-------|
| Heuristic identity generator | P0 | Low | File types, structure |
| Identity generation in finalize_job | P0 | Low | End of ingestion |
| Identity refresh on re-sync | P1 | Low | Delta update |
| Optional LLM enhancement | P2 | Medium | Premium users only |

### Phase 3: Dominance Guard (1 Week)
**Goal:** Intelligent scope collision handling

| Task | Priority | Risk | Notes |
|------|----------|------|-------|
| `analyze_scope_dominance()` function | P0 | Medium | Core logic |
| DOMINANT path (silent assume) | P0 | Low | Easiest path |
| CONTESTED path (annotated answer) | P0 | Medium | Footnote generation |
| FRAGMENTED path (clarification) | P0 | Medium | Scope list generation |
| Integration with chat endpoint | P0 | Medium | Flow control |

### Phase 4: Sticky Scope (1 Week)
**Goal:** Conversation continuity

| Task | Priority | Risk | Notes |
|------|----------|------|-------|
| Store preferred_scope_id on clarification | P0 | Low | UPDATE conversation |
| Apply sticky scope in retrieval | P0 | Medium | Filter logic |
| Auto-lock after 3x dominance | P1 | Low | Counter tracking |
| Scope unlock commands | P1 | Low | "search all sources" |
| API scope_id parameter | P1 | Low | Request body extension |

### Phase 5: Rollout Strategy (1-2 Weeks)
**Goal:** Safe production deployment

| Stage | Duration | Behavior |
|-------|----------|----------|
| **Shadow Mode** | 3-5 days | Log scope analysis results, no user impact |
| **Soft Enforce** | 5-7 days | Show footnotes for DOMINANT, clarify for FRAGMENTED only |
| **Hard Enforce** | Ongoing | Full scope disambiguation active |

### Phase 6: Observability (Ongoing)
**Goal:** Monitor and tune

| Metric | Dashboard | Alert Threshold |
|--------|-----------|-----------------|
| Dominance ratio distribution | Histogram | < 50% DOMINANT = investigate |
| Clarification request rate | Counter | > 30% = threshold too strict |
| Scope lock conversions | Funnel | Low conversion = UX issue |
| Retrieval latency by scope count | P95/P99 | > 500ms = index issue |

---

## 8. Success Metrics (V2 Refined)

### 8.1 Quantitative Targets

| Metric | Baseline | V2 Target | Measurement |
|--------|----------|-----------|-------------|
| Cross-scope contamination | ~35% | < 5% | % queries with 3+ scopes in top-10 |
| Clarification request rate | 0% | 10-15% | % queries triggering FRAGMENTED |
| Silent assumption rate | 0% | 60-70% | % queries with DOMINANT classification |
| Annotated answer rate | 0% | 15-25% | % queries with CONTESTED classification |
| Scope lock adoption | N/A | > 40% | % multi-turn conversations with locked scope |
| Identity doc coverage | 0% | 100% | % scopes with identity document |
| Retrieval latency (P95) | ~200ms | < 250ms | With scope filtering |

### 8.2 Qualitative Targets

- Reduction in "confused mixed answer" support tickets
- Positive user feedback on scope footnotes ("helpful context")
- Increase in successful "summarize X" queries via identity docs
- Fewer "wrong source" feedback reports

---

## 9. Risk Mitigation (V2 Enhanced)

### 9.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope extraction fails for edge cases | Medium | Medium | Fallback to `scope_id = "unknown"`, log for review |
| Backfill corrupts data | High | Low | Run in transaction, test on staging, batch processing |
| Performance regression | Medium | Medium | Benchmark before/after, use EXPLAIN ANALYZE |
| Generated column index bloat | Low | Low | Monitor index size, consider partial indexes |

### 9.2 UX Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Over-clarification annoys users | High | Medium | 85% dominance threshold, sticky scope |
| Users don't understand scope concept | Medium | Medium | Clear UI labels, in-app education |
| Footnotes clutter responses | Low | Low | Collapsible/subtle design |
| Auto-lock frustrates users | Medium | Low | Easy unlock via "search all", visible indicator |

### 9.3 Operational Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Identity doc drift (stale data) | Medium | Medium | TTL-based refresh, regenerate on sync |
| Scope ID format changes | High | Low | Version scope URIs, migration strategy |
| Inconsistent scope assignment | Medium | Medium | Validation tests per connector, CI checks |

---

## 10. Appendix: File Change Index

### Backend Files to Modify

| File | Changes |
|------|---------|
| `backend/connectors/github.py` | Add `scope_id`, `scope_type`, `scope_name`, `scope_hints` to metadata |
| `backend/connectors/s3.py` | Add scope metadata, extract from prefix |
| `backend/connectors/box.py` | Add scope metadata, resolve folder hierarchy |
| `backend/connectors/dropbox.py` | Add scope metadata, use namespace |
| `backend/connectors/drive.py` | Add scope metadata, use drive/folder |
| `backend/connectors/notion.py` | Add scope metadata, use workspace/page |
| `backend/worker/tasks.py` | Persist scope columns, trigger identity generation |
| `backend/api/v1/chat.py` | Dominance analysis, sticky scope, API extensions |
| `backend/services/scope_analysis.py` | **NEW**: Dominance guard logic |
| `backend/services/scope_identity.py` | **NEW**: Identity document generation |

### Database Migrations

| File | Purpose |
|------|---------|
| `20260116000000_add_scope_columns.sql` | Add scope_id, scope_type, scope_name to documents |
| `20260116000001_conversation_scope.sql` | Add sticky scope to conversations |
| `20260116000002_backfill_scopes.sql` | Backfill existing documents |
| `20260116000003_hybrid_search_scoped.sql` | Scope-aware search function |
| `20260116000004_scope_identities.sql` | Create scope_identities table |

### Frontend Files to Modify

| File | Changes |
|------|---------|
| `components/chat/ChatMessage.tsx` | Render scope footnotes, clarification UI |
| `components/chat/ScopeSelector.tsx` | **NEW**: Scope selection component |
| `hooks/useChat.ts` | Handle scope_context in response |
| `types/chat.ts` | Add scope types to API contracts |

---

## 11. Conclusion

V2.0 of the Universal Context Disambiguation Architecture synthesizes strategic UX vision with critical performance optimizations. The key innovations are:

1. **Dominance Guard**: Eliminates friction for 60-70% of queries where one scope clearly dominates
2. **Sticky Scope Sessions**: Prevents repeated clarifications within a conversation
3. **Zero-JOIN Retrieval**: Denormalized scope columns enable fast scoped search
4. **Machine-Readable Identities**: Rich scope profiles enable intelligent re-ranking

The phased rollout (Shadow → Soft → Hard) ensures we can validate assumptions and tune thresholds before full enforcement. The architecture is designed to be **non-breaking** — existing functionality continues unchanged while scope awareness gradually activates.

---

*Document prepared by Principal AI Solutions Architect with Performance Engineering feedback*  
*Version 2.0 — Ready for Implementation Review*
