# Connector and Unified Ingestion Protocol

## Overview
The ingestion pipeline enforces a strict SourceDocument contract and a scope-aware chain of custody. Each connector must stamp a canonical `scope_id` at source, and the worker refuses documents without it.

Key contracts and entry points:
- SourceDocument schema: `backend/connectors/enhanced.py`
- Scope URI builder: `backend/core/scopes.py`
- Unified ingestion orchestration: `backend/worker/tasks.py`
- Connector registry: `backend/connectors/registry.py`

## Canonical Scope IDs
`backend/core/scopes.py` defines canonical formats:
- GitHub: `github://{org}/{repo}@{branch}`
- S3: `s3://{bucket}/{prefix}`
- Box: `box://folder/{folder_id}:{folder_name}`
- Dropbox: `dropbox://{namespace_id}/{path}`
- Google Drive: `gdrive://{drive_id}/{folder_id}:{name}`
- Notion: `notion://{workspace_id}/{page_id}:{title}`
- Web: `web://{domain}`
- File upload: `file_upload://{storage_path}`

## Connector Implementations (Scope Stamping)
Current scope-aware connectors that explicitly call `build_scope_uri`:
- GitHub: `backend/connectors/github.py` in `_fetch_single_file` and folder expansion.
- S3: `backend/connectors/s3.py` in `fetch_documents_sync`.
- Box: `backend/connectors/box.py` in `_build_source_document`.

Other connectors (Drive, Notion, Dropbox, OneDrive, SharePoint, SFTP, Web, File Upload) currently emit metadata without an explicit `scope_id`. The worker enforces `scope_id` and will fail fast if missing, so these connectors must be updated to comply before production use.

Connector registry:
- `backend/connectors/registry.py` lists supported connectors and capabilities.

## Unified Ingestion Pipeline (Worker)
The ingestion flow is driven by Celery tasks in `backend/worker/tasks.py`:
1. `unified_ingest_task` resolves connector and fetches `SourceDocument` items.
2. Each document becomes an `ingestion_file_status` row and is serialized for Celery.
3. `process_file_task` decodes content, enforces `scope_id` and `organization_id`, then parses content with `DocumentProcessorFactory` in `backend/services/parsers.py`.
4. Parsed chunks are embedded via `backend/services/embeddings.py` and stored in `documents` and `document_chunks`.
5. `finalize_job_task` groups documents by scope and triggers identity synthesis.

Worker enforcement points:
- `process_file_task` in `backend/worker/tasks.py` raises if `scope_id` or `organization_id` is missing.
- `unified_ingest_task` sets `scope_id` in task payload and expects connectors to provide it.

Mermaid: ingestion to vector flow
```mermaid
flowchart LR
  C[Connector] --> SD[SourceDocument]
  SD --> UI[unified_ingest_task]
  UI --> PF[process_file_task]
  PF --> PARSE[DocumentProcessorFactory]
  PARSE --> EMB[embeddings]
  EMB --> DOCS[(documents)]
  EMB --> CH[(document_chunks)]
  PF --> FINAL[finalize_job_task]
  FINAL --> ID[scope identities]
```

## Identity Synthesis (Finalize Job)
Identity synthesis runs after job completion:
- `finalize_job_task` gathers successfully indexed documents and groups by `scope_id`.
- `synthesize_and_save_identity` builds a summary and tree and persists to `scope_identities`.
- Database-level locking is handled by RPC `upsert_scope_identity_document` (SELECT FOR UPDATE) defined in `supabase/migrations/20260201000000_llm_quota_and_identity_lock.sql`.

Identity safeguards in `backend/services/scope_identity.py`:
- `MAX_DOCS_FOR_IDENTITY = 1000` (sampling for large scopes)
- `MAX_TREE_DEPTH = 3` (tree depth cap)
- `MAX_SUMMARY_CHARS = 2000` (summary size cap)
- Mandatory `scope_id`, `organization_id`, and `user_id` arguments (missing values raise ValueError)

## Connector Summary (Current Code)
Connector list (see `backend/connectors/`):
- GitHub, S3, Box (scope stamping implemented)
- Google Drive, Notion, Dropbox, OneDrive, SharePoint, SFTP, Web, File Upload (scope stamping pending)

## Connector Flows (Sequence Diagrams)
Each diagram includes connection, discovery/listing, ingestion, and identity synthesis stages.

### File Upload
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant S as Storage
  participant Q as Celery
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Select file
  W->>A: POST /api/v1/uploads/upload-url
  A->>D: quota and admission checks
  A->>S: create_signed_upload_url
  S-->>W: signed URL
  W->>S: PUT file
  W->>A: POST /api/v1/uploads/file/reference
  A->>D: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>S: download staged file
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for file uploads is pending
```

### GitHub
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant G as GitHub
  participant S as Supabase
  participant Q as Celery
  participant C as GitHubConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect GitHub
  W->>A: POST /api/v1/integrations/github/exchange
  A->>G: OAuth token exchange
  A->>G: GET /user
  A->>S: upsert user_integrations (encrypted token)
  W->>A: GET /api/v1/integrations/github/repos
  A->>C: get_available_repositories
  C->>G: list repos
  W->>A: POST /api/v1/integrations/github/repos/select
  A->>S: update selected_repositories
  W->>A: POST /api/v1/integrations/github/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>G: list tree + fetch blobs
  C-->>C: build_scope_uri -> metadata.scope_id
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
```

### Box
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant B as Box
  participant S as Supabase
  participant Q as Celery
  participant C as BoxConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect Box
  W->>A: POST /api/v1/integrations/box/exchange
  A->>B: OAuth token exchange
  A->>B: GET /users/me
  A->>S: upsert user_integrations (encrypted tokens)
  W->>A: GET /api/v1/integrations/box/items
  A->>C: list_files
  C->>B: list folders/files
  W->>A: POST /api/v1/integrations/box/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>B: download file content
  C-->>C: build_scope_uri -> metadata.scope_id
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
```

### Google Drive
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant G as Google
  participant S as Supabase
  participant Q as Celery
  participant C as DriveConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect Google Drive
  W->>A: POST /api/v1/integrations/google/exchange
  A->>G: OAuth token exchange
  A->>S: upsert user_integrations (encrypted tokens)
  W->>A: GET /api/v1/integrations/google_drive/items
  A->>C: list_files
  C->>G: list folders/files
  W->>A: POST /api/v1/integrations/google_drive/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>G: download file content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for Google Drive is pending
```

### Notion
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant N as Notion
  participant S as Supabase
  participant Q as Celery
  participant C as NotionConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect Notion
  W->>A: POST /api/v1/integrations/notion/exchange
  A->>N: OAuth token exchange
  A->>S: upsert user_integrations (encrypted token)
  A->>N: POST /v1/search (auto-ingest discovery)
  A->>S: insert ingestion_jobs (auto)
  A->>Q: dispatch unified_ingest_task (auto)
  W->>A: GET /api/v1/integrations/notion/items
  A->>C: list_files
  C->>N: list pages/databases
  W->>A: POST /api/v1/integrations/notion/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>N: fetch page content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for Notion is pending
```

### Dropbox
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant Dp as Dropbox
  participant S as Supabase
  participant Q as Celery
  participant C as DropboxConnector
  participant P as Parser
  participant E as Embeddings
  participant DB as DB
  U->>W: Connect Dropbox
  W->>A: POST /api/v1/integrations/dropbox/exchange
  A->>Dp: OAuth token exchange
  A->>Dp: /users/get_current_account
  A->>S: upsert user_integrations (encrypted tokens + namespace_id)
  W->>A: GET /api/v1/integrations/dropbox/items
  A->>C: list_files
  C->>Dp: list folders/files
  W->>A: POST /api/v1/integrations/dropbox/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>Dp: download file content
  Q->>P: parse
  P->>E: embed
  E->>DB: insert documents + chunks
  Q->>DB: finalize_job_task
  DB->>DB: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for Dropbox is pending
```

### OneDrive
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant M as Microsoft
  participant S as Supabase
  participant Q as Celery
  participant C as OneDriveConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect OneDrive
  W->>A: POST /api/v1/integrations/microsoft/exchange
  A->>M: OAuth token exchange (Graph)
  A->>M: GET /me/drive
  A->>S: upsert user_integrations
  W->>A: GET /api/v1/integrations/onedrive/items
  A->>C: list_files
  C->>M: list items
  W->>A: POST /api/v1/integrations/onedrive/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>M: download file content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for OneDrive is pending
```

### SharePoint
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant M as Microsoft
  participant S as Supabase
  participant Q as Celery
  participant C as SharePointConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect SharePoint
  W->>A: POST /api/v1/integrations/microsoft/exchange
  A->>M: OAuth token exchange (Graph)
  A->>M: GET /sites/root or /sites/{site_id}
  A->>S: upsert user_integrations
  W->>A: GET /api/v1/integrations/sharepoint/items
  A->>C: list_files
  C->>M: list items
  W->>A: POST /api/v1/integrations/sharepoint/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync (integration_id)
  C->>M: download file content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for SharePoint is pending
```

### SFTP
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant S as Supabase
  participant Q as Celery
  participant C as SFTPConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect SFTP
  W->>A: POST /api/v1/integrations/sftp/connect
  A->>C: verify_connection
  A->>S: upsert user_integrations (encrypted creds)
  W->>A: GET /api/v1/integrations/sftp/items
  A->>C: list_files
  C->>C: open SFTP session
  W->>A: POST /api/v1/integrations/sftp/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync
  C->>C: download file content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for SFTP is pending
```

### S3
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant S3 as AmazonS3
  participant S as Supabase
  participant Q as Celery
  participant C as S3Connector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Connect S3
  W->>A: POST /api/v1/integrations/s3/connect
  A->>C: verify_access (ListBucket/GetObject)
  A->>S: upsert user_integrations (encrypted creds)
  W->>A: GET /api/v1/integrations/s3/items
  A->>C: list_files
  C->>S3: list objects
  W->>A: POST /api/v1/integrations/s3/ingest
  A->>S: insert ingestion_jobs
  A->>Q: dispatch unified_ingest_task
  Q->>C: fetch_documents_sync
  C->>S3: download object
  C-->>C: build_scope_uri -> metadata.scope_id
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
```

### Web
```mermaid
sequenceDiagram
  participant U as User
  participant W as WebApp
  participant A as API
  participant Q as Celery
  participant C as WebConnector
  participant P as Parser
  participant E as Embeddings
  participant D as DB
  U->>W: Start crawl
  W->>A: POST /api/v1/integrations/web/crawl
  A->>A: validate URL + feature gate
  A->>Q: queue_web_crawl (task + job)
  Q->>C: fetch URLs
  C->>C: scrape content
  Q->>P: parse
  P->>E: embed
  E->>D: insert documents + chunks
  Q->>D: finalize_job_task
  D->>D: synthesize_and_save_identity + upsert_scope_identity_document
  Note over Q: scope_id stamping for Web is pending
```

## Recommendations for New Connectors
- Always call `build_scope_uri` with connector-specific metadata.
- Write `scope_id` into `SourceDocument.metadata` at creation time.
