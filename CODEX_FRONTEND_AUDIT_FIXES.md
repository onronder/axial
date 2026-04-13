# Frontend Audit — Consolidated Findings & Fixes (v2)

**Status:** DESIGN LOCK — ready for implementation  
**Priority:** PRE-GO-LIVE (performance & UX quality)  
**Source:** Claude audit (3 agents) + Codex audit — deduplicated, merged, Codex-reviewed  
**Commit base:** 2c7972f (Wave 4 complete)  
**Review round:** 2 — 7+3 Codex findings applied (see changelog at bottom)

---

## Overview

Two independent audits found 16 raw issues. After deduplication and one review
round, **9 items remain in pre-go-live scope** organized into 3 tiers, plus a
post-launch refactor bucket. Items removed or demoted are documented in the
changelog.

---

## CRITICAL — Auth Bootstrap Duplication

### F1. useAuth duplicates SessionProvider — kill the duplication `[X]`

**Problem:** `useAuth()` (`hooks/useAuth.ts:81-140`) independently calls
`supabase.auth.getSession()` and subscribes to `onAuthStateChange()`. This is
identical to what `SessionProvider` (`components/providers/SessionProvider.tsx:30-66`)
already does at the app root. Every component that calls `useAuth()` opens its
own Supabase auth subscription and fires its own session fetch.

**Affected consumers (6+):**
- `app/dashboard/layout.tsx:38`
- `app/auth/layout.tsx:16`
- `components/layout/DashboardSidebar.tsx:32`
- `hooks/useIngestionProgress.tsx:62` (via `global-progress.tsx:60`)
- `app/dashboard/settings/general/page.tsx:51`
- `hooks/useIngestionJobs.ts:74`

**Fix:** Refactor `useAuth` to be a thin wrapper around `useSession()` context.
Remove the independent `getSession()` call and `onAuthStateChange` subscription
from `useAuth`. All auth state must flow from the single `SessionProvider`
subscription. `useAuth` should only add the action methods (`login`, `register`,
`logout`, `signInWithOAuth`, `resetPassword`, `updatePassword`) and the
`mapUser()` transform on top of the session context.

```typescript
// Target shape of useAuth — NO independent subscription
export const useAuth = () => {
    const { session, user: rawUser, loading } = useSession();
    const router = useRouter();
    const user = useMemo(() => mapUser(rawUser), [rawUser]);
    // ... action methods (login, register, logout, etc.) unchanged
    return { user, loading, isAuthenticated: !!user, login, register, ... };
};
```

**Test:** After fix, place a `console.count("auth-subscribe")` inside
`onAuthStateChange` callback. On full app load, count must be exactly 1
(from SessionProvider only).

### F2. Auth redirect ownership scattered across 4 locations `[X]`

**Problem:** SIGNED_OUT navigation is handled in multiple places simultaneously:
- `SessionProvider.tsx:58` — pushes `/login` on SIGNED_OUT
- `useAuth.ts:124-126` — pushes `/login` on SIGNED_OUT (duplicate)
- `app/dashboard/layout.tsx:~43` — unauthenticated fallback redirect
- `app/auth/layout.tsx:~19` — authenticated user redirect to `/dashboard`

Multiple actors on the same navigation event cause transient blank renders and
redundant route transitions.

**Fix:** Consolidate to exactly three redirect owners, each with a single
non-overlapping responsibility:
1. **SessionProvider** — sole owner of SIGNED_OUT event → `/login` redirect
2. **Dashboard layout** — sole owner of unauthenticated render guard → `/login`
3. **Auth layout** — sole owner of authenticated render guard → `/dashboard`

Remove the SIGNED_OUT redirect from `useAuth` entirely (it's now just a context
consumer). Remove any redundant redirect logic in `useAuth.logout()` that
races with SessionProvider's event handler — `logout()` should only call
`supabase.auth.signOut()` + `clearAuthCache()` and let SessionProvider handle
the navigation.

---

## HIGH — Re-render & Data Fetching

### F3. SessionProvider context value not memoized `[CX]`

**File:** `components/providers/SessionProvider.tsx:73-78`

**Problem:** `value` object `{ session, user, loading, signOut }` is recreated
every render. Every consumer of `useSession()` re-renders even when the actual
values haven't changed.

**Fix:**
```typescript
const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    router.push("/login");
}, [router]);

const value = useMemo(
    () => ({ session, user, loading, signOut }),
    [session, user, loading, signOut]
);
```

### F4. Memoize the 4 unmemoized dashboard providers `[C, narrowed]`

**Context:** Dashboard layout nests 8 providers. Two already use `useMemo`:
ProfileProvider (`hooks/useProfile.tsx:116`) and UsageProvider
(`hooks/useUsage.ts:152`). DataInvalidationProvider
(`components/providers/DataInvalidationProvider.tsx:118`) also already uses
`useMemo`.

**The 4 that don't** (SessionProvider is also unmemoized but covered by F3):
- `QuotaStatusProvider` (`hooks/useQuotaStatus.tsx:286`)
- `ChatHistoryProvider` (`hooks/useChatHistory.tsx:262`)
- `IngestionProgressProvider` (`hooks/useIngestionProgress.tsx:162`)
- `IngestModalProvider` (`hooks/useIngestModal.tsx:30`)

**Fix:** Add `useMemo` to each of the 4 providers listed above. For each, wrap
the value object in `useMemo` with appropriate dependency arrays.

**Note:** This reduces context-value churn but does not fully solve provider
cascade — that requires a deeper refactor (selector-based context or Zustand)
which is post-launch scope.

### F5. DashboardSidebar missing React.memo `[C, narrowed]`

**File:** `components/layout/DashboardSidebar.tsx:29-176`

**Problem:** DashboardSidebar re-renders on any parent layout state change. It
receives no frequently-changing props, so `React.memo()` would effectively
prevent re-renders.

**Fix:** Wrap with `React.memo()`.

**Note:** ChatArea was removed from this item. ChatArea receives `messages`,
`isTyping`, `streamingMessage`, `thinkingStatus` as props — these change on
every interaction, making React.memo low ROI. If ChatArea perf is a concern,
the optimization target is MessageBubble/list virtualization, not memo on the
parent.

---

## MEDIUM — Unnecessary Load & Wiring

### F6. KnowledgeBaseBrowser — 500-doc client-side tree `[X]`

**File:** `KnowledgeBaseBrowser.tsx:106, 176, 184, 201`

**Problem:** `TREE_FETCH_LIMIT = 500` documents fetched upfront, then
`buildFolderTree()` runs entirely in browser. For large tenants this means
incomplete data (>500 docs truncated) AND heavy client computation.

**Fix:** Two options (choose one):
- **Option A (correct):** Add server-side `/documents/tree` endpoint that
  returns pre-built folder structure with pagination per folder. Client only
  fetches expanded folders on demand.
- **Option B (quick):** Keep client tree but add virtual scrolling
  (`react-window`) and increase limit with pagination. Still front-loads data
  but handles rendering efficiently.

**Recommendation:** Option A is correct long-term. If time-constrained, Option B
with a TODO for Option A post-launch. F6 should ship before any large-tenant
onboarding.

### F7. Ingestion complete — intentional double refresh `[X]`

**File:** `GlobalProgress.tsx:180-190`

**Problem:** On ingestion completion, `refresh(true)` + `invalidateQueries(["documents"])` +
`invalidateQueries(["documentCount"])` fires immediately, then the same set
fires again after 2 seconds. `useUsage.refresh()` also runs in parallel.
Every successful ingest triggers 2× the necessary network load.

**Fix:** Remove the delayed (2-second) duplicate invalidation. If the concern is
backend eventual consistency, use React Query's `refetchInterval` on the
documents query temporarily (e.g., 5s for 30s after ingest) instead of a
blind timeout retry.

### F8. useNotifications — extra profile fetch for user_id `[X]`

**File:** `hooks/useNotifications.ts:168-175`

**Problem:** Before setting up Supabase Realtime subscription, this hook fetches
`GET /settings/profile` just to extract `user_id`. The app already has
`user_id` available from SessionProvider and ProfileProvider.

**Fix:** Get `user_id` from `useSession()` context (`session.user.id`) instead
of making a separate API call.

### F9. DataInvalidationProvider re-resolves org/team `[X, clarified]`

**File:** `DataInvalidationProvider.tsx:67-77`

**Problem:** After getting user from session, it queries `team_members` to
extract organization/team info. This org wiring already exists in other
contexts within the app but is not easily accessible — ProfileProvider does
not currently carry org/team data.

**Fix:** The frontend profile model (`useProfile.tsx:8`) only carries `has_team`
and `role`; the backend `/settings/profile` endpoint (`settings.py:25,143`)
does not return `organization_id` or `team_id`. So this is not a simple
frontend rewire — backend work is required.

Two approaches:
- **Option A (backend + frontend):** Extend the `/settings/profile` response
  to include `organization_id` and `team_id`. Then expose these fields through
  ProfileProvider's context. DataInvalidationProvider reads from context
  instead of re-querying `team_members`.
- **Option B (new provider):** Create a dedicated `OrgProvider` that calls a
  new lightweight endpoint (e.g., `GET /team/identity`) returning only org/team
  IDs. DataInvalidationProvider consumes this context.

**Recommendation:** Option A — it's a small backend change (add two fields to an
existing serializer) plus a frontend context extension. Option B creates more
moving parts for the same result.

---

## POST-LAUNCH REFACTOR BUCKET

These items are architectural improvements, not runtime bugs. They should be
separate tickets, not part of the pre-go-live sprint.

### R1. useTeamMembers → React Query migration `[CX]`

**File:** `hooks/useTeamMembers.ts:158-175, 209, 332`

Currently uses `useState + useEffect` with manual `fetchStats()` calls during
mutations. Works correctly but lacks deduplication and cache. Convert to
React Query with `invalidateQueries(["team"])` pattern.

### R2. useUsage → React Query migration `[C]`

**File:** `hooks/useUsage.ts:64-139`

Custom `CACHE_DURATION` logic, `fetchInProgress` ref, AbortController.
Reimplements what React Query provides natively. Context value is already
memoized (UsageProvider:152). Functional but inconsistent with the rest of
the app's data layer.

### R3. useDataSources → React Query migration `[C]`

**File:** `hooks/useDataSources.ts:203-245`

`dedupedRequest` handles concurrent dedup but no persistent cache. Component
unmount = data gone, remount = full refetch. Not a user-visible bug but
causes unnecessary network on navigation.

### R4. Admin JobsDashboard — duplicate Realtime consumer `[X]`

**File:** `JobsDashboard.tsx:399`, `hooks/useIngestionJobs.ts:163`

GlobalProgress already subscribes to `ingestion_jobs` Realtime channel.
Admin JobsDashboard opens a second subscription. Admin-only, low impact.
Ideally share a single Realtime subscription via context.

---

## Implementation Order

**Phase 1 — Auth consolidation (F1 + F2 + F3):**
These three are tightly coupled. Fix F1 first (useAuth becomes context
consumer), then F2 (single redirect owner), then F3 (memoize context value).
Ship together.

**Phase 2 — Provider memoization + quick wins (F4 + F5 + F7 + F8):**
Memoize the 4 unmemoized providers, add React.memo to DashboardSidebar,
remove double refresh, fix useNotifications profile fetch. All independent,
quick fixes.

**Phase 3 — Larger items (F6 + F9):**
KnowledgeBaseBrowser refactor and DataInvalidationProvider rewire. These
require more design work. F6 must ship before large-tenant onboarding.

**Post-launch — Refactor bucket (R1 + R2 + R3 + R4):**
React Query migrations and admin Realtime dedup. Separate tickets, not
blocking go-live.

---

## Acceptance Criteria

1. `onAuthStateChange` subscription count = exactly 1 on full app load
2. No SIGNED_OUT redirect outside SessionProvider
3. SessionProvider value object is referentially stable when deps unchanged
4. QuotaStatusProvider, ChatHistoryProvider, IngestionProgressProvider, IngestModalProvider all memoize context values
5. DashboardSidebar wrapped in React.memo
6. Ingestion completion fires exactly 1 round of invalidation, not 2
7. useNotifications gets user_id from context, not from API call
8. All existing tests pass, no new full-page reloads introduced

---

## Explicitly Out of Scope

- **ChatArea React.memo** — low ROI; props change every interaction. If perf
  needed, target MessageBubble virtualization instead
- **Analytics page dynamic()** — App Router already does route-level code split
- **FeedbackButtons timer leak** — false positive; cleanup exists at line 111
- **useSecurityLog background polling** — React Query default
  `refetchIntervalInBackground` is already `false`; no runtime issue
- **Settings layout SSR conversion** — nice-to-have, not blocking
- **SignatureAnimation nested timer cleanup** — extremely low impact
- **useAnalytics + useFeedback query key dedup** — minor, not user-visible
- **Error boundary hard reload** — crash recovery paths, acceptable behavior

---

## Changelog

**v1 → v2 (Codex review round 1, 7 findings):**

1. **F4/F7/F8 demoted to post-launch refactor bucket (R1/R2/R3)** — these are
   architectural improvements, not runtime bugs. useUsage and useDataSources
   have working singleton/dedup logic. Pre-go-live should focus on real user-
   visible issues.
2. **F6 (provider cascade) narrowed** — ProfileProvider:116, UsageProvider:152,
   and DataInvalidationProvider:118 are already memoized. Fix now targets only
   the 4 unmemoized providers. Acceptance criterion updated from "all 8" to
   the specific 4. Also clarified that memoization reduces context-value churn
   but does not fully solve cascade.
3. **F5 narrowed to DashboardSidebar only** — ChatArea receives frequently-
   changing props (messages, isTyping, streamingMessage, thinkingStatus);
   React.memo has low ROI there. Real ChatArea perf target is MessageBubble/
   list diff, not parent memo.
4. **F14 (analytics code-split) removed** — Next.js App Router already does
   route-level code splitting. Adding `dynamic(..., { ssr: false })` on top
   is unnecessary and could harm UX.
5. **F15 (FeedbackButtons timer leak) removed** — false positive. Cleanup
   already exists at `FeedbackButtons.tsx:111`: `return () => clearTimeout(timer)`.
   Only unused props remain, which is too minor to track.
6. **F11 (useSecurityLog background polling) removed** — React Query's default
   for `refetchIntervalInBackground` is `false`. No explicit opt-in found in
   the hook. Not a real runtime issue.
7. **F13 (DataInvalidationProvider) clarified** — ProfileProvider does not
   currently carry org/team data, so "just read from existing context" was
   underspecified. Added concrete fix options: extend ProfileProvider payload
   or create OrgProvider.

**v2 → v2.1 (Codex review round 2, 3 findings):**

8. **F9 Option A rewritten** — ProfileProvider does not fetch org/team data and
   backend `/settings/profile` does not return `organization_id`/`team_id`.
   Fix now explicitly states backend serializer change is required before
   frontend rewire.
9. **F2 "exactly two" → "exactly three"** — directive listed 3 redirect owners
   but said "two". Fixed text to match the actual ownership model.
10. **F1 affected consumer path corrected** — `IngestionProgressProvider.tsx`
    reference updated to `useIngestionProgress.tsx:62` with note that the
    actual `useAuth` call site is `global-progress.tsx:60`.
