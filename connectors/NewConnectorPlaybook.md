# New Connector Playbook (Void & Glass Platform)

Version: 1.0  
Purpose: Checklist and patterns to add any new connector with production-grade reliability, gating, and observability.

## 1) Capabilities & Contract
- Connector type must implement the unified ingestion interface: list/browse items, fetch content, return `SourceDocument` objects with metadata (id, name, mime, source_type, size, url/path).
- Respect tenant isolation: every call is scoped to the authenticated user/team.
- Honor feature gating: check usage/plan features server-side and in UI before enabling ingest.

## 2) Rate Limits & Concurrency
- Define safe concurrency in `backend/core/config.py`:
  - `CONNECTOR_CONCURRENCY_<TYPE>` entry (fallback to `CONNECTOR_CONCURRENCY_DEFAULT`).
- Wrap all network calls in `connector_fetch_limit("<type>")` (see `backend/connectors/limits.py`).
- Implement retries with jitter:
  - Use `with_retry_sync`/`with_google_retry` or a connector-specific decorator with 3 attempts, exponential backoff, and jitter.
  - Treat 429/502/503/504, connection errors, timeouts as retryable.
- Document provider rate limits in code comments and notes; keep under 80–90% of published limits.

## 3) Auth & Tokens
- Use `OAuthTokenManager` when OAuth is required; support refresh and reconnection errors.
- Never log secrets; log only connector type and user/tenant ids (truncated).
- Ensure stored tokens are encrypted (existing DB schema already encrypts secrets).

## 4) Data Hygiene
- Normalize IDs and paths; include file size when available.
- Skip empty content; set sensible MIME types.
- Avoid PII leaks in logs; redact request bodies and headers.

## 5) Gating & Roles
- Backend: protect endpoints with `validate_team_access` and `require_editor` for ingest/write ops.
- Frontend: disable connect/ingest/sync actions for viewer roles; surface upgrade messaging if plan limits block the connector.
- Respect plan features: add a feature flag in usage response if the connector is paid/enterprise-only.

## 6) Ingestion Path
- Use unified ingest endpoints (`/integrations/{provider}/ingest`) and job creation.
- For uploads, use signed URL → storage → `ingest_file_reference`.
- Ensure size, source_url/path, and job_id are passed through so progress/UI render correctly.

## 7) Observability
- Metrics: increment retries, rate-limit hits, and operation durations (see `core/metrics`).
- Logging: info-level for start/end; warning for retries; error for final failures. No secret values.
- Progress: ensure ingestion jobs emit status updates; document any long-running phases.

## 8) Testing
- Add unit tests for list/fetch logic and retry handling (mock provider responses).
- Add integration smoke test (if provider sandbox exists) or contract test with recorded fixtures.
- Run `python3 -m py_compile` on updated modules; run backend pytest where relevant.

## 9) UI Integration
- Add connector definition to `/integrations/available` and icon assets.
- Update frontend data-source grid card with gating copy and disabled states.
- Ensure ingestion job progress shows sizes/paths and handles failures gracefully.

## 10) Deployment Checklist
- Config: set connector concurrency defaults and any provider-specific env vars.
- Secrets: add provider client id/secret to env (not committed); validate in staging before prod.
- Docs: update README/migration notes with limits, scopes, and setup steps.

## 11) Rollback Plan
- If rate limits spike or errors regress, lower `CONNECTOR_CONCURRENCY_<TYPE>` and redeploy.
- Disable connector availability temporarily via config/feature flag if provider is unstable.
