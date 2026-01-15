@workspace /explain 

**Role:** Principal AI Architect & Chaos Engineer
**Objective:** Perform a 360-degree audit of the Axial V2 Infrastructure. We must validate "Full-Stack Wiring", "Data Integrity", and "Hybrid-LLM Orchestration" (OpenAI + Grok).

---

### 🧩 Task 1: Hybrid-LLM Orchestration & Smart Routing (The Brain)
1. **Check:** `backend/services/router.py` & `backend/api/v1/chat.py`.
2. **Failover Logic:** Verify if a "Circuit Breaker" exists. If OpenAI (Fast or Pro) returns 429/5xx, does it fallback to Grok automatically?
3. **Complexity Routing:** Beyond context window size, identify if we can force OpenAI "Pro" for complex intents (e.g., 'refactor', 'architect') while using Grok or Mini for general queries.
4. **Prompt Optimization:** Do we adjust `scope_identity` formatting for Grok's specific attention mechanism?

---

### 🗄️ Task 2: Data Integrity & PGVector Purge (The Memory)
1. **Check:** `backend/services/cleanup.py` & `backend/worker/tasks.py`.
2. **Atomic Deletion:** Ensure `DELETE /organization` uses a single transaction. If a background ingestion is active, does a "Guard Rail" prevent deletion to avoid orphaned embeddings?
3. **Race Conditions:** Verify row-level locking (`SELECT FOR UPDATE`) on `scope_identities` during synthesis to prevent duplicate identity documents.

---

### 📉 Task 3: Token Budgeting & Scaling (The Limits)
1. **Check:** `backend/api/v1/chat.py` -> `get_scoped_prompt`.
2. **Global Identity Budget:** If a user selects `__all__` (Search All Sources), do we truncate individual `scope_identity` summaries to ensure the actual RAG chunks aren't pushed out of the LLM window?
3. **Billing Sync:** Verify that token usage from BOTH OpenAI and Grok is unified under the organization's global quota.

---

### 🔗 Task 4: 100% Wiring & UX Resilience (The Interface)
1. **Field Alignment:** Cross-check `scope_identities` DB fields with `frontend-new/types/index.ts`. Are there any naming mismatches (snake_case vs camelCase)?
2. **Error-to-Human Mapping:** Verify that `CustomException` codes (e.g., `PLAN_LIMIT_EXCEEDED`) are caught by the Frontend and displayed as friendly UI Toasts/Banners instead of raw 500 errors.
3. **Search All Wiring:** Confirm the "Search All Sources" button correctly passes the wildcard to the `hybrid_search_scoped` RPC without crashing.

---

**Output Requirement:**
Provide a **"Final Production-Readiness Report"**. Identify **BLOCKERS** (Security/Isolation/Billing) and **ADVISORIES** (UX/Performance).