# AxioHub On-Premise Refactoring Guide

> **Version:** 1.0 | **Date:** February 2026 | **Status:** Planning
>
> Enterprise-grade technical specification for refactoring the AxioHub RAG platform
> from cloud-hosted SaaS to a fully self-contained on-premise deployment.
> This document serves as the single source of truth for architecture decisions,
> migration strategies, deployment procedures, and quality trade-offs.

---

## Table of Contents

1. [Executive Summary & Business Case](#1-executive-summary--business-case)
2. [Architecture Overview: Cloud vs. On-Premise](#2-architecture-overview-cloud-vs-on-premise)
3. [Component Inventory & Dependency Map](#3-component-inventory--dependency-map)
4. [Migration Strategy (Per-Component)](#4-migration-strategy-per-component)
5. [On-Premise Architecture](#5-on-premise-architecture)
6. [LLM & Embedding Migration](#6-llm--embedding-migration)
7. [Self-Hosted Supabase Strategy](#7-self-hosted-supabase-strategy)
8. [SaaS Service Replacements](#8-saas-service-replacements)
9. [Setup & Deployment Procedure](#9-setup--deployment-procedure)
10. [Hardware Requirements & Sizing Guide](#10-hardware-requirements--sizing-guide)
11. [Security Considerations](#11-security-considerations)
12. [Quality Trade-offs: Cloud vs. On-Premise](#12-quality-trade-offs-cloud-vs-on-premise)
13. [Testing & Verification Plan](#13-testing--verification-plan)
14. [Project Timeline & Milestones](#14-project-timeline--milestones)
15. [Risk Register](#15-risk-register)
16. [Appendices](#16-appendices)

---

## 1. Executive Summary & Business Case

### 1.1 Purpose

This document specifies the complete refactoring of AxioHub from a cloud-dependent SaaS platform into a **self-contained on-premise deployment** that can run entirely within an organization's own infrastructure — air-gapped if required — with zero external API calls for core functionality.

### 1.2 Why On-Premise?

| Driver | Cloud (Current) | On-Premise (Target) |
|--------|----------------|---------------------|
| **Data Sovereignty** | Data transits to Supabase Cloud, OpenAI API, Sentry | All data stays within organization's network perimeter |
| **Regulatory Compliance** | Depends on vendor compliance (SOC 2, GDPR DPA) | Full control over data residency and retention |
| **Air-Gap Capability** | Not possible — requires internet for core features | Fully functional with zero internet connectivity |
| **Cost at Scale** | Variable — OpenAI API costs grow with usage | Fixed hardware cost — predictable TCO after initial investment |
| **Latency** | Network round-trips to OpenAI (~200-500ms per embedding batch) | Local inference (~50-150ms per embedding batch on GPU) |
| **Customization** | Limited to vendor-provided models and configurations | Fine-tune models on proprietary data, custom tokenizers |

### 1.3 Scope

**In Scope:**
- Replace all cloud-hosted SaaS dependencies with self-hosted alternatives
- Local LLM inference (Ollama/vLLM) replacing OpenAI API
- Self-hosted Supabase replacing Supabase Cloud
- Self-hosted monitoring, email, and billing replacements
- Single-command Docker Compose deployment
- Hardware sizing and procurement guidance

**Out of Scope:**
- Kubernetes/Helm chart orchestration (future phase)
- Multi-node distributed deployment (single-server focus)
- Custom model training and fine-tuning procedures
- Frontend redesign or feature changes

### 1.4 Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Zero external API calls | Network audit shows no outbound traffic to cloud APIs |
| Feature parity | All 10 connectors functional (OAuth providers need internal IdP) |
| RAG quality | Semantic search recall within 15% of OpenAI baseline |
| Deployment time | < 30 minutes from bare metal to operational (with pre-pulled images) |
| Health checks passing | All 4 health endpoints return 200 (`/health`, `/health/ready`, `/health/live`, `/health/startup`) |

---

## 2. Architecture Overview: Cloud vs. On-Premise

### 2.1 Current Cloud Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser<br/>(Next.js 16 App)"]
    end

    subgraph Edge["Vercel Edge"]
        Proxy["proxy.ts<br/>(Auth Middleware)"]
        Rewrites["API Rewrites<br/>(/api/py/* → Backend)"]
    end

    subgraph Cloud["Cloud Services (External)"]
        SupaCloud["Supabase Cloud<br/>(PostgreSQL + pgvector + Auth + Storage + Realtime)"]
        OpenAI["OpenAI API<br/>(GPT-4o + Embeddings)"]
        Groq["Groq Cloud<br/>(Llama 3.1 Guardrails)"]
        SentryCloud["Sentry.io<br/>(Error Tracking)"]
        ResendCloud["Resend<br/>(Transactional Email)"]
        PolarCloud["Polar.sh<br/>(Billing)"]
        BrightData["Bright Data<br/>(YouTube Proxy)"]
    end

    subgraph Backend["Railway / Docker"]
        API["FastAPI<br/>(main.py)"]
        Celery["Celery Workers"]
        Redis["Redis"]
        ClamAV["ClamAV"]
    end

    Browser --> Proxy --> Rewrites --> API
    API --> SupaCloud
    API --> OpenAI
    API --> Groq
    API --> SentryCloud
    API --> ResendCloud
    API --> PolarCloud
    Celery --> SupaCloud
    Celery --> OpenAI
    Celery --> Redis
    Celery --> BrightData

    style Cloud fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style Backend fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
```

### 2.2 Target On-Premise Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Browser["Browser<br/>(Next.js 16 App)"]
    end

    subgraph Reverse["Reverse Proxy"]
        Nginx["Nginx<br/>(TLS Termination + Routing)"]
    end

    subgraph OnPrem["On-Premise Docker Stack"]
        Frontend["Next.js Container<br/>(Port 3000)"]
        API["FastAPI Container<br/>(Port 8000)"]
        Celery["Celery Workers<br/>(2-4 workers)"]
        Beat["Celery Beat<br/>(Scheduler)"]
        Flower["Flower<br/>(Task Monitoring)"]

        subgraph AI["AI Inference Layer"]
            Ollama["Ollama<br/>(LLM + Embeddings)"]
            VLLM["vLLM<br/>(Optional: High-Throughput)"]
        end

        subgraph Data["Data Layer"]
            Supabase["Self-Hosted Supabase<br/>(PostgreSQL + Auth + Storage + Realtime)"]
            Redis["Redis<br/>(Cache + Celery Broker)"]
        end

        subgraph Monitoring["Monitoring"]
            Sentry["Self-Hosted Sentry"]
            Prometheus["Prometheus + Grafana"]
        end

        subgraph Support["Support Services"]
            ClamAV["ClamAV<br/>(Malware Scanning)"]
            Postfix["Postfix / SMTP<br/>(Email)"]
        end
    end

    Browser --> Nginx
    Nginx --> Frontend
    Nginx --> API
    API --> Supabase
    API --> Ollama
    API --> Redis
    API --> Sentry
    Celery --> Supabase
    Celery --> Ollama
    Celery --> Redis
    Celery --> ClamAV
    Beat --> Redis

    style OnPrem fill:#dcfce7,stroke:#22c55e,stroke-width:2px
    style AI fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
```

### 2.3 Key Architectural Changes

| Component | Cloud (Current) | On-Premise (Target) | Change Impact |
|-----------|----------------|---------------------|---------------|
| **Database** | Supabase Cloud | Self-Hosted Supabase | Configuration only — same SDK |
| **Auth** | Supabase Auth (Cloud) | Supabase GoTrue (Self-Hosted) | Same API surface |
| **Storage** | Supabase Storage (Cloud) | Supabase Storage (Self-Hosted + MinIO) | Same API surface |
| **LLM Chat** | OpenAI GPT-4o | Ollama (Llama 3.1 70B / Qwen 2.5 72B) | Provider swap in `llm_factory.py` |
| **Embeddings** | OpenAI text-embedding-3-small | Ollama (nomic-embed-text / mxbai-embed-large) | Provider swap in `embeddings.py` |
| **Guardrails** | Groq (Llama 3.1 8B) | Ollama (Llama 3.1 8B) | Same model, local inference |
| **Error Tracking** | Sentry.io | Self-Hosted Sentry | DSN change only |
| **Email** | Resend API | Postfix / SMTP relay | Service swap in `email.py` |
| **Billing** | Polar.sh | Disabled / License-key based | Remove or replace |
| **YouTube Proxy** | Bright Data | Direct (on-prem IPs not blocked) | Simplified — remove proxy layer |
| **Deployment** | Vercel + Railway | Docker Compose + Nginx | New compose file |

---

## 3. Component Inventory & Dependency Map

### 3.1 External Service Dependencies (Must Replace)

| # | Service | Used For | Files Affected | Priority |
|---|---------|----------|---------------|----------|
| 1 | **OpenAI API** | Chat LLM (GPT-4o, GPT-4o-mini) | `backend/services/llm_factory.py`, `backend/core/config.py:31-72` | **CRITICAL** |
| 2 | **OpenAI API** | Embeddings (text-embedding-3-small, 1536d) | `backend/services/embeddings.py`, `backend/core/embeddings.py` | **CRITICAL** |
| 3 | **Supabase Cloud** | PostgreSQL + pgvector + Auth + Storage + Realtime | `backend/core/db.py`, `frontend-new/lib/supabase/*.ts` | **CRITICAL** |
| 4 | **Groq Cloud** | Guardrail model (Llama 3.1 8B) | `backend/services/guardrails.py`, `backend/services/llm_factory.py` | HIGH |
| 5 | **Resend** | Transactional email (invites, notifications) | `backend/services/email.py` | HIGH |
| 6 | **Polar.sh** | Subscription billing | `backend/services/subscription.py`, `backend/api/v1/billing.py`, `backend/api/v1/webhooks.py` | HIGH |
| 7 | **Sentry.io** | Error tracking + session replay | `backend/core/sentry_utils.py`, `frontend-new/sentry.*.config.ts` | MEDIUM |
| 8 | **Bright Data** | YouTube transcript proxy | `backend/connectors/web.py`, `backend/core/config.py:229-254` | LOW |
| 9 | **LlamaParse** | Advanced PDF OCR | `backend/services/parsers.py` | LOW |
| 10 | **Grok (xAI)** | Optional LLM provider | `backend/core/config.py:119-122` | LOW |

### 3.2 Self-Hosted Services (Already Containerized)

| # | Service | Status | Docker Service | Notes |
|---|---------|--------|---------------|-------|
| 1 | **Redis** | Ready | `docker-compose.yml` | No changes needed |
| 2 | **ClamAV** | Ready | `docker/backend.Dockerfile` | Bundled in backend container |
| 3 | **Celery Workers** | Ready | `backend/Dockerfile.worker` | No changes needed |
| 4 | **Celery Beat** | Ready | Same container | Schedule configuration only |
| 5 | **Flower** | Ready | `docker-compose.yml` | No changes needed |

### 3.3 OAuth Connector Dependencies

These connectors require OAuth with **external cloud providers**. On-premise deployment has two options per connector: (A) keep external OAuth if internet access exists, or (B) replace with self-hosted alternatives.

| Connector | OAuth Provider | File | On-Prem Alternative |
|-----------|---------------|------|---------------------|
| Google Drive | Google Cloud | `backend/connectors/drive.py` (478 lines) | Nextcloud + WebDAV |
| Notion | Notion API | `backend/connectors/notion.py` (462 lines) | Self-hosted wiki + API |
| Dropbox | Dropbox API | `backend/connectors/dropbox.py` (778 lines) | Nextcloud / Seafile |
| GitHub | GitHub.com | `backend/connectors/github.py` (1,376 lines) | Gitea / GitLab API |
| OneDrive | Microsoft Graph | `backend/connectors/microsoft.py` (503 lines) | Nextcloud / Seafile |
| SharePoint | Microsoft Graph | `backend/connectors/microsoft.py` (503 lines) | Nextcloud / Seafile |
| Box | Box API | `backend/connectors/box.py` (993 lines) | Nextcloud |
| S3 | AWS IAM | `backend/connectors/s3.py` (899 lines) | MinIO (S3-compatible) |
| SFTP | SSH keys | `backend/connectors/sftp.py` (464 lines) | Direct — no changes |
| Web Crawler | None | `backend/connectors/web.py` (1,209 lines) | Direct — no changes |
| File Upload | Supabase Storage | `backend/connectors/file_upload.py` (179 lines) | Self-hosted Supabase Storage |

### 3.4 Dependency Graph

```mermaid
graph LR
    subgraph Critical["Critical Path (Must Replace)"]
        OpenAI["OpenAI API"]
        Supabase["Supabase Cloud"]
    end

    subgraph High["High Priority"]
        Groq["Groq Cloud"]
        Resend["Resend Email"]
        Polar["Polar.sh Billing"]
    end

    subgraph Medium["Medium Priority"]
        Sentry["Sentry.io"]
        OAuth["OAuth Providers"]
    end

    subgraph Low["Low Priority"]
        BrightData["Bright Data"]
        LlamaParse["LlamaParse"]
    end

    API["FastAPI Backend"] --> OpenAI
    API --> Supabase
    API --> Groq
    API --> Resend
    API --> Polar
    API --> Sentry
    API --> OAuth
    Celery["Celery Workers"] --> OpenAI
    Celery --> Supabase
    Celery --> BrightData
    Celery --> LlamaParse
    Frontend["Next.js Frontend"] --> Supabase
    Frontend --> Sentry

    style Critical fill:#fee2e2,stroke:#ef4444,stroke-width:2px
    style High fill:#fef3c7,stroke:#f59e0b,stroke-width:2px
    style Medium fill:#dbeafe,stroke:#3b82f6,stroke-width:2px
    style Low fill:#f3f4f6,stroke:#9ca3af,stroke-width:1px
```

---

## 4. Migration Strategy (Per-Component)

### 4.1 LLM Provider Migration (OpenAI → Ollama)

**Current Implementation** — `backend/services/llm_factory.py`:

The LLM factory already supports multiple providers through a provider/model name pattern. The migration requires adding Ollama as a provider option.

**What Changes:**

```python
# backend/core/config.py — Change defaults
PRIMARY_MODEL_PROVIDER = "ollama"          # was: "openai"
PRIMARY_MODEL_NAME = "llama3.1:70b"        # was: "gpt-4o"
SECONDARY_MODEL_PROVIDER = "ollama"        # was: "openai"
SECONDARY_MODEL_NAME = "llama3.1:8b"       # was: "gpt-4o-mini"
GUARDRAIL_MODEL_PROVIDER = "ollama"        # was: "groq"
GUARDRAIL_MODEL_NAME = "llama3.1:8b"       # was: "llama-3.1-8b-instant"
```

```python
# backend/services/llm_factory.py — Add Ollama provider
from langchain_community.chat_models import ChatOllama

def create_llm(provider: str, model: str, **kwargs):
    if provider == "ollama":
        return ChatOllama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,  # http://ollama:11434
            temperature=kwargs.get("temperature", 0.1),
            num_ctx=kwargs.get("num_ctx", 8192),
        )
    elif provider == "openai":
        # ... existing OpenAI code
```

**New Environment Variables:**
```env
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_KEEP_ALIVE=5m
OLLAMA_NUM_PARALLEL=4
```

### 4.2 Embedding Migration (OpenAI → Ollama/Local)

**Current Implementation** — `backend/services/embeddings.py`:

The embedding pipeline uses OpenAI's `text-embedding-3-small` (1536 dimensions) with batch processing, TPM regulation, and adaptive throttling.

**What Changes:**

```python
# backend/core/embeddings.py — Update embedding factory
# The multi-tier factory already supports LOCAL tier with HuggingFace
# Promote LOCAL to default for on-premise:

class EmbeddingTier(str, Enum):
    LOCAL = "local"        # HuggingFace BAAI/bge-small-en-v1.5 (384d) — CPU-only
    OLLAMA = "ollama"      # nomic-embed-text (768d) — via Ollama API
    PREMIUM = "premium"    # OpenAI (1536d) — cloud fallback

# Add Ollama embedding support:
def get_ollama_embeddings():
    from langchain_community.embeddings import OllamaEmbeddings
    return OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=settings.OLLAMA_BASE_URL,
    )
```

**Critical:** The pgvector index dimension must match the embedding model:
- OpenAI `text-embedding-3-small`: **1536 dimensions**
- `nomic-embed-text`: **768 dimensions**
- `mxbai-embed-large`: **1024 dimensions**
- HuggingFace `bge-small-en-v1.5`: **384 dimensions**

**Migration SQL** (run once after switching models):
```sql
-- Drop existing vector index
DROP INDEX IF EXISTS idx_chunks_embedding;

-- Alter column dimension (e.g., 768 for nomic-embed-text)
ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(768);

-- Recreate HNSW index
CREATE INDEX idx_chunks_embedding ON chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- WARNING: All existing embeddings must be regenerated!
-- Existing 1536-dim vectors are incompatible with 768-dim index.
```

### 4.3 Supabase Migration (Cloud → Self-Hosted)

**Current Implementation** — Uses Supabase SDK everywhere:

| Layer | File | SDK |
|-------|------|-----|
| Backend DB | `backend/core/db.py` | `supabase-py` |
| Backend Auth | `backend/core/security.py` | JWT validation via `python-jose` |
| Frontend Browser | `frontend-new/lib/supabase/client.ts` | `@supabase/supabase-js` |
| Frontend Server | `frontend-new/lib/supabase/server.ts` | `@supabase/ssr` |
| Frontend Proxy | `frontend-new/proxy.ts` | `@supabase/ssr` |

**What Changes:**

The **code does not change** — only the `SUPABASE_URL` and keys change to point to the self-hosted instance. This is the primary reason we use self-hosted Supabase rather than replacing it with raw PostgreSQL + a different auth system.

```env
# Cloud (current):
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SECRET_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# On-Premise (target):
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_SECRET_KEY=<self-hosted-service-role-key>
SUPABASE_JWT_SECRET=<self-hosted-jwt-secret>
NEXT_PUBLIC_SUPABASE_URL=https://supabase.your-domain.com
NEXT_PUBLIC_SUPABASE_ANON_KEY=<self-hosted-anon-key>
```

See [Section 7](#7-self-hosted-supabase-strategy) for full self-hosted Supabase setup.

### 4.4 Email Migration (Resend → SMTP)

**Current Implementation** — `backend/services/email.py` (500+ lines):

The email service sends team invitations, ingestion notifications, failure alerts, DLQ retries, enterprise inquiries, and welcome emails via the Resend API.

**What Changes:**

```python
# backend/services/email.py — Add SMTP transport
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class EmailService:
    def __init__(self):
        self.provider = settings.EMAIL_PROVIDER  # "resend" or "smtp"

    def _send_via_smtp(self, to: str, subject: str, html: str):
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAILS_FROM_EMAIL
        msg["To"] = to
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAILS_FROM_EMAIL, to, msg.as_string())
```

**New Environment Variables:**
```env
EMAIL_PROVIDER=smtp                    # "resend" or "smtp"
SMTP_HOST=postfix                      # Docker service name
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=                         # Optional for local Postfix
SMTP_PASSWORD=                         # Optional for local Postfix
```

### 4.5 Billing Migration (Polar.sh → Disabled/License-Key)

**Current Implementation** — `backend/services/subscription.py`, `backend/api/v1/billing.py`:

Polar.sh handles subscription management with product IDs for Starter, Pro, and Enterprise tiers.

**On-Premise Strategy:**

For on-premise deployments, billing is typically handled through enterprise license agreements rather than self-service subscriptions. The migration:

1. **Disable Polar webhook handler** in `backend/api/v1/webhooks.py`
2. **Set default plan to enterprise** in `backend/core/config.py`:
   ```python
   # On-premise: all users get enterprise limits
   ON_PREMISE_MODE = True
   DEFAULT_PLAN = "enterprise_large"
   ```
3. **Quota limits become configurable** rather than plan-gated:
   ```env
   ONPREMISE_MODE=true
   DEFAULT_PLAN=enterprise_large
   LIMITS_ENTERPRISE_FILES=999999
   LIMITS_ENTERPRISE_SCOPES=999999
   LIMITS_ENTERPRISE_MB=999999
   LIMITS_ENTERPRISE_LLM_TOKENS=999999999
   ```

### 4.6 Error Tracking Migration (Sentry.io → Self-Hosted Sentry)

**Current DSN**: `https://18f4a279...@o4508223588663296.ingest.de.sentry.io/4510600366194768`

**What Changes:**

Replace the DSN in environment variables only — all Sentry SDK code remains identical:

```env
# Backend
SENTRY_DSN=https://<key>@sentry.your-domain.com/<project-id>

# Frontend
NEXT_PUBLIC_SENTRY_DSN=https://<key>@sentry.your-domain.com/<project-id>
```

Self-hosted Sentry is deployed via its official Docker Compose setup (see [Section 8.3](#83-monitoring--observability)).

### 4.7 YouTube Proxy Migration (Bright Data → Direct)

**Current Implementation** — `backend/connectors/web.py`:

Bright Data's Unlocker API is used because cloud IP ranges (AWS, GCP, Railway) are blocked by YouTube. On-premise servers typically use residential/commercial IP addresses that are **not blocked**.

**What Changes:**

```env
# Disable Bright Data — direct access from on-prem IP
BRIGHTDATA_API_KEY=              # Leave empty
YOUTUBE_DIRECT_FALLBACK=true     # Already the fallback behavior
```

The web connector's `youtube-transcript-api` library works directly when not on cloud IPs. No code changes needed — the existing fallback logic handles this.

---

## 5. On-Premise Architecture

### 5.1 Docker Compose Service Topology

```mermaid
graph TB
    subgraph External["Host Network"]
        Nginx["Nginx<br/>:443 (HTTPS)<br/>:80 (HTTP → HTTPS)"]
    end

    subgraph Frontend["Frontend Network"]
        NextJS["Next.js<br/>:3000"]
    end

    subgraph Backend["Backend Network"]
        API["FastAPI<br/>:8000"]
        Worker1["Celery Worker 1"]
        Worker2["Celery Worker 2"]
        Beat["Celery Beat"]
        Flower["Flower<br/>:5555"]
    end

    subgraph AI["AI Network"]
        Ollama["Ollama<br/>:11434"]
    end

    subgraph Data["Data Network (Internal)"]
        Supabase["Supabase Stack<br/>(Kong + GoTrue + PostgREST<br/>+ Realtime + Storage)"]
        PG["PostgreSQL 15<br/>+ pgvector<br/>:5432"]
        Redis["Redis<br/>:6379"]
    end

    subgraph Monitoring["Monitoring Network"]
        Sentry["Self-Hosted Sentry<br/>:9000"]
        ClamAV["ClamAV<br/>:3310"]
    end

    Nginx -->|/| NextJS
    Nginx -->|/api/py/*| API
    Nginx -->|/flower/| Flower
    NextJS -->|SSR auth| Supabase
    API --> Supabase
    API --> PG
    API --> Redis
    API --> Ollama
    API --> ClamAV
    API --> Sentry
    Worker1 --> PG
    Worker1 --> Redis
    Worker1 --> Ollama
    Worker1 --> ClamAV
    Worker2 --> PG
    Worker2 --> Redis
    Worker2 --> Ollama
    Beat --> Redis
    Flower --> Redis
    Supabase --> PG
```

### 5.2 Network Isolation

| Network | Driver | Internal | Services |
|---------|--------|----------|----------|
| `frontend-net` | bridge | No | Nginx, Next.js |
| `backend-net` | bridge | No | Nginx, FastAPI, Workers, Beat, Flower |
| `data-net` | bridge | **Yes** | PostgreSQL, Redis, Supabase |
| `ai-net` | bridge | **Yes** | Ollama, FastAPI, Workers |
| `monitoring-net` | bridge | **Yes** | Sentry, ClamAV, FastAPI |

The `data-net` and `ai-net` networks are marked `internal: true` — no external access is possible. Only the FastAPI and worker containers bridge between networks.

### 5.3 Nginx Reverse Proxy Configuration

```nginx
# /etc/nginx/conf.d/axiohub.conf

upstream frontend {
    server nextjs:3000;
}

upstream backend {
    server api:8000;
}

upstream flower {
    server flower:5555;
}

# HTTP → HTTPS redirect
server {
    listen 80;
    server_name axiohub.your-domain.com;
    return 301 https://$server_name$request_uri;
}

# Main HTTPS server
server {
    listen 443 ssl http2;
    server_name axiohub.your-domain.com;

    # TLS Configuration
    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers on;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Frontend (default)
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for Supabase Realtime via Next.js proxy)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Backend API
    location /api/py/ {
        proxy_pass http://backend/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Streaming support for chat responses
        proxy_buffering off;
        proxy_read_timeout 300s;

        # File upload limit
        client_max_body_size 110m;
    }

    # Health check (unauthenticated)
    location /api/py/health {
        proxy_pass http://backend/health;
        access_log off;
    }

    # Flower (restricted access)
    location /flower/ {
        # IP allowlist — restrict to admin network
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;

        proxy_pass http://flower/;
        proxy_set_header Host $host;
    }

    # Static asset caching
    location /_next/static/ {
        proxy_pass http://frontend;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### 5.4 Docker Compose (On-Premise)

The complete `docker-compose.onpremise.yml` file structure:

```yaml
# docker-compose.onpremise.yml
version: "3.8"

services:
  # ─── Reverse Proxy ───────────────────────────────────
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      nextjs:
        condition: service_healthy
      api:
        condition: service_healthy
    networks:
      - frontend-net
      - backend-net
    restart: unless-stopped

  # ─── Frontend ────────────────────────────────────────
  nextjs:
    build:
      context: ./frontend-new
      dockerfile: Dockerfile
    environment:
      - NEXT_PUBLIC_SUPABASE_URL=https://supabase.your-domain.com
      - NEXT_PUBLIC_SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - NEXT_PUBLIC_API_URL=https://axiohub.your-domain.com
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - frontend-net
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: "1"
    restart: unless-stopped

  # ─── Backend API ─────────────────────────────────────
  api:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    environment:
      - ENVIRONMENT=production
      - SUPABASE_URL=http://supabase-kong:8000
      - SUPABASE_SECRET_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - OLLAMA_BASE_URL=http://ollama:11434
      - PRIMARY_MODEL_PROVIDER=ollama
      - PRIMARY_MODEL_NAME=llama3.1:70b
      - SECONDARY_MODEL_PROVIDER=ollama
      - SECONDARY_MODEL_NAME=llama3.1:8b
      - GUARDRAIL_MODEL_PROVIDER=ollama
      - GUARDRAIL_MODEL_NAME=llama3.1:8b
      - EMBEDDING_PROVIDER=ollama
      - EMBEDDING_MODEL=nomic-embed-text
      - REDIS_URL=redis://redis:6379/0
      - EMAIL_PROVIDER=smtp
      - SMTP_HOST=postfix
      - SMTP_PORT=25
      - ONPREMISE_MODE=true
      - DEFAULT_PLAN=enterprise_large
      - MALWARE_SCAN_FAIL_CLOSED=true
      - STRICT_ENCRYPTION_MODE=true
      - CHUNK_ENCRYPTION_KEY=${CHUNK_ENCRYPTION_KEY}
      - ALLOWED_ORIGINS=https://axiohub.your-domain.com
      - SENTRY_DSN=${SENTRY_DSN}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    depends_on:
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
    networks:
      - backend-net
      - data-net
      - ai-net
      - monitoring-net
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "4"
        reservations:
          memory: 1G
          cpus: "1"
    restart: unless-stopped

  # ─── Celery Workers ─────────────────────────────────
  worker:
    build:
      context: .
      dockerfile: backend/Dockerfile.worker
    environment:
      # Same as api service (inherits via env_file)
      - ENVIRONMENT=production
      - SUPABASE_URL=http://supabase-kong:8000
      - SUPABASE_SECRET_KEY=${SUPABASE_SERVICE_ROLE_KEY}
      - SUPABASE_JWT_SECRET=${SUPABASE_JWT_SECRET}
      - OLLAMA_BASE_URL=http://ollama:11434
      - PRIMARY_MODEL_PROVIDER=ollama
      - PRIMARY_MODEL_NAME=llama3.1:70b
      - EMBEDDING_PROVIDER=ollama
      - EMBEDDING_MODEL=nomic-embed-text
      - REDIS_URL=redis://redis:6379/0
      - CHUNK_ENCRYPTION_KEY=${CHUNK_ENCRYPTION_KEY}
      - CELERY_WORKER_CONCURRENCY=2
      - CELERY_WORKER_MAX_MEMORY_PER_CHILD=3000000
    depends_on:
      redis:
        condition: service_healthy
      ollama:
        condition: service_started
    networks:
      - backend-net
      - data-net
      - ai-net
      - monitoring-net
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 4G
          cpus: "2"
    restart: unless-stopped

  # ─── Celery Beat ─────────────────────────────────────
  beat:
    build:
      context: .
      dockerfile: backend/Dockerfile.worker
    command: celery -A core.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - backend-net
      - data-net
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: "0.25"
    restart: unless-stopped

  # ─── Flower (Celery Monitoring) ──────────────────────
  flower:
    build:
      context: .
      dockerfile: docker/backend.Dockerfile
    command: celery -A core.celery_app flower --port=5555
    environment:
      - REDIS_URL=redis://redis:6379/0
      - FLOWER_BASIC_AUTH=${FLOWER_USER}:${FLOWER_PASSWORD}
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5555/api/workers"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - backend-net
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: "0.5"
    restart: unless-stopped

  # ─── Ollama (LLM Inference) ──────────────────────────
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_KEEP_ALIVE=5m
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_LOADED_MODELS=3
    deploy:
      resources:
        limits:
          memory: 48G
          cpus: "8"
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - ai-net
    restart: unless-stopped

  # ─── Redis ───────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: >
      redis-server
      --maxmemory 1gb
      --maxmemory-policy allkeys-lru
      --appendonly yes
      --save 60 1000
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - data-net
    deploy:
      resources:
        limits:
          memory: 1536M
          cpus: "1"
    restart: unless-stopped

  # ─── PostgreSQL (for Supabase) ───────────────────────
  postgres:
    image: supabase/postgres:15.6.1.143
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: postgres
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./supabase/migrations:/docker-entrypoint-initdb.d/migrations
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - data-net
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: "2"
    restart: unless-stopped

  # ─── ClamAV ─────────────────────────────────────────
  clamav:
    image: clamav/clamav:latest
    volumes:
      - clamav-data:/var/lib/clamav
    healthcheck:
      test: ["CMD", "clamdscan", "--ping", "1"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 120s
    networks:
      - monitoring-net
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "1"
    restart: unless-stopped

volumes:
  ollama-data:
  redis-data:
  postgres-data:
  clamav-data:

networks:
  frontend-net:
    driver: bridge
  backend-net:
    driver: bridge
  data-net:
    driver: bridge
    internal: true
  ai-net:
    driver: bridge
    internal: true
  monitoring-net:
    driver: bridge
    internal: true
```

> **Note:** Self-hosted Supabase services (Kong, GoTrue, PostgREST, Realtime, Storage) are omitted from the above for clarity. They are defined in the Supabase self-hosting Docker Compose and linked via the `data-net` network. See [Section 7](#7-self-hosted-supabase-strategy).

---

## 6. LLM & Embedding Migration

### 6.1 Model Selection Matrix

| Use Case | Cloud Model | On-Prem Recommendation | VRAM Required | Quality Delta |
|----------|-------------|----------------------|---------------|---------------|
| **Primary Chat** | GPT-4o | Llama 3.1 70B (Q4_K_M) | 40 GB | -10-15% on complex reasoning |
| **Secondary/Fast** | GPT-4o-mini | Llama 3.1 8B (Q8_0) | 8 GB | -5-10% on simple tasks |
| **Guardrails** | Llama 3.1 8B (Groq) | Llama 3.1 8B (Ollama) | 8 GB | Identical model |
| **Embeddings** | text-embedding-3-small (1536d) | nomic-embed-text (768d) | 2 GB | -5-8% on retrieval recall |
| **Embeddings (Alt)** | text-embedding-3-small (1536d) | mxbai-embed-large (1024d) | 3 GB | -3-5% on retrieval recall |
| **Vision/OCR** | GPT-4o Vision | LLaVA 1.6 34B | 20 GB | -15-20% on diagram reading |

### 6.2 Ollama Setup & Model Pre-Pull

```bash
# Pull required models (run after Ollama container starts)
# This is a one-time operation — models persist in ollama-data volume

# Primary chat model (~40GB download)
docker exec ollama ollama pull llama3.1:70b

# Secondary/fast model (~4.7GB download)
docker exec ollama ollama pull llama3.1:8b

# Embedding model (~274MB download)
docker exec ollama ollama pull nomic-embed-text

# Optional: Larger embedding model (~670MB download)
docker exec ollama ollama pull mxbai-embed-large

# Optional: Vision model (~20GB download)
docker exec ollama ollama pull llava:34b

# Verify models are loaded
docker exec ollama ollama list
```

### 6.3 Alternative: vLLM for High-Throughput

For organizations processing **>1000 documents/day**, vLLM provides significantly better throughput than Ollama through continuous batching:

```yaml
# vLLM service (alternative to Ollama for embeddings)
vllm:
  image: vllm/vllm-openai:latest
  command: >
    --model nomic-ai/nomic-embed-text-v1.5
    --dtype auto
    --max-model-len 8192
    --port 8001
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  networks:
    - ai-net
```

vLLM exposes an OpenAI-compatible API, so the backend code uses the same `openai` SDK with a different `base_url`:

```python
# backend/services/embeddings.py — vLLM compatibility
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",  # vLLM ignores API key
    base_url="http://vllm:8001/v1",
)

response = client.embeddings.create(
    model="nomic-ai/nomic-embed-text-v1.5",
    input=texts,
)
```

### 6.4 Embedding Dimension Migration

When switching from OpenAI (1536d) to a local model, **all existing embeddings become incompatible**. The migration process:

```mermaid
graph TD
    A["1. Stop ingestion workers"] --> B["2. Run dimension ALTER SQL"]
    B --> C["3. Mark all chunks for re-embedding"]
    C --> D["4. Start workers with new model"]
    D --> E["5. Re-embed all chunks (background)"]
    E --> F["6. Verify search quality"]
    F --> G["7. Resume normal operations"]
```

**Estimated re-embedding time** (based on chunk count):

| Chunk Count | Ollama (1× A100) | Ollama (1× RTX 4090) | CPU Only |
|------------|-------------------|----------------------|----------|
| 10,000 | ~5 min | ~8 min | ~2 hours |
| 100,000 | ~45 min | ~1.5 hours | ~20 hours |
| 1,000,000 | ~7 hours | ~15 hours | ~8 days |

### 6.5 TPM Regulation Adjustments

The current TPM (Tokens Per Minute) regulator in `backend/services/embeddings.py` uses quotas designed for OpenAI rate limits. On-premise, these limits should match your hardware throughput:

```python
# backend/core/config.py — On-premise TPM limits
QUOTA_LIMITS = {
    "enterprise_large": {
        "max_concurrent_jobs": 50,
        "max_storage_mb": 1_000_000,
        "max_daily_jobs": 10_000,
        "max_tpm": 1_000_000,  # Local inference is not rate-limited by API
    }
}
```

---

## 7. Self-Hosted Supabase Strategy

### 7.1 Why Self-Host Supabase (Not Replace It)

The decision to self-host Supabase rather than replace it with raw PostgreSQL + a separate auth system is driven by **code compatibility**:

| Approach | Code Changes | Risk | Timeline |
|----------|-------------|------|----------|
| **Self-Host Supabase** | ~0 lines (env vars only) | Low | 1-2 days |
| **Replace with raw PG + Keycloak** | ~5,000+ lines across 40+ files | Very High | 4-8 weeks |
| **Replace with raw PG + custom auth** | ~8,000+ lines across 50+ files | Extreme | 8-12 weeks |

The AxioHub codebase uses Supabase SDK methods throughout:
- **Backend**: `supabase.table("x").select().eq().execute()` — 79+ calls in `integrations.py` alone
- **Frontend**: `supabase.auth.getSession()`, `supabase.auth.exchangeCodeForSession()`
- **Realtime**: `supabase.channel("x").on("postgres_changes", ...)` for live quota updates
- **Storage**: `supabase.storage.from_("ephemeral-staging").create_signed_url()`

Self-hosted Supabase provides **identical APIs** — zero code changes.

### 7.2 Self-Hosted Supabase Components

Self-hosted Supabase is itself a Docker Compose stack with these services:

| Service | Image | Purpose | Port |
|---------|-------|---------|------|
| **Kong** | `kong:2.8.1` | API Gateway (routes to GoTrue, PostgREST, etc.) | 8000 |
| **GoTrue** | `supabase/gotrue` | Authentication (JWT, OAuth, email/password) | 9999 |
| **PostgREST** | `postgrest/postgrest` | Auto-generated REST API from PostgreSQL schema | 3000 |
| **Realtime** | `supabase/realtime` | PostgreSQL changes → WebSocket broadcasts | 4000 |
| **Storage** | `supabase/storage-api` | S3-compatible file storage (backed by MinIO or local FS) | 5000 |
| **Meta** | `supabase/postgres-meta` | PostgreSQL introspection for Supabase Studio | 8080 |
| **Studio** | `supabase/studio` | Web UI for database management (optional) | 3000 |

### 7.3 Supabase Self-Hosting Configuration

```bash
# Clone official self-hosting repo
git clone --depth 1 https://github.com/supabase/supabase
cd supabase/docker

# Copy and customize environment
cp .env.example .env

# Critical settings to configure:
# POSTGRES_PASSWORD=<strong-random-password>
# JWT_SECRET=<min-32-char-random-string>
# ANON_KEY=<generate-with-supabase-cli>
# SERVICE_ROLE_KEY=<generate-with-supabase-cli>
# SITE_URL=https://axiohub.your-domain.com
# API_EXTERNAL_URL=https://supabase.your-domain.com

# Start Supabase stack
docker compose up -d
```

### 7.4 pgvector Extension Setup

The self-hosted PostgreSQL image (`supabase/postgres:15.6.1.143`) includes pgvector. Verify and initialize:

```sql
-- Verify pgvector is available
CREATE EXTENSION IF NOT EXISTS vector;

-- Check version (should be >= 0.5.0 for HNSW)
SELECT extversion FROM pg_extension WHERE extname = 'vector';

-- Apply AxioHub migrations
-- Copy from: supabase/migrations/*.sql
-- These create: documents, chunks, user_integrations, ingestion_jobs, etc.
```

### 7.5 Migration from Cloud Supabase

```bash
# 1. Export data from Supabase Cloud
supabase db dump --db-url "postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres" \
  --data-only > data_dump.sql

# 2. Export schema (or use migration files)
supabase db dump --db-url "postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres" \
  --schema-only > schema_dump.sql

# 3. Import to self-hosted
psql "postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres" < schema_dump.sql
psql "postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres" < data_dump.sql

# 4. Re-create RLS policies
# Apply all migration files from supabase/migrations/ in order
for f in supabase/migrations/*.sql; do
  psql "postgresql://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres" < "$f"
done
```

**Important:** After migration, all user sessions are invalidated. Users must log in again with the new self-hosted GoTrue instance.

### 7.6 Cost Analysis

AxioHub on-premise ships as a **single Docker image** containing the full stack — FastAPI, Celery, Redis, PostgreSQL, and Supabase — all bundled together. The customer loads the image onto their own hardware and runs it. There is no cloud connection, no separate Supabase subscription, and no internet dependency. The deployment is fully offline and air-gapped. This means the Supabase cost question has a simple answer: it's included, at no additional cost.

#### Resource Footprint (Included in Image)

The bundled Supabase services (PostgreSQL, GoTrue, PostgREST, Realtime, Storage API, Meta, Kong, Analytics, Vector) consume resources within the same Docker environment as the rest of the AxioHub stack. There is nothing extra to install or provision — these containers are already part of the image.

| Resource | Supabase Containers | Notes |
|----------|-------------------|-------|
| RAM | ~2–4 GB | Shared with AxioHub stack |
| CPU | ~1–2 cores | Shared with AxioHub stack |
| Disk | ~10–20 GB base + data growth | PostgreSQL data, Storage objects, WAL |

> **Note:** These resources are part of the overall AxioHub deployment footprint. Verify your server meets the **total** stack requirements defined in Section 2.2 — Supabase does not require separate sizing.

#### Cloud vs. On-Prem Cost Comparison

| | **Cloud (Supabase SaaS)** | **On-Prem (Bundled in Image)** |
|---|---|---|
| Base cost | $25/month per project | $0 — included in image |
| Database storage | 8 GB included, $0.125/GB overage | Unlimited (limited only by hardware) |
| Auth (MAU) | 100K included, overage charges apply | Unlimited |
| File storage | 100 GB included, $0.021/GB overage | Unlimited (limited only by disk) |
| Bandwidth | 250 GB included, $0.09/GB overage | No metering — local network only |
| Realtime connections | 500 concurrent, $10/100K peak | Limited only by server RAM |
| Point-in-Time Recovery | $100/month add-on | Free (pg_basebackup + WAL archiving) |
| Internet requirement | **Required** — always connected | **None** — fully offline |
| Data residency | Data transits to/from Supabase Cloud | **Data never leaves your network** |
| Overage risk | Usage-based billing can spike | No overage fees — hardware is the only limit |

#### What On-Prem Eliminates

- **No SaaS subscription** — Supabase is bundled; there is no monthly fee for database services
- **No usage-based billing** — No per-GB storage charges, no bandwidth metering, no MAU limits
- **No data egress** — All data stays on the customer's network; nothing is transmitted externally
- **No cloud dependency** — The system operates fully offline with no internet requirement
- **No vendor lock-in for the database layer** — The bundled PostgreSQL instance is standard; data is portable

#### Maintenance

Supabase does not require separate maintenance. It runs as part of the unified Docker image alongside all other AxioHub services. The customer's operations team manages the Docker environment as a whole — starting, stopping, monitoring, and backing up the single deployment. When updates are available, they are delivered as a new image version that replaces the previous one, covering the entire stack including Supabase. There is no separate Supabase upgrade process.

---

## 8. SaaS Service Replacements

### 8.1 Email (Resend → Postfix/SMTP)

**Docker Service:**

```yaml
postfix:
  image: boky/postfix:latest
  environment:
    - ALLOWED_SENDER_DOMAINS=your-domain.com
    - HOSTNAME=mail.your-domain.com
  networks:
    - backend-net
  deploy:
    resources:
      limits:
        memory: 256M
        cpus: "0.25"
  restart: unless-stopped
```

**DNS Records Required:**
```
mail.your-domain.com    A       <server-ip>
your-domain.com         MX 10   mail.your-domain.com
your-domain.com         TXT     "v=spf1 ip4:<server-ip> -all"
```

**Code Change** — `backend/services/email.py`:

Add an SMTP transport alongside the existing Resend transport. The `EMAIL_PROVIDER` env var controls which transport is used. All email templates (Jinja2-based) remain unchanged.

### 8.2 Billing (Polar.sh → Disabled)

For on-premise, billing is handled via enterprise license agreements. The migration:

1. Set `ONPREMISE_MODE=true` in environment
2. All quota checks return enterprise-tier limits
3. Billing UI routes (`/dashboard/settings/billing`) show "Enterprise License" instead of subscription plans
4. Polar webhook endpoint (`/api/v1/webhooks/polar`) returns 404

**No code removal needed** — the feature is gated by environment variable.

### 8.3 Monitoring & Observability

#### Self-Hosted Sentry

```bash
# Official Sentry self-hosting
git clone https://github.com/getsentry/self-hosted.git
cd self-hosted
./install.sh  # Interactive setup — creates admin user
docker compose up -d
```

**Resource Requirements:** Sentry is resource-intensive:
- Minimum: 4 CPU, 8 GB RAM, 20 GB disk
- Recommended: 8 CPU, 16 GB RAM, 50 GB disk
- Services: PostgreSQL, Redis, Kafka, ClickHouse, Snuba, Web, Worker, Cron

#### Prometheus + Grafana (Lightweight Alternative)

If Sentry's footprint is too large, use Prometheus + Grafana instead:

```yaml
prometheus:
  image: prom/prometheus:latest
  volumes:
    - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    - prometheus-data:/prometheus
  networks:
    - monitoring-net
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: "0.5"

grafana:
  image: grafana/grafana:latest
  volumes:
    - grafana-data:/var/lib/grafana
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
  networks:
    - monitoring-net
    - backend-net
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: "0.5"
```

The backend already exposes Prometheus metrics via `prometheus-client==0.20.0`.

### 8.4 Proxy (Vercel + Railway → Nginx)

| Current | On-Premise |
|---------|-----------|
| Vercel Edge (proxy.ts) | Nginx + Next.js standalone server |
| Railway (FastAPI) | Docker container behind Nginx |
| Vercel CDN | Nginx static file caching |
| Vercel Preview URLs | Not applicable |

The `proxy.ts` middleware continues to work identically in the Next.js standalone server — it's framework-level, not deployment-platform-level.

---

## 9. Setup & Deployment Procedure

### 9.1 Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Ubuntu 22.04 LTS / RHEL 9 | Ubuntu 24.04 LTS |
| **Docker** | 24.0+ | 25.0+ |
| **Docker Compose** | 2.20+ | 2.24+ |
| **NVIDIA Driver** | 535+ (for GPU inference) | 545+ |
| **NVIDIA Container Toolkit** | 1.14+ | Latest |
| **Disk Space** | 100 GB (SSD) | 500 GB (NVMe) |
| **Network** | Static IP, DNS A record | Static IP + wildcard cert |

### 9.2 Single-Command Deployment

```bash
#!/bin/bash
# deploy-axiohub.sh — Single-command on-premise deployment

set -euo pipefail

echo "══════════════════════════════════════════════"
echo "  AxioHub On-Premise Deployment"
echo "══════════════════════════════════════════════"

# ─── Step 1: Validate Prerequisites ──────────────
echo "▸ Checking prerequisites..."
command -v docker >/dev/null 2>&1 || { echo "ERROR: Docker not installed"; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "ERROR: Docker Compose not installed"; exit 1; }

# Check for GPU (optional)
if command -v nvidia-smi >/dev/null 2>&1; then
    echo "  ✓ NVIDIA GPU detected: $(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)"
    GPU_AVAILABLE=true
else
    echo "  ⚠ No NVIDIA GPU detected — will use CPU-only models"
    GPU_AVAILABLE=false
fi

# ─── Step 2: Generate Secrets ────────────────────
echo "▸ Generating secrets..."
if [ ! -f .env.onpremise ]; then
    cp .env.onpremise.example .env.onpremise

    # Generate encryption keys
    CHUNK_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    JWT_SECRET=$(openssl rand -hex 32)
    PG_PASSWORD=$(openssl rand -base64 32)

    sed -i "s|CHUNK_ENCRYPTION_KEY=.*|CHUNK_ENCRYPTION_KEY=${CHUNK_KEY}|" .env.onpremise
    sed -i "s|ENCRYPTION_KEY=.*|ENCRYPTION_KEY=${ENCRYPTION_KEY}|" .env.onpremise
    sed -i "s|SUPABASE_JWT_SECRET=.*|SUPABASE_JWT_SECRET=${JWT_SECRET}|" .env.onpremise
    sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG_PASSWORD}|" .env.onpremise

    echo "  ✓ Secrets generated in .env.onpremise"
    echo "  ⚠ CRITICAL: Back up .env.onpremise to a secure location!"
else
    echo "  ✓ Using existing .env.onpremise"
fi

# ─── Step 3: Pull & Build Images ────────────────
echo "▸ Building containers..."
docker compose -f docker-compose.onpremise.yml --env-file .env.onpremise build

# ─── Step 4: Start Infrastructure ────────────────
echo "▸ Starting infrastructure services..."
docker compose -f docker-compose.onpremise.yml --env-file .env.onpremise up -d \
    postgres redis clamav

echo "  Waiting for PostgreSQL to be ready..."
until docker compose -f docker-compose.onpremise.yml exec postgres pg_isready -U postgres; do
    sleep 2
done

# ─── Step 5: Initialize Database ────────────────
echo "▸ Applying database migrations..."
for migration in supabase/migrations/*.sql; do
    docker compose -f docker-compose.onpremise.yml exec -T postgres \
        psql -U postgres -d postgres < "$migration"
done

# ─── Step 6: Start Supabase Stack ───────────────
echo "▸ Starting Supabase services..."
# (Assumes self-hosted Supabase compose is merged or linked)
docker compose -f docker-compose.onpremise.yml --env-file .env.onpremise up -d \
    supabase-kong supabase-auth supabase-rest supabase-realtime supabase-storage

# ─── Step 7: Start Ollama & Pull Models ─────────
echo "▸ Starting Ollama..."
docker compose -f docker-compose.onpremise.yml --env-file .env.onpremise up -d ollama

echo "  Pulling AI models (this may take 30-60 minutes on first run)..."
docker compose -f docker-compose.onpremise.yml exec ollama ollama pull llama3.1:8b
docker compose -f docker-compose.onpremise.yml exec ollama ollama pull nomic-embed-text

if [ "$GPU_AVAILABLE" = true ]; then
    echo "  Pulling large model for GPU..."
    docker compose -f docker-compose.onpremise.yml exec ollama ollama pull llama3.1:70b
fi

# ─── Step 8: Start Application Stack ────────────
echo "▸ Starting application services..."
docker compose -f docker-compose.onpremise.yml --env-file .env.onpremise up -d \
    api worker beat flower nextjs nginx

# ─── Step 9: Verify Health ──────────────────────
echo "▸ Verifying health..."
sleep 15

HEALTH=$(curl -sf http://localhost:8000/health || echo "FAILED")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "  ✓ Backend API: healthy"
else
    echo "  ✗ Backend API: $HEALTH"
fi

READY=$(curl -sf http://localhost:8000/health/ready || echo "FAILED")
if echo "$READY" | grep -q "ready"; then
    echo "  ✓ Readiness probe: ready"
else
    echo "  ✗ Readiness probe: $READY"
fi

FRONTEND=$(curl -sf -o /dev/null -w "%{http_code}" http://localhost:3000 || echo "000")
if [ "$FRONTEND" = "200" ]; then
    echo "  ✓ Frontend: running"
else
    echo "  ✗ Frontend: HTTP $FRONTEND"
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  AxioHub is ready!"
echo "  URL: https://axiohub.your-domain.com"
echo "  Flower: https://axiohub.your-domain.com/flower/"
echo "══════════════════════════════════════════════"
```

### 9.3 Post-Deployment Steps

1. **Create admin user** via Supabase Studio or CLI:
   ```bash
   curl -X POST http://localhost:8000/auth/v1/signup \
     -H "apikey: ${SUPABASE_ANON_KEY}" \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@your-domain.com", "password": "secure-password"}'
   ```

2. **Configure OAuth providers** (if internet access is available):
   - Google Cloud Console → Create OAuth credentials → Set redirect URI
   - Microsoft Azure → App Registration → Configure redirect
   - Each provider requires setting `*_CLIENT_ID` and `*_CLIENT_SECRET` in `.env.onpremise`

3. **Set up TLS certificates**:
   ```bash
   # Option A: Let's Encrypt (if internet access available)
   certbot certonly --standalone -d axiohub.your-domain.com

   # Option B: Self-signed (air-gapped)
   openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout nginx/ssl/privkey.pem \
     -out nginx/ssl/fullchain.pem \
     -subj "/CN=axiohub.your-domain.com"
   ```

4. **Verify encryption key** — this is the most critical step:
   ```bash
   # Test that the encryption key can encrypt/decrypt
   docker compose -f docker-compose.onpremise.yml exec api \
     python -c "
   from cryptography.fernet import Fernet
   import os
   key = os.environ['CHUNK_ENCRYPTION_KEY']
   f = Fernet(key.encode())
   assert f.decrypt(f.encrypt(b'test')) == b'test'
   print('Encryption key verified OK')
   "
   ```

---

## 10. Hardware Requirements & Sizing Guide

### 10.1 Deployment Profiles

#### Profile A: Small Team (1-10 users, <50k documents)

| Component | Specification |
|-----------|--------------|
| **CPU** | 16 cores (AMD EPYC 7313 or Intel Xeon Silver 4314) |
| **RAM** | 64 GB DDR4 ECC |
| **GPU** | 1× NVIDIA RTX 4090 (24 GB VRAM) |
| **Storage** | 1 TB NVMe SSD (OS + Docker) + 2 TB SATA SSD (Data) |
| **Network** | 1 Gbps |
| **LLM Model** | Llama 3.1 8B (Q8_0) — fits in 24 GB VRAM |
| **Embedding Model** | nomic-embed-text (768d) |
| **Est. Cost** | ~$5,000-8,000 |

**Resource Allocation:**

| Service | Memory | CPU |
|---------|--------|-----|
| PostgreSQL | 8 GB | 2 |
| Redis | 1 GB | 0.5 |
| Ollama | 24 GB | 4 |
| FastAPI | 4 GB | 2 |
| Celery Workers (×2) | 8 GB | 4 |
| Next.js | 1 GB | 1 |
| Nginx | 256 MB | 0.25 |
| ClamAV | 2 GB | 0.5 |
| Other (Beat, Flower) | 1 GB | 0.5 |
| **Total** | **~50 GB** | **~15** |

#### Profile B: Medium Organization (10-100 users, <500k documents)

| Component | Specification |
|-----------|--------------|
| **CPU** | 32 cores (AMD EPYC 7543 or Intel Xeon Gold 6330) |
| **RAM** | 128 GB DDR4 ECC |
| **GPU** | 1× NVIDIA A100 80 GB or 2× RTX 4090 |
| **Storage** | 2 TB NVMe SSD (OS + Docker) + 4 TB SATA SSD (Data) |
| **Network** | 10 Gbps |
| **LLM Model** | Llama 3.1 70B (Q4_K_M) — fits in 40 GB VRAM |
| **Embedding Model** | mxbai-embed-large (1024d) |
| **Est. Cost** | ~$15,000-25,000 |

#### Profile C: Enterprise (100+ users, 1M+ documents)

| Component | Specification |
|-----------|--------------|
| **CPU** | 64 cores (AMD EPYC 9554 or Intel Xeon Platinum 8480+) |
| **RAM** | 256 GB DDR5 ECC |
| **GPU** | 2× NVIDIA A100 80 GB or 4× RTX 4090 |
| **Storage** | 4 TB NVMe SSD (OS) + RAID-10 array (Data) |
| **Network** | 25 Gbps |
| **LLM Model** | Llama 3.1 70B (FP16) or Qwen 2.5 72B |
| **Embedding Model** | mxbai-embed-large (1024d) with vLLM |
| **Est. Cost** | ~$50,000-80,000 |

### 10.2 Disk Space Calculations

| Data Category | Formula | Example (100k docs) |
|--------------|---------|---------------------|
| **Raw Documents** | Avg 500 KB × doc count | 50 GB |
| **PostgreSQL Data** | ~2 KB per chunk × chunks | 20 GB (10M chunks) |
| **pgvector Index** | ~4 bytes × dimensions × chunks | 30 GB (768d × 10M) |
| **Redis** | ~1 KB per active job | 1 GB |
| **Ollama Models** | 4-40 GB per model | 52 GB (8B + 70B + embed) |
| **ClamAV Definitions** | Fixed | 1 GB |
| **Docker Images** | All services | 15 GB |
| **Logs** | ~100 MB/day | 36 GB/year |
| **Overhead (25%)** | Safety margin | 51 GB |
| **Total** | | **~256 GB** |

### 10.3 GPU vs. CPU-Only Trade-offs

| Metric | GPU (RTX 4090) | CPU Only (16 cores) |
|--------|---------------|---------------------|
| **Chat Response (8B model)** | 40-60 tokens/sec | 3-5 tokens/sec |
| **Chat Response (70B model)** | 15-25 tokens/sec | Not feasible |
| **Embedding (1000 chunks)** | ~30 sec | ~20 min |
| **Daily Ingestion Capacity** | ~50,000 docs | ~2,000 docs |
| **Power Consumption** | +350W | Baseline |
| **Cost Delta** | +$1,500-2,000 | — |

**Recommendation:** GPU is strongly recommended for any deployment expecting more than 10 concurrent users or >1,000 documents/day.

---

## 11. Security Considerations

### 11.1 Encryption at Rest (Ghost Protocol)

The AxioHub Ghost Protocol provides military-grade data protection. All encryption features work identically on-premise:

| Feature | File | Behavior |
|---------|------|----------|
| **Chunk Encryption** | `backend/core/security.py` | AES-256 (Fernet) encryption of all document chunks |
| **Token Encryption** | `backend/services/oauth_token_manager.py` | OAuth tokens encrypted before DB storage |
| **Secure Wipe** | `backend/services/secure_cleanup.py` | 3-pass DoD 5220.22-M deletion (0x00 → 0xFF → Random) |
| **SmartBuffer** | `backend/services/secure_cleanup.py` | RAM < 10MB, spills to encrypted temp files |
| **Key Rotation** | `backend/core/security.py` | Comma-separated key list, first key for encryption |

**Critical On-Premise Requirements:**

```env
# These MUST be set in production — backend refuses to start without them
CHUNK_ENCRYPTION_KEY=<Fernet-key>        # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
STRICT_ENCRYPTION_MODE=true               # Crash on unencrypted reads
SECURE_WIPE_PASSES=3                      # DoD 5220.22-M compliance
SECURE_WIPE_VERIFY=true                   # Verify wipe success
MALWARE_SCAN_FAIL_CLOSED=true             # Reject uploads if ClamAV unavailable
```

### 11.2 Network Security

```
┌─────────────────────────────────────────────────────────┐
│                    Host Firewall                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Port 443 (HTTPS) ──── Nginx ──┬── Frontend      │  │
│  │  Port 80 (→ 443)               ├── Backend API    │  │
│  │                                 └── Flower (IP ACL)│  │
│  └───────────────────────────────────────────────────┘  │
│                                                          │
│  ┌── Internal Only (no external access) ──────────────┐ │
│  │  PostgreSQL :5432                                   │ │
│  │  Redis :6379                                        │ │
│  │  Ollama :11434                                      │ │
│  │  ClamAV :3310                                       │ │
│  │  Supabase services :3000, :4000, :5000, :8000, :9999│ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Firewall Rules (UFW example):**
```bash
# Allow only HTTPS and SSH
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirect to HTTPS)
ufw allow 443/tcp   # HTTPS
ufw enable
```

### 11.3 TLS Configuration

- **Minimum:** TLS 1.2
- **Recommended:** TLS 1.3 only
- **Certificate:** Let's Encrypt (auto-renew) or internal CA for air-gapped
- **HSTS:** `max-age=31536000; includeSubDomains; preload` (already configured in `next.config.ts`)

### 11.4 Authentication Security

| Feature | Implementation | File |
|---------|---------------|------|
| **JWT Validation** | HS256 with `SUPABASE_JWT_SECRET` | `backend/core/security.py` |
| **OAuth State** | Required CSRF token — not optional | `backend/api/v1/integrations.py` |
| **Open Redirect Protection** | `next` param validated: starts `/`, not `//`, no `:` | `frontend-new/app/auth/callback/route.ts` |
| **SSRF Protection** | `getaddrinfo()` checks all DNS records | `backend/connectors/web.py` |
| **Rate Limiting** | 50 req/min default via slowapi | `backend/main.py` |
| **Request Size Limit** | 100 MB via Content-Length check | `backend/main.py` |
| **CORS** | Whitelisted origins only (no wildcards in production) | `backend/main.py` |

### 11.5 Air-Gap Considerations

For fully air-gapped deployments:

1. **Pre-pull all Docker images** on an internet-connected machine, save as tarballs:
   ```bash
   docker save ollama/ollama:latest | gzip > ollama.tar.gz
   docker save redis:7-alpine | gzip > redis.tar.gz
   # ... repeat for all images
   ```

2. **Pre-pull Ollama models** and export:
   ```bash
   # On internet-connected machine
   ollama pull llama3.1:70b
   # Copy ~/.ollama/models/ to air-gapped machine
   ```

3. **ClamAV virus definitions** — download `main.cvd`, `daily.cvd`, `bytecode.cvd` from https://www.clamav.net/downloads and copy to the volume

4. **No OAuth connectors** — only SFTP, S3 (pointing to local MinIO), Web Crawler (internal sites), and File Upload will work

5. **Self-signed TLS certificates** — use internal CA for trust chain

---

## 12. Quality Trade-offs: Cloud vs. On-Premise

### 12.1 LLM Response Quality

| Benchmark | GPT-4o (Cloud) | Llama 3.1 70B (On-Prem) | Delta |
|-----------|---------------|--------------------------|-------|
| **MMLU** | 88.7% | 86.0% | -2.7% |
| **HumanEval** | 90.2% | 80.5% | -9.7% |
| **MT-Bench** | 9.3/10 | 8.8/10 | -5.4% |
| **RAG-specific QA** | Baseline | -10-15% | Context-dependent |
| **Instruction Following** | Excellent | Very Good | Noticeable on complex chains |
| **Multilingual** | 50+ languages | 8 languages (best) | Significant for non-English |

**Mitigation Strategies:**
- Use Qwen 2.5 72B for better multilingual support
- Increase `num_ctx` (context window) to compensate for reduced reasoning
- Add few-shot examples to system prompts for complex tasks
- Consider a hybrid approach: local for simple queries, cloud fallback for complex ones

### 12.2 Embedding Quality (Retrieval Recall)

| Benchmark | text-embedding-3-small (Cloud) | nomic-embed-text (On-Prem) | mxbai-embed-large (On-Prem) |
|-----------|-------------------------------|---------------------------|----------------------------|
| **MTEB Average** | 62.3 | 60.1 | 64.7 |
| **Retrieval (BEIR)** | 51.7 | 48.2 | 54.3 |
| **Clustering** | 44.8 | 41.2 | 43.9 |
| **Dimensions** | 1536 | 768 | 1024 |
| **Speed (1000 docs, GPU)** | ~3s (API) | ~5s (local) | ~8s (local) |

**Recommendation:** Use `mxbai-embed-large` for best on-premise retrieval quality — it actually **exceeds** OpenAI's model on several benchmarks while using fewer dimensions.

### 12.3 Operational Differences

| Aspect | Cloud | On-Premise |
|--------|-------|-----------|
| **Uptime** | 99.9% (vendor SLA) | Depends on your infrastructure |
| **Scaling** | Automatic | Manual (add hardware) |
| **Maintenance** | Vendor-managed | Self-managed (OS patches, Docker updates) |
| **Backup** | Supabase PITR (7-day) | Must configure pg_dump cron jobs |
| **Model Updates** | Automatic (OpenAI deploys new versions) | Manual (pull new Ollama models) |
| **Disaster Recovery** | Cloud replication | Must implement yourself |
| **Support** | Vendor support tickets | Internal team or consultant |

### 12.4 Cost Comparison (Annual, 50 Users, 100k Documents)

| Category | Cloud | On-Premise | Savings |
|----------|-------|-----------|---------|
| **Compute** | Railway Pro ($600/yr) | Server amortized ($2,000/yr) | -$1,400 |
| **Database** | Supabase Pro ($300/yr) | Included in server | +$300 |
| **LLM API** | OpenAI (~$6,000/yr at moderate usage) | Electricity (~$500/yr) | +$5,500 |
| **Embedding API** | OpenAI (~$1,200/yr) | Included | +$1,200 |
| **Email** | Resend Pro ($240/yr) | Postfix (free) | +$240 |
| **Monitoring** | Sentry Team ($312/yr) | Self-hosted (free) | +$312 |
| **Frontend** | Vercel Pro ($240/yr) | Included | +$240 |
| **Staff Time** | Low (managed services) | High (1-2 hrs/week maintenance) | -$5,000 |
| **Total** | **~$8,892/yr** | **~$7,500/yr** | **~$1,400/yr** |

> **Note:** The primary savings come from eliminating OpenAI API costs. For low-usage deployments (<$2,000/yr OpenAI), cloud may be more cost-effective when accounting for maintenance staff time.

---

## 13. Testing & Verification Plan

### 13.1 Smoke Test Matrix

| # | Test | Command | Expected Result |
|---|------|---------|-----------------|
| 1 | Backend health | `curl http://localhost:8000/health` | `{"status": "healthy"}` |
| 2 | Readiness probe | `curl http://localhost:8000/health/ready` | `{"status": "ready", "checks": {"database": true, "celery": true, "memory": true}}` |
| 3 | Ollama connectivity | `curl http://ollama:11434/api/tags` | JSON list of loaded models |
| 4 | Redis connectivity | `docker exec redis redis-cli ping` | `PONG` |
| 5 | PostgreSQL connectivity | `docker exec postgres pg_isready -U postgres` | Exit code 0 |
| 6 | pgvector extension | `docker exec postgres psql -U postgres -c "SELECT extversion FROM pg_extension WHERE extname='vector'"` | Version string |
| 7 | Frontend loads | `curl -o /dev/null -sw "%{http_code}" http://localhost:3000` | `200` |
| 8 | Nginx HTTPS | `curl -k https://axiohub.your-domain.com/` | `200` |
| 9 | Supabase Auth | `curl http://supabase-kong:8000/auth/v1/health` | `200` |
| 10 | ClamAV | `docker exec clamav clamdscan --ping 1` | `PONG` |

### 13.2 Functional Test Plan

| Category | Test | Verification |
|----------|------|-------------|
| **Auth** | Register new user via email | User created, JWT issued, redirect to dashboard |
| **Auth** | Login with existing user | Session established, `proxy.ts` passes through |
| **Upload** | Upload a PDF file (<10 MB) | Presigned URL generated, file stored, ingestion job created |
| **Ingestion** | Full pipeline: upload → parse → chunk → embed → index | Celery task chain completes, chunks appear in DB with embeddings |
| **Search** | Semantic search for uploaded content | Relevant chunks returned with cosine similarity > 0.35 |
| **Chat** | Ask a question about uploaded content | LLM generates response citing uploaded document |
| **Chat Streaming** | Verify streaming response | Tokens arrive incrementally (SSE) |
| **Guardrails** | Ask off-topic question | Guardrail model rejects with "not relevant" response |
| **Encryption** | Verify chunk encryption | `SELECT embedding IS NOT NULL, content LIKE 'gAAAA%' FROM chunks LIMIT 1` (Fernet prefix) |
| **Malware Scan** | Upload EICAR test file | Upload rejected with malware detection message |
| **Email** | Invite team member | Email sent via SMTP, received in inbox |
| **Connectors** | SFTP integration | Files listed, selected files ingested |
| **Connectors** | S3 (MinIO) integration | Buckets listed, files ingested |
| **Connectors** | Web crawler | Single page crawled, content indexed |
| **Quota** | Exceed file limit | Upload rejected with quota error |

### 13.3 Performance Benchmarks

Run after deployment to establish baselines:

```bash
# Embedding throughput
time docker exec api python -c "
from services.embeddings import generate_embeddings_batch_sync
texts = ['Sample document text for benchmarking.'] * 100
results = generate_embeddings_batch_sync(texts, 'test-user')
print(f'Embedded {len(results)} texts')
"

# Chat response latency
time curl -X POST http://localhost:8000/api/v1/chat/message \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": "test", "message": "What is 2+2?", "stream": false}'

# Search latency
time curl -X POST http://localhost:8000/api/v1/search \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"query": "test search", "limit": 10}'
```

### 13.4 Load Testing

```bash
# Install k6 for load testing
# Test: 50 concurrent users searching
k6 run --vus 50 --duration 60s - <<'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export default function() {
  const res = http.post('http://localhost:8000/api/v1/search', JSON.stringify({
    query: 'test document',
    limit: 10
  }), {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${__ENV.TOKEN}`
    }
  });
  check(res, { 'status is 200': (r) => r.status === 200 });
  sleep(1);
}
EOF
```

**Target Performance:**

| Metric | Target (Profile A) | Target (Profile B) | Target (Profile C) |
|--------|-------------------|--------------------|--------------------|
| Search P95 latency | < 500ms | < 200ms | < 100ms |
| Chat first-token | < 2s | < 1s | < 500ms |
| Embedding throughput | 100 chunks/min | 500 chunks/min | 2000 chunks/min |
| Concurrent users | 5 | 25 | 100+ |

---

## 14. Project Timeline & Milestones

### 14.1 Phase Overview

```mermaid
gantt
    title AxioHub On-Premise Refactoring Timeline
    dateFormat YYYY-MM-DD
    axisFormat %b %d

    section Phase 1: Core Infrastructure
    Self-hosted Supabase setup       :p1a, 2026-03-01, 5d
    Docker Compose (on-prem)         :p1b, 2026-03-01, 5d
    Nginx reverse proxy              :p1c, 2026-03-03, 3d
    Frontend Dockerfile              :p1d, 2026-03-04, 2d
    Integration testing              :p1e, after p1a, 3d

    section Phase 2: LLM Migration
    Ollama integration               :p2a, 2026-03-10, 5d
    Embedding provider swap          :p2b, 2026-03-10, 5d
    Guardrail model swap             :p2c, 2026-03-12, 2d
    Dimension migration SQL          :p2d, after p2b, 2d
    Quality benchmarking             :p2e, after p2d, 3d

    section Phase 3: SaaS Replacements
    SMTP email transport             :p3a, 2026-03-19, 3d
    On-premise billing mode          :p3b, 2026-03-19, 2d
    Self-hosted Sentry               :p3c, 2026-03-21, 3d
    Remove Bright Data dependency    :p3d, 2026-03-21, 1d

    section Phase 4: Hardening
    Security audit                   :p4a, 2026-03-26, 3d
    Load testing                     :p4b, 2026-03-26, 3d
    Air-gap testing                  :p4c, 2026-03-28, 2d
    Documentation & runbooks         :p4d, after p4c, 3d

    section Phase 5: Deployment
    Staging deployment               :p5a, 2026-04-02, 3d
    UAT (User Acceptance Testing)    :p5b, after p5a, 5d
    Production deployment            :p5c, after p5b, 2d
    Hypercare support                :p5d, after p5c, 10d
```

### 14.2 Milestone Definitions

| Milestone | Date | Deliverable | Exit Criteria |
|-----------|------|-------------|---------------|
| **M1: Infrastructure Ready** | Week 2 | Self-hosted Supabase + Docker stack running | All smoke tests pass |
| **M2: AI Stack Ready** | Week 4 | Local LLM + embeddings working | Chat + search functional with local models |
| **M3: Feature Complete** | Week 5 | All SaaS replacements done | No external API calls in network audit |
| **M4: Security Hardened** | Week 6 | Pen test complete, load test passed | All security checklist items green |
| **M5: Production Ready** | Week 8 | UAT complete, runbooks written | Stakeholder sign-off |

### 14.3 Resource Requirements

| Role | FTE | Duration | Skills Required |
|------|-----|----------|----------------|
| **Backend Engineer** | 1.0 | 8 weeks | Python, FastAPI, Docker, Celery |
| **DevOps Engineer** | 0.5 | 8 weeks | Docker Compose, Nginx, Linux, GPU drivers |
| **Frontend Engineer** | 0.25 | 2 weeks | Next.js, environment configuration |
| **QA Engineer** | 0.5 | 4 weeks | API testing, load testing, security testing |
| **Project Manager** | 0.25 | 8 weeks | Stakeholder coordination, risk management |

---

## 15. Risk Register

| # | Risk | Probability | Impact | Mitigation | Owner |
|---|------|-------------|--------|-----------|-------|
| **R1** | LLM quality insufficient for enterprise use | Medium | High | Benchmark before commitment; keep cloud fallback option | Backend Lead |
| **R2** | Embedding dimension migration corrupts data | Low | Critical | Full database backup before migration; test on staging first | Backend Lead |
| **R3** | Self-hosted Supabase compatibility issues | Low | High | Test all 79+ SDK calls against self-hosted instance | Backend Lead |
| **R4** | GPU driver compatibility (NVIDIA Container Toolkit) | Medium | Medium | Test on target hardware before procurement | DevOps |
| **R5** | Ollama model loading exceeds available VRAM | Medium | High | Profile VRAM usage; use quantized models (Q4_K_M) | DevOps |
| **R6** | ClamAV virus definitions stale in air-gap | Medium | Medium | Scheduled manual updates; or network-connected update proxy | Security |
| **R7** | PostgreSQL performance regression (self-hosted vs. Supabase Cloud) | Low | Medium | Tune `shared_buffers`, `work_mem`, `effective_cache_size` | DevOps |
| **R8** | Email deliverability issues (self-hosted Postfix) | Medium | Low | Configure SPF, DKIM, DMARC; or use external SMTP relay | Backend Lead |
| **R9** | Encryption key loss | Low | **Critical** | Documented backup procedure; key stored in 2+ secure locations | Security |
| **R10** | Supabase self-hosted version drift | Medium | Medium | Pin Docker image versions; quarterly update schedule | DevOps |
| **R11** | OAuth connectors non-functional in air-gap | High | Medium | Expected — document which connectors require internet; provide SFTP/S3/Upload as alternatives | PM |
| **R12** | Insufficient disk space for model storage | Medium | Medium | Monitor `/root/.ollama` volume; alert at 80% | DevOps |

---

## 16. Appendices

### Appendix A: Environment Variable Reference (On-Premise)

```env
# ═══════════════════════════════════════════════════════════════
# AxioHub On-Premise Environment Configuration
# ═══════════════════════════════════════════════════════════════

# ─── Mode ──────────────────────────────────────────────────────
ENVIRONMENT=production
ONPREMISE_MODE=true
DEFAULT_PLAN=enterprise_large

# ─── Supabase (Self-Hosted) ───────────────────────────────────
SUPABASE_URL=http://supabase-kong:8000
SUPABASE_SECRET_KEY=<service-role-key>
SUPABASE_JWT_SECRET=<jwt-secret-min-32-chars>
SUPABASE_PUBLISHABLE_KEY=<anon-key>
NEXT_PUBLIC_SUPABASE_URL=https://supabase.your-domain.com
NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon-key>

# ─── PostgreSQL ───────────────────────────────────────────────
POSTGRES_PASSWORD=<strong-random-password>
INGESTION_DATABASE_URL=postgresql://ingestion_role:<password>@postgres:5432/postgres

# ─── AI / LLM (Ollama) ───────────────────────────────────────
OLLAMA_BASE_URL=http://ollama:11434
PRIMARY_MODEL_PROVIDER=ollama
PRIMARY_MODEL_NAME=llama3.1:70b
SECONDARY_MODEL_PROVIDER=ollama
SECONDARY_MODEL_NAME=llama3.1:8b
GUARDRAIL_MODEL_PROVIDER=ollama
GUARDRAIL_MODEL_NAME=llama3.1:8b
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text

# OpenAI key not required for on-premise (set to empty)
OPENAI_API_KEY=
GROQ_API_KEY=

# ─── Redis ────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ─── Encryption (Ghost Protocol) ─────────────────────────────
CHUNK_ENCRYPTION_KEY=<fernet-key>
ENCRYPTION_KEY=<fernet-key>
STRICT_ENCRYPTION_MODE=true
SECURE_WIPE_PASSES=3
SECURE_WIPE_PATTERN=dod_5220_22_m
SECURE_WIPE_VERIFY=true

# ─── Email (SMTP) ────────────────────────────────────────────
EMAIL_PROVIDER=smtp
SMTP_HOST=postfix
SMTP_PORT=25
SMTP_USE_TLS=false
EMAILS_FROM_EMAIL=noreply@your-domain.com

# ─── Malware Scanning ────────────────────────────────────────
MALWARE_SCAN_FAIL_CLOSED=true
SKIP_FRESHCLAM=false

# ─── Monitoring ───────────────────────────────────────────────
SENTRY_DSN=https://<key>@sentry.your-domain.com/<project>
NEXT_PUBLIC_SENTRY_DSN=https://<key>@sentry.your-domain.com/<project>

# ─── Application ─────────────────────────────────────────────
APP_URL=https://axiohub.your-domain.com
ALLOWED_ORIGINS=https://axiohub.your-domain.com
RATE_LIMIT_DEFAULT=50/minute

# ─── Billing (Disabled) ──────────────────────────────────────
POLAR_ACCESS_TOKEN=
POLAR_ORGANIZATION_ID=
POLAR_WEBHOOK_SECRET=

# ─── YouTube Proxy (Disabled) ────────────────────────────────
BRIGHTDATA_API_KEY=
YOUTUBE_DIRECT_FALLBACK=true

# ─── Celery Workers ──────────────────────────────────────────
CELERY_WORKER_CONCURRENCY=2
CELERY_WORKER_MAX_MEMORY_PER_CHILD=3000000
CELERY_TASK_SOFT_TIME_LIMIT=900
CELERY_TASK_TIME_LIMIT=1200

# ─── Resource Limits ─────────────────────────────────────────
MAX_FILE_SIZE=104857600
MAX_STRUCTURED_FILE_SIZE=52428800
EMBEDDING_BATCH_SIZE=10
MAX_CHUNK_BATCH_SIZE=100

# ─── Connector Concurrency ───────────────────────────────────
CONNECTOR_CONCURRENCY_DEFAULT=2
CONNECTOR_CONCURRENCY_S3=4
CONNECTOR_CONCURRENCY_SFTP=2

# ─── Flower (Monitoring) ─────────────────────────────────────
FLOWER_USER=admin
FLOWER_PASSWORD=<strong-password>

# ─── Quota Overrides (On-Premise Enterprise) ─────────────────
LIMITS_ENTERPRISE_FILES=999999
LIMITS_ENTERPRISE_SCOPES=999999
LIMITS_ENTERPRISE_MB=999999
LIMITS_ENTERPRISE_LLM_TOKENS=999999999
```

### Appendix B: File Reference Map

| Purpose | File Path | Lines | On-Prem Changes |
|---------|-----------|-------|-----------------|
| **LLM Factory** | `backend/services/llm_factory.py` | ~200 | Add Ollama provider |
| **Embeddings** | `backend/services/embeddings.py` | ~375 | Add Ollama embedding support |
| **Embedding Factory** | `backend/core/embeddings.py` | ~175 | Add Ollama tier |
| **Configuration** | `backend/core/config.py` | ~397 | Add OLLAMA_*, SMTP_*, ONPREMISE_* vars |
| **Email Service** | `backend/services/email.py` | ~500 | Add SMTP transport |
| **Subscription** | `backend/services/subscription.py` | ~300 | Add on-premise mode bypass |
| **Billing API** | `backend/api/v1/billing.py` | ~200 | On-premise mode check |
| **Webhooks** | `backend/api/v1/webhooks.py` | ~150 | Disable Polar webhooks |
| **DB Client** | `backend/core/db.py` | ~222 | No changes (env vars only) |
| **Security** | `backend/core/security.py` | ~400 | No changes |
| **Main App** | `backend/main.py` | ~422 | No changes |
| **Celery App** | `backend/core/celery_app.py` | ~224 | No changes |
| **Web Connector** | `backend/connectors/web.py` | ~1,209 | No changes (Bright Data auto-disabled) |
| **Frontend Client** | `frontend-new/lib/supabase/client.ts` | ~50 | No changes (env vars only) |
| **Frontend Server** | `frontend-new/lib/supabase/server.ts` | ~50 | No changes (env vars only) |
| **Frontend Proxy** | `frontend-new/proxy.ts` | ~100 | No changes |
| **Next.js Config** | `frontend-new/next.config.ts` | ~200 | Update rewrite target |
| **Docker Compose** | `docker-compose.yml` | ~120 | New file: `docker-compose.onpremise.yml` |
| **Docker Compose Prod** | `docker-compose.prod.yml` | ~100 | Reference for production settings |
| **Backend Dockerfile** | `docker/backend.Dockerfile` | ~80 | No changes |
| **Worker Dockerfile** | `backend/Dockerfile.worker` | ~70 | No changes |
| **Migrations** | `supabase/migrations/*.sql` | ~20 files | Apply to self-hosted PG |
| **Health Endpoints** | `backend/api/v1/health.py` | ~100 | No changes |

### Appendix C: Model Comparison (Detailed)

#### Chat Models

| Model | Parameters | Quantization | VRAM | Tokens/sec (A100) | Tokens/sec (4090) | MMLU | MT-Bench |
|-------|-----------|-------------|------|-------------------|-------------------|------|----------|
| GPT-4o | Unknown | N/A | Cloud | Cloud | Cloud | 88.7 | 9.3 |
| Llama 3.1 70B | 70B | Q4_K_M | 40 GB | 25 t/s | 15 t/s | 86.0 | 8.8 |
| Llama 3.1 70B | 70B | Q8_0 | 75 GB | 20 t/s | N/A | 86.0 | 8.8 |
| Qwen 2.5 72B | 72B | Q4_K_M | 42 GB | 22 t/s | 13 t/s | 86.1 | 8.9 |
| Llama 3.1 8B | 8B | Q8_0 | 8 GB | 80 t/s | 60 t/s | 73.0 | 8.0 |
| Mistral 7B v0.3 | 7B | Q8_0 | 8 GB | 85 t/s | 65 t/s | 62.5 | 7.6 |

#### Embedding Models

| Model | Dimensions | Size | MTEB Avg | Retrieval (BEIR) | Speed (GPU, 1k docs) |
|-------|-----------|------|----------|------------------|---------------------|
| text-embedding-3-small | 1536 | Cloud | 62.3 | 51.7 | ~3s (API latency) |
| text-embedding-3-large | 3072 | Cloud | 64.6 | 55.4 | ~5s (API latency) |
| nomic-embed-text | 768 | 274 MB | 60.1 | 48.2 | ~5s |
| mxbai-embed-large | 1024 | 670 MB | 64.7 | 54.3 | ~8s |
| bge-small-en-v1.5 | 384 | 134 MB | 51.7 | 42.1 | ~2s (CPU OK) |
| bge-large-en-v1.5 | 1024 | 1.34 GB | 64.2 | 54.3 | ~10s |

### Appendix D: Troubleshooting Guide

| Symptom | Likely Cause | Resolution |
|---------|-------------|------------|
| Backend returns 503 | PostgreSQL not ready | Check `docker logs postgres`, verify `pg_isready` |
| "Model not found" from Ollama | Model not pulled | Run `docker exec ollama ollama pull <model>` |
| Embeddings fail with dimension error | Vector index mismatch | Run dimension migration SQL (Section 6.4) |
| Supabase Auth 500 | GoTrue misconfigured | Check `GOTRUE_JWT_SECRET` matches `SUPABASE_JWT_SECRET` |
| Frontend shows blank page | Env vars missing | Verify `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` |
| Nginx 502 Bad Gateway | Backend not started | Check `docker logs api`, verify health endpoint |
| ClamAV timeout on startup | Virus definitions downloading | Wait 2-3 minutes; check `docker logs clamav` |
| Chat response very slow | Ollama loading model | First request loads model into VRAM; subsequent requests are fast |
| "Encryption key not set" | Missing `CHUNK_ENCRYPTION_KEY` | Generate and set in `.env.onpremise` |
| OAuth callback fails | Redirect URI mismatch | Update `*_REDIRECT_URI` to match new domain |
| Redis connection refused | Redis not on correct network | Verify both `data-net` and `backend-net` connectivity |
| Worker OOM killed | `CELERY_WORKER_MAX_MEMORY_PER_CHILD` too high | Lower to 2GB; reduce `CELERY_WORKER_CONCURRENCY` |

### Appendix E: Backup & Recovery (On-Premise)

```bash
# ─── Daily PostgreSQL Backup ─────────────────────────
# Add to crontab: 0 2 * * * /opt/axiohub/backup.sh

#!/bin/bash
BACKUP_DIR=/opt/axiohub/backups
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL dump
docker exec postgres pg_dump -U postgres \
  --format=custom \
  --compress=9 \
  postgres > "${BACKUP_DIR}/pg_${DATE}.dump"

# Redis RDB snapshot
docker exec redis redis-cli BGSAVE
sleep 5
docker cp redis:/data/dump.rdb "${BACKUP_DIR}/redis_${DATE}.rdb"

# Retention: keep 30 days
find "${BACKUP_DIR}" -name "*.dump" -mtime +30 -delete
find "${BACKUP_DIR}" -name "*.rdb" -mtime +30 -delete

echo "Backup complete: pg_${DATE}.dump, redis_${DATE}.rdb"
```

```bash
# ─── Restore from Backup ─────────────────────────────
# Stop application services first
docker compose -f docker-compose.onpremise.yml stop api worker beat flower nextjs

# Restore PostgreSQL
docker exec -i postgres pg_restore \
  --dbname=postgres \
  --clean \
  --if-exists \
  --no-owner \
  -U postgres < "${BACKUP_DIR}/pg_${DATE}.dump"

# Restart application
docker compose -f docker-compose.onpremise.yml up -d api worker beat flower nextjs
```

### Appendix F: Maintenance Checklist

| Task | Frequency | Command | Notes |
|------|-----------|---------|-------|
| **Update ClamAV definitions** | Daily (if internet) | `docker exec clamav freshclam` | Air-gap: manual `*.cvd` copy |
| **PostgreSQL VACUUM** | Weekly | `docker exec postgres psql -U postgres -c "VACUUM ANALYZE"` | Reclaims dead tuples |
| **Docker log rotation** | Automatic | Configured via `json-file` driver | Max 50MB × 5 files |
| **Ollama model updates** | Monthly | `docker exec ollama ollama pull <model>` | Check release notes first |
| **Docker image updates** | Monthly | `docker compose pull && docker compose up -d` | Test in staging first |
| **OS security patches** | Monthly | `apt update && apt upgrade -y` | Schedule maintenance window |
| **TLS certificate renewal** | Before expiry | `certbot renew` or manual | Let's Encrypt auto-renews |
| **Disk space check** | Weekly | `df -h /var/lib/docker` | Alert at 80% |
| **Backup verification** | Monthly | Test restore to staging | Verify encryption key works |

---

> **Document Revision History**
>
> | Version | Date | Author | Changes |
> |---------|------|--------|---------|
> | 1.0 | February 2026 | AxioHub Engineering | Initial release |
