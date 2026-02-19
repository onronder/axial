# AxioHub Architecture Diagrams

> **Version:** 1.0 | **Date:** February 2026 | **Status:** Production
>
> This document contains all Mermaid architecture diagrams for the AxioHub platform.
> Each diagram can be rendered independently for presentations and slide decks.

---

## Table of Contents

1. [System Architecture (High-Level)](#1-system-architecture-high-level)
2. [Request Lifecycle](#2-request-lifecycle)
3. [Authentication Flow](#3-authentication-flow)
4. [OAuth Connector Flow](#4-oauth-connector-flow)
5. [File Upload & Ingestion Pipeline](#5-file-upload--ingestion-pipeline)
6. [Celery Task Chain & Queue Topology](#6-celery-task-chain--queue-topology)
7. [RAG Chat Flow](#7-rag-chat-flow)
8. [Security Layers (Defense in Depth)](#8-security-layers-defense-in-depth)
9. [Ghost Protocol Encryption Flow](#9-ghost-protocol-encryption-flow)
10. [Consent & Compliance Flow](#10-consent--compliance-flow)
11. [Team & RBAC Hierarchy](#11-team--rbac-hierarchy)
12. [Billing & Subscription Flow](#12-billing--subscription-flow)
13. [Frontend Component Architecture](#13-frontend-component-architecture)
14. [Docker Infrastructure](#14-docker-infrastructure)
15. [CI/CD Pipeline Flow](#15-cicd-pipeline-flow)

---

## 1. System Architecture (High-Level)

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser<br/>(Next.js 16 App)"]
        MCP["MCP Client<br/>(External AI Agent)"]
    end

    subgraph Edge["Edge / Middleware"]
        Proxy["proxy.ts<br/>(Auth Middleware)"]
        NextAPI["Next.js API Rewrites<br/>(/api/py/* → Backend)"]
    end

    subgraph Backend["Backend (FastAPI)"]
        API["FastAPI Application<br/>(main.py)"]
        Auth["Auth & Security<br/>(core/security.py)"]
        Routers["API Routers<br/>(api/v1/*.py)"]
        Services["Services Layer<br/>(LLM, Embeddings, Guardrails)"]
    end

    subgraph Workers["Background Workers"]
        Celery["Celery Workers<br/>(worker/tasks.py)"]
        Beat["Celery Beat<br/>(Scheduler)"]
    end

    subgraph Connectors["Data Connectors"]
        GDrive["Google Drive"]
        Notion["Notion"]
        Dropbox["Dropbox"]
        GitHub["GitHub"]
        OneDrive["OneDrive"]
        SharePoint["SharePoint"]
        Box["Box"]
        SFTP["SFTP"]
        S3["Amazon S3"]
        Web["Web Crawler"]
    end

    subgraph Storage["Data Layer"]
        Supabase["Supabase PostgreSQL<br/>(+ pgvector)"]
        SupaStorage["Supabase Storage<br/>(File Buckets)"]
        Redis["Redis<br/>(Cache + Queue Broker)"]
    end

    subgraph External["External Services"]
        OpenAI["OpenAI API<br/>(GPT-4o, Embeddings)"]
        Polar["Polar.sh<br/>(Billing)"]
        ClamAV["ClamAV<br/>(Malware Scan)"]
        Sentry["Sentry<br/>(Error Tracking)"]
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

## 2. Request Lifecycle

```mermaid
sequenceDiagram
    actor User
    participant Browser as Next.js App
    participant Proxy as proxy.ts
    participant Rewrite as API Rewrite
    participant FastAPI as FastAPI Backend
    participant Auth as Auth Middleware
    participant Router as API Router
    participant DB as Supabase PostgreSQL
    participant Redis as Redis Cache

    User->>Browser: Action (click, navigate)
    Browser->>Proxy: HTTP Request

    alt Protected Route
        Proxy->>Proxy: Validate session via Supabase getUser()
        alt Session Valid
            Proxy->>Browser: Allow request
        else Session Invalid
            Proxy->>Browser: Redirect to /login?redirectTo=...
        end
    end

    Browser->>Rewrite: /api/py/* request
    Rewrite->>FastAPI: Forward to backend :8000/api/v1/*

    FastAPI->>Auth: Extract JWT from Authorization header
    Auth->>Auth: Verify token with Supabase
    Auth->>Auth: Check rate limit (slowapi + Redis)
    Auth->>Auth: Validate Content-Length (max 100MB)

    FastAPI->>Router: Route to handler
    Router->>DB: Query/Mutate data (RLS enforced)
    DB-->>Router: Response data
    Router->>Redis: Cache if applicable
    Router-->>FastAPI: JSON response

    FastAPI-->>Rewrite: HTTP Response
    Rewrite-->>Browser: Response
    Browser-->>User: Updated UI (React Query cache)
```

---

## 3. Authentication Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Next.js App
    participant Supabase as Supabase Auth
    participant Proxy as proxy.ts
    participant Backend as FastAPI
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,DB: Email/Password Login
        User->>App: Enter credentials
        App->>Supabase: signInWithPassword(email, password)
        Supabase->>Supabase: Validate credentials
        Supabase-->>App: Session (access_token + refresh_token)
        App->>App: Store session in cookies (httpOnly)
        App->>App: Cache token in memory (5 min)
    end

    rect rgb(255, 245, 230)
        Note over User,DB: OAuth Provider Login (Google, GitHub, etc.)
        User->>App: Click "Sign in with Google"
        App->>Supabase: signInWithOAuth(provider: 'google')
        Supabase->>User: Redirect to Google consent screen
        User->>Supabase: Authorize & return code
        Supabase->>Supabase: Exchange code for tokens
        Supabase-->>App: Redirect to /auth/callback
        App->>App: Extract session from URL hash
    end

    rect rgb(230, 255, 230)
        Note over User,DB: Session Validation on Every Request
        App->>Proxy: Any protected page request
        Proxy->>Supabase: getUser() (validates JWT)
        alt Token Expired
            Proxy->>Supabase: Refresh token via cookie
            Supabase-->>Proxy: New access_token
            Proxy->>Proxy: Update cookie
        else Session Not Found
            Proxy->>Proxy: Clear stale cookies
            Proxy-->>App: Redirect to /login
        end
        Proxy-->>App: Allow request
    end

    rect rgb(255, 230, 230)
        Note over User,DB: API Request Authorization
        App->>Backend: GET /api/v1/documents (Bearer token)
        Backend->>Backend: Extract JWT from header
        Backend->>Supabase: Verify token (get_current_user)
        Backend->>DB: Query with RLS (user_id filter)
        DB-->>Backend: Scoped results
        Backend-->>App: JSON response
    end
```

---

## 4. OAuth Connector Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Frontend
    participant Backend as FastAPI
    participant Provider as OAuth Provider<br/>(Google/Notion/GitHub/etc.)
    participant DB as PostgreSQL
    participant Encrypt as Fernet Encryption

    User->>App: Click "Connect Google Drive"
    App->>App: Generate OAuth state token (CSRF)
    App->>Provider: Redirect to authorization URL<br/>(scope: drive.readonly)

    Provider->>User: Show consent screen
    User->>Provider: Approve access
    Provider->>App: Redirect to /oauth/callback?code=xxx&state=yyy

    App->>App: Validate state token (CSRF check)
    App->>Backend: POST /integrations/google/exchange<br/>{code, redirect_uri}

    Backend->>Provider: Exchange code for tokens<br/>(POST /oauth/token)
    Provider-->>Backend: {access_token, refresh_token, expires_in}

    Backend->>Encrypt: Encrypt tokens with Fernet
    Encrypt-->>Backend: Encrypted token blob

    Backend->>DB: INSERT into integrations<br/>(user_id, provider, encrypted_credentials)
    DB-->>Backend: Integration ID

    Backend-->>App: {status: "connected", integration_id}
    App-->>User: Show "Connected" badge

    Note over Backend,Provider: Token Refresh (Background)
    loop Every request / On expiry
        Backend->>DB: Read encrypted credentials
        Backend->>Encrypt: Decrypt tokens
        Encrypt-->>Backend: Plaintext tokens
        alt Token Expired
            Backend->>Provider: POST /oauth/token (refresh_token)
            Provider-->>Backend: New access_token
            Backend->>Encrypt: Re-encrypt
            Backend->>DB: UPDATE encrypted_credentials
        end
    end
```

---

## 5. File Upload & Ingestion Pipeline

```mermaid
flowchart TB
    subgraph Upload["1. Upload Phase"]
        A[User selects file] --> B[SHA-256 hash computed<br/>client-side]
        B --> C{Duplicate check<br/>POST /check-duplicates}
        C -->|Duplicate found| D[Show existing document]
        C -->|New file| E[Request presigned URL<br/>POST /upload-url]
        E --> F[Direct upload to<br/>Supabase Storage]
        F --> G[Malware scan<br/>ClamAV]
        G -->|Clean| H[Register file reference<br/>POST /file/reference]
        G -->|Infected| I[Reject + delete]
        G -->|ClamAV down +<br/>FAIL_CLOSED=True| I
    end

    subgraph Ingest["2. Ingestion Phase (Celery)"]
        H --> J[unified_ingest_task<br/>Queue: ingestion<br/>Timeout: 15min]
        J --> K[Fetch from source<br/>via Connector]
        K --> L[process_file_task<br/>Queue: file_processing<br/>Timeout: 10min]
    end

    subgraph Parse["3. Parse Phase"]
        L --> M{File type?}
        M -->|PDF| N[PDF Parser<br/>PyPDF2 + pdfplumber]
        M -->|DOCX| O[DOCX Parser<br/>python-docx]
        M -->|HTML| P[HTML Parser<br/>BeautifulSoup]
        M -->|Markdown| Q[Markdown Parser]
        M -->|Code| R[Code Parser<br/>language-aware]
        M -->|CSV/Excel| S[Tabular Parser<br/>pandas]
        M -->|Email| T[Email Parser<br/>eml/msg]
    end

    subgraph Chunk["4. Chunk Phase"]
        N & O & P & Q & R & S & T --> U[Semantic Chunking<br/>~500 tokens per chunk]
        U --> V[Metadata extraction<br/>title, headings, page#]
    end

    subgraph Embed["5. Embed Phase"]
        V --> W[generate_embeddings_task<br/>Queue: embeddings<br/>Timeout: 10min]
        W --> X[TPM Regulator<br/>thread-safe throttle]
        X --> Y[OpenAI text-embedding-3-small<br/>1536 dimensions]
    end

    subgraph Index["6. Index Phase"]
        Y --> Z[index_chunks_task<br/>Queue: indexing<br/>Timeout: 5min]
        Z --> AA{Ghost Protocol<br/>enabled?}
        AA -->|Yes| AB[AES-256 Fernet encrypt<br/>chunk content]
        AA -->|No| AC[Store plaintext]
        AB --> AD[INSERT document +<br/>chunks atomically<br/>via ingest_document_with_chunks RPC]
        AC --> AD
        AD --> AE[HNSW vector index<br/>auto-updated]
    end

    subgraph Finalize["7. Finalize"]
        AE --> AF[finalize_job_task<br/>Timeout: 2min]
        AF --> AG[Update job status<br/>Notify user via Realtime]
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

## 6. Celery Task Chain & Queue Topology

```mermaid
graph LR
    subgraph Queues["Redis Queues"]
        Q1["ingestion<br/>(unified_ingest_task)"]
        Q2["file_processing<br/>(process_file_task)"]
        Q3["embeddings<br/>(generate_embeddings_task)"]
        Q4["indexing<br/>(index_chunks_task)"]
        Q5["finalization<br/>(finalize_job_task)"]
        Q6["crawl<br/>(crawl_discovery_task,<br/>process_page_task,<br/>finalize_crawl_task)"]
        Q7["default<br/>(health_check_task,<br/>cleanup tasks)"]
    end

    subgraph Tasks["Task Chain (File Ingestion)"]
        T1["unified_ingest_task<br/>soft: 900s / hard: 960s"]
        T2["process_file_task<br/>soft: 600s / hard: 660s"]
        T3["generate_embeddings_task<br/>soft: 600s / hard: 660s"]
        T4["index_chunks_task<br/>soft: 300s / hard: 330s"]
        T5["finalize_job_task<br/>soft: 120s / hard: 150s"]
    end

    subgraph CrawlTasks["Task Chain (Web Crawl)"]
        C1["crawl_discovery_task<br/>soft: 1800s / hard: 1860s"]
        C2["process_page_task<br/>soft: 300s / hard: 330s"]
        C3["finalize_crawl_task<br/>soft: 120s / hard: 150s"]
    end

    T1 -->|"per file"| T2
    T2 -->|"chunks"| T3
    T3 -->|"vectors"| T4
    T4 -->|"complete"| T5

    C1 -->|"per page"| C2
    C2 -->|"all done"| C3

    Q1 -.-> T1
    Q2 -.-> T2
    Q3 -.-> T3
    Q4 -.-> T4
    Q5 -.-> T5
    Q6 -.-> C1
    Q6 -.-> C2
    Q6 -.-> C3

    subgraph Workers["Worker Pool"]
        W1["Worker 1<br/>(concurrency: 4)"]
        W2["Worker 2<br/>(concurrency: 4)"]
        W3["Worker N<br/>(auto-scale)"]
    end

    Queues -.->|consume| Workers
```

---

## 7. RAG Chat Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Frontend
    participant API as FastAPI
    participant Guard as Guardrails<br/>(Llama Guard)
    participant Search as Vector Search<br/>(pgvector)
    participant LLM as OpenAI GPT-4o
    participant Stream as SSE Stream

    User->>App: Send message
    App->>API: POST /chat {message, conversation_id, scope}

    rect rgb(255, 230, 230)
        Note over API,Guard: Input Safety Check
        API->>Guard: Check message safety
        Guard->>Guard: Llama Guard 3 classification
        alt Unsafe Input
            Guard-->>API: BLOCKED (category)
            API-->>App: Error: "Message flagged"
        end
        Guard-->>API: SAFE
    end

    rect rgb(230, 245, 255)
        Note over API,Search: Context Retrieval
        API->>API: Generate query embedding<br/>(text-embedding-3-small)
        API->>Search: hybrid_search(embedding, query_text)
        Search->>Search: Vector similarity (cosine)<br/>+ Full-text search (ts_rank)
        Search->>Search: Filter by scope<br/>(organization_id, scope_ids)
        Search->>Search: Exclude tombstoned docs<br/>(compliance_tombstones check)
        Search-->>API: Top-K relevant chunks<br/>(with scores)
    end

    rect rgb(230, 255, 230)
        Note over API,LLM: Response Generation
        API->>API: Build system prompt<br/>(scope context + instructions)
        API->>API: Dominance Guard check<br/>(prevent single-source bias)
        API->>LLM: Chat completion request<br/>(model: gpt-4o, stream: true)

        loop Streaming Response
            LLM-->>Stream: Token chunk
            Stream-->>App: SSE data event
            App-->>User: Render token
        end

        Note over Stream: Heartbeat every 15s<br/>(keeps connection alive)
    end

    rect rgb(255, 245, 230)
        Note over API,LLM: Post-Processing
        API->>API: Extract source citations
        API->>API: Save message to conversation
        API->>API: Update token usage counters
        API-->>App: SSE [DONE] event
    end

    App->>App: Display sources panel
    App-->>User: Complete response with citations
```

---

## 8. Security Layers (Defense in Depth)

```mermaid
graph TB
    subgraph L1["Layer 1: Network & Transport"]
        HTTPS["HTTPS Only<br/>(HSTS preload)"]
        CORS["CORS Whitelist<br/>(specific origins)"]
        CSP["Content Security Policy<br/>(script-src, connect-src)"]
        XFrame["X-Frame-Options: DENY"]
        NoSniff["X-Content-Type-Options: nosniff"]
    end

    subgraph L2["Layer 2: Authentication"]
        JWT["JWT Verification<br/>(Supabase-issued)"]
        Session["Session Management<br/>(proxy.ts validation)"]
        TokenCache["Token Caching<br/>(5-min in-memory)"]
        OAuthState["OAuth State Tokens<br/>(CSRF protection)"]
    end

    subgraph L3["Layer 3: Authorization"]
        RLS["Row Level Security<br/>(PostgreSQL policies)"]
        RBAC["Role-Based Access<br/>(admin/editor/viewer)"]
        PlanGate["Plan-Based Gates<br/>(require_plan dependency)"]
        ScopeGuard["Scope Guard<br/>(data source isolation)"]
    end

    subgraph L4["Layer 4: Input Validation"]
        RateLimit["Rate Limiting<br/>(slowapi per-endpoint)"]
        BodySize["Request Body Size<br/>(100MB max)"]
        Pydantic["Pydantic Validation<br/>(max_length, Field())"]
        Sanitize["Input Sanitization<br/>(XSS prevention)"]
        OpenRedirect["Open Redirect Prevention<br/>(path validation)"]
    end

    subgraph L5["Layer 5: Data Protection"]
        Fernet["Fernet AES-256<br/>(Ghost Protocol)"]
        TokenEncrypt["OAuth Token Encryption<br/>(at rest)"]
        Wipe["Secure Deletion<br/>(DoD 5220.22-M 3-pass)"]
        Tombstone["Compliance Tombstones<br/>(instant access revocation)"]
    end

    subgraph L6["Layer 6: Runtime Protection"]
        SSRF["SSRF Protection<br/>(getaddrinfo + IP validation)"]
        Malware["Malware Scanning<br/>(ClamAV, fail-closed)"]
        Guardrails["LLM Guardrails<br/>(Llama Guard 3)"]
        ConsoleGate["Console Gating<br/>(no leaks in production)"]
    end

    subgraph L7["Layer 7: Monitoring"]
        SentryFE["Sentry (Frontend)<br/>(client + edge)"]
        SentryBE["Sentry (Backend)<br/>(server)"]
        AuditLog["Audit Logging<br/>(all critical actions)"]
        Health["Health Endpoint<br/>(/health)"]
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

## 9. Ghost Protocol Encryption Flow

```mermaid
sequenceDiagram
    participant Writer as Ingestion Worker
    participant GhostP as Ghost Protocol<br/>(core/security.py)
    participant Key as CHUNK_ENCRYPTION_KEY<br/>(Fernet AES-256)
    participant DB as PostgreSQL<br/>(document_chunks)
    participant Reader as Search / Chat
    participant Wipe as Secure Wipe

    rect rgb(230, 245, 255)
        Note over Writer,DB: Encryption at Write Time
        Writer->>GhostP: encrypt_content(plaintext_chunk)
        GhostP->>Key: Load Fernet key from env
        GhostP->>GhostP: Fernet.encrypt(plaintext.encode())
        Note over GhostP: Output: base64-encoded<br/>ciphertext with timestamp
        GhostP-->>Writer: encrypted_blob
        Writer->>DB: INSERT chunk (content=encrypted_blob,<br/>embedding=vector)
    end

    rect rgb(230, 255, 230)
        Note over Reader,DB: Decryption at Read Time
        Reader->>DB: Vector search → top-K chunks
        DB-->>Reader: Encrypted chunk content
        Reader->>GhostP: decrypt_content(encrypted_blob)
        GhostP->>Key: Load Fernet key
        GhostP->>GhostP: Fernet.decrypt(blob)
        GhostP-->>Reader: plaintext_chunk
        Reader->>Reader: Include in LLM context
    end

    rect rgb(255, 230, 230)
        Note over Wipe,DB: Secure Deletion (DoD 5220.22-M)
        Wipe->>DB: SELECT chunk content
        Wipe->>Wipe: Pass 1: Overwrite with 0x00
        Wipe->>Wipe: Pass 2: Overwrite with 0xFF
        Wipe->>Wipe: Pass 3: Overwrite with random
        Wipe->>DB: DELETE chunk row
        Wipe->>DB: INSERT compliance_tombstone<br/>(instant access revocation)
        Note over Wipe,DB: Tombstone broadcast via<br/>Supabase Realtime
    end
```

---

## 10. Consent & Compliance Flow

```mermaid
flowchart TB
    subgraph Request["Compliance Request"]
        A[User/Admin requests<br/>data action] --> B{Action type?}
        B -->|GDPR Art. 17<br/>Right to Erasure| C[Deletion Request]
        B -->|CCPA ADMT<br/>Right to Know| D[Data Export Request]
        B -->|Scope Consent<br/>Change| E[Consent Update]
    end

    subgraph Consent["Consent Management"]
        E --> F{Scope level?}
        F -->|Organization| G[Update org consent<br/>PATCH /consent/organization]
        F -->|Data Source| H[Update scope consent<br/>PATCH /consent/scope]
        F -->|Document| I[Update document consent<br/>PATCH /consent/document]
        G & H & I --> J[Audit log entry<br/>created]
        J --> K[Realtime notification<br/>to all tabs]
    end

    subgraph Deletion["Deletion Pipeline"]
        C --> L[Create compliance_tombstone<br/>status: active]
        L --> M[Instant access revocation<br/>via Supabase Realtime]
        M --> N[Ghost Protocol<br/>secure wipe initiated]
        N --> O[3-pass overwrite<br/>DoD 5220.22-M]
        O --> P[DELETE from document_chunks]
        P --> Q[DELETE from documents]
        Q --> R[Update tombstone<br/>status: completed]
    end

    subgraph Export["Data Export"]
        D --> S[Collect all user data<br/>documents, chunks, metadata]
        S --> T[Package as JSON/ZIP]
        T --> U[Return download URL]
    end

    subgraph Audit["Audit Trail"]
        J --> V[consent_audit_log table]
        R --> V
        V --> W[GET /consent/audit<br/>paginated history]
        V --> X[GET /consent/report<br/>compliance summary]
    end

    style Request fill:#fff3e0
    style Consent fill:#e8f5e9
    style Deletion fill:#fce4ec
    style Export fill:#e3f2fd
    style Audit fill:#f3e5f5
```

---

## 11. Team & RBAC Hierarchy

```mermaid
graph TB
    subgraph Organization["Organization (Team)"]
        Team["Team Entity<br/>(teams table)"]

        subgraph Roles["Role Hierarchy"]
            Admin["Admin<br/>Full control"]
            Editor["Editor<br/>Read + Write + Ingest"]
            Viewer["Viewer<br/>Read only"]
        end

        subgraph Members["Team Members"]
            Owner["Owner<br/>(created the team)"]
            M1["Member 1<br/>role: editor"]
            M2["Member 2<br/>role: viewer"]
            M3["Pending Invite<br/>status: invited"]
        end
    end

    subgraph Permissions["Permission Matrix"]
        P1["View documents"]
        P2["Upload / ingest files"]
        P3["Delete documents"]
        P4["Manage connectors"]
        P5["Manage team members"]
        P6["Billing & subscription"]
        P7["Audit logs"]
        P8["Consent management"]
    end

    subgraph PlanGates["Plan-Based Feature Gates"]
        Free["Free Plan<br/>1 user, basic features"]
        Starter["Starter Plan<br/>Up to 3 users"]
        Pro["Pro Plan<br/>Up to 10 users"]
        Enterprise["Enterprise Plan<br/>Unlimited users"]
    end

    Admin --> P1 & P2 & P3 & P4 & P5 & P6 & P7 & P8
    Editor --> P1 & P2 & P3 & P4
    Viewer --> P1

    Team --> Owner
    Team --> M1 & M2 & M3

    subgraph InviteFlow["Invite Flow"]
        I1["Admin sends invite<br/>POST /team/invite"]
        I2["Email sent to user"]
        I3["User clicks link<br/>/invite/{token}"]
        I4["POST /team/accept"]
        I5["Member added with role"]
        I6["Bulk invite via CSV<br/>POST /team/bulk-invite"]
    end

    I1 --> I2 --> I3 --> I4 --> I5
    I6 --> I2

    style Organization fill:#e3f2fd
    style Permissions fill:#e8f5e9
    style PlanGates fill:#fff3e0
    style InviteFlow fill:#f3e5f5
```

---

## 12. Billing & Subscription Flow

```mermaid
sequenceDiagram
    actor User
    participant App as Frontend
    participant API as FastAPI
    participant Polar as Polar.sh<br/>(Payment Provider)
    participant Webhook as Webhook Handler
    participant DB as PostgreSQL

    rect rgb(230, 245, 255)
        Note over User,DB: Plan Selection & Checkout
        User->>App: Click "Upgrade to Pro"
        App->>API: POST /billing/checkout<br/>{plan_id: "pro_monthly"}
        API->>Polar: Create checkout session
        Polar-->>API: {checkout_url}
        API-->>App: Redirect URL
        App->>User: Redirect to Polar checkout
        User->>Polar: Enter payment details
        Polar->>Polar: Process payment
    end

    rect rgb(230, 255, 230)
        Note over Polar,DB: Webhook Processing
        Polar->>Webhook: POST /webhooks/polar<br/>(subscription.created)
        Webhook->>Webhook: Verify webhook signature
        Webhook->>DB: UPDATE organizations SET<br/>plan = 'pro',<br/>subscription_id = '...'
        Webhook->>DB: UPDATE quota limits<br/>(storage, daily_jobs, etc.)
        Note over Webhook: If webhook fails → DLQ<br/>(Dead Letter Queue)
    end

    rect rgb(255, 245, 230)
        Note over User,DB: Quota Enforcement
        User->>App: Upload file
        App->>API: POST /upload-url
        API->>DB: Check current usage vs plan limits
        alt Within Quota
            API-->>App: Presigned URL
        else Quota Exceeded
            API-->>App: 402 "Storage limit reached"
            App-->>User: Show upgrade prompt
        end
    end

    rect rgb(255, 230, 230)
        Note over User,DB: Subscription Management
        User->>App: Click "Manage Subscription"
        App->>API: POST /billing/portal
        API->>Polar: Create portal session
        Polar-->>API: {portal_url}
        API-->>App: Redirect URL
        App->>User: Redirect to Polar portal
        Note over User,Polar: Change plan, cancel,<br/>update payment method
    end
```

---

## 13. Frontend Component Architecture

```mermaid
graph TB
    subgraph RootLayout["Root Layout (app/layout.tsx)"]
        QP["QueryProvider<br/>(React Query + DevTools)"]
        SP["SessionProvider<br/>(Supabase Auth)"]
        TP["ThemeProvider<br/>(Light/Dark/System)"]
        TT["TooltipProvider + Toaster"]
    end

    subgraph DashboardLayout["Dashboard Layout"]
        PP["ProfileProvider<br/>(single-fetch)"]
        UP["UsageProvider<br/>(plan + quotas)"]
        QSP["QuotaStatusProvider<br/>(localStorage + Realtime)"]
        DIP["DataInvalidationProvider<br/>(Ghost Protocol tombstones)"]
        CHP["ChatHistoryProvider<br/>(conversations)"]
        IMP["IngestModalProvider<br/>(global modal)"]
        IPP["IngestionProgressProvider<br/>(progress tracking)"]
        PW["PaywallGuard<br/>(subscription enforcement)"]
    end

    subgraph RouteGroups["Route Groups (5)"]
        RG1["(auth)<br/>login, register,<br/>forgot-password"]
        RG2["(marketing)<br/>landing, legal"]
        RG3["auth<br/>callback, reset,<br/>error"]
        RG4["dashboard<br/>chat, documents,<br/>settings/*"]
        RG5["oauth<br/>callback"]
    end

    subgraph StateManagement["State Management"]
        RQ["React Query<br/>Server state,<br/>caching, dedup"]
        CTX["Context Providers<br/>Singleton state<br/>(Profile, Usage)"]
        LS["localStorage<br/>Quota status,<br/>theme preference"]
        BC["BroadcastChannel<br/>Cross-tab sync<br/>(7 query prefixes)"]
    end

    subgraph ErrorBoundaries["Error Boundaries (18+)"]
        GE["global-error.tsx<br/>(app-wide)"]
        DE["dashboard/error.tsx"]
        SE["settings/*/error.tsx<br/>(12 files)"]
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

## 14. Docker Infrastructure

```mermaid
graph TB
    subgraph DockerCompose["Docker Compose Services"]
        subgraph Core["Core Services"]
            BE["backend<br/>FastAPI<br/>Port: 8000<br/>Memory: 4G / CPU: 4"]
            Redis["redis<br/>Redis 7 Alpine<br/>Port: 6379<br/>Memory: 1G / CPU: 1"]
        end

        subgraph WorkerServices["Worker Services"]
            W1["celery-worker<br/>Celery Worker<br/>(concurrency: auto)<br/>Memory: 4G / CPU: 4"]
            Beat["celery-beat<br/>Celery Beat<br/>(periodic scheduler)"]
            Flower["flower<br/>Celery Flower<br/>Port: 5555<br/>Memory: 512M / CPU: 0.5"]
        end
    end

    subgraph ProductionOverrides["Production Overrides (docker-compose.prod.yml)"]
        NoExpose["No exposed ports<br/>(except backend:8000)"]
        NetIsolation["Network isolation<br/>(internal network)"]
        RedisPersist["Redis AOF persistence<br/>(appendonly yes)"]
        FlowerAuth["Flower authentication<br/>(basic_auth required)"]
        LogRotation["JSON log rotation<br/>(max 10MB x 3 files)"]
    end

    subgraph HealthChecks["Health Checks"]
        HC1["backend: /health<br/>interval: 30s, retries: 3"]
        HC2["redis: redis-cli ping<br/>interval: 10s, retries: 3"]
        HC3["flower: /api/workers<br/>interval: 30s, retries: 3"]
    end

    subgraph External["External Services"]
        Supabase["Supabase Cloud<br/>(PostgreSQL + Auth<br/>+ Storage + Realtime)"]
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

## 15. CI/CD Pipeline Flow

```mermaid
flowchart LR
    subgraph Trigger["Trigger"]
        Push["Push to main"]
        PR["Pull Request"]
    end

    subgraph Lint["Job 1: Lint"]
        L1["ruff check backend/"]
        L2["ruff format --check"]
    end

    subgraph BackendTest["Job 2: Backend Tests"]
        BT1["pip install -r requirements.txt"]
        BT2["pytest -m unit<br/>--tb=short"]
    end

    subgraph FrontendLint["Job 3: Frontend Lint"]
        FL1["npm ci"]
        FL2["npm run lint<br/>(ESLint + TypeScript)"]
    end

    subgraph FrontendTest["Job 4: Frontend Tests"]
        FT1["npm ci"]
        FT2["npx vitest run<br/>(2798 tests)"]
    end

    subgraph FrontendBuild["Job 5: Frontend Build"]
        FB1["npm ci"]
        FB2["CI=true npm run build<br/>(skip env validation)"]
    end

    subgraph Security["Job 6: Security Audit"]
        S1["pip-audit<br/>(Python dependencies)"]
        S2["npm audit<br/>(Node dependencies)"]
    end

    Push & PR --> Lint & BackendTest & FrontendLint & FrontendTest & FrontendBuild & Security

    Lint -->|Pass| Done["All Checks Pass"]
    BackendTest -->|Pass| Done
    FrontendLint -->|Pass| Done
    FrontendTest -->|Pass| Done
    FrontendBuild -->|Pass| Done
    Security -->|Pass| Done

    style Trigger fill:#e3f2fd
    style Lint fill:#fff3e0
    style BackendTest fill:#e8f5e9
    style FrontendLint fill:#f3e5f5
    style FrontendTest fill:#fce4ec
    style FrontendBuild fill:#fff8e1
    style Security fill:#e0f7fa
```

---

## Rendering Notes

- All diagrams use **Mermaid** syntax and can be rendered in:
  - GitHub Markdown (native support)
  - VS Code with Mermaid extension
  - Mermaid Live Editor: https://mermaid.live
  - Notion, Confluence, and most modern documentation platforms
- For slide decks: export as SVG/PNG from Mermaid Live Editor
- Recommended: Use dark theme for presentations (better contrast)
