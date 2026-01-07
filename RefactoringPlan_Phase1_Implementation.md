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
🎯 Service Level Objectives (SLOs)1. ⏱️ Ingestion LatencyTime elapsed from "Upload" click to "Completed" status.MetricTarget ValueJustificationp50 (Median)< 30 secondsThe Coffee Rule: Users accept waiting 30s for a standard 10-20 page document without switching tabs.p95 (Majority)< 2 minutesEnterprise Docs: For dense reports (100+ pages), users expect a wait but should not perceive a "freeze."p99 (Outliers)< 5 minutesStress Test: For books (500+ pages) or OCR tasks. Reliability is the metric here, not speed.Note: Current BATCH_SIZE=20 and SLEEP=1.0s settings deliberately limit maximum speed to ensure 100% stability.2. ⏳ Queue Wait TimeTime elapsed between "Job Created" in DB and "Worker Started".StateTarget ValueJustificationNormal Load< 2 secondsPerceived Speed: Users should see the status change from Pending to Processing almost instantly.Peak Load< 10 secondsBurst Handling: If 50 users upload at once, the queue should drain reasonably fast without auto-scaling.3. 🚨 Error Rate ThresholdsRatio of failed jobs to total jobs.Failure TypeTargetDescription & ActionHard Failure< 1.0%System Crashes/Timeouts. Unacceptable. Requires immediate P1 fix.Soft Failure< 5.0%User Errors. Encrypted PDFs, corrupted files. System must handle these gracefully (Red Toast).Retry Rate< 10%Throttling. If >10% of jobs hit 429 errors, we need to adjust our Rate Limiters.🧪 Representative Workload DefinitionsUse these scenarios for Smoke Tests and Load Tests.A. "The Quick Win" (60% of volume)File: Standard Contract / Article.Specs: ~15 Pages, Text-only, < 2MB.Target: Complete in 15-20s.B. "The Enterprise Doc" (30% of volume)File: Annual Report / User Manual.Specs: ~100 Pages, Mixed Text & Images, ~15MB.Target: Complete in 90s. Progress bar must be smooth.C. "The Stress Test" (10% of volume)File: Technical Book / Scanned Legal Doc.Specs: 500+ Pages, High Density or OCR required, > 50MB.Target: Complete in 5-8m. Must not crash (OOM) or Timeout.

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
- TBD

---

## Step 2: Region alignment for DB and workers

Status: TBD (set before start)
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
- TBD

---

## Step 3: Reduce progress update frequency

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Approved progress milestone definitions and UI behavior.

User inputs (fill below):
- Update (Phase 1 decision):
  - Remove strict ENUM/CHECK constraint on ingestion_file_status.status to allow flexible status strings.
  - Action: Change status column to TEXT without strict constraint (drop CHECK).
  - Reason: Enable granular progress bars without a migration for every new stage.
- Approved progress milestone definitions and UI behavior: 

Progress Tracking Specification
Purpose: Define milestones, triggers, and UI behavior for enterprise-grade ingestion progress tracking
Goal: Provide granular, real-time stage updates while avoiding per-chunk write amplification

Milestones (Ordered)
File-level statuses:

pending - File queued, not started
uploading - Uploading or fetching file (if applicable)
parsing - Extracting text from file
embedding - Generating embeddings
indexing - Writing to database
completed - Successfully finished
failed - Error occurred
skipped - Empty/unsupported file
Job-level statuses (ingestion_jobs table):

pending - Job created, not started
processing
 - Files being processed
completed
 - All files done
failed
 - Critical error (job cannot continue)
Milestone Trigger Definitions
File-Level (ingestion_file_status)
Status  Trigger Point  DB Write Required
pending  When file status record created  ✅ Yes (initial)
uploading  When upload or fetch begins (if applicable)  ✅ Yes
parsing  When parsing begins (if applicable)  ✅ Yes
embedding  When embedding begins  ✅ Yes
indexing  Before DB write  ✅ Yes
completed  After successful DB write  ✅ Yes (final)
failed  On any error  ✅ Yes (error state)
skipped  If file empty/unsupported  ✅ Yes (final)

Granular Update Policy:
- Write on each stage transition only; no per-chunk updates.
- Do not write repeated updates within the same stage.
- Status values are defined in code (enum) and can expand without DB migrations due to TEXT storage.
Job-Level (ingestion_jobs)
Status	Trigger Point	Update Frequency
pending	Job created	Once (initial)
processing
First file starts	Once (transition)
completed
All files done	Once (final)
failed
Critical error	Once (error)
Job Progress Field:

Update processed_files count only when files complete
Update frequency: Batched every 10 files OR every 30 seconds
Formula: progress = (processed_files / total_files) * 100
Progress Calculation Rules
File-Level Progress Mapping (frontend default):

pending=0 → uploading=10 → parsing=30 → embedding=60 → indexing=85 → completed=100
failed=100, skipped=100

Fallback rule:
- If an unknown status is received, use job.progress (capped at 95) until file completes.
- Legacy support: treat "processing" as equivalent to "parsing" for UI display.

// Example frontend mapping
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
Job-Level Progress
Formula:

progress = (processed_files / total_files) * 100
Where:

processed_files = count of files with status in (
completed
, 
failed
, skipped)
total_files = total files in job
No byte-weighting (simpler, good enough for UX)
Update Strategy:

# Only update job progress when:
# 1. Every 10 files complete, OR
# 2. Every 30 seconds (timer-based batch)
completed_since_last_update = 0
def mark_file_complete(file_id):
    # Update file status
    update_file_status(file_id, "completed")
    
    completed_since_last_update += 1
    
    # Batch job progress updates
    if completed_since_last_update >= 10:
        update_job_progress()
        completed_since_last_update = 0
# Timer-based backup
every_30_seconds:
    if completed_since_last_update > 0:
        update_job_progress()
        completed_since_last_update = 0
UI Behavior Requirements
Must Show
Progress Modal:

Overall progress bar - Based on job.progress (0-100%)
File list with per-file status badges:
⏳ Pending (gray)
⬆️ Uploading (blue)
🧩 Parsing (blue)
🧠 Embedding (purple)
📥 Indexing (blue)
✅ Completed (green)
❌ Failed (red)
⏭️ Skipped (yellow)
Status counts - "3/11 files completed"
Current activity - "Processing files..." (inferred from job status)
Optional (Nice-to-Have):

ETA estimation (based on avg time per file)
Failed file error messages (on click/expand)
Retry button for failed files
Allowed Staleness
Real-time Updates (Supabase Realtime):

Subscribe to ingestion_jobs changes
Subscribe to ingestion_file_status changes
Update frequency: As DB changes occur (granular stage updates)
Acceptable Delays:

Job progress: Up to 30 seconds stale (batched updates)
File status: Near-real-time for each stage transition
Overall UX: User sees "something happening" within 5 seconds
Display Rules
Failed Files:

Show red ❌ badge
Display error message on hover/click
Provide "Retry" button (if applicable)
Don't block other files from completing
Skipped Files:

Show yellow ⏭️ badge with skip icon
Show reason (e.g., "Empty file", "Unsupported format")
Don't count as failure
Retried Files:

Reset to pending status
Show as new file in queue
Optional: Badge showing "Retry #2"
Non-Negotiable UX Constraints
1. Progress Must Be Monotonic
✅ Allowed: 0% → 27% → 54% → 100%
❌ Not Allowed: 50% → 30% → 70% (backwards)
Implementation:

Never decrease job.progress value
If recalculation shows lower value, keep current value
Only increase when files actually complete
2. Avoid Large Progress Jumps
✅ Smooth: 10% → 20% → 30% → 40%
❌ Jarring: 10% → 95% → 100%
Implementation:

With 11 files, each file = ~9% progress
Batching every 10 files = max 90% jump (acceptable for large batches)
For small jobs (<20 files), update more frequently
3. Always Show Activity
While job.status = 'processing':
  - Show spinner animation
  - Update "X/Y files completed" every 30s
  - Show "Processing..." text
Never:

Freeze UI with no feedback
Show 0% for extended period
Hide errors from user
4. Handle Edge Cases Gracefully
Empty Job (0 files):

Progress: 100% immediately
Message: "No files to process"
All Files Failed:

Progress: 100% (job is "done")
Status: 
failed
Show error summary
Single File:

Progress: 0% → 100% (one jump)
Acceptable (user understands single file = simple)
Database Schema Alignment
ingestion_file_status columns:

status TEXT (no CHECK constraint by design)

Migration Required:

-- Remove the existing CHECK constraint to allow flexible status values
ALTER TABLE ingestion_file_status 
DROP CONSTRAINT ingestion_file_status_status_check;
Implementation Summary
Database Writes Profile (Phase 1)
- File-level: one update per stage transition (pending, uploading, parsing, embedding, indexing, completed/failed/skipped). Expected 5-7 writes per file depending on stages used.
- Job-level: pending, processing, completed/failed plus batched progress updates every 10 files or 30 seconds.
- Rationale: prioritize UX with granular progress while avoiding per-chunk updates.

Expected Performance Impact
- With co-location (<5ms RTT), stage-level status updates should not dominate ingestion latency at current scale.
- Monitor PostgREST throughput and Realtime fan-out during 50+ parallel uploads; adjust batching or throttle if needed.

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
- TBD

---

## Step 4: Increase embedding batch size and concurrency

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current embedding provider limits and quotas.
- Maximum acceptable request size and concurrency per provider.

User inputs (fill below):
- Question 1: Current embedding provider limits and quotas

Provider: OpenAI text-embedding-3-small
Account Tier: Usage Tier 1 (confirmed from your dashboard)
Rate Limits:
3,000 requests per minute (RPM)
1,000,000 tokens per minute (TPM)
Monthly Budget: $1.36 spent / $120.00 limit
Daily Quota: 90M tokens/day (batch queue)
Question 2: Maximum acceptable request size and concurrency

Max Request Size:
2,048 embeddings per request (OpenAI hard limit)
8,191 tokens per input
Recommended: 1,000 embeddings/request (safe, fast)
Max Concurrency:
For 2-minute target: 10-15 concurrent requests
Safety limit: 20 concurrent (stays under RPM limit)
Recommended: 10 concurrent requests

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
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 5: Increase chunk insert batch size (still PostgREST)

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- PostgREST request size limits.
- Supabase limits on payload size and request rate.

User inputs (fill below):
PostgREST request size limits
Supabase’s REST API is powered by PostgREST behind a NGINX/API gateway. Practical limits you’ll encounter are:

Request body size (POST/PATCH/PUT):
JSON payloads: up to ~10 MB per request is safe. Larger requests can be rejected by the API gateway with “Request Entity Too Large”.
Multi-part uploads: Not supported via PostgREST; use Supabase Storage or a signed URL for large file uploads.
Query string length:
Keep under ~8–16 KB to avoid 414 URI Too Long at the edge. If your filters/IN lists are large, switch to POST with Prefer: params=single-object and send filters in the body, or use RPC.
Response size:
Large responses are allowed but may be capped by:
Timeout (default ~60s at the edge). Use range pagination and narrower selects to avoid timeouts and excessive memory.
Client SDK/network constraints.
Row limits:
Default range limit is typically 1,000 rows per request unless you configure Range headers. Use pagination and indexes to stay performant.
UPSERT/INSERT batches:
Batching thousands of rows is possible, but keep JSON arrays under a few MBs. Prefer chunking (e.g., 1–5k rows per request depending on row size) and ensure indexes/constraints are tuned.
Notes:

If you need to move larger payloads, use:
Supabase Storage for files and store metadata in Postgres.
RPCs that stream or chunk work server-side (still subject to timeouts).
Edge Functions to pre-process, validate, and write in smaller batches.
Supabase limits on payload size and request rate
HTTP payload size:
Practical limit ~10 MB for API requests. For anything larger, use Storage or presigned uploads.
Rate limiting:
Supabase enforces per-project rate limits at the API gateway. Exact numbers depend on your plan and current infrastructure. If you hit rate limits, you’ll receive 429 Too Many Requests with Retry-After.
Best practices:
Implement exponential backoff on 429/5xx.
Batch reads with pagination and selective columns.
Batch writes in modest chunks with retries.
Use server-side operations (Edge Functions) to reduce client round-trips.
Statement timeout:
API-side timeouts commonly around 60 seconds. Keep queries indexed, use LIMIT/Range, and avoid large cross-joins.
Recommendations
Keep request bodies under 5–10 MB and paginate results.
Prefer POST with Prefer: params=single-object for complex filters to avoid long URLs.
Use Storage for files and large binary payloads.
Index columns used in filters and RLS conditions to avoid timeouts.
If you expect to approach limits, consider an Edge Function that:
Accepts a large request,
Streams data to Storage or chunks writes,
Uses the service role key for controlled, privileged operations.

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
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 6: Constrain connector concurrency and retries

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Documented rate limits for each connector provider.
- Desired retry and backoff policy.

User inputs (fill below):
Question 1: Documented rate limits for each connector provider

From 
backend/core/resilience.py
:

Provider	Rate Limit Documented	Retry Config
Google Drive	❌ No specific limits in code	Retries: 403, 429, 500-504 (lines 211-212)
Notion	❌ No specific limits in code	Uses standard retry (line 84)
OpenAI	❌ No specific limits in code	3 attempts, 2-10s backoff (lines 388-393)
LlamaParse	❌ No specific limits in code	3 attempts, 3-15s backoff (lines 402-407)
Supabase	❌ No specific limits in code	3 attempts, 1-5s backoff (lines 395-400)
Actual provider documentation (external):

Google Drive API: 10,000 queries/100 seconds/user
Notion API: 3 requests/second average
OpenAI: Based on tier (you have Tier 1)
Status: ❌ Not documented in codebase

Question 2: Desired retry and backoff policy

Current Implementation (from resilience.py):

python
# Default retry policy (lines 72-104)
max_attempts: 3
min_wait: 1 second
max_wait: 10 seconds
backoff: exponential (multiplier=1)
# Google API specific (lines 223)
max_attempts: 3
min_wait: 2 seconds
max_wait: 30 seconds
backoff: exponential (multiplier=2)
# OpenAI (lines 388-393)
max_attempts: 3
min_wait: 2 seconds
max_wait: 10 seconds
# LlamaParse (lines 402-407)
max_attempts: 3
min_wait: 3 seconds
max_wait: 15 seconds
Retryable errors (lines 48-49):

HTTP 429 (rate limit)
HTTP 502, 503, 504 (server errors)
Connection errors, timeouts, SSL errors
Status: ✅ Implemented in code

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
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 7: Reduce Celery chord/result overhead

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current Celery configuration and result backend settings.

User inputs (fill below):
Update (Decision):
- Current state: Procfile uses default command `celery -A backend.core.celery_app worker --loglevel=info`.
- Implication: Defaults to prefork pool with concurrency equal to container CPU count.
- Recommended production command: `celery -A backend.core.celery_app worker --pool=prefork --concurrency=2 --loglevel=info`.

Current Celery configuration and result backend settings:

From 
backend/core/celery_app.py
:

Basic Configuration (lines 48-53):

python
broker: Redis (from settings.REDIS_URL)
backend: Redis (from settings.REDIS_URL)
app_name: "axial_worker"
Production Settings (lines 59-88):

python
# Connection
broker_connection_retry_on_startup: True
# Task Acknowledgment
task_acks_late: True  # Only ack after completion
task_reject_on_worker_lost: True  # Requeue if worker dies
# Concurrency
worker_prefetch_multiplier: 1  # One task at a time per worker
# Serialization
task_serializer: "json"
accept_content: ["json"]
result_serializer: "json"
# Timezone
timezone: "UTC"
enable_utc: True
# Results
result_expires: 86400  # 24 hours
# Retry
task_default_retry_delay: 60  # 1 minute
task_max_retries: 3
Scheduled Tasks (lines 93-124):

Check scheduled crawls: Every hour
Cleanup old jobs: Daily
Retry failed tasks: Every 5 minutes
Update memory metrics: Every minute
Cleanup file status: Daily at 3am UTC
Cleanup audit logs: Weekly Sunday 4am UTC
NOT Documented in code:

❌ Worker pool type (gevent vs prefork)
❌ Concurrency count (number of workers)
❌ Redis connection pool settings
❌ Task time limits
❌ Rate limiting
Status: ✅ Basic config documented, ⚠️ Worker runtime settings missing

Sub-task checklist:
- [ ] Audit current chord usage and result backend storage size.
- [ ] Define job-level counters stored in Redis for completion tracking.
- [ ] Implement atomic increment/decrement operations for job progress.
- [ ] Update finalize logic to use counters instead of chord results.
- [ ] Add monitoring for counter drift and reconciliation logic.
- [ ] Validate completion correctness under failure and retry scenarios.

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
- Record verification outcome in Notes.


Notes:
- TBD

---

## Step 8: Add ingestion idempotency and strict retry policy

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Idempotency scope definition (job, file, chunk).
- Retry policy and backoff settings.

User inputs (fill below):
Decision (Idempotency):
- Scope: File-level (Filename + Content Hash).
- Behavior: Replace.
- Logic: If a file already exists (hash match), identify existing document_id, delete existing chunks, then re-process and insert new chunks.

Question 1: Idempotency scope definition (job, file, chunk)

From codebase analysis:

❌ No idempotency mechanism implemented

Evidence:

No duplicate detection before inserting documents
No checks for existing chunks with same content hash
No job-level idempotency keys
Only duplicate found: webhook processing (line in 
webhooks.py
)
Current behavior:

Re-running same job → creates duplicate documents/chunks
Scope: None (no deduplication at any level)
Status: ❌ Not implemented

Question 2: Retry policy and backoff settings

From 
backend/core/celery_app.py
 (lines 86-88):

python
task_default_retry_delay: 60 seconds (1 minute)
task_max_retries: 3
From 
backend/core/resilience.py
:

python
# Default (lines 72-76)
max_attempts: 3
exponential backoff: 1s min, 10s max
multiplier: 1
# Google API (line 223)
max_attempts: 3
exponential backoff: 2s min, 30s max
multiplier: 2
# OpenAI (lines 388-393)
max_attempts: 3
backoff: 2s min, 10s max
# LlamaParse (lines 402-407)
max_attempts: 3
backoff: 3s min, 15s max
Backoff formula:

wait_time = min(max_wait, min_wait * (multiplier ^ attempt))
Example (Google, multiplier=2):
Attempt 1: 2s
Attempt 2: 4s
Attempt 3: 8s
Attempt 4: 16s → capped at 30s
Status: ✅ Implemented but not configurable per service

Sub-task checklist:
- [ ] Define idempotency keys and lifecycle for jobs, files, and chunks.
- [ ] Update ingestion API to accept or generate idempotency keys.
- [ ] Implement idempotency checks before processing and inserting.
- [ ] Define retry policies for transient vs permanent errors.
- [ ] Ensure DLQ preserves idempotency context.
- [ ] Add metrics for duplicate detection and retry counts.

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
- TBD

---

## Step 9: Add parser safety guardrails

Status: TBD (set before start)
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
- [ ] Inventory supported file types and associated parsers.
- [ ] Define safe file size limits and timeouts for each parser.
- [ ] Implement early exits for risky or oversized files.
- [ ] Define how the system reports partial or skipped parsing.
- [ ] Add metrics for parser timeouts and file rejections.

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
- TBD

---

## Step 10: Security quick wins

Status: TBD (set before start)
Owner: TBD (input required)
Target start: TBD (input required)
Target end: TBD (input required)
Dependencies: Step 1 completed
Inputs required:
- Current list of secrets, keys, and rotation policies.
- Current RLS policy inventory.
- Current CORS rules and allowed origins.

User inputs (fill below):
- Environment note: Not running locally. Tests are run on Railway and Vercel after git push. All environment variables are defined on Railway and Vercel.
- Rotation policy: Event-based. Rotate secrets only on suspected compromise or key employee offboarding (no scheduled rotation yet).
- Migration status (20260106140000_fix_advisor_issues.sql): File exists in supabase/migrations/. Assumed applied via pipeline/manual push; will verify via Supabase Table Editor during next smoke test.
1. Secrets & API Keys Inventory
From 
backend/core/config.py
:

Required Secrets (No defaults)
SUPABASE_URL: str
SUPABASE_SECRET_KEY: str  # Service role key
SUPABASE_JWT_SECRET: str  # For JWT verification
OPENAI_API_KEY: str
Optional Secrets
# OAuth Providers
GOOGLE_CLIENT_ID: Optional[str]
GOOGLE_CLIENT_SECRET: Optional[str]
NOTION_CLIENT_ID: Optional[str]
NOTION_CLIENT_SECRET: Optional[str]
# Services
RESEND_API_KEY: Optional[str]  # Email
SENTRY_DSN: Optional[str]  # Error tracking
GROQ_API_KEY: Optional[str]  # AI provider
LLAMA_CLOUD_API_KEY: Optional[str]  # PDF parsing
# Payment
POLAR_ACCESS_TOKEN: Optional[str]
POLAR_WEBHOOK_SECRET: Optional[str]
Encryption Keys
From 
backend/core/security.py
:

ENCRYPTION_KEY: str  # Fernet encryption for OAuth tokens
# Required in production (line 15)
# Generated with: Fernet.generate_key()
Default/Hardcoded Values
API_KEY: "default-insecure-key"  # ⚠️ Should be changed
REDIS_URL: "redis://localhost:6379/0"  # Default
Rotation Policy: ❌ Not documented in code

2. RLS Policy Inventory
From supabase/migrations/*.sql:

Tables with RLS Enabled (20 tables)
documents                ✅ RLS enabled
document_chunks          ✅ RLS enabled
conversations            ✅ RLS enabled
messages                 ✅ RLS enabled
subscriptions            ✅ RLS enabled
ingestion_file_status    ✅ RLS enabled
audit_logs               ✅ RLS enabled
teams                    ✅ RLS enabled
team_members             ✅ RLS enabled
user_integrations        ✅ RLS enabled
sync_state               ✅ RLS enabled
web_crawl_configs        ✅ RLS enabled
user_profiles            ✅ RLS enabled
user_notification_settings ✅ RLS enabled
notifications            ✅ RLS enabled
connector_definitions    ✅ RLS enabled
ingestion_jobs           ✅ RLS enabled
failed_tasks             ✅ RLS enabled
RLS Policies by Table
documents (security_lockdown.sql):

"Users can view own or team documents"
  - FOR SELECT
  - user_id = auth.uid() OR team_id IN (user's teams)
  - ❌ NO INSERT/UPDATE/DELETE (backend-only writes)
document_chunks (security_lockdown.sql):

"Users can view chunks of allowed documents"
  - FOR SELECT
  - Inherits from parent document access
  - ❌ NO INSERT/UPDATE/DELETE
conversations:

"Users can view own conversations" (SELECT)
"Users can insert own conversations" (INSERT)
"Users can update own conversations" (UPDATE)
"Users can delete own conversations" (DELETE)
messages:

"Users can view messages in own conversations" (SELECT)
"Users can insert messages in own conversations" (INSERT)
"Users can delete messages in own conversations" (DELETE)
subscriptions:

"Users can view team subscription" (SELECT via team_id)
ingestion_file_status:

"Users can view own file status" (SELECT, user_id = auth.uid())
"Service role full access" (ALL, TO service_role)
audit_logs:

"Service role can insert audit logs" (INSERT, TO service_role)
teams:

"Owners can view own team" (SELECT, owner_id = auth.uid())
"Owners can update own team" (UPDATE, owner_id = auth.uid())
"Members can view team" (SELECT, via team_members)
team_members:

"Members can view teammates" (SELECT)
"Owners can view own team" (SELECT)
"Owners can insert team members" (INSERT)
"Owners can update team members" (UPDATE)
"Owners can delete team members" (DELETE)
user_integrations:

"Users can view own integrations" (SELECT)
"Users can insert own integrations" (INSERT)
"Users can update own integrations" (UPDATE)
sync_state:

"Users can view own sync state" (SELECT)
"Users can insert own sync state" (INSERT)
"Users can update own sync state" (UPDATE)
"Service role full access to sync_state" (ALL)
web_crawl_configs:

"Users can view their own crawl configs" (SELECT)
"Users can create their own crawl configs" (INSERT)
"Users can update their own crawl configs" (UPDATE)
"Users can delete their own crawl configs" (DELETE)
"Service role has full access to crawl configs" (ALL)
user_profiles:

"Users can view own profile" (SELECT, user_id = auth.uid())
❌ NO UPDATE in lockdown (backend-only writes)
user_notification_settings:

"Users can view own notifications" (SELECT)
"Users can insert own notifications" (INSERT)
"Users can update own notifications" (UPDATE)
"Users can delete own notifications" (DELETE)
notifications:

"Users can view their own notifications" (SELECT)
"Users can update their own notifications" (UPDATE)
"Users can delete their own notifications" (DELETE)
"Service role has full access to notifications" (ALL)
connector_definitions:

"Anyone can view active connectors" (SELECT, TO authenticated)
ingestion_jobs:

RLS enabled (specific policies not shown in search results)
failed_tasks:

"Users can view own failed tasks" (SELECT)
"Users can update own failed tasks" (UPDATE)
Policy Pattern: Most follow user_id = auth.uid() or team-based access

3. CORS Configuration
From 
backend/main.py
 (lines 120-200):

Production Mode
if ENVIRONMENT == "production":
    # REQUIRED: ALLOWED_ORIGINS must be set
    if not origins:
        raise RuntimeError("ALLOWED_ORIGINS must be set in production!")
    
    # BLOCKED: Wildcard not allowed
    if "*" in origins:
        raise RuntimeError("Wildcard (*) CORS not allowed in production!")
    
    # VALIDATED: HTTPS enforcement
    for origin in origins:
        if not origin.startswith("https://"):
            logger.warning("Non-HTTPS origin in production")
Development Mode
if not origins:
    # Fallback to localhost
    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
# Vercel preview support
if VERCEL_ENV in ("preview", "development"):
    origins.append("https://*.vercel.app")
Current Configuration (from config.py line 35)
ALLOWED_ORIGINS: str = ""  # Empty by default
Actual Origins: Must be set via environment variable
Format: Comma-separated list
Example: ALLOWED_ORIGINS=https://app.axiohub.io,https://www.axiohub.io

CORS Middleware Settings (lines 198-206)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,  # From configure_cors()
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
Summary
Secrets Management:

✅ 15+ secrets/API keys documented
✅ Encryption key required in production
❌ No rotation policy documented
⚠️ Default API_KEY is insecure
RLS Policies:

✅ 20 tables with RLS enabled
✅ 60+ total policies across all tables
✅ Security lockdown enforces backend-only writes for core tables
✅ Team-based access control implemented
✅ Service role bypass for backend operations
CORS Configuration:

✅ Production: Strict (requires ALLOWED_ORIGINS, blocks wildcards, HTTPS enforced)
✅ Development: Permissive (localhost fallback)
⚠️ Current value: Empty (must be configured)
✅ Credentials allowed, all methods/headers permitted
Do you want to push these migrations to the remote database?
 • 20260106140000_fix_advisor_issues.sql
 
 [Y/n] y
Applying migration 20260106140000_fix_advisor_issues.sql...
NOTICE (00000): policy "Users can view own failed tasks" for relation "public.failed_tasks" does not exist, skipping
NOTICE (00000): policy "Users can update own failed tasks" for relation "public.failed_tasks" does not exist, skipping
NOTICE (00000): policy "Service role full access to failed_tasks" for relation "public.failed_tasks" does not exist, skipp
ing
Finished supabase db push.
A new version of Supabase CLI is available: v2.67.1 (currently installed v2.65.5)
We recommend updating regularly for new features and bug fixes: https://supabase.com/docs/guides/cli/getting-started#updat
ing-the-supabase-cli
onronder@Onurs-MacBook-Air axial % git add -A
git commit -m "fix: address Supabase advisor security and performance issues"
git push
[main d6e8fc5] fix: address Supabase advisor security and performance issues
 1 file changed, 421 insertions(+)
 create mode 100644 supabase/migrations/20260106140000_fix_advisor_issues.sql
Enumerating objects: 8, done.
Counting objects: 100% (8/8), done.
Delta compression using up to 8 threads
Compressing objects: 100% (5/5), done.
Writing objects: 100% (5/5), 2.43 KiB | 2.43 MiB/s, done.
Total 5 (delta 3), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (3/3), completed with 3 local objects.
To https://github.com/onronder/axial.git
   ec0e5da..d6e8fc5  main -> main
onronder@Onurs-MacBook-Air axial % 


Sub-task checklist:
- [ ] Inventory all secrets and access keys used by API and workers.
- [ ] Rotate secrets and update deployments.
- [ ] Audit RLS policies for all ingestion-related tables.
- [ ] Add or update tests that validate cross-tenant isolation.
- [ ] Identify sensitive fields in logs and DLQ payloads.
- [ ] Implement log and DLQ redaction for sensitive fields.
- [ ] Review and tighten CORS configuration.
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
- TBD

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
Decision:
- Approval: Propose the standard benchmark datasets.
- Release gates (initial):
  - Success rate: > 95% of files processed without error.
  - Latency (p50): < 30s for standard text PDFs.
  - Blocker: Any 500 Internal Server Error during ingestion blocks release.

1. Benchmark Dataset Definitions
Status: ❌ Not defined in code

Test Harness Found:

Location: 
backend/tests/unit/test_performance.py
Framework: pytest with pytest-benchmark
Existing Benchmark Tests:

@pytest.mark.benchmark
test_benchmark_single_document_processing()
  - Measures: Single document processing time
  - No predefined dataset
@pytest.mark.benchmark
test_benchmark_batch_processing()
  - Measures: 10 documents processing
  - No predefined dataset (uses mock_documents fixture)
@pytest.mark.benchmark
test_benchmark_connector_fetch()
  - Measures: 100 file fetches
  - Uses: Generated mock data (b"x" * 1024)
@pytest.mark.benchmark
test_benchmark_memory_usage()
  - Measures: Memory for 50 × 1MB files
  - Uses: Generated data (b"x" * 1MB)
@pytest.mark.benchmark
test_benchmark_concurrent_processing()
  - Measures: 20 concurrent documents
  - Uses: Simulated processing (asyncio.sleep)
Dataset Characteristics (from tests):

Single doc: Undefined size
Batch: 10 documents
Connector: 100 files @ 1KB each
Memory: 50 files @ 1MB each
Concurrent: 20 documents
Missing:

❌ No real-world representative datasets
❌ No PDFs, DOCX, code files test data
❌ No multi-GB test files
❌ No benchmark corpus definition
2. Test Harness Selection
Framework: pytest Configuration: 
backend/pytest.ini

testpaths = tests
asyncio_mode = auto
addopts = -v --tb=short
Markers:
- unit: Unit tests (fast, no external dependencies)
- integration: Integration tests (may require external services)
- slow: Slow tests (skip with -m "not slow")
- benchmark: Performance benchmarks (not in pytest.ini)
Test Organization:

tests/
├── unit/          # 34 files
├── integration/   # 4 files
├── load/          # 2 files
├── security/      # 1 file
└── conftest.py    # Shared fixtures
Fixtures (from conftest.py):

@pytest.fixture
def mock_supabase()  # Mock DB
def mock_openai_embeddings()  # Mock embeddings
def sample_document()  # Test document
def sample_chunks()  # Test chunks
def mock_environment()  # Test env vars
No formal test data:

No CSV/JSON datasets
No test file repository
No golden outputs for comparison
3. Release Gate Thresholds
Status: ❌ Not defined in code

Found References (from RefactoringPlan docs):

RefactoringPlan_Phase1_Implementation.md:437
"Define release gate thresholds and publish results."
❌ Not implemented
Hardcoded Test Assertions:

# From test_performance.py (not formal gates)
Line 70:
assert processing_time < 10  # 10 docs in <10 seconds
Line 102:
assert fetch_time < 5  # 100 files in <5 seconds
Line 147:
assert peak < 500 * 1024 * 1024  # <500MB for 50×1MB
Line 203:
assert concurrent_time < 1  # <1 second with concurrency
These are NOT release gates, just test assertions

4. Current Testing Infrastructure
Unit Tests:

test_ingest_tasks.py
test_worker_progress.py
test_settings.py
test_performance.py (benchmarks)
test_notifications.py
test_ingestion_pipeline.py
28+ more files
Integration Tests:

4 files in tests/integration/
Load Tests:

2 files in tests/load/
No CI/CD configuration found:

❌ No .github/workflows/
❌ No .gitlab-ci.yml
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
