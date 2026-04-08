# Pre-Faz4 Closure Directive — Zero-Gap Checkpoint

> **Goal:** Every Faz 1–3 feature must be fully wired, tested, and smoke-verified before Faz 4 begins.  
> **Constraint:** Backend code is written and reviewed. Work is frontend wiring, SSE contract, and verification.

---

## BLOCK A — Frontend Type, Render & Test Wiring (7 changes)

### A1. StreamEvent type — add warning fields
**File:** `frontend-new/lib/chat-utils.ts` line 108  
**Current:**
```ts
| { type: 'done'; message_id?: string }
```
**Change to:**
```ts
| { type: 'done'; message_id?: string; warning?: string; faithfulness_warning?: string; citations_stripped?: number }
```
**Why:** Backend `chat.py:2780-2784` sends `warning`, `faithfulness_warning` on the done SSE event. Frontend silently drops them because the union arm doesn't declare them.

---

### A2. ChatResult interface — add faithfulness_warning
**File:** `frontend-new/lib/chat-utils.ts` lines 116-122  
**Current:** no `faithfulness_warning` field  
**Add after `scope_context?`:**
```ts
faithfulness_warning?: string;
```
**Why:** Non-stream `ChatResponse` (backend `chat.py:517`) includes `faithfulness_warning`. The fetch-based non-stream path parses this as JSON → ChatResult, but the field is lost on the type.

---

### A3. SSE fallback parser — preserve done event fields
**File:** `frontend-new/lib/chat-utils.ts` lines 361-362  
**Current:**
```ts
yield { type: 'done' as const } satisfies StreamEvent;
```
**Change to:**
```ts
// Extract message_id and warning fields from malformed JSON
const messageIdMatch = jsonStr.match(/"message_id"\s*:\s*"([^"]+)"/);
const warningMatch = jsonStr.match(/"warning"\s*:\s*"([^"]+)"/);
const faithfulnessMatch = jsonStr.match(/"faithfulness_warning"\s*:\s*"([^"]+)"/);
yield {
    type: 'done' as const,
    ...(messageIdMatch && { message_id: messageIdMatch[1] }),
    ...(warningMatch && { warning: warningMatch[1] }),
    ...(faithfulnessMatch && { faithfulness_warning: faithfulnessMatch[1] }),
} satisfies StreamEvent;
```
**Why:** When SSE JSON parse fails, the fallback loses ALL fields except `type`. This is the only code path where `message_id` is already being dropped — but now `faithfulness_warning` matters too.

---

### A4. Done handler in page.tsx — read new fields
**File:** `frontend-new/app/dashboard/chat/[chatId]/page.tsx` line 597  
**Current:**
```ts
const doneEvent = event as { type: 'done'; message_id?: string };
```
**Change to:**
```ts
const doneEvent = event as {
    type: 'done';
    message_id?: string;
    warning?: string;
    faithfulness_warning?: string;
    citations_stripped?: number;
};
```
**Then after `serverMessageId` assignment (line 601), add:**
```ts
if (doneEvent.faithfulness_warning) {
    // Store warning for display in MessageBubble
    faithfulnessWarningRef.current = doneEvent.faithfulness_warning;
}
```
**Implementation note:** You'll need to add a `faithfulnessWarningRef = useRef<string | null>(null)` and thread it into the assistant message object that gets saved to state. When the streaming message is finalized (around where `setStreamingMessage(null)` is called and the message is pushed to history), include the warning.

---

### A5. Message interface — add warning fields
**File:** `frontend-new/hooks/useChatHistory.tsx` line 33-45  
**Add to Message interface:**
```ts
/** Faithfulness warning from LLM-as-Judge (informational, not blocking) */
faithfulness_warning?: string;
/** Number of hallucinated citation references stripped from response */
citations_stripped?: number;
```

---

### A6. MessageBubble — render faithfulness warning
**File:** `frontend-new/components/chat/MessageBubble.tsx`  
**Add to MessageBubbleProps interface (line 13):**
```ts
faithfulness_warning?: string;
```
**Add render block** inside the assistant message body, after the response text and before FeedbackButtons:
```tsx
{faithfulness_warning && (
    <div className="mt-2 flex items-start gap-2 rounded-md bg-warning/10 px-3 py-2 text-xs text-warning">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
        <span>{faithfulness_warning}</span>
    </div>
)}
```
**Import:** Add `AlertTriangle` from `lucide-react`.  
**Design:** Subtle amber banner, non-blocking, informational. Matches existing `warning` color tokens in tailwind config (`--warning: 38 92% 50%`).

---

### A7. Frontend test updates — cover new done event shape and warning render
The existing frontend tests use the old done event shape (`{ type: 'done' }` without warning fields). After A1-A6 changes, these tests will still pass but will NOT verify any new behavior. Add explicit coverage:

**File:** `frontend-new/__tests__/lib/chat-utils.test.ts`
- **Lines 735, 808, 840:** Existing done event tests use bare `{ type: 'done' }`.
- **Add new test case:** SSE stream with done event containing `message_id`, `faithfulness_warning`, `citations_stripped` → verify all fields are yielded.
- **Add new test case:** Malformed JSON fallback (the A3 regex path) → mock a malformed SSE line containing `"faithfulness_warning":"some warning"` → verify the fallback parser extracts it correctly instead of yielding bare `{ type: 'done' }`.

**File:** `frontend-new/__tests__/components/ChatPage.test.tsx`
- **Line 928-950:** One test already uses `{ type: 'done', message_id: 'server-msg-123' }` — extend it or add a sibling test that also includes `faithfulness_warning: 'Some claims may not be supported'`.
- **Verify:** After done event with `faithfulness_warning`, the finalized assistant message object in state includes the warning.
- **Lines 1180 and other mock generators:** These can stay as-is (optional fields are legitimately absent), but the NEW test must explicitly verify the warning propagation path.

**File:** `frontend-new/__tests__/components/MessageBubble.test.tsx`
- **Add 2 new test cases:**
  1. Render with `faithfulness_warning="Some claims may not be fully supported"` → assert amber warning banner is present, assert `AlertTriangle` icon renders, assert warning text is visible.
  2. Render without `faithfulness_warning` (undefined) → assert no warning banner is rendered.

**Rule:** No A1-A6 change is considered complete without its corresponding test in A7. Runtime code and test code ship together.

---

## BLOCK B — Backend Verification (1 item)

### B1. Unit test execution
**Context:** Tests exist in `backend/tests/` but were never executed because the sandbox runs Python 3.9.6 while the repo requires 3.11.6.

**Action:** Run tests in correct Python environment:
```bash
cd backend
python -m pytest tests/ -x -v --tb=short 2>&1 | head -100
```
Focus on:
- `tests/test_output_filter.py` — citation strip logic
- `tests/test_faithfulness_guard.py` — fail-open, threshold, timeout
- `tests/test_rag_analytics.py` — request_id keying, completion_status

If any test fails, fix the code, not the test (tests were written to match the spec).

**Runtime note:** Backend requires Python 3.11+ (see `runtime.txt`). Code uses `str | None` union syntax (PEP 604, Python 3.10+). Do NOT attempt to run tests on Python 3.9 — they will fail with syntax errors, not logic errors.

> **Optional (not a closure gate):** The repo has no mypy config (`mypy.ini`, `pyproject.toml [tool.mypy]`) and mypy is not in any requirements file. The quality gate is pytest + black + isort. Setting up mypy is a separate tooling initiative, not a Faz 1-3 closure item.

---

## BLOCK C — Migration & Data Operations

### C1. Apply migrations to staging Supabase (5 migrations) — ✅ DONE
```
1. 20260407110000_fix_fts_pipeline_simple.sql
2. 20260407113000_add_update_content_search_simple_rpc.sql
3. 20260407114000_regrant_ingest_rpc_permissions.sql
4. 20260407123000_create_rag_analytics.sql
5. 20260408100000_expand_rag_analytics_request_id_and_citations.sql
```
Already applied via `supabase db push --include-all`. Verified with `--dry-run` → "Remote database is up to date."

### ~~C2. Run content_search backfill~~ — REMOVED
~~`backend/scripts/backfill_content_search.py`~~

**Why removed:** The backfill script exists to populate `content_search` TSVECTOR for **pre-existing** document chunks that were ingested before the Faz 1 FTS pipeline fix. However, the product is pre-launch with no production users. The decision (made during Faz 3 pre-flight, L2 Opsiyon A) is to **delete all existing test sources and re-ingest from scratch**. Fresh ingest uses the corrected pipeline which populates `content_search` with `to_tsvector('simple', ...)` automatically.

This also eliminates the need for 5 environment secrets (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `SUPABASE_JWT_SECRET`, `OPENAI_API_KEY`, `CHUNK_ENCRYPTION_KEY`) that the backfill script requires to connect to Supabase and decrypt Ghost Protocol content.

**Action instead:** Before go-live, delete all data sources from the dashboard and re-ingest them. No script, no secrets, no ops overhead.

### ~~C3. Post-backfill maintenance~~ — REMOVED
~~`REINDEX CONCURRENTLY` + `ANALYZE`~~

**Why removed:** REINDEX and ANALYZE are only needed after a bulk backfill that writes thousands of rows without triggering autovacuum. Fresh ingest goes through normal insert paths, and PostgreSQL autovacuum handles index maintenance automatically. No manual ops step needed.

### C2. Verify rag_analytics partitions exist (was C4)
```sql
SELECT tablename FROM pg_tables
WHERE tablename LIKE 'rag_analytics_%'
ORDER BY tablename;
```
Expected: partitions for current month through 6 months ahead (e.g., `rag_analytics_2026_04` through `rag_analytics_2026_10`). These are precreated by migration #4 via `ensure_rag_analytics_partitions(6)` at apply time. pg_cron, if available, handles future monthly maintenance automatically; if not (as indicated by the `pg_cron not available` notice during push), partitions must be created manually or via a scheduled task before each new month.

---

## BLOCK D — End-to-End Smoke Test Checklist

After Blocks A-C are complete, verify these scenarios manually:

### D1. Non-stream chat (happy path)
- Send a query with `stream: false`
- Verify response includes `faithfulness_warning` field (may be null)
- Verify `rag_analytics` row exists with `request_id`, `completion_status = 'success'`, `message_id` populated

### D2. Stream chat (happy path)
- Send a query with `stream: true`
- Verify SSE done event includes `message_id`
- Verify `faithfulness_warning` appears in done event when faithfulness check fires a warning
- Verify `citations_stripped` count in done event when response has invalid [N] references
- Verify `rag_analytics` row matches

### D3. Citation strip (asymmetric behavior by design)
- Seed a scenario where LLM produces `[99]` reference with only 3 sources
- **Non-stream:** `_sanitize_response_output()` runs BEFORE response is returned (chat.py:2428). Verify `[99]` is **absent** from the `answer` field the client receives.
- **Stream:** Tokens are sent to the client in real-time (chat.py:2688-2693) BEFORE sanitization (chat.py:2705). The user **may see `[99]` in the live token stream** — this is expected behavior, NOT a bug. Sanitization runs post-hoc on the accumulated response. Verify:
  - `rag_analytics.citations_stripped_count > 0`
  - The DB-stored `message.content` does NOT contain `[99]`
  - The done event's `citations_stripped` count reflects the strip
- **Key principle:** The verification point for stream citation strip is the DB and analytics, never the live token stream.

### D4. Faithfulness warning render
- Trigger faithfulness warning (low-quality sources + hallucinated claim)
- Verify amber warning banner renders in MessageBubble (frontend)
- Verify warning is NOT blocking — answer still displays

### D5. No-answer path
- Query with zero matching documents
- Verify deterministic no-answer response (no LLM call)
- Verify `rag_analytics` row: `no_answer = true`, `completion_status = 'success'`

### D6. Cached response
- Send same query twice
- Second response should be from cache
- Verify `cached = true` in `rag_analytics`
- Verify `faithfulness_warning` is preserved from cache

### D7. Feedback correlation
- Submit thumbs-up/down on a message
- Verify `rag_analytics.user_feedback` is updated for matching `message_id`

### D8. Stream error (provider failure mid-stream)
- Simulate provider timeout after partial tokens
- Verify `rag_analytics.completion_status = 'partial_stream_failure'`
- Verify `partial_response_length` is populated
- Verify `rag_stream_failures_total` Prometheus counter increments

---

## Decision Lock Summary

| ID | Decision | Rationale |
|----|----------|-----------|
| A1-A6 | Frontend wiring exactly as specified | Backend already sends these fields; frontend silently drops them |
| A7 | Frontend tests ship with runtime code | Untested wiring is not verified wiring; tests cover done shape, fallback parser, and warning render |
| B1 | Run existing tests in Python 3.11+, fix code not tests | Tests were written to spec across Faz 1-3; repo quality gate is pytest, not mypy |
| C1 | Migrations already applied | Verified with `supabase db push --dry-run` |
| C2 | Backfill + REINDEX removed — re-ingest instead | Pre-launch, no prod users. Delete sources → re-ingest populates content_search via corrected pipeline. Eliminates 5 env secrets and ops overhead (Faz 3 pre-flight L2 decision) |
| D1-D8 | Manual smoke test, not automated E2E | No E2E framework exists; manual verification is sufficient for pre-launch |
| D3 | Stream citation strip is post-hoc by design | Live tokens may contain invalid [N]; verification point is DB + analytics, not token stream |

---

## Out of Scope (Faz 4)

These are explicitly NOT part of this closure:
- Language detection with fast-langdetect (Faz 4 feature)
- Per-language FTS retrieval parameterization
- Automated E2E test suite
- Production deployment (staging only for now)
