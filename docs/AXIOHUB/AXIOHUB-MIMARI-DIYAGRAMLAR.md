# AxioHub Mimari Diyagramlar

> **Versiyon:** 1.0 | **Tarih:** Şubat 2026 | **Durum:** Üretim
>
> Bu belge, AxioHub platformuna ait tüm Mermaid mimari diyagramlarını içerir.
> Her diyagram, sunumlar ve slayt desteleri için bağımsız olarak oluşturulabilir.

---

## İçindekiler

1. [Sistem Mimarisi (Üst Düzey)](#1-sistem-mimarisi-üst-düzey)
2. [İstek Yaşam Döngüsü](#2-i̇stek-yaşam-döngüsü)
3. [Kimlik Doğrulama Akışı](#3-kimlik-doğrulama-akışı)
4. [OAuth Bağlayıcı Akışı](#4-oauth-bağlayıcı-akışı)
5. [Dosya Yükleme ve Veri İşleme Hattı](#5-dosya-yükleme-ve-veri-i̇şleme-hattı)
6. [Celery Görev Zinciri ve Kuyruk Topolojisi](#6-celery-görev-zinciri-ve-kuyruk-topolojisi)
7. [RAG Sohbet Akışı](#7-rag-sohbet-akışı)
8. [Güvenlik Katmanları (Derinlemesine Savunma)](#8-güvenlik-katmanları-derinlemesine-savunma)
9. [Ghost Protocol Şifreleme Akışı](#9-ghost-protocol-şifreleme-akışı)
10. [Onay ve Uyumluluk Akışı](#10-onay-ve-uyumluluk-akışı)
11. [Takım ve RBAC Hiyerarşisi](#11-takım-ve-rbac-hiyerarşisi)
12. [Faturalandırma ve Abonelik Akışı](#12-faturalandırma-ve-abonelik-akışı)
13. [Önyüz Bileşen Mimarisi](#13-önyüz-bileşen-mimarisi)
14. [Docker Altyapısı](#14-docker-altyapısı)
15. [CI/CD İş Hattı Akışı](#15-cicd-i̇ş-hattı-akışı)

---

## 1. Sistem Mimarisi (Üst Düzey)

```mermaid
graph TB
    subgraph Client["İstemci Katmanı"]
        Browser["Tarayıcı<br/>(Next.js 16 Uygulaması)"]
        MCP["MCP İstemcisi<br/>(Harici AI Ajanı)"]
    end

    subgraph Edge["Uç / Ara Katman"]
        Proxy["proxy.ts<br/>(Kimlik Doğrulama Ara Katmanı)"]
        NextAPI["Next.js API Yönlendirmeleri<br/>(/api/py/* → Arka Uç)"]
    end

    subgraph Backend["Arka Uç (FastAPI)"]
        API["FastAPI Uygulaması<br/>(main.py)"]
        Auth["Kimlik Doğrulama ve Güvenlik<br/>(core/security.py)"]
        Routers["API Yönlendiriciler<br/>(api/v1/*.py)"]
        Services["Servis Katmanı<br/>(LLM, Gömme, Koruma Rayları)"]
    end

    subgraph Workers["Arka Plan İşçileri"]
        Celery["Celery İşçileri<br/>(worker/tasks.py)"]
        Beat["Celery Beat<br/>(Zamanlayıcı)"]
    end

    subgraph Connectors["Veri Bağlayıcıları"]
        GDrive["Google Drive"]
        Notion["Notion"]
        Dropbox["Dropbox"]
        GitHub["GitHub"]
        OneDrive["OneDrive"]
        SharePoint["SharePoint"]
        Box["Box"]
        SFTP["SFTP"]
        S3["Amazon S3"]
        Web["Web Tarayıcı"]
    end

    subgraph Storage["Veri Katmanı"]
        Supabase["Supabase PostgreSQL<br/>(+ pgvector)"]
        SupaStorage["Supabase Depolama<br/>(Dosya Kovaları)"]
        Redis["Redis<br/>(Önbellek + Kuyruk Aracısı)"]
    end

    subgraph External["Harici Servisler"]
        OpenAI["OpenAI API<br/>(GPT-4o, Gömme)"]
        Polar["Polar.sh<br/>(Faturalandırma)"]
        ClamAV["ClamAV<br/>(Zararlı Yazılım Taraması)"]
        Sentry["Sentry<br/>(Hata Takibi)"]
    end

    Browser --> Proxy
    MCP --> API
    Proxy --> NextAPI
    NextAPI --> API
    API --> Auth
    API --> Routers
    Routers --> Services
    Routers --> Celery
    Celery --> Connectors
    Services --> OpenAI
    Celery --> Supabase
    Celery --> SupaStorage
    API --> Supabase
    API --> Redis
    Celery --> Redis
    Beat --> Redis
    API --> ClamAV
    API --> Sentry
    Browser --> Sentry
    Routers --> Polar
```

---

## 2. İstek Yaşam Döngüsü

```mermaid
sequenceDiagram
    actor User as Kullanıcı
    participant Browser as Next.js Uygulaması
    participant Proxy as proxy.ts
    participant Rewrite as API Yönlendirme
    participant FastAPI as FastAPI Arka Uç
    participant Auth as Kimlik Doğrulama Ara Katmanı
    participant Router as API Yönlendirici
    participant DB as Supabase PostgreSQL
    participant Redis as Redis Önbellek

    User->>Browser: Eylem (tıklama, gezinme)
    Browser->>Proxy: HTTP İstek

    alt Korumalı Rota
        Proxy->>Proxy: Supabase getUser() ile oturum doğrulama
        alt Oturum Geçerli
            Proxy->>Browser: İsteğe izin ver
        else Oturum Geçersiz
            Proxy->>Browser: /login?redirectTo=... adresine yönlendir
        end
    end

    Browser->>Rewrite: /api/py/* isteği
    Rewrite->>FastAPI: Arka uca yönlendir :8000/api/v1/*

    FastAPI->>Auth: Authorization başlığından JWT çıkar
    Auth->>Auth: Supabase ile token doğrula
    Auth->>Auth: Hız sınırı kontrol et (slowapi + Redis)
    Auth->>Auth: Content-Length doğrula (maks. 100MB)

    FastAPI->>Router: İşleyiciye yönlendir
    Router->>DB: Veriyi sorgula/değiştir (RLS uygulanır)
    DB-->>Router: Yanıt verisi
    Router->>Redis: Uygunsa önbelleğe al
    Router-->>FastAPI: JSON yanıt

    FastAPI-->>Rewrite: HTTP Yanıt
    Rewrite-->>Browser: Yanıt
    Browser-->>User: Güncellenmiş Arayüz (React Query önbellek)
```

---

## 3. Kimlik Doğrulama Akışı

```mermaid
sequenceDiagram
    actor User as Kullanıcı
    participant App as Next.js Uygulaması
    participant Supabase as Supabase Auth
    participant Proxy as proxy.ts
    participant Backend as FastAPI
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,DB: E-posta/Parola ile Giriş
        User->>App: Kimlik bilgilerini gir
        App->>Supabase: signInWithPassword(email, password)
        Supabase->>Supabase: Kimlik bilgilerini doğrula
        Supabase-->>App: Oturum (access_token + refresh_token)
        App->>App: Oturumu çerezlerde sakla (httpOnly)
        App->>App: Token'ı bellekte önbelleğe al (5 dk)
    end

    rect rgb(255, 245, 230)
        Note over User,DB: OAuth Sağlayıcı ile Giriş (Google, GitHub, vb.)
        User->>App: "Google ile Giriş Yap" tıkla
        App->>Supabase: signInWithOAuth(provider: 'google')
        Supabase->>User: Google onay ekranına yönlendir
        User->>Supabase: Yetkilendir ve kodu döndür
        Supabase->>Supabase: Kodu token ile değiştir
        Supabase-->>App: /auth/callback adresine yönlendir
        App->>App: URL hash'inden oturumu çıkar
    end

    rect rgb(230, 255, 230)
        Note over User,DB: Her İstekte Oturum Doğrulama
        App->>Proxy: Herhangi bir korumalı sayfa isteği
        Proxy->>Supabase: getUser() (JWT doğrular)
        alt Token Süresi Dolmuş
            Proxy->>Supabase: Çerez ile token yenile
            Supabase-->>Proxy: Yeni access_token
            Proxy->>Proxy: Çerezi güncelle
        else Oturum Bulunamadı
            Proxy->>Proxy: Eski çerezleri temizle
            Proxy-->>App: /login adresine yönlendir
        end
        Proxy-->>App: İsteğe izin ver
    end

    rect rgb(255, 230, 230)
        Note over User,DB: API İstek Yetkilendirmesi
        App->>Backend: GET /api/v1/documents (Bearer token)
        Backend->>Backend: Başlıktan JWT çıkar
        Backend->>Supabase: Token doğrula (get_current_user)
        Backend->>DB: RLS ile sorgula (user_id filtresi)
        DB-->>Backend: Kapsamlı sonuçlar
        Backend-->>App: JSON yanıt
    end
```

---

## 4. OAuth Bağlayıcı Akışı

```mermaid
sequenceDiagram
    actor User as Kullanıcı
    participant App as Önyüz
    participant Backend as FastAPI
    participant Provider as OAuth Sağlayıcı<br/>(Google/Notion/GitHub/vb.)
    participant DB as PostgreSQL
    participant Encrypt as Fernet Şifreleme

    User->>App: "Google Drive Bağla" tıkla
    App->>App: OAuth durum token'ı oluştur (CSRF)
    App->>Provider: Yetkilendirme URL'sine yönlendir<br/>(kapsam: drive.readonly)

    Provider->>User: Onay ekranını göster
    User->>Provider: Erişimi onayla
    Provider->>App: /oauth/callback?code=xxx&state=yyy adresine yönlendir

    App->>App: Durum token'ını doğrula (CSRF kontrolü)
    App->>Backend: POST /integrations/google/exchange<br/>{code, redirect_uri}

    Backend->>Provider: Kodu token ile değiştir<br/>(POST /oauth/token)
    Provider-->>Backend: {access_token, refresh_token, expires_in}

    Backend->>Encrypt: Token'ları Fernet ile şifrele
    Encrypt-->>Backend: Şifrelenmiş token blobu

    Backend->>DB: INSERT into integrations<br/>(user_id, provider, encrypted_credentials)
    DB-->>Backend: Entegrasyon ID

    Backend-->>App: {status: "connected", integration_id}
    App-->>User: "Bağlandı" rozetini göster

    Note over Backend,Provider: Token Yenileme (Arka Plan)
    loop Her istek / Süre dolduğunda
        Backend->>DB: Şifrelenmiş kimlik bilgilerini oku
        Backend->>Encrypt: Token'ların şifresini çöz
        Encrypt-->>Backend: Düz metin token'lar
        alt Token Süresi Dolmuş
            Backend->>Provider: POST /oauth/token (refresh_token)
            Provider-->>Backend: Yeni access_token
            Backend->>Encrypt: Yeniden şifrele
            Backend->>DB: UPDATE encrypted_credentials
        end
    end
```

---

## 5. Dosya Yükleme ve Veri İşleme Hattı

```mermaid
flowchart TB
    subgraph Upload["1. Yükleme Aşaması"]
        A[Kullanıcı dosya seçer] --> B[SHA-256 hash hesaplanır<br/>istemci tarafında]
        B --> C{Tekrar kontrolü<br/>POST /check-duplicates}
        C -->|Tekrar bulundu| D[Mevcut belgeyi göster]
        C -->|Yeni dosya| E[Önceden imzalanmış URL iste<br/>POST /upload-url]
        E --> F[Doğrudan yükleme<br/>Supabase Storage'a]
        F --> G[Zararlı yazılım taraması<br/>ClamAV]
        G -->|Temiz| H[Dosya referansı kaydet<br/>POST /file/reference]
        G -->|Enfekte| I[Reddet + sil]
        G -->|ClamAV kapalı +<br/>FAIL_CLOSED=True| I
    end

    subgraph Ingest["2. Veri Alım Aşaması (Celery)"]
        H --> J[unified_ingest_task<br/>Kuyruk: ingestion<br/>Zaman aşımı: 15dk]
        J --> K[Kaynaktan getir<br/>Bağlayıcı aracılığıyla]
        K --> L[process_file_task<br/>Kuyruk: file_processing<br/>Zaman aşımı: 10dk]
    end

    subgraph Parse["3. Ayrıştırma Aşaması"]
        L --> M{Dosya türü?}
        M -->|PDF| N[PDF Ayrıştırıcı<br/>PyPDF2 + pdfplumber]
        M -->|DOCX| O[DOCX Ayrıştırıcı<br/>python-docx]
        M -->|HTML| P[HTML Ayrıştırıcı<br/>BeautifulSoup]
        M -->|Markdown| Q[Markdown Ayrıştırıcı]
        M -->|Kod| R[Kod Ayrıştırıcı<br/>dile duyarlı]
        M -->|CSV/Excel| S[Tablo Ayrıştırıcı<br/>pandas]
        M -->|E-posta| T[E-posta Ayrıştırıcı<br/>eml/msg]
    end

    subgraph Chunk["4. Parçalama Aşaması"]
        N & O & P & Q & R & S & T --> U[Anlamsal Parçalama<br/>~500 token/parça]
        U --> V[Meta veri çıkarma<br/>başlık, alt başlıklar, sayfa no]
    end

    subgraph Embed["5. Gömme Aşaması"]
        V --> W[generate_embeddings_task<br/>Kuyruk: embeddings<br/>Zaman aşımı: 10dk]
        W --> X[TPM Düzenleyici<br/>iş parçacığı güvenli kısıtlama]
        X --> Y[OpenAI text-embedding-3-small<br/>1536 boyut]
    end

    subgraph Index["6. İndeksleme Aşaması"]
        Y --> Z[index_chunks_task<br/>Kuyruk: indexing<br/>Zaman aşımı: 5dk]
        Z --> AA{Ghost Protocol<br/>etkin mi?}
        AA -->|Evet| AB[AES-256 Fernet şifreleme<br/>parça içeriği]
        AA -->|Hayır| AC[Düz metin olarak sakla]
        AB --> AD[INSERT belge +<br/>parçalar atomik olarak<br/>ingest_document_with_chunks RPC ile]
        AC --> AD
        AD --> AE[HNSW vektör indeksi<br/>otomatik güncellenir]
    end

    subgraph Finalize["7. Sonlandırma"]
        AE --> AF[finalize_job_task<br/>Zaman aşımı: 2dk]
        AF --> AG[İş durumunu güncelle<br/>Kullanıcıyı Realtime ile bilgilendir]
    end

    style Upload fill:#e3f2fd
    style Ingest fill:#fff3e0
    style Parse fill:#f3e5f5
    style Chunk fill:#e8f5e9
    style Embed fill:#fce4ec
    style Index fill:#fff8e1
    style Finalize fill:#e0f7fa
```

---

## 6. Celery Görev Zinciri ve Kuyruk Topolojisi

```mermaid
graph LR
    subgraph Queues["Redis Kuyrukları"]
        Q1["ingestion<br/>(unified_ingest_task)"]
        Q2["file_processing<br/>(process_file_task)"]
        Q3["embeddings<br/>(generate_embeddings_task)"]
        Q4["indexing<br/>(index_chunks_task)"]
        Q5["finalization<br/>(finalize_job_task)"]
        Q6["crawl<br/>(crawl_discovery_task,<br/>process_page_task,<br/>finalize_crawl_task)"]
        Q7["default<br/>(health_check_task,<br/>temizlik görevleri)"]
    end

    subgraph Tasks["Görev Zinciri (Dosya Alımı)"]
        T1["unified_ingest_task<br/>yumuşak: 900s / sert: 960s"]
        T2["process_file_task<br/>yumuşak: 600s / sert: 660s"]
        T3["generate_embeddings_task<br/>yumuşak: 600s / sert: 660s"]
        T4["index_chunks_task<br/>yumuşak: 300s / sert: 330s"]
        T5["finalize_job_task<br/>yumuşak: 120s / sert: 150s"]
    end

    subgraph CrawlTasks["Görev Zinciri (Web Tarama)"]
        C1["crawl_discovery_task<br/>yumuşak: 1800s / sert: 1860s"]
        C2["process_page_task<br/>yumuşak: 300s / sert: 330s"]
        C3["finalize_crawl_task<br/>yumuşak: 120s / sert: 150s"]
    end

    T1 -->|"dosya başına"| T2
    T2 -->|"parçalar"| T3
    T3 -->|"vektörler"| T4
    T4 -->|"tamamlandı"| T5

    C1 -->|"sayfa başına"| C2
    C2 -->|"tümü bitti"| C3

    Q1 -.-> T1
    Q2 -.-> T2
    Q3 -.-> T3
    Q4 -.-> T4
    Q5 -.-> T5
    Q6 -.-> C1
    Q6 -.-> C2
    Q6 -.-> C3

    subgraph Workers["İşçi Havuzu"]
        W1["İşçi 1<br/>(eşzamanlılık: 4)"]
        W2["İşçi 2<br/>(eşzamanlılık: 4)"]
        W3["İşçi N<br/>(otomatik ölçekleme)"]
    end

    Queues -.->|tüket| Workers
```

---

## 7. RAG Sohbet Akışı

```mermaid
sequenceDiagram
    actor User as Kullanıcı
    participant App as Önyüz
    participant API as FastAPI
    participant Guard as Koruma Rayları<br/>(Llama Guard)
    participant Search as Vektör Arama<br/>(pgvector)
    participant LLM as OpenAI GPT-4o
    participant Stream as SSE Akışı

    User->>App: Mesaj gönder
    App->>API: POST /chat {message, conversation_id, scope}

    rect rgb(255, 230, 230)
        Note over API,Guard: Girdi Güvenlik Kontrolü
        API->>Guard: Mesaj güvenliğini kontrol et
        Guard->>Guard: Llama Guard 3 sınıflandırması
        alt Güvensiz Girdi
            Guard-->>API: ENGELLENDİ (kategori)
            API-->>App: Hata: "Mesaj işaretlendi"
        end
        Guard-->>API: GÜVENLİ
    end

    rect rgb(230, 245, 255)
        Note over API,Search: Bağlam Getirme
        API->>API: Sorgu gömme vektörü oluştur<br/>(text-embedding-3-small)
        API->>Search: hybrid_search(embedding, query_text)
        Search->>Search: Vektör benzerliği (kosinüs)<br/>+ Tam metin arama (ts_rank)
        Search->>Search: Kapsama göre filtrele<br/>(organization_id, scope_ids)
        Search->>Search: Kaldırılmış belgeleri hariç tut<br/>(compliance_tombstones kontrolü)
        Search-->>API: En alakalı K parça<br/>(skorlarla birlikte)
    end

    rect rgb(230, 255, 230)
        Note over API,LLM: Yanıt Üretimi
        API->>API: Sistem istemini oluştur<br/>(kapsam bağlamı + talimatlar)
        API->>API: Baskınlık Koruması kontrolü<br/>(tek kaynak yanlılığını önle)
        API->>LLM: Sohbet tamamlama isteği<br/>(model: gpt-4o, stream: true)

        loop Akış Yanıtı
            LLM-->>Stream: Token parçası
            Stream-->>App: SSE veri olayı
            App-->>User: Token'ı oluştur
        end

        Note over Stream: Her 15 saniyede kalp atışı<br/>(bağlantıyı canlı tutar)
    end

    rect rgb(255, 245, 230)
        Note over API,LLM: Son İşleme
        API->>API: Kaynak atıflarını çıkar
        API->>API: Mesajı konuşmaya kaydet
        API->>API: Token kullanım sayaçlarını güncelle
        API-->>App: SSE [DONE] olayı
    end

    App->>App: Kaynaklar panelini göster
    App-->>User: Atıflarla birlikte tam yanıt
```

---

## 8. Güvenlik Katmanları (Derinlemesine Savunma)

```mermaid
graph TB
    subgraph L1["Katman 1: Ağ ve İletim"]
        HTTPS["Yalnızca HTTPS<br/>(HSTS ön yükleme)"]
        CORS["CORS Beyaz Listesi<br/>(belirli kaynaklar)"]
        CSP["İçerik Güvenliği Politikası<br/>(script-src, connect-src)"]
        XFrame["X-Frame-Options: DENY"]
        NoSniff["X-Content-Type-Options: nosniff"]
    end

    subgraph L2["Katman 2: Kimlik Doğrulama"]
        JWT["JWT Doğrulama<br/>(Supabase tarafından verilmiş)"]
        Session["Oturum Yönetimi<br/>(proxy.ts doğrulaması)"]
        TokenCache["Token Önbellekleme<br/>(5 dk bellek içi)"]
        OAuthState["OAuth Durum Token'ları<br/>(CSRF koruması)"]
    end

    subgraph L3["Katman 3: Yetkilendirme"]
        RLS["Satır Düzeyinde Güvenlik<br/>(PostgreSQL politikaları)"]
        RBAC["Rol Tabanlı Erişim<br/>(yönetici/editör/izleyici)"]
        PlanGate["Plan Bazlı Kapılar<br/>(require_plan bağımlılığı)"]
        ScopeGuard["Kapsam Koruması<br/>(veri kaynağı izolasyonu)"]
    end

    subgraph L4["Katman 4: Girdi Doğrulama"]
        RateLimit["Hız Sınırlama<br/>(slowapi uç nokta bazlı)"]
        BodySize["İstek Gövdesi Boyutu<br/>(maks. 100MB)"]
        Pydantic["Pydantic Doğrulama<br/>(max_length, Field())"]
        Sanitize["Girdi Temizleme<br/>(XSS önleme)"]
        OpenRedirect["Açık Yönlendirme Önleme<br/>(yol doğrulaması)"]
    end

    subgraph L5["Katman 5: Veri Koruma"]
        Fernet["Fernet AES-256<br/>(Ghost Protocol)"]
        TokenEncrypt["OAuth Token Şifreleme<br/>(durağan halde)"]
        Wipe["Güvenli Silme<br/>(DoD 5220.22-M 3 geçişli)"]
        Tombstone["Uyumluluk Mezar Taşları<br/>(anında erişim iptali)"]
    end

    subgraph L6["Katman 6: Çalışma Zamanı Koruması"]
        SSRF["SSRF Koruması<br/>(getaddrinfo + IP doğrulama)"]
        Malware["Zararlı Yazılım Taraması<br/>(ClamAV, hata durumunda kapat)"]
        Guardrails["LLM Koruma Rayları<br/>(Llama Guard 3)"]
        ConsoleGate["Konsol Kapılaması<br/>(üretimde sızıntı yok)"]
    end

    subgraph L7["Katman 7: İzleme"]
        SentryFE["Sentry (Önyüz)<br/>(istemci + uç)"]
        SentryBE["Sentry (Arka Uç)<br/>(sunucu)"]
        AuditLog["Denetim Günlüğü<br/>(tüm kritik eylemler)"]
        Health["Sağlık Uç Noktası<br/>(/health)"]
    end

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7

    style L1 fill:#e3f2fd
    style L2 fill:#fff3e0
    style L3 fill:#f3e5f5
    style L4 fill:#e8f5e9
    style L5 fill:#fce4ec
    style L6 fill:#fff8e1
    style L7 fill:#e0f7fa
```

---

## 9. Ghost Protocol Şifreleme Akışı

```mermaid
sequenceDiagram
    participant Writer as Veri Alım İşçisi
    participant GhostP as Ghost Protocol<br/>(core/security.py)
    participant Key as CHUNK_ENCRYPTION_KEY<br/>(Fernet AES-256)
    participant DB as PostgreSQL<br/>(document_chunks)
    participant Reader as Arama / Sohbet
    participant Wipe as Güvenli Silme

    rect rgb(230, 245, 255)
        Note over Writer,DB: Yazma Anında Şifreleme
        Writer->>GhostP: encrypt_content(düz_metin_parça)
        GhostP->>Key: Ortam değişkeninden Fernet anahtarını yükle
        GhostP->>GhostP: Fernet.encrypt(plaintext.encode())
        Note over GhostP: Çıktı: base64 kodlanmış<br/>zaman damgalı şifreli metin
        GhostP-->>Writer: şifrelenmiş_blob
        Writer->>DB: INSERT parça (content=şifrelenmiş_blob,<br/>embedding=vektör)
    end

    rect rgb(230, 255, 230)
        Note over Reader,DB: Okuma Anında Şifre Çözme
        Reader->>DB: Vektör arama → en iyi K parça
        DB-->>Reader: Şifrelenmiş parça içeriği
        Reader->>GhostP: decrypt_content(şifrelenmiş_blob)
        GhostP->>Key: Fernet anahtarını yükle
        GhostP->>GhostP: Fernet.decrypt(blob)
        GhostP-->>Reader: düz_metin_parça
        Reader->>Reader: LLM bağlamına dahil et
    end

    rect rgb(255, 230, 230)
        Note over Wipe,DB: Güvenli Silme (DoD 5220.22-M)
        Wipe->>DB: SELECT parça içeriği
        Wipe->>Wipe: Geçiş 1: 0x00 ile üzerine yaz
        Wipe->>Wipe: Geçiş 2: 0xFF ile üzerine yaz
        Wipe->>Wipe: Geçiş 3: Rastgele ile üzerine yaz
        Wipe->>DB: DELETE parça satırı
        Wipe->>DB: INSERT compliance_tombstone<br/>(anında erişim iptali)
        Note over Wipe,DB: Mezar taşı yayını<br/>Supabase Realtime aracılığıyla
    end
```

---

## 10. Onay ve Uyumluluk Akışı

```mermaid
flowchart TB
    subgraph Request["Uyumluluk Talebi"]
        A[Kullanıcı/Yönetici<br/>veri eylemi talep eder] --> B{Eylem türü?}
        B -->|GDPR Madde 17<br/>Silinme Hakkı| C[Silme Talebi]
        B -->|CCPA ADMT<br/>Bilme Hakkı| D[Veri Dışa Aktarma Talebi]
        B -->|Kapsam Onay<br/>Değişikliği| E[Onay Güncellemesi]
    end

    subgraph Consent["Onay Yönetimi"]
        E --> F{Kapsam düzeyi?}
        F -->|Organizasyon| G[Organizasyon onayını güncelle<br/>PATCH /consent/organization]
        F -->|Veri Kaynağı| H[Kapsam onayını güncelle<br/>PATCH /consent/scope]
        F -->|Belge| I[Belge onayını güncelle<br/>PATCH /consent/document]
        G & H & I --> J[Denetim günlüğü kaydı<br/>oluşturuldu]
        J --> K[Gerçek zamanlı bildirim<br/>tüm sekmelere]
    end

    subgraph Deletion["Silme Hattı"]
        C --> L[compliance_tombstone oluştur<br/>durum: aktif]
        L --> M[Anında erişim iptali<br/>Supabase Realtime aracılığıyla]
        M --> N[Ghost Protocol<br/>güvenli silme başlatıldı]
        N --> O[3 geçişli üzerine yazma<br/>DoD 5220.22-M]
        O --> P[DELETE from document_chunks]
        P --> Q[DELETE from documents]
        Q --> R[Mezar taşını güncelle<br/>durum: tamamlandı]
    end

    subgraph Export["Veri Dışa Aktarma"]
        D --> S[Tüm kullanıcı verisini topla<br/>belgeler, parçalar, meta veri]
        S --> T[JSON/ZIP olarak paketle]
        T --> U[İndirme URL'si döndür]
    end

    subgraph Audit["Denetim İzi"]
        J --> V[consent_audit_log tablosu]
        R --> V
        V --> W[GET /consent/audit<br/>sayfalanmış geçmiş]
        V --> X[GET /consent/report<br/>uyumluluk özeti]
    end

    style Request fill:#fff3e0
    style Consent fill:#e8f5e9
    style Deletion fill:#fce4ec
    style Export fill:#e3f2fd
    style Audit fill:#f3e5f5
```

---

## 11. Takım ve RBAC Hiyerarşisi

```mermaid
graph TB
    subgraph Organization["Organizasyon (Takım)"]
        Team["Takım Varlığı<br/>(teams tablosu)"]

        subgraph Roles["Rol Hiyerarşisi"]
            Admin["Yönetici<br/>Tam kontrol"]
            Editor["Editör<br/>Okuma + Yazma + Veri Alımı"]
            Viewer["İzleyici<br/>Yalnızca okuma"]
        end

        subgraph Members["Takım Üyeleri"]
            Owner["Sahip<br/>(takımı oluşturan)"]
            M1["Üye 1<br/>rol: editör"]
            M2["Üye 2<br/>rol: izleyici"]
            M3["Bekleyen Davet<br/>durum: davet edildi"]
        end
    end

    subgraph Permissions["Yetki Matrisi"]
        P1["Belgeleri görüntüle"]
        P2["Dosya yükle / veri al"]
        P3["Belgeleri sil"]
        P4["Bağlayıcıları yönet"]
        P5["Takım üyelerini yönet"]
        P6["Faturalandırma ve abonelik"]
        P7["Denetim günlükleri"]
        P8["Onay yönetimi"]
    end

    subgraph PlanGates["Plan Bazlı Özellik Kapıları"]
        Free["Ücretsiz Plan<br/>1 kullanıcı, temel özellikler"]
        Starter["Başlangıç Planı<br/>3 kullanıcıya kadar"]
        Pro["Pro Plan<br/>10 kullanıcıya kadar"]
        Enterprise["Kurumsal Plan<br/>Sınırsız kullanıcı"]
    end

    Admin --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8
    Editor --> P1 & P2 & P3 & P4
    Viewer --> P1

    Team --> Owner
    Team --> M1 & M2 & M3

    subgraph InviteFlow["Davet Akışı"]
        I1["Yönetici davet gönderir<br/>POST /team/invite"]
        I2["Kullanıcıya e-posta gönderilir"]
        I3["Kullanıcı bağlantıya tıklar<br/>/invite/{token}"]
        I4["POST /team/accept"]
        I5["Üye rol ile eklenir"]
        I6["CSV ile toplu davet<br/>POST /team/bulk-invite"]
    end

    I1 --> I2 --> I3 --> I4 --> I5
    I6 --> I2

    style Organization fill:#e3f2fd
    style Permissions fill:#e8f5e9
    style PlanGates fill:#fff3e0
    style InviteFlow fill:#f3e5f5
```

---

## 12. Faturalandırma ve Abonelik Akışı

```mermaid
sequenceDiagram
    actor User as Kullanıcı
    participant App as Önyüz
    participant API as FastAPI
    participant Polar as Polar.sh<br/>(Ödeme Sağlayıcı)
    participant Webhook as Webhook İşleyici
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,DB: Plan Seçimi ve Ödeme
        User->>App: "Pro'ya Yükselt" tıkla
        App->>API: POST /billing/checkout<br/>{plan_id: "pro_monthly"}
        API->>Polar: Ödeme oturumu oluştur
        Polar-->>API: {checkout_url}
        API-->>App: Yönlendirme URL'si
        App->>User: Polar ödeme sayfasına yönlendir
        User->>Polar: Ödeme bilgilerini gir
        Polar->>Polar: Ödemeyi işle
    end

    rect rgb(230, 255, 230)
        Note over Polar,DB: Webhook İşleme
        Polar->>Webhook: POST /webhooks/polar<br/>(subscription.created)
        Webhook->>Webhook: Webhook imzasını doğrula
        Webhook->>DB: UPDATE organizations SET<br/>plan = 'pro',<br/>subscription_id = '...'
        Webhook->>DB: UPDATE kota limitleri<br/>(depolama, günlük_işler, vb.)
        Note over Webhook: Webhook başarısız olursa → DLQ<br/>(Ölü Mektup Kuyruğu)
    end

    rect rgb(255, 245, 230)
        Note over User,DB: Kota Kontrolü
        User->>App: Dosya yükle
        App->>API: POST /upload-url
        API->>DB: Mevcut kullanımı plan limitleriyle kontrol et
        alt Kota Dahilinde
            API-->>App: Önceden imzalanmış URL
        else Kota Aşıldı
            API-->>App: 402 "Depolama limiti aşıldı"
            App-->>User: Yükseltme istemini göster
        end
    end

    rect rgb(255, 230, 230)
        Note over User,DB: Abonelik Yönetimi
        User->>App: "Aboneliği Yönet" tıkla
        App->>API: POST /billing/portal
        API->>Polar: Portal oturumu oluştur
        Polar-->>API: {portal_url}
        API-->>App: Yönlendirme URL'si
        App->>User: Polar portalına yönlendir
        Note over User,Polar: Plan değiştir, iptal et,<br/>ödeme yöntemini güncelle
    end
```

---

## 13. Önyüz Bileşen Mimarisi

```mermaid
graph TB
    subgraph RootLayout["Kök Yerleşim (app/layout.tsx)"]
        QP["QueryProvider<br/>(React Query + DevTools)"]
        SP["SessionProvider<br/>(Supabase Auth)"]
        TP["ThemeProvider<br/>(Açık/Koyu/Sistem)"]
        TT["TooltipProvider + Toaster"]
    end

    subgraph DashboardLayout["Gösterge Paneli Yerleşimi"]
        PP["ProfileProvider<br/>(tek seferlik getirme)"]
        UP["UsageProvider<br/>(plan + kotalar)"]
        QSP["QuotaStatusProvider<br/>(localStorage + Realtime)"]
        DIP["DataInvalidationProvider<br/>(Ghost Protocol mezar taşları)"]
        CHP["ChatHistoryProvider<br/>(konuşmalar)"]
        IMP["IngestModalProvider<br/>(genel modal)"]
        IPP["IngestionProgressProvider<br/>(ilerleme takibi)"]
        PW["PaywallGuard<br/>(abonelik zorunluluğu)"]
    end

    subgraph RouteGroups["Rota Grupları (5)"]
        RG1["(auth)<br/>giriş, kayıt,<br/>şifremi-unuttum"]
        RG2["(marketing)<br/>açılış, yasal"]
        RG3["auth<br/>geri çağırma, sıfırlama,<br/>hata"]
        RG4["dashboard<br/>sohbet, belgeler,<br/>ayarlar/*"]
        RG5["oauth<br/>geri çağırma"]
    end

    subgraph StateManagement["Durum Yönetimi"]
        RQ["React Query<br/>Sunucu durumu,<br/>önbellekleme, tekrar önleme"]
        CTX["Context Sağlayıcılar<br/>Tekil durum<br/>(Profil, Kullanım)"]
        LS["localStorage<br/>Kota durumu,<br/>tema tercihi"]
        BC["BroadcastChannel<br/>Sekmeler arası senkronizasyon<br/>(7 sorgu ön eki)"]
    end

    subgraph ErrorBoundaries["Hata Sınırları (18+)"]
        GE["global-error.tsx<br/>(uygulama geneli)"]
        DE["dashboard/error.tsx"]
        SE["settings/*/error.tsx<br/>(12 dosya)"]
        CE["chat/[chatId]/error.tsx"]
        HE["help/[slug]/error.tsx"]
        LE["legal/[slug]/error.tsx"]
        IE["invite/[token]/error.tsx"]
    end

    QP --> SP --> TP --> TT
    TT --> DashboardLayout
    PP --> UP --> QSP --> DIP --> CHP --> IMP --> IPP --> PW
    PW --> RouteGroups

    RQ -.-> QP
    CTX -.-> DashboardLayout
    LS -.-> QSP
    BC -.-> QP

    style RootLayout fill:#e3f2fd
    style DashboardLayout fill:#fff3e0
    style RouteGroups fill:#e8f5e9
    style StateManagement fill:#f3e5f5
    style ErrorBoundaries fill:#fce4ec
```

---

## 14. Docker Altyapısı

```mermaid
graph TB
    subgraph DockerCompose["Docker Compose Servisleri"]
        subgraph Core["Temel Servisler"]
            BE["backend<br/>FastAPI<br/>Port: 8000<br/>Bellek: 4G / CPU: 4"]
            Redis["redis<br/>Redis 7 Alpine<br/>Port: 6379<br/>Bellek: 1G / CPU: 1"]
        end

        subgraph WorkerServices["İşçi Servisleri"]
            W1["celery-worker<br/>Celery İşçi<br/>(eşzamanlılık: otomatik)<br/>Bellek: 4G / CPU: 4"]
            Beat["celery-beat<br/>Celery Beat<br/>(periyodik zamanlayıcı)"]
            Flower["flower<br/>Celery Flower<br/>Port: 5555<br/>Bellek: 512M / CPU: 0.5"]
        end
    end

    subgraph ProductionOverrides["Üretim Geçersiz Kılmaları (docker-compose.prod.yml)"]
        NoExpose["Açık port yok<br/>(yalnızca backend:8000)"]
        NetIsolation["Ağ izolasyonu<br/>(dahili ağ)"]
        RedisPersist["Redis AOF kalıcılığı<br/>(appendonly yes)"]
        FlowerAuth["Flower kimlik doğrulaması<br/>(basic_auth gerekli)"]
        LogRotation["JSON günlük rotasyonu<br/>(maks. 10MB x 3 dosya)"]
    end

    subgraph HealthChecks["Sağlık Kontrolleri"]
        HC1["backend: /health<br/>aralık: 30s, yeniden deneme: 3"]
        HC2["redis: redis-cli ping<br/>aralık: 10s, yeniden deneme: 3"]
        HC3["flower: /api/workers<br/>aralık: 30s, yeniden deneme: 3"]
    end

    subgraph External["Harici Servisler"]
        Supabase["Supabase Cloud<br/>(PostgreSQL + Auth<br/>+ Depolama + Realtime)"]
        OpenAI["OpenAI API"]
        PolarSh["Polar.sh"]
        SentryIO["Sentry.io"]
    end

    BE --> Redis
    W1 --> Redis
    Beat --> Redis
    Flower --> Redis

    BE --> Supabase
    W1 --> Supabase
    BE --> OpenAI
    W1 --> OpenAI
    BE --> PolarSh
    BE --> SentryIO

    HC1 -.-> BE
    HC2 -.-> Redis
    HC3 -.-> Flower

    style Core fill:#e3f2fd
    style WorkerServices fill:#fff3e0
    style ProductionOverrides fill:#fce4ec
    style HealthChecks fill:#e8f5e9
    style External fill:#f3e5f5
```

---

## 15. CI/CD İş Hattı Akışı

```mermaid
flowchart LR
    subgraph Trigger["Tetikleyici"]
        Push["main'e Push"]
        PR["Pull Request"]
    end

    subgraph Lint["İş 1: Lint"]
        L1["ruff check backend/"]
        L2["ruff format --check"]
    end

    subgraph BackendTest["İş 2: Arka Uç Testleri"]
        BT1["pip install -r requirements.txt"]
        BT2["pytest -m unit<br/>--tb=short"]
    end

    subgraph FrontendLint["İş 3: Önyüz Lint"]
        FL1["npm ci"]
        FL2["npm run lint<br/>(ESLint + TypeScript)"]
    end

    subgraph FrontendTest["İş 4: Önyüz Testleri"]
        FT1["npm ci"]
        FT2["npx vitest run<br/>(2798 test)"]
    end

    subgraph FrontendBuild["İş 5: Önyüz Derleme"]
        FB1["npm ci"]
        FB2["CI=true npm run build<br/>(ortam doğrulamayı atla)"]
    end

    subgraph Security["İş 6: Güvenlik Denetimi"]
        S1["pip-audit<br/>(Python bağımlılıkları)"]
        S2["npm audit<br/>(Node bağımlılıkları)"]
    end

    Push & PR --> Lint & BackendTest & FrontendLint & FrontendTest & FrontendBuild & Security

    Lint -->|Geçti| Done["Tüm Kontroller Başarılı"]
    BackendTest -->|Geçti| Done
    FrontendLint -->|Geçti| Done
    FrontendTest -->|Geçti| Done
    FrontendBuild -->|Geçti| Done
    Security -->|Geçti| Done

    style Trigger fill:#e3f2fd
    style Lint fill:#fff3e0
    style BackendTest fill:#e8f5e9
    style FrontendLint fill:#f3e5f5
    style FrontendTest fill:#fce4ec
    style FrontendBuild fill:#fff8e1
    style Security fill:#e0f7fa
```

---

## Oluşturma Notları

- Tüm diyagramlar **Mermaid** söz dizimini kullanır ve aşağıdaki ortamlarda oluşturulabilir:
  - GitHub Markdown (yerel destek)
  - VS Code Mermaid uzantısı ile
  - Mermaid Canlı Düzenleyici: https://mermaid.live
  - Notion, Confluence ve diğer modern belgeleme platformları
- Slayt desteleri için: Mermaid Canlı Düzenleyici'den SVG/PNG olarak dışa aktarın
- Önerilen: Sunumlar için koyu tema kullanın (daha iyi kontrast)
