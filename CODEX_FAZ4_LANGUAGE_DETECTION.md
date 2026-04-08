# Faz 4 Directive — Language Detection at Ingest

> **Goal:** Detect chunk language during ingest, store as ISO 639-1 code in `document_chunks.language`, preserve `'simple'` regconfig for FTS.  
> **Scope:** Backend ingest pipeline only. No frontend changes. No FTS regconfig change.  
> **Constraint:** Per-language FTS retrieval is explicitly OUT OF SCOPE (Faz 5). Ingest and query regconfig must stay in sync — both `'simple'` — until query-side language routing is built alongside.

---

## Context & Rationale

The `document_chunks.language` column already exists (migration `20260302200000_multilang_search.sql:7-9`, `TEXT DEFAULT 'english'`) but is never populated during ingest. The active ingest pipeline and retrieval functions both use `'simple'` regconfig globally (Faz 1 decision). Faz 4 adds language detection to populate this column for future use, without changing FTS behavior.

**Why NOT change regconfig now:** Switching ingest to `to_tsvector(detected_lang::regconfig, ...)` without also changing the query path would break FTS — a query parsed with `'simple'` cannot match tokens generated with `'turkish'` stemming. Both sides must change together (Faz 5).

**Storage format decision:** The `language` column stores **ISO 639-1 lowercase codes** (`"tr"`, `"en"`, `"de"`), NOT PostgreSQL regconfig names (`"turkish"`, `"english"`). Reason: the column is a language label, not a FTS configuration directive. Mapping to regconfig is a concern of the query layer (Faz 5). When detection fails, is disabled, or text is too short, write **`NULL`** — not `"simple"` or `"unknown"`. `NULL` cleanly means "not detected" and is distinguishable from any valid language.

---

## Decision Lock

| ID | Decision | Rationale |
|----|----------|-----------|
| K1 | Library: `fast-langdetect` | FastText wrapper, 917KB compressed model, deterministic, Python 3.11 compatible, ~1ms/chunk on 1500 chars |
| K2 | Granularity: per-chunk | Each chunk detected independently. Mixed-language documents (TR report with EN technical terms) get correct per-chunk labels |
| K3 | Fallback: confidence < 0.5 or failure → `NULL` | Below threshold, detection failure, disabled, or text too short → write `NULL`. `NULL` = "not detected", cleanly distinguishable from any real language code |
| K4 | Regconfig stays `'simple'` — language is data-only | Populate `document_chunks.language` for analytics and future Faz 5 per-language retrieval. Do NOT change `to_tsvector()` regconfig in ingest RPC or search functions |
| K5 | Model loading: module-level singleton | Load compressed model once at worker startup. Zero per-chunk I/O. ~917KB memory overhead |
| K6 | Column default: keep `'english'` as-is | All existing data will be deleted and re-ingested. New ingest always writes detected value or NULL. Changing default is cosmetic, not functional |
| K7 | Storage format: ISO 639-1 lowercase | Store `"tr"`, `"en"`, `"de"` — not regconfig names. Language label ≠ FTS config. Regconfig mapping belongs in query layer (Faz 5) |
| K8 | Both write paths updated | `prepare_chunks_for_ghost_protocol()` (RPC path) AND `_insert_chunks_direct()` (fallback path) must both write `language`. No silent default fallback |

---

## BLOCK A — Language Detection Service (new file)

### A1. Create `backend/services/language_detector.py`

```python
"""
Chunk language detection using fast-langdetect (FastText wrapper).

- Loaded once at module level (singleton pattern)
- Deterministic: same input → same output
- Fail-open: detection failure returns None
- Compressed model: ~917KB memory footprint
- Returns ISO 639-1 codes ("tr", "en", "de"), NOT regconfig names
"""

from fast_langdetect import detect

import logging

logger = logging.getLogger(__name__)


def detect_language(text: str, *, confidence_threshold: float = 0.5, min_chars: int = 20) -> str | None:
    """
    Detect language of text and return ISO 639-1 code.
    
    Returns None if:
    - text is empty or too short (< min_chars)
    - detection confidence is below threshold
    - detection fails for any reason
    
    Returns ISO 639-1 lowercase code ("tr", "en", "de", etc.) on success.
    """
    if not text or len(text.strip()) < min_chars:
        return None
    
    try:
        result = detect(text, low_memory=True)
        lang_code = result.get("lang", "")
        score = result.get("score", 0.0)
        
        if score < confidence_threshold:
            logger.debug(
                "Language detection low confidence: lang=%s score=%.3f, returning None",
                lang_code, score
            )
            return None
        
        # fast-langdetect returns ISO 639-1 codes already ("en", "tr", "de")
        return lang_code.lower() if lang_code else None
        
    except Exception as e:
        logger.warning("Language detection failed: %s, returning None", e)
        return None
```

**Design notes:**
- `low_memory=True` uses the compressed 917KB model
- Returns ISO 639-1 code directly — no regconfig mapping (that's Faz 5's job)
- Returns `None` on any failure — stored as `NULL` in DB
- Parameters accept overrides from config (see C2)
- The function is pure (no state mutation), testable in isolation

---

## BLOCK B — Ingest Pipeline Integration (3 changes)

### B1. Wire detection into `prepare_chunks_for_ghost_protocol()`

**File:** `backend/core/ingestion_utils.py`  
**Function:** `prepare_chunks_for_ghost_protocol()` (line 74)

This is the PRIMARY write path — chunks go through Ghost Protocol RPC.

**Where:** After line 111 where `content_plaintext = content` is assigned, before the `prepared_chunk` dict is built (line 118).

**Add import at top of file:**
```python
from services.language_detector import detect_language
```

**Modify prepared_chunk dict (lines 118-125) — add `language` field:**
```python
prepared_chunk = {
    "id": str(uuid4()),
    "document_id": str(document_id),
    "content_encrypted": content_encrypted,
    "content_plaintext": content_plaintext,
    "embedding": chunk.get("embedding"),
    "chunk_index": chunk.get("chunk_index", 0),
    "language": detect_language(content_plaintext),  # NEW: Faz 4 — ISO 639-1 or None
}
```

**Why this location:** Plaintext is available (line 111), encryption hasn't occurred yet (line 110), and the prepared dict feeds directly into the RPC. This is the safe window for detection in the Ghost Protocol pipeline.

### B2. Wire detection into `_insert_chunks_direct()` (fallback path)

**File:** `backend/core/ingestion_utils.py`  
**Function:** `_insert_chunks_direct()` (line 207)

This is the FALLBACK write path — used when Ghost Protocol RPC is not deployed. It builds its own insert dicts (lines 230-242) independently of `prepare_chunks_for_ghost_protocol()`.

**Current code (lines 230-242):**
```python
for chunk in batch:
    content = chunk.get("content") or ""
    if HAS_CHUNK_ENCRYPTION:
        content = encrypt_text(content)
    insert_batch.append({
        "document_id": str(document_id),
        "content": content,
        "embedding": chunk.get("embedding"),
        "chunk_index": chunk.get("chunk_index", 0),
    })
```

**Change to:**
```python
for chunk in batch:
    content_raw = chunk.get("content") or ""
    detected_lang = detect_language(content_raw)  # NEW: detect BEFORE encryption
    if HAS_CHUNK_ENCRYPTION:
        content = encrypt_text(content_raw)
    else:
        content = content_raw
    insert_batch.append({
        "document_id": str(document_id),
        "content": content,
        "embedding": chunk.get("embedding"),
        "chunk_index": chunk.get("chunk_index", 0),
        "language": detected_lang,  # NEW: Faz 4 — ISO 639-1 or None
    })
```

**Why this matters:** Without this change, any chunk inserted via the fallback path gets `DEFAULT 'english'` from the schema — silently wrong. Both paths must write the detected language.

### B3. Update ingest RPC to store language

**New migration file:** `supabase/migrations/YYYYMMDDHHMMSS_ingest_rpc_add_language.sql`

**IMPORTANT:** This migration does NOT add a new column — `document_chunks.language` already exists (migration `20260302200000`). It only modifies the RPC to read and write the `language` field from the JSONB payload.

```sql
-- Faz 4: Update ingest RPC to populate existing language column.
-- Column already exists: ALTER TABLE document_chunks ADD COLUMN language TEXT DEFAULT 'english'
-- (migration 20260302200000_multilang_search.sql:7-9)
-- This migration ONLY modifies the RPC function.

CREATE OR REPLACE FUNCTION ingest_document_chunks_batch(
    p_chunks JSONB
)
RETURNS TABLE(inserted_id UUID, chunk_index INT)
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    INSERT INTO document_chunks (
        id,
        document_id,
        content,
        content_search,
        embedding,
        chunk_index,
        language              -- EXISTING column, now populated by RPC
    )
    SELECT
        COALESCE((chunk->>'id')::UUID, gen_random_uuid()),
        (chunk->>'document_id')::UUID,
        chunk->>'content_encrypted',
        to_tsvector('simple', COALESCE(chunk->>'content_plaintext', '')),
        (chunk->>'embedding')::VECTOR(1536),
        (chunk->>'chunk_index')::INT,
        chunk->>'language'    -- ISO 639-1 code or NULL (from Python detect_language)
    FROM jsonb_array_elements(p_chunks) AS chunk
    RETURNING id AS inserted_id, chunk_index;
END;
$$;
```

**Key points:**
- `to_tsvector('simple', ...)` stays unchanged — regconfig is NOT affected
- `chunk->>'language'` returns `NULL` when the key is absent or its value is JSON null — both are correct fallback behavior
- No `COALESCE` wrapper — we WANT `NULL` when detection didn't produce a result

---

## BLOCK C — Dependency & Config (2 items)

### C1. Add `fast-langdetect` to requirements

**File:** `backend/requirements.txt`  
**Add:**
```
fast-langdetect>=0.2.0
```

### C2. Add config settings

**File:** `backend/core/config.py`  
**Add after existing FAITHFULNESS_GUARD settings:**
```python
# Language Detection (Faz 4)
LANGUAGE_DETECTION_ENABLED: bool = True
LANGUAGE_DETECTION_CONFIDENCE_THRESHOLD: float = 0.5
LANGUAGE_DETECTION_MIN_CHARS: int = 20
```

**Then update `language_detector.py` to read from settings:**
- If `LANGUAGE_DETECTION_ENABLED` is `False`, `detect_language()` returns `None` immediately
- Threshold and min_chars come from config instead of hardcoded defaults

This allows disabling detection entirely via env var (`LANGUAGE_DETECTION_ENABLED=false`) if issues arise — fail-safe without code change.

---

## BLOCK D — Tests (3 items)

### D1. Unit tests for `language_detector.py`

**File:** `backend/tests/unit/test_language_detector.py`

Test cases:
- English text (>20 chars) → returns `"en"`
- Turkish text (>20 chars) → returns `"tr"`
- Empty string → returns `None`
- Very short text (<20 chars) → returns `None`
- Mixed/ambiguous text with low confidence → returns `None`
- Exception during detection → returns `None` (fail-open)
- Detection disabled via config → returns `None`

### D2. Integration test for ingest pipeline

**File:** `backend/tests/unit/test_ghost_protocol_ingestion.py` (extend existing `tests/integration/test_ghost_protocol_sql.py` pattern)

Test both write paths:

**RPC path (`prepare_chunks_for_ghost_protocol`):**
- Call with English chunk content → prepared_chunk dict has `"language": "en"`
- Call with Turkish chunk content → prepared_chunk dict has `"language": "tr"`
- Call with very short content → prepared_chunk dict has `"language": None`

**Fallback path (`_insert_chunks_direct`):**
- Verify insert_batch dict includes `"language"` key
- Verify detection happens BEFORE encryption (content_raw is used, not encrypted content)

### D3. Migration verification

After applying the new migration, verify:
```sql
-- Insert a test chunk via RPC WITH language field
SELECT * FROM ingest_document_chunks_batch(
    '[{"document_id": "...", "content_encrypted": "test", "content_plaintext": "test content", "embedding": "[0.1, ...]", "chunk_index": 0, "language": "tr"}]'::JSONB
);
-- Verify: language = 'tr'

-- Insert a test chunk via RPC WITHOUT language field (backward compat)
SELECT * FROM ingest_document_chunks_batch(
    '[{"document_id": "...", "content_encrypted": "test", "content_plaintext": "test", "embedding": "[0.1, ...]", "chunk_index": 0}]'::JSONB
);
-- Verify: language = NULL (not 'english', not 'simple')

-- Insert a test chunk via RPC with explicit NULL
SELECT * FROM ingest_document_chunks_batch(
    '[{"document_id": "...", "content_encrypted": "test", "content_plaintext": "test", "embedding": "[0.1, ...]", "chunk_index": 0, "language": null}]'::JSONB
);
-- Verify: language = NULL
```

**Note:** The second case will actually get `DEFAULT 'english'` from the schema unless the RPC explicitly writes NULL. Verify that `chunk->>'language'` returns SQL NULL (not the string `"null"`) when the key is absent from JSONB. If the column default kicks in, the migration may need `COALESCE(chunk->>'language', NULL)` or the column default should be changed to `NULL`.

---

## BLOCK E — Smoke Test Checklist

### E1. Ingest Turkish document
- Upload a Turkish text source
- After ingest completes, query `document_chunks` for that document
- Verify `language = 'tr'` on all chunks

### E2. Ingest English document
- Upload an English text source
- Verify `language = 'en'` on all chunks

### E3. Ingest mixed-language document
- Upload a document with both Turkish and English sections
- Verify chunks get per-chunk language labels (some `'tr'`, some `'en'`)

### E4. FTS regression check
- After ingest, run a keyword search query
- Verify `content_search` TSVECTOR was generated with `'simple'` (not the detected language)
- Hybrid search returns expected results — no regression from Faz 1-3

### E5. Detection disabled
- Set `LANGUAGE_DETECTION_ENABLED=false`
- Ingest a document
- Verify all chunks get `language = NULL`

### E6. Fallback path
- If testable: simulate RPC unavailability to trigger `_insert_chunks_direct()`
- Verify chunks still get correct `language` values via the fallback path

---

## Out of Scope (Faz 5)

These are explicitly NOT part of Faz 4:
- Per-language `to_tsvector(lang::regconfig, ...)` at ingest time
- Query-side language routing (`plainto_tsquery(lang::regconfig, ...)`)
- Per-language regconfig in `hybrid_search` / `hybrid_search_scoped` functions
- ISO 639-1 → regconfig mapping layer
- Frontend language display or selection UI
- Bulk re-detection of existing chunks (all data will be fresh from re-ingest)
- Changing column default from `'english'` to `NULL` (cosmetic, all rows will have explicit values after re-ingest)

---

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/services/language_detector.py` | NEW | Language detection service, returns ISO 639-1 or None, fail-open, singleton model |
| `backend/core/ingestion_utils.py` | MODIFY | Add `detect_language()` in BOTH `prepare_chunks_for_ghost_protocol()` (line 118) AND `_insert_chunks_direct()` (line 237) |
| `backend/core/config.py` | MODIFY | Add 3 `LANGUAGE_DETECTION_*` settings |
| `backend/requirements.txt` | MODIFY | Add `fast-langdetect>=0.2.0` |
| `supabase/migrations/YYYYMMDDHHMMSS_ingest_rpc_add_language.sql` | NEW | Update `ingest_document_chunks_batch` RPC to write EXISTING `language` column |
| `backend/tests/unit/test_language_detector.py` | NEW | Unit tests for detection service |
| `backend/tests/unit/test_ghost_protocol_ingestion.py` | NEW | Integration tests for both RPC and fallback write paths |
