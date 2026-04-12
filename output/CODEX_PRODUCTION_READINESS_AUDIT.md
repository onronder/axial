# AxioHub Production Readiness Audit — Fix Directive

> **Tarih:** 9 Nisan 2026  
> **Kaynak:** Codex statik audit + Claude doğrulama  
> **Kapsam:** Connector provider rollout/OAuth hariç tüm katmanlar  
> **Hedef:** Enterprise SaaS production-ready durumuna getirme  
> **Akış:** Claude doğrular → Codex uygular

---

## Severity Legend

| Etiket | Anlamı | Launch Etkisi |
|--------|--------|---------------|
| BLOCKER | Production'da veri kaybı veya güvenlik ihlali | Launch engelleyici — fix olmadan deploy yapılmaz |
| HIGH | Kullanıcı deneyimini ciddi etkiler veya sessiz hata | Launch öncesi fix — 48 saat içinde |
| MEDIUM | UX sorunu veya teknik borç | Go-live sonrası sprint — ilk 2 hafta |
| LOW | Dormant/inactive kod, gelecek risk | Backlog — aktive edilmeden önce fix |

---

## Finding #1 — NULL scope_id Regresyonu

**Severity: BLOCKER**  
**Katman:** Backend / SQL / E2E  
**Etki:** Scope-restricted kullanıcılar org-level paylaşımlı dokümanları (scope_id = NULL) göremez hale gelir.

> **Bu bulgu ayrı bir hotfix directive olarak çıkarılmıştır:**  
> `CODEX_HOTFIX_NULL_SCOPE_REGRESSION.md`  
> Hotfix bu brief'ten bağımsız olarak derhal uygulanmalıdır.

### Özet

Faz 5 migration'ı `hybrid_search_scoped` fonksiyonunu yeniden yazarken `20260228000000_scoped_search_include_null_scope.sql` migration'ındaki `OR d.scope_id IS NULL` dalını kaybetti. 2 CTE (semantic + keyword) etkileniyor. Çağrı zincirleri: `search.py:161`, `chat.py:1756`.

### Enterprise Best Practice

Multi-tenant SaaS'ta `CREATE OR REPLACE FUNCTION` kullanan migration'lar önceki fonksiyon gövdesini tamamen siler. Her yeniden yazımda önceki access-control logic (scope filtre, tombstone, identity exclusion) denetlenmeli. Bu tür regresyonları önlemek için SQL fonksiyon gövdesinde assertion test'leri CI'ya eklenmeli (bkz. Finding #8).

> **Codex validation note (9 Nisan 2026):** Bu bulgu ve ayrı hotfix directive teknik olarak doğrulandı. `CODEX_HOTFIX_NULL_SCOPE_REGRESSION.md` bu haliyle izole şekilde uygulanabilir görünüyor.

---

## Finding #2 — Production Backend Fallback (Fail-Open)

**Severity: HIGH**  
**Katman:** Frontend / DevOps  
**Etki:** `NEXT_PUBLIC_API_URL` yoksa staging/preview deploy'ları sessizce production veritabanına vurur. Veri sızıntısı ve istenmeyen mutation riski.

### Problem

`frontend-new/next.config.ts` dosyasında 2 yerde hardcoded production URL fallback var:

**Line 78 (CSP headers):**
```typescript
const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://axial-production-1503.up.railway.app';
```

**Line 193 (API rewrites):**
```typescript
const rawApiBase = process.env.NEXT_PUBLIC_API_URL || "https://axial-production-1503.up.railway.app";
```

### Enterprise Best Practice

Production ortamına sessiz fallback asla kabul edilmez. Environment variable yoksa:
1. **Build-time fail-fast:** Build hata versin, deploy engellenir
2. **Veya runtime banner:** Geliştirici localhost'a düşer, uyarı görür

### Fix

**Dosya:** `frontend-new/next.config.ts`

**Line 78 — build-time guard ekle:**
```typescript
const apiUrl = process.env.NEXT_PUBLIC_API_URL;
if (!apiUrl && process.env.NODE_ENV === 'production') {
  throw new Error(
    'NEXT_PUBLIC_API_URL is required in production builds. ' +
    'Set it in your deployment environment variables.'
  );
}
const resolvedApiUrl = apiUrl || 'http://127.0.0.1:8000';
```

**Line 193 — aynı guard:**
```typescript
const rawApiBase = process.env.NEXT_PUBLIC_API_URL;
if (!rawApiBase && process.env.NODE_ENV === 'production') {
  throw new Error(
    'NEXT_PUBLIC_API_URL is required in production builds.'
  );
}
const trimmedApiBase = (rawApiBase || 'http://127.0.0.1:8000').replace(/\/$/, "");
```

**Ek:** Railway/Vercel deploy config'inde `NEXT_PUBLIC_API_URL` zorunlu env olarak işaretlenmeli.

> **Codex validation note (9 Nisan 2026):** Fix yönü doğru. Ancak patch uygulanırken `resolvedApiUrl` değişkeninin CSP `connect-src` satırında da gerçekten kullanıldığından emin olunmalı; aksi halde guard eklenip CSP tarafı eski değişkende kalabilir.

### Test

- `NODE_ENV=production` + `NEXT_PUBLIC_API_URL` unset → `next build` hata vermeli
- `NODE_ENV=development` + `NEXT_PUBLIC_API_URL` unset → localhost'a düşmeli (mevcut dev davranışı)
- `NEXT_PUBLIC_API_URL=https://...` set → normal çalışmalı

---

## Finding #3 — Documents Sayfası 10-Kayıt Limiti

**Severity: MEDIUM-HIGH**  
**Katman:** Frontend / UX  
**Etki:** `/dashboard/documents` sayfası sadece ilk 10 dokümanı gösterir, pagination UI yok. 11+ dokümanı olan kullanıcı "dokümanlarım kayıp" algısı yaşar. Client-side arama da sadece bu 10 kayıt üzerinde çalışır.

### Problem

**`frontend-new/app/dashboard/documents/page.tsx:39`:**
```tsx
<DocumentList />
```

**`frontend-new/components/documents/DocumentList.tsx:26`:**
```typescript
const { documents, isLoading, deleteDocument } = useDocuments();
```
→ Default parametrelerle çağırılıyor: `page=1, pageSize=10, search=""`

**`frontend-new/hooks/useDocuments.ts:150-154`:**
```typescript
export const useDocuments = (
    page: number = 1,
    pageSize: number = 10,
    search: string = ""
) => {
```

**Mevcut çözüm:** `DocumentsTable.tsx:116` tam pagination desteği var (page size selector, prev/next butonları) ama `DocumentList`'e bağlı değil.

### Enterprise Best Practice

Bir SaaS ürününde list view'da pagination/infinite scroll olmadan hardcoded limit kullanılmaz. Kullanıcı tüm veriye erişebilmeli.

### Fix

**ÖNEMLİ:** `DocumentsTable` kendi başlığını, toolbar'ını ve upload CTA'sını render eder (`DocumentsTable.tsx:438-453`). Mevcut `page.tsx` de kendi header/upload butonu var. Direkt swap yapılırsa çift header + çift CTA oluşur.

**Adım 1 — page.tsx header/CTA'sını kaldır, DocumentsTable'ı render et:**

```tsx
// frontend-new/app/dashboard/documents/page.tsx
import { DocumentsTable } from "@/components/knowledge-base/DocumentsTable";

export default function DocumentsPage() {
    return (
        <div className="h-full overflow-auto">
            <DocumentsTable />
        </div>
    );
}
```

**Adım 2 — Mevcut header/CTA çakışmasını kontrol et:**
`DocumentsTable.tsx:438-453` kendi header ("Knowledge Base" başlığı, StorageMeter, toolbar) render ediyor. Eğer page.tsx'te başka bir header/wrapper varsa, sadece birini tut. Gerekirse DocumentsTable'dan header bölümünü prop ile disable edilebilir yap veya page.tsx'in mevcut wrapper'ını kaldır.

**Adım 3 — DocumentList kullanılmıyor doğrulaması:**
Swap sonrası `DocumentList` component'ını hiçbir route import etmiyorsa, `@deprecated` annotation ekle veya kaldır.

> **Codex validation note (9 Nisan 2026):** Bu geçiş upload entry point'i koruyacak şekilde yapılmalı. Mevcut page-level header upload butonu kaldırılırsa, `DocumentsTable` içine eşdeğer bir CTA eklenmeli veya page wrapper'da korunmalı; aksi halde `/dashboard/documents` sayfasında ingest başlatma butonu kaybolur.

### Test

- 15+ doküman yükle → hepsi listelenebilmeli (pagination ile)
- Arama tüm dokümanlar üzerinde çalışmalı (server-side)
- Sayfa başına çift header/CTA olmadığını görsel doğrula
- Upload butonu çalışıyor olmalı

---

## Finding #4 — Fallback Path Keyword Blindness

**Severity: MEDIUM-HIGH (kabul edilmiş risk)**  
**Katman:** Backend / E2E  
**Etki:** Ghost Protocol RPC deploy edilmemişse, direct insert fallback `content_search` tsvector üretmez. Keyword search tamamen kör kalır.

### Problem

**`backend/core/ingestion_utils.py:217-248` (fallback path):**
```python
insert_batch.append({
    "document_id": str(document_id),
    "content": content,
    "language": detected_language,       # ISO 639-1 yazılır
    "embedding": chunk.get("embedding"),
    "chunk_index": chunk.get("chunk_index", 0),
    # content_search YOK — tsvector üretilmez
})
```

**SQL keyword branch'i `content_search` gerektirir:**
```sql
-- 20260408190000_per_language_fts_regconfig.sql:221
AND dc.content_search @@ plainto_tsquery(search_language::regconfig, query_text)
```

### Bağlam

Bu Faz 5 directive'inde **K9 kararı** olarak bilinçli kabul edildi: "Fallback only triggers when Ghost Protocol RPC not deployed. Active hot path always uses RPC." Pre-launch durumunda RPC her zaman deploy edilmiş olacak.

### Enterprise Best Practice

Fallback path'ler sessizce kalite düşürmemeli. En azından monitoring/alerting olmalı.

### Fix (defensive — zorunlu değil ama önerilen)

**Dosya:** `backend/core/ingestion_utils.py`

`_insert_chunks_direct()` fonksiyonunun başına uyarı log'u ekle:

```python
def _insert_chunks_direct(self, ...):
    logger.warning(
        "⚠️ [DirectInsert] Fallback path active — keyword search will NOT work "
        "for these chunks. Deploy Ghost Protocol RPC to enable full FTS. "
        f"doc_id={document_id}"
    )
    # ... mevcut kod ...
```

Bu log production monitoring'de alert tetikleyebilir — RPC deployment drift'ini erken yakalar.

### Test

- Fallback path tetiklendiğinde log mesajı WARNING seviyesinde olmalı
- RPC mevcut olduğunda bu log hiç görülmemeli

---

## Finding #5 — /documents Pagination Contract Bozukluğu

**Severity: MEDIUM**  
**Katman:** Backend API / Frontend  
**Etki:** `/documents` endpoint'inde 3 ayrı sorun var: (a) `X-Total-Count` header sadece başarılı dokümanlardan, (b) failed file query offset kullanmıyor — her sayfaya aynı failed'lar ekleniyor, (c) birleşik liste sort sonrası page boundary kayar.

### Problem — 3 Katmanlı

**Sorun A — Header drift:**

`documents.py:292-293`'te header sadece başarılı dokümanlardan set edilir:
```python
if db_res.count is not None:
     response.headers["X-Total-Count"] = str(db_res.count)
```
Sonra `documents.py:358`'de failed file'lar eklenir — header zaten set.

**Sorun B — Failed files offset'siz:**

`documents.py:286-288` başarılı dokümanlar offset/limit ile paginate edilir:
```python
db_res = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
```

Ama `documents.py:328-330` failed file query'si offset yok, sadece `limit(limit)`:
```python
failed_res = failed_query.order("created_at", desc=True).limit(limit).execute()
```
→ **Sayfa 1'de görünen failed file'lar, sayfa 2'de de tekrar görünür.**

**Sorun C — Post-merge sort:**

`documents.py:380` birleşik listeyi `created_at`'e göre sort eder:
```python
docs.sort(key=lambda x: x.get('created_at', ''), reverse=True)
```
Bu sort, pagination boundary'lerini kırar. Başarılı dokümanlar DB'den sıralı geliyor ama failed file'lar araya giriyor — sayfa geçişlerinde kayıp/tekrar riski.

**Frontend etkisi:**

`useDocuments.ts:91-93` header'a güveniyor:
```typescript
const totalHeader = response.headers['x-total-count'];
const total = totalHeader ? parseInt(totalHeader, 10) : response.data.length;
```

`DocumentsTable.tsx:183-186` bu total'den sayfa hesaplıyor — yanlış sonuç.

### Enterprise Best Practice

Birden fazla kaynaktan veri birleştiren paginated endpoint'ler, tüm kaynakları birleşik bir view olarak paginate etmeli. En temiz çözüm: DB-level UNION veya ayrı API response'ları.

### Fix (Önerilen — Ayrı Kanal)

**Yaklaşım:** Failed file'ları başarılı dokümanlarla aynı response'ta karıştırmak yerine ayrı bir kanal kullan.

**Adım 1 — Response'u ayır:**

```python
# documents.py — return değerini değiştir:
result = {
    "documents": docs,        # Sadece başarılı, paginated
    "failed_files": failed_docs,  # Ayrı liste, pagination yok (genelde az sayıda)
    "total_documents": db_res.count or 0,
    "total_failed": len(failed_docs) if include_failed else 0,
}
```

**Adım 2 — Frontend ayrı render:**

Failed file'ları pagination'dan bağımsız olarak ayrı bir section'da göster (örn. "Failed Uploads" uyarı banner'ı). Bu şekilde:
- Başarılı dokümanlar temiz paginate olur
- Failed file'lar her sayfada tekrar etmez
- `X-Total-Count` sadece başarılı doküman toplamını gösterir (doğru)

**Alternatif (minimal fix):** Eğer mevcut response formatı korunmalıysa, failed file'lara da offset/limit uygula ve header'ı birleşik total yap. Ama bu "failed + success" mixed pagination UX açısından kötü.

> **Codex validation note (9 Nisan 2026):** Bu remediation response shape değiştiriyor. `useDocuments` hook'u ve onu kullanan diğer consumer'lar (`DocumentsTable`, `KnowledgeBaseBrowser`) aynı değişiklik setine explicit olarak dahil edilmeden uygulanmamalı; aksi halde backend fix frontend'i kırar.

### Test

- 10 başarılı + 3 failed doküman, pageSize=5:
  - Sayfa 1: 5 başarılı doküman + 3 failed (ayrı section)
  - Sayfa 2: 5 başarılı doküman + 3 failed (ayrı section, aynı)
  - Sayfa 3: 0 başarılı (boş) → sayfa gösterilmez
- Failed file'lar sayfa değiştiğinde tekrar ETMEMELİ (eski davranış) veya ayrı section'daysa tutarlı kalmalı
- `X-Total-Count` = başarılı doküman sayısı (pagination doğru)

---

## Finding #6 — Blocking I/O (search.py + chat.py embedding)

**Severity: MEDIUM**  
**Katman:** Backend / Performance  
**Etki:** `search.py` tamamen senkron (embedding + 2 RPC), `chat.py` RPC'yi thread'e sarıyor ama embedding hâlâ senkron. Trafik altında event loop bloklanır, tail latency artar.

### Problem

**`backend/api/v1/search.py:137` (blocking embedding):**
```python
query_vector = embeddings_model.embed_query(payload.query)
```

**`search.py:163, 174` (blocking RPC):**
```python
response = supabase.rpc("hybrid_search_scoped", {...}).execute()  # senkron!
```

**`backend/api/v1/chat.py:1623` (blocking embedding):**
```python
query_vector = embeddings_model.embed_query(search_query)  # senkron!
```

**`chat.py:1730` (RPC doğru thread'de):**
```python
response = await asyncio.wait_for(asyncio.to_thread(
    lambda: supabase.rpc("hybrid_search_scoped", {...}).execute()
), timeout=_DB_RPC_TIMEOUT)  # ✓ doğru pattern
```

### Enterprise Best Practice

Async endpoint'lerdeki tüm I/O-bound çağrılar (HTTP, DB, external API) `asyncio.to_thread()` veya native async client ile sarılmalı.

### Fix

**Dosya:** `backend/api/v1/search.py`

Chat.py'deki doğru pattern'i (`asyncio.wait_for` + `asyncio.to_thread` + timeout) search.py'ye de uygula:

```python
import asyncio

_EMBED_TIMEOUT = 10.0   # embedding API timeout (saniye)
_DB_RPC_TIMEOUT = 15.0  # DB RPC timeout (saniye) — chat.py ile tutarlı

# Embedding — line 137
query_vector = await asyncio.wait_for(
    asyncio.to_thread(embeddings_model.embed_query, payload.query),
    timeout=_EMBED_TIMEOUT,
)

# RPC çağrıları — line 163 ve 174 (her iki branch için)
response = await asyncio.wait_for(
    asyncio.to_thread(
        lambda: supabase.rpc("hybrid_search_scoped", {
            "query_text": payload.query,
            "query_embedding": query_vector,
            "match_count": payload.limit,
            "filter_org_id": organization_id,
            "filter_scope_ids": effective_scope_ids,
            "similarity_threshold": payload.threshold,
            "search_language": search_language,
        }).execute()
    ),
    timeout=_DB_RPC_TIMEOUT,
)
```

**Dosya:** `backend/api/v1/chat.py`

```python
# Embedding — line 1623 (RPC zaten to_thread + wait_for içinde, sadece embedding eksik)
query_vector = await asyncio.wait_for(
    asyncio.to_thread(embeddings_model.embed_query, search_query),
    timeout=_EMBED_TIMEOUT,
)
```

**Not:** `_DB_RPC_TIMEOUT` chat.py'de zaten tanımlı. search.py'de de aynı değeri kullan. `_EMBED_TIMEOUT` her iki dosyaya da eklenecek yeni sabit.

### Test

- Search endpoint'i concurrent 10 request ile test et → tail latency öncesine göre düşmeli
- Embedding timeout aşılırsa → `asyncio.TimeoutError` → HTTP 504 veya uygun hata
- Functional davranış değişmemeli (aynı sonuçlar)

---

## Finding #7 — useSearch Hook Kontrat Kopukluğu

**Severity: LOW-MEDIUM**  
**Katman:** Frontend / API Contract  
**Etki:** `useSearch` hook'u `top_k` ve `filters` gönderiyor, backend `limit` ve `scope_ids` bekliyor. Hook şu an hiçbir canlı route'ta kullanılmıyor — dormant bug.

### Problem

**`frontend-new/hooks/useSearch.ts:175-181`:**
```typescript
const response = await api.post('/search', {
    query,
    top_k: topK,        // ← Backend 'limit' bekliyor
    filters,             // ← Backend 'scope_ids' bekliyor
}, {
    signal: abortController.signal,
});
```

**`backend/api/v1/search.py:74-86` (backend contract):**
```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    limit: int = Field(default=10, ge=1, le=50)           # 'top_k' değil
    threshold: float = Field(default=0.25, ge=0.0, le=1.0)
    scope_ids: list[str] | None = Field(default=None)      # 'filters' değil
    include_scope_analysis: bool = Field(default=False)
```

**Kullanım:** Hook sadece test dosyasında import edilmiş, hiçbir canlı page/component'ta yok.

### Enterprise Best Practice

Frontend-backend kontratları TypeScript type generation (OpenAPI → TypeScript) veya shared schema ile senkronize tutulmalı. Dead/dormant code periyodik olarak temizlenmeli.

### Fix

**Dosya:** `frontend-new/hooks/useSearch.ts`

```typescript
const response = await api.post('/search', {
    query,
    limit: topK,                                    // top_k → limit
    scope_ids: filters?.scope_ids || undefined,     // filters → scope_ids
    threshold: filters?.threshold || undefined,
    include_scope_analysis: filters?.include_scope_analysis || false,
}, {
    signal: abortController.signal,
});
```

Veya hook aktive edilene kadar `@deprecated` annotation ile işaretlenip backlog'a alınabilir.

### Test

- Hook'u canlı bir route'a bağla → backend'den valid response gelmeli
- Veya integration test'te kontratı doğrula

---

## Finding #8 — CI Integration Test Gap (SQL Drift Riski)

**Severity: MEDIUM**  
**Katman:** DevOps / Testing  
**Etki:** DB-integration testleri CI'da hiç çalışmıyor. SQL fonksiyon regresyonları (Finding #1 gibi) ancak manuel smoke ile yakalanıyor.

### Problem

**`backend/tests/integration/test_ghost_protocol_sql.py:23-32` (env-based skip):**
```python
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
HAS_DATABASE = bool(SUPABASE_URL and SUPABASE_KEY)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_db,
    pytest.mark.skipif(not HAS_DATABASE, reason="Database connection required"),
]
```

**`.github/workflows/ci.yml:69-72` (sadece unit marker):**
```yaml
- name: Run unit tests
  working-directory: backend
  run: python -m pytest tests/ -m "unit" --tb=short -q
```

CI sadece `unit` marker çalıştırıyor. `integration` ve `requires_db` marker'lı testler skip ediliyor. `SUPABASE_URL` CI'da gerçek bir veritabanına işaret etmiyor (test placeholder).

> **Codex validation note (9 Nisan 2026):** Dosya yolu burada integration klasörü olarak düzeltildi. Önerilen yeni assertion testi `backend/tests/unit/test_sql_migration_assertions.py` altında kalırsa mevcut CI marker filtresiyle gerçekten koşar.

### Enterprise Best Practice

SQL fonksiyon gövdesi `CREATE OR REPLACE` ile tamamen değişiyor. CI'da en azından SQL assertion testleri çalışmalı:
- Fonksiyon imzası değişmedi mi?
- Beklenen WHERE koşulları fonksiyon gövdesinde var mı?
- pg_proc sorgusu ile runtime doğrulama

### Fix — 2 Seviye

**Seviye 1 (minimal — önerilen):** CI'ya SQL body assertion testi ekle. Bu test gerçek DB bağlantısı gerektirmez — migration dosyalarını statik analiz eder:

```python
# backend/tests/unit/test_sql_migration_assertions.py
import pathlib
import pytest

MIGRATIONS_DIR = pathlib.Path(__file__).parents[3] / "supabase" / "migrations"

def _latest_migration_containing(func_name: str) -> str:
    """Find the latest migration file that defines a given SQL function."""
    candidates = sorted(MIGRATIONS_DIR.glob("*.sql"), reverse=True)
    for path in candidates:
        text = path.read_text()
        if f"CREATE OR REPLACE FUNCTION public.{func_name}" in text:
            return text
    pytest.skip(f"No migration found defining {func_name}")

class TestHybridSearchScopedAssertions:
    def test_null_scope_id_branch_present(self):
        """Regression guard: OR d.scope_id IS NULL must be in hybrid_search_scoped."""
        body = _latest_migration_containing("hybrid_search_scoped")
        assert body.count("d.scope_id IS NULL") >= 2, (
            "hybrid_search_scoped must contain 'OR d.scope_id IS NULL' in both "
            "semantic_results and keyword_results CTEs"
        )

    def test_tombstone_cte_present(self):
        """Ensure tombstone filtering is not dropped during rewrites."""
        body = _latest_migration_containing("hybrid_search_scoped")
        assert "tombstoned_docs" in body, (
            "hybrid_search_scoped must include compliance_tombstones filtering"
        )

    def test_search_language_sanitization(self):
        """Ensure search_language is sanitized (not hardcoded to 'simple')."""
        body = _latest_migration_containing("hybrid_search_scoped")
        assert "search_language := 'simple'" not in body, (
            "hybrid_search_scoped must not override search_language to 'simple'"
        )
```

**Seviye 2 (gelişmiş — opsiyonel):** CI'ya staging Supabase projesi bağla, `integration` marker'lı testleri de çalıştır. Bu daha fazla altyapı gerektirir ve go-live sonrası yapılabilir.

### Test

- `pytest tests/unit/test_sql_migration_assertions.py -v` → tüm assertion'lar geçer
- Eğer birisi gelecekte `OR d.scope_id IS NULL`'ı silerse → test FAIL eder

---

## Uygulama Sırası

```
Faz   Kapsamdaki Bulgular       Tahmini Süre    Gate
───── ─────────────────────────  ──────────────  ──────────────────────
 A    #1 (BLOCKER)               1 saat          Migration push + smoke
      → Ayrı directive: CODEX_HOTFIX_NULL_SCOPE_REGRESSION.md
 B    #2 (HIGH)                  30 dk           Build test (CI)
 C    #8 (MEDIUM — CI guard)     1 saat          pytest geçiyor
 D    #6 (MEDIUM — async I/O)    1 saat          Functional + timeout test
 E    #5 (MEDIUM — pagination)   2 saat          API + frontend test
 F    #3 (MEDIUM-HIGH — UX)      2 saat          Frontend görsel doğrulama
 G    #4 (defensive log)         15 dk           Log doğrulama
 H    #7 (LOW — dormant)         30 dk           Hook aktive edilince
```

**Faz A zorunlu ve izole — diğer fazlar paralel yapılabilir.**  
**Faz C (#8) önerilir Faz A ile birlikte:** SQL assertion testleri aynı tür regresyonun tekrarını önler.

---

## Dosya Değişiklik Özeti

| Dosya | Bulgu | Değişiklik |
|-------|-------|------------|
| `supabase/migrations/YYYYMMDDHHMMSS_fix_null_scope_regression.sql` | #1 | YENİ — `OR d.scope_id IS NULL` geri ekle (2 CTE × 1 fonksiyon). **Ayrı directive'de.** |
| `frontend-new/next.config.ts` | #2 | MODIFY — fail-fast guard (line 78, 193) |
| `frontend-new/app/dashboard/documents/page.tsx` | #3 | MODIFY — `DocumentList` → `DocumentsTable` (header çakışmasına dikkat) |
| `backend/core/ingestion_utils.py` | #4 | MODIFY — WARNING log ekle (line 217) |
| `backend/api/v1/documents.py` | #5 | MODIFY — failed files'ı ayrı kanal veya offset'li pagination |
| `backend/api/v1/search.py` | #6 | MODIFY — `asyncio.wait_for` + `to_thread` ekle (line 137, 163, 174) |
| `backend/api/v1/chat.py` | #6 | MODIFY — embedding `wait_for` + `to_thread` ekle (line 1623) |
| `frontend-new/hooks/useSearch.ts` | #7 | MODIFY — `top_k` → `limit`, `filters` → `scope_ids` |
| `backend/tests/unit/test_sql_migration_assertions.py` | #8 | YENİ — SQL body assertion testleri (scope NULL, tombstone, language) |

---

## Çapraz Risk Notu

Finding #1 ve #4 birlikte düşünülmeli: Eğer RPC deploy edilmemişken (#4) scope-restricted kullanıcı sorgu yaparsa (#1), hem keyword search kör hem NULL scope dokümanlar kayıp olur — retrieval kalitesi çift katmanlı düşer. #1 fix'i bu zincirin en kritik halkasını kapatır.

---

## Kontrol Listesi (Codex Self-Check)

- [ ] Migration push sonrası `supabase db push --include-all --dry-run` → "up to date"
- [ ] `hybrid_search_scoped` fonksiyonunda `OR d.scope_id IS NULL` 2 yerde mevcut
- [ ] `next build` (NODE_ENV=production, NEXT_PUBLIC_API_URL unset) → build hata verir
- [ ] `next build` (NODE_ENV=production, NEXT_PUBLIC_API_URL set) → build başarılı
- [ ] `/dashboard/documents` sayfası pagination ile 10+ doküman gösterir
- [ ] Documents sayfasında çift header/CTA yok
- [ ] Failed dokümanlar sayfa değiştiğinde tekrar etmiyor
- [ ] `search.py` embedding ve RPC: `asyncio.wait_for` + `asyncio.to_thread` + timeout
- [ ] `chat.py` embedding: `asyncio.wait_for` + `asyncio.to_thread` + timeout
- [ ] Fallback insert path WARNING log'u mevcut
- [ ] SQL assertion testleri geçiyor: `pytest tests/unit/test_sql_migration_assertions.py -v`
- [ ] Tüm mevcut testler geçer (`pytest` + `ruff check`)
