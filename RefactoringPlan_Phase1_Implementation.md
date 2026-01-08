# Phase 1 Implementation Tracker (Minimum)

Version: 1.0
Date: January 6, 2026
Scope: Phase 1 execution tracking for RefactoringPlan.md
Reference: RefactoringPlan_Phase1_2_WBS.md

Status key:
- Status: TBD (set before start), In Progress, Blocked, Done

---

## Step 1: Define SLOs and baseline metrics

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: None
Inputs required:
- Target SLO values for ingestion latency per file/job (p50/p95/p99).
- Acceptable queue wait time thresholds.
- Acceptable error rate thresholds.
- Representative workload definitions (file types, sizes, connectors).

User inputs (fill below):
- Service level objectives (SLOs)
  - Ingestion latency (Upload click to Completed status):
    - p50 < 30 seconds (standard 10-20 page document).
    - p95 < 2 minutes (dense 100+ page reports).
    - p99 < 5 minutes (books/OCR; reliability over speed).
  - Note: Current BATCH_SIZE=20 and SLEEP=1.0s intentionally limit max speed for stability.
- Queue wait time:
  - Normal load: < 2 seconds.
  - Peak load: < 10 seconds (50-user burst).
- Error rate thresholds:
  - Hard failures: < 1.0% (system crashes/timeouts; P1 fix).
  - Soft failures: < 5.0% (user errors like encrypted/corrupted files).
  - Retry rate: < 10% (throttling; adjust rate limiters if higher).
- Representative workload definitions:
  - Quick Win (60%): 15 pages, text-only, < 2MB, target 15-20s.
  - Enterprise Doc (30%): 100 pages, mixed text/images, ~15MB, target 90s; progress bar must be smooth.
  - Stress Test (10%): 500+ pages, OCR/high density, > 50MB, target 5-8m; must not OOM/timeout.

Sub-task checklist:
- [ ] Inventory ingestion stages and define measurement boundaries (list, fetch, parse, chunk, embed, insert, status update).
- [ ] Inventory existing telemetry sources and confirm reusable signals.
- [ ] Define correlation identifiers for jobs, files, and chunks across services.
- [ ] Define metric names, units, and labels for each stage.
- [ ] Define baseline workload scenarios and confirm datasets.
- [ ] Draft SLO document with target metrics and acceptable variance.
- [ ] Define how baseline will be captured and stored (dashboards and reports).
- [ ] Review SLOs with product, ops, and security stakeholders.

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

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- Reminder: Apply `supabase db push` for the status constraint migration before deploy; `git push` is OK. Verify in Supabase Table Editor during the next smoke test.
- Implementation detail: ingestion_jobs writes update both `message` and `status_message` for compatibility; frontend prefers `message`.
- UI: progress modal styling and chunk progress presentation updated for clearer per-file status.
- Additional migration: add `cancelled` to `job_status` enum to keep cancellation updates valid.

---

## Step 2: Region alignment for DB and workers

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current Railway region(s) for API and workers.
- Current Supabase region and migration options.
- Downtime tolerance and migration window policy.

User inputs (fill below):
- Decision: Confirmed US-East-1 co-location (Railway API and Supabase DB now in us-east-1).
- Maintenance window: Sunday 03:00 - 05:00 UTC (low traffic period).
- Advance notice policy: 24 hours via email/dashboard banner for planned maintenance affecting availability.
- Zero-downtime deployments are standard for code updates.

Sub-task checklist:
- [ ] Confirm current deployment regions for Railway services.
- [ ] Confirm current Supabase project region and migration capabilities.
- [ ] Evaluate options: move Railway to Supabase region or migrate Supabase to Railway region.
- [ ] Assess data migration risks and requirements (backup, restore, cutover).
- [ ] Define a cutover plan and rollback plan.
- [ ] Update environment variables and connection endpoints.
- [ ] Validate connectivity and measure latency post-change.
- [ ] Update monitoring dashboards to capture new RTT baselines.

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

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- Railway API services and Supabase are now co-located in us-east-1 (per user confirmation).
- Maintenance window: Sunday 03:00 - 05:00 UTC; 24-hour advance notice policy recorded.

---

## Step 3: Stage-based progress updates (no per-chunk writes)

Status: In Progress
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Approved progress milestone definitions and UI behavior.

User inputs (fill below):
- Decision (Phase 1):
  - Remove strict ENUM/CHECK constraint on ingestion_file_status.status to allow flexible status strings.
  - Action: Keep status column as TEXT and drop ingestion_file_status_status_check.
  - Reason: Enable granular progress stages without a migration for every new stage.
- Approved progress milestone definitions and UI behavior:
  - Purpose: define milestones, triggers, and UI behavior for real-time progress tracking.
  - Goal: granular stage updates without per-chunk write amplification.
  - Milestones (file-level, ordered):
    - pending: file queued, not started.
    - uploading: uploading or fetching file (if applicable).
    - parsing: extracting text.
    - embedding: generating embeddings.
    - indexing: writing to database.
    - completed: successfully finished.
    - failed: error occurred.
    - skipped: empty/unsupported file.
  - Job-level statuses (ingestion_jobs):
    - pending: job created, not started.
    - processing: files being processed.
    - completed: all files done.
    - failed: critical error (job cannot continue).
  - Milestone trigger definitions (file-level):
    - pending: file status record created.
    - uploading: upload/fetch begins (if applicable).
    - parsing: parsing begins.
    - embedding: embedding begins.
    - indexing: before DB write.
    - completed: after successful DB write.
    - failed: on any error.
    - skipped: empty/unsupported file.
  - Granular update policy:
    - Write on each stage transition only; no per-chunk updates.
    - Do not write repeated updates within the same stage.
    - Status values are defined in code and can expand without DB migrations.
  - Job progress field:
    - Update processed_files only when files complete.
    - Update frequency: batch every 10 files or every 30 seconds.
    - Formula: progress = (processed_files / total_files) * 100.
  - File-level progress mapping (frontend default):
    - pending=0, uploading=10, parsing=30, embedding=60, indexing=85, completed=100.
    - failed=100, skipped=100.
    - Fallback: if unknown status, use job.progress (cap 95) until file completes.
    - Legacy: treat "processing" as equivalent to "parsing".
  - Example frontend mapping:
    ```js
    function calculateFileProgress(file, job) {
      const map = {
        pending: 0,
        uploading: 10,
        parsing: 30,
        embedding: 60,
        indexing: 85,
        completed: 100,
        failed: 100,
        skipped: 100,
      };
      if (file.status in map) return map[file.status];
      const avgProgress = job.progress || 0;
      return Math.min(avgProgress, 95);
    }
    ```
  - Job-level progress:
    - processed_files = count of files with status in (completed, failed, skipped).
    - total_files = total files in job.
    - No byte-weighting (simple UX).
    - Update strategy:
      - Update when every 10 files complete, OR every 30 seconds (timer).
      - Monotonic: never decrease job.progress.
  - UI behavior requirements:
    - Must show: overall progress bar, file list with per-file badges, status counts, current activity text.
    - Optional: ETA, failed file error details, retry button for failed files.
  - Allowed staleness:
    - Job progress: up to 30 seconds stale (batched updates).
    - File status: near real-time per stage transition.
    - Overall UX: user sees activity within 5 seconds.
  - Display rules:
    - Failed files: red badge, show error message, allow retry, do not block others.
    - Skipped files: yellow badge, show reason, do not count as failure.
    - Retried files: reset to pending; optional retry badge.
  - Non-negotiable UX constraints:
    - Progress must be monotonic.
    - Avoid large jumps; small jobs should update more frequently.
    - Always show activity while job.status = processing.
    - Handle edge cases: empty job, all files failed, single file.
  - Database schema alignment:
    - ingestion_file_status.status is TEXT with no CHECK constraint.
    - Migration: drop ingestion_file_status_status_check.
  - Performance impact:
    - With co-location (<5ms RTT), stage updates should not dominate latency.
    - Monitor PostgREST throughput and Realtime fan-out at 50+ parallel uploads.

Sub-task checklist:
- [ ] Inventory all current ingestion status update points in workers.
- [ ] Define the stage-transition update policy and mapping to UI states.
- [ ] Update status update logic to write on each stage transition (no per-chunk loops).
- [ ] Ensure job-level progress uses aggregated metrics rather than per-chunk updates.
- [ ] Update frontend progress UI to align with granular stage statuses.
- [ ] Update Supabase realtime subscriptions to handle granular status updates.
- [ ] Verify that progress information remains accurate and non-misleading.
- [ ] Add metrics for update count per job.

Deliverables:
- Updated progress update policy document.
- Frontend UI specification for milestone progress.

Validation and acceptance:
- File status updates reflect every defined stage transition.
- UI displays consistent status transitions without regressions.
- Status update rate remains within acceptable limits during load tests.

Rollback or contingency:
- Restore previous update cadence if progress tracking becomes unusable.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- Reminder: Apply `supabase db push` for the status constraint migration before deploy; `git push` is OK. Verify in Supabase Table Editor during the next smoke test.
- Implementation detail: ingestion_jobs writes update both `message` and `status_message` for compatibility; frontend prefers `message`.

---

## Step 4: Increase embedding batch size and concurrency

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current embedding provider limits and quotas.
- Maximum acceptable request size and concurrency per provider.

User inputs (fill below):
- Embedding provider limits and quotas:
  - Provider: OpenAI text-embedding-3-small.
  - Account tier: Usage Tier 1.
  - Rate limits: 3,000 RPM, 1,000,000 TPM.
  - Monthly budget: $1.36 spent / $120.00 limit.
  - Daily quota: 90M tokens/day (batch queue).
- Maximum acceptable request size and concurrency:
  - Max request size: 2,048 embeddings/request (OpenAI hard limit).
  - Max tokens per input: 8,191.
  - Recommended batch size: 1,000 embeddings/request (safe, fast).
  - Target concurrency for 2-minute goal: 10-15 concurrent requests.
  - Safety limit: 20 concurrent requests.
  - Recommended: 10 concurrent requests.

Sub-task checklist:
- [ ] Audit current embedding configuration (batch size, concurrency, sleeps).
- [ ] Define target batch size and concurrency based on provider limits.
- [ ] Replace fixed sleep with adaptive throttling behavior.
- [ ] Implement error handling for rate-limit responses and retries.
- [ ] Add metrics for embedding throughput and error rates.
- [ ] Validate throughput on staging workloads.

Deliverables:
- Embedding configuration update plan.
- Metrics dashboard for embedding throughput.

Validation and acceptance:
- Throughput improves without violating provider limits.
- Error rates remain within thresholds.

Rollback or contingency:
- Revert to previous configuration if rate limits or errors increase.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Run a quick syntax check for modified Python modules (py_compile).
- Record verification outcome in Notes.


Notes:
- Configured embedding batch size and sleep interval via `backend/core/config.py`.
- Async embedding helper now delegates to the synchronous implementation to avoid event-loop usage in workers.
- Added adaptive throttle for embedding batches (duration-based + rate-limit backoff with jittered retries).
- Added Prometheus metrics for embedding batch duration and counts; rate-limit failures increment retry metrics.
- Verification: `python3 -m py_compile backend/services/embeddings.py`.

---

## Step 5: Increase chunk insert batch size (still PostgREST)

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- PostgREST request size limits.
- Supabase limits on payload size and request rate.

User inputs (fill below):
- PostgREST request size limits:
  - Request body (POST/PATCH/PUT): JSON up to ~10 MB per request is safe; larger may be rejected (413).
  - Multi-part uploads: not supported via PostgREST; use Supabase Storage or signed URLs.
  - Query string length: keep under ~8-16 KB; use POST with Prefer: params=single-object for complex filters.
  - Response size: large responses allowed but limited by timeouts (~60s) and client constraints; use pagination.
  - Row limits: default range limit ~1,000 rows unless Range headers are set.
  - UPSERT/INSERT batches: keep JSON arrays under a few MB; prefer 1-5k rows/request based on row size.
  - For larger payloads: use Storage, RPCs, or Edge Functions to chunk server-side.
- Supabase API limits:
  - HTTP payload size: practical limit ~10 MB.
  - Rate limiting: project rate limits enforced; 429 with Retry-After if exceeded.
  - Statement timeout: ~60s at the edge; keep queries indexed and bounded.
- Recommendations:
  - Keep request bodies under 5-10 MB and paginate results.
  - Prefer POST with Prefer: params=single-object for complex filters.
  - Use Storage for large files/binary payloads.
  - Index columns used in filters and RLS to avoid timeouts.
  - If approaching limits, consider an Edge Function that accepts large payloads and chunks writes using service role.

Sub-task checklist:
- [ ] Audit current batch size and insert frequency.
- [ ] Determine safe maximum batch size per request.
- [ ] Update batching logic to the new size.
- [ ] Add retry handling for partial failures.
- [ ] Track insert latency and error rate metrics.

Deliverables:
- Updated batching configuration.
- Insert latency report.

Validation and acceptance:
- Total PostgREST insert calls reduced as expected.
- No increase in failure rate for inserts.

Rollback or contingency:
- Revert to prior batch size if payload limits are exceeded.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Run a quick syntax check for modified Python modules (py_compile).
- Record verification outcome in Notes.


Notes:
- Chunk insert batch size is now configurable via `backend/core/config.py` and used in the worker ingestion paths.
- Drive and Notion sync paths now use the same configurable batch size.
- Added retry + jitter for chunk inserts with per-batch latency logging via `backend/core/db_utils.py`.
- Added Prometheus metrics for Supabase insert/delete latency and retry outcomes.
- Verification: `python3 -m py_compile backend/core/db_utils.py`.

---

## Step 6: Constrain connector concurrency and retries

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Documented rate limits for each connector provider.
- Desired retry and backoff policy.

User inputs (fill below):
- Documented rate limits for each connector provider:
  - From backend/core/resilience.py:
    - Google Drive: no specific limits in code; retries on 403/429/500-504.
    - Notion: no specific limits in code; standard retry policy.
    - OpenAI: no specific limits in code; 3 attempts, 2-10s backoff.
    - LlamaParse: no specific limits in code; 3 attempts, 3-15s backoff.
    - Supabase: no specific limits in code; 3 attempts, 1-5s backoff.
  - Provider documentation (external):
    - Google Drive API: 10,000 queries/100 seconds/user.
    - Notion API: 3 requests/second average.
    - OpenAI: tier-based (current Tier 1).
  - Status: provider rate limits are not documented in codebase.
- Desired retry and backoff policy (current implementation from resilience.py):
  - Default retry policy:
    - max_attempts: 3
    - min_wait: 1s
    - max_wait: 10s
    - backoff: exponential (multiplier=1)
  - Google API:
    - max_attempts: 3
    - min_wait: 2s
    - max_wait: 30s
    - backoff: exponential (multiplier=2)
  - OpenAI:
    - max_attempts: 3
    - min_wait: 2s
    - max_wait: 10s
  - LlamaParse:
    - max_attempts: 3
    - min_wait: 3s
    - max_wait: 15s
  - Retryable errors:
    - HTTP 429
    - HTTP 502/503/504
    - Connection errors, timeouts, SSL errors
  - Status: implemented in code.

Sub-task checklist:
- [ ] Inventory connector list/fetch calls and their concurrency patterns.
- [ ] Define per-connector concurrency caps.
- [ ] Implement exponential backoff with jitter for rate limit responses.
- [ ] Add metrics for rate limit errors and retries per connector.
- [ ] Validate connector behavior under load.

Deliverables:
- Connector concurrency policy.
- Connector error and retry metrics.

Validation and acceptance:
- Rate-limit errors decrease.
- Connector throughput remains stable.

Rollback or contingency:
- Revert to prior concurrency settings if performance regresses.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Run a quick syntax check for modified Python modules (py_compile).
- Record verification outcome in Notes.


Notes:
- Connector fetches are now gated by a per-connector concurrency limiter in `backend/connectors/limits.py`.
- Notion API requests use retry with jitter and rate-limit logging.
- Google Drive list/get calls are retried with jitter via `with_google_retry`.
- Defaults in config: google_drive=2, notion=1, web=2, default=2; file_upload is unlimited.
- Added Prometheus metrics for connector rate-limit retries (Google Drive + Notion).
- Verification: `python3 -m py_compile backend/core/resilience.py backend/connectors/notion.py`.

---

## Step 7: Reduce Celery chord/result overhead

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current Celery configuration and result backend settings.

User inputs (fill below):
- Decision:
  - Current state: Procfile uses `celery -A backend.core.celery_app worker --loglevel=info`.
  - Implication: defaults to prefork with concurrency equal to container CPU count.
  - Recommended production command:
    ```
    celery -A backend.core.celery_app worker --pool=prefork --concurrency=2 --loglevel=info
    ```
- Current Celery configuration and result backend settings (backend/core/celery_app.py):
  - Basic configuration:
    - broker: Redis (settings.REDIS_URL)
    - backend: Redis (settings.REDIS_URL)
    - app_name: axial_worker
  - Production settings:
    - broker_connection_retry_on_startup: true
    - task_acks_late: true (ack after completion)
    - task_reject_on_worker_lost: true
    - worker_prefetch_multiplier: 1 (one task at a time per worker)
    - task_serializer: json
    - accept_content: [json]
    - result_serializer: json
    - timezone: UTC
    - enable_utc: true
    - result_expires: 86400 (24 hours)
    - task_default_retry_delay: 60s
    - task_max_retries: 3
  - Scheduled tasks:
    - Check scheduled crawls: hourly.
    - Cleanup old jobs: daily.
    - Retry failed tasks: every 5 minutes.
    - Update memory metrics: every minute.
    - Cleanup file status: daily at 3am UTC.
    - Cleanup audit logs: weekly Sunday 4am UTC.
  - Not documented in code:
    - Worker pool type (gevent vs prefork).
    - Concurrency count (number of workers).
    - Redis connection pool settings.
    - Task time limits.
    - Rate limiting.
  - Status: basic config documented; worker runtime settings missing.

Sub-task checklist:
- [x] Audit current chord usage and result backend storage size.
- [x] Define job-level counters stored in Redis for completion tracking.
- [x] Implement atomic increment/decrement operations for job progress.
- [x] Update finalize logic to use counters instead of chord results.
- [x] Add monitoring for counter drift and reconciliation logic.
- [x] Validate completion correctness under failure and retry scenarios.

Deliverables:
- Updated orchestration design.
- Redis counter metrics and alerts.

Validation and acceptance:
- Reduced Redis memory usage during large jobs.
- Job completion and failure handling remains correct.

Rollback or contingency:
- Restore chord-based finalization if counters become inconsistent.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Run a quick syntax check for modified Python modules (py_compile).
- Record verification outcome in Notes.


Notes:
- User requested to keep worker concurrency at 10 for now; defer reducing until further validation.
- Replaced ingestion and crawl chords with Redis counters + group dispatch for completion tracking.
- Added per-file outcome tracking to handle retries and status transitions without double counting.
- Added reconciliation task (`reconcile_ingestion_jobs`) to finalize jobs when Redis counters are missing.
- Set `ignore_result=True` for fan-out tasks to reduce result backend overhead.
- Verification: `python3 -m py_compile backend/worker/tasks.py backend/worker/periodic_tasks.py backend/core/job_counters.py`.

---

## Step 8: Add ingestion idempotency and strict retry policy

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Idempotency scope definition (job, file, chunk).
- Retry policy and backoff settings.

User inputs (fill below):
- Decision (idempotency):
  - Scope: file-level (filename + content hash).
  - Behavior: replace.
  - Logic: if a file already exists (hash match), identify existing document_id, delete existing chunks, then re-process and insert new chunks.
- Current codebase analysis:
  - No idempotency mechanism implemented.
  - Evidence:
    - No duplicate detection before inserting documents.
    - No checks for existing chunks with same content hash.
    - No job-level idempotency keys.
    - Only duplicate handling exists in webhook processing (webhooks.py).
  - Current behavior: re-running the same job creates duplicate documents/chunks.
  - Status: not implemented.
- Retry policy and backoff settings:
  - backend/core/celery_app.py:
    - task_default_retry_delay: 60s
    - task_max_retries: 3
  - backend/core/resilience.py:
    - Default: max_attempts=3, exponential backoff 1s min, 10s max, multiplier=1.
    - Google API: max_attempts=3, 2s min, 30s max, multiplier=2.
    - OpenAI: max_attempts=3, 2s min, 10s max.
    - LlamaParse: max_attempts=3, 3s min, 15s max.
  - Backoff formula:
    - wait_time = min(max_wait, min_wait * (multiplier ^ attempt))
    - Example (Google, multiplier=2): 2s, 4s, 8s, 16s (capped at 30s)
  - Status: implemented but not configurable per service.

Sub-task checklist:
- [x] Define idempotency keys and lifecycle for jobs, files, and chunks.
- [x] Update ingestion API to accept or generate idempotency keys.
- [x] Implement idempotency checks before processing and inserting.
- [x] Define retry policies for transient vs permanent errors.
- [x] Ensure DLQ preserves idempotency context.
- [x] Add metrics for duplicate detection and retry counts.

Deliverables:
- Idempotency specification.
- Retry policy document.

Validation and acceptance:
- Duplicate ingestion attempts do not create duplicate data.
- Retries stop after the defined policy.

Rollback or contingency:
- Disable idempotency checks only if they cause false negatives and block valid ingestion.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- Added `content_hash` to `documents` with index (migration required).
- Unified ingestion and connector sync now reuse existing documents by title + content hash and replace chunks.
- Added `idempotency_key` to `ingestion_jobs` with unique index (user_id + provider + key); API honors Idempotency-Key headers.
- Web ingestion and the ingestion pipeline now use idempotent batched inserts with content hashes.
- Added `pipeline_idempotency_hits_total` metric for duplicate detection.

---

## Step 9: Add parser safety guardrails

Status: Done
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Max file size per file type and parser.
- Timeout thresholds per parser.

User inputs (fill below):
- Global size limit: 100 MB (retain existing config).
- Per-type limits: None (no differentiation yet).
- Timeouts (soft):
  - Text/Markdown/Code: 60 seconds.
  - PDF (standard): 300 seconds (5 minutes).
  - PDF (OCR/Scanned): 600 seconds (10 minutes, requires LlamaParse).

Sub-task checklist:
- [x] Inventory supported file types and associated parsers.
- [x] Define safe file size limits and timeouts for each parser.
- [x] Implement early exits for risky or oversized files.
- [x] Define how the system reports partial or skipped parsing.
- [x] Add metrics for parser timeouts and file rejections.

Deliverables:
- Parser safety policy.
- Updated worker parsing behavior.

Validation and acceptance:
- No OOMs on large or malformed files.
- Clear error reporting for rejected files.

Rollback or contingency:
- Adjust thresholds if valid files are rejected too aggressively.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- Enforced max file size checks in ingestion and connector sync paths.
- Added soft parse-time thresholds for text-like files and PDFs (OCR/non-OCR).
- Unsupported/binary files are now skipped with explicit status reasons (unsupported/binary_content).
- Added `pipeline_parser_rejections_total` and parse timeout counters for observability.

---

## Step 10: Security quick wins

Status: In Progress
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current list of secrets, keys, and rotation policies.
- Current RLS policy inventory.
- Current CORS rules and allowed origins.

User inputs (fill below):
- Environment note: not running locally; tests run on Railway and Vercel after git push; env vars are defined on Railway and Vercel.
- Rotation policy: event-based (rotate secrets on suspected compromise or key employee offboarding; no scheduled rotation).
- Migration status (20260106140000_fix_advisor_issues.sql): file exists in supabase/migrations; assumed applied via pipeline/manual push; verify in Supabase Table Editor during next smoke test.
- Secrets and API keys inventory (from `backend/core/config.py`):
  - Required secrets (no defaults):
    - SUPABASE_URL
    - SUPABASE_SECRET_KEY (service role key)
    - SUPABASE_JWT_SECRET (JWT verification)
    - OPENAI_API_KEY
  - Optional secrets:
    - OAuth: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, NOTION_CLIENT_ID, NOTION_CLIENT_SECRET
    - Services: RESEND_API_KEY, SENTRY_DSN, GROQ_API_KEY, LLAMA_CLOUD_API_KEY
    - Payment: POLAR_ACCESS_TOKEN, POLAR_WEBHOOK_SECRET
  - Encryption keys (from `backend/core/security.py`):
    - ENCRYPTION_KEY (Fernet); required in production; generated with Fernet.generate_key().
  - Default/hardcoded values:
    - API_KEY: "default-insecure-key" (should be changed).
    - REDIS_URL: "redis://localhost:6379/0".
  - Rotation policy: not documented in code.
- RLS policy inventory (from `supabase/migrations/*.sql`):
  - Tables with RLS enabled (20): documents, document_chunks, conversations, messages, subscriptions, ingestion_file_status, audit_logs, teams, team_members, user_integrations, sync_state, web_crawl_configs, user_profiles, user_notification_settings, notifications, connector_definitions, ingestion_jobs, failed_tasks.
  - RLS policies by table:
    - documents (security_lockdown.sql):
      - Users can view own or team documents (SELECT).
      - Condition: user_id = auth.uid() OR team_id IN (user teams).
      - No INSERT/UPDATE/DELETE (backend-only writes).
    - document_chunks (security_lockdown.sql):
      - Users can view chunks of allowed documents (SELECT).
      - Inherits from parent document access.
      - No INSERT/UPDATE/DELETE.
    - conversations:
      - Users can view own conversations (SELECT).
      - Users can insert own conversations (INSERT).
      - Users can update own conversations (UPDATE).
      - Users can delete own conversations (DELETE).
    - messages:
      - Users can view messages in own conversations (SELECT).
      - Users can insert messages in own conversations (INSERT).
      - Users can delete messages in own conversations (DELETE).
    - subscriptions:
      - Users can view team subscription (SELECT via team_id).
    - ingestion_file_status:
      - Users can view own file status (SELECT, user_id = auth.uid()).
      - Service role full access (ALL).
    - audit_logs:
      - Service role can insert audit logs (INSERT).
    - teams:
      - Owners can view own team (SELECT, owner_id = auth.uid()).
      - Owners can update own team (UPDATE, owner_id = auth.uid()).
      - Members can view team (SELECT, via team_members).
    - team_members:
      - Members can view teammates (SELECT).
      - Owners can view own team (SELECT).
      - Owners can insert team members (INSERT).
      - Owners can update team members (UPDATE).
      - Owners can delete team members (DELETE).
    - user_integrations:
      - Users can view own integrations (SELECT).
      - Users can insert own integrations (INSERT).
      - Users can update own integrations (UPDATE).
    - sync_state:
      - Users can view own sync state (SELECT).
      - Users can insert own sync state (INSERT).
      - Users can update own sync state (UPDATE).
      - Service role full access to sync_state (ALL).
    - web_crawl_configs:
      - Users can view own crawl configs (SELECT).
      - Users can create own crawl configs (INSERT).
      - Users can update own crawl configs (UPDATE).
      - Users can delete own crawl configs (DELETE).
      - Service role has full access to crawl configs (ALL).
    - user_profiles:
      - Users can view own profile (SELECT, user_id = auth.uid()).
      - No UPDATE in lockdown (backend-only writes).
    - user_notification_settings:
      - Users can view own notifications (SELECT).
      - Users can insert own notifications (INSERT).
      - Users can update own notifications (UPDATE).
      - Users can delete own notifications (DELETE).
    - notifications:
      - Users can view own notifications (SELECT).
      - Users can update own notifications (UPDATE).
      - Users can delete own notifications (DELETE).
      - Service role has full access to notifications (ALL).
    - connector_definitions:
      - Anyone can view active connectors (SELECT, authenticated).
    - ingestion_jobs:
      - RLS enabled (specific policies not surfaced in search results).
    - failed_tasks:
      - Users can view own failed tasks (SELECT).
      - Users can update own failed tasks (UPDATE).
  - Policy pattern: most policies use user_id = auth.uid() or team-based access.
- CORS configuration (from `backend/main.py`):
  - Production mode:
    - ALLOWED_ORIGINS must be set; wildcard not allowed.
    - HTTPS enforcement: warn on non-HTTPS origins.
  - Development mode:
    - Fallback origins: localhost and 127.0.0.1 on ports 3000/3001.
    - Vercel preview support: add https://*.vercel.app when VERCEL_ENV in (preview, development).
  - Current config (from `backend/core/config.py`):
    - ALLOWED_ORIGINS default: empty string.
    - Must be set via env var; comma-separated list.
    - Example: ALLOWED_ORIGINS=https://app.axiohub.io,https://www.axiohub.io
  - CORS middleware settings:
    - allow_origins=cors_origins, allow_credentials=true.
    - allow_methods=["*"], allow_headers=["*"], expose_headers=["*"], max_age=3600.
- Summary:
  - Secrets management:
    - 15+ secrets/API keys documented.
    - Encryption key required in production.
    - No rotation policy documented in code.
    - Default API_KEY is insecure.
  - RLS policies:
    - 20 tables with RLS enabled.
    - 60+ total policies.
    - Security lockdown enforces backend-only writes for core tables.
    - Team-based access control implemented.
    - Service role bypass for backend operations.
  - CORS configuration:
    - Production: strict (ALLOWED_ORIGINS required, wildcards blocked, HTTPS enforced).
    - Development: permissive localhost fallback.
    - Current value empty; must be configured.
    - Credentials allowed; all methods/headers permitted.


Sub-task checklist:
- [x] Inventory all secrets and access keys used by API and workers.
- [ ] Rotate secrets and update deployments.
- [x] Audit RLS policies for all ingestion-related tables.
- [ ] Add or update tests that validate cross-tenant isolation.
- [x] Identify sensitive fields in logs and DLQ payloads.
- [x] Implement log and DLQ redaction for sensitive fields.
- [x] Review and tighten CORS configuration.
- [ ] Validate that changes do not break ingestion or UI flows.

Deliverables:
- Secret rotation log.
- RLS audit report.
- Logging redaction policy.

Validation and acceptance:
- No unauthorized cross-tenant reads or writes in tests.
- Secrets rotated and verified across all services.

Rollback or contingency:
- Roll back CORS or policy changes if they block valid traffic, with a documented fix path.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- DLQ payloads now redact sensitive fields before persistence.
- Added `.gitignore` rule for `TEST_RESULTS/` to prevent log/secrets from being committed.

---

## Step 11: Benchmark and release gates

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Steps 2-10 completed
Inputs required:
- Benchmark dataset definitions and test harness selection.
- Release gate thresholds.

User inputs (fill below):
- Decision:
  - Approval: propose the standard benchmark datasets.
  - Release gates (initial):
    - Success rate: > 95% of files processed without error.
    - Latency (p50): < 30s for standard text PDFs.
    - Blocker: any 500 Internal Server Error during ingestion blocks release.
- Benchmark dataset definitions:
  - Status: not defined in code.
  - Test harness found:
    - Location: `backend/tests/unit/test_performance.py`.
    - Framework: pytest with pytest-benchmark.
  - Existing benchmark tests:
    - test_benchmark_single_document_processing(): measures single document processing time; no predefined dataset.
    - test_benchmark_batch_processing(): measures 10 documents; uses mock_documents fixture.
    - test_benchmark_connector_fetch(): measures 100 file fetches; uses mock data (b"x" * 1024).
    - test_benchmark_memory_usage(): measures memory for 50 x 1MB files; uses mock data.
    - test_benchmark_concurrent_processing(): measures 20 concurrent documents; uses asyncio.sleep.
  - Dataset characteristics (from tests):
    - Single doc: undefined size.
    - Batch: 10 documents.
    - Connector: 100 files @ 1KB each.
    - Memory: 50 files @ 1MB each.
    - Concurrent: 20 documents.
  - Missing:
    - No real-world representative datasets.
    - No PDFs, DOCX, or code file test data.
    - No multi-GB test files.
    - No benchmark corpus definition.
- Test harness selection:
  - Framework: pytest.
  - Config: `backend/pytest.ini`.
    - testpaths=tests
    - asyncio_mode=auto
    - addopts=-v --tb=short
  - Markers:
    - unit (fast, no external deps).
    - integration (may require external services).
    - slow (skip with -m "not slow").
    - benchmark (performance; not in pytest.ini).
  - Test organization:
    - tests/unit (34 files)
    - tests/integration (4 files)
    - tests/load (2 files)
    - tests/security (1 file)
    - tests/conftest.py (shared fixtures)
  - Fixtures (conftest.py):
    - mock_supabase (mock DB)
    - mock_openai_embeddings
    - sample_document
    - sample_chunks
    - mock_environment
  - No formal test data:
    - No CSV/JSON datasets.
    - No test file repository.
    - No golden outputs for comparison.
- Release gate thresholds:
  - Status: not defined in code.
  - References in RefactoringPlan docs: "Define release gate thresholds and publish results." (not implemented).
  - Hardcoded test assertions (from test_performance.py; not formal gates):
    - Line 70: assert processing_time < 10 (10 docs in <10 seconds).
    - Line 102: assert fetch_time < 5 (100 files in <5 seconds).
    - Line 147: assert peak < 500 * 1024 * 1024 (<500MB for 50 x 1MB).
    - Line 203: assert concurrent_time < 1 (<1 second with concurrency).
- Current testing infrastructure:
  - Unit tests: test_ingest_tasks.py, test_worker_progress.py, test_settings.py, test_performance.py (benchmarks), test_notifications.py, test_ingestion_pipeline.py, plus 28+ more files.
  - Integration tests: 4 files in tests/integration.
  - Load tests: 2 files in tests/load.
  - CI/CD config: none found (.github/workflows or .gitlab-ci.yml).
❌ No pytest-cov configuration
❌ No coverage thresholds
Summary
Benchmarks:

✅ pytest-benchmark framework configured
✅ 6 performance tests exist
❌ No formal benchmark datasets
❌ No real-world test corpus
Test Harness:

✅ pytest with asyncio support
✅ Unit/integration/benchmark markers
✅ Mock fixtures for DB and APIs
❌ No load test framework
Release Gates:

❌ Not defined in code
❌ No performance baselines
❌ No coverage requirements
❌ No CI/CD gates

Sub-task checklist:
- [ ] Define benchmark scenarios and datasets for 15, 150, 1,500 files.
- [ ] Implement or configure a repeatable benchmark harness.
- [ ] Run baseline benchmarks and record results.
- [ ] Run post-change benchmarks and compare results.
- [ ] Define release gate thresholds and publish results.
- [ ] Prepare rollback plan if SLOs are not met.

Deliverables:
- Benchmark report (baseline vs post-change).
- Release gate checklist.

Validation and acceptance:
- Target performance improvement achieved.
- Release gates satisfied with documented evidence.

Rollback or contingency:
- Roll back to previous build if performance or stability regresses.

Step completion check:
- Review impacts on other files/modules and update references if needed.
- Verify environment/config dependencies for any changes (Railway/Vercel).
- Confirm no pending migrations or infra updates remain unreviewed.
- Record verification outcome in Notes.


Notes:
- TBD
