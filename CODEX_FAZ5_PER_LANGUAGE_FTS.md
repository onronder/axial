# Faz 5 Directive — Per-Language FTS Retrieval

> **Goal:** Make both ingest and query FTS pipelines language-aware. Chunks are indexed with their detected language's regconfig; queries are parsed with the query language's regconfig. Shared mapping ensures ingest and query stay in sync.  
> **Scope:** Backend only. Shared mapping module, ingest RPC update, search function update, chat.py + search.py caller updates.  
> **Constraint:** Mapping must be a single source of truth used by both ingest and query. Mismatch = broken FTS.

---

## Context & Rationale

Faz 4 populated `document_chunks.language` with ISO 639-1 codes (`"tr"`, `"en"`, etc.) but kept FTS regconfig at `'simple'` globally. Faz 5 activates per-language stemming:

- **Ingest:** `to_tsvector('simple', plaintext)` → `to_tsvector(regconfig, plaintext)` where regconfig is derived from the chunk's detected language
- **Query:** `plainto_tsquery('simple', query_text)` → `plainto_tsquery(regconfig, query_text)` where regconfig is derived from the query's detected language

**Why both must change together:** A chunk indexed with `to_tsvector('turkish', ...)` produces stemmed tokens (e.g., "kitaplar" → "kitap"). A query parsed with `plainto_tsquery('simple', 'kitap')` produces the raw token "kitap" — this matches. But `plainto_tsquery('simple', 'kitapların')` produces "kitapların" — this does NOT match "kitap". Only `plainto_tsquery('turkish', 'kitapların')` stems to "kitap" and matches. Ingest and query regconfig must be symmetric.

**Unsupported languages fall back safely:** If a language has no PostgreSQL regconfig (e.g., Japanese, Chinese, Korean), both ingest and query use `'simple'`. This is identical to current Faz 1-4 behavior — no regression.

**Turkish stemming quality:** PostgreSQL uses Snowball stemmer for Turkish. It handles noun suffixes (-lar, -ler, -da, -de, -dan, -den, -nın, -nin) but NOT verb conjugations (-yor, -mış, -ecek). Over-stemming risk on compound words and loanwords. For 1500-char RAG chunks this is acceptable — better recall than `'simple'` with manageable precision trade-off.

---

## Decision Lock

| ID | Decision | Rationale |
|----|----------|-----------|
| K1 | Shared mapping in `backend/core/language_config.py` | Single source of truth for ISO 639-1 → regconfig. Both ingest and query import from same module. Mismatch impossible |
| K2 | Chat query language: `guardrail_result.language` → mapping | Guardrail already detects query language via LLM, returns ISO 639-1. Zero additional cost |
| K3 | Search query language: `language_detector.detect(query_text)` → mapping | Search endpoint doesn't run guardrail. Use Faz 4's `language_detector.detect()` (fast-langdetect, 1ms). Consistent with ingest detection |
| K4 | Ingest regconfig: Python-side mapping, sent to RPC as `language_regconfig` | Mapping lives in Python (single source), SQL just uses what it receives. No mapping logic in SQL |
| K5 | SQL override removal: delete `search_language := 'simple'` lines | Functions already accept `search_language` parameter. Remove hardcoded override, let caller pass the value |
| K6 | Unsupported language → `'simple'` fallback | Languages without PG regconfig (ja, zh, ko, etc.) get `'simple'`. Same as Faz 1-4 behavior, zero regression |
| K7 | No backfill needed | All sources will be deleted and re-ingested. New pipeline uses per-language regconfig automatically |
| K8 | `NULL` language in DB → `'simple'` at query time | Chunks with `language = NULL` (detection failed in Faz 4) are indexed with `'simple'` and queried with `'simple'`. Consistent |
| K9 | Fallback direct insert path: NO `language_regconfig` | `_insert_chunks_direct()` uses `db_utils.insert_rows_with_retry()` which does direct table INSERT. Table has no `language_regconfig` column — adding it to the dict would crash. Fallback path keeps `content_search` as schema default. RPC hot path handles per-language regconfig |
| K10 | Language detector API: `language_detector.detect()` | Faz 4 created a `LanguageDetector` class with `.detect()` method and a module-level singleton `language_detector`. Ingest uses wrapper `_detect_chunk_language()`. Query paths use `language_detector.detect()` directly. Do NOT call `detect_language()` — that function doesn't exist |

---

## BLOCK A — Shared Language Config Module (new file)

### A1. Create `backend/core/language_config.py`

```python
"""
Shared ISO 639-1 → PostgreSQL regconfig mapping.

This module is the SINGLE SOURCE OF TRUTH for language-to-regconfig conversion.
Both ingest (content_search generation) and query (FTS parsing) MUST use this mapping.
If ingest uses a different regconfig than query for the same language, FTS breaks.

Supported languages are those with a built-in PostgreSQL text search configuration.
Unsupported languages fall back to 'simple' (no stemming, just tokenization).
"""

# Complete mapping of ISO 639-1 codes to PostgreSQL regconfig names.
# Only languages with built-in PG text search configurations are included.
LANG_TO_REGCONFIG: dict[str, str] = {
    "ar": "arabic",
    "hy": "armenian",
    "eu": "basque",
    "ca": "catalan",
    "da": "danish",
    "nl": "dutch",
    "en": "english",
    "fi": "finnish",
    "fr": "french",
    "de": "german",
    "el": "greek",
    "hi": "hindi",
    "hu": "hungarian",
    "id": "indonesian",
    "ga": "irish",
    "it": "italian",
    "lt": "lithuanian",
    "ne": "nepali",
    "no": "norwegian",
    "pt": "portuguese",
    "ro": "romanian",
    "ru": "russian",
    "sr": "serbian",
    "es": "spanish",
    "sv": "swedish",
    "ta": "tamil",
    "tr": "turkish",
    "yi": "yiddish",
}

# Default regconfig when language is unknown, unsupported, or NULL
DEFAULT_REGCONFIG = "simple"


def get_regconfig(lang_code: str | None) -> str:
    """
    Convert ISO 639-1 language code to PostgreSQL regconfig name.
    
    Args:
        lang_code: ISO 639-1 lowercase code ("tr", "en", "de") or None
        
    Returns:
        PostgreSQL regconfig name ("turkish", "english", "simple", etc.)
        Returns 'simple' for None, empty string, or unsupported languages.
    """
    if not lang_code:
        return DEFAULT_REGCONFIG
    return LANG_TO_REGCONFIG.get(lang_code.lower(), DEFAULT_REGCONFIG)
```

**Design notes:**
- Pure function, no side effects, trivially testable
- `LANG_TO_REGCONFIG` dict covers all 28 built-in PG text search configs (PG 15+)
- `get_regconfig(None)` → `"simple"` handles Faz 4 NULL language chunks
- Both ingest and query import `get_regconfig()` from this single module

---

## BLOCK B — Ingest Pipeline Update (2 changes)

### B1. Wire regconfig into `prepare_chunks_for_ghost_protocol()`

**File:** `backend/core/ingestion_utils.py`  
**Function:** `prepare_chunks_for_ghost_protocol()` (line 74)

**Add import at top of file:**
```python
from core.language_config import get_regconfig
```

**Current prepared_chunk dict (from Faz 4) already calls `_detect_chunk_language(content_plaintext)` (ingestion_utils.py:129) which returns ISO 639-1 or None. Add `"language_regconfig"` using the same detected value:**

**Modify the loop in `prepare_chunks_for_ghost_protocol()` — capture detection result, then add regconfig:**
```python
detected_lang = _detect_chunk_language(content_plaintext)  # Faz 4: existing call

prepared_chunk = {
    "id": str(uuid4()),
    "document_id": str(document_id),
    "content_encrypted": content_encrypted,
    "content_plaintext": content_plaintext,
    "embedding": chunk.get("embedding"),
    "chunk_index": chunk.get("chunk_index", 0),
    "language": detected_lang,                        # Faz 4: ISO 639-1 or None
    "language_regconfig": get_regconfig(detected_lang),  # NEW Faz 5: regconfig for to_tsvector
}
```

### B2. Fallback write path `_insert_chunks_direct()` — NO `language_regconfig` change

**File:** `backend/core/ingestion_utils.py`  
**Function:** `_insert_chunks_direct()` (line 214)

**DO NOT add `language_regconfig` to this path.** This function uses `db_utils.insert_rows_with_retry()` which does a direct table INSERT. The `document_chunks` table has no `language_regconfig` column — adding it to the insert dict would cause a Supabase/PostgREST error.

Additionally, this path cannot populate `content_search` with per-language regconfig because there is no trigger or default expression on the column that accepts a regconfig parameter. The direct insert path writes `language` (ISO 639-1, from Faz 4) but `content_search` remains unpopulated — no per-language tsvector is generated for fallback-path chunks.

**This is acceptable because:**
1. The fallback path only triggers when the Ghost Protocol RPC is not deployed (legacy/migration scenario)
2. The active hot path is always the RPC path (B1 + C1), which handles per-language regconfig correctly
3. If fallback is ever triggered, chunks get `language` populated (for future re-ingest) but `content_search` remains empty — no per-language tsvector is generated

**No code change needed in B2 for Faz 5.** Faz 4 already added `language` to this path — that stays.

---

## BLOCK C — Ingest RPC Migration

### C1. Update `ingest_document_chunks_batch` to use per-language regconfig

**New migration file:** `supabase/migrations/YYYYMMDDHHMMSS_ingest_rpc_per_language_regconfig.sql`

```sql
-- Faz 5: Update ingest RPC to generate content_search with per-language regconfig.
-- The language_regconfig field is provided by the Python caller via get_regconfig().
-- Mapping logic lives in Python (backend/core/language_config.py), not in SQL.
-- Fallback: if language_regconfig is absent, defaults to 'simple'.

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
        language
    )
    SELECT
        COALESCE((chunk->>'id')::UUID, gen_random_uuid()),
        (chunk->>'document_id')::UUID,
        chunk->>'content_encrypted',
        to_tsvector(
            COALESCE(chunk->>'language_regconfig', 'simple')::regconfig,
            COALESCE(chunk->>'content_plaintext', '')
        ),
        (chunk->>'embedding')::VECTOR(1536),
        (chunk->>'chunk_index')::INT,
        chunk->>'language'
    FROM jsonb_array_elements(p_chunks) AS chunk
    RETURNING id AS inserted_id, chunk_index;
END;
$$;
```

**Key change:** `to_tsvector('simple', ...)` → `to_tsvector(COALESCE(chunk->>'language_regconfig', 'simple')::regconfig, ...)`. The regconfig comes from the Python caller. If absent, falls back to `'simple'`.

---

## BLOCK D — Query Pipeline Update (3 changes)

### D1. Remove hardcoded override in `hybrid_search`

**New migration (same file as C1 or separate):**

In `hybrid_search` function, **remove line 136:**
```sql
-- REMOVE THIS LINE:
search_language := 'simple';
```

The function signature already has `search_language TEXT DEFAULT 'simple'`. Without the override, callers can now pass the actual language. Non-Faz-5 callers that don't pass `search_language` still get `'simple'` from the default.

### D2. Remove hardcoded override in `hybrid_search_scoped`

Same change — **remove line 285:**
```sql
-- REMOVE THIS LINE:
search_language := 'simple';
```

### D3. Update chat.py caller — pass detected language

**File:** `backend/api/v1/chat.py`

**Add import:**
```python
from core.language_config import get_regconfig
```

**Current (line 1723):**
```python
search_language = "simple"  # Short-term FTS strategy is globally normalized.
```

**Change to:**
```python
search_language = get_regconfig(detected_language)  # Faz 5: per-language FTS
```

`detected_language` is already available from `guardrail_result.language` (line 1478). No additional detection needed.

This flows into all 4 RPC call sites (lines 1730, 1743, 1759, 1774) which already pass `"search_language": search_language`.

### D4. Update search.py caller — detect query language

**File:** `backend/api/v1/search.py`

**Add imports:**
```python
from services.language_detector import language_detector
from core.language_config import get_regconfig
```

**Current (line 141):**
```python
search_language = "simple"  # Short-term FTS strategy is globally normalized.
```

**Change to:**
```python
query_lang = language_detector.detect(query)  # Faz 5: detect query language via fast-langdetect
search_language = get_regconfig(query_lang)
```

This flows into both RPC call sites (lines 167, 177) which already pass `"search_language": search_language`.

**API note:** The Faz 4 language detector exposes a `LanguageDetector` class with `.detect()` instance method, plus a module-level singleton `language_detector`. The existing ingest code uses a private wrapper `_detect_chunk_language()` (ingestion_utils.py:27) which delegates to `language_detector.detect()`. In search.py, use the singleton directly — no need for the ingestion wrapper.

**Why fast-langdetect here (not guardrail):** The search endpoint doesn't run the guardrail service (no LLM call). Using `language_detector.detect()` adds ~1ms per query — negligible. The detection source is different from chat (fasttext vs LLM) but the mapping function is the same, so regconfig output is consistent.

---

## BLOCK E — Tests (4 items)

### E1. Unit tests for `language_config.py`

**File:** `backend/tests/unit/test_language_config.py`

Test cases:
- `get_regconfig("tr")` → `"turkish"`
- `get_regconfig("en")` → `"english"`
- `get_regconfig("de")` → `"german"`
- `get_regconfig("ja")` → `"simple"` (unsupported)
- `get_regconfig("zh")` → `"simple"` (unsupported)
- `get_regconfig(None)` → `"simple"`
- `get_regconfig("")` → `"simple"`
- `get_regconfig("TR")` → `"turkish"` (case insensitive)
- Verify `LANG_TO_REGCONFIG` has exactly 28 entries (all PG built-in configs)

### E2. Integration test for ingest with per-language regconfig

**File:** `backend/tests/unit/test_ghost_protocol_ingestion.py` (extend Faz 4 tests)

Test that `prepare_chunks_for_ghost_protocol()`:
- Turkish content chunk → `language_regconfig = "turkish"` in prepared dict
- English content chunk → `language_regconfig = "english"` in prepared dict
- Short/undetectable content → `language_regconfig = "simple"` in prepared dict

### E3. Test search_language propagation in chat.py

**File:** `backend/tests/unit/test_chats.py` (extend existing)

Mock `guardrail_result.language = "tr"` → verify the RPC call receives `search_language = "turkish"`.
Mock `guardrail_result.language = "ja"` → verify `search_language = "simple"` (unsupported fallback).

### E4. Test search_language propagation in search.py

**File:** `backend/tests/unit/test_search_api.py` (new or extend)

Mock `language_detector.detect()` returning `"tr"` → verify RPC call receives `search_language = "turkish"`.
Mock `language_detector.detect()` returning `None` → verify `search_language = "simple"`.

---

## BLOCK F — Smoke Test Checklist

### F1. Turkish ingest + Turkish query
- Delete existing sources, re-ingest TR-AXIAL-20260408.pdf
- Query `document_chunks` → verify `language = 'tr'` on chunks
- Verify `content_search` was generated with `'turkish'` regconfig:
  ```sql
  SELECT ts_debug('turkish', 'kitapların') -- should stem to 'kitap'
  ```
- Search for "cografi isaret denetimi" via chat → verify TR document found
- Search for "denetim" (stemmed form would match "denetimi") → verify improved recall vs Faz 4

### F2. English ingest + English query
- Re-ingest EN-AXIAL-20260408.pdf
- Verify `language = 'en'`, `content_search` generated with `'english'` regconfig
- Search for "quarterly variance bridge" → verify EN document found
- Search for "variances" (stemmed → "variance") → verify match

### F3. Cross-language query (hybrid search behavior)
- Query Turkish document with English search term (e.g., "inspection")
- **Important:** Hybrid search combines semantic (vector) AND keyword (FTS) branches (see `20260407110000_fix_fts_pipeline_simple.sql:172,221`). Even if FTS keyword branch returns no match (regconfig mismatch), the **vector branch may still return results** based on embedding similarity. This is expected behavior, not a bug.
- **What to verify:** The FTS `keyword_score` component should be 0 or very low for cross-language queries, while `vector_score` may still be positive. The overall RRF-combined score will be lower than a same-language query.
- To isolate FTS behavior specifically, test with a raw SQL query:
  ```sql
  -- This should return no match (English query against Turkish-stemmed content)
  SELECT content_search @@ plainto_tsquery('english', 'denetim') FROM document_chunks WHERE language = 'tr' LIMIT 1;
  -- This should return a match (Turkish query against Turkish-stemmed content)
  SELECT content_search @@ plainto_tsquery('turkish', 'denetim') FROM document_chunks WHERE language = 'tr' LIMIT 1;
  ```

### F4. Unsupported language
- If possible, ingest a Japanese/Chinese text → verify `language = 'ja'`/`'zh'`, `content_search` generated with `'simple'`
- Query with Japanese text → verify fallback to `'simple'`, no error

### F5. NULL language chunks
- Any chunk where Faz 4 detection returned NULL → verify `content_search` uses `'simple'`
- Query still finds these chunks via `'simple'` tokenization

### F6. Search endpoint
- Use `/search` endpoint (not chat) → verify language-aware FTS works
- Search for Turkish term → verify `'turkish'` regconfig used in query

### F7. FTS regression check
- Run the same queries from Faz 4 smoke test → verify results are equal or better (more recall from stemming)
- No query that worked before should break

---

## Out of Scope (Future)

- CJK language support (requires pg_bigm or custom tokenizer, not PG built-in)
- Custom Turkish morphological analyzer (Zemberek integration)
- Frontend language display
- Language-based routing (different LLM prompts per language — already done via guardrail)
- Per-document language override UI

---

## File Change Summary

| File | Action | Description |
|------|--------|-------------|
| `backend/core/language_config.py` | NEW | Shared ISO 639-1 → regconfig mapping, `get_regconfig()` function |
| `backend/core/ingestion_utils.py` | MODIFY | Add `language_regconfig` to RPC write path only (`prepare_chunks_for_ghost_protocol`). Fallback `_insert_chunks_direct` NOT changed — table has no `language_regconfig` column |
| `backend/api/v1/chat.py` | MODIFY | Line 1723: `search_language = get_regconfig(detected_language)` |
| `backend/api/v1/search.py` | MODIFY | Line 141: `language_detector.detect(query)` → `get_regconfig()` → `search_language` |
| `supabase/migrations/YYYYMMDDHHMMSS_ingest_rpc_per_language_regconfig.sql` | NEW | RPC uses `chunk->>'language_regconfig'` for `to_tsvector()`. Remove `search_language := 'simple'` override in both search functions |
| `backend/tests/unit/test_language_config.py` | NEW | Mapping tests |
| `backend/tests/unit/test_ghost_protocol_ingestion.py` | MODIFY | Add regconfig propagation tests |
| `backend/tests/unit/test_chats.py` | MODIFY | Add search_language propagation test |
| `backend/tests/unit/test_search_api.py` | NEW/MODIFY | Add search_language propagation test |
