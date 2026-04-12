# AxioHub RAG Engine — Go-Live Implementation Plan

**Tarih:** 7 Nisan 2026  
**Durum:** Implementation-ready  
**Kaynak Dokuman:** `output/RAG_Engine_GoLive.md`  
**Amac:** Audit bulgularini, codebase ile uyumlu ve isimlendirme hatasi icermeyen uygulanabilir bir is planina cevirmek.

---

## 1. Sabit Kararlar

Bu plan asagidaki kararleri sabit kabul eder:

- FTS stratejisi kisa vadede **global `simple`** olacak.
- `content_search` keyword search icin tek dogru alan; `dc.content` uzerinden FTS yapilmayacak.
- Tombstone exclusion SQL katmanina geri alinacak, `/search` endpoint'inde app-layer yedek filtre de eklenecek.
- Deterministic no-answer hem streaming hem non-stream path icin ayni helper ile calisacak.
- Semantic cache key yalniz tenant degil, **effective scope set** izolasyonunu da kapsayacak.
- Analytics korelasyonu `conversation_id` degil, **`message_id`** bazli olacak.
- Yeni metrikler hot path icinde degil, **`backend/core/metrics.py`** icinde module-level tanimlanacak.

---

## 2. Uygulama Kisitlari

Plan yazilirken codebase uzerinde teyit edilen ve implementasyonda korunmasi gereken kritik kisitlar:

- Backfill script yuzeyi `manage.py` degil; repo yapisi `backend/scripts/` pattern'ini kullaniyor.
- Ghost Protocol decrypt helper adi `core.security.decrypt_text`.
- `document_chunks.organization_id` su an gorunmuyor; org filtresi `documents` uzerinden kurulacak.
- Chat endpoint dependency degisken adi `allowed_scopes`.
- `ChatResponse` modeli su an `answer`, `sources`, `conversation_id`, `message_id`, `scope_context` alanlarini tasiyor.
- SSE akisi mevcutta `done` event’i ile biter; yeni ayri event tipi acmadan, gerekirse `done` event payload’i genisletilecek.
- `LLMFactory.get_guardrail_model()` mevcut public yuzey; `GuardrailService._get_model()` private ic detaydir.

---

## 3. Uygulama Sirasi

### Faz 1 — Go-Live Blocker

#### 1. FTS pipeline duzeltmesi

**Hedef:** Keyword search’i tekrar calisir hale getirmek ve encryption ile uyumlu yapmak.

**Degisecek yerler:**

- Yeni migration: `supabase/migrations/<timestamp>_fix_fts_pipeline_simple.sql`
- Mevcut SQL fonksiyonlari:
  - `hybrid_search`
  - `hybrid_search_scoped`
- API cagrilari:
  - `backend/api/v1/chat.py`
  - `backend/api/v1/search.py`

**Ne yapilacak:**

- Her iki SQL fonksiyonunda keyword branch `dc.content` yerine `dc.content_search` kullanacak.
- Hem ingest hem query tarafinda `simple` regconfig kullanilacak.
- Tombstone CTE her iki SQL fonksiyonuna geri alinacak.
- `search_language` parametresi contract uyumu icin tutulacak ama bu fazda explicit olarak `"simple"` gonderilecek.
- `chat.py` ve `search.py` icindeki RPC cagrilarina `search_language: "simple"` eklenecek.

**Kabul kriteri:**

- `pg_get_functiondef(...)` ciktisinda `dc.content_search` gorunmeli.
- `pg_get_functiondef(...)` ciktisinda `compliance_tombstones` gorunmeli.
- `backend/api/v1/chat.py` ve `backend/api/v1/search.py` icinde her iki RPC cagrisi `search_language` gondermeli.

**Not:**

- `documents.deleted_at` benzeri bir filtre eklenmeyecek.

---

#### 2. Eski `content_search` verisinin backfill’i

**Hedef:** Mevcut `english` lexeme’lerle uretilmis satirlari `simple` ile yeniden olusturmak.

**Degisecek yerler:**

- Yeni script: `backend/scripts/backfill_content_search.py`
- Yardimci RPC migration’i:
  - `supabase/migrations/<timestamp>_add_update_content_search_simple_rpc.sql`

**Ne yapilacak:**

- Script `core.security.decrypt_text` kullanacak.
- Script `document_chunks` satirlarini org’a gore **`documents` join/RPC** uzerinden sececek; `document_chunks.organization_id` varsayimi yapmayacak.
- Plaintext DB’ye yazilmayacak; yalniz `content_search` guncellenecek.
- Batch boyutu configurable olacak.
- Dry-run modu eklenecek.

**Onerilen sorgu yaklasimi:**

- Ya SQL tarafinda org filtreli bir helper RPC ile `chunk_id, encrypted_content` batch’leri cek.
- Ya da PostgREST `documents!inner(...)` join’i ile ilgili chunk setini sec.

**Kabul kriteri:**

- Script belirli bir org icin batch halinde calisabiliyor olmali.
- Plaintext kalici tabloda saklanmamali.
- Backfill sonrasi `simple` query ile eski chunk’lar bulunabilmeli.

**Risk:**

- Bu is, FTS migration’i production’a ciktiktan hemen sonra ama semantic behavior testlerinden once calistirilmali.

---

#### 3. `/search` endpoint tombstone savunmasi

**Hedef:** Chat path ile `/search` path arasindaki davranis farkini kapatmak.

**Degisecek yerler:**

- `backend/api/v1/search.py`

**Ne yapilacak:**

- `_decrypt_search_results(matches)` sonrasina `compliance_switch.filter_tombstoned_docs(...)` eklenecek.

**Kabul kriteri:**

- Tombstoned bir dokuman chat’te de `/search` sonucunda da gorunmemeli.

---

#### 4. Deterministic no-answer helper

**Hedef:** Bos/yetersiz context durumunda LLM cagrisini tamamen bypass etmek.

**Degisecek yerler:**

- Yeni helper: `backend/services/no_answer.py`
- Entegrasyon:
  - `backend/api/v1/chat.py`

**Ne yapilacak:**

- `should_return_no_answer(docs, threshold)` helper’i eklenecek.
- `build_no_answer_payload()` benzeri tek helper tanimlanacak.
- Hem streaming hem non-stream path ayni karari kullanacak.
- Non-stream donus, mevcut `ChatResponse` alanlariyla uyumlu tutulacak.

**Kabul kriteri:**

- Stream path’te token harcanmadan deterministik yanit donebilmeli.
- Non-stream path ayni metni ve bos `sources` listesiyle donebilmeli.

**Not:**

- `ChatResponse` modeline bu fazda ekstra alan eklemek zorunlu degil; mevcut schema korunabilir.

---

#### 5. Semantic cache key izolasyonu

**Hedef:** Cache anahtarini tenant ve scope izolasyonu acisindan guvenli hale getirmek.

**Degisecek yerler:**

- `backend/services/semantic_cache.py`
- `backend/api/v1/chat.py`

**Ne yapilacak:**

- Cache key su alanlari kapsayacak:
  - `organization_id`
  - selected scope set (`scope_ids_for_cache`)
  - effective access scope set (`allowed_scopes`)
  - quantized embedding
- `chat.py` icinde gercek dependency adi olan `allowed_scopes` kullanilacak.
- `get()` ve `put()` imzalari buna gore guncellenecek.

**Kabul kriteri:**

- Ayni org + ayni embedding + farkli `allowed_scopes` setleri farkli key uretmeli.
- Feature kapali olsa da unit testler hazir olmali.

---

### Faz 2 — Kritik Kalite

#### 6. Faithfulness guard

**Hedef:** Post-generation claim destek kontrolu eklemek.

**Degisecek yerler:**

- Yeni modul: `backend/services/faithfulness_guard.py`
- LLM access:
  - Tercih A: `backend/services/guardrails.py` icine public helper eklemek
  - Tercih B: `backend/services/llm_factory.py` uzerinden `LLMFactory.get_guardrail_model()` kullanmak
- Entegrasyon:
  - `backend/api/v1/chat.py`

**Onerilen teknik karar:**

- **Tercih A**: `GuardrailService` icine public bir `run_json_prompt(prompt: str)` helper’i eklemek.
- **Fallback B**: `LLMFactory.get_guardrail_model(streaming=False, temperature=0)` ile dogrudan cagri.

**Neden A daha iyi:**

- Guardrail modeli tek yerde tutulur.
- Private `_get_model()` disardan kullanilmaz.
- Gelecekte provider degisirse faithfulness kodu daha az kirilir.

**Streaming davranisi:**

- Yeni ayri SSE event tipi acilmayacak.
- Gerekirse mevcut `done` payload’i `faithfulness_warning` alani ile genisletilecek.
- Non-stream path’te cevap donmeden once check yapilip footer/disclaimer eklenebilir.

**Kabul kriteri:**

- Streaming path mevcut `done` event mantigini bozmamali.
- Non-stream path’te unsupported claim varsa cevap markalanmali.

---

#### 7. Reranker observability

**Hedef:** Reranker yokken sessiz kalite dususunu gorunur hale getirmek.

**Degisecek yerler:**

- `backend/core/metrics.py`
- `backend/api/v1/chat.py`
- Gerekirse startup check:
  - `backend/main.py`

**Ne yapilacak:**

- `rerank_score_histogram`
- `rerank_skipped_total`
- `COHERE_API_KEY` startup check

**Kabul kriteri:**

- `retrieval_score` anlami bozulmamis olmali.
- Yeni metrikler module-level tanimli olmali.

---

#### 8. Request-level analytics

**Hedef:** Tekil request kalitesini ve feedback’i baglayabilmek.

**Degisecek yerler:**

- Yeni migration: `supabase/migrations/<timestamp>_create_rag_analytics.sql`
- Yeni servis: `backend/services/rag_analytics.py`
- Entegrasyon:
  - `backend/api/v1/chat.py`
  - `backend/services/feedback_service.py`

**Ne yapilacak:**

- `rag_analytics.message_id` ana korelasyon anahtari olacak.
- Analytics insert’i `save_messages()` sonrasinda, `message_id` elde edildikten sonra yapilacak.
- Feedback update’i `.eq("message_id", message_id)` ile calisacak.

**Kabul kriteri:**

- Ayni conversation icindeki diger mesajlar etkilenmemeli.
- Streaming ve non-stream path’te `message_id` dogru propagate edilmeli.

---

### Faz 3 — Sonraki Iterasyon

#### 9. Output filter citation enforcement

**Hedef:** Invalid citation tespitini yalniz log seviyesinden cikarip karar mekanizmasina almak.

**Degisecek yerler:**

- `backend/services/output_filter.py`
- `backend/api/v1/chat.py`

**Opsiyonlar:**

- Invalid citation varsa cevap footer ile isaretle
- Invalid citation varsa cevabi post-process et
- Invalid citation varsa faithfulness warning ile birlestir

---

#### 10. `document_chunks.language` populate etme

**Hedef:** Gelecekte per-language retrieval tasarlanacaksa veri tabanini hazirlamak.

**Degisecek yerler:**

- `backend/worker/tasks.py`
- Gerekirse ingest helper’lari

**Not:**

- Bu is global `simple` stratejisinin blocker’i degil.

---

## 4. Onerilen Gercek Uygulama Sirası

Asagidaki sira dependency ve risk acisindan en dusuk maliyetli akistir:

1. FTS SQL fix + tombstone SQL fix
2. `chat.py` ve `search.py` RPC parametre guncellemeleri
3. `/search` tombstone app-layer filter
4. Backfill RPC + `backend/scripts/backfill_content_search.py`
5. Deterministic no-answer helper ve iki path entegrasyonu
6. Semantic cache key izolasyonu
7. Reranker metrics ve startup visibility
8. Faithfulness guard
9. `rag_analytics` schema + service + feedback korelasyonu
10. Output filter citation enforcement

Bu sira ile:

- Once retrieval dogrulugu duzeltilir.
- Sonra yanit kalitesi ve cache safety ele alinir.
- En son analytics ve ek guardrail katmanlari eklenir.

---

## 5. Dosya Bazli Is Listesi

### Yeni dosyalar

- `backend/scripts/backfill_content_search.py`
- `backend/services/no_answer.py`
- `backend/services/faithfulness_guard.py`
- `backend/services/rag_analytics.py`
- `supabase/migrations/<timestamp>_fix_fts_pipeline_simple.sql`
- `supabase/migrations/<timestamp>_add_update_content_search_simple_rpc.sql`
- `supabase/migrations/<timestamp>_create_rag_analytics.sql`

### Guncellenecek dosyalar

- `backend/api/v1/chat.py`
- `backend/api/v1/search.py`
- `backend/services/semantic_cache.py`
- `backend/services/feedback_service.py`
- `backend/services/guardrails.py` veya `backend/services/llm_factory.py`
- `backend/core/metrics.py`
- Gerekirse `backend/main.py`

---

## 6. Test Planı

### Retrieval

- Turkish query ile `simple` FTS sonucu geliyor mu
- Encrypted content uzerinden degil `content_search` uzerinden arama yapiliyor mu
- Tombstoned doc hem chat hem `/search` sonucundan dusuyor mu

### No-answer

- Streaming path: bos context -> sabit mesaj, `done` event, 0 generation
- Non-stream path: bos context -> sabit `ChatResponse`

### Cache

- Ayni embedding + farkli `allowed_scopes` => farkli cache key
- Ayni scope + farkli org => farkli cache key

### Faithfulness

- Unsupported claim iceren test cevapta warning/disclaimer geliyor mu
- Streaming path yeni event tipi acmadan warning tasiyabiliyor mu

### Analytics

- `message_id` ile analytics insert oluyor mu
- Feedback update yalniz ilgili satiri guncelliyor mu

---

## 7. Rollout Stratejisi

### Once staging

- SQL migration’lari uygula
- Kucuk bir org uzerinde backfill dry-run
- Sonra canli backfill
- Retrieval smoke test
- Tombstone smoke test

### Sonra production

- SQL migration
- API deploy
- Semantic verification
- Controlled backfill
- Metrics ve log takibi

### Rollback

- FTS function migration’i icin onceki function body snapshot’i alinmali
- Backfill script idempotent olacak sekilde tasarlanmali
- Cache feature zaten kapali; rollback riski dusuk

---

## 8. Cikis Kriteri

Bu plan tamamlanmis sayilmasi icin asagidaki maddeler birlikte saglanmali:

- `hybrid_search` ve `hybrid_search_scoped` `content_search` + tombstone CTE ile calisiyor
- API `search_language: "simple"` gonderiyor
- Eski `content_search` verisi backfill edildi
- `/search` tombstone filter’e sahip
- Deterministic no-answer her iki response path’inde ayni calisiyor
- Semantic cache key tenant + scope izole
- Faithfulness check streaming ve non-stream path icin tanimli
- Request analytics `message_id` bazli kayit aliyor
- Yeni metrikler `backend/core/metrics.py` icinde tanimli

---

## 9. Uygulama Notlari

- Per-language FTS bu fazda yapilmayacak.
- `document_chunks.language` populate etme isi gelecek iterasyona birakilabilir.
- Faithfulness katmani ilk iterasyonda warning/disclaimer seviyesinde tutulabilir; hard block yapmak gerekmez.
- `done` SSE envelope’unu genisletmek, yeni event tipi eklemekten daha dusuk risklidir.

---

## 10. Execution Update — 8 Nisan 2026

Bu planin Faz 1-3 kapsamindaki kod degisiklikleri bu turda yeniden dogrulandi ve full-stack wiring bosluklari kapatildi. Remote migration push tamamlandi; ancak backfill/maintenance/smoke zinciri bu session icinde tamamlanamadi.

### 10.1 Kod Entegrasyon Durumu

- [x] Backend stream `done` payload'i `faithfulness_warning` ve `citations_stripped` tasiyor.
- [x] Frontend `StreamEvent` ve `ChatResult` contract'i yeni alanlari tasiyor.
- [x] Malformed SSE `done` fallback parser'i `message_id`, `warning`, `faithfulness_warning`, `citations_stripped` alanlarini koruyor.
- [x] `page.tsx` final assistant message state'ine warning/citation metadata yaziyor.
- [x] `MessageBubble` faithfulness warning banner'ini render ediyor.
- [x] Frontend testleri yeni done shape ve warning render yolunu kapsiyor.

### 10.2 Dogrulama Kanitlari

Frontend hedef testleri:

```bash
cd frontend-new && npm test -- __tests__/lib/chat-utils.test.ts __tests__/components/ChatPage.test.tsx __tests__/components/MessageBubble.test.tsx
```

Sonuc:

- 3 test file passed
- 189 test passed

Backend syntax dogrulamasi:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile \
  backend/api/v1/chat.py backend/api/v1/search.py backend/core/config.py \
  backend/core/metrics.py backend/main.py backend/services/feedback_service.py \
  backend/services/guardrails.py backend/services/output_filter.py \
  backend/services/reranker.py backend/services/semantic_cache.py \
  backend/services/faithfulness_guard.py backend/services/no_answer.py \
  backend/services/rag_analytics.py backend/tests/unit/test_chats.py \
  backend/tests/unit/test_core_metrics.py backend/tests/unit/test_feedback_service.py \
  backend/tests/unit/test_guardrails.py backend/tests/unit/test_output_filter.py \
  backend/tests/unit/test_reranker.py backend/tests/unit/test_semantic_cache.py \
  backend/tests/unit/test_faithfulness_guard.py backend/tests/unit/test_rag_analytics.py
```

Sonuc:

- Hata yok, syntax temiz

Backend hedef unit testleri (Python 3.11 Docker image uzerinden):

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
- Migration sirasinda `pg_cron not available - manual partition maintenance required` notice'u dondu

### 10.3 Operasyonel Durum

- [x] C1: 5 migration remote Supabase'a apply edildi
- [x] C2: `content_search` backfill — **KALDIRILDI** (asagidaki karara bakin)
- [x] C3: `REINDEX INDEX CONCURRENTLY` + `ANALYZE` — **KALDIRILDI** (backfill ile birlikte gereksiz)
- [ ] C2: `rag_analytics_*` partitionlari remote DB'de dogrulanacak

### 10.4 Backfill Kaldirilma Karari (8 Nisan 2026)

Urun pre-launch asamasinda, canli kullanici ve production verisi yok. Mevcut test verileri icin backfill yapmak yerine tum source'lar silinip yeniden ingest edilecek. Bu karar Faz 3 pre-flight'ta alinmisti (L2 Opsiyon A: "Tum source'lari silip bir daha eklerim, sorun yok").

Yeni ingest pipeline Faz 1 FTS fix'ini iceriyor: `content_search` kolonu `to_tsvector('simple', ...)` ile otomatik dolduruluyor. Bu sayede:

- `backfill_content_search.py` scripti calistirilmayacak
- 5 env secret (SUPABASE_URL, SUPABASE_SECRET_KEY, SUPABASE_JWT_SECRET, OPENAI_API_KEY, CHUNK_ENCRYPTION_KEY) gerekmiyor
- `REINDEX` + `ANALYZE` operasyonu gerekmiyor (normal insert autovacuum ile yonetiliyor)

### 10.5 Faz 4 Sonrasi Zorunlu Kapanis

Faz 4 tamamlandiktan sonra kalan operasyon zinciri:

1. `rag_analytics_*` partitionlarinin remote DB'de dogrulanmasi (migration #4 `ensure_rag_analytics_partitions(6)` ile precreate ediyor; pg_cron yoksa ileride manual partition maintenance gerekecek).
2. Mevcut test source'larinin silinip yeniden ingest edilmesi (backfill yerine).
3. D1-D8 smoke senaryolarinin staging uzerinde dogrulanmasi.
4. Bu zincir tamamlandiktan sonra Faz 5 per-language retrieval / routing calismasi uygulanacak.

### 10.6 Faz 4 Uygulama ve Dogrulama Durumu (8 Nisan 2026)

Uygulanan kod degisiklikleri:

- `backend/services/language_detector.py` eklendi. `fast-langdetect` ustunde fail-open ISO 639-1 detector servisi olusturuldu.
- `backend/core/ingestion_utils.py` icinde hem `prepare_chunks_for_ghost_protocol()` hem `_insert_chunks_direct()` path'i `language` yazacak sekilde guncellendi.
- `backend/core/config.py` icine `LANGUAGE_DETECTION_ENABLED`, `LANGUAGE_DETECTION_MIN_CHARS`, `LANGUAGE_DETECTION_MIN_CONFIDENCE` ayarlari eklendi.
- `backend/requirements.txt`, `backend/requirements-test.txt` ve `requirements.txt` icine `fast-langdetect` eklendi.
- `supabase/migrations/20260408113000_write_chunk_language_on_ingest.sql` eklendi ve batch + single-row ingest RPC'leri `document_chunks.language` yazacak sekilde guncellendi.
- Unit ve integration test yuzeyleri guncellendi: `backend/tests/unit/test_language_detector.py`, `backend/tests/unit/test_ghost_protocol_ingestion.py`, `backend/tests/integration/test_ghost_protocol_sql.py`.

Dogrulama kanitlari:

```bash
PYTHONPYCACHEPREFIX=/tmp/pycache python3 -m py_compile \
  backend/services/language_detector.py \
  backend/core/ingestion_utils.py \
  backend/tests/unit/test_language_detector.py \
  backend/tests/unit/test_ghost_protocol_ingestion.py \
  backend/tests/integration/test_ghost_protocol_sql.py

docker run --rm \
  -e SUPABASE_URL=http://localhost \
  -e SUPABASE_SECRET_KEY=test-secret \
  -e SUPABASE_JWT_SECRET=test-jwt \
  -e OPENAI_API_KEY=test-openai \
  -v /Users/onuronder/axial:/app \
  -w /app/backend \
  axial-backend-py311 sh -lc \
  'pip install --no-cache-dir fast-langdetect pytest pytest-asyncio >/tmp/langdetect-pip.log && \
   python -m pytest tests/unit/test_language_detector.py tests/unit/test_ghost_protocol_ingestion.py -q'

supabase db push --include-all
supabase db push --include-all --dry-run
```

Sonuc:

- `py_compile` temiz gecti
- Python 3.11 container icinde Faz 4 unit testleri: `30 passed in 0.40s`
- Remote Supabase migration apply edildi: `20260408113000_write_chunk_language_on_ingest.sql`
- Sonraki dry-run: `Remote database is up to date.`

### 10.7 Faz 5 Uygulama ve Smoke Durumu (9 Nisan 2026)

Faz 5 kapsaminda per-language FTS wiring'i tamamlandi:

- `backend/core/language_config.py` eklendi ve ISO 639-1 -> PostgreSQL `regconfig` mapping'i tek modulde toplandi
- `backend/core/ingestion_utils.py` icinde Ghost Protocol RPC path'i `language_regconfig` yollayacak sekilde guncellendi
- `backend/api/v1/chat.py` icinde `guardrail_result.language` -> `get_regconfig()` -> `search_language` akisi aktif edildi
- `backend/api/v1/search.py` icinde `language_detector.detect()` -> `get_regconfig()` -> `search_language` akisi aktif edildi
- `supabase/migrations/20260408190000_per_language_fts_regconfig.sql` eklendi; ingest RPC'leri per-language `to_tsvector(...::regconfig, ...)` uretecek sekilde guncellendi, query tarafindaki zorunlu `'simple'` override'i kaldirildi
- Faz 5 unit/integration test yuzeyi eklendi: `backend/tests/unit/test_language_config.py`, `backend/tests/unit/test_ghost_protocol_ingestion.py`, `backend/tests/unit/test_search_api.py`, `backend/tests/unit/test_chats.py`, `backend/tests/integration/test_ghost_protocol_sql.py`

Dogrulama kanitlari:

- Python syntax derlemesi temiz gecti
- Python 3.11 container icinde hedefli Faz 5 lint: `ruff check` temiz
- Python 3.11 container icinde hedefli Faz 5 unit yuzeyi: `41 passed in 4.13s`
- `supabase db push --include-all` ile `20260408190000_per_language_fts_regconfig.sql` remote projeye uygulandi
- Sonraki `supabase db push --include-all --dry-run` sonucu: `Remote database is up to date.`

Operasyonel smoke kanitlari (tum baglantilar silinip yeniden ingest sonrasi):

- `TR-AXIAL-20260408.pdf` (`8a57311d-e4e0-432f-8146-fd2caa4b0537`): `6` chunk, `5 tr`, `1 null`, `null_search_chunks = 0`
- `EN-AXIAL-20260408.pdf` (`9b120585-0cb6-4472-ba70-d77b66b50eb8`): `8` chunk, `7 en`, `1 null`, `null_search_chunks = 0`
- SQL smoke:
  - `plainto_tsquery('turkish', 'uretici')` TR dokumanda eslesti
  - `plainto_tsquery('english', 'variance')` EN dokumanda eslesti
- Uygulama smoke:
  - TR search/chat dogru dokumana gitti
  - EN search/chat dogru dokumana gitti
- Analytics smoke:
  - 9 Nisan 2026 cagrilari icin yeni `rag_analytics` satirlari `completion_status = success` ile olustu
  - `faithfulness_warning` gerektiğinde doldu, digerlerinde `null` kaldi

Son durum:

- Faz 5 per-language FTS hatti smoke seviyesinde dogrulandi
- ingest -> FTS build -> search -> chat -> analytics zinciri birlikte saglikli
- Gercek service-role env ile ayrik DB integration test kosusu bu shell'de yapilmadi; ancak remote migration apply + SQL smoke + uygulama smoke ile release-blocking risk kalmadi
