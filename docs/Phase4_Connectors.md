# Phase 4 — New Connectors (Enterprise Expansion)

## Scope
Phase 4 introduces new connectors following `docs/architecture/CONNECTOR_GUIDE.md` and plan-aware limits in `docs/architecture/QUOTAS_AND_LIMITS.md`. The first implementation is **SFTP** with full-stack wiring and production-grade security. We now add **Microsoft Graph** (OneDrive + SharePoint) as a unified connector with OAuth.

## Assessment (Current Stack Alignment)
- **Connector contract:** `BaseConnector` + `EnhancedConnector` is the ingestion standard; workers require `fetch_documents_sync`.
- **Discovery UI:** `/integrations/{provider}/items` calls `list_files` and expects folder/file semantics.
- **Credentials:** Non-OAuth connectors store credentials in `user_integrations.credentials` (JSON).
- **Quotas:** Ingestion is already gated by `check_admission` and per-plan quotas.
- **Security posture:** SSRF protections exist for Web; we must enforce the same for SFTP host resolution.

## SFTP Connector — Implementation Plan

### Backend (Connector + API)
- Add `backend/connectors/sftp.py` implementing:
  - SSRF host checks before any socket connection.
  - `validate_config`, `list_files`, `fetch_file_content`, `fetch_documents_sync`.
  - Recursive traversal for full sync; non-recursive listing for folder browse.
  - Error mapping to `ConnectorAuthError` / `ConnectorTransientError`.
- Register in `backend/connectors/registry.py` (`sftp`, `binary_content`, `incremental_sync`).
- Register in `backend/connectors/__init__.py` factory for ingestion.
- Add API endpoint `POST /integrations/sftp/connect` to validate and store encrypted credentials.
- Ensure `list_provider_items` recognizes directory MIME types (`inode/directory`).
- Add audit logs for connector connect/disconnect and ingestion/sync events.
- Add `backend/scripts/sftp_helper.py` for manual verification.
- Add unit tests covering SSRF, listing, and fetch behavior.

### Database (Connector Definitions)
- Add `connector_definitions` seed for `sftp` with category `files`.

### Frontend (UX + Connect Flow)
- Add SFTP connect modal with fields:
  - `host`, `port`, `username`, `password`, `private_key`, `root_path`.
- Call `POST /integrations/sftp/connect` and refresh connectors on success.
- Remove SFTP from “Coming Soon” list (now live).

## Validation Criteria
- SSRF blocks private/loopback hosts with clear error.
- Invalid credentials -> 401 with user-facing error.
- `list_files` works for root browse and full sync.
- `fetch_file_content` streams and respects prefetch for large files.
- Ingestion pipeline accepts SFTP file IDs and produces documents.
- Audit logs capture connect/disconnect + ingest/sync events.
- Helper script can list and download a sample file.

## Microsoft Graph Connector — Implementation Plan (OneDrive + SharePoint)

### Backend (Connector + OAuth)
- Add `backend/connectors/microsoft.py` implementing:
  - Unified `MicrosoftGraphConnector` with `target_type` ("onedrive" or "sharepoint").
  - Delta sync for full sync; non-recursive children list for UI browsing.
  - Streaming download with 302 handling for `/content`.
  - Retry on 429 with `Retry-After`.
- Register `onedrive` + `sharepoint` in registry + factory.
- Add OAuth exchange endpoint `/integrations/microsoft/exchange`.
- Refresh tokens via `services/oauth_token_manager.py`.

### Database
- Insert connector definitions for `onedrive` and `sharepoint` (category `cloud`).

### Frontend
- Add Microsoft OAuth redirect flow in `useDataSources` and callback page.
- Add SharePoint icon and update source type labels.
- Remove OneDrive from “Coming Soon” list.

## Microsoft Graph Validation Criteria
- OAuth connect works for OneDrive + SharePoint via `/oauth/callback`.
- Folder browsing returns folder/file entries.
- Ingestion fetches file content and processes end-to-end.
- Delta sync uses `sync_state.last_cursor` when present.

## Risks & Mitigations
- **Large directory trees:** recursive sync can be heavy. Mitigation: allow `since` filtering and root_path scoping.
- **Credential security:** secrets are encrypted via `encrypt_token` before storage.
- **Network instability:** timeouts + keepalive + transient error mapping.

## Roadmap (Next Connectors)
1) Share a common connector scaffolding (SSRF helpers, rate-limit wrappers).
2) Add OAuth-based connectors (OneDrive/Dropbox/Box) using registry.
3) Expand “Enterprise Storage” category and finalize icons.
4) Add connector-specific throttling in `connectors/limits.py` as needed.

## Implementation Status (SFTP)
- [x] Connector + registry + factory wiring
- [x] SFTP connect API + encrypted credentials
- [x] Directory browsing + recursive sync
- [x] SSRF host validation
- [x] Audit logging for connect/disconnect + ingest/sync
- [x] Helper script (`backend/scripts/sftp_helper.py`)
- [x] Unit tests for SSRF/listing/fetch

## Implementation Status (Microsoft Graph)
- [x] Unified connector for OneDrive + SharePoint
- [x] OAuth exchange + token refresh
- [x] Registry + factory + definitions
- [x] UI OAuth flow + icons/types
