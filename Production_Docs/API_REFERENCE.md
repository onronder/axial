# API Reference (Production)

This reference documents all mounted API endpoints in `backend/main.py`. It is code-aligned and grouped by router.

## Base URLs
- Direct backend: `/api/v1`
- Frontend proxy: `/api/py` (Next.js proxy used by the web app)

## Auth and Access Control
All non-public endpoints require a Supabase JWT bearer token.

Common dependencies:
- `validate_team_access`: blocks access when team membership or owner subscription is invalid.
- `require_editor`: requires editor/admin (owners allowed); viewers blocked from write actions.
- `require_admin`: requires team owner or admin role.

## Error Format
Most endpoints return `HTTPException` with `detail`:
- Simple errors: `{"detail": "message"}`
- Structured errors (via `raise_http_error`):
  - `{"detail": {"error": "CODE", "message": "text", "details": {...}}}`

## Health
### GET `/health`
- Auth: none
- Response: JSON with `status`, `checks` for db/redis, and `health` self link.
- Side effects: DB and Redis probe.

Note: `backend/api/v1/health.py` defines additional health endpoints (`/health/ready`, `/health/live`, `/health/startup`) but they are not mounted in `backend/main.py`.

## Chat and Conversations
### GET `/api/v1/conversations`
- Auth: `validate_team_access`
- Response: list of `ConversationResponse`
  - `id`, `title`, `created_at`, `updated_at`

### POST `/api/v1/conversations`
- Auth: `validate_team_access`
- Body: `ConversationCreate`
  - `title` (string, max 200)
- Response: `ConversationResponse`
- Side effects: inserts row in `conversations`.

### GET `/api/v1/conversations/{conversation_id}`
- Auth: `validate_team_access`
- Response: `ConversationResponse`
- Errors: 404 if not found or not owned.

### PATCH `/api/v1/conversations/{conversation_id}`
- Auth: `validate_team_access`
- Body: `ConversationUpdate`
  - `title` (string, max 200)
- Response: `ConversationResponse`

### DELETE `/api/v1/conversations/{conversation_id}`
- Auth: `validate_team_access`
- Response: `{status: "success", deleted_id: conversation_id}`
- Side effects: deletes conversation and messages (cascade) and writes audit log.

### GET `/api/v1/conversations/{conversation_id}/messages`
- Auth: `validate_team_access`
- Response: list of `MessageResponse`
  - `id`, `role`, `content`, `sources` (array), `created_at`

### POST `/api/v1/chat`
- Auth: `validate_team_access`
- Body: `ChatRequest`
  - `query` (string, 1..20000)
  - `conversation_id` (string or null)
  - `history` (array of `{role, content}`)
  - `model` (tier alias or model name)
  - `stream` (bool)
  - `scope_id` (string or null, `__all__` allowed)
- Response (non-stream): `ChatResponse`
  - `answer`, `sources` (array), `conversation_id`, `message_id`, `scope_context`
- Response (clarification): HTTP 300 with `ClarificationResponse`
  - `action`, `message`, `candidates` (`id`, `summary`, `type`), `query`
- Response (stream): SSE with `token`, `sources`, `scope_context`, `done`, `error`
- Side effects: persists chat messages, records LLM usage, performs scope analysis.

## Streaming
### POST `/api/v1/chat/stream`
- Auth: `validate_team_access`
- Body: `ChatRequest` (stream forced true)
  - `query` (string, 1..20000)
  - `conversation_id` (string or null)
  - `history` (array of `{role, content}`)
  - `model` (tier alias or model name)
  - `scope_id` (string or null, `__all__` allowed)
- Response: SSE events `sources`, `token`, `done`, `error`
- Notes: Same guardrails as `/api/v1/chat` (dominance, quotas, failover).

## Search
### POST `/api/v1/search`
- Auth: `validate_team_access`
- Body: `SearchRequest`
  - `query` (string, 1..10000)
  - `limit` (1..50)
  - `threshold` (0..1)
  - `scope_ids` (optional list of scope URIs)
  - `include_scope_analysis` (bool)
- Response: `SearchResponse`
  - `results` (array of documents from RPC)
  - `scope_analysis` (optional) including `classification`, `primary_scope_id`, `dominance_ratio`, `total_docs`, `scoped_docs`, `distribution` (list of scope stats)

## Uploads (Presigned Upload Flow)
Base prefix: `/api/v1/uploads`

### POST `/api/v1/uploads/check-duplicates`
- Auth: `require_editor`
- Body: `DuplicateCheckRequest`
  - `content_hash` (SHA-256 hex, 64 chars)
  - `filename`
  - `file_size`
- Response: `DuplicateCheckResponse`
  - `is_duplicate`, `existing_document`, `action_required`

### POST `/api/v1/uploads/upload-url`
- Auth: `require_editor`
- Body: `UploadUrlRequest`
  - `filename`, `file_type`, `file_size`, `content_hash` (optional), `force_overwrite` (bool)
- Response: `UploadUrlResponse`
  - `upload_url`, `storage_path`, `expires_in`
- Side effects: admission/quota checks, generates presigned upload URL.

### POST `/api/v1/uploads/file/reference`
- Auth: `require_editor`
- Body: `FileReferenceRequest`
  - `storage_path`, `filename`, `file_size`, `metadata`
- Response: `IngestResponse` (status, doc_id)
- Side effects: creates ingestion job and dispatches `unified_ingest_task`.

## Documents
### GET `/api/v1/documents/stats`
- Auth: `validate_team_access`
- Response: `DocumentStatsDTO`
  - `total_documents`, `last_updated`

### GET `/api/v1/documents`
- Auth: `validate_team_access`
- Query: `limit`, `offset`, `q`, `include_failed` (bool)
- Response: list of `DocumentDTO`
  - `id`, `title`, `source_type`, `source_url`, `created_at`, `status`, `indexing_status`, `size`, `file_size_bytes`, `metadata`
- Side effects: none; optionally merges failed ingestion records.

### DELETE `/api/v1/documents`
- Auth: `require_editor`
- Body: `BulkDeleteRequest`
  - `document_ids` (optional list)
  - `source_type` (optional)
- Response: `{status, deleted, failed}`
- Side effects: deletes documents via cleanup service, recalculates usage, logs audit.

### DELETE `/api/v1/documents/{doc_id}`
- Auth: `require_editor`
- Response: `{status, id}`
- Side effects: deletes document via cleanup service and logs audit.

### PATCH `/api/v1/documents/{document_id}`
- Auth: `require_editor`
- Body: `DocumentUpdate` with `title`, `description`, `tags`
- Response: `DocumentDTO`
- Side effects: updates metadata and logs audit.

### GET `/api/v1/documents/{document_id}/chunks`
- Auth: `validate_team_access`
- Query: `limit`, `offset`
- Response: list of `DocumentChunkDTO`
  - `id`, `document_id`, `content`, `chunk_index`, `metadata`

## Jobs
### GET `/api/v1/jobs/active`
- Auth: `validate_team_access`
- Response: `IngestionJobResponse` or `null`

### GET `/api/v1/jobs/{job_id}`
- Auth: `validate_team_access`
- Response: `IngestionJobResponse`

### GET `/api/v1/jobs`
- Auth: `validate_team_access`
- Query: `limit`
- Response: list of `IngestionJobResponse`

### POST `/api/v1/jobs/{job_id}/cancel`
- Auth: `require_editor`
- Response: `{status, job_id, message}`
- Side effects: cancels job, revokes Celery task, updates file statuses.

### POST `/api/v1/jobs/files/{file_status_id}/retry`
- Auth: `require_editor`
- Response: `{status, file_status_id, retry_count, message}`
- Side effects: resets file status and marks job as processing.

### GET `/api/v1/jobs/{job_id}/files`
- Auth: `validate_team_access`
- Response: list of `ingestion_file_status` rows.

### POST `/api/v1/jobs/{job_id}/retry`
- Auth: `require_editor`
- Response: `{status, job_id, files_queued, files_skipped, message}`
- Side effects: resets failed files and updates job status.

## Integrations
### GET `/api/v1/integrations/available`
- Auth: `validate_team_access`
- Response: list of `ConnectorDefinitionOut`
  - `id`, `type`, `name`, `description`, `icon_path`, `category`, `is_active`

### GET `/api/v1/integrations/status`
- Auth: `validate_team_access`
- Response: list of `UserIntegrationOut`
  - `id`, `connector_definition_id`, `connector_type`, `connector_name`, `connector_icon`, `category`, `connected`, `last_sync_at`

### POST `/api/v1/integrations/google/exchange`
- Auth: `require_editor`
- Body: `ExchangeRequest` (`code`)
- Response: `{status, provider, integration_id}`
- Side effects: OAuth code exchange, stores encrypted tokens in `user_integrations`.

### POST `/api/v1/integrations/notion/exchange`
- Auth: `require_editor`
- Body: `ExchangeRequest` (`code`)
- Response: `{status, provider, integration_id, workspace_name}`
- Side effects: OAuth exchange + optional auto-ingestion of accessible pages.

### POST `/api/v1/integrations/microsoft/exchange`
- Auth: `require_editor`
- Body: `MicrosoftExchangeRequest`
  - `code`, `target_type` (`onedrive` or `sharepoint`), `site_id` (optional), `code_verifier` (optional)
- Response: `{status, provider, integration_id}`
- Side effects: OAuth exchange and Graph API validation, stores tokens.

### POST `/api/v1/integrations/dropbox/exchange`
- Auth: `require_editor`
- Body: `DropboxExchangeRequest`
  - `code`, `root_path` (optional)
- Response: `{status, provider, integration_id, is_team_account, display_name}`
- Side effects: OAuth exchange, resolves namespace/team metadata, stores tokens.

### POST `/api/v1/integrations/github/exchange`
- Auth: `require_editor`
- Body: `GitHubExchangeRequest` (`code`)
- Response: `{status, provider, integration_id, github_login, github_name}`
- Side effects: OAuth exchange, stores token, captures user metadata.

### GET `/api/v1/integrations/github/repos`
- Auth: `validate_team_access`
- Response: `{repositories: [...], total}`
- Side effects: calls GitHub API via connector using stored access token.

### POST `/api/v1/integrations/github/repos/select`
- Auth: `require_editor`
- Body: `GitHubRepoSelectionRequest`
  - `selected_repositories` array of `{full_name, branch?, enabled?}`
- Response: `{status, integration_id, repos_selected}`
- Side effects: stores selected repos in integration credentials.

### POST `/api/v1/integrations/box/exchange`
- Auth: `require_editor`
- Body: `BoxExchangeRequest` (`code`)
- Response: `{status, provider, integration_id, box_login, box_name, is_enterprise}`
- Side effects: OAuth exchange, stores rotating refresh tokens.

### POST `/api/v1/integrations/sftp/connect`
- Auth: `require_editor`
- Body: `SFTPConnectRequest`
  - `host`, `port`, `username`, `password?`, `private_key?`, `root_path`
- Response: `{status, provider, integration_id}`
- Side effects: verifies SFTP connectivity and stores encrypted credentials.

### POST `/api/v1/integrations/s3/connect`
- Auth: `require_editor` + `get_effective_plan`
- Body: `S3ConnectRequest`
  - `access_key_id`, `secret_access_key`, `region`, `bucket_name`, `prefix`
- Response: `{status, provider, integration_id, bucket, region, prefix}`
- Side effects: enterprise gate check, verifies access, stores encrypted IAM credentials.

### GET `/api/v1/integrations/{provider}/status`
- Auth: `validate_team_access`
- Response: `{connected: bool}`

### DELETE `/api/v1/integrations/{provider}`
- Auth: `require_editor`
- Response: `{status, provider, cleanup: {documents_deleted, jobs_deleted}}`
- Side effects: revokes tokens when possible and deletes documents/jobs/sync_state.

### GET `/api/v1/integrations/{provider}/items`
- Auth: `validate_team_access`
- Query: `parent_id` (optional)
- Response: list of items `{id, name, type, mimeType, size, parent_id, web_view_url}`
- Side effects: fetches remote items via connector.

### POST `/api/v1/integrations/web/crawl`
- Auth: `require_editor`
- Body: `WebCrawlRequest`
  - `url`, `crawl_type`, `max_depth`, `respect_robots`, `max_pages`, `allow_subdomains`
- Response: `{status, crawl_id, task_id, job_id?, root_url}`
- Side effects: queues a crawl and creates ingestion job.

### DELETE `/api/v1/integrations/web/crawl/{config_id}`
- Auth: `require_editor`
- Response: `{status, message, config_id}`
- Side effects: cancels crawl task and deletes configuration.

### POST `/api/v1/integrations/{provider}/ingest`
- Auth: `require_editor`
- Body: `IngestRequest`
  - `item_ids` (array, max 100)
- Response: `{status, message, task_id, job_id}` or crawl payload for `web`
- Side effects: creates ingestion job and dispatches `unified_ingest_task` (or queues web crawl).

### POST `/api/v1/integrations/{integration_id}/sync`
- Auth: `require_editor`
- Response: `{status, job_id, message}`
- Side effects: creates job and runs background sync via `run_background_sync`.

### GET `/api/v1/integrations/{integration_id}/sync-history`
- Auth: `validate_team_access`
- Query: `limit`
- Response: `{integration_id, provider, history}` (rows from `sync_state`).

## Team
### GET `/api/v1/team`
- Auth: `validate_team_access`
- Response: `TeamResponse`

### PATCH `/api/v1/team`
- Auth: `validate_team_access`
- Body: `TeamUpdate` (`name?`, `slug?`)
- Response: `TeamResponse`

### DELETE `/api/v1/team`
- Auth: `validate_team_access`
- Query: `purge_data` (bool, default true)
- Response: `{status, message}`
- Side effects: optional org purge via `purge_organization` RPC, deletes team and members.

### GET `/api/v1/team/effective-plan`
- Auth: `validate_team_access`
- Response: `EffectivePlanResponse`
  - `plan`, `inherited`, `team_id`, `team_name`

### GET `/api/v1/team/members`
- Auth: `validate_team_access`
- Response: list of `TeamMemberResponse`

### GET `/api/v1/team/stats`
- Auth: `validate_team_access`
- Response: `TeamStatsResponse`
  - `total_seats`, `active_members`, `pending_invites`

### POST `/api/v1/team/invite`
- Auth: `validate_team_access`
- Body: `InviteRequest` (`email`, `role`, `name?`)
- Response: `InviteResponse`

### POST `/api/v1/team/bulk-invite`
- Auth: `validate_team_access`
- Body: CSV file upload
- Response: `BulkInviteResponse`

### POST `/api/v1/team/members`
- Auth: `validate_team_access`
- Body: `TeamMemberCreate` (`email`, `role`, `name?`)
- Response: `TeamMemberResponse`

### PATCH `/api/v1/team/members/{member_id}`
- Auth: `validate_team_access`
- Body: `TeamMemberUpdate` (`name?`, `role?`, `status?`)
- Response: `TeamMemberResponse`

### DELETE `/api/v1/team/members/{member_id}`
- Auth: `validate_team_access`
- Response: `{status, message}`

### POST `/api/v1/team/members/{member_id}/resend`
- Auth: `validate_team_access`
- Response: `{status, message}`

### POST `/api/v1/team/accept`
- Auth: `validate_team_access`
- Body: `AcceptInviteRequest` (`token`)
- Response: `AcceptInviteResponse`

## Billing
Base prefix: `/api/v1/billing`

### GET `/api/v1/billing/plans`
- Auth: `validate_team_access`
- Response: list of `PlanResponse`
  - `id`, `name`, `description`, `price_amount`, `price_currency`, `interval`, `type`, `features`, `button_text`, `button_variant`, `popular`

### POST `/api/v1/billing/checkout`
- Auth: `validate_team_access`
- Body: `CheckoutRequest` (`plan`, `interval`)
- Response: `{url}`

### POST `/api/v1/billing/portal`
- Auth: `validate_team_access`
- Response: `PortalResponse` (`url`)

### GET `/api/v1/billing/subscription`
- Auth: `validate_team_access`
- Response: `SubscriptionDetailResponse` or `null`

### POST `/api/v1/billing/subscription/cancel`
- Auth: `validate_team_access`
- Response: `{status, message, subscription_id}`

### GET `/api/v1/billing/invoices`
- Auth: `validate_team_access`
- Response: list of `InvoiceResponse`

### GET `/api/v1/billing/invoices/{order_id}/download`
- Auth: `validate_team_access`
- Response: `{url}` or `{status: "generating", message}`

### POST `/api/v1/billing/fix-customer-id`
- Auth: `validate_team_access`
- Response: `{status, customer_id?, message?, response?}`

### POST `/api/v1/billing/enterprise-inquiry`
- Auth: `validate_team_access`
- Body: `EnterpriseInquiryRequest` (`name`, `email`, `company`, `message`, `team_size`)
- Response: `{status, message}`

## Usage
### GET `/api/v1/usage`
- Auth: `validate_team_access`
- Response: `UsageResponse`
  - `plan`, `files`, `storage`, `features`, `model_tier`, `subscription_status`

### GET `/api/v1/plans`
- Auth: `validate_team_access`
- Response: `PlansResponse` with plan limits from `QUOTA_LIMITS`.

## Settings
### GET `/api/v1/settings/profile`
- Auth: `validate_team_access`
- Response: `ProfileResponse`
  - `id`, `user_id`, `first_name`, `last_name`, `plan`, `theme`, `has_team`, `role`, `created_at`, `updated_at`

### PATCH `/api/v1/settings/profile`
- Auth: `validate_team_access`
- Body: `ProfileUpdate` (`first_name?`, `last_name?`, `theme?`)
- Response: `ProfileResponse`

### DELETE `/api/v1/settings/profile/me`
- Auth: `validate_team_access`
- Response: `{message, details}`
- Side effects: full account deletion (vectors, storage, DB, auth).

### POST `/api/v1/settings/profile/me/anonymize`
- Auth: `validate_team_access`
- Response: `{message, details}`

### GET `/api/v1/settings/notifications`
- Auth: `validate_team_access`
- Response: list of `NotificationSettingResponse`

### PATCH `/api/v1/settings/notifications`
- Auth: `validate_team_access`
- Body: `NotificationSettingUpdate` (`setting_key`, `enabled`)
- Response: `NotificationSettingResponse`

### DELETE `/api/v1/settings/notifications`
- Auth: `validate_team_access`
- Response: `{status, message, deleted_count}`

## Notifications
### GET `/api/v1/notifications`
- Auth: `validate_team_access`
- Query: `limit`, `offset`, `unread_only`
- Response: `NotificationListResponse`

### GET `/api/v1/notifications/unread-count`
- Auth: `validate_team_access`
- Response: `UnreadCountResponse`

### PATCH `/api/v1/notifications/{notification_id}/read`
- Auth: `validate_team_access`
- Response: `NotificationResponse`

### PATCH `/api/v1/notifications/read-all`
- Auth: `validate_team_access`
- Response: `{status, message}`

### DELETE `/api/v1/notifications/all`
- Auth: `validate_team_access`
- Response: `{status, message}`

### DELETE `/api/v1/notifications/{notification_id}`
- Auth: `validate_team_access`
- Response: `{status, message}`

## Admin
Base prefix: `/api/v1/admin`

### GET `/api/v1/admin/audit-logs`
- Auth: `require_admin`
- Query: `limit`, `offset`, `action?`, `resource_type?`, `from_date?`, `to_date?`
- Response: `AuditLogListResponse`

### GET `/api/v1/admin/audit-logs/actions`
- Auth: `require_admin`
- Response: `{actions: [..]}`

## Dead Letter Queue (DLQ)
Base prefix: `/api/v1/dlq`

### GET `/api/v1/dlq/failed-tasks/{job_id}`
- Auth: `validate_team_access`
- Response: `FailedTaskResponse` or `null`

### POST `/api/v1/dlq/retry/{task_id}`
- Auth: `validate_team_access`
- Body: `ManualRetryRequest` (`reason?`)
- Response: `ManualRetryResponse`

### POST `/api/v1/dlq/resolve/{task_id}`
- Auth: `validate_team_access`
- Response: `ManualRetryResponse`

## OpenAPI Excerpts
Path-level excerpts (not a full OpenAPI document). `bearerAuth` refers to the standard JWT bearer scheme.

```yaml
paths:
  /health:
    get:
      summary: Health check
      tags: [health]
      responses:
        "200":
          description: OK
  /api/v1/conversations:
    get:
      summary: List conversations
      tags: [conversations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    post:
      summary: Create conversation
      tags: [conversations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ConversationCreate"
      responses:
        "200":
          description: OK
  /api/v1/conversations/{conversation_id}:
    parameters:
      - in: path
        name: conversation_id
        required: true
        schema:
          type: string
    get:
      summary: Get conversation
      tags: [conversations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    patch:
      summary: Update conversation
      tags: [conversations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ConversationUpdate"
      responses:
        "200":
          description: OK
    delete:
      summary: Delete conversation
      tags: [conversations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/conversations/{conversation_id}/messages:
    parameters:
      - in: path
        name: conversation_id
        required: true
        schema:
          type: string
    get:
      summary: List conversation messages
      tags: [conversations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/chat:
    post:
      summary: Scope-aware RAG chat
      tags: [chat]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ChatRequest"
      responses:
        "200":
          description: Chat response
        "300":
          description: Clarification required
  /api/v1/chat/stream:
    post:
      summary: Chat streaming
      tags: [chat]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ChatRequest"
      responses:
        "200":
          description: text/event-stream
  /api/v1/search:
    post:
      summary: Hybrid search
      tags: [search]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/SearchRequest"
      responses:
        "200":
          description: OK
  /api/v1/uploads/check-duplicates:
    post:
      summary: Check upload deduplication
      tags: [uploads]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/DuplicateCheckRequest"
      responses:
        "200":
          description: OK
  /api/v1/uploads/upload-url:
    post:
      summary: Generate presigned upload URL
      tags: [uploads]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/UploadUrlRequest"
      responses:
        "200":
          description: OK
  /api/v1/uploads/file/reference:
    post:
      summary: Create file reference and ingestion job
      tags: [uploads]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/FileReferenceRequest"
      responses:
        "200":
          description: OK
  /api/v1/documents/stats:
    get:
      summary: Document stats
      tags: [documents]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/documents:
    get:
      summary: List documents
      tags: [documents]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
        - in: query
          name: offset
          schema:
            type: integer
        - in: query
          name: q
          schema:
            type: string
        - in: query
          name: include_failed
          schema:
            type: boolean
      responses:
        "200":
          description: OK
    delete:
      summary: Bulk delete documents
      tags: [documents]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/BulkDeleteRequest"
      responses:
        "200":
          description: OK
  /api/v1/documents/{doc_id}:
    parameters:
      - in: path
        name: doc_id
        required: true
        schema:
          type: string
    delete:
      summary: Delete document
      tags: [documents]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/documents/{document_id}:
    parameters:
      - in: path
        name: document_id
        required: true
        schema:
          type: string
    patch:
      summary: Update document metadata
      tags: [documents]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/DocumentUpdate"
      responses:
        "200":
          description: OK
  /api/v1/documents/{document_id}/chunks:
    parameters:
      - in: path
        name: document_id
        required: true
        schema:
          type: string
    get:
      summary: List document chunks
      tags: [documents]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
        - in: query
          name: offset
          schema:
            type: integer
      responses:
        "200":
          description: OK
  /api/v1/jobs/active:
    get:
      summary: Get active ingestion job
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/jobs:
    get:
      summary: List ingestion jobs
      tags: [jobs]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
      responses:
        "200":
          description: OK
  /api/v1/jobs/{job_id}:
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
    get:
      summary: Get ingestion job
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/jobs/{job_id}/cancel:
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
    post:
      summary: Cancel ingestion job
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/jobs/files/{file_status_id}/retry:
    parameters:
      - in: path
        name: file_status_id
        required: true
        schema:
          type: string
    post:
      summary: Retry ingestion file
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/jobs/{job_id}/files:
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
    get:
      summary: List ingestion files
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/jobs/{job_id}/retry:
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
    post:
      summary: Retry ingestion job
      tags: [jobs]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/available:
    get:
      summary: List available connectors
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/status:
    get:
      summary: List integration statuses
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/google/exchange:
    post:
      summary: Exchange Google OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/notion/exchange:
    post:
      summary: Exchange Notion OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/microsoft/exchange:
    post:
      summary: Exchange Microsoft OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/MicrosoftExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/dropbox/exchange:
    post:
      summary: Exchange Dropbox OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/DropboxExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/github/exchange:
    post:
      summary: Exchange GitHub OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/GitHubExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/github/repos:
    get:
      summary: List GitHub repositories
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/github/repos/select:
    post:
      summary: Select GitHub repositories
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/GitHubRepoSelectionRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/box/exchange:
    post:
      summary: Exchange Box OAuth code
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/BoxExchangeRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/sftp/connect:
    post:
      summary: Connect SFTP
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/SFTPConnectRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/s3/connect:
    post:
      summary: Connect S3 (Enterprise)
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/S3ConnectRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/{provider}/status:
    parameters:
      - in: path
        name: provider
        required: true
        schema:
          type: string
    get:
      summary: Integration status
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/{provider}:
    parameters:
      - in: path
        name: provider
        required: true
        schema:
          type: string
    delete:
      summary: Disconnect integration
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/{provider}/items:
    parameters:
      - in: path
        name: provider
        required: true
        schema:
          type: string
    get:
      summary: List integration items
      tags: [integrations]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: parent_id
          schema:
            type: string
      responses:
        "200":
          description: OK
  /api/v1/integrations/web/crawl:
    post:
      summary: Start web crawl
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/WebCrawlRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/web/crawl/{config_id}:
    parameters:
      - in: path
        name: config_id
        required: true
        schema:
          type: string
    delete:
      summary: Delete web crawl
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/{provider}/ingest:
    parameters:
      - in: path
        name: provider
        required: true
        schema:
          type: string
    post:
      summary: Ingest integration items
      tags: [integrations]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/IngestRequest"
      responses:
        "200":
          description: OK
  /api/v1/integrations/{integration_id}/sync:
    parameters:
      - in: path
        name: integration_id
        required: true
        schema:
          type: string
    post:
      summary: Run integration sync
      tags: [integrations]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/integrations/{integration_id}/sync-history:
    parameters:
      - in: path
        name: integration_id
        required: true
        schema:
          type: string
    get:
      summary: Integration sync history
      tags: [integrations]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
      responses:
        "200":
          description: OK
  /api/v1/team:
    get:
      summary: Get team
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    patch:
      summary: Update team
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/TeamUpdate"
      responses:
        "200":
          description: OK
    delete:
      summary: Delete team
      tags: [team]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: purge_data
          schema:
            type: boolean
      responses:
        "200":
          description: OK
  /api/v1/team/effective-plan:
    get:
      summary: Get effective plan
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/team/members:
    get:
      summary: List team members
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    post:
      summary: Create team member
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/TeamMemberCreate"
      responses:
        "200":
          description: OK
  /api/v1/team/members/{member_id}:
    parameters:
      - in: path
        name: member_id
        required: true
        schema:
          type: string
    patch:
      summary: Update team member
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/TeamMemberUpdate"
      responses:
        "200":
          description: OK
    delete:
      summary: Delete team member
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/team/members/{member_id}/resend:
    parameters:
      - in: path
        name: member_id
        required: true
        schema:
          type: string
    post:
      summary: Resend team invite
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/team/accept:
    post:
      summary: Accept team invite
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/AcceptInviteRequest"
      responses:
        "200":
          description: OK
  /api/v1/team/stats:
    get:
      summary: Team stats
      tags: [team]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/team/invite:
    post:
      summary: Invite team member
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/InviteRequest"
      responses:
        "200":
          description: OK
  /api/v1/team/bulk-invite:
    post:
      summary: Bulk invite team members
      tags: [team]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          multipart/form-data:
            schema:
              $ref: "#/components/schemas/BulkInviteRequest"
      responses:
        "200":
          description: OK
  /api/v1/billing/plans:
    get:
      summary: List billing plans
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/checkout:
    post:
      summary: Start checkout
      tags: [billing]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/CheckoutRequest"
      responses:
        "200":
          description: OK
  /api/v1/billing/portal:
    post:
      summary: Customer portal
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/subscription:
    get:
      summary: Subscription details
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/subscription/cancel:
    post:
      summary: Cancel subscription
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/invoices:
    get:
      summary: List invoices
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/invoices/{order_id}/download:
    parameters:
      - in: path
        name: order_id
        required: true
        schema:
          type: string
    get:
      summary: Download invoice
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/fix-customer-id:
    post:
      summary: Fix billing customer id
      tags: [billing]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/billing/enterprise-inquiry:
    post:
      summary: Enterprise inquiry
      tags: [billing]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/EnterpriseInquiryRequest"
      responses:
        "200":
          description: OK
  /api/v1/usage:
    get:
      summary: Usage summary
      tags: [usage]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/plans:
    get:
      summary: Plan limits
      tags: [usage]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/settings/profile:
    get:
      summary: Get user profile
      tags: [settings]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    patch:
      summary: Update user profile
      tags: [settings]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ProfileUpdate"
      responses:
        "200":
          description: OK
  /api/v1/settings/profile/me:
    delete:
      summary: Delete account
      tags: [settings]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/settings/profile/me/anonymize:
    post:
      summary: Anonymize account
      tags: [settings]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/settings/notifications:
    get:
      summary: List notification settings
      tags: [settings]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
    patch:
      summary: Update notification setting
      tags: [settings]
      security:
        - bearerAuth: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/NotificationSettingUpdate"
      responses:
        "200":
          description: OK
    delete:
      summary: Reset notification settings
      tags: [settings]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/notifications:
    get:
      summary: List notifications
      tags: [notifications]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
        - in: query
          name: offset
          schema:
            type: integer
        - in: query
          name: unread_only
          schema:
            type: boolean
      responses:
        "200":
          description: OK
  /api/v1/notifications/unread-count:
    get:
      summary: Unread notification count
      tags: [notifications]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/notifications/{notification_id}/read:
    parameters:
      - in: path
        name: notification_id
        required: true
        schema:
          type: string
    patch:
      summary: Mark notification read
      tags: [notifications]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/notifications/read-all:
    patch:
      summary: Mark all notifications read
      tags: [notifications]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/notifications/all:
    delete:
      summary: Delete all notifications
      tags: [notifications]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/notifications/{notification_id}:
    parameters:
      - in: path
        name: notification_id
        required: true
        schema:
          type: string
    delete:
      summary: Delete notification
      tags: [notifications]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/admin/audit-logs:
    get:
      summary: List audit logs
      tags: [admin]
      security:
        - bearerAuth: []
      parameters:
        - in: query
          name: limit
          schema:
            type: integer
        - in: query
          name: offset
          schema:
            type: integer
        - in: query
          name: action
          schema:
            type: string
        - in: query
          name: resource_type
          schema:
            type: string
        - in: query
          name: from_date
          schema:
            type: string
        - in: query
          name: to_date
          schema:
            type: string
      responses:
        "200":
          description: OK
  /api/v1/admin/audit-logs/actions:
    get:
      summary: List audit log actions
      tags: [admin]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/dlq/failed-tasks/{job_id}:
    parameters:
      - in: path
        name: job_id
        required: true
        schema:
          type: string
    get:
      summary: Get failed DLQ tasks for job
      tags: [dlq]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
  /api/v1/dlq/retry/{task_id}:
    parameters:
      - in: path
        name: task_id
        required: true
        schema:
          type: string
    post:
      summary: Retry DLQ task
      tags: [dlq]
      security:
        - bearerAuth: []
      requestBody:
        required: false
        content:
          application/json:
            schema:
              $ref: "#/components/schemas/ManualRetryRequest"
      responses:
        "200":
          description: OK
  /api/v1/dlq/resolve/{task_id}:
    parameters:
      - in: path
        name: task_id
        required: true
        schema:
          type: string
    post:
      summary: Resolve DLQ task
      tags: [dlq]
      security:
        - bearerAuth: []
      responses:
        "200":
          description: OK
```

### GET `/api/v1/dlq/stats`
- Auth: `validate_team_access`
- Response: `DLQStatsResponse`

### GET `/api/v1/dlq/my-tasks`
- Auth: `validate_team_access`
- Query: `page`, `page_size`, `status_filter?`
- Response: `DLQListResponse`

### GET `/api/v1/dlq/admin/all`
- Auth: `require_admin`
- Query: `page`, `page_size`, `status_filter?`
- Response: `DLQListResponse`

### POST `/api/v1/dlq/admin/trigger-retry-cycle`
- Auth: `require_admin`
- Response: `{success, message, retried, failed}`

### GET `/api/v1/dlq/admin/stats`
- Auth: `require_admin`
- Response: `{total_failed, pending_retry, retrying, permanently_failed, resolved, unique_users}`

## Webhooks
### POST `/api/v1/webhooks/polar`
- Auth: none (signature-verified)
- Body: Polar/Svix webhook payload (raw bytes)
- Response: `{status: "received"}` (idempotent on webhook-id)
- Side effects: subscription updates, Redis idempotency key.

### GET `/api/v1/webhooks/health`
- Auth: none
- Response: `{status, service}`
