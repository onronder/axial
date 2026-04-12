# HOTFIX — NULL scope_id Regresyonu

> **Severity:** BLOCKER — deploy öncesi zorunlu  
> **Tarih:** 9 Nisan 2026  
> **Kök Neden:** Faz 5 migration'ı `hybrid_search_scoped` fonksiyonunu yeniden yazarken `20260228000000_scoped_search_include_null_scope.sql` migration'ındaki `OR d.scope_id IS NULL` dalını kaybetti.  
> **Etki:** Scope-restricted kullanıcılar, `scope_id = NULL` olan org-level paylaşımlı dokümanları göremez. Hem search hem chat path'i etkileniyor.

---

## Kök Neden Detayı

Faz 5 migration'ı (`20260408190000_per_language_fts_regconfig.sql`) `hybrid_search_scoped` fonksiyonunu `CREATE OR REPLACE` ile tamamen yeniden yazdı. Bu, önceki fonksiyon gövdesini siler. Önceki fix'te (Şubat 2026) eklenen NULL scope_id dalı yeni gövdede yer almıyor.

**Eski (doğru) — `20260228000000_scoped_search_include_null_scope.sql`:**

Line 49 (semantic CTE):
```sql
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
```

Line 82 (keyword CTE):
```sql
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
```

**Faz 5 (regresyon) — `20260408190000_per_language_fts_regconfig.sql`:**

Line 330 (semantic CTE):
```sql
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
```

Line 368 (keyword CTE):
```sql
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))
```

**Çağrı zincirleri:**
- `search.py:161` → `supabase.rpc("hybrid_search_scoped", {...})`
- `chat.py:1756` → `supabase.rpc("hybrid_search_scoped", {...})` (restricted user path)

---

## Fix

**Yeni migration dosyası:** `supabase/migrations/YYYYMMDDHHMMSS_fix_scoped_search_null_scope_regression.sql`

Bu migration mevcut `hybrid_search_scoped` fonksiyonunu `CREATE OR REPLACE` ile güncelleyecek. Tek değişiklik: semantic_results ve keyword_results CTE'lerindeki scope filtre satırına `OR d.scope_id IS NULL` eklemek.

**Değişecek 2 satır (semantic CTE ve keyword CTE):**

```sql
-- MEVCUT (line 330 ve line 368):
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids))

-- OLACAK:
AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
```

**ÖNEMLİ:** Fonksiyonun geri kalanı (imza, return type, GRANT'lar, diğer WHERE koşulları, tombstone CTE, search_language sanitizasyonu) DEĞİŞMEMELİ. Sadece bu 2 satır güncellenir.

**Tam fonksiyon gövdesini kopyalama:** Mevcut `20260408190000_per_language_fts_regconfig.sql` dosyasındaki `hybrid_search_scoped` fonksiyonunun tamamını (line 271-416) yeni migration'a kopyala, sadece line 330 ve line 368'deki scope filtrelerini düzelt.

**Migration yapısı:**

```sql
-- HOTFIX: Restore NULL scope_id visibility in hybrid_search_scoped
-- 
-- Faz 5 migration (20260408190000) rewrote hybrid_search_scoped but dropped
-- the OR d.scope_id IS NULL branch added by 20260228000000. This caused
-- scope-restricted users to lose visibility of org-level shared documents.

BEGIN;

CREATE OR REPLACE FUNCTION public.hybrid_search_scoped(
    -- ... aynı imza ...
)
RETURNS TABLE (
    -- ... aynı return type ...
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    -- ... aynı gövde, SADECE scope filtre satırları düzeltilmiş ...
    -- semantic_results CTE'de:
    --   AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
    -- keyword_results CTE'de:
    --   AND (filter_scope_ids IS NULL OR d.scope_id = ANY(filter_scope_ids) OR d.scope_id IS NULL)
END;
$$;

-- Re-grant (imza aynı, teknik olarak gereksiz ama defensive)
GRANT EXECUTE ON FUNCTION public.hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION public.hybrid_search_scoped(TEXT, VECTOR, INT, UUID, TEXT[], FLOAT, FLOAT, FLOAT, TEXT) TO service_role;

NOTIFY pgrst, 'reload config';

COMMIT;
```

---

## Test

### T1. NULL scope_id doküman scope-filtered aramayla bulunmalı

```sql
-- Setup: org_id ve scope_id = NULL doküman + chunk oluştur
-- Test: hybrid_search_scoped(filter_scope_ids = ['scope_a']) çağır
-- Beklenen: scope_id IS NULL doküman sonuçlarda olmalı
```

### T2. Farklı scope dokümanı filtrelenmeli

```sql
-- Setup: scope_id = 'scope_b' doküman + chunk oluştur
-- Test: hybrid_search_scoped(filter_scope_ids = ['scope_a']) çağır
-- Beklenen: scope_b doküman sonuçlarda OLMAMALI
```

### T3. filter_scope_ids = NULL → tüm dokümanlar

```sql
-- Test: hybrid_search_scoped(filter_scope_ids = NULL) çağır
-- Beklenen: tüm dokümanlar gelir (scope filtre devre dışı)
```

### T4. Mevcut testler kırılmamalı

```bash
pytest tests/ -m "unit" --tb=short -q
```

---

## Doğrulama

```bash
# 1. Migration push
supabase db push --include-all

# 2. Dry-run
supabase db push --include-all --dry-run
# Beklenen: "Remote database is up to date"

# 3. SQL doğrulama — fonksiyon gövdesinde OR d.scope_id IS NULL var mı?
# Supabase SQL Editor'da:
SELECT prosrc FROM pg_proc WHERE proname = 'hybrid_search_scoped';
# Çıktıda "d.scope_id IS NULL" ifadesi 2 kere geçmeli (semantic + keyword CTE)
```

---

## Kontrol Listesi

- [ ] Yeni migration dosyası oluşturuldu
- [ ] Semantic CTE'de `OR d.scope_id IS NULL` mevcut
- [ ] Keyword CTE'de `OR d.scope_id IS NULL` mevcut
- [ ] Fonksiyon imzası ve diğer WHERE koşulları DEĞİŞMEDİ
- [ ] GRANT ve NOTIFY korundu
- [ ] `supabase db push --include-all` başarılı
- [ ] `supabase db push --include-all --dry-run` → "up to date"
- [ ] Mevcut unit testler geçiyor
- [ ] pg_proc sorgusu fonksiyon gövdesinde NULL scope dalını doğruluyor
