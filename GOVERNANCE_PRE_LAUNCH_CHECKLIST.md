# AxioHub Pre-Launch Governance Checklist

> **Tarih:** 2026-04-10
> **Commit:** a0ae638 (main)
> **Amaç:** Connector canlı geçişi öncesi tüm sistemin doğrulanmış durumu

---

## 1. HARDENING DOĞRULAMA — Sprint 1 + Sprint 2

### Sprint 1 (Tamamı Doğrulandı ✅)

| ID | Madde | Doğrulama | Kanıt |
|----|-------|-----------|-------|
| A1 | Documents pagination fix | ✅ | `documents.py:302,327-330` — offset-based range, `failed_files` ayrı response alanı, post-merge sort yok. Frontend `useDocuments.ts:41-46,95-139` yeni response shape'i kullanıyor |
| E1 | CI security audit gerçek fail | ✅ | `ci.yml:82-101` — `continue-on-error` yok, `pip-audit || true` yok, `npm audit || true` yok |
| E3 | Backend X-Content-Type-Options | ✅ | `main.py:349-363` — `_apply_api_security_headers()` middleware tüm response'lara `nosniff` ekliyor |
| F2 | Query text log redaction | ✅ | `chat.py` + `search.py` — tüm query logları `describe_query()` kullanıyor → `len=N sha=XXXX` formatı. `core/log_safety.py:15-17` implementasyonu doğrulandı |
| C2 | SQL migration contract testleri | ✅ | `test_sql_migration_contracts.py` — 4 test fonksiyonu: NULL scope guard, regconfig pattern, identity exclusion, SECURITY DEFINER search_path |

### Sprint 2 (Tamamı Doğrulandı ✅)

| ID | Madde | Doğrulama | Kanıt |
|----|-------|-----------|-------|
| A2 | PostgREST filter hardening | ✅ | `documents.py:130-156` — `_quote_postgrest_filter_value()` escape + validation, `_build_scope_visibility_filter()` safe builder |
| B2 | Language detector logging | ✅ | `language_detector.py:124-136,160,174` — variant tracking, fallthrough logging. `requirements.txt:27` — `fast-langdetect==0.2.0` pinned |
| E2 | Flower credential override | ✅ | `docker-compose.prod.yml:41` — `${FLOWER_USER:?must be set}:${FLOWER_PASSWORD:?must be set}` — default yok, deploy başarısız olur |
| B4 | Encryption key rotation tracking | ✅ | `security.py:310-317` — `encryption_key_usage_total.labels(key_index=...)` decrypt döngüsünde |
| B5 | DB retry log rate limiting | ✅ | `db_utils.py:35-67` — ilk + son attempt WARNING, ortası DEBUG |

---

## 2. ÖNCEKİ AUDIT KAPANIŞLARI

| Bulgu | Kaynak | Durum |
|-------|--------|-------|
| NULL scope_id regression | Production Audit #1 | ✅ Hotfix deployed (20260409113000) |
| Prod backend fallback URL | Production Audit #2 | ✅ Build-time guard (next.config.ts:28-46) |
| Documents 10-item limit | Production Audit #3 | ✅ DocumentsTable swap ile çözüldü |
| K9 fallback keyword blindness | Production Audit #4 | ✅ WARNING log eklendi (ingestion_utils.py:233-238) |
| Documents pagination | Production Audit #5 | ✅ Sprint 1 A1 ile çözüldü |
| Blocking I/O | Production Audit #6 | ✅ asyncio.to_thread + wait_for (search.py:141-198) |
| useSearch hook contract drift | Production Audit #7 | ✅ limit/scope_ids düzeltildi (useSearch.ts:173-191) |
| SQL migration CI gap | Production Audit #8 | ✅ Sprint 1 C2 ile kapatıldı |
| Sidebar cookie flags | Security Audit | ✅ Commit 3b278fc |
| Chart color sanitization | Security Audit | ✅ Commit 3b278fc |
| S3 credential no-echo tests | Security Audit | ✅ Commit 3b278fc |

---

## 3. BİLİNEN AÇIK KALEMLER (Sprint 3 — Post-Launch)

| ID | Madde | Risk | Etki |
|----|-------|------|------|
| D1 | CSP nonce migration | Orta-Yüksek | Blast radius yüksek, perf ölçümlü spike gerekir |
| E4 | CI integration test pipeline | Düşük-Orta | 136 integration test CI'da koşmuyor |
| A3 | Exception handling differentiation | Düşük | Operasyonel izlenebilirlik |
| F1 | Strict mode getattr cleanup | Düşük | Temizlik, düşük ROI |
| B3 | Unknown language code logging | Düşük | Observability |
| A4 | Search query length validation | Düşük | Edge case |
| C3 | Per-language FTS integration test | Düşük | Test coverage |

**Bu kalemlerden hiçbiri launch-blocking değil.** Connector canlı geçişini engellemez.

---

## 4. CI / DEPLOY ZİNCİRİ DURUMU

| Kontrol | Durum |
|---------|-------|
| Backend Lint | ✅ success |
| Backend Compile Check | ✅ success |
| Backend Pattern Enforcement | ✅ success |
| Backend Unit Tests (684 passed, 4 skipped) | ✅ success |
| Dependency Security Audit (pip-audit + npm audit) | ✅ success |
| Frontend Build & Lint | ✅ success |
| Frontend Targeted Tests (91 passed) | ✅ success |
| Vercel Deploy | ✅ success |
| Railway Backend Deploy | ✅ success |
| Railway Celery Deploy | ✅ success |

---

## 5. GÜVENLİK DURUMU

| Alan | Durum | Not |
|------|-------|-----|
| Authentication (Supabase RLS) | ✅ | Org-based isolation, service-role restricted inserts |
| Encryption (Ghost Protocol) | ✅ | AES-256 Fernet, multi-key rotation, key usage metrics |
| CORS | ✅ | Production fail-closed, wildcard sadece dev |
| CSP | ⚠️ | script-src 'unsafe-inline' hâlâ var — Sprint 3 D1 |
| Input Validation | ✅ | PostgREST filter escaped, query text redacted |
| Secret Management | ✅ | Env-driven, no hardcoded secrets, Flower creds required |
| Rate Limiting | ✅ | Redis-backed, per-org throttling |
| SQL Injection | ✅ | Supabase ORM + parameterized RPC functions |
| XSS Protection | ✅ | React DOM escaping, no dangerouslySetInnerHTML on user input |
| HSTS | ✅ | max-age=31536000; includeSubDomains; preload |

---

## 6. FAZ DURUMU

| Faz | Kapsam | Durum |
|-----|--------|-------|
| Faz 1 | Temel RAG pipeline | ✅ Kapatıldı |
| Faz 2 | Ghost Protocol encryption | ✅ Kapatıldı |
| Faz 3 | Hybrid search (semantic + keyword) | ✅ Kapatıldı |
| Faz 4 | Scoped search & multi-tenant | ✅ Kapatıldı |
| Faz 5 | Per-language FTS | ✅ Kapatıldı |
| Hardening Sprint 1 | Pagination, CI, log redaction, SQL tests | ✅ Kapatıldı |
| Hardening Sprint 2 | Filter, lang detector, Flower, key metrics, retry logs | ✅ Kapatıldı |
| Hardening Sprint 3 | CSP nonce, integration tests, observability | 🔲 Post-launch |

---

## 7. CONNECTOR CANLI GEÇİŞİ İÇİN ONAY

### Ön Koşullar
- [x] Faz 1-5 kapatıldı
- [x] Tüm bilinen blocker'lar çözüldü
- [x] Sprint 1 + Sprint 2 hardening deployed ve doğrulandı
- [x] CI zinciri yeşil (lint, compile, unit tests, security audit, frontend build)
- [x] Deploy zinciri yeşil (Vercel, Railway backend, Celery)
- [x] Güvenlik durumu kabul edilebilir (tek açık: CSP — post-launch)
- [x] Query text loglardan redakte edildi
- [x] Secret management env-driven, no defaults
- [x] SQL regression testleri CI'da çalışıyor

### Karar

**✅ SİSTEM CONNECTOR CANLI GEÇİŞİNE HAZIR**

Kalan Sprint 3 kalemleri post-launch stabilization olarak planlanmıştır ve connector geçişini engellemez.

---

---

## 8. CODEX DOĞRULAMA NOTLARI

**Codex code-level verify:** ✅ Geçti (2026-04-10)

**Non-blocking notlar:**
1. Bu dosya (`GOVERNANCE_PRE_LAUNCH_CHECKLIST.md`) ve `CODEX_FULL_STACK_HARDENING_PLAN.md` henüz untracked — repo artefaktı olacaksa commitlenmeli
2. `KnowledgeBaseBrowser.tsx:105` — 500 kayıt fetch cap'i bilinçli sınır. Büyük tenant'larda ayrı UX/backlog maddesi olarak izlenmeli

---

*Bu doküman Claude tarafından code-level doğrulama ile üretilmiştir. Codex tarafından bağımsız olarak verify edilmiştir. Tüm kanıtlar commit a0ae638 üzerinden doğrulanmıştır.*
