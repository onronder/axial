# Universal Context Disambiguation Architecture
## Strategic Blueprint for Scope-Aware Intelligence Layer

**Version:** 1.0  
**Date:** January 15, 2026  
**Author:** Principal AI Solutions Architect  
**Status:** Strategic Analysis Complete

---

## Executive Summary

The Axial platform has completed its V1 Foundation with 6 operational connectors (Box, Dropbox, Google Drive, S3, GitHub, Notion) verified by 2,800+ unit tests at a 98% pass rate. However, the system suffers from a critical limitation: **Context Flattening** — treating all ingested data as undifferentiated flat content, leading to catastrophic retrieval failures when users query across multiple data sources.

This document presents a comprehensive architectural blueprint for implementing a **Scope-Aware Intelligence Layer** that solves the "Heat Pump Paradox" and prevents context collisions during RAG retrieval.

---

## 1. The Diagnosis: Context Flattening Problem

### 1.1 Current Architecture Analysis

After examining the codebase, I can confirm the following architectural reality:

**Current Metadata Storage (from `backend/connectors/*.py`):**

```python
# GitHub Connector - backend/connectors/github.py:1116-1129
SourceDocument(
    metadata={
        "source": "github",
        "repository": repo,  # e.g., "owner/repo-name"
        "path": path,
        "git_blob_sha": sha,
    },
    source_type=SourceType.GITHUB,
    source_id=item_id,  # e.g., "owner/repo:sha:path/to/file.py"
    ...
)

# S3 Connector - backend/connectors/s3.py:616-628
SourceDocument(
    metadata={
        "source": "s3",
        "bucket": bucket,
        "key": key,
        "region": resolved.get("region"),
        "storage_class": storage_class,
    },
    source_type=SourceType.S3,
    source_id=f"s3://{bucket}/{key}",  # Deterministic ID
    ...
)

# Box Connector - backend/connectors/box.py:845-860
SourceDocument(
    metadata={
        "source": "box",
        "box_id": file_id,
        "sha1": metadata.get("sha1"),
        "parent_id": self._get_parent_id(metadata),
    },
    source_type=SourceType.BOX,
    source_id=f"box://file/{file_id}",  # Canonical format
    ...
)
```

**Current RAG Retrieval (from `backend/api/v1/chat.py:505-530`):**

```python
# The hybrid_search RPC blindly retrieves by semantic similarity
response = supabase.rpc("hybrid_search", {
    "query_text": search_query,
    "query_embedding": query_vector,
    "match_count": 10,
    "filter_user_id": user_id,  # ← Only filters by user, NOT by scope
    "vector_weight": 0.7,
    "keyword_weight": 0.3,
    "similarity_threshold": 0.25
}).execute()
```

### 1.2 The Heat Pump Paradox — Concrete Example

**Scenario:** An Enterprise user "Acme Corp" has ingested:

| Source | Scope | Content Type |
|--------|-------|--------------|
| GitHub | `acme/backend-v2` | Python microservices |
| GitHub | `acme/frontend-v3` | React TypeScript app |
| S3 | `docs-bucket/legacy/` | PDF manuals for deprecated product |
| S3 | `docs-bucket/current/` | PDF manuals for current product |
| Box | `Marketing 2024` | Sales brochures, PowerPoints |
| Notion | `Engineering Wiki` | Internal documentation |

**User Query:** *"How do I configure the authentication system?"*

**Current Behavior (FAILURE):**
```
Retrieved Chunks:
1. backend-v2/auth/config.py (score: 0.89) - OAuth2 setup code
2. legacy/UserManual_2019.pdf (score: 0.85) - "Configure auth settings in Admin Panel"
3. Marketing 2024/Security_Brochure.pptx (score: 0.83) - "Our authentication is enterprise-grade..."
4. frontend-v3/src/auth/hooks.ts (score: 0.81) - useAuth() React hook
5. Engineering Wiki/Onboarding (score: 0.79) - "Set up your dev environment..."
```

**LLM Receives:** A toxic cocktail of backend code, frontend hooks, marketing copy, a 5-year-old manual, and onboarding docs — all with similar semantic scores.

**LLM Output:** An incoherent response mixing deprecated instructions with current code and sales language.

### 1.3 Root Cause Analysis

The root cause is **missing scope awareness at three levels:**

1. **Ingestion Level:** Connectors inject `source_type` but NOT hierarchical scope identifiers
2. **Storage Level:** Documents table has `source_type` and `metadata` JSONB but no first-class `scope_id`
3. **Retrieval Level:** `hybrid_search` function filters only by `user_id`, not by semantic scope

---

## 2. Universal Scope Taxonomy

### 2.1 Scope Definition by Connector

| Connector | Scope Type | Scope Identifier Format | Example |
|-----------|-----------|------------------------|---------|
| **GitHub** | Repository + Branch | `github://{owner}/{repo}@{branch}` | `github://acme/backend-v2@main` |
| **S3** | Bucket + Prefix | `s3://{bucket}/{prefix}` | `s3://docs-bucket/current/` |
| **Box** | Top-Level Folder | `box://folder/{folder_id}:{name}` | `box://folder/123456:Marketing 2024` |
| **Dropbox** | Namespace + Root Path | `dropbox://{namespace_id}/{root_path}` | `dropbox://ns123456/Team/Engineering` |
| **Google Drive** | Shared Drive or Root Folder | `gdrive://{drive_id}:{name}` | `gdrive://0AGh...xyz:Product Docs` |
| **Notion** | Workspace + Top-Level Page | `notion://{workspace_id}/{page_id}:{title}` | `notion://ws123/pg456:Engineering Wiki` |

### 2.2 Unified `source_scope` Schema

```typescript
interface SourceScope {
  // Primary Identifiers (always required)
  scope_type: "repository" | "bucket" | "folder" | "workspace" | "namespace";
  scope_id: string;           // Canonical identifier (e.g., "github://owner/repo@branch")
  scope_name: string;         // Human-readable name (e.g., "Backend V2")
  
  // Hierarchical Context (optional)
  parent_scope_id?: string;   // For nested scopes
  scope_path?: string;        // Full path within scope (e.g., "/src/auth/")
  
  // Semantic Classification (optional, for Identity Document)
  scope_content_type?: "source_code" | "documentation" | "data" | "mixed";
  primary_language?: string;  // e.g., "python", "typescript"
  
  // Temporal Context
  scope_created_at?: string;  // When this scope was first ingested
  scope_last_synced?: string; // Last sync timestamp
}
```

### 2.3 Implementation for Each Connector

#### GitHub Connector Enhancement

```python
# backend/connectors/github.py - Enhanced SourceDocument creation

def _build_source_document(self, config, metadata) -> SourceDocument:
    repo = metadata.get("repository")
    branch = config.get("branch", "main")
    path = metadata.get("path", "")
    
    # Build hierarchical scope
    scope = {
        "scope_type": "repository",
        "scope_id": f"github://{repo}@{branch}",
        "scope_name": repo.split("/")[-1],  # Just repo name
        "scope_path": os.path.dirname(path),
        "scope_content_type": self._infer_content_type(path),
        "primary_language": self._detect_language(path),
    }
    
    return SourceDocument(
        metadata={
            **existing_metadata,
            "source_scope": scope,  # NEW: Inject scope
        },
        ...
    )

def _infer_content_type(self, path: str) -> str:
    if "/docs/" in path or path.endswith(".md"):
        return "documentation"
    if "/test" in path or path.startswith("test"):
        return "test_code"
    return "source_code"
```

#### S3 Connector Enhancement

```python
# backend/connectors/s3.py - Enhanced SourceDocument creation

def _build_source_document(self, config, obj_metadata) -> SourceDocument:
    bucket = config["bucket_name"]
    key = obj_metadata["key"]
    prefix = config.get("prefix", "")
    
    # Extract logical scope from prefix
    scope_name = self._extract_scope_name(prefix, key)
    
    scope = {
        "scope_type": "bucket",
        "scope_id": f"s3://{bucket}/{prefix}",
        "scope_name": scope_name,
        "scope_path": os.path.dirname(key),
        "scope_content_type": self._classify_content(key),
    }
    
    return SourceDocument(
        metadata={
            **existing_metadata,
            "source_scope": scope,
        },
        ...
    )

def _extract_scope_name(self, prefix: str, key: str) -> str:
    # Extract meaningful name from prefix
    # e.g., "documents/product-manuals/2024/" → "Product Manuals 2024"
    parts = prefix.strip("/").split("/")
    if len(parts) >= 2:
        return " ".join(p.replace("-", " ").replace("_", " ").title() for p in parts[-2:])
    return prefix.strip("/") or "Root"
```

#### Box Connector Enhancement

```python
# backend/connectors/box.py - Enhanced with scope tracking

def _fetch_folder_documents(self, config, folder_id, processed_ids):
    # Get folder metadata for scope info
    folder_meta = self._request(config, f"/folders/{folder_id}")
    folder_name = folder_meta.get("name", "Unknown")
    
    # Determine top-level scope (walk up to root or first level)
    root_scope = self._resolve_root_scope(config, folder_id)
    
    scope = {
        "scope_type": "folder",
        "scope_id": f"box://folder/{root_scope['id']}:{root_scope['name']}",
        "scope_name": root_scope["name"],
        "parent_scope_id": root_scope.get("parent_id"),
    }
    
    # Inject scope into all documents from this folder
    for doc in self._recursive_fetch(config, folder_id, scope):
        yield doc
```

---

## 3. The Meta-Summary Concept: Identity Documents

### 3.1 Problem: "Forest for the Trees"

When a user asks *"Summarize the backend repository"* or *"What's in my Marketing folder?"*, the system needs high-level understanding without retrieving every chunk.

### 3.2 Solution: Synthetic Identity Documents

Every scope should have a programmatically-generated "Identity Card" that serves as a navigational map.

#### 3.2.1 Identity Document Schema

```python
@dataclass
class ScopeIdentityDocument:
    """Synthetic document summarizing a scope's contents."""
    
    scope_id: str
    scope_name: str
    scope_type: str
    
    # Content Summary
    file_count: int
    total_size_bytes: int
    file_types: Dict[str, int]  # e.g., {"python": 45, "markdown": 12}
    
    # Structure Map
    directory_tree: str  # ASCII tree representation
    key_paths: List[str]  # Most important directories
    
    # Semantic Summary (optional, LLM-generated)
    description: Optional[str]  # "Python microservices backend with OAuth2 auth"
    key_topics: List[str]  # ["authentication", "REST API", "database models"]
    
    # Temporal
    first_ingested: datetime
    last_updated: datetime
    document_count: int  # Number of indexed documents
```

#### 3.2.2 Identity Document Generation Strategies

**Strategy A: File-Listing Heuristics (Fast, No LLM)**

```python
# backend/services/scope_identity.py

def generate_identity_document_heuristic(
    scope_id: str,
    documents: List[Document]
) -> ScopeIdentityDocument:
    """Generate identity doc using file metadata only (no LLM cost)."""
    
    # Aggregate file types
    file_types = defaultdict(int)
    paths = set()
    total_size = 0
    
    for doc in documents:
        ext = os.path.splitext(doc.filename)[1].lower()
        file_types[ext] += 1
        paths.add(doc.metadata.get("source_scope", {}).get("scope_path", "/"))
        total_size += doc.file_size_bytes or 0
    
    # Build directory tree
    tree = build_ascii_tree(sorted(paths))
    
    # Identify key paths (most files)
    key_paths = sorted(paths, key=lambda p: -count_files_in_path(p, documents))[:5]
    
    return ScopeIdentityDocument(
        scope_id=scope_id,
        file_count=len(documents),
        total_size_bytes=total_size,
        file_types=dict(file_types),
        directory_tree=tree,
        key_paths=key_paths,
        description=None,  # Not generated
        key_topics=[],
    )
```

**Strategy B: LLM-Enhanced Summary (Higher Quality, Cost)**

```python
async def generate_identity_document_llm(
    scope_id: str,
    documents: List[Document],
    sample_size: int = 20
) -> ScopeIdentityDocument:
    """Generate identity doc with LLM-powered semantic summary."""
    
    # First, get heuristic base
    identity = generate_identity_document_heuristic(scope_id, documents)
    
    # Sample representative documents for LLM analysis
    samples = sample_representative_documents(documents, sample_size)
    
    # Build prompt for summarization
    prompt = f"""Analyze this collection of {identity.file_count} documents from scope "{identity.scope_name}".

File Types: {json.dumps(identity.file_types)}
Directory Structure:
{identity.directory_tree}

Sample Document Titles:
{chr(10).join(f"- {d.title}" for d in samples)}

Sample Content Excerpts:
{chr(10).join(f"[{d.title}]: {d.content[:500]}..." for d in samples[:5])}

Provide:
1. A one-sentence description of what this scope contains
2. A list of 5-10 key topics covered
3. The primary content type (source_code/documentation/data/mixed)
"""

    llm = get_llm(model="gpt-4o-mini")  # Fast, cheap
    response = await llm.generate(prompt)
    
    # Parse response
    identity.description = response.description
    identity.key_topics = response.topics
    identity.scope_content_type = response.content_type
    
    return identity
```

### 3.3 Identity Document Storage

```sql
-- New table for scope identity documents
CREATE TABLE scope_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id),
    team_id UUID REFERENCES teams(id),
    
    -- Scope identification
    scope_id TEXT NOT NULL,  -- e.g., "github://acme/backend@main"
    scope_name TEXT NOT NULL,
    scope_type TEXT NOT NULL,  -- repository, bucket, folder, workspace
    
    -- Content metadata
    file_count INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0,
    file_types JSONB DEFAULT '{}',
    directory_tree TEXT,
    key_paths TEXT[],
    
    -- Semantic metadata (LLM-generated)
    description TEXT,
    key_topics TEXT[],
    content_type TEXT,  -- source_code, documentation, data, mixed
    
    -- Timestamps
    first_ingested_at TIMESTAMPTZ DEFAULT NOW(),
    last_updated_at TIMESTAMPTZ DEFAULT NOW(),
    document_count INTEGER DEFAULT 0,
    
    -- Embedding for scope-level retrieval
    embedding VECTOR(1536),
    
    UNIQUE(user_id, scope_id)
);

-- Index for fast scope lookups
CREATE INDEX idx_scope_identities_user ON scope_identities(user_id);
CREATE INDEX idx_scope_identities_team ON scope_identities(team_id);
CREATE INDEX idx_scope_identities_type ON scope_identities(scope_type);
```

### 3.4 When to Generate Identity Documents

```python
# backend/worker/tasks.py - Add identity generation at end of ingestion

@celery_app.task
def finalize_ingestion_job(job_id: str):
    """Called after all files in a job are processed."""
    
    supabase = get_supabase()
    job = get_job(supabase, job_id)
    
    # Group processed documents by scope
    documents = get_job_documents(supabase, job_id)
    scopes = group_by_scope(documents)
    
    for scope_id, scope_docs in scopes.items():
        # Generate or update identity document
        existing = get_scope_identity(supabase, scope_id, job["user_id"])
        
        if existing:
            # Merge new documents into existing identity
            updated = merge_identity_document(existing, scope_docs)
            update_scope_identity(supabase, updated)
        else:
            # Generate new identity document
            identity = generate_identity_document_heuristic(scope_id, scope_docs)
            
            # Optionally enhance with LLM (for premium users)
            if should_use_llm(job["user_id"]):
                identity = await generate_identity_document_llm(scope_id, scope_docs)
            
            insert_scope_identity(supabase, identity)
    
    # Continue with existing finalization...
```

---

## 4. The Ambiguity Guard: Scope-Aware Retrieval

### 4.1 The Multi-Scope Detection Problem

When retrieval returns chunks from multiple scopes, the system must detect this as an ambiguity signal.

### 4.2 Enhanced Retrieval Pipeline

```python
# backend/api/v1/chat.py - Enhanced with scope awareness

@router.post("/chat")
async def chat_endpoint(request: Request, payload: ChatRequest, ...):
    # ... existing guardrail and routing logic ...
    
    # STEP 8: ENHANCED HYBRID SEARCH WITH SCOPE EXTRACTION
    docs = await hybrid_search_with_scope(
        supabase=supabase,
        query=search_query,
        embedding=query_vector,
        user_id=user_id,
        match_count=15,  # Retrieve more for scope analysis
    )
    
    # STEP 9: SCOPE COLLISION DETECTION (NEW)
    scope_analysis = analyze_scope_distribution(docs)
    
    if scope_analysis.has_collision:
        # Multiple distinct scopes detected
        return await handle_scope_collision(
            payload=payload,
            docs=docs,
            scope_analysis=scope_analysis,
            user_id=user_id,
            detected_language=detected_language,
        )
    
    # STEP 10: Single scope or no collision - proceed normally
    # ... existing context injection and LLM generation ...
```

### 4.3 Scope Analysis Logic

```python
# backend/services/scope_analysis.py

@dataclass
class ScopeAnalysis:
    """Result of analyzing retrieved documents for scope distribution."""
    scopes: Dict[str, List[Document]]  # scope_id -> documents
    primary_scope: Optional[str]  # Dominant scope if clear
    has_collision: bool  # True if multiple significant scopes
    confidence: float  # How confident we are in primary scope
    collision_type: Optional[str]  # "ambiguous" | "cross_reference" | "multi_source"

def analyze_scope_distribution(docs: List[Dict]) -> ScopeAnalysis:
    """
    Analyze retrieved documents for scope collision.
    
    Collision Detection Rules:
    1. If >80% of high-scoring docs (score > 0.7) are from same scope: NO collision
    2. If docs split roughly evenly (40-60%) between 2 scopes: COLLISION
    3. If docs span 3+ scopes with no dominant: COLLISION
    """
    
    # Extract scopes from documents
    scopes = defaultdict(list)
    for doc in docs:
        scope_id = doc.get("metadata", {}).get("source_scope", {}).get("scope_id", "unknown")
        scopes[scope_id].append(doc)
    
    # Filter to high-quality matches only
    high_quality_scopes = defaultdict(list)
    for doc in docs:
        score = doc.get("vector_score", 0) or doc.get("similarity", 0)
        if score >= 0.7:
            scope_id = doc.get("metadata", {}).get("source_scope", {}).get("scope_id", "unknown")
            high_quality_scopes[scope_id].append(doc)
    
    total_high_quality = sum(len(d) for d in high_quality_scopes.values())
    
    if total_high_quality == 0:
        # No high-quality matches, no collision to report
        return ScopeAnalysis(
            scopes=dict(scopes),
            primary_scope=None,
            has_collision=False,
            confidence=0.0,
            collision_type=None,
        )
    
    # Find dominant scope
    scope_percentages = {
        scope: len(docs) / total_high_quality 
        for scope, docs in high_quality_scopes.items()
    }
    
    sorted_scopes = sorted(scope_percentages.items(), key=lambda x: -x[1])
    primary_scope, primary_pct = sorted_scopes[0]
    
    # Collision detection
    if primary_pct >= 0.8:
        # Clear winner - no collision
        return ScopeAnalysis(
            scopes=dict(scopes),
            primary_scope=primary_scope,
            has_collision=False,
            confidence=primary_pct,
            collision_type=None,
        )
    
    if len(sorted_scopes) >= 2:
        secondary_pct = sorted_scopes[1][1]
        
        if secondary_pct >= 0.3:
            # Significant secondary scope - collision
            return ScopeAnalysis(
                scopes=dict(scopes),
                primary_scope=primary_scope,
                has_collision=True,
                confidence=primary_pct,
                collision_type="ambiguous" if secondary_pct >= 0.4 else "cross_reference",
            )
    
    if len(sorted_scopes) >= 3 and primary_pct < 0.5:
        # Spread across many scopes
        return ScopeAnalysis(
            scopes=dict(scopes),
            primary_scope=primary_scope,
            has_collision=True,
            confidence=primary_pct,
            collision_type="multi_source",
        )
    
    return ScopeAnalysis(
        scopes=dict(scopes),
        primary_scope=primary_scope,
        has_collision=False,
        confidence=primary_pct,
        collision_type=None,
    )
```

### 4.4 Collision Handling Strategies

```python
# backend/api/v1/chat.py - Collision response generation

async def handle_scope_collision(
    payload: ChatRequest,
    docs: List[Dict],
    scope_analysis: ScopeAnalysis,
    user_id: str,
    detected_language: str,
) -> ChatResponse:
    """
    Handle queries that retrieve from multiple scopes.
    
    Strategy:
    1. If collision_type == "ambiguous": Ask user to clarify
    2. If collision_type == "cross_reference": Synthesize with clear attribution
    3. If collision_type == "multi_source": List options and ask for focus
    """
    
    # Get scope identity documents for context
    scope_identities = await get_scope_identities(
        user_id=user_id,
        scope_ids=list(scope_analysis.scopes.keys()),
    )
    
    if scope_analysis.collision_type == "ambiguous":
        # Generate clarification request
        clarification = generate_clarification_message(
            query=payload.query,
            scopes=scope_identities,
            language=detected_language,
        )
        
        return ChatResponse(
            answer=clarification,
            sources=[],
            requires_clarification=True,
            suggested_scopes=[
                {"scope_id": s.scope_id, "name": s.scope_name, "description": s.description}
                for s in scope_identities
            ],
        )
    
    elif scope_analysis.collision_type == "cross_reference":
        # Synthesize with explicit scope attribution
        # Filter docs to primary scope but note cross-references
        primary_docs = scope_analysis.scopes[scope_analysis.primary_scope]
        secondary_scopes = {k: v for k, v in scope_analysis.scopes.items() 
                          if k != scope_analysis.primary_scope}
        
        # Generate response with clear section headers
        prompt = build_cross_reference_prompt(
            query=payload.query,
            primary_docs=primary_docs,
            secondary_scopes=secondary_scopes,
            scope_identities=scope_identities,
        )
        
        # ... generate with LLM ...
    
    else:  # multi_source
        # List all scopes and ask user to pick
        scope_list = format_scope_list(scope_identities, detected_language)
        
        return ChatResponse(
            answer=f"I found relevant information across multiple sources:\n\n{scope_list}\n\nWhich source would you like me to focus on?",
            sources=[],
            requires_clarification=True,
            suggested_scopes=[...],
        )

def generate_clarification_message(
    query: str,
    scopes: List[ScopeIdentityDocument],
    language: str,
) -> str:
    """Generate a user-friendly clarification request."""
    
    scope_descriptions = []
    for i, scope in enumerate(scopes[:5], 1):
        desc = scope.description or f"{scope.scope_type}: {scope.scope_name}"
        scope_descriptions.append(f"{i}. **{scope.scope_name}** - {desc}")
    
    if language.lower() != "en":
        # Could use LLM to translate, but for now English
        pass
    
    return f"""Your question could relate to multiple sources in your knowledge base:

{chr(10).join(scope_descriptions)}

Could you specify which source you're asking about? For example:
- "In the backend repository, how do I..."
- "From the product manual, what is..."
- "In the Marketing 2024 folder, where can I find..."

Or I can search across all sources and clearly label where each piece of information comes from."""
```

### 4.5 Enhanced System Prompt for Scope Awareness

```python
# backend/api/v1/chat.py - Enhanced system prompt

SCOPE_AWARE_SYSTEM_PROMPT = """You are Axio, an intelligent AI assistant with access to the user's knowledge base.

## Your Role
- Answer questions using ONLY the provided context documents
- Be aware that documents come from DIFFERENT SOURCES with different contexts
- Synthesize information accurately, respecting source boundaries

## Source Attribution Rules (CRITICAL)
Each document is tagged with its SOURCE SCOPE. When answering:
1. If all documents are from the SAME SCOPE: Answer directly with citations [1], [2], etc.
2. If documents are from DIFFERENT SCOPES: 
   - Clearly label which information comes from which source
   - Use headers like "According to [Source Name]:" 
   - Do NOT mix instructions from different sources as if they were the same

## Conflict Resolution
If you detect CONFLICTING information across sources:
- State the conflict explicitly
- Present both perspectives with clear attribution
- Ask the user which source is authoritative for their context

## Citation Format
- Use [1], [2], [3] for source citations
- Each source is labeled with its scope (e.g., "[1] GitHub: backend-v2", "[2] S3: Product Manual")

## KNOWLEDGE BASE CONTEXT:

{context}

---

Remember: Different sources may have different conventions. A "config.py" in one repository is NOT the same as in another. Treat each scope as a separate domain of knowledge."""
```

---

## 5. Database Schema Changes

### 5.1 Add `scope_id` to Documents Table

```sql
-- Migration: Add scope_id as first-class column
-- File: supabase/migrations/20260116000000_add_scope_id.sql

ALTER TABLE documents
ADD COLUMN IF NOT EXISTS scope_id TEXT;

-- Index for fast scope-based filtering
CREATE INDEX IF NOT EXISTS idx_documents_scope_id
ON documents(user_id, scope_id)
WHERE scope_id IS NOT NULL;

-- Composite index for scope + vector search
CREATE INDEX IF NOT EXISTS idx_documents_scope_vector
ON documents(user_id, scope_id, created_at DESC);

COMMENT ON COLUMN documents.scope_id IS 
  'Canonical scope identifier for context disambiguation (e.g., github://owner/repo@branch)';
```

### 5.2 Backfill Existing Documents

```sql
-- Backfill scope_id from existing metadata

-- GitHub documents
UPDATE documents
SET scope_id = CONCAT(
    'github://',
    metadata->>'repository',
    '@main'  -- Default branch assumption
)
WHERE source_type = 'github'
  AND scope_id IS NULL
  AND metadata ? 'repository';

-- S3 documents  
UPDATE documents
SET scope_id = metadata->>'source_id'  -- Already uses s3://bucket/key format
WHERE source_type = 's3'
  AND scope_id IS NULL
  AND metadata ? 'source_id';

-- Box documents
UPDATE documents
SET scope_id = CONCAT(
    'box://folder/',
    COALESCE(metadata->>'parent_id', 'root')
)
WHERE source_type = 'box'
  AND scope_id IS NULL;

-- Google Drive
UPDATE documents
SET scope_id = CONCAT(
    'gdrive://',
    COALESCE(metadata->>'parent_id', metadata->>'file_id', 'root')
)
WHERE source_type = 'google_drive'
  AND scope_id IS NULL;
```

### 5.3 Enhanced `hybrid_search` Function

```sql
-- Enhanced hybrid_search with optional scope filtering
-- File: supabase/migrations/20260116000001_scope_aware_search.sql

DROP FUNCTION IF EXISTS hybrid_search_scoped;

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_user_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,  -- NEW: Optional scope filter
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
    scope_id TEXT,  -- NEW: Include scope in results
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
            d.title,
            d.metadata,
            (1 - (dc.embedding <=> query_embedding))::FLOAT as score,
            ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) as rank
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE (filter_user_id IS NULL OR d.user_id = filter_user_id)
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))  -- NEW
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
          AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))  -- NEW
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

## 6. Implementation Roadmap

### Phase 1: Schema Foundation (Week 1)
**Goal:** Add scope infrastructure without breaking existing functionality

| Task | Priority | Risk | Dependencies |
|------|----------|------|--------------|
| Add `scope_id` column to documents table | P0 | Low | None |
| Create `scope_identities` table | P0 | Low | None |
| Create `hybrid_search_scoped` function | P0 | Low | scope_id column |
| Backfill scope_id for existing documents | P1 | Medium | scope_id column |

### Phase 2: Connector Enhancement (Week 2)
**Goal:** Inject scope metadata during ingestion

| Task | Priority | Risk | Dependencies |
|------|----------|------|--------------|
| Enhance GitHub connector with scope injection | P0 | Low | Phase 1 |
| Enhance S3 connector with scope injection | P0 | Low | Phase 1 |
| Enhance Box connector with scope injection | P0 | Low | Phase 1 |
| Enhance Dropbox connector with scope injection | P1 | Low | Phase 1 |
| Enhance Drive connector with scope injection | P1 | Low | Phase 1 |
| Enhance Notion connector with scope injection | P1 | Low | Phase 1 |

### Phase 3: Identity Document Generation (Week 3)
**Goal:** Implement scope-level summaries

| Task | Priority | Risk | Dependencies |
|------|----------|------|--------------|
| Implement heuristic identity generation | P0 | Low | Phase 2 |
| Add identity generation to ingestion finalization | P0 | Low | Phase 2 |
| (Optional) Implement LLM-enhanced identity | P2 | Medium | Phase 2 |

### Phase 4: Scope-Aware Retrieval (Week 4)
**Goal:** Implement collision detection and handling

| Task | Priority | Risk | Dependencies |
|------|----------|------|--------------|
| Implement `analyze_scope_distribution()` | P0 | Medium | Phase 1 |
| Implement clarification response generation | P0 | Medium | Phase 3 |
| Update chat endpoint with collision handling | P0 | Medium | All above |
| Add scope filter parameter to chat API | P1 | Low | Phase 1 |
| Update frontend with scope selection UI | P1 | Medium | API changes |

### Phase 5: Testing & Validation (Week 5)
**Goal:** Ensure no regressions and verify disambiguation

| Task | Priority | Risk | Dependencies |
|------|----------|------|--------------|
| Unit tests for scope analysis | P0 | Low | Phase 4 |
| Integration tests for scoped retrieval | P0 | Medium | Phase 4 |
| Load testing with multi-scope queries | P1 | Medium | Phase 4 |
| A/B testing clarification UX | P2 | Low | Frontend |

---

## 7. Success Metrics

### 7.1 Quantitative Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Cross-scope contamination rate | ~35% | <5% | % of queries returning docs from 3+ scopes |
| User clarification rate | 0% | 15-25% | % of queries triggering scope clarification |
| Scope identification accuracy | N/A | >95% | Correct scope assignment during ingestion |
| Identity document coverage | 0% | 100% | % of scopes with identity documents |

### 7.2 Qualitative Metrics

- User feedback on answer relevance (NPS delta)
- Reduction in "confusing mixed answers" complaints
- Increase in successful "summarize X" queries

---

## 8. Risk Analysis

### 8.1 Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope extraction fails for edge cases | Medium | Medium | Fallback to "unknown" scope, log for review |
| LLM identity generation costs | Low | High | Make LLM enhancement opt-in for premium |
| Clarification UX frustrates users | Medium | Medium | Provide "search all" fallback option |
| Backfill corrupts existing data | High | Low | Run in transaction, test on staging first |

### 8.2 Product Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Users don't understand scope concept | Medium | Medium | In-app education, clear UI labels |
| Over-triggering clarifications | High | Medium | Tune thresholds, allow user preference |
| Scope detection wrong | Medium | Low | Include "wrong scope?" feedback option |

---

## 9. Appendix: Code Reference Index

### Files to Modify

| File | Changes |
|------|---------|
| `backend/connectors/github.py` | Add `source_scope` to metadata |
| `backend/connectors/s3.py` | Add `source_scope` to metadata |
| `backend/connectors/box.py` | Add `source_scope` to metadata |
| `backend/connectors/dropbox.py` | Add `source_scope` to metadata |
| `backend/connectors/drive.py` | Add `source_scope` to metadata |
| `backend/connectors/notion.py` | Add `source_scope` to metadata |
| `backend/worker/tasks.py` | Inject scope_id into document insert, add identity generation |
| `backend/api/v1/chat.py` | Add scope analysis, collision handling |
| `backend/services/scope_analysis.py` | NEW: Scope collision detection |
| `backend/services/scope_identity.py` | NEW: Identity document generation |

### New Migrations

| File | Purpose |
|------|---------|
| `supabase/migrations/20260116000000_add_scope_id.sql` | Add scope_id column |
| `supabase/migrations/20260116000001_scope_identities.sql` | Create scope_identities table |
| `supabase/migrations/20260116000002_hybrid_search_scoped.sql` | Scope-aware search function |
| `supabase/migrations/20260116000003_backfill_scopes.sql` | Backfill existing documents |

---

## 10. Conclusion

The Universal Context Disambiguation Architecture addresses a critical limitation in the Axial platform's RAG pipeline. By implementing scope-aware ingestion, identity documents, and collision detection, we transform the system from "flat data retrieval" to "intelligent context navigation."

The phased implementation approach ensures we can deliver incremental value while minimizing regression risk. The key insight is that disambiguation happens at **three levels**:

1. **Ingestion Time:** Tag every document with its canonical scope
2. **Storage Time:** Maintain scope-level identity documents for navigation
3. **Retrieval Time:** Detect and handle multi-scope collisions gracefully

This architecture positions Axial to handle enterprise-scale knowledge bases where data from dozens of repositories, buckets, and folders coexist — without the "Heat Pump Paradox" of mixing instructions from incompatible sources.

---

*Document prepared by Principal AI Solutions Architect*  
*For questions or clarifications, reference this document in your query.*
