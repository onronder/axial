# AxioHub API Reference

> **Version:** 1.0 | **Date:** February 2026 | **Base URL:** `/api/v1`
>
> Complete endpoint reference for the AxioHub REST API.
> All endpoints require authentication unless otherwise noted.
> Rate limits are per-user, per-minute, enforced via slowapi + Redis.

---

## Table of Contents

1. [Chat & Conversations](#1-chat--conversations)
2. [Search](#2-search)
3. [Documents](#3-documents)
4. [Uploads](#4-uploads)
5. [Integrations & Connectors](#5-integrations--connectors)
6. [Settings & Profile](#6-settings--profile)
7. [Team Management](#7-team-management)
8. [Billing & Usage](#8-billing--usage)
9. [Jobs & Ingestion](#9-jobs--ingestion)
10. [Notifications](#10-notifications)
11. [Consent Management](#11-consent-management)
12. [Compliance](#12-compliance)
13. [Approvals](#13-approvals)
14. [Admin & Audit](#14-admin--audit)
15. [Dead Letter Queue (DLQ)](#15-dead-letter-queue-dlq)
16. [Health](#16-health)
17. [Webhooks](#17-webhooks)
18. [MCP (Model Context Protocol)](#18-mcp-model-context-protocol)
19. [Feedback & Analytics](#19-feedback--analytics)

**Total Endpoints: ~146** (excluding unregistered health probes and documentation-only examples in `dependencies.py`)

---

## Authentication

All authenticated endpoints require a valid JWT in the `Authorization` header:

```
Authorization: Bearer <supabase_access_token>
```

The JWT is issued by Supabase Auth and validated on every request. Role-based access is enforced via dependency injection:

| Dependency | Description |
|-----------|-------------|
| `get_current_user` | Any authenticated user (returns `user_id`) |
| `require_editor` | Requires editor or admin role |
| `require_admin` | Requires admin role |
| `require_plan(["pro", "enterprise"])` | Requires specific subscription plan |
| `require_paid_access` | Requires any paid plan (starter+) |
| `get_user_organization_id` | Extracts organization ID from user context |

---

## 1. Chat & Conversations

### Conversations

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/conversations` | List all conversations (paginated) | User | 60/min |
| `POST` | `/conversations` | Create new conversation | User | 30/min |
| `GET` | `/conversations/{conversation_id}` | Get conversation details | User | 60/min |
| `PATCH` | `/conversations/{conversation_id}` | Update conversation (title, etc.) | User | 30/min |
| `DELETE` | `/conversations/{conversation_id}` | Delete conversation | User | 30/min |
| `GET` | `/conversations/{conversation_id}/messages` | List messages in conversation | User | 60/min |

### Chat

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/chat` | Send message and get AI response (SSE stream) | User | 30/min |
| `POST` | `/chat/stream` | Alternative streaming chat endpoint | User | 30/min |

**`POST /chat` Request:**
```json
{
  "message": "What are the key findings from the Q4 report?",
  "conversation_id": "uuid (optional - creates new if omitted)",
  "scope": "google_drive (optional - filter by source)",
  "model": "gpt-4o (optional)"
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"content": "Based on", "type": "token"}
data: {"content": " the Q4 report", "type": "token"}
...
data: {"sources": [...], "type": "sources"}
data: [DONE]
```

---

## 2. Search

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/search` | Hybrid vector + fulltext search | User | 60/min |

**Request:**
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

**Response:**
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

## 3. Documents

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/documents/stats` | Get document statistics (count, storage) | User | 60/min |
| `GET` | `/documents` | List documents (paginated, searchable) | User | 60/min |
| `DELETE` | `/documents` | Bulk delete documents | Editor | 30/min |
| `DELETE` | `/documents/{doc_id}` | Delete single document | Editor | 30/min |
| `PATCH` | `/documents/{document_id}` | Update document metadata | Editor | 30/min |
| `GET` | `/documents/{document_id}/chunks` | List document chunks (paginated) | User | 60/min |
| `GET` | `/documents/{document_id}/content` | Get document text content | User | 60/min |
| `GET` | `/documents/{document_id}/download` | Download original file | User | 30/min |
| `POST` | `/documents/{document_id}/wipe` | Initiate secure wipe (DoD 5220.22-M) | Editor | 10/min |
| `GET` | `/documents/{document_id}/wipe-status` | Check wipe progress | User | 60/min |

---

## 4. Uploads

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/uploads/check-duplicates` | Check for duplicate files by SHA-256 hash | User | 60/min |
| `POST` | `/uploads/upload-url` | Get presigned URL for direct upload | User | 30/min |
| `POST` | `/uploads/file/reference` | Register uploaded file and trigger ingestion | Editor | 30/min |

**Upload Flow:**
1. `POST /uploads/check-duplicates` → `{is_duplicate, existing_document_id?}`
2. `POST /uploads/upload-url` → `{upload_url, storage_path}`
3. `PUT {upload_url}` (direct to Supabase Storage)
4. `POST /uploads/file/reference` → `{job_id, status: "queued"}`

---

## 5. Integrations & Connectors

### OAuth Token Exchange

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/integrations/google/exchange` | Exchange Google OAuth code | User | 30/min |
| `POST` | `/integrations/notion/exchange` | Exchange Notion OAuth code | User | 30/min |
| `POST` | `/integrations/microsoft/exchange` | Exchange Microsoft OAuth code (PKCE) | User | 30/min |
| `POST` | `/integrations/dropbox/exchange` | Exchange Dropbox OAuth code | User | 30/min |
| `POST` | `/integrations/github/exchange` | Exchange GitHub OAuth code | User | 30/min |
| `POST` | `/integrations/box/exchange` | Exchange Box OAuth code | User | 30/min |

### Credential-Based Connection

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/integrations/sftp/connect` | Connect SFTP (host, user, key) | User | 30/min |
| `POST` | `/integrations/s3/connect` | Connect S3 (IAM credentials) | User | 30/min |

### Integration Management

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/integrations/available` | List all available connectors | User | 60/min |
| `GET` | `/integrations/status` | List user's connected integrations | User | 60/min |
| `GET` | `/integrations/{provider}/status` | Get specific integration status | User | 60/min |
| `DELETE` | `/integrations/{provider}` | Disconnect integration | Editor | 30/min |
| `GET` | `/integrations/{provider}/items` | Browse items in connected source | User | 60/min |

### GitHub-Specific

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/integrations/github/repos` | List GitHub repositories | User | 60/min |
| `POST` | `/integrations/github/repos/select` | Select repos for ingestion | Editor | 30/min |

### Web Crawler

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/integrations/web/crawl` | List crawl configurations | User | 60/min |
| `GET` | `/integrations/web/crawl/active` | Get active crawl config | User | 60/min |
| `GET` | `/integrations/web/crawl/{config_id}` | Get specific crawl config | User | 60/min |
| `POST` | `/integrations/web/crawl` | Create new crawl (returns 202) | Editor | 30/min |
| `DELETE` | `/integrations/web/crawl/{config_id}` | Delete crawl config | Editor | 30/min |

### Ingestion & Sync

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/integrations/{provider}/ingest` | Trigger ingestion from connector (returns 202) | Editor | 30/min |
| `POST` | `/integrations/{integration_id}/sync` | Trigger incremental sync | Editor | 30/min |
| `GET` | `/integrations/{integration_id}/sync-history` | Get sync history | User | 60/min |
| `GET` | `/integrations/{provider}/ingested-files` | List ingested files for provider | User | 60/min |

---

## 6. Settings & Profile

### Profile

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/settings/profile` | Get user profile | User | 60/min |
| `PATCH` | `/settings/profile` | Update profile (name, theme, etc.) | User | 30/min |
| `DELETE` | `/settings/profile/me` | Delete account (GDPR) | User | 3/min |
| `POST` | `/settings/profile/me/anonymize` | Anonymize account data | User | 3/min |

### Notification Preferences

| Method | Path | Purpose | Auth | Rate Limit | Plan |
|--------|------|---------|------|------------|------|
| `GET` | `/settings/notifications` | Get notification preferences | User | 60/min | Paid |
| `PATCH` | `/settings/notifications` | Update notification preferences | User | 30/min | Paid |
| `DELETE` | `/settings/notifications` | Reset notification preferences | User | 30/min | Paid |

---

## 7. Team Management

All team endpoints require paid plan access (`_paid_team_deps`).

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/team` | Get team details | Member | 60/min |
| `PATCH` | `/team` | Update team settings | Admin | 30/min |
| `DELETE` | `/team` | Delete team | Admin (owner) | 10/min |
| `GET` | `/team/my-invites` | List pending invites for current user | User | 60/min |
| `GET` | `/team/effective-plan` | Get effective plan for paywall checks | Member | 60/min |
| `GET` | `/team/members` | List team members | Member | 60/min |
| `GET` | `/team/stats` | Get team statistics | Member | 60/min |
| `POST` | `/team/invite` | Send invite email | Admin | 30/min |
| `POST` | `/team/bulk-invite` | Bulk invite via CSV | Admin | 10/min |
| `POST` | `/team/members` | Add member directly | Admin | 30/min |
| `PATCH` | `/team/members/{member_id}` | Update member role | Admin | 30/min |
| `DELETE` | `/team/members/{member_id}` | Remove member | Admin | 30/min |
| `POST` | `/team/members/{member_id}/resend` | Resend invite email | Admin | 10/min |
| `POST` | `/team/accept` | Accept team invite | User | 30/min |

---

## 8. Billing & Usage

### Billing

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/billing/plans` | List available plans | User | 60/min |
| `POST` | `/billing/checkout` | Create Polar.sh checkout session | User | 10/min |
| `POST` | `/billing/portal` | Create Polar.sh billing portal | User | 10/min |
| `GET` | `/billing/subscription` | Get current subscription details | User | 60/min |
| `POST` | `/billing/subscription/cancel` | Cancel subscription | User | 10/min |
| `GET` | `/billing/invoices` | List invoices (paginated) | User | 60/min |
| `GET` | `/billing/invoices/{order_id}/download` | Download invoice | User | 30/min |
| `POST` | `/billing/fix-customer-id` | Fix Polar customer ID mapping | User | 10/min |
| `POST` | `/billing/enterprise-inquiry` | Submit enterprise plan inquiry | User | 3/min |

### Usage

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/usage` | Get current usage statistics | User | 60/min |
| `GET` | `/plans` | Get available plans (alt route) | User | 60/min |

---

## 9. Jobs & Ingestion

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/jobs/active` | Get active ingestion job | User | 60/min |
| `GET` | `/jobs/{job_id}` | Get job details | User | 60/min |
| `GET` | `/jobs` | List all ingestion jobs | User | 60/min |
| `POST` | `/jobs/{job_id}/cancel` | Cancel running job | Editor | 30/min |
| `POST` | `/jobs/files/{file_status_id}/retry` | Retry failed file (max 3) | Editor | 30/min |
| `GET` | `/jobs/{job_id}/files` | List file statuses for job | User | 60/min |
| `POST` | `/jobs/{job_id}/retry` | Retry entire failed job | Editor | 10/min |

---

## 10. Notifications

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/notifications` | List notifications (paginated) | User | 60/min |
| `GET` | `/notifications/unread-count` | Get unread notification count | User | 60/min |
| `PATCH` | `/notifications/{notification_id}/read` | Mark notification as read | User | 60/min |
| `PATCH` | `/notifications/read-all` | Mark all as read | User | 30/min |
| `DELETE` | `/notifications/all` | Delete all notifications | User | 10/min |
| `DELETE` | `/notifications/{notification_id}` | Delete single notification | User | 30/min |

---

## 11. Consent Management

### Scopes

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/scopes` | List all data scopes | User | 60/min |

### Organization Consent

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/consent/organization` | Get organization-level consent | User | 60/min |
| `PATCH` | `/consent/organization` | Update organization consent | Admin | 30/min |

### Scope Consent

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/consent/scope` | Get scope-level consent | User | 60/min |
| `PATCH` | `/consent/scope` | Update scope consent | Editor | 30/min |
| `POST` | `/consent/scope/bulk` | Bulk update scope consents | Editor | 30/min |
| `PATCH` | `/consent/scope/agents` | Update AI agent access per scope | Editor | 30/min |
| `DELETE` | `/consent/scope` | Revoke scope consent | Admin | 10/min |

### Document Consent

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/consent/document/{document_id}` | Get document-level consent | User | 60/min |
| `PATCH` | `/consent/document/{document_id}` | Update document consent | Editor | 30/min |
| `PATCH` | `/consent/document/{document_id}/agents` | Update AI agent access per document | Editor | 30/min |
| `DELETE` | `/consent/document/{document_id}` | Revoke document consent | Admin | 10/min |

### Audit & Reports

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/consent/audit` | Paginated consent audit trail | User | 60/min |
| `GET` | `/consent/report` | Compliance summary report | User | 30/min |

---

## 12. Compliance

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/delete-request` | GDPR Article 17 deletion request (returns 202) | User | 10/min |
| `POST` | `/admt-optout` | CCPA ADMT opt-out request (returns 202) | User | 10/min |
| `GET` | `/tombstones` | List compliance tombstones | User | 30/min |
| `GET` | `/tombstone/{tombstone_id}` | Get specific tombstone details | User | 60/min |
| `GET` | `/report` | Compliance report (deletions, status) | User | 10/min |
| `GET` | `/pending` | List pending compliance requests | User | 30/min |

**`POST /delete-request` Request:**
```json
{
  "resource_type": "document",
  "resource_id": "uuid",
  "compliance_type": "gdpr_art17",
  "reason": "User requested data deletion"
}
```

**Response (202 Accepted):**
```json
{
  "tombstone_id": "uuid",
  "status": "active",
  "message": "Data access revoked. Secure deletion in progress.",
  "estimated_completion": "2026-02-16T08:30:00Z"
}
```

---

## 13. Approvals

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/approvals/request` | Create approval request | Editor | 30/min |
| `POST` | `/approvals/{approval_id}/approve` | Approve a request | Admin | 30/min |
| `POST` | `/approvals/{approval_id}/reject` | Reject a request | Admin | 30/min |
| `POST` | `/approvals/{approval_id}/execute` | Execute approved action | Admin | 30/min |
| `GET` | `/approvals/pending` | List pending approvals (paginated) | Admin | 60/min |
| `GET` | `/approvals/{approval_id}` | Get approval details | User | 60/min |

---

## 14. Admin & Audit

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/audit-logs` | List audit logs (paginated, filterable) | Admin | 30/min |
| `GET` | `/audit-logs/actions` | List available audit action types | Admin | 60/min |
| `GET` | `/security-log` | Security event log (login, IP) | Admin | 30/min |

**`GET /audit-logs` Query Parameters:**
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

## 15. Dead Letter Queue (DLQ)

Failed tasks and webhooks are stored in a DLQ for retry and investigation.

### User Endpoints

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/failed-tasks/{job_id}` | Get failed task for a specific job | User | 60/min |
| `POST` | `/retry/{task_id}` | Manually retry a failed task | Editor | 30/min |
| `POST` | `/resolve/{task_id}` | Mark failed task as resolved | Editor | 30/min |
| `GET` | `/stats` | Get DLQ statistics for current user | User | 60/min |
| `GET` | `/my-tasks` | List all failed tasks for current user | User | 60/min |

### Admin Endpoints

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/admin/all` | List all failed tasks (all users) | Admin | 30/min |
| `POST` | `/admin/trigger-retry-cycle` | Trigger automatic retry cycle | Admin | 10/min |
| `GET` | `/admin/stats` | Global DLQ statistics | Admin | 30/min |

---

## 16. Health

The active health endpoint is defined inline in `main.py` (not via a registered router). It is publicly accessible (no authentication required).

| Method | Path | Purpose | Rate Limit |
|--------|------|---------|------------|
| `GET` | `/health` | Health check (DB + Redis connectivity) | 60/min |

**`GET /health` Response:**
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

> **Note:** `backend/api/v1/health.py` defines additional Kubernetes-style probes (`/health/ready`, `/health/live`, `/health/startup`) but this router is **not registered** in `main.py`. These endpoints are not currently active.

---

## 17. Webhooks

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/webhooks/polar` | Polar.sh payment webhook receiver | Signature | N/A |
| `POST` | `/webhooks/dlq/retry` | Retry failed webhooks from DLQ | Admin | 10/min |
| `GET` | `/webhooks/dlq/stats` | Webhook DLQ statistics | Admin | 30/min |
| `GET` | `/webhooks/health` | Webhook system health | Admin | 60/min |

**Polar Webhook Events:**
- `subscription.created` — New subscription
- `subscription.updated` — Plan change
- `subscription.cancelled` — Cancellation
- `order.completed` — One-time payment

---

## 18. MCP (Model Context Protocol)

MCP enables external AI agents to search and interact with the AxioHub knowledge base.

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/mcp/v1/rpc` | MCP JSON-RPC endpoint | API Key | 60/min |
| `POST` | `/mcp/api-keys` | Create MCP API key | Admin | 10/min |
| `GET` | `/mcp/api-keys` | List MCP API keys | Admin | 60/min |
| `GET` | `/mcp/api-keys/{key_id}` | Get specific API key | Admin | 60/min |
| `POST` | `/mcp/api-keys/{key_id}/rotate` | Rotate API key | Admin | 10/min |
| `DELETE` | `/mcp/api-keys/{key_id}` | Revoke API key | Admin | 10/min |
| `GET` | `/mcp/info` | Get MCP server info | User | 60/min |

**MCP RPC Request:**
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

## 19. Feedback & Analytics

### Chat Feedback

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `POST` | `/chat/feedback` | Submit chat response feedback (returns 201) | User | 30/min |
| `GET` | `/chat/feedback/conversation/{conversation_id}` | Get feedback for a conversation | User | 60/min |

### Team Analytics

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/analytics/feedback` | Team-level feedback analytics | Admin | 30/min |
| `GET` | `/analytics/feedback/sources` | Feedback source metrics | Admin | 30/min |

### Platform Admin

| Method | Path | Purpose | Auth | Rate Limit |
|--------|------|---------|------|------------|
| `GET` | `/admin/feedback/platform` | Platform-wide feedback data | Super Admin | 10/min |
| `POST` | `/admin/feedback/refresh-metrics` | Refresh feedback metrics cache | Super Admin | 3/min |

---

## Error Response Format

All endpoints return errors in a consistent format:

```json
{
  "detail": "Human-readable error message"
}
```

### Common HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `400` | Bad Request | Invalid input, validation failure |
| `401` | Unauthorized | Missing or invalid JWT |
| `402` | Payment Required | Quota exceeded, plan upgrade needed |
| `403` | Forbidden | Insufficient role or plan |
| `404` | Not Found | Resource doesn't exist or not in user's org |
| `409` | Conflict | Duplicate resource, concurrent modification |
| `422` | Unprocessable Entity | Pydantic validation failure |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Unexpected server error |
| `502` | Bad Gateway | External service unavailable |
| `503` | Service Unavailable | System overloaded |

---

## Rate Limit Response

When rate limited, the API returns:

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

## Pagination

Endpoints that return lists support pagination via query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-indexed) |
| `limit` | int | 20 | Items per page (bounded: 1-100) |
| `offset` | int | 0 | Alternative: skip N items |

Bounded pagination prevents abuse — all paginated endpoints use `Query(ge=1, le=100)` for the limit parameter.

---

## Router Registration

All routers are registered in `backend/main.py` with the `/api/v1` prefix:

| Router Module | Prefix | Tags |
|---------------|--------|------|
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
| ~~`health`~~ | ~~`/api/v1`~~ | ~~Health~~ *(not registered — `/health` defined inline in `main.py`)* |
| `webhooks` | `/api/v1` | Webhooks |
| `mcp` | `/api/v1` | MCP |
| `feedback` | `/api/v1` | Feedback |
