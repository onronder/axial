# Phase 2 Implementation Tracker (Safe, RLS-Preserving)

Version: 2.0  
Date: January 12, 2026  
Scope: Execution tracker for the revised Phase 2 (Admission Control → Split Queues → Connector Hardening).  
Change log: Direct DB writes, staging tables, and deferred indexing are **archived/blocked** due to RLS risk and lack of current performance need.

Status key:  
- Status: TBD (set before start), In Progress, Blocked, Done  

---

## Overview & Guardrails
- RLS must never be bypassed; no direct Postgres writes without explicit tenant filters and a restricted role.  
- Priorities: (1) Multi-tenant fairness and protection, (2) Worker stability and cost control, (3) Connector quality.  
- Performance is currently within SLOs; speed optimizations are optional and must be feature-flagged.

---

## Step 1: Per-tenant admission control & quotas

Status: Done (core enforcement shipped)  
Owner: Backend  
Target start: 2026-01-12  
Target end: 2026-01-12  
Dependencies: Phase 1 complete  
Inputs required:  
- Quota model per tenant tier (rate, concurrency, volume): Completed (see QUOTA_LIMITS in backend/core/config.py)  
- Enforcement points (API ingest, queue dispatch) and overload behavior (reject/delay/degrade): Completed (403 on QuotaExceededError)  

Sub-task checklist:  
- [x] Define per-tenant quotas and burst caps by tier.  
- [x] Add admission checks at API ingestion endpoints.  
- [x] Enforce queue dispatch limits per tenant (pre-dispatch admission + active job count).  
- [x] Define overload behavior and user-facing errors (403 with reason, logged denials).  
- [ ] Add per-tenant usage metrics/alerts (Prometheus/Supabase).  
- [ ] Validate fairness under simulated multi-tenant load.  

Deliverables:  
- Admission control policy + configuration.  
- Metrics dashboard for per-tenant usage and rejections.  

Validation and acceptance:  
- No single tenant can monopolize workers/DB; SLOs remain stable under mixed load.  
- Clear, actionable user errors when throttled.  

Rollback or contingency:  
- Relax quotas or disable admission hooks via config/feature flag if valid workloads are blocked.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies (Railway/Vercel/Supabase).  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- ✅ QUOTA_LIMITS defined in backend/core/config.py (high-perception concurrency, TPM caps).  
- ✅ RLS-safe admission enforced in backend/api/v1/uploads.py and backend/api/v1/integrations.py (403 on QuotaExceededError; logs include org_id and reason).  
- ✅ org_usage table added via migration 20260112090000_high_perception_quotas.sql; teams.plan populated/defaulted to starter.  
- ✅ Usage increments on enqueue via increment_usage(); plan_code propagated to workers; embeddings throttle per-plan TPM.  
- ⏳ TODO: Add metrics/alerts and run multi-tenant load fairness drill.  

---

## Step 2: Split Celery queues by stage

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 1 completed  
Inputs required:  
- Queue naming convention and routing policy: TBD  
- Worker concurrency targets per stage: TBD  

Sub-task checklist:  
- [ ] Define parse, embed, and write queues plus routing rules.  
- [ ] Update task definitions to route correctly.  
- [ ] Configure separate worker processes per queue with tuned concurrency.  
- [ ] Add monitoring for queue depth and worker utilization.  
- [ ] Validate end-to-end ingestion with the new topology.  

Deliverables:  
- Queue topology and routing specification.  
- Worker deployment configuration.  

Validation and acceptance:  
- Queue backlogs remain bounded; no task starvation across stages.  

Rollback or contingency:  
- Revert to a single queue if routing introduces failures.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Step 3: Connector extensibility hardening

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 1 completed  
Inputs required:  
- Connector manifest schema (capabilities, scopes, limits): TBD  
- Conformance test requirements: TBD  

Sub-task checklist:  
- [ ] Define connector manifest schema and required metadata.  
- [ ] Standardize connector error/retry/limit interfaces.  
- [ ] Implement a connector test harness with core conformance checks.  
- [ ] Update existing connectors to conform to the manifest.  
- [ ] Document the connector integration process.  
- [ ] Validate with at least two existing connectors.  

Deliverables:  
- Connector manifest specification.  
- Connector test harness and docs.  

Validation and acceptance:  
- New connectors can be added without breaking ingestion; conformance tests pass.  

Rollback or contingency:  
- Allow legacy connectors temporarily if manifest changes cause failures.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Step 4: Buffered progress tracking

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 2 completed  
Inputs required:  
- Buffer store choice (Redis or event stream) and data model: TBD  
- Snapshot cadence and trigger conditions: TBD  

Sub-task checklist:  
- [ ] Define progress buffer schema/keys per job/file.  
- [ ] Implement buffered writes in workers.  
- [ ] Define snapshot policy to persist progress to DB.  
- [ ] Update frontend to read progress from snapshots.  
- [ ] Add recovery logic for crashes (rebuild from DB).  
- [ ] Add monitoring for buffer consistency and snapshot success.  

Deliverables:  
- Progress buffering design and implementation.  

Validation and acceptance:  
- DB write volume for progress is significantly reduced; progress remains accurate.  

Rollback or contingency:  
- Revert to direct DB updates if buffering introduces inconsistencies.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Step 5: True async embeddings (optional, gated by need)

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 2 completed  
Inputs required:  
- Chosen async client and concurrency policy: TBD  
- Provider limits for async calls: TBD  

Sub-task checklist:  
- [ ] Select/integrate async embedding client.  
- [ ] Implement concurrency controls with backpressure.  
- [ ] Replace sync executor usage with direct async calls.  
- [ ] Implement robust retry/error handling.  
- [ ] Update metrics to track async throughput/errors.  

Deliverables:  
- Updated embedding service layer.  
- Async embedding performance report.  

Validation and acceptance:  
- Throughput improves without exceeding provider limits; error rates remain within thresholds.  

Rollback or contingency:  
- Revert to previous embedding path if async errors increase.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- Optional; only if throughput becomes a bottleneck.  

---

## Step 6: File and chunk deduplication

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 2 completed  
Inputs required:  
- Hashing algorithm and canonicalization rules: TBD  
- Dedup behavior for duplicates (skip/link/version): TBD  

Sub-task checklist:  
- [ ] Define file-level and chunk-level hash strategy.  
- [ ] Add hash fields to schema with uniqueness constraints.  
- [ ] Update ingestion pipeline to compute/check hashes.  
- [ ] Define behavior for duplicates and embeddings reuse.  
- [ ] Validate that duplicates do not re-trigger embeddings.  

Deliverables:  
- Dedup specification and schema updates.  

Validation and acceptance:  
- Duplicate content does not create duplicate chunks; no false positives blocking valid ingestion.  

Rollback or contingency:  
- Disable dedup if false positives block valid ingestion.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Step 7: Least-privilege DB roles for ingestion

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Step 1 completed  
Inputs required:  
- Role/permission model for ingestion operations: TBD  
- Secret storage and rotation policy: TBD  

Sub-task checklist:  
- [ ] Define least-privilege roles for ingestion (read/write scope only).  
- [ ] Update DB permissions accordingly.  
- [ ] Rotate and update secrets for workers.  
- [ ] Validate RLS behavior under the new role.  
- [ ] Add tests for cross-tenant access attempts.  

Deliverables:  
- Role and permission specification; updated secrets.  

Validation and acceptance:  
- Ingestion succeeds with the restricted role; cross-tenant access denied.  

Rollback or contingency:  
- Temporarily elevate permissions only to restore service, with explicit approval.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Step 8: Enterprise-scale load tests

Status: TBD  
Owner: TBD  
Target start: TBD  
Target end: TBD  
Dependencies: Steps 1-7 completed  
Inputs required:  
- Load model (file counts, sizes, concurrency): TBD  
- Target SLO thresholds: TBD  

Sub-task checklist:  
- [ ] Define load test scenarios for single-user and multi-tenant cases.  
- [ ] Prepare datasets and test environment.  
- [ ] Run load tests with monitoring enabled.  
- [ ] Analyze bottlenecks and confirm SLO compliance.  
- [ ] Document results and required tuning.  

Deliverables:  
- Load test report with SLO verification.  

Validation and acceptance:  
- SLOs met under defined load scenarios; no severe stability regressions.  

Rollback or contingency:  
- Delay release if SLOs are not met; revert specific changes as needed.  

Step completion check:  
- Review impacts on other modules and update references.  
- Verify environment/config dependencies.  
- Confirm migrations/infra updates reviewed.  
- Record verification outcome in Notes.  

Notes:  
- TBD  

---

## Archived / Deferred (Do Not Execute Now)
- **Direct Postgres pooled writes for ingestion**: Removed due to RLS bypass risk; only reconsider with restricted role + explicit tenant filters + feature flag.  
- **Staging tables for chunk writes**: Deferred; no current contention signal.  
- **Deferred/batched HNSW index updates**: Optional future experiment; only if write amplification becomes a proven bottleneck.  
