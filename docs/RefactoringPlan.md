# PROJECT STATUS: DEPLOYED v2.0 (Enterprise Ready)
# Refactoring Plan: Minimum -> Balanced -> Enterprise

Version: 1.0
Date: January 6, 2026
Scope: Performance + security improvements while retaining Supabase + Railway + Celery + Redis

This plan is sequenced by dependency and preserves the current architecture. It targets ~80% performance uplift in Phase 1 (Minimum), a sellable Balanced release in Phase 2, and an enterprise-grade update in Phase 3.

---

## Phase 1 — Minimum (Target: ~80% uplift, no architecture change, go-live fast)

Goal: Remove the largest latency taxes (cross-region RTT, write amplification, embedding throttling) and stabilize ingestion without adding services or rewriting the app.

1) Define SLOs and baseline metrics
- Dependency: None
- Change: Define ingestion SLOs (p50/p95/p99 per file and per job), queue wait time, DB latency, error rate.
- Full-stack changes:
  - Observability dashboards for ingestion stage timing (fetch, parse, chunk, embed, insert)
  - API timing headers and worker stage timers
  - DB latency tracking

2) Region alignment for DB and workers
- Dependency: Step 1
- Change: Co-locate Railway workers and Supabase DB to eliminate cross-region RTT.
- Full-stack changes:
  - Infra deployment region updates
  - Updated environment variables

3) Reduce progress update frequency
- Dependency: Step 1
- Change: Update status only at coarse milestones, not per chunk.
- Full-stack changes:
  - Frontend progress UI expectations
  - Worker status update cadence
  - Supabase realtime filtering

4) Increase embedding batch size and concurrency
- Dependency: Step 1
- Change: Raise batch size and concurrency; replace fixed sleeps with adaptive throttling.
- Full-stack changes:
  - Embedding configuration in workers
  - Rate-limit handling logic

5) Increase chunk insert batch size (still PostgREST)
- Dependency: Step 1
- Change: Larger batches to reduce PostgREST calls.
- Full-stack changes:
  - Worker ingestion batching logic

6) Constrain connector concurrency and retries
- Dependency: Step 1
- Change: Limit connector list/fetch concurrency, enforce backoff.
- Full-stack changes:
  - Connector runtime limits
  - Retry and throttle behavior

7) Reduce Celery chord/result overhead
- Dependency: Step 1
- Change: Replace large fan-out chord results with job-level counters in Redis.
- Full-stack changes:
  - Worker orchestration and Redis usage

8) Add ingestion idempotency and strict retry policy
- Dependency: Step 1
- Change: Idempotency keys to prevent reprocessing storms.
- Full-stack changes:
  - API ingestion endpoints
  - Worker retry logic and DLQ behavior

9) Add parser safety guardrails
- Dependency: Step 1
- Change: Timeouts, file size caps, early exits for risky parsing.
- Full-stack changes:
  - Worker parsing constraints

10) Security quick wins
- Dependency: Step 1
- Change: Rotate secrets, audit RLS, redact logs/DLQ payloads, tighten CORS.
- Full-stack changes:
  - Secrets management
  - DB policies
  - Logging configuration
  - Frontend CORS expectations

11) Benchmark and release gates
- Dependency: Steps 2-10
- Change: Benchmark ingestion for 15, 150, 1,500 files; enforce performance gates.
- Full-stack changes:
  - QA and release process updates

Phase 1 outcomes:
- Reduced latency due to region alignment and fewer writes
- Higher embedding throughput without new services
- Stabilized ingestion with safer retries and parsing

---

## Phase 2 — Balanced (Sellable release, same architecture)

Goal: Keep Supabase/Railway/Celery/Redis but refactor the ingestion hot path for sustained throughput and predictable performance under heavy agent load.

1) Direct Postgres pooled writes for ingestion
- Dependency: Phase 1 complete
- Change: Bypass PostgREST for ingestion writes using pooled connections.
- Full-stack changes:
  - Worker DB client and connection pool
  - Supabase roles for ingestion

2) Staging tables for chunk writes
- Dependency: Step 1
- Change: Write chunks to staging, then bulk-move into indexed tables.
- Full-stack changes:
  - Supabase migrations
  - Worker write path

3) Defer or batch HNSW index updates
- Dependency: Step 2
- Change: Reduce per-insert HNSW maintenance cost.
- Full-stack changes:
  - Index maintenance strategy and schedules

4) Split Celery queues by stage
- Dependency: Step 1
- Change: Separate parse, embed, and write queues with specialized workers.
- Full-stack changes:
  - Worker config and routing
  - Concurrency profiles

5) Streaming ingestion pipeline
- Dependency: Step 4
- Change: Parse -> chunk -> embed -> write without loading full files.
- Full-stack changes:
  - Worker pipeline flow

6) True async embeddings
- Dependency: Step 4
- Change: Replace sync executor calls with async client.
- Full-stack changes:
  - Embedding service layer

7) File and chunk deduplication
- Dependency: Step 5
- Change: Hash-based dedup to skip re-embedding duplicates.
- Full-stack changes:
  - Worker ingest logic
  - DB uniqueness constraints

8) Buffered progress tracking
- Dependency: Step 4
- Change: Track progress in Redis/event stream, periodic DB snapshots.
- Full-stack changes:
  - Worker progress writes
  - Frontend realtime subscription

9) Per-tenant admission control
- Dependency: Step 1
- Change: Rate limits and quotas so heavy agents cannot starve others.
- Full-stack changes:
  - API gating
  - Worker queue policy

10) Connector extensibility hardening
- Dependency: Step 1
- Change: Standard connector manifest, rate-limit config per connector, test harness.
- Full-stack changes:
  - Connector library
  - Connector documentation

11) Least-privilege DB roles for ingestion
- Dependency: Step 1
- Change: Limit ingestion role scope and remove shared super keys.
- Full-stack changes:
  - DB roles and permissions
  - Secrets management

12) Enterprise-scale load tests
- Dependency: Steps 1-11
- Change: Stress test 1,000-person agent workloads against SLOs.
- Full-stack changes:
  - QA and performance gates

Phase 2 outcomes:
- Bulk write path and staging tables eliminate PostgREST overhead
- Streaming ingestion avoids OOM and improves throughput
- Stage-separated worker pools stabilize latency at scale

---

## Phase 3 — Security Hardening & Content Safety (Replaces prior Phase 3)

Goal: Make the platform enterprise-ready by prioritizing security and safety across all tiers. The previous Phase 3 (partitioning/multi-region/ledger) is deferred as future infrastructure.

1) SSRF Protection (Web Connector)
- Secure against internal network scanning and localhost/private IP access; validate redirects/hosts.

2) Content Security (Malware Stub)
- Add a streaming scan interface in the worker pipeline (stub ready for ClamAV or equivalent); reject/quarantine flagged content.

3) Enhanced Audit Logging
- Log critical ingestion lifecycle events (ingest/delete/fail/skip/rate-limit) with org/user/source context for compliance.

4) Least-Privilege Role Activation (Planning)
- Document the rollout plan to move workers to `ingestion_role` with feature flag/guardrails, prerequisites, and secret rotation steps.

Phase 3 outcomes:
- Hardened ingestion against SSRF and unsafe content
- Better compliance traceability via audit logs
- Clear path to least-privilege execution for workers

### Deferred: Future Enterprise Infrastructure (formerly Phase 3)
- Tenant partitioning or cell-based isolation
- Multi-region ingestion with residency routing
- Durable job ledger and event-driven ingestion
- Optional write-optimized vector store
- Advanced admission control
- Connector sandboxing and SSRF controls (deep isolation model)
- File security scanning and parser sandboxing (full production AV/sandbox)
- RAG security controls (advanced redaction/guardrails)
- Compliance readiness (third-party audits, retention controls)
- Enterprise launch validation (regional load tests, audits)

Note: To be revisited when scale exceeds single-region Postgres limits.

---

## Coverage Map (All Identified Issues Included)

- PostgREST write overhead -> Phase 2 Steps 1-2
- Cross-region latency -> Phase 1 Step 2, Phase 3 Step 2
- HNSW insert cost -> Phase 2 Step 3, Phase 3 Step 4
- Progress update amplification -> Phase 1 Step 3, Phase 2 Step 8
- Embedding throttling/sync calls -> Phase 1 Step 4, Phase 2 Step 6
- Worker pool mismatch -> Phase 2 Step 4
- Chord/result overhead -> Phase 1 Step 7, Phase 2 Step 3
- Non-streamed ingestion/OOM -> Phase 1 Step 9, Phase 2 Step 5
- No connection pooling -> Phase 2 Step 1
- No deduplication -> Phase 2 Step 7
- Connector rate limits/sequential fetch -> Phase 1 Step 6, Phase 2 Step 10
- DLQ retry thrash -> Phase 1 Step 8
- RLS/service key risk -> Phase 1 Step 10, Phase 2 Step 11
- OAuth token security -> Phase 2 Step 11, Phase 3 Step 9
- SSRF risk -> Phase 3 Step 6
- Parser CVEs -> Phase 3 Step 7
- Prompt injection/data exfil -> Phase 3 Step 8
- Sensitive logging -> Phase 1 Step 10
- Observability/SLOs -> Phase 1 Step 1, Phase 2 Step 12, Phase 3 Step 10
