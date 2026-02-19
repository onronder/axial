# AxioHub API Referansi

> **Surum:** 1.0 | **Tarih:** Subat 2026 | **Temel URL:** `/api/v1`
>
> AxioHub REST API icin eksiksiz uc nokta referansi.
> Aksi belirtilmedikce tum uc noktalar kimlik dogrulama gerektirir.
> Hiz sinirlari kullanici basina, dakika basina, slowapi + Redis araciligiyla uygulanir.

---

## Icindekiler

1. [Sohbet ve Konusmalar](#1-sohbet-ve-konusmalar)
2. [Arama](#2-arama)
3. [Belgeler](#3-belgeler)
4. [Yuklemeler](#4-yuklemeler)
5. [Entegrasyonlar ve Baglayicilar](#5-entegrasyonlar-ve-baglayicilar)
6. [Ayarlar ve Profil](#6-ayarlar-ve-profil)
7. [Takim Yonetimi](#7-takim-yonetimi)
8. [Faturalandirma ve Kullanim](#8-faturalandirma-ve-kullanim)
9. [Isler ve Veri Alimi](#9-isler-ve-veri-alimi)
10. [Bildirimler](#10-bildirimler)
11. [Onay Yonetimi](#11-onay-yonetimi)
12. [Uyumluluk](#12-uyumluluk)
13. [Onaylar](#13-onaylar)
14. [Yonetim ve Denetim](#14-yonetim-ve-denetim)
15. [Olu Mektup Kuyrugu (DLQ)](#15-olu-mektup-kuyrugu-dlq)
16. [Saglik](#16-saglik)
17. [Webhook'lar](#17-webhooklar)
18. [MCP (Model Context Protocol)](#18-mcp-model-context-protocol)
19. [Geri Bildirim ve Analitik](#19-geri-bildirim-ve-analitik)

**Toplam Uc Nokta: ~146** (kayit disi saglik yoklamalari ve `dependencies.py` icerisindeki dokumantasyon ornekleri haric)

---

## Kimlik Dogrulama

Tum kimlik dogrulamali uc noktalar, `Authorization` basliginda gecerli bir JWT gerektirir:

```
Authorization: Bearer <supabase_access_token>
```

JWT, Supabase Auth tarafindan verilir ve her istekte dogrulanir. Rol tabanli erisim, bagimlilik enjeksiyonu araciligiyla uygulanir:

| Bagimlilik | Aciklama |
|-----------|----------|
| `get_current_user` | Herhangi bir kimligi dogrulanmis kullanici (`user_id` dondurur) |
| `require_editor` | Editor veya yonetici rolu gerektirir |
| `require_admin` | Yonetici rolu gerektirir |
| `require_plan(["pro", "enterprise"])` | Belirli abonelik plani gerektirir |
| `require_paid_access` | Herhangi bir ucretli plan gerektirir (starter+) |
| `get_user_organization_id` | Kullanici baglamindaki kurulusID'sini cikarir |

---

## 1. Sohbet ve Konusmalar

### Konusmalar

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/conversations` | Tum konusmalari listele (sayfalandirilmis) | Kullanici | 60/dk |
| `POST` | `/conversations` | Yeni konusma olustur | Kullanici | 30/dk |
| `GET` | `/conversations/{conversation_id}` | Konusma ayrintilari al | Kullanici | 60/dk |
| `PATCH` | `/conversations/{conversation_id}` | Konusmayi guncelle (baslik vb.) | Kullanici | 30/dk |
| `DELETE` | `/conversations/{conversation_id}` | Konusmayi sil | Kullanici | 30/dk |
| `GET` | `/conversations/{conversation_id}/messages` | Konusmadaki mesajlari listele | Kullanici | 60/dk |

### Sohbet

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/chat` | Mesaj gonder ve AI yaniti al (SSE akisi) | Kullanici | 30/dk |
| `POST` | `/chat/stream` | Alternatif akisli sohbet uc noktasi | Kullanici | 30/dk |

**`POST /chat` Istek:**
```json
{
  "message": "What are the key findings from the Q4 report?",
  "conversation_id": "uuid (optional - creates new if omitted)",
  "scope": "google_drive (optional - filter by source)",
  "model": "gpt-4o (optional)"
}
```

**Yanit:** Server-Sent Events (SSE) akisi
```
data: {"content": "Based on", "type": "token"}
data: {"content": " the Q4 report", "type": "token"}
...
data: {"sources": [...], "type": "sources"}
data: [DONE]
```

---

## 2. Arama

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/search` | Hibrit vektor + tam metin aramasi | Kullanici | 60/dk |

**Istek:**
```json
{
  "query": "quarterly revenue growth",
  "limit": 10,
  "scope_ids": ["scope_uri_1"],
  "filters": {
    "source_type": "google_drive"
  }
}
```

**Yanit:**
```json
{
  "results": [
    {
      "chunk_id": "uuid",
      "document_id": "uuid",
      "content": "Revenue grew 15% in Q4...",
      "score": 0.89,
      "metadata": { "title": "Q4 Report", "page": 3 }
    }
  ],
  "total": 42
}
```

---

## 3. Belgeler

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/documents/stats` | Belge istatistikleri al (sayi, depolama) | Kullanici | 60/dk |
| `GET` | `/documents` | Belgeleri listele (sayfalandirilmis, aranabilir) | Kullanici | 60/dk |
| `DELETE` | `/documents` | Toplu belge silme | Editor | 30/dk |
| `DELETE` | `/documents/{doc_id}` | Tekil belge silme | Editor | 30/dk |
| `PATCH` | `/documents/{document_id}` | Belge meta verisini guncelle | Editor | 30/dk |
| `GET` | `/documents/{document_id}/chunks` | Belge parcalarini listele (sayfalandirilmis) | Kullanici | 60/dk |
| `GET` | `/documents/{document_id}/content` | Belge metin icerigini al | Kullanici | 60/dk |
| `GET` | `/documents/{document_id}/download` | Orijinal dosyayi indir | Kullanici | 30/dk |
| `POST` | `/documents/{document_id}/wipe` | Guvenli silme baslat (DoD 5220.22-M) | Editor | 10/dk |
| `GET` | `/documents/{document_id}/wipe-status` | Silme ilerlemesini kontrol et | Kullanici | 60/dk |

---

## 4. Yuklemeler

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/uploads/check-duplicates` | SHA-256 hash ile yinelenen dosyalari kontrol et | Kullanici | 60/dk |
| `POST` | `/uploads/upload-url` | Dogrudan yukleme icin on imzali URL al | Kullanici | 30/dk |
| `POST` | `/uploads/file/reference` | Yuklenen dosyayi kaydet ve veri alimini tetikle | Editor | 30/dk |

**Yukleme Akisi:**
1. `POST /uploads/check-duplicates` -> `{is_duplicate, existing_document_id?}`
2. `POST /uploads/upload-url` -> `{upload_url, storage_path}`
3. `PUT {upload_url}` (dogrudan Supabase Storage'a)
4. `POST /uploads/file/reference` -> `{job_id, status: "queued"}`

---

## 5. Entegrasyonlar ve Baglayicilar

### OAuth Token Degisimi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/integrations/google/exchange` | Google OAuth kodunu degistir | Kullanici | 30/dk |
| `POST` | `/integrations/notion/exchange` | Notion OAuth kodunu degistir | Kullanici | 30/dk |
| `POST` | `/integrations/microsoft/exchange` | Microsoft OAuth kodunu degistir (PKCE) | Kullanici | 30/dk |
| `POST` | `/integrations/dropbox/exchange` | Dropbox OAuth kodunu degistir | Kullanici | 30/dk |
| `POST` | `/integrations/github/exchange` | GitHub OAuth kodunu degistir | Kullanici | 30/dk |
| `POST` | `/integrations/box/exchange` | Box OAuth kodunu degistir | Kullanici | 30/dk |

### Kimlik Bilgisi Tabanli Baglanti

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/integrations/sftp/connect` | SFTP baglantisi kur (host, kullanici, anahtar) | Kullanici | 30/dk |
| `POST` | `/integrations/s3/connect` | S3 baglantisi kur (IAM kimlik bilgileri) | Kullanici | 30/dk |

### Entegrasyon Yonetimi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/integrations/available` | Mevcut tum baglayicilari listele | Kullanici | 60/dk |
| `GET` | `/integrations/status` | Kullanicinin bagli entegrasyonlarini listele | Kullanici | 60/dk |
| `GET` | `/integrations/{provider}/status` | Belirli entegrasyon durumunu al | Kullanici | 60/dk |
| `DELETE` | `/integrations/{provider}` | Entegrasyonu kes | Editor | 30/dk |
| `GET` | `/integrations/{provider}/items` | Bagli kaynaktaki ogelere goz at | Kullanici | 60/dk |

### GitHub'a Ozel

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/integrations/github/repos` | GitHub depolarini listele | Kullanici | 60/dk |
| `POST` | `/integrations/github/repos/select` | Veri alimi icin depolari sec | Editor | 30/dk |

### Web Tarayici

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/integrations/web/crawl` | Tarama yapilandirmalarini listele | Kullanici | 60/dk |
| `GET` | `/integrations/web/crawl/active` | Aktif tarama yapilandirmasini al | Kullanici | 60/dk |
| `GET` | `/integrations/web/crawl/{config_id}` | Belirli tarama yapilandirmasini al | Kullanici | 60/dk |
| `POST` | `/integrations/web/crawl` | Yeni tarama olustur (202 dondurur) | Editor | 30/dk |
| `DELETE` | `/integrations/web/crawl/{config_id}` | Tarama yapilandirmasini sil | Editor | 30/dk |

### Veri Alimi ve Senkronizasyon

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/integrations/{provider}/ingest` | Baglayicidan veri alimini tetikle (202 dondurur) | Editor | 30/dk |
| `POST` | `/integrations/{integration_id}/sync` | Artimsal senkronizasyonu tetikle | Editor | 30/dk |
| `GET` | `/integrations/{integration_id}/sync-history` | Senkronizasyon gecmisini al | Kullanici | 60/dk |
| `GET` | `/integrations/{provider}/ingested-files` | Saglayici icin alinan dosyalari listele | Kullanici | 60/dk |

---

## 6. Ayarlar ve Profil

### Profil

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/settings/profile` | Kullanici profilini al | Kullanici | 60/dk |
| `PATCH` | `/settings/profile` | Profili guncelle (ad, tema vb.) | Kullanici | 30/dk |
| `DELETE` | `/settings/profile/me` | Hesabi sil (GDPR) | Kullanici | 3/dk |
| `POST` | `/settings/profile/me/anonymize` | Hesap verilerini anonimlistir | Kullanici | 3/dk |

### Bildirim Tercihleri

| Metot | Yol | Amac | Yetki | Hiz Siniri | Plan |
|-------|-----|------|-------|------------|------|
| `GET` | `/settings/notifications` | Bildirim tercihlerini al | Kullanici | 60/dk | Ucretli |
| `PATCH` | `/settings/notifications` | Bildirim tercihlerini guncelle | Kullanici | 30/dk | Ucretli |
| `DELETE` | `/settings/notifications` | Bildirim tercihlerini sifirla | Kullanici | 30/dk | Ucretli |

---

## 7. Takim Yonetimi

Tum takim uc noktalari ucretli plan erisimi gerektirir (`_paid_team_deps`).

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/team` | Takim ayrintilari al | Uye | 60/dk |
| `PATCH` | `/team` | Takim ayarlarini guncelle | Yonetici | 30/dk |
| `DELETE` | `/team` | Takimi sil | Yonetici (sahip) | 10/dk |
| `GET` | `/team/my-invites` | Mevcut kullanici icin bekleyen davetleri listele | Kullanici | 60/dk |
| `GET` | `/team/effective-plan` | Paywall kontrolleri icin etkin plani al | Uye | 60/dk |
| `GET` | `/team/members` | Takim uyelerini listele | Uye | 60/dk |
| `GET` | `/team/stats` | Takim istatistiklerini al | Uye | 60/dk |
| `POST` | `/team/invite` | Davet e-postasi gonder | Yonetici | 30/dk |
| `POST` | `/team/bulk-invite` | CSV ile toplu davet | Yonetici | 10/dk |
| `POST` | `/team/members` | Dogrudan uye ekle | Yonetici | 30/dk |
| `PATCH` | `/team/members/{member_id}` | Uye rolunu guncelle | Yonetici | 30/dk |
| `DELETE` | `/team/members/{member_id}` | Uyeyi kaldir | Yonetici | 30/dk |
| `POST` | `/team/members/{member_id}/resend` | Davet e-postasini yeniden gonder | Yonetici | 10/dk |
| `POST` | `/team/accept` | Takim davetini kabul et | Kullanici | 30/dk |

---

## 8. Faturalandirma ve Kullanim

### Faturalandirma

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/billing/plans` | Mevcut planlari listele | Kullanici | 60/dk |
| `POST` | `/billing/checkout` | Polar.sh odeme oturumu olustur | Kullanici | 10/dk |
| `POST` | `/billing/portal` | Polar.sh faturalandirma portali olustur | Kullanici | 10/dk |
| `GET` | `/billing/subscription` | Mevcut abonelik ayrintilari al | Kullanici | 60/dk |
| `POST` | `/billing/subscription/cancel` | Aboneligi iptal et | Kullanici | 10/dk |
| `GET` | `/billing/invoices` | Faturalari listele (sayfalandirilmis) | Kullanici | 60/dk |
| `GET` | `/billing/invoices/{order_id}/download` | Faturayi indir | Kullanici | 30/dk |
| `POST` | `/billing/fix-customer-id` | Polar musteri ID eslemesini duzelt | Kullanici | 10/dk |
| `POST` | `/billing/enterprise-inquiry` | Kurumsal plan basvurusu gonder | Kullanici | 3/dk |

### Kullanim

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/usage` | Guncel kullanim istatistiklerini al | Kullanici | 60/dk |
| `GET` | `/plans` | Mevcut planlari al (alternatif rota) | Kullanici | 60/dk |

---

## 9. Isler ve Veri Alimi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/jobs/active` | Aktif veri alim isini al | Kullanici | 60/dk |
| `GET` | `/jobs/{job_id}` | Is ayrintilari al | Kullanici | 60/dk |
| `GET` | `/jobs` | Tum veri alim islerini listele | Kullanici | 60/dk |
| `POST` | `/jobs/{job_id}/cancel` | Calisan isi iptal et | Editor | 30/dk |
| `POST` | `/jobs/files/{file_status_id}/retry` | Basarisiz dosyayi yeniden dene (maks 3) | Editor | 30/dk |
| `GET` | `/jobs/{job_id}/files` | Is icin dosya durumlarini listele | Kullanici | 60/dk |
| `POST` | `/jobs/{job_id}/retry` | Basarisiz isin tamamini yeniden dene | Editor | 10/dk |

---

## 10. Bildirimler

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/notifications` | Bildirimleri listele (sayfalandirilmis) | Kullanici | 60/dk |
| `GET` | `/notifications/unread-count` | Okunmamis bildirim sayisini al | Kullanici | 60/dk |
| `PATCH` | `/notifications/{notification_id}/read` | Bildirimi okundu olarak isaretle | Kullanici | 60/dk |
| `PATCH` | `/notifications/read-all` | Tumunu okundu olarak isaretle | Kullanici | 30/dk |
| `DELETE` | `/notifications/all` | Tum bildirimleri sil | Kullanici | 10/dk |
| `DELETE` | `/notifications/{notification_id}` | Tekil bildirimi sil | Kullanici | 30/dk |

---

## 11. Onay Yonetimi

### Kapsamlar

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/scopes` | Tum veri kapsamlarini listele | Kullanici | 60/dk |

### Kurulus Onayi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/consent/organization` | Kurulus duzeyinde onayi al | Kullanici | 60/dk |
| `PATCH` | `/consent/organization` | Kurulus onayini guncelle | Yonetici | 30/dk |

### Kapsam Onayi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/consent/scope` | Kapsam duzeyinde onayi al | Kullanici | 60/dk |
| `PATCH` | `/consent/scope` | Kapsam onayini guncelle | Editor | 30/dk |
| `POST` | `/consent/scope/bulk` | Kapsam onaylarini toplu guncelle | Editor | 30/dk |
| `PATCH` | `/consent/scope/agents` | Kapsam basina AI ajan erisimini guncelle | Editor | 30/dk |
| `DELETE` | `/consent/scope` | Kapsam onayini iptal et | Yonetici | 10/dk |

### Belge Onayi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/consent/document/{document_id}` | Belge duzeyinde onayi al | Kullanici | 60/dk |
| `PATCH` | `/consent/document/{document_id}` | Belge onayini guncelle | Editor | 30/dk |
| `PATCH` | `/consent/document/{document_id}/agents` | Belge basina AI ajan erisimini guncelle | Editor | 30/dk |
| `DELETE` | `/consent/document/{document_id}` | Belge onayini iptal et | Yonetici | 10/dk |

### Denetim ve Raporlar

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/consent/audit` | Sayfalandirilmis onay denetim izi | Kullanici | 60/dk |
| `GET` | `/consent/report` | Uyumluluk ozet raporu | Kullanici | 30/dk |

---

## 12. Uyumluluk

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/delete-request` | GDPR Madde 17 silme talebi (202 dondurur) | Kullanici | 10/dk |
| `POST` | `/admt-optout` | CCPA ADMT devre disi birakma talebi (202 dondurur) | Kullanici | 10/dk |
| `GET` | `/tombstones` | Uyumluluk mezar taslarini listele | Kullanici | 30/dk |
| `GET` | `/tombstone/{tombstone_id}` | Belirli mezar tasi ayrintilari al | Kullanici | 60/dk |
| `GET` | `/report` | Uyumluluk raporu (silmeler, durum) | Kullanici | 10/dk |
| `GET` | `/pending` | Bekleyen uyumluluk taleplerini listele | Kullanici | 30/dk |

**`POST /delete-request` Istek:**
```json
{
  "resource_type": "document",
  "resource_id": "uuid",
  "compliance_type": "gdpr_art17",
  "reason": "User requested data deletion"
}
```

**Yanit (202 Kabul Edildi):**
```json
{
  "tombstone_id": "uuid",
  "status": "active",
  "message": "Data access revoked. Secure deletion in progress.",
  "estimated_completion": "2026-02-16T08:30:00Z"
}
```

---

## 13. Onaylar

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/approvals/request` | Onay talebi olustur | Editor | 30/dk |
| `POST` | `/approvals/{approval_id}/approve` | Talebi onayla | Yonetici | 30/dk |
| `POST` | `/approvals/{approval_id}/reject` | Talebi reddet | Yonetici | 30/dk |
| `POST` | `/approvals/{approval_id}/execute` | Onaylanmis eylemi calistir | Yonetici | 30/dk |
| `GET` | `/approvals/pending` | Bekleyen onaylari listele (sayfalandirilmis) | Yonetici | 60/dk |
| `GET` | `/approvals/{approval_id}` | Onay ayrintilari al | Kullanici | 60/dk |

---

## 14. Yonetim ve Denetim

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/audit-logs` | Denetim kayitlarini listele (sayfalandirilmis, filtrelenebilir) | Yonetici | 30/dk |
| `GET` | `/audit-logs/actions` | Mevcut denetim eylem turlerini listele | Yonetici | 60/dk |
| `GET` | `/security-log` | Guvenlik olay kaydi (giris, IP) | Yonetici | 30/dk |

**`GET /audit-logs` Sorgu Parametreleri:**
```
?action=document.delete
&resource_type=document
&user_id=uuid
&from_date=2026-01-01
&to_date=2026-02-16
&page=1
&limit=50
```

---

## 15. Olu Mektup Kuyrugu (DLQ)

Basarisiz gorevler ve webhook'lar yeniden deneme ve inceleme icin DLQ'da saklanir.

### Kullanici Uc Noktalari

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/failed-tasks/{job_id}` | Belirli bir is icin basarisiz gorevi al | Kullanici | 60/dk |
| `POST` | `/retry/{task_id}` | Basarisiz gorevi elle yeniden dene | Editor | 30/dk |
| `POST` | `/resolve/{task_id}` | Basarisiz gorevi cozuldu olarak isaretle | Editor | 30/dk |
| `GET` | `/stats` | Mevcut kullanici icin DLQ istatistiklerini al | Kullanici | 60/dk |
| `GET` | `/my-tasks` | Mevcut kullanici icin tum basarisiz gorevleri listele | Kullanici | 60/dk |

### Yonetici Uc Noktalari

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/admin/all` | Tum basarisiz gorevleri listele (tum kullanicilar) | Yonetici | 30/dk |
| `POST` | `/admin/trigger-retry-cycle` | Otomatik yeniden deneme dongusunu tetikle | Yonetici | 10/dk |
| `GET` | `/admin/stats` | Global DLQ istatistikleri | Yonetici | 30/dk |

---

## 16. Saglik

Aktif saglik uc noktasi `main.py` icerisinde dogrudan tanimlanmistir (kayitli bir yonlendirici uzerinden degil). Herkese aciktir (kimlik dogrulama gerektirmez).

| Metot | Yol | Amac | Hiz Siniri |
|-------|-----|------|------------|
| `GET` | `/health` | Saglik kontrolu (DB + Redis baglantisi) | 60/dk |

**`GET /health` Yanit:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "services": {
    "database": "connected",
    "redis": "connected"
  },
  "issues": []
}
```

> **Not:** `backend/api/v1/health.py` dosyasi ek Kubernetes tarzi yoklamalar tanimlar (`/health/ready`, `/health/live`, `/health/startup`) ancak bu yonlendirici `main.py` icerisinde **kayitli degildir**. Bu uc noktalar su anda aktif degildir.

---

## 17. Webhook'lar

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/webhooks/polar` | Polar.sh odeme webhook alicisi | Imza | Yok |
| `POST` | `/webhooks/dlq/retry` | DLQ'dan basarisiz webhook'lari yeniden dene | Yonetici | 10/dk |
| `GET` | `/webhooks/dlq/stats` | Webhook DLQ istatistikleri | Yonetici | 30/dk |
| `GET` | `/webhooks/health` | Webhook sistemi sagligi | Yonetici | 60/dk |

**Polar Webhook Olaylari:**
- `subscription.created` -- Yeni abonelik
- `subscription.updated` -- Plan degisikligi
- `subscription.cancelled` -- Iptal
- `order.completed` -- Tek seferlik odeme

---

## 18. MCP (Model Context Protocol)

MCP, harici AI ajanlarinin AxioHub bilgi tabaninda arama yapmasini ve etkilesimde bulunmasini saglar.

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/mcp/v1/rpc` | MCP JSON-RPC uc noktasi | API Anahtari | 60/dk |
| `POST` | `/mcp/api-keys` | MCP API anahtari olustur | Yonetici | 10/dk |
| `GET` | `/mcp/api-keys` | MCP API anahtarlarini listele | Yonetici | 60/dk |
| `GET` | `/mcp/api-keys/{key_id}` | Belirli API anahtarini al | Yonetici | 60/dk |
| `POST` | `/mcp/api-keys/{key_id}/rotate` | API anahtarini yenile | Yonetici | 10/dk |
| `DELETE` | `/mcp/api-keys/{key_id}` | API anahtarini iptal et | Yonetici | 10/dk |
| `GET` | `/mcp/info` | MCP sunucu bilgisini al | Kullanici | 60/dk |

**MCP RPC Istek:**
```json
{
  "jsonrpc": "2.0",
  "method": "search",
  "params": {
    "query": "quarterly revenue",
    "limit": 5
  },
  "id": 1
}
```

---

## 19. Geri Bildirim ve Analitik

### Sohbet Geri Bildirimi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `POST` | `/chat/feedback` | Sohbet yaniti geri bildirimi gonder (201 dondurur) | Kullanici | 30/dk |
| `GET` | `/chat/feedback/conversation/{conversation_id}` | Konusma icin geri bildirimi al | Kullanici | 60/dk |

### Takim Analitigi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/analytics/feedback` | Takim duzeyinde geri bildirim analitigi | Yonetici | 30/dk |
| `GET` | `/analytics/feedback/sources` | Geri bildirim kaynagi metrikleri | Yonetici | 30/dk |

### Platform Yonetimi

| Metot | Yol | Amac | Yetki | Hiz Siniri |
|-------|-----|------|-------|------------|
| `GET` | `/admin/feedback/platform` | Platform geneli geri bildirim verileri | Super Yonetici | 10/dk |
| `POST` | `/admin/feedback/refresh-metrics` | Geri bildirim metrik onbellegini yenile | Super Yonetici | 3/dk |

---

## Hata Yanit Formati

Tum uc noktalar hatalari tutarli bir formatta dondurur:

```json
{
  "detail": "Human-readable error message"
}
```

### Yaygin HTTP Durum Kodlari

| Kod | Anlam | Yaygin Nedenler |
|-----|-------|-----------------|
| `400` | Hatali Istek | Gecersiz girdi, dogrulama hatasi |
| `401` | Yetkisiz | Eksik veya gecersiz JWT |
| `402` | Odeme Gerekli | Kota asildi, plan yukseltmesi gerekli |
| `403` | Yasak | Yetersiz rol veya plan |
| `404` | Bulunamadi | Kaynak mevcut degil veya kullanicinin kurulusunda degil |
| `409` | Catisma | Yinelenen kaynak, es zamanli degisiklik |
| `422` | Islenemeyen Varlik | Pydantic dogrulama hatasi |
| `429` | Cok Fazla Istek | Hiz siniri asildi |
| `500` | Sunucu Ici Hata | Beklenmeyen sunucu hatasi |
| `502` | Hatali Agit Gecidi | Dis hizmet kullanilamiyor |
| `503` | Hizmet Kullanilamiyor | Sistem asiri yuklenmis |

---

## Hiz Siniri Yaniti

Hiz sinirlamasi uygulandiginda, API su yaniti dondurur:

```
HTTP 429 Too Many Requests
Retry-After: 60
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1708070460

{
  "detail": "Rate limit exceeded: 30 per 1 minute"
}
```

---

## Sayfalandirma

Liste donduren uc noktalar, sorgu parametreleri araciligiyla sayfalandirmayi destekler:

| Parametre | Tur | Varsayilan | Aciklama |
|-----------|-----|-----------|----------|
| `page` | int | 1 | Sayfa numarasi (1'den baslar) |
| `limit` | int | 20 | Sayfa basina oge sayisi (sinirli: 1-100) |
| `offset` | int | 0 | Alternatif: N oge atla |

Sinirli sayfalandirma kotuye kullanimi onler -- tum sayfalandirilmis uc noktalar limit parametresi icin `Query(ge=1, le=100)` kullanir.

---

## Yonlendirici Kaydi

Tum yonlendiriciler `backend/main.py` dosyasinda `/api/v1` oneki ile kaydedilir:

| Yonlendirici Modulu | Onek | Etiketler |
|---------------------|------|-----------|
| `chat` | `/api/v1` | Chat |
| `stream` | `/api/v1` | Chat |
| `search` | `/api/v1` | Search |
| `documents` | `/api/v1` | Documents |
| `uploads` | `/api/v1/uploads` | Uploads |
| `integrations` | `/api/v1` | Integrations |
| `settings` | `/api/v1` | Settings |
| `team` | `/api/v1` | Team |
| `billing` | `/api/v1/billing` | Billing |
| `usage` | `/api/v1` | Usage |
| `jobs` | `/api/v1` | Jobs |
| `notifications` | `/api/v1` | Notifications |
| `consent` | `/api/v1` | Consent |
| `compliance` | `/api/v1` | Compliance |
| `approvals` | `/api/v1` | Approvals |
| `admin` | `/api/v1/admin` | Admin |
| `dlq` | `/api/v1/dlq` | DLQ |
| ~~`health`~~ | ~~`/api/v1`~~ | ~~Health~~ *(kayitli degil — `/health` dogrudan `main.py` icerisinde tanimli)* |
| `webhooks` | `/api/v1` | Webhooks |
| `mcp` | `/api/v1` | MCP |
| `feedback` | `/api/v1` | Feedback |
