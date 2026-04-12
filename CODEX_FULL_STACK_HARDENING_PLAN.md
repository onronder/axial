# AxioHub Full-Stack Hardening Plan

> **Tarih:** 2026-04-10
> **Amaç:** Connector canlı geçişi öncesi tüm bilinen hardening borçlarının konsolide listesi
> **Kaynak:** Production Readiness Audit, Security Audit, Final Code Review, Codex validasyonları
> **Kural:** Blocker olup olmadığına bakılmaksızın, yapılması gereken her şey listelendi

---

## A — BACKEND API LAYER

### A1. Documents Pagination 3-Layer Bug
**Severity:** Orta | **Kaynak:** Production Audit Finding #5 | **Durum:** HÂLÂ AÇIK

**Sorun:** `documents.py:290` — `range(0, page_window_end)` kullanımı. Tüm sayfalar aynı prefix window'u çeker, failed files offset'siz tekrar eder, post-merge sort sayfa sınırlarını bozar.

**Düzeltme (Full-Stack):**
1. **Backend:** Başarılı dokümanlar için `query.range(offset, offset + limit - 1)` kullanılmalı
2. **Backend:** Failed files için ayrı kanal: response'a `failed_files` array'i eklenmeli, paginated docs'a karıştırılmamalı
3. **Backend:** Post-merge sort kaldırılmalı — DB'den sıralı gelen veri yeterli

**DİKKAT — Response Shape Değişikliği:**
`failed_files` ayrı alana taşınırsa endpoint response contract'ı değişir. Aşağıdaki frontend consumer'lar da güncellenmeli:
- `frontend-new/hooks/useDocuments.ts` — response parsing
- `frontend-new/components/knowledge-base/KnowledgeBaseBrowser.tsx` — failed files rendering
- `frontend-new/app/dashboard/documents/` — documents page consumer'ları

**Test planı:**
- Sayfa 1 ve sayfa 2'de aynı doküman görünmediğini doğrula
- X-Total-Count header'ının gerçek toplam ile tutarlı olduğunu doğrula
- Failed files'ın sayfalama ile karışmadığını doğrula
- Frontend'in yeni response shape'i ile doğru çalıştığını doğrula

**Dosyalar:** `backend/api/v1/documents.py:262-383`, `frontend-new/hooks/useDocuments.ts`, `frontend-new/components/knowledge-base/`

---

### A2. PostgREST Filter String Interpolation Hardening
**Severity:** Düşük-Orta | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `documents.py:276-277` — `.or_(f"scope_id.in.({scope_filter}),scope_id.is.null")` string birleştirmesi. `allowed_scopes` DB'den geliyor (user input değil), ama canonical URI'de reserved karakter varsa filter mantığı kayabilir.

**Düzeltme:** Scope ID'lerde PostgREST-safe karakter politikası enforcelamak VEYA her scope_id'yi escape/quote etmek. UUID validation değil — scope_id TEXT URI'dir.

**Test planı:**
- Özel karakter içeren scope_id (parantez, virgül, nokta) ile filtreleme testi
- Normal scope filtrelemenin kırılmadığını regresyon testi

**Dosyalar:** `backend/api/v1/documents.py:274-280`

---

### A3. Broad Exception Handling — Error Differentiation
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `chat.py` ve `search.py`'de `except Exception` blokları transient (timeout) ile permanent (bad input) hataları aynı şekilde logluyor. Operasyonel izlenebilirlik zayıf.

**Düzeltme:** Kritik try-except bloklarında hata tipine göre ayrıştırma:
- `TimeoutError` → retry-worthy, WARNING log
- `ValueError`/`ValidationError` → permanent, ERROR log
- `Exception` → unknown, ERROR log + alert

**Dosyalar:** `backend/api/v1/chat.py`, `backend/api/v1/search.py`

---

### A4. Search Query Length vs Embedding Token Limit
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `search.py:80` — `max_length=10000` karakter izni. Embedding modeli genellikle 512-1024 token sınırında. Uzun query sessizce truncate edilebilir.

**Düzeltme:** Embedding model token limitine göre query uzunluğunu doğrulayan validation veya truncation + uyarı logu eklemek.

**Dosyalar:** `backend/api/v1/search.py:80`

---

## B — BACKEND CORE SERVICES

### B1. K9 Fallback Path — Defensive WARNING Log
**Severity:** Orta | **Kaynak:** Production Audit Finding #4 | **Durum:** DÜZELTİLDİ ✅

`_insert_chunks_direct()` artık WARNING logu içeriyor. Kapandı.

---

### B2. Language Detector — API Variant Fallthrough Logging
**Severity:** Düşük-Orta | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `language_detector.py:140-151` — `fast_langdetect` API çağrısı 6 variant deniyor, `TypeError`'ları sessizce atlıyor. Hangi variant'ın kullanıldığı loglanmıyor.

**Düzeltme:**
1. İlk başarılı variant'ı debug logla kaydet
2. `fast-langdetect` versiyonunu `requirements.txt`'te pinle (API değişikliği riski)
3. Detection failure'larında `len(text)` ve `error_type` logu ekle

**Dosyalar:** `backend/services/language_detector.py:122-168`

---

### B3. Language Config — Unknown Language Code Logging
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `language_config.py:44-51` — Bilinmeyen dil kodu geldiğinde sessizce `"simple"` döndürüyor.

**Düzeltme:** Unknown language code'larda debug log + opsiyonel metrik counter eklemek. Hangi dil kodlarının desteklenmediğini görmek için.

**Dosyalar:** `backend/core/language_config.py:44-51`

---

### B4. Encryption Key Rotation — Usage Tracking
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `security.py:96-112` — Decrypt sırasında hangi key'in başarılı olduğu loglanmıyor. Key rotation sonrası eski key'i ne zaman kaldırmanın güvenli olduğunu bilme yolu yok.

**Düzeltme:** Decrypt başarısında kullanılan key index'i metrik olarak kaydet. Ops dashboard'da "key 0: %95, key 1: %5" görünürlüğü sağla.

**Dosyalar:** `backend/core/security.py:96-112`

---

### B5. Database Retry Logging — Rate Limiting
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `db_utils.py:96-111` — Toplu insert failure'larında her retry ayrı WARNING logu üretiyor. 100 batch × 3 retry = 300 log satırı.

**Düzeltme:** Sadece ilk failure ve son attempt logla. Aradaki retry'ları suppress et veya aggregate et.

**Dosyalar:** `backend/core/db_utils.py:96-111`

---

## C — DATABASE / MIGRATION LAYER

### C1. NULL Scope Hotfix
**Durum:** DÜZELTİLDİ ✅ — `20260409113000_fix_scoped_search_null_scope_regression.sql`

---

### C2. SQL Migration CI Assertion Tests — Scope Genişletme
**Severity:** Orta | **Kaynak:** Production Audit Finding #8 | **Durum:** KISMEN KAPANDI

**Mevcut durum:** `test_sql_migration_contracts.py` zaten var ve en kritik iki regression'ı test ediyor:
- `d.scope_id IS NULL` clause varlığı
- Per-language `plainto_tsquery(search_language::regconfig, ...)` pattern'i

**Kalan iş:** Mevcut test coverage'ı genişletmek:
- Identity document exclusion clause kontrolü (`source_type NOT IN ('identity', 'scope_identity')`)
- `SECURITY DEFINER SET search_path = public` pattern kontrolü
- Yeni migration eklendiğinde otomatik regression tespiti

**Dosyalar:** `backend/tests/unit/test_sql_migration_contracts.py` (mevcut dosyayı genişlet)

---

### C3. Per-Language FTS Integration Test
**Severity:** Düşük | **Kaynak:** Database Review | **Durum:** AÇIK

**Sorun:** Eski chunk'lar `'simple'` regconfig ile, yeni chunk'lar per-language regconfig ile yazılıyor. Arama tutarlılığı entegrasyon testi yok.

**Düzeltme:** Mixed-language corpus ile search consistency testi. Mevcut `test_search_api.py` coverage'ını genişlet.

**Dosyalar:** `backend/tests/` (mevcut test dosyasına ekleme)

---

## D — FRONTEND

### D1. CSP Nonce Migration (script-src 'unsafe-inline' Removal)
**Severity:** Orta-Yüksek | **Kaynak:** Security Audit | **Durum:** AÇIK — Ayrı engineering spike

**Sorun:** `next.config.ts:114` — Production'da `script-src 'self' 'unsafe-inline'`. HTML injection + inline JS kombinasyonunda koruma düşer.

**Not:** Repo zaten Next.js 16.1.5 üzerinde (`package.json`). Nonce migration teknik olarak mümkün. Erteleme gerekçesi "Next 16'yı bekle" değil, "Next 16'da da yüksek blast-radius'lı değişiklik" olması.

**Düzeltme:** Proxy.ts'e per-request nonce generation, layout'a nonce propagation, chart.tsx style tag'ine nonce ekleme. `'unsafe-inline'` → `'nonce-{value}'` geçişi.

**Riskler:**
- Dynamic rendering zorunluluğu → static/ISR/PPR kaybı → TTFB artışı
- Sentry Replay uyumsuzluğu (getsentry/sentry-javascript#10481)
- Hydration mismatch riski

**Yaklaşım:** Performans etkisi ölçümlü, izole spike olarak ele alınacak. Önce TTFB baseline ölç, sonra nonce ekle, delta karşılaştır.

**Dosyalar:** `next.config.ts`, `proxy.ts`, `app/layout.tsx`, `components/ui/chart.tsx`

---

### D2. Sidebar Cookie Flags
**Durum:** DÜZELTİLDİ ✅ — Commit 3b278fc

---

### D3. Chart Color Sanitization
**Durum:** DÜZELTİLDİ ✅ — Commit 3b278fc

---

### D4. S3 Credential No-Echo Tests
**Durum:** DÜZELTİLDİ ✅ — Commit 3b278fc

---

### D5. useSearch Hook Contract (top_k → limit, filters → scope_ids)
**Durum:** DÜZELTİLDİ ✅ — Doğrulandı

---

## E — INFRASTRUCTURE / CI / OPS

### E1. CI Security Audit — Gerçek Fail'e Çevirme
**Severity:** Orta | **Kaynak:** Infra Review + Codex düzeltmesi | **Durum:** HÂLÂ AÇIK

**Sorun:** `.github/workflows/ci.yml` — `security-audit` job'u 3 katmanlı olarak fail'i yutuyor:
1. Job seviyesinde `continue-on-error: true` (satır 85)
2. `pip-audit ... || true` komutu — audit failure'ı exit 0'a çeviriyor
3. `npm audit ... || true` komutu — aynı şekilde

Bu 3 katman birlikte olduğu sürece sadece `continue-on-error` kaldırmak yetmez — komutlar yine yeşil kalır.

**Düzeltme (3 adım, hepsi birlikte):**
1. `continue-on-error: true` kaldır
2. `pip-audit ... || true` → `pip-audit ...` (|| true kaldır)
3. `npm audit ... || true` → `npm audit ...` (|| true kaldır)

**Dosyalar:** `.github/workflows/ci.yml:85, 98-102`

---

### E2. Flower Default Credentials
**Severity:** Düşük-Orta | **Kaynak:** Final Code Review, Codex doğruladı | **Durum:** AÇIK

**Sorun:** `docker-compose.prod.yml:41` — `FLOWER_USER:-admin` / `FLOWER_PASSWORD:-changeme`. Port kapalı (internal only) ama lateral movement riski var.

**Düzeltme:** Deploy checklist'te FLOWER_USER ve FLOWER_PASSWORD override'ını zorunlu kıl. Opsiyonel: startup script'te default credential kontrolü.

**Dosyalar:** `docker-compose.prod.yml:41`

---

### E3. Backend Security Headers (X-Content-Type-Options)
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** Backend API `X-Content-Type-Options: nosniff` header'ı dönmüyor. Frontend next.config.ts'te tanımlı ama API endpoint'leri doğrudan çağrıldığında bu header yok.

**Düzeltme:** FastAPI middleware'ine `X-Content-Type-Options: nosniff` ekle. Tek satır.

**Dosyalar:** `backend/main.py` (middleware bölümü)

---

### E4. Integration Tests CI'da Çalışmıyor
**Severity:** Düşük-Orta | **Kaynak:** Infra Review | **Durum:** AÇIK

**Sorun:** CI sadece `pytest -m "unit"` çalıştırıyor. 136 integration test hiçbir zaman CI'da koşmuyor.

**Düzeltme:** CI'a ayrı integration test job'u ekle (Redis/Postgres gerektirir). Veya en azından critical path integration testlerini unit marker'ına taşı.

**Dosyalar:** `.github/workflows/ci.yml`

---

## F — OPERASYONEL GÖRÜNÜRLÜK (Observability Hardening)

### F1. Decryption Fallback — Silent Legacy Pass
**Severity:** Düşük | **Kaynak:** Core Services Review | **Durum:** AÇIK

**Sorun:** `security.py:322-338` — Tüm key'ler başarısız olduğunda, strict mode kapalıysa plaintext sessizce dönüyor. `getattr` + Pydantic field tutarlılığı tartışmalı ama Codex "makul" dedi.

**Düzeltme:** `getattr(settings, ...)` yerine doğrudan `settings.STRICT_ENCRYPTION_MODE` kullan (Pydantic field zaten tanımlı). Daha explicit, daha güvenli.

**Dosyalar:** `backend/core/security.py:323`

---

### F2. Query Text Logging Redaction
**Severity:** Düşük | **Kaynak:** Final Code Review | **Durum:** AÇIK

**Sorun:** `chat.py:201, 867, 1444` ve `search.py` — Log mesajlarında query text'in ilk 50 karakteri görünüyor. Log leak durumunda kullanıcı verisi açığa çıkabilir.

**Düzeltme:** Query content yerine `len(query)` veya `hash(query)[:8]` logla. Hem chat hem search endpoint'lerinde.

**Dosyalar:** `backend/api/v1/chat.py`, `backend/api/v1/search.py`

---

---

## ÖZET TABLO

| ID | Katman | Açıklama | Severity | Durum |
|----|--------|----------|----------|-------|
| A1 | Backend API | Documents pagination 3-layer bug | Orta | AÇIK |
| A2 | Backend API | PostgREST filter string interpolation | Düşük-Orta | AÇIK |
| A3 | Backend API | Broad exception handling | Düşük | AÇIK |
| A4 | Backend API | Search query length validation | Düşük | AÇIK |
| B1 | Core | K9 fallback WARNING log | Orta | ✅ KAPANDI |
| B2 | Core | Language detector variant logging | Düşük-Orta | AÇIK |
| B3 | Core | Language config unknown code logging | Düşük | AÇIK |
| B4 | Core | Encryption key rotation tracking | Düşük | AÇIK |
| B5 | Core | DB retry log rate limiting | Düşük | AÇIK |
| C1 | Database | NULL scope hotfix | Yüksek | ✅ KAPANDI |
| C2 | Database | SQL migration CI assertions — scope genişletme | Orta | KISMEN KAPANDI |
| C3 | Database | Per-language FTS integration test | Düşük | AÇIK |
| D1 | Frontend | CSP nonce migration | Orta-Yüksek | AÇIK (spike) |
| D2 | Frontend | Sidebar cookie flags | Düşük | ✅ KAPANDI |
| D3 | Frontend | Chart color sanitization | Düşük | ✅ KAPANDI |
| D4 | Frontend | S3 no-echo tests | Düşük | ✅ KAPANDI |
| D5 | Frontend | useSearch hook contract | Orta | ✅ KAPANDI |
| E1 | CI/Infra | Security audit continue-on-error | Orta | AÇIK |
| E2 | CI/Infra | Flower default credentials | Düşük-Orta | AÇIK |
| E3 | CI/Infra | Backend X-Content-Type-Options | Düşük | AÇIK |
| E4 | CI/Infra | Integration tests in CI | Düşük-Orta | AÇIK |
| F1 | Observability | Decryption strict mode getattr | Düşük | AÇIK |
| F2 | Observability | Query text log redaction | Düşük | AÇIK |

**Toplam:** 23 madde — 7 kapandı, 16 açık

---

## ÖNERİLEN UYGULAMA SIRASI

### Sprint 1: Connector Geçişi Öncesi (Hemen)
> Riskli, değerli ve kolay olanlar

1. **A1** — Documents pagination fix — full-stack (backend + frontend consumer'lar)
2. **E1** — CI security audit gerçek fail'e çevirme (3 adım: continue-on-error + pip-audit || true + npm audit || true)
3. **E3** — Backend X-Content-Type-Options header (tek satır)
4. **F2** — Query text log redaction (gerçek kullanıcı verisi log'a gidiyor, yüksek ROI)
5. **C2** — Mevcut SQL migration contract testlerini genişlet (identity exclusion, search_path)

### Sprint 2: Connector Geçişi Sırasında (Paralel)
> Operasyonel görünürlük ve defensive depth

6. **A2** — PostgREST filter hardening
7. **B2** — Language detector logging + version pin
8. **E2** — Flower credential override checklist
9. **B4** — Encryption key rotation tracking
10. **B5** — DB retry log rate limiting

### Sprint 3: Post-Launch Stabilization
> Daha büyük scope, daha yüksek risk

11. **D1** — CSP nonce migration (ayrı spike, perf ölçümlü)
12. **E4** — CI integration test pipeline
13. **A3** — Exception handling differentiation
14. **F1** — Strict mode getattr cleanup (düşük ROI, ama temizlik)
15. **B3** — Unknown language code logging
16. **A4** — Search query length validation + C3 FTS integration test
