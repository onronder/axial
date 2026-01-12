# Migration Audit & Execution Log

## Scope
This migration removes the deprecated `/api/v1/ingest` router, moves the presigned upload flow to `/api/v1/uploads`, enforces canonical provider values at API boundaries, and standardizes all ingestion paths on the unified ingestion engine. Web crawl config deletion is re-homed under `/integrations/web/crawl/{config_id}`. Connector fetches are synchronous-only for worker pipelines to avoid event-loop conflicts.

## Execution Log
- Next.js upgrade prep: renamed `middleware.ts` to `proxy.ts` and handler to `proxy` to silence deprecation warning; reran frontend lint/build/test to confirm.
- Usage flags corrected to match backend: `useUsage` now reads `features.team`/`premium_models` and exposes `modelTier`/`premiumModels`; plan gating consumers (team, crawl, billing) receive accurate entitlements.
- Team/admin gating hardened: team settings actions (invite, bulk import, role changes, revoke, resend) now blocked unless plan allows seats and user is an admin/owner; viewer/admin lock banners added. DLQ dashboard now read-only for viewers (no retry/resolve/selection) with clear messaging.
- Settings shell restyled to Void & Glass (floating nav rail, blurred header gradients) to align with UI_Refactoring guidance; keeps responsive scroll/overflow behaviour.
- Notification settings restyled with glass cards, gradient hero, and consistent toggles/icons for Void & Glass theme.
- Implemented ingestion/document fixes: document size persisted from `file_size_bytes`/metadata, bulk document delete/clear-all by source type (keeps connector auth), ingestion job creation for web crawl (job + per-page file status), chat sources now saved/returned end-to-end, billing guard now treats active subscriptions as paid (no trial).
- Frontend wiring: knowledge base table shows sizes and supports bulk delete/clear by connector, crawl ingest modal/URL input surface returned job ids and progress, chat bubbles render reference cards immediately, Paywall/BillingSettings route active subs to portal/manage.
- Tooling/tests: updated ESLint ignores to drop coverage noise (v9 config), reran test/build matrix: `backend/.venv-py311/bin/python -m pytest`, `cd frontend-new && npm run lint`, `npm test`, `npm run build`.
- Gating sweep: added team-access dependencies to all API routers, enforced editor/admin checks on destructive ingest/document/connector endpoints, and blocked viewer flows in data sources/ingest UI (connect/sync/upload/crawl/ingest) with view-only messaging.
- Plan-aware web crawl gating: UI now disables crawl inputs with clear upgrade messaging when plan flags disallow crawling (uses usage features), while keeping viewer restrictions intact.
- UI polish: chat area/input now use Void & Glass shell (radial glows, glass container, glowing send/model pills) for consistency with new tokens; IngestModal tests now run under mocked profile/usage providers to reflect production gating contexts.
- Pending: apply DB migrations if not already pushed (see Database Migrations).
- Ran targeted backend tests: `backend/tests/unit/test_uploads_api.py`, `backend/tests/unit/test_integrations.py`, `backend/tests/unit/test_ingestion_utils.py`.
- Ran full backend suite: `./backend/.venv-py311/bin/python -m pytest`.
- Ran full frontend coverage suite: `cd frontend-new && npm run test:coverage`.
- Cleared backend deprecation warnings by upgrading Supabase client and removing httpx `app` shortcut usage in tests.

## Canonical Provider Rules (API Boundary)
Supported providers (current implementations):
- `file_upload`
- `google_drive`
- `notion`
- `web`

Rejected (deprecated) provider values:
- `file`
- `drive`
- `upload`

Unsupported providers are rejected at API boundaries by:
- `backend/core/ingestion_utils.py` (`require_canonical_provider`)
- `backend/api/v1/integrations.py` (all `{provider}` routes)

## Audit: Links & References (Updated)
### Backend routes and handlers
- `/api/v1/uploads/upload-url`
  - Handler: `backend/api/v1/uploads.py:generate_upload_url`
  - Frontend: `frontend-new/lib/api.ts:getUploadUrl`
  - Scripts: `tenancy_smoke.py`, `agent/main.py`, `backend/debug_auth_request.py`
- `/api/v1/uploads/file/reference`
  - Handler: `backend/api/v1/uploads.py:ingest_file_reference`
  - Frontend: `frontend-new/lib/api.ts:ingestFileReference`, `frontend-new/components/ingest-modal.tsx`
  - Scripts: `tenancy_smoke.py`, `agent/main.py`
- `/api/v1/integrations/web/crawl`
  - Handler: `backend/api/v1/integrations.py:crawl_web`
  - Frontend: `frontend-new/components/ingest-modal.tsx`
- `/api/v1/integrations/web/crawl/{config_id}`
  - Handler: `backend/api/v1/integrations.py:delete_crawl_config`
- `/api/v1/integrations/{provider}/ingest`
  - Handler: `backend/api/v1/integrations.py:ingest_provider_items`
  - Frontend: `frontend-new/hooks/useDataSources.ts`, `frontend-new/components/drive-explorer.tsx`
- `/api/v1/integrations/{provider}/items`
  - Handler: `backend/api/v1/integrations.py:list_provider_items`
  - Frontend: `frontend-new/hooks/useDataSources.ts`, `frontend-new/components/drive-explorer.tsx`
- `/api/v1/integrations/status`
  - Handler: `backend/api/v1/integrations.py:get_user_integrations`
  - Frontend: `frontend-new/hooks/useDataSources.ts`
- `/api/v1/integrations/available`
  - Handler: `backend/api/v1/integrations.py:get_available_connectors`
  - Frontend: `frontend-new/hooks/useDataSources.ts`
- `/api/v1/integrations/{provider}` (DELETE)
  - Handler: `backend/api/v1/integrations.py:disconnect_provider`
  - Frontend: `frontend-new/hooks/useDataSources.ts`

### Frontend proxy links
API proxy remains `/api/py/*` -> `/api/v1/*` via `frontend-new/next.config.ts`.

## Completed Work (Code Changes)
### Backend
- Added `backend/api/v1/uploads.py` and removed `backend/api/v1/ingest.py`.
- Updated `backend/main.py` router wiring to use `/api/v1/uploads`.
- Moved `delete_crawl_config` to `backend/api/v1/integrations.py` under `/integrations/web/crawl/{config_id}`.
- Enforced canonical provider values via `core/ingestion_utils.require_canonical_provider` (deprecated + unsupported rejected).
- Unified connector registry now only includes implemented connectors:
  - `backend/connectors/drive.py`, `backend/connectors/notion.py`, `backend/connectors/web.py`, `backend/connectors/file_upload.py`
- Removed legacy connector wrappers:
  - `backend/connectors/google_drive.py`, `backend/connectors/notion_enhanced.py`, `backend/connectors/web_enhanced.py`
- Worker ingestion uses synchronous `fetch_documents_sync` only (no asyncio fallback).
- Updated Supabase dependency to `supabase-auth` backed client (Supabase 2.27.1) and aligned Pydantic to 2.12.5.
- Reworked request-tracing tests to use `httpx.ASGITransport` instead of the deprecated `app=` shortcut.
- Document endpoints now surface `file_size_bytes` with metadata fallback for size rendering, defaulting to zero when absent.
- Added bulk delete endpoint `/api/v1/documents` (ids or `source_type`), blocks viewers, recalculates usage, and logs audit entries while preserving connector auth.
- Web crawl queue/worker now creates or upserts ingestion jobs and per-page file statuses, threads `job_id` through discovery/process/finalize, and updates unified job progress (including scheduler recrawls).
- Chat persistence keeps `sources` payloads on save/stream/get so downstream UI can render reference cards without refresh.
- Web crawl hardening: sitemap preflight now skips HTML/login responses before parsing to avoid Sentry noise; crawl status updates no longer write a missing `message` column (uses `status_message` only).

### Frontend
- Updated upload API calls to `/api/v1/uploads/*` in `frontend-new/lib/api.ts`.
- Knowledge base table now shows document sizes and supports multi-select delete or “clear all” per connector type; viewer role cannot delete.
- Crawl ingest UI surfaces returned `job_id` and progresses via unified job updates; global progress tray aligns with web crawl like Google Drive.
- Chat bubbles render reference cards immediately (string or object sources) and history SSE normalizes sources.
- Paywall guard and BillingSettings send active subscribers to portal/manage instead of trial checkout; upgrade CTA labels clarified.
- ESLint config ignores coverage output to remove lint noise on v9.

### Tests
- Renamed and updated upload tests: `backend/tests/unit/test_uploads_api.py`.
- Adjusted provider validation tests in `backend/tests/unit/test_integrations.py` and `backend/tests/unit/test_ingestion_utils.py`.

## Database Migrations
Present in repo (apply if not already pushed):
- `supabase/migrations/20260109101500_add_documents_updated_at.sql` (documents.updated_at + trigger)
- `supabase/migrations/20260109120000_normalize_provider_values.sql` (normalize legacy provider/source_type values)

## Runtime Flows (Unified Engine)
### File Upload (Presigned)
1. `POST /api/v1/uploads/upload-url`
2. `PUT` file to signed URL
3. `POST /api/v1/uploads/file/reference`
4. `unified_ingest_task` -> `process_file_task` -> document/chunk insert
5. Staged upload cleanup

### Connector Ingest (OAuth + Unified)
1. `POST /api/v1/integrations/{provider}/ingest`
2. `unified_ingest_task` -> `process_file_task` -> document/chunk insert

### Web Crawl
1. `POST /api/v1/integrations/web/crawl`
2. Worker crawl tasks manage ingest and job progress
3. `DELETE /api/v1/integrations/web/crawl/{config_id}` for cleanup

## Validation Status
- Static audit: no remaining references to `/api/v1/ingest` in code/scripts.
- Tests: full backend suite and frontend coverage suite completed (see Execution Log).

## Immediate Execution Steps
1. Run `supabase db push` to apply pending migrations (if not already applied).
2. Run backend tests: `./backend/.venv-py311/bin/python -m pytest`.
3. Run frontend tests: `cd frontend-new && npm run test:coverage`.
