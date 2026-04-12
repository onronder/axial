# AxioHub RAG Engine — Production Go-Live Final Audit & Implementation Plan

**Tarih:** 7 Nisan 2026 (Rev.4 — Codex 5.4 Round 3 + Claude cross-review)
**Durum:** Pre-Launch Critical Code Audit
**Yontem:** Kaynak kod satir-bazli analiz + Codex 5.4 uc tur dogrulama + industry best practices
**Kapsam:** Chunking → Embedding → Vector Storage → Hybrid Search → Reranking → Guardrails → Cache → Ingestion → Monitoring

---

## REVISION LOG

| Rev | Tarih | Yapan | Degisiklik |
|-----|-------|-------|------------|
| 1.0 | 07.04.2026 | Claude | Ilk audit dokumani |
| 1.1 | 07.04.2026 | Codex 5.4 | Satir-bazli dogrulama notlari |
| 2.0 | 07.04.2026 | Claude | Tam revizyon — Codex Round 1 duzeltmeleri islendi, yeni bulgular eklendi, her madde icin implementation blueprint yazildi |
| 2.1 | 07.04.2026 | Codex 5.4 | Round 2 — 16 yeni yorum: alan adi duzeltmeleri, FTS strateji tutarsizligi, backfill plani eksikligi, schema dogrulamalari |
| 3.0 | 07.04.2026 | Claude | Tam revizyon — Tum 16 Codex Round 2 yorumu islendi. FTS stratejisi `simple` olarak tutarlistirildi, backfill plani eklendi, GuardrailService pattern'ine gecildi, H2 dual-path helper, cache key'e scope set eklendi, feedback message_id bazli duzeltildi, metric tanimlari module-level'a tasinidi |
| 3.1 | 07.04.2026 | Codex 5.4 | Round 3 — 5 yorum: backfill script yolu/encryption fonksiyon adi, document_chunks.organization_id schema hatasi, private _get_model kullanimi, SSE done.warning pattern'i, allowed_scopes degisken adi |
| 4.0 | 07.04.2026 | Claude | Hedefli duzeltme — Backfill `backend/scripts/` + `decrypt_text` pattern'ine gecti, document_chunks.organization_id → documents JOIN, faithfulness guard public `analyze_query_with_context` pattern'i, SSE `done.warning` genisleme, cache `allowed_scopes` dogru degisken adi |

---

## EXECUTIVE SUMMARY

AxioHub RAG pipeline, hybrid search (RRF), format-aware chunking, 3-tier PDF processing, Dominance Guard, Ghost Protocol encryption ve kapsamli multi-tenancy izolasyonuna sahip olgun bir sistem. Codex 5.4 ile yapilan **uc tur cross-review** sonucunda toplam **19 bulgu** kalibrandi, **4 kritik yeni bulgu** eklendi ve tum implementation blueprint'leri somut kod ornekleriyle desteklendi.

**Rev 4.0 Anahtar Degisiklikler (Round 3 uzerine):**

- **Backfill scripti gercek codebase pattern'ine hizalandi:** `manage.py` / `management/commands/` yok — `backend/scripts/` kullanildi. `decrypt_content` yok — dogru fonksiyon `core.security.decrypt_text` (`backend/core/security.py:262`).
- **document_chunks.organization_id yok:** Schema'da bu kolon bulunmuyor, org baglami `documents` tablosu uzerinden JOIN ile geliyor. Backfill SQL'leri duzeltildi.
- **Faithfulness guard artik public API kullaniyor:** `_get_model()` private metoda disaridan baglanti kirilgan. Blueprint, mevcut public `analyze_query_with_context()` pattern'ini kullanacak sekilde veya yeni public method ekleyecek sekilde yeniden yazildi.
- **SSE faithfulness warning `done.warning` uzerinden:** Yeni event tipi yerine mevcut `done` event'inin `warning` field'i genisletildi (`chat.py:2458-2461` zaten bu pattern'i kullaniyor).
- **Cache `allowed_scopes` dogru degisken adi:** `allowed_scopes` → `allowed_scopes` (chat endpoint dependency: `chat.py:1286`).

---

## BOLUM 1: CHUNKING PIPELINE

### 1.1 Mevcut Durum

**Dosya:** `backend/services/parsers.py`

| Format | Chunk Size | Overlap | Ozel Davranis |
|--------|-----------|---------|---------------|
| Code | 1500 chars | 100 | `RecursiveCharacterTextSplitter.from_language()`, hard limit 2000 token |
| Markdown | 1000 chars | 150 | Header-aware split, `[Context: header_path]` prefix |
| PDF | 1000 chars | 200 | 3-tier: LlamaParse → PyMuPDF → Tesseract |
| HTML | 1000 chars | 150 | Standard recursive split |
| DOCX | 1000 chars | 200 | Legal mode: 2000 chars |
| CSV | 500 satir/batch | - | `col1: val1 \| col2: val2` format |
| XLSX | 200 satir/batch | - | CSV ile benzer |
| PPTX | 1000 chars | 150 | Standard recursive split |

**Token Counting:** tiktoken `cl100k_base`, fallback `len(text) // 4`

### 1.2 Sorunlar ve Implementation Blueprint'leri

---

#### SORUN-C1: Chunk Size Tutarsizligi (Orta Oncelik)

**Kanit:** Code: 1500 char (~400 token), diger format'lar: 1000 char (~250 token).

**ClaudeRevize (Rev 2.0):** Codex notu "best practice tarafinda tek global chunk_size yerine modalite bazli token histogramlari ve retrieval kalitesi uzerinden kalibrasyon daha dogru olur" dogrulandi.

**Guncellenmis Oneri:** Tek hedef yerine, format bazli optimal aralik belirle:
- Code: 300-500 token (fonksiyon/class sinirlari korunmali)
- Prose (MD/DOCX/PDF/HTML): 200-350 token
- Tabular (CSV/XLSX): Satir bazli, degistirme

**IMPLEMENTATION BLUEPRINT:**

Adim 1 — Mevcut dagilimi olc (SQL calistirilacaksa Supabase SQL Editor uzerinden):
```sql
SELECT
  d.source_type,
  COUNT(dc.id) as chunk_count,
  AVG(length(dc.content)) as avg_char_length
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
GROUP BY d.source_type
ORDER BY chunk_count DESC;
```

> **ClaudeRevize (Rev 2.0):** Orijinal rapordaki `metadata->>'token_count'` sorgusu guvenilir degil. Codex, `ingest_document_batched()` fonksiyonunun chunk metadata'sini insert oncesi temizleyebildigini belirtti. `length(dc.content)` char bazli kullaniliyor, token sayisi icin `length / 4` yaklasik tahmin uygulanabilir.

Adim 2 — Eger tutarsizlik retrieval kalitesini etkiliyorsa, parsers.py'de format bazli chunk_size'lari token-bazli yaklasima cevir:
```python
# parsers.py - Ornek degisiklik (Code processor)
# ONCE:
# text_splitter = RecursiveCharacterTextSplitter.from_language(
#     language=lang, chunk_size=1500, chunk_overlap=100
# )
# SONRA:
TARGET_TOKENS = 400
CHARS_PER_TOKEN = 4  # cl100k_base icin ortalama
text_splitter = RecursiveCharacterTextSplitter.from_language(
    language=lang,
    chunk_size=TARGET_TOKENS * CHARS_PER_TOKEN,
    chunk_overlap=100,
    length_function=lambda t: len(TIKTOKEN_ENCODER.encode(t))
)
```

**Dogrulama:** Degisiklik sonrasi ayni dokumani yeniden ingest et, yeni chunk'larin token dagilimini karsilastir.

---

#### SORUN-C2: PDF Scanned Detection — Dead Code (Dusuk Oncelik)

**ClaudeRevize (Rev 2.0):** Codex bu bulguyu **reddetti**. `SCANNED_TEXT_THRESHOLD` ve `_is_likely_scanned()` dosyada var ama aktif PDF akisinda cagrilmiyor. Gercek OCR fallback karari `MIN_TOKENS_THRESHOLD = 50` ile dokuman seviyesinde veriliyor. Bu bulgu "dead code" kategorisinde.

**Guncellenmis Oneri:** Dead code temizligi yap veya page-level scanned detection'i aktif akisa bagla. Go-live blocker degil.

---

#### SORUN-C3: CSV/XLSX Semantic Bilgi Kaybi (Orta Oncelik)

**Kanit:** Satirlar `col1: val1 | col2: val2` formatinda serlestirilior.

**ClaudeRevize (Rev 2.0):** Codex notu "tek chunk icinde yuzlerce satir tutulabildigi icin ayni chunk icindeki iliskiler yasayabiliyor" dogrulandi. Risk dusuruldu.

**IMPLEMENTATION BLUEPRINT:**

```python
# parsers.py - CSV processor'a sheet/table summary ekle
def _build_table_summary(df, sheet_name=None):
    """Chunk basina eklenen meta-context."""
    summary_parts = []
    if sheet_name:
        summary_parts.append(f"Sheet: {sheet_name}")
    summary_parts.append(f"Columns: {', '.join(df.columns.tolist())}")
    summary_parts.append(f"Total rows: {len(df)}")
    for col in df.select_dtypes(include='number').columns[:5]:
        summary_parts.append(f"{col}: min={df[col].min()}, max={df[col].max()}, mean={df[col].mean():.1f}")
    return "[Table Context: " + " | ".join(summary_parts) + "]\n"
```

---

## BOLUM 2: EMBEDDING PIPELINE

### 2.1 Mevcut Durum

**Dosyalar:** `backend/services/embeddings.py`, `backend/core/embeddings.py`

- Model: `text-embedding-3-small` (1536 dim), DB HNSW index'e kilitli
- Batch: 200 (max 1000), 250K token/request
- Thread-safe: Double-checked locking
- TPM: Per-plan regulator (Starter 20K → Enterprise 500K)
- Retry: 3 attempt, 2-10s exponential backoff

**ClaudeRevize (Rev 2.0):** Canli ingest/retrieval yolunun ana kontrol noktasi `backend/services/embeddings.py` icindeki dogrudan OpenAI singleton yolu. `EmbeddingFactory.auto_select()` production-irrelevant.

### 2.2 Sorunlar ve Implementation Blueprint'leri

---

#### SORUN-E1: Embedding Model Upgrade Yolu (Dusuk Oncelik — Gelecek Planlama)

**Kanit:** `REQUIRED_DIMENSION = 1536`, HNSW index `vector(1536)`.

**IMPLEMENTATION BLUEPRINT (Gelecek Sprint):**

```sql
-- Migration: add_embedding_version_tracking.sql
ALTER TABLE document_chunks
  ADD COLUMN IF NOT EXISTS embedding_model TEXT DEFAULT 'text-embedding-3-small',
  ADD COLUMN IF NOT EXISTS embedding_dim INT DEFAULT 1536,
  ADD COLUMN IF NOT EXISTS embedded_at TIMESTAMPTZ DEFAULT now();

UPDATE document_chunks
SET embedding_model = 'text-embedding-3-small',
    embedding_dim = 1536,
    embedded_at = created_at
WHERE embedding_model IS NULL;
```

---

#### SORUN-E2: Kisa Text Embedding Kalitesi (Dusuk Oncelik)

**IMPLEMENTATION BLUEPRINT:**

```python
# embeddings.py - generate_embeddings_batch_sync icine min-token guard ekle
MIN_EMBEDDING_TOKENS = 10

def generate_embeddings_batch_sync(texts, ...):
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        token_count = len(TIKTOKEN_ENCODER.encode(text)) if text.strip() else 0
        if token_count < MIN_EMBEDDING_TOKENS:
            logger.debug(f"Skipping short text ({token_count} tokens): {text[:50]}")
            continue
        valid_texts.append(text)
        valid_indices.append(i)
    # ... mevcut batch logic valid_texts uzerinde calisir
```

**Dogrulama:**
```sql
SELECT COUNT(*) as short_chunks
FROM document_chunks
WHERE length(content) < 40;  -- ~10 token * 4 char/token
```

---

#### SORUN-E3: TPM Regulator Cross-Worker (Dusuk Oncelik)

**Aksiyon:** Monitor et. Eger production'da OpenAI 429 hatalari artarsa, Redis-based distributed TPM counter implement et.

---

## BOLUM 3: VECTOR STORAGE & HYBRID SEARCH

### 3.1 Mevcut Durum

**Dosyalar:** `supabase/migrations/`, `backend/core/db.py`

- Vector DB: PostgreSQL + pgvector (Supabase hosted)
- Index: HNSW, m=16, ef_construction=64
- Similarity: Cosine distance (`<=>`)
- Hybrid: RRF fusion (`vector_weight=0.7, keyword_weight=0.3`, k=60)
- Security: NULL org_id check, match_count cap 100

**ClaudeRevize (Rev 2.0):** Orijinal rapordaki "ef_search=128 runtime'da set ediliyor" iddiasi Codex tarafindan **reddedildi**. Migration adinda `ef_search=128` yazmasi ile gercekten set edilmesi ayni sey degil — guncel SQL zincirinde `SET LOCAL hnsw.ef_search` komutu bulunmuyor.

**Ghost Protocol Dual-Column Mimarisi (Dogrulandi):**
- `content`: Encrypted (AES-256 Fernet) — aranabilir degil
- `content_search`: Plaintext TSVECTOR (yalnizca word stems) — FTS icin
- Insert: `ingest_document_chunks_batch` RPC'si hem `content_encrypted` hem `content_plaintext` aliyor
- `content_plaintext` sadece `to_tsvector()` icin kullaniliyor, tabloda saklanmiyor

**Tombstone Filtering (Dual-Layer — Dogrulandi):**
- SQL Layer: `compliance_tombstones` tablosu, `document_ids UUID[]` GIN indexed
- App Layer: `compliance_switch.filter_tombstoned_docs()` (chat.py line 1613-1617)

### 3.2 Sorunlar ve Implementation Blueprint'leri

---

#### ~~SORUN-V1: HNSW ef_search Sabit Deger~~ → SORUN-V1-REV: ef_search Durumu Belirsiz (Dusuk Oncelik)

**IMPLEMENTATION BLUEPRINT:**

Adim 1 — Gercek runtime degerini dogrula:
```sql
SHOW hnsw.ef_search;
SELECT current_setting('hnsw.ef_search', true);
```

Adim 2 — Eger default (40) ise ve 10K+ chunk varsa, hybrid_search fonksiyonlarina ekle:
```sql
-- HER IKI fonksiyona da (hybrid_search VE hybrid_search_scoped):
BEGIN
  SET LOCAL hnsw.ef_search = 128;
  -- ... mevcut sorgu
END;
```

> **Best Practice:** Production'da session-level SET kullanma, SET LOCAL veya function-level kullan. Connection pooler reuse'da diger sorgulari etkiler.

---

#### SORUN-V2-REV: Keyword Search Pipeline Kirik (KRITIK — 10/10)

**ClaudeRevize (Rev 2.0):** Orijinal raporda 7/10 olarak derecelendirilmisti. Gercek sorun **4 katmanli:**

**Katman 1 — API search_language gecmiyor:**
```python
# chat.py lines 1545-1595 — HIC search_language parametresi yok
response = await asyncio.to_thread(
    lambda: supabase.rpc("hybrid_search_scoped", {
        "query_text": search_query,
        "query_embedding": query_vector,
        "match_count": ...,
        "filter_org_id": organization_id,
        "filter_scope_ids": [...],
        "similarity_threshold": settings.RAG_RETRIEVAL_THRESHOLD
        # search_language EKSIK → default 'english' kullanilir
    }).execute()
)
```

```python
# search.py lines 158-174 — Ayni sorun
response = supabase.rpc("hybrid_search_scoped", {
    "query_text": payload.query,
    "query_embedding": query_vector,
    "match_count": payload.limit,
    "filter_org_id": organization_id,
    "filter_scope_ids": effective_scope_ids,
    "similarity_threshold": payload.threshold,
    # search_language EKSIK
}).execute()
```

**Katman 2 — Son migration FTS yolu `content_search` yerine `dc.content` kullaniyor:**
`20260303100000_fix_tsvector_regconfig.sql` migration'i `to_tsvector(search_language::regconfig, dc.content)` kullaniyor. Ghost Protocol mimarisinde `dc.content` ENCRYPTED. `content_search` kolonu bu amacla olusturulmustu ama son migration'lar bunu kullanmiyor.

**Katman 3 — GIN index `english` ile olusturulmus:**
Non-English content icin GIN index'ten fayda saglanamaz.

**Katman 4 — Dil bilgisi ingest sirasinda populate edilmiyor:**

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da "document_chunks.language kolonu yok" denmisti. Codex Round 2 bu ifadeyi duzeltdi: `document_chunks.language` kolonu **var** (`supabase/migrations/20260302200000_multilang_search.sql:7-9`). Gercek sorun kolonun yoklugu degil; aktif ingest yolunun bu alani **hic populate etmemesi** ve retrieval tarafinin bunu **fiilen kullanmamasi** (`backend/core/ingestion_utils.py:117-125`, `backend/worker/tasks.py:869-875`).

**IMPLEMENTATION BLUEPRINT (4 Adimli Fix):**

> **ClaudeRevize (Rev 3.0) — FTS Strateji Karari:** Rev 2.0'da Adim 2'de per-language query parsing (english/german/turkish vb.) onerilmisti, Adim 4'te ise ingest tarafinda `to_tsvector('simple', ...)` kullanimi onerilmisti. Codex Round 2 bu ikisinin birbiriyle celisdigini tespit etti: eger `content_search` lexeme'leri `simple` ile uretilecekse, query tarafinda da `simple` kullanmak **zorunlu**. Per-language query parsing ancak row-level dil bazli lexeme uretimi varsa anlamli olur — ki bu su an yok ve kisa vadede planlanmiyor.
>
> **KARAR: Hem ingest hem query tarafinda tutarli olarak `'simple'` kullanilacak.** Bu, stemming kaybina ragmen tum dillerde tutarli ve guvenilir sonuc verir. Turkce icin `'turkish'` regconfig mevcut ama stemming kalitesi sinirli, risk/odun karsilastirmasinda `'simple'` kazaniyor.

**Adim 1 — content_search kullanimini geri getir + tutarli 'simple' regconfig (KRITIK):**
```sql
-- Migration: fix_fts_pipeline_v3.sql
-- HER IKI fonksiyon da (hybrid_search VE hybrid_search_scoped) guncellenmeli

CREATE OR REPLACE FUNCTION hybrid_search_scoped(
    query_text TEXT,
    query_embedding VECTOR(1536),
    match_count INT DEFAULT 10,
    filter_org_id UUID DEFAULT NULL,
    filter_scope_ids TEXT[] DEFAULT NULL,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    similarity_threshold FLOAT DEFAULT 0.25,
    search_language TEXT DEFAULT 'simple'
)
RETURNS TABLE(...) AS $$
BEGIN
  SET LOCAL hnsw.ef_search = 128;

  RETURN QUERY
  WITH
  tombstoned_docs AS (
      SELECT UNNEST(t.document_ids) AS blocked_doc_id
      FROM compliance_tombstones t
      WHERE t.organization_id = filter_org_id
        AND t.status = 'active'
  ),
  semantic_results AS (
      SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
             dc.content_search,
             1 - (dc.embedding <=> query_embedding) AS vector_score,
             ROW_NUMBER() OVER (ORDER BY dc.embedding <=> query_embedding) AS vector_rank
      FROM document_chunks dc
      JOIN documents d ON dc.document_id = d.id
      WHERE d.organization_id = filter_org_id
        AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
        AND 1 - (dc.embedding <=> query_embedding) >= similarity_threshold
        AND NOT EXISTS (SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id)
      ORDER BY dc.embedding <=> query_embedding
      LIMIT match_count * 2
  ),
  keyword_results AS (
      SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
             -- content_search KULLAN (encrypted content degil!)
             -- 'simple' regconfig — ingest tarafindaki ile TUTARLI
             ts_rank_cd(dc.content_search, plainto_tsquery('simple', query_text), 32) AS keyword_score,
             ROW_NUMBER() OVER (
               ORDER BY ts_rank_cd(dc.content_search, plainto_tsquery('simple', query_text), 32) DESC
             ) AS keyword_rank
      FROM document_chunks dc
      JOIN documents d ON dc.document_id = d.id
      WHERE d.organization_id = filter_org_id
        AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
        AND dc.content_search @@ plainto_tsquery('simple', query_text)
        AND NOT EXISTS (SELECT 1 FROM tombstoned_docs td WHERE td.blocked_doc_id = d.id)
      ORDER BY keyword_score DESC
      LIMIT match_count * 2
  ),
  -- RRF Fusion (mevcut mantik ayni)
  ...
$$;

-- AYNI duzeltme hybrid_search (unscoped) fonksiyonuna da uygulanmali!
-- Chat akisi explicit/all-scope yoksa hybrid_search RPC'sine dusuyor
-- (backend/api/v1/chat.py:1586-1594)
-- /search endpoint'i de scoped ve unscoped iki yolu kullaniyor
-- (backend/api/v1/search.py:158-174)
```

> **ClaudeRevize (Rev 3.0):** Rev 2.0'daki SQL blueprint'inde `d.deleted_at IS NULL` filtresi vardi. Codex Round 2 bunu reddetti: `documents.deleted_at` kolonu mevcut repo semasinda **bulunmuyor**. Migration ve backend taramasinda bu kolon yok. Tombstone exclusion bugun yalnizca `compliance_tombstones` CTE'si ve chat tarafindaki app-layer filter ile temsil ediliyor. Bu Rev 3.0'da `d.deleted_at` tamamen kaldirildi.

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da `search_language` parametresi sadece `hybrid_search_scoped` icin dusunulmustu. Codex Round 2 bunu genisletti: chat akisi `hybrid_search` (unscoped) RPC'sine de dusebiliyor, `/search` endpoint'i de her iki yolu kullaniyor. **Tum hybrid search SQL fonksiyonlari ayni duzeltmeyi almali.**

**Adim 2 — API'den search_language gonder (her iki endpoint + her iki RPC):**
```python
# chat.py - guardrails.py zaten dil tespiti yapiyor
guardrail_result = await analyze_query_with_context(...)

# DOGRU alan adi: guardrail_result.language (guardrails.py:63-79)
# NOT: .detected_language DEGIL — bu alan GuardrailResult'ta yok
detected_lang = guardrail_result.language or "simple"
```

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da `guardrail_result.detected_language` kullanilmisti. Codex Round 2 bunu duzeltdi: GuardrailResult dataclass'inda alan adi `language` (`backend/services/guardrails.py:63-79`), chat akisi da `guardrail_result.language` okuyor (`backend/api/v1/chat.py:1338-1343`). Dogru alan adi: **`guardrail_result.language`**.

```python
# TUTARLI 'simple' stratejisi nedeniyle LANG_MAP basitlesti:
# Tum content_search lexeme'leri 'simple' ile uretildigi icin
# query tarafinda da 'simple' kullanmak ZORUNLU.
# Per-language mapping YALNIZCA content_search row-level dil bazli
# lexeme uretirse anlamli olur (gelecek iyilestirme).
search_lang = "simple"

# HER IKI RPC cagrisina da ekle:
# 1. hybrid_search_scoped (chat.py + search.py)
response = supabase.rpc("hybrid_search_scoped", {
    "query_text": search_query,
    "query_embedding": query_vector,
    "match_count": ...,
    "filter_org_id": organization_id,
    "filter_scope_ids": [...],
    "similarity_threshold": settings.RAG_RETRIEVAL_THRESHOLD,
    "search_language": search_lang  # YENI
}).execute()

# 2. hybrid_search (unscoped fallback — chat.py:1586-1594)
response = supabase.rpc("hybrid_search", {
    "query_text": search_query,
    "query_embedding": query_vector,
    "match_count": ...,
    "filter_org_id": organization_id,
    "similarity_threshold": settings.RAG_RETRIEVAL_THRESHOLD,
    "search_language": search_lang  # YENI
}).execute()
```

**Adim 3 — GIN index yeniden olustur:**
```sql
-- Migration: fix_gin_index_simple.sql
DROP INDEX IF EXISTS idx_document_chunks_content_search;
CREATE INDEX idx_document_chunks_content_search
  ON document_chunks USING GIN (content_search);
-- content_search zaten TSVECTOR, GIN index regconfig gerektirmez
```

**Adim 4 — Ingest sirasinda content_search'u `simple` ile olustur:**
```sql
-- ingest_document_chunks_batch RPC'sinde:
-- ONCE:
to_tsvector('english', COALESCE(chunk->>'content_plaintext', ''))
-- SONRA:
to_tsvector('simple', COALESCE(chunk->>'content_plaintext', ''))
```

**Adim 5 — YENI: Mevcut content_search verisini backfill et:**

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da bu adim tamamen eksikti. Codex Round 2 bunu tespit etti: Adim 4 yalniz **yeni** ingest'leri duzeltir. Mevcut `content_search` satirlari `to_tsvector('english', ...)` ile uretilmis durumda. Ghost Protocol plaintext'i DB'de tutmadigi icin salt SQL migration yeterli degil — **kontrollu app-side re-ingest gerekir.**

**Backfill Stratejisi:**

```
YAKLASIM A — Kontrollu Re-ingest (ONERILEN):
1. Backfill icin script olustur:
   python backend/scripts/backfill_content_search.py --org-id=... --batch-size=100
   (Repo'daki mevcut utility script pattern'i: backend/scripts/)

2. Script akisi:
   a. documents tablosu uzerinden org_id filtrele, JOIN ile document_chunks'a ulas
   b. content (encrypted) alanini Ghost Protocol ile decrypt et
   c. Decrypt edilmis plaintext'i to_tsvector('simple', ...) ile yeniden olustur
   d. content_search alanini guncelle

3. Neden salt SQL yetmez:
   - content kolonu AES-256 Fernet ile encrypted
   - Decryption application-side (Python Fernet key) — SQL icinden yapilamaz
   - content_plaintext tabloda saklanmiyor (yalnizca ingest sirasinda gecici)

4. Guvenlik:
   - Plaintext HICBIR ZAMAN DB'ye yazilmaz (mevcut Ghost Protocol kontrati)
   - Sadece content_search TSVECTOR guncellenir
   - Batch halinde isleyin, tum tabloyu kilitlemek yok
```

> **ClaudeRevize (Rev 4.0):** Rev 3.0'da `management/commands/` klasoru ve `backend.core.encryption.decrypt_content` fonksiyonu varsayilmisti. Codex Round 3 duzeltdi: codebase'de `manage.py` / `management/commands` yok, utility script'ler `backend/scripts/` altinda yasiyor. Dogru decryption fonksiyonu `decrypt_text` (`backend/core/security.py:262`). Ayrica `document_chunks` tablosunda `organization_id` kolonu yok — org baglami `documents` tablosu uzerinden JOIN ile saglanir.

```python
# backend/scripts/backfill_content_search.py
from backend.core.security import decrypt_text  # Ghost Protocol — dogru fonksiyon adi

async def backfill_content_search(org_id: str, batch_size: int = 100):
    """Mevcut content_search'u 'simple' regconfig ile yeniden olustur."""
    offset = 0
    total_updated = 0

    while True:
        # document_chunks'ta organization_id YOK — documents uzerinden JOIN
        rows = supabase.table("document_chunks") \
            .select("id, content, document_id, documents!inner(organization_id)") \
            .eq("documents.organization_id", org_id) \
            .range(offset, offset + batch_size - 1) \
            .execute()

        if not rows.data:
            break

        for row in rows.data:
            # Ghost Protocol decrypt (core.security.decrypt_text)
            plaintext = decrypt_text(row["content"])

            # content_search'u 'simple' ile guncelle
            supabase.rpc("update_content_search_simple", {
                "chunk_id": row["id"],
                "plaintext": plaintext
            }).execute()
            total_updated += 1

        offset += batch_size
        logger.info(f"Backfill progress: {total_updated} chunks updated")

    logger.info(f"Backfill complete: {total_updated} total chunks")
```

> **Codex Comment:** Bu backfill ornegi mevcut repo yuzeyiyle birebir uyusmuyor. Proje Django degil; workspace'te `manage.py` veya `management/commands` yapisi gorunmuyor, daha cok `backend/scripts/` pattern'i var. Ayrica decrypt helper adi da farkli: codebase'de kullanilan fonksiyon `core.security.decrypt_text`, `backend.core.encryption.decrypt_content` degil.

> **Codex Comment:** Ornekte `document_chunks` tablosunda `.eq("organization_id", org_id)` filtresi kullaniliyor, fakat mevcut schema/migration zincirinde `document_chunks.organization_id` gorunmuyor; org baglami `documents` tablosu uzerinden geliyor. Backfill batch'i ya `documents` ile join eden bir RPC uzerinden ya da once ilgili `document_id` setini cikarip sonra chunk'lari onunla yurutarak tasarlanmalı.

```sql
-- Backfill icin yardimci RPC (plaintext'i sadece TSVECTOR'e cevirir, saklamaz)
CREATE OR REPLACE FUNCTION update_content_search_simple(
    chunk_id UUID,
    plaintext TEXT
) RETURNS VOID AS $$
BEGIN
    UPDATE document_chunks
    SET content_search = to_tsvector('simple', COALESCE(plaintext, ''))
    WHERE id = chunk_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Adim 6 — document_chunks.language kolonunu populate et (Gelecek Iyilestirme):**

> **ClaudeRevize (Rev 3.0):** Kolon var ama bos. Simdilik `'simple'` stratejisi dil bilgisine ihtiyac duymuyor. Gelecekte per-language FTS istenirse, ingest sirasinda guardrails dil tespitini language kolonuna yazmak gerekecek.

```python
# tasks.py - ingest_document_batched icinde (GELECEK)
# Chunk metadata'ya dil bilgisi ekle:
chunk_data["language"] = detected_language or "unknown"
```

**Dogrulama:**
```sql
-- Turkce content ile test (backfill sonrasi)
SELECT ts_rank_cd(
  to_tsvector('simple', 'proje yonetimi analiz raporu hazirlama'),
  plainto_tsquery('simple', 'proje raporu')
) as score;
-- Score > 0 olmali

-- Backfill dogrulamasi: regconfig tutarliligi
-- Tum content_search satirlarinin 'simple' ile erisilebildigini dogrula
SELECT COUNT(*) as total,
  COUNT(CASE WHEN content_search @@ plainto_tsquery('simple', 'test') THEN 1 END) as searchable
FROM document_chunks
WHERE content_search IS NOT NULL;
```

---

#### SORUN-V3-NEW: Tombstone Exclusion Regresyonu (YUKSEK — 8/10)

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da "tasimimis olabilir" ifadesi kullanilmisti. Codex Round 2 bunu guclendirdi: Bu **teyit edilmis** bir regresyon. En son migration govdesinde (`supabase/migrations/20260303100000_fix_tsvector_regconfig.sql:153-270`) tombstone CTE **gorunmuyor**; buna karsilik eski `20260203000012_hybrid_search_tombstone_filter.sql:191-255` dosyasinda acikca vardi. Dolayisiyla tombstone CTE'si migration zincirinde kaybolmus.

**Kanit:**
- En son migration'daki `hybrid_search_scoped` govdesinde tombstone CTE YOK (kesin)
- Eski migration'da (`20260203000012`) acikca VARDI
- chat.py line 1613-1617: `compliance_switch.filter_tombstoned_docs()` VAR (app-layer yedek)
- search.py: Boyle bir app-layer filter YOK

**IMPLEMENTATION BLUEPRINT:**

Adim 1 — `pg_get_functiondef` ile runtime dogrulamasi yap (kesin teyit):
```sql
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'hybrid_search_scoped'
ORDER BY oid DESC LIMIT 1;
-- "compliance_tombstones" gorulmeli — gorulmuyorsa regresyon kesin
```

Adim 2 — V2-REV migration'ina tombstone CTE'si dahil (yukaridaki Adim 1 blueprint'inde zaten var).

Adim 3 — `/search` endpoint'ine app-layer tombstone filter ekle:
```python
# search.py - chat.py'deki pattern'i kopyala
from services.compliance_switch import compliance_switch

# Hybrid search sonuclarindan sonra:
matches = _decrypt_search_results(matches)
# YENI: Tombstone filter
matches = await compliance_switch.filter_tombstoned_docs(matches, organization_id)
```

**Dogrulama:** Bir dokumani tombstone'a ekle, `/search` endpoint'inden arayarak sonuclarda gorulmedigini dogrula.

---

## BOLUM 4: RETRIEVAL & RANKING

### 4.1 Mevcut Durum

**Threshold Zinciri:**
| Asama | Threshold | Neye Uygulanir |
|-------|-----------|----------------|
| Hybrid Search | 0.25 | vector_score (retrieval CTE'sinde) |
| Scope Analysis | 0.25 | Dominance Guard icin minimum |
| Quality Gate | 0.35 | vector_score/similarity (context'e kabul) |
| Guardrail Preflight | 0.35 | match_documents RPC |

**Reranking:** Cohere `rerank-v3.5`, top_k=12 (default), 20 (comparison). Hata durumunda sessizce original order'a doner.

**Output Filter (Codex Onayli, Kisitlamalar Netlestirildi):**

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da output filter'in "citation index dogrulama" yaptigi belirtilmisti ama davranis detaylandirilmamisti. Codex Round 2 netlistirdi: `output_filter.py` citation index'lerini **tespit ediyor** ama **otomatik duzeltmiyor**. `invalid_citations` bulununca `OutputFilterResult.is_safe=false` oluyor, fakat `filtered_text` degismiyor (`backend/services/output_filter.py:53-95`). Chat akisi yalnizca `pii_detected` durumunda cevabi rewrite ediyor (`backend/api/v1/chat.py:2168-2181`). Bu, invalid citation'in kullaniciya ulasabilecegi anlamina gelir.

**Pratik Etki:** Eger LLM `[3]` referansi uretir ama sadece 2 source varsa, output filter bunu log'a yazar ama cevabi degistirmez. Kullanici gecersiz citation gorur. Bu, faithfulness guard (H1) ile birlikte ele alinmali.

### 4.2 Sorunlar ve Implementation Blueprint'leri

---

#### SORUN-R1: Reranker Zorunlu Degil + Monitoring Eksik (Yuksek Oncelik — 7/10)

**IMPLEMENTATION BLUEPRINT:**

```python
# main.py veya startup hook'unda:
import os, logging
logger = logging.getLogger(__name__)

def _check_reranker_availability():
    key = os.getenv("COHERE_API_KEY")
    if not key:
        logger.error(
            "COHERE_API_KEY not set — reranking DISABLED. "
            "RAG quality will be degraded."
        )
    else:
        logger.info("Cohere reranker available (rerank-v3.5)")

_check_reranker_availability()
```

> **ClaudeRevize (Rev 3.0):** Rev 2.0'daki metric orneginde iki sorun vardi: (1) `retrieval_score` Histogram'ina rerank_score yazmak veri setini karistirirdi (bu metrik retrieval similarity icin tanimli), (2) Hot path icinde `Counter(...)` tanimlamak duplicate registration riski tasir. Codex Round 2 her ikisini de tespit etti.
>
> **Duzeltme:** Tum yeni metrikler `backend/core/metrics.py` icinde module-level tanimlanmali, hot path'te import edilmeli.

```python
# backend/core/metrics.py — MODULE-LEVEL TANIMLAR (mevcut metriklerin yanina)
from prometheus_client import Counter, Histogram

# YENI: Reranker metrikleri (mevcut retrieval_score'dan AYRI)
rerank_score_histogram = Histogram(
    "rerank_score", "Cohere rerank score distribution",
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
rerank_skipped_total = Counter(
    "rerank_skipped_total", "Reranking skipped",
    ["reason"]
)
```

```python
# chat.py - reranking sonrasi (IMPORT ile kullan, tanimla degil)
from core.metrics import rerank_score_histogram, rerank_skipped_total

# Reranking uygulandiginda:
for doc in reranked_docs:
    rerank_score_histogram.observe(doc.get("rerank_score", 0))

# Reranking ATLANDIGINDA:
if not reranker_available:
    rerank_skipped_total.labels(reason="no_api_key").inc()
elif len(docs) <= rerank_top_k:
    rerank_skipped_total.labels(reason="below_threshold").inc()
```

---

#### SORUN-R2: Confidence Score Yok (Yuksek Oncelik — 7/10)

**Fraz 2'ye tasindi** (Rev 2.0 karari korundu). Go-live blocker degil, once request-level analytics alt yapisi kurulmali.

**IMPLEMENTATION BLUEPRINT:**

```python
# services/confidence.py — Yeni modul
from dataclasses import dataclass

@dataclass
class ConfidenceResult:
    score: float          # 0.0 - 1.0
    level: str            # "high", "medium", "low"
    factors: dict

def compute_confidence(
    docs: list[dict],
    rerank_applied: bool,
    scope_classification: str,
    scope_dominance_ratio: float,
) -> ConfidenceResult:
    if not docs:
        return ConfidenceResult(score=0.0, level="low", factors={})

    top_k = docs[:5]
    avg_sim = sum(
        d.get("vector_score", d.get("similarity", 0)) for d in top_k
    ) / len(top_k)

    if rerank_applied:
        avg_rerank = sum(d.get("rerank_score", 0) for d in top_k) / len(top_k)
    else:
        avg_rerank = avg_sim * 0.8

    scope_score = scope_dominance_ratio if scope_classification != "fragmented" else 0.3
    citation_coverage = min(len(docs) / 5.0, 1.0)

    score = (
        0.4 * avg_sim +
        0.3 * avg_rerank +
        0.2 * scope_score +
        0.1 * citation_coverage
    )

    level = "high" if score >= 0.7 else "medium" if score >= 0.45 else "low"

    return ConfidenceResult(
        score=round(score, 3),
        level=level,
        factors={
            "avg_similarity": round(avg_sim, 3),
            "avg_rerank": round(avg_rerank, 3),
            "scope_clarity": round(scope_score, 3),
            "citation_coverage": round(citation_coverage, 3),
        }
    )
```

SSE entegrasyonu icin not: Mevcut SSE contract'i `status`, `token`, `heartbeat`, `sources`, `scope_context`, `done` tiplerini kullaniyor. `metadata` tipi eklenecekse frontend event consumer da guncellenmeli.

---

#### SORUN-R3: Threshold Dogrulanmamis (Orta Oncelik — 6/10)

**IMPLEMENTATION BLUEPRINT:**

```python
# eval/rag_eval_dataset.py
EVAL_DATASET = [
    {
        "query": "S3 connector'un rate limit degeri nedir?",
        "expected_answer_contains": ["1000"],
        "expected_scope": "github://axiohub/backend",
        "type": "answerable",
    },
    {
        "query": "Mars'a gidis tarihi ne zaman?",
        "expected_answer_contains": ["bulamadim", "couldn't find"],
        "type": "unanswerable",
    },
    {
        "query": "Proje deadline'i ne zaman?",
        "expected_scope": None,
        "type": "answerable",
    },
]

async def evaluate_threshold(threshold: float, dataset: list):
    correct = 0
    for item in dataset:
        # ... RAG pipeline'i bu threshold ile calistir
        # ... cevabi expected ile karsilastir
        pass
    return {"threshold": threshold, "accuracy": correct / len(dataset)}
```

---

## BOLUM 5: HALLUCINATION & GUARDRAILS

### 5.1 Mevcut Durum

**Koruma Katmanlari (Dogrulandi + Codex Ek):**
1. Intent Classification: Groq llama-3.1-8b-instant, temperature=0
2. Preflight Document Check: match_documents RPC
3. Context-Aware Override: OFF_TOPIC → RAG_QUERY (eger preflight match bulursa)
4. Prompt Injection Detection: 10 regex pattern
5. Scope Identity Sanitization: 7 injection pattern
6. **Output Filter (Codex Ek):** PII redaction + citation index detection (tespit eder ama duzeltmez — bkz. Bolum 4.1)

### 5.2 Sorunlar ve Implementation Blueprint'leri

---

#### SORUN-H1: Post-Generation Faithfulness Check Yok (KRITIK — 9/10)

**Kanit:** Guardrails pre-generation. Output filter post-generation ama sadece PII + citation index tespit. Cevaptaki claim'lerin retrieved context ile tutarliligi kontrol edilmiyor.

**IMPLEMENTATION BLUEPRINT — LLM-as-Judge Yaklasimi:**

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da `_call_groq_guardrail` import ediliyordu. Codex Round 2 bunu reddetti: repo'da boyle bir import edilebilir helper **yok**. Guardrail akisi `GuardrailService._get_model().ainvoke(...)` ve `analyze_query_with_context()` uzerinden ilerliyor.

> **ClaudeRevize (Rev 4.0):** Rev 3.0'da `GuardrailService()._get_model()` private metoduna disaridan erisim onerilmisti. Codex Round 3 bunu kirilgan buldu — `_get_model()` private method, yalnizca class icinden cagrilmali. Dogru yaklasim: (A) GuardrailService'e yeni bir **public method** eklemek (`check_faithfulness`) veya (B) mevcut `LLMFactory.get_guardrail_model()` factory'yi dogrudan kullanmak. Opsiyon A tercih edildi — service encapsulation korunur.

```python
# services/faithfulness_guard.py
import json
import logging
from core.llm_factory import LLMFactory

logger = logging.getLogger(__name__)

FAITHFULNESS_PROMPT = """You are a faithfulness checker. Given CONTEXT (retrieved documents) and ANSWER (LLM response), check if every claim in the answer is supported by the context.

CONTEXT:
{context}

ANSWER:
{answer}

Respond in JSON:
{{
  "faithful": true/false,
  "unsupported_claims": ["list of claims not found in context"],
  "score": 0.0-1.0
}}

Rules:
- A claim is "supported" if the context contains the same information
- Generic/introductory sentences don't need support
- Numbers, dates, and names MUST be in the context to be supported
- If answer says "I couldn't find" or similar, it's automatically faithful
"""

async def check_faithfulness(
    context_chunks: list[str],
    answer: str,
    max_context_chars: int = 3000
) -> dict:
    """Post-generation faithfulness check."""
    # "Bulunamadi" cevaplari otomatik faithful
    no_info_phrases = ["bulamadim", "couldn't find", "no relevant", "bilgi bulunamadi"]
    if any(phrase in answer.lower() for phrase in no_info_phrases):
        return {"faithful": True, "unsupported_claims": [], "score": 1.0}

    context_text = "\n---\n".join(
        c[:500] for c in context_chunks[:6]
    )[:max_context_chars]

    prompt = FAITHFULNESS_PROMPT.format(context=context_text, answer=answer[:1500])

    try:
        # YAKLASIM A (ONERILEN): GuardrailService'e public method ekle
        # guardrails.py'ye eklenecek:
        #   async def check_faithfulness(self, prompt: str) -> str:
        #       model = self._get_model()  # private method ICERIDEN cagrilir
        #       result = await model.ainvoke(prompt)
        #       return result.content
        #
        # Kullanim:
        # from services.guardrails import guardrail_service  # singleton (line 515)
        # raw_result = await guardrail_service.check_faithfulness(prompt)

        # YAKLASIM B (ALTERNATIF): LLMFactory dogrudan kullan
        # GuardrailService._get_model() zaten LLMFactory.get_guardrail_model()
        # cagiriyor — ayni factory'yi dogrudan kullanmak private method'a
        # bagimlilik yaratmaz:
        model = LLMFactory.get_guardrail_model()
        result = await model.ainvoke(prompt)
        parsed = json.loads(result.content)
        return {
            "faithful": parsed.get("faithful", True),
            "unsupported_claims": parsed.get("unsupported_claims", []),
            "score": parsed.get("score", 0.5),
        }
    except Exception as e:
        logger.warning(f"Faithfulness check failed: {e}")
        return {"faithful": True, "unsupported_claims": [], "score": 0.5}
```

> **Implementasyon Notu:** Yaklasim A (public method) tercih edilir — GuardrailService zaten model lifecycle'ini yonetiyor (lazy load, singleton). Yaklasim B (LLMFactory dogrudan) daha hizli implement edilir ama service katmanini bypass eder. Her iki yaklasim da `_get_model()` private methoduna disaridan erisim gerektirmez.

> **Codex Comment:** Bu revizyon oncekine gore repo pattern'ine daha yakin; ancak hala `GuardrailService._get_model()` gibi private bir metoda disaridan bagimli. Uygulama asamasinda bunu public bir `invoke_json_guardrail(...)` / `run_guardrail_prompt(...)` helper'iyle sarmalamak daha saglikli olur; aksi halde guardrails internals degistikce faithfulness modulu kirilgan kalir.

**Chat pipeline entegrasyonu — Streaming + Non-Stream ayirimi:**

> **ClaudeRevize (Rev 3.0):** SSE streaming akisinda token'lar parca parca client'a gonderiiliyor, cevap bittikten sonra calisan faithfulness check yaniti **geri cekemez**.

> **ClaudeRevize (Rev 4.0):** Rev 3.0'da ayri bir `{"type": "warning", ...}` SSE event'i onerilmisti. Codex Round 3 bunu duzeltdi: mevcut akista `done` event'i zaten opsiyonel `warning` field'i destekliyor (`chat.py:2458-2461`). Yeni event tipi yerine mevcut `done.warning` pattern'ini genisletmek frontend degisikligi gerektirmez.

```python
# chat.py — STREAMING yolunda:
# Cevap tamamen stream edildikten SONRA, done event'i olusturulurken:
faith_result = await check_faithfulness(
    context_chunks=[d.get("content", "") for d in high_quality_docs],
    answer=full_answer_text  # stream sirasinda biriktirilen tam cevap
)

# Mevcut done event pattern'i (chat.py:2458-2461):
#   done_event = {'type': 'done', 'message_id': message_id}
#   if _save_warning:
#       done_event['warning'] = _save_warning
#   yield _safe_sse_json(done_event)

# Faithfulness warning'i AYNI pattern uzerinden:
done_event = {'type': 'done', 'message_id': message_id}
if _save_warning:
    done_event['warning'] = _save_warning
if not faith_result["faithful"]:
    logger.warning("Faithfulness FAILED: %s", faith_result["unsupported_claims"])
    done_event['faithfulness_warning'] = (
        "Bu cevaptaki bazi bilgiler kaynaklardan tam dogrulanamadi."
    )
    done_event['unsupported_claims'] = faith_result["unsupported_claims"]
yield _safe_sse_json(done_event)

# chat.py — NON-STREAM yolunda (ChatResponse):
# Cevap donmeden ONCE check yapilabilir:
faith_result = await check_faithfulness(
    context_chunks=[d.get("content", "") for d in high_quality_docs],
    answer=answer
)
if not faith_result["faithful"]:
    answer += "\n\n> Bu cevaptaki bazi bilgiler kaynaklardan tam dogrulanamadi."
```

**Latency Etkisi:** Groq llama-3.1-8b-instant ~200ms. Streaming'de done event olusturulmadan once calisir. Non-stream'de +200ms eklenir.

---

#### SORUN-H2: "I Don't Know" Davranisi Prompt-Based (YUKSEK — Kritik'e Yukseldi)

**ClaudeRevize (Rev 2.0):** Mevcut kod bos-context durumunda LLM cagrisini bypass etmiyor; sadece context'e `[No relevant documents found ...]` satiri koyup yine generation'a gidiyor.

> **ClaudeRevize (Rev 3.0):** Rev 2.0'daki blueprint yalnizca streaming generator yoluna uyuyordu (`yield`). Codex Round 2 bunu tespit etti: kod tabaninda ayri bir non-stream `ChatResponse` yolu da var (`backend/api/v1/chat.py:1381-1397`, `:2231-2238`). Deterministic no-answer karari tek helper'da toplanmazsa iki akisin davranisi ayrisabilir.
>
> **Duzeltme:** Paylasilmis helper fonksiyon + her iki path icin entegrasyon.

**IMPLEMENTATION BLUEPRINT:**

```python
# services/no_answer.py — Paylasilmis helper (HER IKI path icin)
NO_ANSWER_MESSAGE = (
    "Dokumanlarda bu soruyla ilgili yeterli bilgi bulunamadi. "
    "Farkli bir arama terimi deneyebilir veya ilgili kaynaklari baglayabilirsiniz."
)

def should_return_no_answer(docs: list[dict], threshold: float) -> bool:
    """Deterministic karar: quality gate'i gecen dok var mi?"""
    high_quality = [d for d in docs
        if d.get("vector_score", d.get("similarity", 0)) >= threshold]
    return len(high_quality) == 0

def build_no_answer_response() -> dict:
    """Non-stream ChatResponse icin standart yapit."""
    return {
        "answer": NO_ANSWER_MESSAGE,
        "sources": [],
        "confidence": 0.0,
        "confidence_level": "low",
        "no_answer": True,
    }
```

```python
# chat.py — STREAMING yolunda:
from services.no_answer import should_return_no_answer, NO_ANSWER_MESSAGE, build_no_answer_response

if should_return_no_answer(docs, settings.RAG_SIMILARITY_THRESHOLD):
    yield json.dumps({"type": "token", "content": NO_ANSWER_MESSAGE}) + "\n"
    yield json.dumps({"type": "sources", "sources": []}) + "\n"
    yield json.dumps({"type": "done"}) + "\n"
    return  # LLM cagrilmaz, token harcanmaz

# chat.py — NON-STREAM yolunda (ChatResponse):
if should_return_no_answer(docs, settings.RAG_SIMILARITY_THRESHOLD):
    no_answer = build_no_answer_response()
    return ChatResponse(
        answer=no_answer["answer"],
        sources=no_answer["sources"],
        # ... diger alanlar
    )
```

**Dogrulama:** Hicbir dokuman baglanmamis bir scope'ta sorgu yap, deterministic mesajin dondugunu ve LLM token kullanilmadigini dogrula. **HER IKI** path'i test et (streaming ve direct ChatResponse).

---

## BOLUM 6: SEMANTIC CACHE

### 6.1 Mevcut Durum

- Backend: Redis (async), DEVRE DISI (`SEMANTIC_CACHE_ENABLED = False`)
- TTL: 3600s, Key: SHA-256(quantized_embedding + scope_ids)
- Mevcut Prometheus: `semantic_cache_ops` counter (hit/miss/put/error)

### 6.2 Sorunlar

---

#### SORUN-SC-NEW: Cross-Tenant Cache Key Vulnerability (KRITIK — Feature Acilirsa 10/10)

**Kanit (semantic_cache.py lines 66-77):**
```python
def _cache_key(self, query_embedding, scope_ids):
    quantized = [round(v, 4) for v in query_embedding]
    scope_key = "|".join(sorted(scope_ids)) if scope_ids else "__global__"
    raw = f"{quantized}:{scope_key}"
    return f"sem_cache:{hashlib.sha256(raw.encode()).hexdigest()}"
    # organization_id YOK! allowed_scopes YOK!
```

**Risk:** Feature acilirsa, Org-A'nin cevabi Org-B'ye donebilir. Ayrica ayni org icinde farkli `allowed_scopes` setlerine sahip kullanicilar arasinda da yanlis hit riski var.

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da yalnizca `organization_id` eklenmesi onerilmisti. Codex Round 2 bunu genisletti: bugunku cache key girdisi `scope_ids_for_cache = [payload.scope_id] if payload.scope_id else []` uzerinden kuruluyor. Bu, ayni org icinde farkli `allowed_scopes` setlerine sahip kullanicilar arasinda da yanlis hit riski birakir. Key'in **effective retrieval scope set'ini** de kapsamasi gerekir.

**IMPLEMENTATION BLUEPRINT:**

```python
# semantic_cache.py - _cache_key'e org_id + effective scope set ekle
def _cache_key(
    self,
    query_embedding: list[float],
    scope_ids: list[str],
    org_id: str,
    allowed_scopes: list[str] | None = None
) -> str:
    """
    Cache key = org_id + effective scope set + quantized embedding.
    allowed_scopes: kullanicinin erisim yetkisi olan tum scope'lar.
    scope_ids: kullanicinin bu query icin sectigi scope'lar.
    Her ikisi de key'e girmeli — ayni query, farkli erisim = farkli sonuc.
    """
    quantized = [round(v, 4) for v in query_embedding]
    scope_key = "|".join(sorted(scope_ids)) if scope_ids else "__global__"
    allowed_key = "|".join(sorted(allowed_scopes)) if allowed_scopes else "__all__"
    raw = f"{org_id}:{allowed_key}:{scope_key}:{quantized}"
    return f"sem_cache:{hashlib.sha256(raw.encode()).hexdigest()}"

# put() ve get() metotlarinin imzasina org_id + allowed_scopes ekle
async def get(self, query_embedding, scope_ids, org_id: str, allowed_scopes: list[str] | None = None):
    key = self._cache_key(query_embedding, scope_ids, org_id, allowed_scopes)
    # ...

async def put(self, query_embedding, scope_ids, org_id: str, allowed_scopes: list[str] | None = None, answer=None, sources=None):
    key = self._cache_key(query_embedding, scope_ids, org_id, allowed_scopes)
    # ...
```

> **ClaudeRevize (Rev 4.0):** Rev 3.0'da `user_allowed_scopes` degisken adi kullanilmisti. Codex Round 3 duzeltdi: chat endpoint'inde dependency adi `allowed_scopes` (`chat.py:1286: allowed_scopes: list[str] | None = Depends(get_user_allowed_scopes)`). Tum referanslar `allowed_scopes` olarak duzeltildi.

```python
# chat.py - cache cagrilarinda org_id + allowed_scopes gec
# allowed_scopes: endpoint dependency'den gelen degisken (chat.py:1286)
cached = await semantic_cache.get(
    query_vector,
    scope_ids_for_cache,
    organization_id,
    allowed_scopes=allowed_scopes  # endpoint dependency (Depends(get_user_allowed_scopes))
)

# Cache put:
await semantic_cache.put(
    query_vector,
    scope_ids_for_cache,
    organization_id,
    allowed_scopes=allowed_scopes,
    answer=answer,
    sources=sources_metadata
)
```

> **Codex Comment:** Buradaki degisken adi da repo ile birebir uyusmuyor. Chat endpoint imzasinda mevcut dependency adi `allowed_scopes` (`backend/api/v1/chat.py:1281-1287`); `allowed_scopes` yeni bir degisken olarak tanimli degil. Uygulama degisikliginde isim birligi korunmali.

**Bu fix, feature acilmadan ONCE yapilmali.** Feature su an kapali oldugu icin aktif risk yok, ama kod fix'i simdi yapilmali ki feature acildiginda hazir olsun.

---

## BOLUM 7: INGESTION PIPELINE

### 7.1 Sorunlar

---

#### SORUN-I1: Chunk Replace Race Condition (Orta Oncelik — 4/10)

**IMPLEMENTATION BLUEPRINT — Atomic Swap:**

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da `source_id` yeniden kullanimi onerisi vardi. Codex Round 2 bunu detaylandirdi: Repo'da dedup icin `(organization_id, source_id)` uzerinde normal index var ve bir RPC bu kolonu `ON CONFLICT (organization_id, source_id)` ile kullaniyor, **fakat migration zincirinde ayni anahtar icin acik bir UNIQUE constraint gorunmuyor**. Atomic-swap tasarimi constraint gercegi ile birlikte tekrar dogrulanmali.

```python
# tasks.py - ingest_document_batched icinde
# MEVCUT (race condition):
# delete_rows_with_retry(supabase, "document_chunks", "document_id", existing_doc_id)
# ... yeni chunk'lar insert edilir

# ONERILEN — Constraint-aware atomic swap:
# Adim 0: Oncelikle (organization_id, source_id) uzerinde
#          UNIQUE constraint varligini dogrula:
```

```sql
-- Dogrulama SQL'i:
SELECT conname, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'documents'::regclass
  AND contype = 'u';
-- 'organization_id, source_id' iceren unique constraint aranir

-- Eger YOKSA, migration ile ekle:
ALTER TABLE documents
  ADD CONSTRAINT uq_documents_org_source
  UNIQUE (organization_id, source_id);
```

```python
# Constraint dogrulandiktan sonra atomic swap:
# YAKLASIM A — RPC ile tek transaction:
supabase.rpc("atomic_replace_document", {
    "p_org_id": organization_id,
    "p_source_id": source_id,
    "p_doc_data": doc_data,
    "p_chunks": chunks_payload,
}).execute()
```

```sql
-- Atomic replace RPC:
CREATE OR REPLACE FUNCTION atomic_replace_document(
    p_org_id UUID,
    p_source_id TEXT,
    p_doc_data JSONB,
    p_chunks JSONB
) RETURNS UUID AS $$
DECLARE
    old_doc_id UUID;
    new_doc_id UUID;
BEGIN
    -- Eski dokumani bul
    SELECT id INTO old_doc_id
    FROM documents
    WHERE organization_id = p_org_id AND source_id = p_source_id;

    -- Eski chunk'lari sil (cascade)
    IF old_doc_id IS NOT NULL THEN
        DELETE FROM document_chunks WHERE document_id = old_doc_id;
        DELETE FROM documents WHERE id = old_doc_id;
    END IF;

    -- Yeni dokuman + chunk'lari insert et
    -- (mevcut ingest_document_chunks_batch mantigi)
    -- ...

    RETURN new_doc_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

---

#### SORUN-I2: Failed Embedding Sessizce Atlaniyor (Orta Oncelik — 5/10)

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da hot path icinde `Counter(...)` tanimlanmisti. Codex Round 2 bunu reddetti: repo'da Prometheus metrikleri module-level olarak `backend/core/metrics.py` icinde tanimlaniyor. Hot path icinde yeni Counter olusturmak duplicate registration ve test kirilmasi riski tasir.

**IMPLEMENTATION BLUEPRINT:**

```python
# backend/core/metrics.py — MODULE-LEVEL (mevcut metriklerin yanina)
embedding_failures_total = Counter(
    "embedding_failures_total", "Failed embeddings",
    ["source_type"]
)
embedding_failure_ratio = Counter(
    "embedding_failure_ratio_exceeded_total",
    "Documents exceeding 20% embedding failure threshold",
    ["source_type"]
)
```

```python
# tasks.py - generate_embeddings_task icinde (IMPORT ile kullan)
from core.metrics import embedding_failures_total, embedding_failure_ratio

failed_count = 0
for chunk, embedding in zip(chunk_payload, embeddings):
    if embedding is None:
        failed_count += 1
        continue
    enriched.append(...)

if failed_count > 0:
    embedding_failures_total.labels(source_type=source_type or "unknown").inc(failed_count)
    logger.warning(f"{failed_count}/{len(chunk_payload)} embeddings failed for doc {doc_title}")

# Eger %20'den fazla basarisiz ise DLQ'ya yonlendir
if failed_count > len(chunk_payload) * 0.2:
    embedding_failure_ratio.labels(source_type=source_type or "unknown").inc()
    raise Exception(f"Too many embedding failures ({failed_count}/{len(chunk_payload)})")
```

---

## BOLUM 8: MONITORING & ANALYTICS

### 8.1 Mevcut Monitoring

| Metric | Tip | Aciklama |
|--------|-----|----------|
| `retrieval_score` | Histogram | Similarity score dagilimi |
| `semantic_cache_ops` | Counter | Cache hit/miss/put/error |
| `guardrail_classifications` | Counter | Intent + complexity |
| `llm_request_duration` | Histogram | Provider/model bazli latency |
| `llm_tokens_total` | Counter | Provider/model/type bazli token |
| `llm_routing_decisions` | Counter | Plan/complexity/model bazli routing |
| `documents_processed` | Counter | Source_type/status bazli |
| `chunks_generated` | Counter | Source_type bazli |
| `embeddings_generated` | Counter | Toplam embedding |
| `dedup_actions_total` | Counter | Dedup aksiyon |
| `encryption_operations` | Counter | Encrypt/decrypt |
| 60+ daha... | Cesitli | metrics.py'de tanimli |

**Gercek Eksik:** Request-seviyesinde baglamsal analytics. Mevcut Prometheus metrikleri aggregate — tek bir sorgunun retrieval kalitesini, threshold etkisini ve kullanici feedback'ini iliskilendirmek mumkun degil.

### 8.2 Sorun

---

#### SORUN-M1-REV: Request-Level RAG Analytics Eksik (Yuksek — 8/10)

**IMPLEMENTATION BLUEPRINT:**

```sql
-- Migration: create_rag_analytics.sql
CREATE TABLE rag_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    message_id UUID,  -- DEGISIKLIK: conversation_id degil, message_id
    -- Query bilgileri
    query_hash TEXT,  -- SHA-256 of query (PII-safe)
    query_language TEXT,
    -- Retrieval metrikleri
    chunks_retrieved INT,
    chunks_used INT,
    avg_similarity_score FLOAT,
    max_similarity_score FLOAT,
    -- Reranking
    rerank_applied BOOLEAN DEFAULT false,
    avg_rerank_score FLOAT,
    -- Scope
    scope_classification TEXT,
    dominance_ratio FLOAT,
    scope_count INT,
    -- Quality
    confidence_score FLOAT,
    faithfulness_score FLOAT,
    -- Response
    response_tokens INT,
    model_used TEXT,
    latency_ms INT,
    -- Feedback (sonradan guncellenir)
    user_feedback TEXT,  -- 'positive', 'negative', NULL
    -- Zaman
    created_at TIMESTAMPTZ DEFAULT now()
) PARTITION BY RANGE (created_at);

-- Aylik partition
CREATE TABLE rag_analytics_2026_04 PARTITION OF rag_analytics
  FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE rag_analytics_2026_05 PARTITION OF rag_analytics
  FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');

-- Index
CREATE INDEX idx_rag_analytics_org ON rag_analytics (organization_id, created_at DESC);
CREATE INDEX idx_rag_analytics_msg ON rag_analytics (message_id) WHERE message_id IS NOT NULL;
CREATE INDEX idx_rag_analytics_feedback ON rag_analytics (user_feedback) WHERE user_feedback IS NOT NULL;
```

> **ClaudeRevize (Rev 3.0):** Rev 2.0'da `conversation_id` kullaniliyordu. Codex Round 2 bunu duzeltdi: mevcut feedback akisi `message_id` bazli calisiyor (`backend/services/feedback_service.py:40-145`, `supabase/migrations/20260223000000_message_feedback.sql:31-56`). `conversation_id` ile update etmek ayni konusmadaki birden fazla analytics satirini birlikte degistirebilir. Korelasyon anahtari **`message_id`** olmali.

```python
# services/rag_analytics.py
async def record_rag_event(
    supabase, organization_id, message_id,  # DEGISIKLIK: conversation_id → message_id
    query_hash, query_language,
    chunks_retrieved, chunks_used,
    avg_similarity, max_similarity,
    rerank_applied, avg_rerank,
    scope_classification, dominance_ratio, scope_count,
    confidence_score, faithfulness_score,
    response_tokens, model_used, latency_ms
):
    """Her chat request'inde cagrilir."""
    try:
        supabase.table("rag_analytics").insert({
            "organization_id": organization_id,
            "message_id": message_id,
            "query_hash": query_hash,
            "query_language": query_language,
            "chunks_retrieved": chunks_retrieved,
            "chunks_used": chunks_used,
            "avg_similarity_score": avg_similarity,
            "max_similarity_score": max_similarity,
            "rerank_applied": rerank_applied,
            "avg_rerank_score": avg_rerank,
            "scope_classification": scope_classification,
            "dominance_ratio": dominance_ratio,
            "scope_count": scope_count,
            "confidence_score": confidence_score,
            "faithfulness_score": faithfulness_score,
            "response_tokens": response_tokens,
            "model_used": model_used,
            "latency_ms": latency_ms,
        }).execute()
    except Exception as e:
        logger.warning(f"RAG analytics insert failed: {e}")
```

**Feedback Korelasyonu — message_id bazli:**
```python
# feedback_service.py - feedback submit'te rag_analytics guncelle
async def submit_feedback(self, message_id, rating, ...):
    # ... mevcut feedback logic
    # Ek: analytics tablosunu message_id ile guncelle (tek satir)
    supabase.table("rag_analytics") \
        .update({"user_feedback": rating}) \
        .eq("message_id", message_id) \
        .execute()
```

---

## BOLUM 9: ONCELIKLI AKSIYON PLANI (Rev 3.0)

### FRAZ 1: Go-Live Blocker (Bu Hafta)

| # | Aksiyon | Sorun | Efor | Dogrulama |
|---|---------|-------|------|-----------|
| 1.1 | FTS pipeline duzelt: `content_search` kullan, `'simple'` tutarli, **her iki** SQL fonksiyonuna uygula | V2-REV | 4-6 saat | Turkce keyword search calisiyor mu |
| 1.2 | Mevcut content_search backfill (app-side decrypt + re-tsvector) | V2-REV | 4-6 saat | Backfill sonrasi `simple` ile arama tum eski veriye uygulanabilir mi |
| 1.3 | search_language parametresini chat.py + search.py'den **her iki** RPC'ye gec | V2-REV | 2-3 saat | API cagrilarinda `search_language` gorunuyor mu |
| 1.4 | Tombstone CTE'yi son SQL fonksiyonlarina geri tasi + `/search`'e app-layer filter | V3-NEW | 2-3 saat | Tombstoned doc /search'te gorunmuyor mu |
| 1.5 | Deterministic "bulunamadi" — `_build_no_answer_response()` helper + HER IKI path | H2 | 2-3 saat | Bos scope'ta sorgu → sabit mesaj, 0 token, streaming + non-stream |
| 1.6 | Semantic cache key: `org_id` + `allowed_scopes` ekle | SC-NEW | 2-3 saat | Feature kapali ama unit test ile dogrula |

### FRAZ 2: Kritik Kalite (Ilk 2 Hafta)

| # | Aksiyon | Sorun | Efor | Dogrulama |
|---|---------|-------|------|-----------|
| 2.1 | Faithfulness guard — GuardrailService pattern'i ile, streaming warning + non-stream footer | H1 | 6-8 saat | Uydurma bilgi iceren test cevabini yakaliyor mu |
| 2.2 | COHERE_API_KEY startup kontrolu + reranker metrics (module-level) | R1 | 2-3 saat | Startup log + Prometheus counter |
| 2.3 | RAG Analytics tablosu (partitioned, message_id bazli) + her request'te log | M1-REV | 4-6 saat | INSERT calisiyor mu, feedback korelasyonu dogru mu |
| 2.4 | ef_search runtime degerini dogrula ve fix et | V1-REV | 1-2 saat | `SHOW hnsw.ef_search` → beklenen deger |
| 2.5 | Output filter: invalid citation'da da rewrite yap (sadece PII degil) | R-FILTER | 3-4 saat | Gecersiz [N] referansi cevaptan kaldiriliyor mu |

### FRAZ 3: Kalite Iyilestirme (Ilk Ay)

| # | Aksiyon | Sorun | Efor | Dogrulama |
|---|---------|-------|------|-----------|
| 3.1 | Confidence score hesaplama + SSE metadata (frontend contract guncelleme dahil) | R2 | 4-6 saat | Frontend'de confidence level gorunuyor mu |
| 3.2 | Offline eval dataset (50+ soru) + threshold sweep | R3 | 4-6 saat | F1 score grafigi + optimal threshold |
| 3.3 | Failed embedding tracking (module-level metrics) + %20 threshold → DLQ | I2 | 2-3 saat | Prometheus counter + DLQ retry |
| 3.4 | Reranking 5+ sonucta zorunlu | R1 | 2-3 saat | Tum 5+ sonuc sorgularinda rerank_applied=true |
| 3.5 | document_chunks.language kolonunu ingest sirasinda populate et | V2-REV | 2-3 saat | Yeni chunk'larda language != NULL |

### FRAZ 4: Optimizasyon (Sonraki Sprint)

| # | Aksiyon | Sorun | Efor | Dogrulama |
|---|---------|-------|------|-----------|
| 4.1 | embedding_model_version + embedded_at field'lari | E1 | 1-2 saat | Migration basarili |
| 4.2 | Kisa chunk filtresi (<10 token) | E2 | 2-3 saat | Kisa chunk sayisi azaldi |
| 4.3 | CSV/XLSX table summary | C3 | 3-4 saat | Tabular sorgularda cevap kalitesi |
| 4.4 | Semantic cache ac + monitoring | SC1 | 3-4 saat | Cache hit rate gorunur |
| 4.5 | Chunk race condition atomic swap (constraint dogrulamasiyla) | I1 | 3-4 saat | Replace sirasinda search gap yok |

---

## BOLUM 10: REVIZE EDILMIS RISK MATRISI (Rev 3.0)

| Sorun | Oncelik | Etki | Risk | Degisiklik |
|-------|---------|------|------|------------|
| **V2-REV: Keyword search pipeline kirik** | KRITIK | Yuksek | **10/10** | ↑ 7→10 (Rev 2.0), FTS strateji tutarlistirildi (Rev 3.0) |
| **H1: Faithfulness check yok** | KRITIK | Yuksek | **9/10** | Blueprint GuardrailService pattern'ine gecti (Rev 3.0) |
| **V3-NEW: Tombstone regresyonu** | YUKSEK | Yuksek | **8/10** | "olabilir" → "teyit edilmis" (Rev 3.0) |
| **SC-NEW: Cache tenant + scope izolasyonu** | KRITIK* | Yuksek | **8/10** | org_id + allowed_scopes (Rev 3.0), *feature acilirsa |
| **M1-REV: Request-level analytics yok** | YUKSEK | Yuksek | **8/10** | message_id bazli (Rev 3.0) |
| **H2: Bulunamadi LLM'e birakilmis** | YUKSEK | Orta | **7/10** | Dual-path helper (Rev 3.0) |
| **R1: Reranker zorunlu degil** | YUKSEK | Orta | **7/10** | Metrikler module-level'a tasindi (Rev 3.0) |
| **R2: Confidence score yok** | YUKSEK | Orta | **7/10** | = ayni |
| **R3: Threshold dogrulanmamis** | ORTA | Orta | **6/10** | = ayni |
| **I2: Failed embedding sessiz** | ORTA | Dusuk | **5/10** | Metrikler module-level'a tasindi (Rev 3.0) |
| **I1: Chunk replace race** | ORTA | Dusuk | **4/10** | Constraint dogrulama notu eklendi (Rev 3.0) |
| **C1: Chunk size tutarsiz** | ORTA | Dusuk | **4/10** | = ayni |
| **V1-REV: ef_search belirsiz** | DUSUK | Dusuk | **3/10** | = ayni |
| **E1: Model upgrade yolu yok** | DUSUK | Gelecek | **3/10** | = ayni |
| **C2: Dead code (scanned)** | DUSUK | Yok | **1/10** | = ayni |

---

## BOLUM 11: DOGRULAMA KONTROL LISTESI (Rev 3.0)

### 11.1 Keyword Search Pipeline Testi (EN KRITIK)
```sql
-- 1. content_search kolonu dolu mu?
SELECT COUNT(*) as total,
  COUNT(content_search) as with_search,
  COUNT(*) - COUNT(content_search) as missing_search
FROM document_chunks;

-- 2. Hybrid search fonksiyonu content_search mi dc.content mi kullaniyor?
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'hybrid_search_scoped'
ORDER BY oid DESC LIMIT 1;
-- Sonucta "dc.content_search" gorulmeli, "dc.content" degil

-- 3. hybrid_search (unscoped) da duzeltildi mi?
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'hybrid_search'
ORDER BY oid DESC LIMIT 1;
-- Ayni kontrol: "dc.content_search" gorulmeli

-- 4. Turkce keyword search calisiyor mu?
SELECT ts_rank_cd(
  to_tsvector('simple', 'proje yonetimi analiz raporu'),
  plainto_tsquery('simple', 'proje raporu')
) as simple_score;
-- Score > 0 beklenir

-- 5. Backfill sonrasi: eski satirlar 'simple' ile aranabiliyor mu?
SELECT COUNT(*) as searchable_chunks
FROM document_chunks
WHERE content_search @@ plainto_tsquery('simple', 'test');
```

### 11.2 Tombstone Kontrolu
```sql
-- 6. Son hybrid_search_scoped'da tombstone CTE var mi?
SELECT pg_get_functiondef(oid)
FROM pg_proc
WHERE proname = 'hybrid_search_scoped'
ORDER BY oid DESC LIMIT 1;
-- "compliance_tombstones" gorulmeli
```

### 11.3 ef_search Runtime
```sql
-- 7. Gercek ef_search degeri
SHOW hnsw.ef_search;
SELECT current_setting('hnsw.ef_search', true);
```

### 11.4 Embedding Butunlugu
```sql
-- 8. NULL embedding (veri kaybi)
SELECT COUNT(*) as null_embeddings
FROM document_chunks
WHERE embedding IS NULL;

-- 9. Dimension tutarliligi
SELECT vector_dims(embedding) as dim, COUNT(*)
FROM document_chunks
WHERE embedding IS NOT NULL
GROUP BY vector_dims(embedding);
-- Tum satirlar 1536 olmali
```

### 11.5 Scope Sagligi
```sql
-- 10. Scope'suz dokumanlar (olmamali)
SELECT COUNT(*) FROM documents WHERE scope_id IS NULL;

-- 11. Placeholder identity'ler
SELECT scope_id, status, type FROM scope_identities
WHERE status = 'placeholder';
```

### 11.6 Semantic Cache Key Dogrulamasi
```python
# Unit test: ayni embedding, ayni scope, farkli org → farkli key
key1 = cache._cache_key(emb, ["s1"], "org-A", ["s1", "s2"])
key2 = cache._cache_key(emb, ["s1"], "org-B", ["s1", "s2"])
assert key1 != key2  # cross-tenant izolasyon

# Ayni org, ayni scope, farkli allowed_scopes → farkli key
key3 = cache._cache_key(emb, ["s1"], "org-A", ["s1"])
key4 = cache._cache_key(emb, ["s1"], "org-A", ["s1", "s2"])
assert key3 != key4  # scope-set izolasyon
```

### 11.7 H2 Dual-Path Testi
```python
# Streaming path: yield-based generator test
# Non-stream path: ChatResponse object test
# Her ikisi de ayni should_return_no_answer() helper'ini kullanmali
# Her ikisi de LLM token tuketmemeli
```

### 11.8 Environment
```bash
echo "COHERE_API_KEY: $([ -n \"$COHERE_API_KEY\" ] && echo SET || echo MISSING)"
echo "SEMANTIC_CACHE_ENABLED: ${SEMANTIC_CACHE_ENABLED:-not_set}"
echo "CHUNK_ENCRYPTION_KEY: $([ -n \"$CHUNK_ENCRYPTION_KEY\" ] && echo SET || echo MISSING)"
echo "STRICT_ENCRYPTION_MODE: ${STRICT_ENCRYPTION_MODE:-not_set}"
```

---

## BOLUM 12: REV 3.0 — CODEX ROUND 2 YORUM TAKIP TABLOSU

Her Codex Round 2 yorumunun Rev 3.0'da nerede ele alindigi:

| # | Codex Round 2 Yorum | Adres | Rev 3.0 Degisikligi |
|---|---------------------|-------|---------------------|
| 1 | `document_chunks.language` kolonu var ama populate edilmiyor | V2-REV Katman 4 | "Kolon yok" → "Kolon var ama populate edilmiyor" olarak duzeltildi, migration referansi eklendi |
| 2 | FTS strateji tutarsizligi: ingest 'simple' ama query per-language | V2-REV Adim 1-2 | Tutarli `'simple'` karari alindi, per-language mapping kaldirildi, karar gerekcelendi |
| 3 | `d.deleted_at IS NULL` schema'da yok | V2-REV Adim 1 SQL | `d.deleted_at` tamamen kaldirildi, yalnizca tombstone CTE + app-layer |
| 4 | Mevcut content_search backfill plani eksik | V2-REV Adim 5 (YENI) | App-side decrypt + re-tsvector backfill stratejisi + script blueprint (Rev 4.0: `backend/scripts/` + `decrypt_text` ile duzeltildi) |
| 5 | Tombstone regresyonu "olabilir"den daha guclu | V3-NEW | "olabilir" → "teyit edilmis", migration satir referanslari eklendi |
| 6 | Output filter citation tespit eder ama duzeltmez | Bolum 4.1, Bolum 5.1 | Davranis detayli aciklandi, pratik etki yazildi, Fraz 2'ye fix eklendi |
| 7 | `_call_groq_guardrail` repo'da yok | H1 Blueprint | Rev 3.0: `_get_model()` pattern'i, Rev 4.0: public API (`LLMFactory.get_guardrail_model()` veya yeni public method) |
| 8 | Streaming faithfulness: geri cekme yok | H1 Entegrasyon | Rev 3.0: ayri warning event, Rev 4.0: mevcut `done.warning` pattern'i genisletildi |
| 9 | H2 non-stream ChatResponse yolu da var | H2 Blueprint | `_build_no_answer_response()` paylasilmis helper + her iki path icin kod ornegi |
| 10 | Cache key'e effective scope set de lazim | SC-NEW Blueprint | `allowed_scopes` parametresi eklendi, unit test ornegi yazildi |
| 11 | Feedback `message_id` bazli, `conversation_id` degil | M1-REV Blueprint | Schema + Python + korelasyon kodu `message_id` bazli yazildi |
| 12 | Prometheus Counter hot path'te tanimlanmamali | R1 + I2 Blueprint | Tum yeni metrikler `core/metrics.py` module-level, hot path'te import |
| 13 | `guardrail_result.language` dogru alan adi | V2-REV Adim 2 | `.detected_language` → `.language` duzeltildi, referans satirlari eklendi |
| 14 | Fix her iki SQL fonksiyonuna (hybrid_search + hybrid_search_scoped) | V2-REV Adim 1 + Adim 2 | Acik not + her iki RPC icin kod ornegi eklendi |
| 15 | source_id unique constraint dogrulanmali | I1 Blueprint | Constraint dogrulama SQL'i + migration onerisi eklendi |
| 16 | SSE metadata event tipi mevcut contract'ta yok | R2 Not | Frontend contract guncelleme notu eklendi |

---

## BOLUM 13: REV 4.0 — CODEX ROUND 3 YORUM TAKIP TABLOSU

Her Codex Round 3 yorumunun Rev 4.0'da nerede ele alindigi:

| # | Codex Round 3 Yorum | Adres | Rev 4.0 Degisikligi |
|---|---------------------|-------|---------------------|
| 1 | Backfill: `manage.py`/`management/commands` yok, `decrypt_content` yok — dogru: `backend/scripts/` ve `core.security.decrypt_text` | V2-REV Adim 5 | Script yolu `backend/scripts/backfill_content_search.py`, fonksiyon `decrypt_text` (`backend/core/security.py:262`) olarak duzeltildi |
| 2 | `document_chunks.organization_id` yok — org baglami `documents` uzerinden | V2-REV Adim 5 | `.eq("organization_id", org_id)` → `documents!inner` JOIN + `.eq("documents.organization_id", org_id)` |
| 3 | `_get_model()` private metoda disaridan erisim kirilgan | H1 Blueprint | Iki yaklasim sunuldu: (A) GuardrailService'e public method ekle, (B) `LLMFactory.get_guardrail_model()` dogrudan kullan. Private method'a disaridan erisim kaldirildi |
| 4 | SSE warning icin ayri event yerine mevcut `done.warning` pattern'i | H1 Entegrasyon | `{"type": "warning", ...}` → `done_event['faithfulness_warning']` mevcut pattern uzerinden |
| 5 | `user_allowed_scopes` degisken adi yanlis — dogru: `allowed_scopes` | SC-NEW Blueprint | Tum referanslar `allowed_scopes` olarak duzeltildi, endpoint dependency referansi eklendi |

---

## DOKUMAN SONU

**Rev 4.0 Degisiklik Ozeti (Round 3 uzerine):**
- 5 Codex Round 3 yorumunun tamami islendi
- Backfill scripti gercek codebase yapisiyla hizalandi (`backend/scripts/` + `decrypt_text`)
- `document_chunks.organization_id` schema hatasi duzeltildi (documents JOIN)
- Faithfulness guard private `_get_model()` bagimliliginden kurtarildi
- SSE faithfulness warning mevcut `done.warning` pattern'ine tasindi
- Cache `allowed_scopes` dogru degisken adi kullanildi

**Kumulatif Durum (4 revizyon, 3 Codex turu):**
- 21 Codex yorumunun tamami (Round 1: ~8, Round 2: 16, Round 3: 5, cakisanlar dahil) islendi
- Tum blueprint'ler gercek codebase fonksiyon adlari, dosya yollari ve schema'siyla uyumlu
- Kalan riskler "ana bulgu yanlis" seviyesinde degil; uygulanabilirlik seviyesinde

*Codex 5.4 uc tur cross-review + Claude deep-read + codebase dogrulama + industry best practices bazinda hazirlanmistir.*

---

## BOLUM 14: REV 4.1 — CODEX CLOSURE EXECUTION EVIDENCE

Bu bolum audit bulgularinin yalnizca teorik plan seviyesinde kalmadigini, hangi kisimlarin kodlandigini ve hangilerinin operasyonel olarak halen apply bekledigini kanitli sekilde kaydeder.

### 14.1 Full-Stack Wiring Durumu

`Codex Comment:` Faz 2/Faz 3 backend alanlari frontend contract'ina tasindi. `frontend-new/lib/chat-utils.ts`, `frontend-new/app/dashboard/chat/[chatId]/page.tsx`, `frontend-new/hooks/useChatHistory.tsx`, `frontend-new/types/index.ts`, `frontend-new/components/chat/ChatArea.tsx` ve `frontend-new/components/chat/MessageBubble.tsx` artik `faithfulness_warning`, `warning` ve `citations_stripped` alanlarini kaybetmeden tasiyor.

`Codex Comment:` SSE malformed-JSON fallback yolu artik sessiz metadata kaybi uretmiyor. `done` event parse edilemese bile regex fallback ile `message_id`, `warning`, `faithfulness_warning` ve `citations_stripped` alanlari korunuyor.

`Codex Comment:` Stream tarafindaki citation enforcement bilincli olarak post-hoc kaldi. Kullanici canli token akisinda gecersiz `[N]` gorebilir; ancak final birlesen cevap kaydedilmeden once sanitize ediliyor ve analytics'e `citations_stripped_count` dusuyor.

### 14.2 Dogrulama Kaniti

Frontend hedef testleri:

```bash
cd frontend-new && npm test -- __tests__/lib/chat-utils.test.ts __tests__/components/ChatPage.test.tsx __tests__/components/MessageBubble.test.tsx
```

Sonuc:

- 3 test file passed
- 189 test passed

Backend hedef testleri (Python 3.11 Docker image):

```bash
docker build -f docker/backend.Dockerfile -t axial-backend-py311 .
docker run --rm \
  -e SUPABASE_URL=http://localhost \
  -e SUPABASE_SECRET_KEY=test-secret \
  -e SUPABASE_JWT_SECRET=test-jwt \
  -e OPENAI_API_KEY=test-openai \
  -w /app/backend axial-backend-py311 sh -lc \
  'pip install --no-cache-dir -r requirements-test.txt >/tmp/pytest-install.log && \
   python -m pytest tests/unit/test_output_filter.py tests/unit/test_faithfulness_guard.py tests/unit/test_rag_analytics.py -x -v --tb=short'
```

Sonuc:

- 20 test passed in 0.56s

Remote migration apply:

```bash
supabase db push --include-all
supabase db push --include-all --dry-run
```

Sonuc:

- 5 migration remote projeye uygulandi
- Sonraki dry-run: `Remote database is up to date.`
- Migration notice: `pg_cron not available - manual partition maintenance required`

Ek syntax dogrulamasi:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile ...
```

Sonuc:

- Faz 1-3 kapsaminda degisen backend modullerinde syntax hatasi yok

### 14.3 Backfill Kaldirilma Karari (8 Nisan 2026)

Urun pre-launch asamasinda, canli kullanici ve production verisi bulunmuyor. Faz 3 pre-flight'ta alinan karar (L2 Opsiyon A) geregince mevcut test source'lari silinip yeniden ingest edilecek. Yeni ingest pipeline Faz 1 FTS fix'ini iceriyor ve `content_search` kolonunu `to_tsvector('simple', ...)` ile otomatik dolduruyor.

Bu karar sonucunda asagidaki operasyonel adimlar **kaldirildi**:

- ~~`backend/scripts/backfill_content_search.py` ile content_search backfill~~ — Yeniden ingest ile gereksiz
- ~~`supabase/ops/20260407_post_backfill_content_search_maintenance.sql` (REINDEX + ANALYZE)~~ — Normal insert autovacuum ile yonetiliyor
- ~~5 env secret gerekliligi (SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_JWT_SECRET, OPENAI_API_KEY, CHUNK_ENCRYPTION_KEY)~~ — Backfill scripti calistirilmayacagi icin gerekmiyor

Kalan operasyonel adimlar (8 Nisan 2026 itibariyla):

- `rag_analytics_*` partitionlarinin remote DB'de dogrulanmasi (migration #4 `ensure_rag_analytics_partitions(6)` ile precreate ediyor; pg_cron yoksa ileride manual partition maintenance gerekecek)
- Mevcut test source'larinin silinip yeniden ingest edilmesi
- D1-D8 smoke senaryolarinin staging uzerinde dogrulanmasi

### 14.4 Son Kalibrasyon

`Codex Comment:` Bu noktada kalan risk "kod uyumsuzlugu" degil, "operasyon tamamlama" riskidir. Faz 4 sonrasinda kalan zincir: source sil -> yeniden ingest -> partition dogrulama -> staging smoke test.

### 14.5 Faz 4 Uygulama Statusu (8 Nisan 2026)

Faz 4 kapsaminda ingest-time language detection backend'e eklendi. Regconfig stratejisi bilerek degistirilmedi; hem ingest hem query tarafinda FTS hala `simple` calisiyor. `document_chunks.language` artik yalnizca veri-enrichment kolonu olarak dolduruluyor.

Uygulanan yuzeyler:

- `backend/services/language_detector.py`: `fast-langdetect` tabanli fail-open detector
- `backend/core/ingestion_utils.py`: Ghost Protocol RPC path + direct insert fallback path `language` yaziyor
- `backend/core/config.py`: 3 yeni `LANGUAGE_DETECTION_*` setting
- `supabase/migrations/20260408113000_write_chunk_language_on_ingest.sql`: ingest RPC'ler `document_chunks.language` kolonunu yaziyor
- `backend/tests/unit/test_language_detector.py` ve `backend/tests/unit/test_ghost_protocol_ingestion.py`: Faz 4 unit coverage

Dogrulama:

- `PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile ...` temiz
- Python 3.11 container icinde hedef unit testler: `30 passed in 0.40s`
- `supabase db push --include-all` ile yeni migration remote projeye uygulandi
- `supabase db push --include-all --dry-run` sonucu: `Remote database is up to date.`

### 14.6 Faz 5 Uygulama ve Closure (9 Nisan 2026)

Faz 5 ile per-language FTS wiring'i tamamlandi. Tekil mapping modulu eklendi, ingest RPC path'i `language_regconfig` yollayacak sekilde guncellendi, chat/search query path'leri `get_regconfig()` kullanacak sekilde degistirildi ve query tarafindaki zorunlu `'simple'` override'i kaldirildi.

Uygulanan yuzeyler:

- `backend/core/language_config.py`
- `backend/core/ingestion_utils.py`
- `backend/api/v1/chat.py`
- `backend/api/v1/search.py`
- `supabase/migrations/20260408190000_per_language_fts_regconfig.sql`
- Faz 5 testleri: `backend/tests/unit/test_language_config.py`, `backend/tests/unit/test_ghost_protocol_ingestion.py`, `backend/tests/unit/test_search_api.py`, `backend/tests/unit/test_chats.py`, `backend/tests/integration/test_ghost_protocol_sql.py`

Dogrulama:

- Python 3.11 container icinde hedefli Faz 5 lint temiz
- Python 3.11 container icinde hedefli Faz 5 unit yuzeyi: `41 passed in 4.13s`
- `supabase db push --include-all` ile Phase 5 migration remote Supabase'a apply edildi
- Sonraki dry-run: `Remote database is up to date.`

Re-ingest sonrasi operasyonel smoke:

- `TR-AXIAL-20260408.pdf`: `6` chunk, `5 tr`, `1 null`, `content_search` dolu
- `EN-AXIAL-20260408.pdf`: `8` chunk, `7 en`, `1 null`, `content_search` dolu
- SQL FTS smoke:
  - `plainto_tsquery('turkish', 'uretici')` TR dokumanda eslesti
  - `plainto_tsquery('english', 'variance')` EN dokumanda eslesti
- Search/chat smoke:
  - TR query ve chat dogru TR dokumana gitti
  - EN query ve chat dogru EN dokumana gitti
- Analytics smoke:
  - Yeni `rag_analytics` kayitlari `completion_status = success`
  - `faithfulness_warning` beklenen durumda doluyor

Sonuc:

- Faz 4 sonrasi bekleyen operasyon zinciri tamamlandi
- Faz 5 per-language FTS hatti smoke seviyesinde kapatildi
- Bu noktadaki kalan risk "kod/DB wiring" degil, yalnizca normal release izleme riskidir
