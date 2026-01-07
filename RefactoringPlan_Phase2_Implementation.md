# Phase 2 Implementation Tracker (Balanced)

Version: 1.0
Date: January 6, 2026
Scope: Phase 2 execution tracking for RefactoringPlan.md
Reference: RefactoringPlan_Phase1_2_WBS.md

Status key:
- Status: TBD (set before start), In Progress, Blocked, Done

---

## Step 1: Direct Postgres pooled writes for ingestion

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 1 complete
Inputs required:
- Confirmation that direct DB access is allowed from Railway.
- DB credentials and role strategy for ingestion.
- Connection pool sizing limits for Supabase.

User inputs (fill below):
- Confirmation that direct DB access is allowed from Railway: TBD
- DB credentials and role strategy for ingestion: TBD
- Connection pool sizing limits for Supabase: TBD

Sub-task checklist:
- [ ] Validate network access from workers to Supabase Postgres.
- [ ] Select a DB client library with pooling compatible with worker runtime.
- [ ] Define pool size and connection lifetime policies.
- [ ] Create or update a dedicated ingestion DB role with least privilege.
- [ ] Update worker configuration to use the direct connection for ingestion writes.
- [ ] Ensure all queries enforce tenant isolation (RLS or explicit filters).
- [ ] Add metrics for write latency and pool health.

Deliverables:
- DB access and pooling design.
- Updated worker DB connection configuration.

Validation and acceptance:
- Ingestion write latency reduced compared to PostgREST.
- Connection pool does not exceed DB limits.
- Tenant isolation is verified.

Rollback or contingency:
- Fall back to PostgREST if direct DB access causes stability issues.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 2: Staging tables for chunk writes

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 1 completed
Inputs required:
- Staging table schema design.
- Data retention and cleanup policy for staging tables.

User inputs (fill below):
- Staging table schema design: TBD
- Data retention and cleanup policy for staging tables: TBD

Sub-task checklist:
- [ ] Define staging table schema for document chunks (no index).
- [ ] Create migration for staging tables and permissions.
- [ ] Update ingestion write path to insert into staging tables.
- [ ] Implement bulk move from staging to final indexed table.
- [ ] Define cleanup process for staging data after move.
- [ ] Add integrity checks for moved data.

Deliverables:
- Staging table migration.
- Staging-to-final move procedure.

Validation and acceptance:
- Bulk insert throughput improves measurably.
- No data loss or duplication during move.

Rollback or contingency:
- Disable staging and write directly to final table if staging introduces issues.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 3: Defer or batch HNSW index updates

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 2 completed
Inputs required:
- Approved indexing strategy (deferred rebuild vs batched updates).
- Query freshness tolerance and rebuild windows.

User inputs (fill below):
- Approved indexing strategy (deferred rebuild vs batched updates): TBD
- Query freshness tolerance and rebuild windows: TBD

Sub-task checklist:
- [ ] Measure current HNSW maintenance cost during ingestion.
- [ ] Define the indexing strategy and acceptable freshness delay.
- [ ] Implement scheduled or batched index rebuilds if chosen.
- [ ] Update ingestion pipeline to align with chosen strategy.
- [ ] Validate query accuracy and performance post-index rebuild.

Deliverables:
- Indexing strategy document.
- Operational runbook for index maintenance.

Validation and acceptance:
- Insert latency reduced without unacceptable query degradation.
- Index rebuild process is reliable and repeatable.

Rollback or contingency:
- Revert to immediate index updates if query quality degrades.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 4: Split Celery queues by stage

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 1 completed
Inputs required:
- Queue naming convention and routing policy.
- Worker concurrency targets per stage.

User inputs (fill below):
- Queue naming convention and routing policy: TBD
- Worker concurrency targets per stage: TBD

Sub-task checklist:
- [ ] Define parse, embed, and write queues and routing rules.
- [ ] Update task definitions to route to the correct queue.
- [ ] Configure separate worker processes for each queue.
- [ ] Tune concurrency per worker type.
- [ ] Add monitoring for queue depth and worker utilization.
- [ ] Validate end-to-end ingestion with the new queue topology.

Deliverables:
- Queue topology and routing specification.
- Worker deployment configuration.

Validation and acceptance:
- Queue backlogs remain bounded under load.
- No task starvation across stages.

Rollback or contingency:
- Revert to a single queue if new routing introduces failures.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 5: Streaming ingestion pipeline

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 4 completed
Inputs required:
- Streaming boundaries per file type.
- Partial ingestion behavior for large files.

User inputs (fill below):
- Streaming boundaries per file type: TBD
- Partial ingestion behavior for large files: TBD

Sub-task checklist:
- [ ] Define streaming API for connectors and parsers.
- [ ] Update connector fetch to provide streamable content where possible.
- [ ] Update parser to emit chunks incrementally.
- [ ] Implement backpressure to avoid memory spikes.
- [ ] Update progress reporting to align with streaming stages.
- [ ] Validate large file ingestion without OOM.

Deliverables:
- Streaming ingestion design.
- Updated worker pipeline behavior.

Validation and acceptance:
- Large files are processed without OOM.
- Chunk output remains consistent with previous behavior.

Rollback or contingency:
- Fall back to non-streaming mode if streaming introduces regressions.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 6: True async embeddings

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 4 completed
Inputs required:
- Chosen async client and concurrency policy.
- Provider limits for async calls.

User inputs (fill below):
- Chosen async client and concurrency policy: TBD
- Provider limits for async calls: TBD

Sub-task checklist:
- [ ] Select and integrate an async embedding client.
- [ ] Implement concurrency controls with backpressure.
- [ ] Replace sync executor usage with direct async calls.
- [ ] Implement robust retry and error handling for async requests.
- [ ] Update metrics to track async throughput and errors.

Deliverables:
- Updated embedding service layer.
- Async embedding performance report.

Validation and acceptance:
- Throughput improves without exceeding provider limits.
- Error rates remain within thresholds.

Rollback or contingency:
- Revert to previous embedding path if async errors increase.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 7: File and chunk deduplication

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 5 completed
Inputs required:
- Hashing algorithm and canonicalization rules.
- Deduplication behavior for duplicates (skip, link, or version).

User inputs (fill below):
- Hashing algorithm and canonicalization rules: TBD
- Deduplication behavior for duplicates (skip, link, or version): TBD

Sub-task checklist:
- [ ] Define file-level and chunk-level hash strategy.
- [ ] Add hash fields to storage schema with uniqueness constraints.
- [ ] Update ingestion pipeline to compute and check hashes.
- [ ] Define behavior for duplicates (skip, link to existing, or store new).
- [ ] Validate that duplicates do not re-trigger embeddings.

Deliverables:
- Deduplication specification.
- Schema updates for hash fields.

Validation and acceptance:
- Duplicate content does not create duplicate chunks.
- Dedup does not block valid new content.

Rollback or contingency:
- Disable dedup if false positives block valid ingestion.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 8: Buffered progress tracking

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 4 completed
Inputs required:
- Choice of buffer store (Redis or event stream) and data model.
- Snapshot cadence and trigger conditions.

User inputs (fill below):
- Choice of buffer store (Redis or event stream) and data model: TBD
- Snapshot cadence and trigger conditions: TBD

Sub-task checklist:
- [ ] Define progress buffer schema and keys per job/file.
- [ ] Implement buffered writes in workers.
- [ ] Define snapshot policy to persist progress to DB.
- [ ] Update frontend to read progress from snapshots.
- [ ] Add recovery logic for crashes (rebuild progress from DB).
- [ ] Add monitoring for buffer consistency and snapshot success.

Deliverables:
- Progress buffering design.
- Updated progress update flow.

Validation and acceptance:
- DB write volume for progress reduced significantly.
- Progress display remains accurate under failure conditions.

Rollback or contingency:
- Revert to direct DB updates if buffering introduces inconsistencies.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 9: Per-tenant admission control

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 1 completed
Inputs required:
- Quota model per tenant tier.
- Enforcement points and desired behavior under load.

User inputs (fill below):
- Quota model per tenant tier: TBD
- Enforcement points and desired behavior under load: TBD

Sub-task checklist:
- [ ] Define per-tenant quotas (rate, concurrency, or volume).
- [ ] Implement admission checks at API ingestion endpoints.
- [ ] Enforce queue dispatch limits per tenant.
- [ ] Define overload behavior (reject, delay, or degrade).
- [ ] Add per-tenant usage metrics and alerts.
- [ ] Validate fairness under simulated multi-tenant load.

Deliverables:
- Admission control policy.
- Metrics dashboard for per-tenant usage.

Validation and acceptance:
- No single tenant can monopolize workers or DB.
- SLOs remain stable across tenants under load.

Rollback or contingency:
- Adjust or relax quotas if valid workloads are blocked.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 10: Connector extensibility hardening

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 1 completed
Inputs required:
- Connector manifest schema (capabilities, scopes, limits).
- Conformance test requirements.

User inputs (fill below):
- Connector manifest schema (capabilities, scopes, limits): TBD
- Conformance test requirements: TBD

Sub-task checklist:
- [ ] Define a connector manifest schema and required metadata.
- [ ] Standardize connector error and retry interfaces.
- [ ] Implement a connector test harness with core conformance checks.
- [ ] Update existing connectors to conform to the manifest.
- [ ] Document the connector integration process.
- [ ] Validate using at least two existing connectors.

Deliverables:
- Connector manifest specification.
- Connector test harness.
- Connector integration guide.

Validation and acceptance:
- New connectors can be added without breaking ingestion.
- Conformance tests pass for existing connectors.

Rollback or contingency:
- Allow legacy connectors temporarily if manifest changes cause failures.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 11: Least-privilege DB roles for ingestion

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Step 1 completed
Inputs required:
- Role and permission model for ingestion operations.
- Secret storage and rotation policy.

User inputs (fill below):
- Role and permission model for ingestion operations: TBD
- Secret storage and rotation policy: TBD

Sub-task checklist:
- [ ] Define least-privilege roles for ingestion (read/write scope only).
- [ ] Update DB permissions accordingly.
- [ ] Rotate and update secrets for workers.
- [ ] Validate RLS behavior under the new role.
- [ ] Add tests for cross-tenant access attempts.

Deliverables:
- Role and permission specification.
- Updated secrets and access configuration.

Validation and acceptance:
- Ingestion operations succeed with the restricted role.
- Cross-tenant access is denied in tests.

Rollback or contingency:
- Temporarily elevate permissions only if required to restore service, with explicit approval.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 12: Enterprise-scale load tests

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Phase 2 Steps 1-11 completed
Inputs required:
- Load model (file counts, sizes, concurrency).
- Target SLO thresholds.

User inputs (fill below):
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
- Tuning recommendations.

Validation and acceptance:
- SLOs met under defined load scenarios.
- No severe stability regressions.

Rollback or contingency:
- Delay release if SLOs are not met; revert specific changes as needed.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD

