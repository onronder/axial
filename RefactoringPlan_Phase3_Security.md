# Refactoring Plan - Phase 3: Security Hardening & Content Safety

## Overview
Phase 3 shifts from infrastructure expansion to hardening the platform for enterprise readiness across all tiers (Starter → Enterprise). Focus: prevent abuse (SSRF), ensure content safety (malware), strengthen auditability, and prepare for least-privilege activation.

## Scope & Steps (Must-Haves) — Current Status

### Step 1: SSRF Protection (Web Connector)
- [x] Completed in `backend/connectors/web.py`.
- Secure the Web Connector against internal network scanning and localhost/private IP access.
- Add allowlist/denylist rules and IP/host validation before fetch/crawl.
- Ensure redirects are validated against the same rules.
- Testing: attempts to fetch RFC1918/private/link-local addresses must fail.

### Step 2: Content Security (Real Malware Scan)
- [x] Completed. Real ClamAV streaming scan in `backend/services/malware.py`, wired in `backend/worker/tasks.py` with UX status updates.
- Add a streaming scan interface in the worker pipeline to prepare for ClamAV (or equivalent).
- Provide a stub scanner that can be swapped with a real engine later (feature-flagged).
- Ensure failures in scan path mark files as rejected with clear status.
- Testing: simulate “clean” vs “flagged” outcomes without external engines.

### Step 3: Enhanced Audit Logging
- [x] Completed. Ingest queue/denial/skip events are logged with structured metadata; failures and malware blocks already covered.
- Log critical ingestion lifecycle events: ingest request, delete, failure, skip (dedup), and rate-limit denials.
- Include org_id/user_id/connector/source metadata for compliance trails.
- Ensure logs are structured and can be shipped to observability backends.

### Step 4: Least-Privilege Role Activation (Planning)
- **Status:** Planned/Deferred. `IngestionSessionLocal` is available; workers still use Supabase HTTP client. Activation requires rollout plan and feature flag.
- Define the migration path to switch workers from Supabase service key to `ingestion_role`.
- Document prerequisites (direct DB access, RLS posture, secret rotation) and a rollout plan with guardrails/feature flag.

## Validation & Acceptance
- SSRF checks block private/internal targets; public targets allowed. (**Complete**)
- Malware stub integrated into the ingestion flow; flagged content is quarantined/rejected. (**Complete**)
- Audit logs present for ingest/delete/fail/skip/rate-limit events with tenant/user context. (**Complete**)
- Activation plan for `ingestion_role` documented and ready for execution in a later phase. (**Deferred**)

## Quick Verification Checklist
- `python -m backend.tests.verify_security_phase3` passes (SSRF block + malware stub).
- Sentry/Logs show “Scanning…” then “Scan passed…” on ingestion happy path.
- Sentry/Logs show explicit “Security Violation” on malware/SSRF block.

## Status
- Phase 3 (Security Hardening & Content Safety) is **Complete**, with Step 4 (Least-Privilege Role Activation) **Deferred** for future rollout.

## Deferred: Future Enterprise Infrastructure
The original Phase 3 items are deferred as premature optimization. Revisit when scale exceeds single-region Postgres limits.
- Tenant Partitioning
- Multi-region deployment
- Durable ledgers
- Direct pooled writes with custom routing
- Background rebalancing/archival

Note: To be revisited when scale exceeds single-region Postgres limits.
