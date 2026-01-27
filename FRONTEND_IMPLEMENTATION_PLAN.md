# Frontend Implementation Plan (Revalidated)

> **Generated:** 2026-01-27  
> **Scope:** Critical + high-priority fixes validated against current code  
> **Total Items:** 14 core items + 2 design notes  

---

## Summary

This plan reflects the validated findings in the current `frontend-new` codebase. Obsolete items were removed, incorrect items were corrected, and three additional production gaps were added.

### Removed as Obsolete / Risky
- `useDataSources` state duplication - not a bug (React 18 batching, separate concerns)
- `useChatHistory` double source of truth - already React Query only
- Provider error boundaries - already in place with Sentry
- localStorage handling in `useQuotaStatus` - already wrapped in try/catch
- `useUsage` plan null during loading - required for PaywallGuard to avoid regressions
- Loading naming standardization - too broad, low value

### Corrected
- Supabase realtime cleanup targets (see Phase 1)
- Prefetch/Abort implementation details (export constants, Axios signals)

### Added Gaps
- Safe localStorage wrapper for onboarding + login remember-me + usage banner
- `useDocuments` optimistic update bug (query key mismatch)

---

## Phase 1 - Correctness & Resource Safety (CRITICAL)

### 1.1 Supabase channel cleanup (Memory leak prevention)
**Fix in:**
- `hooks/useQuotaStatus.tsx`
- `hooks/useIngestionJobs.ts` (incl. `useIngestionJobProgress`)
- `hooks/useNotifications.ts`

**Goal:** Ensure both `unsubscribe()` and `supabase.removeChannel()` are called on cleanup.

---

### 1.2 `useDocuments` optimistic update key mismatch (CRITICAL)
**Issue:** optimistic deletes target `['documents']` but actual query keys are `['documents', page, pageSize, search]`.

**Fix:**
- Introduce `DOCUMENTS_KEY` + `documentsQueryKey()` helper
- Use `setQueriesData` + rollback with `getQueriesData`

---

### 1.3 Safe localStorage utility (NEW)
**New file:** `lib/storage.ts`

**Update usage:**
- `hooks/useOnboarding.ts`
- `components/auth/LoginForm.tsx`
- `components/UsageWarningBanner.tsx`

---

### 1.4 `useDocumentCount` staleness
**Fix:** Convert to React Query (1 min stale time, refetch on focus)

---

### 1.5 Memoize citation rendering
**File:** `components/chat/MessageBubble.tsx`

**Fix:** Pre-parse citations with memoized segments and move regex to module scope.

---

## Phase 2 - UX & Loading (HIGH)

### 2.1 Skeleton loaders
**Files:**
- `components/documents/DocumentList.tsx`
- `components/knowledge-base/DocumentsTable.tsx`

**Add:**
- `components/documents/DocumentListSkeleton.tsx`
- `components/knowledge-base/DocumentsTableSkeleton.tsx`

---

### 2.2 Lazy-load global modals
**Files:**
- `components/lazy/index.ts`
- `components/lazy/ModalLoadingFallback.tsx`
- `app/dashboard/layout.tsx`

**Target:** Global modals (`GlobalIngestModal`, `GlobalProgress`) with `Suspense` fallbacks.

---

### 2.3 Accessible spinners (ARIA)
**New file:** `components/ui/spinner.tsx`
**Update:** replace all `Loader2` spinners with `Spinner`.

---

## Phase 3 - Performance (HIGH)

### 3.1 Virtualized document lists
**Files:**
- `components/documents/DocumentList.tsx`
- `components/knowledge-base/DocumentsTable.tsx`

**Strategy:**
- Window virtualizer for list view
- Row virtualization for grid/table when items >= 50

---

### 3.2 Dashboard prefetching
**New file:** `lib/prefetch.ts`
**Update:** `app/dashboard/layout.tsx`

Prefetch chat history + default documents page on dashboard entry.

---

### 3.3 Abort signals for API calls
**Files:**
- `hooks/useDocuments.ts`
- `hooks/useChatHistory.tsx`

Use React Query `signal` and pass to axios config.

---

## Phase 4 - Reliability & Monitoring (HIGH)

### 4.1 Realtime connection status indicator
**New file:** `hooks/useRealtimeStatus.ts`
**New file:** `components/layout/ConnectionStatusIndicator.tsx`
**Update:** `app/dashboard/layout.tsx`

Use `channel.subscribe` status callbacks (SUBSCRIBED, CLOSED, CHANNEL_ERROR, TIMED_OUT).

---

### 4.2 Cross-tab React Query sync (BroadcastChannel)
**New file:** `lib/crossTabSync.ts`
**Update:** `components/providers/QueryProvider.tsx`

Use source IDs + suppression set to avoid echo loops. Broadcast updates/invalidation.

---

## Testing Checklist

### Unit
- `useDocuments` optimistic delete correctly updates cache + rollback
- `safeLocalStorage` handles exceptions
- `useDocumentCount` uses `/documents/stats`

### Integration
- Supabase subscriptions cleaned up without lingering channels
- Cross-tab cache sync updates on another tab

### E2E
- Virtualized lists scroll smoothly at 500+ docs
- Lazy modals load with fallback and no blocking
- Realtime indicator shows on simulated disconnect

---

## Implementation Notes
- Keep all changes client-safe (avoid SSR-only APIs in server components).
- Avoid regressions in PaywallGuard loading behavior.
- Maintain existing UI layout and component semantics where possible.

