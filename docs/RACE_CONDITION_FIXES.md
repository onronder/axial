# Race Condition Fixes - Enterprise Grade Implementation

> **Version:** 1.0  
> **Implemented:** January 22, 2026  
> **Status:** Production Ready

---

## Executive Summary

This document describes the comprehensive race condition fixes implemented across the AXIO Hub platform. All fixes are production-grade, backward-compatible, and include fallback mechanisms for gradual deployment.

---

## Migration Required

Apply the following migration to enable all race condition protections:

```bash
supabase db push
# Or apply manually:
# psql -d your_database -f supabase/migrations/20260224000000_race_condition_fixes.sql
```

---

## 1. LLM Token Usage - Atomic Increment

### Problem
Read-Modify-Write race condition in concurrent chat requests could cause token drift:
- Request A reads: 1000 tokens
- Request B reads: 1000 tokens  
- Request A writes: 1100 tokens
- Request B writes: 1100 tokens (should be 1200!)

### Solution
Database RPC function `increment_llm_tokens` performs atomic upsert with increment:

```sql
-- Called from backend/services/usage.py
SELECT * FROM increment_llm_tokens(
    p_org_id := 'uuid',
    p_tokens := 100,
    p_provider := 'openai',
    p_model := 'gpt-4'
);
-- Returns: (new_total, previous_total)
```

### Backend Integration
- **File:** `backend/services/usage.py`
- **Function:** `record_llm_usage()`
- **Fallback:** Legacy upsert if RPC doesn't exist

---

## 2. Box Token Refresh - Distributed Locking

### Problem
Box refresh tokens are **single-use**. Concurrent refresh attempts would invalidate each other:
- Request A uses refresh_token_v1 → gets refresh_token_v2
- Request B uses refresh_token_v1 (already used!) → FAILS
- Request A saves refresh_token_v2
- Integration is now broken

### Solution
Distributed lock via database before refresh:

```python
# Acquire lock
lock_acquired = supabase.rpc("acquire_lock", {
    "p_lock_key": f"box_token_refresh:{integration_id}",
    "p_locked_by": str(uuid.uuid4()),
    "p_ttl_seconds": 60
}).execute()

# If not acquired, wait and re-check tokens (another process may have refreshed)
```

### Backend Integration
- **File:** `backend/services/oauth_token_manager.py`
- **Function:** `refresh_box_token()`
- **New helpers:** `_acquire_refresh_lock()`, `_release_refresh_lock()`, `_get_fresh_integration_tokens()`

### Lock Flow
```
1. Check if token expired
2. Try to acquire lock
3. If locked by another:
   a. Wait 2 seconds
   b. Re-fetch tokens from DB
   c. If still expired, retry lock acquisition
4. After lock acquired:
   a. Double-check tokens (another process may have refreshed)
   b. Refresh if still needed
   c. Save new tokens
5. Always release lock in finally block
```

---

## 3. Webhook Idempotency - Duplicate Prevention

### Problem
Payment provider (Polar) webhooks may be retried, causing duplicate processing:
- Subscription created webhook arrives
- Processing starts
- Webhook is retried (network timeout)
- Duplicate subscription record created

### Solution
Database table `processed_webhook_events` with unique constraint:

```sql
CREATE TABLE processed_webhook_events (
    event_id TEXT NOT NULL,
    source TEXT NOT NULL,
    event_type TEXT,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_webhook_event_source UNIQUE (event_id, source)
);
```

RPC `try_process_webhook` atomically checks and records:

```sql
SELECT try_process_webhook('evt_123', 'polar', 'subscription.created');
-- Returns: TRUE (process it) or FALSE (already processed)
```

### Backend Integration
- **File:** `backend/services/subscription.py`
- **Function:** `_check_webhook_idempotency()`
- **Called at:** Start of `_upsert_subscription()`

### Auto-Cleanup
Events older than 7 days are automatically cleaned up to prevent table bloat.

---

## 4. Team Seat Limits - Database Constraint

### Problem
Concurrent invites could exceed seat limit:
- Admin A checks: 4/5 seats used
- Admin B checks: 4/5 seats used
- Admin A invites user → 5/5 seats
- Admin B invites user → 6/5 seats!

### Solution
Database trigger `enforce_team_seat_limit` on INSERT:

```sql
CREATE TRIGGER enforce_team_seat_limit
    BEFORE INSERT ON team_members
    FOR EACH ROW
    EXECUTE FUNCTION check_team_seat_limit();
```

Trigger dynamically calculates max seats from subscription plan:
- Enterprise: 50 seats
- Pro: 5 seats
- Starter: 3 seats
- Free: 1 seat

### Backend Integration
- **File:** `backend/services/team_service.py`
- **Function:** `invite_member()`
- **Error handling:** Catches `P0001` error code and returns friendly message

---

## 5. File Status Updates - Idempotency

### Problem
Celery task retries cause redundant database writes:
- Task processes file, updates status to "parsing"
- Task fails, retries
- Task re-updates status to "parsing" (unnecessary write)

### Solution
Database function `update_file_status_if_changed` only writes if state changed:

```sql
SELECT update_file_status_if_changed(
    p_file_status_id := 'uuid',
    p_new_status := 'parsing',
    p_progress := 50
);
-- Returns: TRUE if updated, FALSE if unchanged
```

### Backend Integration
- **File:** `backend/worker/tasks.py`
- **Function:** `update_file_status()`
- **Benefit:** Reduces database writes and realtime events during retries

---

## Database Objects Created

### Tables
| Table | Purpose |
|-------|---------|
| `processed_webhook_events` | Webhook idempotency tracking |
| `distributed_locks` | Distributed locking for token refresh |

### Functions (RPC)
| Function | Purpose |
|----------|---------|
| `increment_llm_tokens` | Atomic token increment |
| `decrement_llm_balance` | Atomic balance decrement |
| `try_process_webhook` | Atomic idempotency check |
| `acquire_lock` | Acquire distributed lock |
| `release_lock` | Release distributed lock |
| `check_lock` | Query lock status |
| `update_file_status_if_changed` | Idempotent status update |
| `cleanup_old_webhook_events` | GDPR-compliant cleanup |

### Triggers
| Trigger | Table | Purpose |
|---------|-------|---------|
| `enforce_team_seat_limit` | `team_members` | Prevent concurrent invite race |

---

## Backward Compatibility

All fixes include fallback mechanisms:

```python
try:
    # Try atomic RPC
    result = supabase.rpc("increment_llm_tokens", {...}).execute()
except Exception as exc:
    if "does not exist" in str(exc):
        # Fallback to legacy behavior if migration not applied
        await _record_llm_usage_fallback(...)
```

This allows:
1. Gradual rollout
2. Migration at convenient time
3. No downtime during deployment

---

## Monitoring Recommendations

### Logs to Watch
```
🔒 [Box] Token refresh locked     → Lock contention (healthy)
🔄 Duplicate event detected       → Idempotency working
⚠️ RPC not found, using fallback → Migration needed
```

### Metrics to Add (Future)
- `race_condition_prevented_total{type="token_drift"}`
- `race_condition_prevented_total{type="box_refresh"}`
- `race_condition_prevented_total{type="duplicate_webhook"}`
- `race_condition_prevented_total{type="seat_limit"}`

---

## Testing

### Manual Test: Token Drift
```bash
# Run 10 concurrent chat requests
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/v1/chat \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"message": "test"}' &
done
wait

# Verify token count = exactly 10 * tokens_per_request
```

### Manual Test: Box Token Refresh
```bash
# Set access token to expire in 1 second
# Run 5 concurrent requests that trigger refresh
# Verify only 1 refresh happened (check logs for single "🔄 Refreshing Box token")
```

### Manual Test: Webhook Idempotency
```bash
# Send same webhook payload twice
curl -X POST http://localhost:8000/webhooks/polar \
  -d '{"id": "evt_test_1", "type": "subscription.created", ...}'

curl -X POST http://localhost:8000/webhooks/polar \
  -d '{"id": "evt_test_1", "type": "subscription.created", ...}'

# Second request should log: "🔄 Duplicate event detected"
```

---

## Deployment Checklist

- [ ] Apply migration: `supabase db push`
- [ ] Deploy backend changes
- [ ] Verify logs show RPC calls (not fallback warnings)
- [ ] Monitor for race condition prevention logs
- [ ] Run load tests to verify fixes

---

## Files Modified

| File | Changes |
|------|---------|
| `supabase/migrations/20260224000000_race_condition_fixes.sql` | New migration |
| `backend/services/usage.py` | Atomic token increment |
| `backend/services/subscription.py` | Webhook idempotency |
| `backend/services/oauth_token_manager.py` | Distributed locking for Box |
| `backend/services/team_service.py` | DB trigger error handling |
| `backend/worker/tasks.py` | Idempotent file status updates |
