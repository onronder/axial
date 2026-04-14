# YouTube Transcript Reliability Plan

## Goal

Define a realistic, low-cost path for YouTube ingestion reliability in Axio.

Target outcome:

- no more "stuck" YouTube jobs
- clear failure reasons
- predictable product behavior
- a path to higher reliability later without locking into one vendor now

## Hard Truth

Reliable YouTube transcript fetching from cloud infrastructure is not free.

If Axio runs transcript fetches from shared cloud worker IPs, YouTube will block some or many requests.
That means the following combination is not realistic:

- SaaS cloud workers
- no proxy / no unlocker / no residential path
- "kusursuz" YouTube transcript fetching

Today there are only 3 credible models:

1. Managed anti-bot provider
2. Customer-hosted worker / BYO network path
3. Manual transcript input fallback

If we do not want to pay for a provider yet, we should not position YouTube URL ingestion as a reliable automatic feature.

## Product Decision

### Short-term decision

Keep YouTube ingestion available only as:

- `best effort` automatic transcript fetch
- with strong user-facing error reporting
- with manual fallback when automatic fetch fails

### What we should NOT promise

Do not promise:

- every public YouTube URL will ingest
- transcript fetch will always work from Axio cloud
- long videos are supported if transcript access is blocked

### What we CAN promise

We can promise:

- if transcript is accessible, we ingest it quickly
- if transcript is not accessible, the user sees the exact reason
- the job will not remain stuck
- the user has a fallback path

## Recommended Phases

## Phase 0: Immediate Stabilization ($0)

Objective: stop misleading behavior and reduce noisy failures.

### Required changes

1. Disable direct cloud fallback in production.

- Set `YOUTUBE_DIRECT_FALLBACK=false`
- Reason: direct datacenter egress is the path most likely to hit IP blocks

2. Add a hard feature mode.

Add config:

- `YOUTUBE_INGEST_MODE=disabled|best_effort|provider_required`

Recommended behavior:

- development: `best_effort`
- production without provider: `best_effort` or `disabled`
- production with provider: `provider_required`

3. Separate YouTube from generic web crawl semantics.

Do not keep treating YouTube as a normal web crawl.

At minimum:

- keep a distinct `is_youtube` execution path
- separate status / notification language
- separate active-state logic

4. Keep detailed failure reason on the job.

Examples:

- `youtube_ip_blocked`
- `youtube_no_captions`
- `youtube_video_unavailable`
- `youtube_login_required`
- `youtube_unlocker_failed`

5. Add a kill switch.

Config:

- `YOUTUBE_INGEST_ENABLED=true|false`

If reliability becomes unacceptable in production, we should be able to turn off URL ingestion without redeploying.

### Acceptance criteria

- no YouTube job remains forever in `processing`
- failure reason is visible in job UI
- Web Scraper UI does not show YouTube work as crawl work

## Phase 1: Low-Cost Product Fallback ($0)

Objective: make YouTube usable even when automatic transcript fetch fails.

### Build manual fallback

If automatic YouTube fetch fails, offer:

1. paste transcript text
2. upload subtitle file (`.srt`, `.vtt`, `.txt`)
3. optional manual notes / summary

This is the only near-zero-cost way to make the end-user workflow reliable today.

### UX behavior

Flow:

1. user submits YouTube URL
2. Axio tries automatic transcript fetch
3. if fail, show exact reason
4. show CTA:
   - `Paste transcript`
   - `Upload subtitles`

### New source types

Recommended:

- `youtube`
- `youtube_manual`

### Acceptance criteria

- user can still ingest a YouTube source without auto-fetch succeeding
- support burden drops because the fallback is built into the UI

## Phase 2: Architectural Separation ($0 engineering, no vendor yet)

Objective: prepare for provider swaps later.

### Split connector abstraction

Current state:

- YouTube logic lives inside `backend/connectors/web.py`

Target state:

- move YouTube transcript logic to `backend/connectors/youtube.py`
- keep web crawl in `backend/connectors/web.py`

### Add provider abstraction

Define an interface like:

- `YouTubeTranscriptProvider.fetch(video_url) -> TranscriptResult`

Provider implementations:

- `DirectTranscriptProvider`
- `BrightDataTranscriptProvider`
- `ScrapingBeeTranscriptProvider`
- `ManualTranscriptProvider`

### Add a provider selection policy

Example config:

- `YOUTUBE_PROVIDER_ORDER=manual,brightdata,direct`

or

- `YOUTUBE_PROVIDER_PRIMARY=brightdata`
- `YOUTUBE_PROVIDER_FALLBACK=none`

### Separate queue and concurrency

Current state:

- YouTube shares `queues.parsing`
- YouTube shares `CONNECTOR_CONCURRENCY_WEB`

Target state:

- queue: `queues.youtube`
- config: `CONNECTOR_CONCURRENCY_YOUTUBE`

Recommended initial value:

- `CONNECTOR_CONCURRENCY_YOUTUBE=1`

Reason:

- YouTube is anti-bot sensitive
- lower concurrency reduces rate-limit and IP reputation damage

### Acceptance criteria

- YouTube failures do not affect generic web crawl throughput
- provider swap is a config and implementation change, not a pipeline rewrite

## Phase 3: Paid Reliability Path (Later)

Objective: increase automatic transcript success rate when the product starts paying for itself.

### Vendor strategy

Do not hard-wire Axio to one vendor.

Add at least one provider behind an interface:

- Bright Data
- ScrapingBee
- or another unlocker / residential browser provider

### Recommended policy

1. keep only one paid provider at first
2. add circuit breaker
3. if provider error rate spikes, fail fast with clear user message
4. only add second provider when volume justifies it

### Why not buy now

Because:

- the product is not monetized yet
- proxy cost without usage revenue is pure burn
- manual fallback covers the gap for early-stage usage

## Technical Work Items

## Backend

### Config

Add:

- `YOUTUBE_INGEST_ENABLED`
- `YOUTUBE_INGEST_MODE`
- `CONNECTOR_CONCURRENCY_YOUTUBE`
- `YOUTUBE_PROVIDER_PRIMARY`
- `YOUTUBE_PROVIDER_FALLBACK`

Update:

- default `YOUTUBE_DIRECT_FALLBACK=false` in production

### Connector refactor

Files:

- `backend/connectors/web.py`
- new `backend/connectors/youtube.py`

Move into YouTube connector:

- transcript fetch
- caption extraction
- provider selection
- YouTube-specific error taxonomy

### Worker changes

Files:

- `backend/worker/tasks.py`
- `backend/core/celery_app.py`

Changes:

- add `queues.youtube`
- route YouTube page processing there
- keep detailed failure reason in `ingestion_jobs.error_message`
- preserve terminal completion/failure semantics

### Data model

At minimum keep:

- source type distinction
- explicit error code
- explicit user message

Prefer adding:

- `provider_used`
- `provider_attempts`
- `youtube_video_id`
- `failure_category`

## Frontend

Files:

- `frontend-new/components/data-sources/YoutubeInput.tsx`
- `frontend-new/components/layout/global-progress.tsx`
- `frontend-new/components/ingestion/IngestionProgressModal.tsx`

Changes:

- show exact failure reason
- add manual transcript fallback CTA
- show feature as `Best effort` until paid reliability exists

## Observability

Track separately from normal web crawl:

- `youtube_fetch_success_total`
- `youtube_fetch_failed_total`
- `youtube_ip_blocked_total`
- `youtube_no_captions_total`
- `youtube_video_unavailable_total`
- `youtube_unlocker_failed_total`
- `youtube_fetch_latency_seconds`
- `youtube_stuck_jobs_total`

Sentry tags:

- `youtube_provider`
- `youtube_failure_category`
- `youtube_video_id`

## Reliability Policy

### Recommended job policy

- `youtube_ip_blocked`: fail fast, no same-path retry
- `youtube_no_captions`: fail terminal
- `youtube_video_unavailable`: fail terminal
- `youtube_login_required`: fail terminal
- `youtube_unlocker_failed`: retry with backoff only if provider is expected to be transient
- `unknown`: retry once, then fail with explicit message

### Recommended timeout policy

- preflight: 5-10s
- transcript fetch total budget: 30-45s
- no job should appear active indefinitely

## Recommended Rollout Order

### Week 1

1. set `YOUTUBE_DIRECT_FALLBACK=false` in production
2. add `YOUTUBE_INGEST_ENABLED`
3. add `YOUTUBE_INGEST_MODE`
4. keep detailed error message on job UI
5. add `Best effort` label to YouTube UI

### Week 2

1. build manual transcript paste/upload fallback
2. add `youtube_manual` source handling
3. add basic YouTube observability dashboard

### Week 3

1. split `youtube.py` from `web.py`
2. create provider interface
3. move YouTube work to `queues.youtube`
4. add `CONNECTOR_CONCURRENCY_YOUTUBE`

### Later

1. integrate first paid provider
2. add provider health checks
3. add second provider only when justified by revenue and volume

## Final Recommendation

If the budget is effectively $0 right now, the correct strategy is:

1. stop pretending YouTube URL ingestion is reliable from cloud IPs
2. keep it as best-effort
3. make failures explicit
4. ship manual transcript fallback
5. delay paid provider integration until usage and revenue justify it

That is the lowest-burn path that is still technically honest and product-usable.
