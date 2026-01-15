# Refactoring Plan WBS (Phase 1 and Phase 2)

Version: 1.0
Date: January 6, 2026
Scope: Detailed work breakdown for Phase 1 (Minimum) and Phase 2 (Balanced)

Rules for this document:
- No assumptions: any required values or choices are explicitly marked as input required.
- No skipped details: every step includes sub-tasks, deliverables, validation, and rollback.
- Full-stack coverage: frontend, backend API, workers, database, infra, security, observability, and ops are addressed where relevant.

---

## Phase 1 - Minimum (Target: ~80% uplift, no architecture change, go-live fast)

### Step 1: Define SLOs and baseline metrics

Objective: Establish measurable performance targets and a baseline before changes.
Dependencies: None.
Inputs required:
- Target SLO values for ingestion latency per file/job (p50/p95/p99).
- Acceptable queue wait time thresholds.
- Acceptable error rate thresholds.
- Representative workload definitions (file types, sizes, connectors).

Sub-tasks:
1) Inventory current ingestion stages and define precise measurement boundaries for: list, fetch, parse, chunk, embed, insert, status update.
2) Inventory existing telemetry sources (logs, Sentry, DB logs) and confirm what can be reused.
3) Define correlation identifiers for jobs, files, and chunks across services.
4) Define metric names, units, and labels for each stage (latency, counts, errors).
5) Define baseline workload scenarios (e.g., 15, 150, 1,500 files) and confirm datasets.
6) Draft the SLO document with target metrics and acceptable variance.
7) Define how baseline will be captured and stored (dashboards and reports).
8) Review SLOs with product, ops, and security stakeholders.

Deliverables:
- SLO document with target values and measurement definitions.
- Metrics specification with event boundaries and labels.
- Baseline workload definition.

Validation and acceptance:
- SLO document approved by stakeholders.
- Baseline metrics collected successfully for all defined stages.
- Correlation IDs present in logs across API and workers.

Rollback or contingency:
- If metrics instrumentation adds overhead, provide a toggle or sampling strategy.

---

### Step 2: Region alignment for DB and workers

Objective: Eliminate cross-region latency between Railway workers and Supabase.
Dependencies: Step 1 completed.
Inputs required:
- Current Railway region(s) for API and workers.
- Current Supabase region and migration options.
- Downtime tolerance and migration window policy.

Sub-tasks:
1) Confirm current deployment regions for Railway services.
2) Confirm current Supabase project region and migration capabilities.
3) Evaluate options: move Railway to Supabase region or migrate Supabase to Railway region.
4) Assess data migration risks and requirements (backup, restore, cutover).
5) Define a cutover plan and rollback plan.
6) Update environment variables and connection endpoints.
7) Validate connectivity and measure latency post-change.
8) Update monitoring dashboards to capture new RTT baselines.

Deliverables:
- Region alignment decision record.
- Migration plan with cutover and rollback steps.
- Post-change latency report.

Validation and acceptance:
- Worker to DB RTT reduced to target threshold.
- No data loss during migration.
- All services connect successfully after cutover.

Rollback or contingency:
- Revert to prior region using backup/restore if latency or stability degrades.

---

### Step 3: Stage-based progress updates (no per-chunk writes)

Objective: Provide granular stage updates while avoiding per-chunk write amplification.
Dependencies: Step 1 completed.
Inputs required:
- Approved progress milestone definitions and UI behavior.

Sub-tasks:
1) Inventory all current ingestion status update points in workers.
2) Define the new milestone-only update policy and mapping to UI states.
3) Update status update logic to only write on milestone changes.
4) Ensure job-level progress uses aggregated metrics rather than per-chunk updates.
5) Update frontend progress UI to align with milestone granularity.
6) Update Supabase realtime subscriptions to filter only milestone updates.
7) Verify that progress information remains accurate and non-misleading.
8) Add metrics for update count per job.

Deliverables:
- Updated progress update policy document.
- Frontend UI specification for milestone progress.

Validation and acceptance:
- DB write count for progress reduced by agreed threshold.
- UI displays consistent status transitions without regressions.

Rollback or contingency:
- Restore previous update cadence if progress tracking becomes unusable.

---

### Step 4: Increase embedding batch size and concurrency

Objective: Increase embedding throughput within provider rate limits.
Dependencies: Step 1 completed.
Inputs required:
- Current embedding provider limits and quotas.
- Maximum acceptable request size and concurrency per provider.

Sub-tasks:
1) Audit current embedding configuration (batch size, concurrency, sleeps).
2) Define target batch size and concurrency based on provider limits.
3) Replace fixed sleep with adaptive throttling behavior.
4) Implement error handling for rate-limit responses and retries.
5) Add metrics for embedding throughput and error rates.
6) Validate throughput on staging workloads.

Deliverables:
- Embedding configuration update plan.
- Metrics dashboard for embedding throughput.

Validation and acceptance:
- Throughput improves without violating provider limits.
- Error rates remain within thresholds.

Rollback or contingency:
- Revert to previous configuration if rate limits or errors increase.

---

### Step 5: Increase chunk insert batch size (still PostgREST)

Objective: Reduce the number of PostgREST calls for chunk inserts.
Dependencies: Step 1 completed.
Inputs required:
- PostgREST request size limits.
- Supabase limits on payload size and request rate.

Sub-tasks:
1) Audit current batch size and insert frequency.
2) Determine safe maximum batch size per request.
3) Update batching logic to the new size.
4) Add retry handling for partial failures.
5) Track insert latency and error rate metrics.

Deliverables:
- Updated batching configuration.
- Insert latency report.

Validation and acceptance:
- Total PostgREST insert calls reduced as expected.
- No increase in failure rate for inserts.

Rollback or contingency:
- Revert to prior batch size if payload limits are exceeded.

---

### Step 6: Constrain connector concurrency and retries

Objective: Prevent connector rate limits and reduce idle worker time.
Dependencies: Step 1 completed.
Inputs required:
- Documented rate limits for each connector provider.
- Desired retry and backoff policy.

Sub-tasks:
1) Inventory connector list/fetch calls and their concurrency patterns.
2) Define per-connector concurrency caps.
3) Implement exponential backoff with jitter for rate limit responses.
4) Add metrics for rate limit errors and retries per connector.
5) Validate connector behavior under load.

Deliverables:
- Connector concurrency policy.
- Connector error and retry metrics.

Validation and acceptance:
- Rate-limit errors decrease.
- Connector throughput remains stable.

Rollback or contingency:
- Revert to prior concurrency settings if performance regresses.

---

### Step 7: Reduce Celery chord/result overhead

Objective: Minimize Redis and Celery result backend overhead for large fan-out jobs.
Dependencies: Step 1 completed.
Inputs required:
- Current Celery configuration and result backend settings.

Sub-tasks:
1) Audit current chord usage and result backend storage size.
2) Define job-level counters stored in Redis for completion tracking.
3) Implement atomic increment/decrement operations for job progress.
4) Update finalize logic to use counters instead of chord results.
5) Add monitoring for counter drift and reconciliation logic.
6) Validate completion correctness under failure and retry scenarios.

Deliverables:
- Updated orchestration design.
- Redis counter metrics and alerts.

Validation and acceptance:
- Reduced Redis memory usage during large jobs.
- Job completion and failure handling remains correct.

Rollback or contingency:
- Restore chord-based finalization if counters become inconsistent.

---

### Step 8: Add ingestion idempotency and strict retry policy

Objective: Prevent reprocessing storms and duplicate writes.
Dependencies: Step 1 completed.
Inputs required:
- Idempotency scope definition (job, file, chunk).
- Retry policy and backoff settings.

Sub-tasks:
1) Define idempotency keys and lifecycle for jobs, files, and chunks.
2) Update ingestion API to accept or generate idempotency keys.
3) Implement idempotency checks before processing and inserting.
4) Define retry policies for transient vs permanent errors.
5) Ensure DLQ preserves idempotency context.
6) Add metrics for duplicate detection and retry counts.

Deliverables:
- Idempotency specification.
- Retry policy document.

Validation and acceptance:
- Duplicate ingestion attempts do not create duplicate data.
- Retries stop after the defined policy.

Rollback or contingency:
- Disable idempotency checks only if they cause false negatives and block valid ingestion.

---

### Step 9: Add parser safety guardrails

Objective: Prevent parser OOM and long-running tasks.
Dependencies: Step 1 completed.
Inputs required:
- Max file size per file type and parser.
- Timeout thresholds per parser.

Sub-tasks:
1) Inventory supported file types and associated parsers.
2) Define safe file size limits and timeouts for each parser.
3) Implement early exits for risky or oversized files.
4) Define how the system reports partial or skipped parsing.
5) Add metrics for parser timeouts and file rejections.

Deliverables:
- Parser safety policy.
- Updated worker parsing behavior.

Validation and acceptance:
- No OOMs on large or malformed files.
- Clear error reporting for rejected files.

Rollback or contingency:
- Adjust thresholds if valid files are rejected too aggressively.

---

### Step 10: Security quick wins

Objective: Reduce immediate security risks with minimal changes.
Dependencies: Step 1 completed.
Inputs required:
- Current list of secrets, keys, and rotation policies.
- Current RLS policy inventory.
- Current CORS rules and allowed origins.

Sub-tasks:
1) Inventory all secrets and access keys used by API and workers.
2) Rotate secrets and update deployments.
3) Audit RLS policies for all ingestion-related tables.
4) Add or update tests that validate cross-tenant isolation.
5) Identify sensitive fields in logs and DLQ payloads.
6) Implement log and DLQ redaction for sensitive fields.
7) Review and tighten CORS configuration.
8) Validate that changes do not break ingestion or UI flows.

Deliverables:
- Secret rotation log.
- RLS audit report.
- Logging redaction policy.

Validation and acceptance:
- No unauthorized cross-tenant reads or writes in tests.
- Secrets rotated and verified across all services.

Rollback or contingency:
- Roll back CORS or policy changes if they block valid traffic, with a documented fix path.

---

### Step 11: Benchmark and release gates

Objective: Validate performance gains and define release readiness.
Dependencies: Steps 2-10 completed.
Inputs required:
- Benchmark dataset definitions and test harness selection.
- Release gate thresholds.

Sub-tasks:
1) Define benchmark scenarios and datasets for 15, 150, 1,500 files.
2) Implement or configure a repeatable benchmark harness.
3) Run baseline benchmarks and record results.
4) Run post-change benchmarks and compare results.
5) Define release gate thresholds and publish results.
6) Prepare rollback plan if SLOs are not met.

Deliverables:
- Benchmark report (baseline vs post-change).
- Release gate checklist.

Validation and acceptance:
- Target performance improvement achieved.
- Release gates satisfied with documented evidence.

Rollback or contingency:
- Roll back to previous build if performance or stability regresses.

---

## Dependency Graphs

Phase 1 dependencies (adjacency list):
```
1 -> 2, 3, 4, 5, 6, 7, 8, 9, 10
2 -> 11
3 -> 11
4 -> 11
5 -> 11
6 -> 11
7 -> 11
8 -> 11
9 -> 11
10 -> 11
```

Phase 2 dependencies (adjacency list):
```
P1_COMPLETE -> 1
1 -> 2, 4, 9, 10, 11, 12
2 -> 3
4 -> 5, 6, 8
5 -> 7
1 -> 12
2 -> 12
3 -> 12
4 -> 12
5 -> 12
6 -> 12
7 -> 12
8 -> 12
9 -> 12
10 -> 12
11 -> 12
```

## Phase 2 - Balanced (Sellable release, same architecture)

### Step 1: Direct Postgres pooled writes for ingestion

Objective: Remove PostgREST overhead for ingestion writes.
Dependencies: Phase 1 complete.
Inputs required:
- Confirmation that direct DB access is allowed from Railway.
- DB credentials and role strategy for ingestion.
- Connection pool sizing limits for Supabase.

Sub-tasks:
1) Validate network access from workers to Supabase Postgres.
2) Select a DB client library with pooling compatible with worker runtime.
3) Define pool size and connection lifetime policies.
4) Create or update a dedicated ingestion DB role with least privilege.
5) Update worker configuration to use the direct connection for ingestion writes.
6) Ensure all queries enforce tenant isolation (RLS or explicit filters).
7) Add metrics for write latency and pool health.

Deliverables:
- DB access and pooling design.
- Updated worker DB connection configuration.

Validation and acceptance:
- Ingestion write latency reduced compared to PostgREST.
- Connection pool does not exceed DB limits.
- Tenant isolation is verified.

Rollback or contingency:
- Fall back to PostgREST if direct DB access causes stability issues.

---

### Step 2: Staging tables for chunk writes

Objective: Improve ingestion throughput by staging bulk inserts.
Dependencies: Phase 2 Step 1.
Inputs required:
- Staging table schema design.
- Data retention and cleanup policy for staging tables.

Sub-tasks:
1) Define staging table schema for document chunks (no index).
2) Create migration for staging tables and permissions.
3) Update ingestion write path to insert into staging tables.
4) Implement bulk move from staging to final indexed table.
5) Define cleanup process for staging data after move.
6) Add integrity checks for moved data.

Deliverables:
- Staging table migration.
- Staging-to-final move procedure.

Validation and acceptance:
- Bulk insert throughput improves measurably.
- No data loss or duplication during move.

Rollback or contingency:
- Disable staging and write directly to final table if staging introduces issues.

---

### Step 3: Defer or batch HNSW index updates

Objective: Reduce insert overhead caused by HNSW maintenance.
Dependencies: Phase 2 Step 2.
Inputs required:
- Approved indexing strategy (deferred rebuild vs batched updates).
- Query freshness tolerance and rebuild windows.

Sub-tasks:
1) Measure current HNSW maintenance cost during ingestion.
2) Define the indexing strategy and acceptable freshness delay.
3) Implement scheduled or batched index rebuilds if chosen.
4) Update ingestion pipeline to align with chosen strategy.
5) Validate query accuracy and performance post-index rebuild.

Deliverables:
- Indexing strategy document.
- Operational runbook for index maintenance.

Validation and acceptance:
- Insert latency reduced without unacceptable query degradation.
- Index rebuild process is reliable and repeatable.

Rollback or contingency:
- Revert to immediate index updates if query quality degrades.

---

### Step 4: Split Celery queues by stage

Objective: Isolate CPU and IO workloads for predictable throughput.
Dependencies: Phase 2 Step 1.
Inputs required:
- Queue naming convention and routing policy.
- Worker concurrency targets per stage.

Sub-tasks:
1) Define parse, embed, and write queues and routing rules.
2) Update task definitions to route to the correct queue.
3) Configure separate worker processes for each queue.
4) Tune concurrency per worker type.
5) Add monitoring for queue depth and worker utilization.
6) Validate end-to-end ingestion with the new queue topology.

Deliverables:
- Queue topology and routing specification.
- Worker deployment configuration.

Validation and acceptance:
- Queue backlogs remain bounded under load.
- No task starvation across stages.

Rollback or contingency:
- Revert to a single queue if new routing introduces failures.

---

### Step 5: Streaming ingestion pipeline

Objective: Avoid loading full files in memory and improve throughput.
Dependencies: Phase 2 Step 4.
Inputs required:
- Streaming boundaries per file type.
- Partial ingestion behavior for large files.

Sub-tasks:
1) Define streaming API for connectors and parsers.
2) Update connector fetch to provide streamable content where possible.
3) Update parser to emit chunks incrementally.
4) Implement backpressure to avoid memory spikes.
5) Update progress reporting to align with streaming stages.
6) Validate large file ingestion without OOM.

Deliverables:
- Streaming ingestion design.
- Updated worker pipeline behavior.

Validation and acceptance:
- Large files are processed without OOM.
- Chunk output remains consistent with previous behavior.

Rollback or contingency:
- Fall back to non-streaming mode if streaming introduces regressions.

---

### Step 6: True async embeddings

Objective: Remove sync bottlenecks and improve embedding throughput.
Dependencies: Phase 2 Step 4.
Inputs required:
- Chosen async client and concurrency policy.
- Provider limits for async calls.

Sub-tasks:
1) Select and integrate an async embedding client.
2) Implement concurrency controls with backpressure.
3) Replace sync executor usage with direct async calls.
4) Implement robust retry and error handling for async requests.
5) Update metrics to track async throughput and errors.

Deliverables:
- Updated embedding service layer.
- Async embedding performance report.

Validation and acceptance:
- Throughput improves without exceeding provider limits.
- Error rates remain within thresholds.

Rollback or contingency:
- Revert to previous embedding path if async errors increase.

---

### Step 7: File and chunk deduplication

Objective: Avoid re-embedding and re-indexing duplicate content.
Dependencies: Phase 2 Step 5.
Inputs required:
- Hashing algorithm and canonicalization rules.
- Deduplication behavior for duplicates (skip, link, or version).

Sub-tasks:
1) Define file-level and chunk-level hash strategy.
2) Add hash fields to storage schema with uniqueness constraints.
3) Update ingestion pipeline to compute and check hashes.
4) Define behavior for duplicates (skip, link to existing, or store new).
5) Validate that duplicates do not re-trigger embeddings.

Deliverables:
- Deduplication specification.
- Schema updates for hash fields.

Validation and acceptance:
- Duplicate content does not create duplicate chunks.
- Dedup does not block valid new content.

Rollback or contingency:
- Disable dedup if false positives block valid ingestion.

---

### Step 8: Buffered progress tracking

Objective: Reduce DB writes by buffering progress and snapshotting periodically.
Dependencies: Phase 2 Step 4.
Inputs required:
- Choice of buffer store (Redis or event stream) and data model.
- Snapshot cadence and trigger conditions.

Sub-tasks:
1) Define progress buffer schema and keys per job/file.
2) Implement buffered writes in workers.
3) Define snapshot policy to persist progress to DB.
4) Update frontend to read progress from snapshots.
5) Add recovery logic for crashes (rebuild progress from DB).
6) Add monitoring for buffer consistency and snapshot success.

Deliverables:
- Progress buffering design.
- Updated progress update flow.

Validation and acceptance:
- DB write volume for progress reduced significantly.
- Progress display remains accurate under failure conditions.

Rollback or contingency:
- Revert to direct DB updates if buffering introduces inconsistencies.

---

### Step 9: Per-tenant admission control

Objective: Prevent heavy tenants from starving others.
Dependencies: Phase 2 Step 1.
Inputs required:
- Quota model per tenant tier.
- Enforcement points and desired behavior under load.

Sub-tasks:
1) Define per-tenant quotas (rate, concurrency, or volume).
2) Implement admission checks at API ingestion endpoints.
3) Enforce queue dispatch limits per tenant.
4) Define overload behavior (reject, delay, or degrade).
5) Add per-tenant usage metrics and alerts.
6) Validate fairness under simulated multi-tenant load.

Deliverables:
- Admission control policy.
- Metrics dashboard for per-tenant usage.

Validation and acceptance:
- No single tenant can monopolize workers or DB.
- SLOs remain stable across tenants under load.

Rollback or contingency:
- Adjust or relax quotas if valid workloads are blocked.

---

### Step 10: Connector extensibility hardening

Objective: Enable rapid connector addition without regressions.
Dependencies: Phase 2 Step 1.
Inputs required:
- Connector manifest schema (capabilities, scopes, limits).
- Conformance test requirements.

Sub-tasks:
1) Define a connector manifest schema and required metadata.
2) Standardize connector error and retry interfaces.
3) Implement a connector test harness with core conformance checks.
4) Update existing connectors to conform to the manifest.
5) Document the connector integration process.
6) Validate using at least two existing connectors.

Deliverables:
- Connector manifest specification.
- Connector test harness.
- Connector integration guide.

Validation and acceptance:
- New connectors can be added without breaking ingestion.
- Conformance tests pass for existing connectors.

Rollback or contingency:
- Allow legacy connectors temporarily if manifest changes cause failures.

---

### Step 11: Least-privilege DB roles for ingestion

Objective: Reduce risk from ingestion credentials.
Dependencies: Phase 2 Step 1.
Inputs required:
- Role and permission model for ingestion operations.
- Secret storage and rotation policy.

Sub-tasks:
1) Define least-privilege roles for ingestion (read/write scope only).
2) Update DB permissions accordingly.
3) Rotate and update secrets for workers.
4) Validate RLS behavior under the new role.
5) Add tests for cross-tenant access attempts.

Deliverables:
- Role and permission specification.
- Updated secrets and access configuration.

Validation and acceptance:
- Ingestion operations succeed with the restricted role.
- Cross-tenant access is denied in tests.

Rollback or contingency:
- Temporarily elevate permissions only if required to restore service, with explicit approval.

---

### Step 12: Enterprise-scale load tests

Objective: Validate Phase 2 under 1,000-person agent workloads.
Dependencies: Phase 2 Steps 1-11.
Inputs required:
- Load model (file counts, sizes, concurrency).
- Target SLO thresholds.

Sub-tasks:
1) Define load test scenarios for single-user and multi-tenant cases.
2) Prepare datasets and test environment.
3) Run load tests with monitoring enabled.
4) Analyze bottlenecks and confirm SLO compliance.
5) Document results and required tuning.

Deliverables:
- Load test report with SLO verification.
- Tuning recommendations.

Validation and acceptance:
- SLOs met under defined load scenarios.
- No severe stability regressions.

Rollback or contingency:
- Delay release if SLOs are not met; revert specific changes as needed.
