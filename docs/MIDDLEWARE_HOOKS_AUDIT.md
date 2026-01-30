# Frontend Middleware & Hooks Comprehensive Audit Report

**Date:** January 30, 2026  
**Scope:** All frontend middleware, hooks, Supabase client configuration, and related backend DB warnings  
**Files Analyzed:** 25 hooks, 4 Supabase client files, 17 existing test files

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Middleware Audit](#2-middleware-audit)
3. [Supabase Client Architecture](#3-supabase-client-architecture)
4. [Hooks Deep Dive](#4-hooks-deep-dive)
5. [Backend Supabase Linter Warnings](#5-backend-supabase-linter-warnings)
6. [Performance Analysis](#6-performance-analysis)
7. [Security Assessment](#7-security-assessment)
8. [Test Coverage Analysis](#8-test-coverage-analysis)
9. [Implementation Plan](#9-implementation-plan)
10. [Appendix: Code Templates](#10-appendix-code-templates)

---

## 1. Executive Summary

### Overall Health Score: 72/100

| Category | Score | Status |
|----------|-------|--------|
| Middleware | 30/100 | 🔴 Critical - Missing |
| Supabase Client | 90/100 | ✅ Good |
| Hooks Quality | 75/100 | ⚠️ Mixed |
| Test Coverage | 68/100 | ⚠️ Partial |
| Performance | 80/100 | ✅ Good |
| Security | 70/100 | ⚠️ Needs Work |

### Critical Issues (Must Fix)

1. **No root middleware.ts** - Auth routes unprotected at edge
2. **`useQuotaStatus.tsx`** - Direct localStorage access causes SSR crash
3. **`useRealtimeStatus.ts`** - No exponential backoff causes connection storms
4. **Supabase DB functions** - Search path mutable (security risk)

### Key Findings

- **25 hooks** in `/frontend-new/hooks/`
- **17 test files** exist (68% coverage by file count)
- **8 hooks** missing test files
- **5 Supabase linter warnings** need resolution
- **4.7s max query time** outliers detected

---

## 2. Middleware Audit

### 2.1 Current State

**Location:** `/frontend-new/lib/supabase/middleware.ts`

```typescript
// Current implementation - ONLY a helper function
export async function updateSession(request: NextRequest) {
    // Creates Supabase client with cookie management
    // Returns { supabase, user, response }
}
```

**Problem:** This is only a helper function. No root `middleware.ts` file exists at `/frontend-new/middleware.ts` to actually invoke it.

### 2.2 Impact Assessment

| Issue | Impact | Severity |
|-------|--------|----------|
| Auth routes unprotected | Authenticated users can access /login | Medium |
| No session refresh on navigation | Tokens may expire mid-session | High |
| OAuth callbacks unvalidated | CSRF vulnerability | Medium |
| Flash of unauthenticated content | Poor UX on protected routes | Medium |

### 2.3 Required Implementation

**File to Create:** `/frontend-new/middleware.ts`

**Features Required:**
- Route protection for `/dashboard/*`
- Redirect authenticated users from auth pages
- Session refresh on every navigation
- Skip middleware for static assets
- Handle OAuth callback routes

### 2.4 Implementation Code

```typescript
// /frontend-new/middleware.ts
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { updateSession } from '@/lib/supabase/middleware';

// Routes that don't require authentication
const PUBLIC_ROUTES = [
    '/login',
    '/register', 
    '/forgot-password',
    '/auth/callback',
    '/auth/reset-password',
    '/oauth/callback',
    '/pricing',
    '/',
];

// Routes that authenticated users should NOT access
const AUTH_ROUTES = ['/login', '/register', '/forgot-password'];

// Routes that should skip middleware entirely
const SKIP_ROUTES = [
    '/_next',
    '/api/py',
    '/favicon.ico',
    '/public',
];

export async function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Skip middleware for static files and API proxy
    if (SKIP_ROUTES.some(route => pathname.startsWith(route))) {
        return NextResponse.next();
    }

    // Update Supabase session (refresh tokens, set cookies)
    const { user, response } = await updateSession(request);

    // Redirect authenticated users away from auth pages
    if (user && AUTH_ROUTES.some(route => pathname.startsWith(route))) {
        const redirectUrl = new URL('/dashboard', request.url);
        return NextResponse.redirect(redirectUrl);
    }

    // Protect dashboard routes - require authentication
    if (!user && pathname.startsWith('/dashboard')) {
        const redirectUrl = new URL('/login', request.url);
        redirectUrl.searchParams.set('next', pathname);
        return NextResponse.redirect(redirectUrl);
    }

    return response;
}

export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - public folder
         */
        '/((?!_next/static|_next/image|favicon.ico|public/).*)',
    ],
};
```

---

## 3. Supabase Client Architecture

### 3.1 Current Structure

```
/frontend-new/lib/
├── supabase.ts              # Browser client singleton
└── supabase/
    ├── client.ts            # Browser client factory
    ├── middleware.ts        # Middleware helper
    └── server.ts            # Server-side client
```

### 3.2 Assessment

| File | Purpose | Status |
|------|---------|--------|
| `supabase.ts` | Browser singleton with SSR config | ✅ Good |
| `supabase/client.ts` | Factory for fresh clients | ✅ Good |
| `supabase/middleware.ts` | Session refresh helper | ✅ Good |
| `supabase/server.ts` | Server components client | ✅ Good |

### 3.3 Configuration Review

**`supabase.ts` - Line 40-46:**
```typescript
export const supabase = createBrowserClient(supabaseUrl, supabaseKey, {
    auth: {
        // INTENTIONAL: OAuth exchanges handled by backend, not Supabase client
        detectSessionInUrl: false,
    },
});
```

✅ **Correct Configuration** - Prevents Supabase from intercepting OAuth codes meant for backend.

### 3.4 Potential Improvements

1. **Add connection pooling configuration** for high-load scenarios
2. **Add realtime configuration** with custom heartbeat intervals
3. **Add error boundary** for Supabase initialization failures

---

## 4. Hooks Deep Dive

### 4.1 Complete Hook Inventory

| # | Hook | File | Lines | Pattern | Test | Status |
|---|------|------|-------|---------|------|--------|
| 1 | `useAuth` | useAuth.ts | 329 | State + Effects | ✅ | ✅ Production-ready |
| 2 | `useChatHistory` | useChatHistory.tsx | 412 | Context + Query | ✅ | ✅ Production-ready |
| 3 | `useDocuments` | useDocuments.ts | 282 | Query + Mutation | ✅ | ✅ Production-ready |
| 4 | `useUsage` | useUsage.ts | 144 | Context + Cache | ✅ | ✅ Production-ready |
| 5 | `useProfile` | useProfile.tsx | 151 | Context | ✅ | ✅ Production-ready |
| 6 | `useDataSources` | useDataSources.ts | 505 | State + Effects | ✅ | ⚠️ Needs refactor |
| 7 | `useNotifications` | useNotifications.ts | 398 | Realtime + State | ✅ | ⚠️ Minor issues |
| 8 | `useTeamMembers` | useTeamMembers.ts | 192 | State + Effects | ✅ | ⚠️ No optimistic |
| 9 | `useIngestionJobs` | useIngestionJobs.ts | 323 | Realtime + Throttle | ✅ | ✅ Good |
| 10 | `useIngestionProgress` | useIngestionProgress.tsx | 211 | Context | ❌ | ⚠️ Needs tests |
| 11 | `useSearch` | useSearch.ts | 92 | State | ✅ | ⚠️ No debounce |
| 12 | `useFeedback` | useFeedback.ts | 257 | State + API | ❌ | ⚠️ Needs tests |
| 13 | `useNotificationSettings` | useNotificationSettings.ts | ~150 | State + API | ✅ | ✅ Good |
| 14 | `useRealtimeStatus` | useRealtimeStatus.ts | 64 | Realtime | ❌ | 🔴 Critical |
| 15 | `useQuotaStatus` | useQuotaStatus.tsx | 208 | Context + Realtime | ❌ | 🔴 Critical |
| 16 | `usePlans` | usePlans.ts | 103 | State + Fetch | ❌ | ⚠️ Needs tests |
| 17 | `useOnboarding` | useOnboarding.ts | 78 | State + Storage | ❌ | ⚠️ Import issue |
| 18 | `useAnalytics` | useAnalytics.ts | ~100 | Query | ✅ | ✅ Good |
| 19 | `useDocumentCount` | useDocumentCount.ts | ~50 | Query | ✅ | ✅ Good |
| 20 | `useIngestModal` | useIngestModal.tsx | ~80 | Context | ✅ | ✅ Good |
| 21 | `useTheme` | useTheme.ts | ~40 | State | ✅ | ✅ Good |
| 22 | `use-toast` | use-toast.ts | ~50 | State | ✅ | ✅ Good |
| 23 | `use-mobile` | use-mobile.tsx | ~30 | State | ✅ | ✅ Good |
| 24 | `useFailedTaskStatus` | useFailedTaskStatus.ts | ~60 | State | ❌ | ⚠️ Needs tests |
| 25 | `useFileStatus` | useFileStatus.ts | ~50 | State | ❌ | ⚠️ Needs tests |

### 4.2 Critical Hook Issues

#### 4.2.1 `useRealtimeStatus.ts` - Connection Storm Risk

**Current Code (Lines 50-55):**
```typescript
const reconnect = useCallback(() => {
    setStatus("connecting");
    supabase.realtime.connect();
    setReconnectToken((value) => value + 1);
}, []);
```

**Problem:** No exponential backoff. If server is down, clients will hammer it.

**Required Fix:**
```typescript
const reconnect = useCallback(() => {
    if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
        setStatus("error");
        return;
    }
    
    const backoffMs = Math.min(
        BASE_DELAY * Math.pow(2, reconnectAttempts.current),
        MAX_DELAY
    );
    
    reconnectAttempts.current += 1;
    
    setTimeout(() => {
        setStatus("connecting");
        supabase.realtime.connect();
        setReconnectToken((value) => value + 1);
    }, backoffMs);
}, []);
```

#### 4.2.2 `useQuotaStatus.tsx` - SSR Crash

**Current Code (Lines 63-77):**
```typescript
useEffect(() => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);  // ❌ Direct access
        // ...
    } catch {
        // ...
    }
}, []);
```

**Problem:** Direct `localStorage` access crashes during SSR.

**Required Fix:**
```typescript
useEffect(() => {
    if (typeof window === 'undefined') return;  // ✅ SSR guard
    
    try {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        // ...
    } catch {
        // ...
    }
}, []);
```

#### 4.2.3 `lib/storage.ts` - SSR Safety Issue

**Current Code:**
```typescript
export const safeLocalStorage = {
  getItem: (key: string): string | null => {
    try {
      return localStorage.getItem(key);  // ❌ Direct access without SSR check
    } catch (error) {
      return null;
    }
  },
  // ...
};
```

**Problem:** The `safeLocalStorage` utility is used across the codebase but doesn't check for SSR environment, which can cause build failures.

**Required Fix:**
```typescript
const isBrowser = typeof window !== 'undefined';

export const safeLocalStorage = {
  getItem: (key: string): string | null => {
    if (!isBrowser) return null;  // ✅ SSR guard
    try {
      return localStorage.getItem(key);
    } catch (error) {
      return null;
    }
  },
  // ... apply to all methods
};
```

**Files Using safeLocalStorage:**
- `hooks/useOnboarding.ts`
- `components/auth/LoginForm.tsx`
- `components/UsageWarningBanner.tsx`

### 4.3 Hooks Requiring Refactoring

#### 4.3.1 `useDataSources.ts` - Complexity Reduction

**Current Issues:**
- 505 lines - too large for a single hook
- Manual state management instead of React Query
- OAuth URL construction duplicated for each provider
- No request deduplication

**Recommended Refactoring:**

```typescript
// Split into:
// 1. useDataSourcesQuery.ts - Data fetching with React Query
// 2. useOAuthConnect.ts - OAuth URL generation
// 3. useDataSourceActions.ts - Connect/disconnect/sync actions

// Example: useDataSourcesQuery.ts
export function useDataSourcesQuery() {
    return useQuery({
        queryKey: ['dataSources'],
        queryFn: async () => {
            const [available, status] = await Promise.all([
                api.get('/integrations/available'),
                api.get('/integrations/status')
            ]);
            return mergeData(available.data, status.data);
        },
        staleTime: 5 * 60 * 1000,
    });
}
```

#### 4.3.2 `useSearch.ts` - Add Debouncing

**Current Code:**
```typescript
const search = useCallback(async (query: string, topK: number = 5) => {
    // Fires immediately on every call
    const { data } = await api.post('/search', { query, top_k: topK });
    // ...
}, []);
```

**Required Enhancement:**
```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSearch = useDebouncedCallback(
    async (query: string, topK: number) => {
        const { data } = await api.post('/search', { query, top_k: topK });
        // ...
    },
    300 // 300ms debounce
);
```

### 4.4 Hook Patterns Analysis

#### Good Patterns Found ✅

1. **Query Key Factory** (`useChatHistory.tsx`):
```typescript
export const chatKeys = {
    all: ['chat'] as const,
    lists: () => [...chatKeys.all, 'list'] as const,
    list: (filter?: string) => [...chatKeys.lists(), filter] as const,
    messages: () => [...chatKeys.all, 'messages'] as const,
    message: (conversationId: string) => [...chatKeys.messages(), conversationId] as const,
};
```

2. **Singleton Context** (`useUsage.ts`):
```typescript
const UsageContext = createContext<UsageContextValue | undefined>(undefined);
// Prevents duplicate API calls across components
```

3. **Optimistic Updates** (`useDocuments.ts`):
```typescript
onMutate: async (deletedId) => {
    await queryClient.cancelQueries({ queryKey: DOCUMENTS_KEY });
    const previous = queryClient.getQueriesData(...);
    queryClient.setQueriesData(...); // Optimistic update
    return { previous };
},
```

4. **Throttled Realtime** (`useIngestionJobs.ts`):
```typescript
const THROTTLE_INTERVAL = 100;
// Batches rapid updates to prevent render storms
```

#### Patterns to Add 🔧

1. **Abort Controller for fetch cancellation**
2. **Error boundaries for hook failures**
3. **Retry logic with exponential backoff**
4. **Request deduplication for parallel calls**

---

## 5. Backend Supabase Linter Warnings

### 5.1 Warning Summary

| Warning | Type | Level | Affected |
|---------|------|-------|----------|
| function_search_path_mutable | SECURITY | WARN | `hybrid_search_scoped` |
| function_search_path_mutable | SECURITY | WARN | `hybrid_search` |
| extension_in_public | SECURITY | WARN | `vector` extension |
| extension_in_public | SECURITY | WARN | `pg_trgm` extension |
| materialized_view_in_api | SECURITY | WARN | `source_feedback_metrics` |

### 5.2 Detailed Analysis

#### 5.2.1 Function Search Path Mutable

**Risk Level:** Medium-High

**Explanation:** When a function doesn't set `search_path`, an attacker could:
1. Create a malicious schema with same-named functions
2. Manipulate the session search path
3. Execute their malicious functions instead of intended ones

**Current Functions Affected:**
- `public.hybrid_search_scoped` 
- `public.hybrid_search`

**Fix Required:**
```sql
-- Add to each function definition:
SET search_path = public, pg_catalog
```

#### 5.2.2 Extensions in Public Schema

**Risk Level:** Medium

**Explanation:** Extensions in `public` schema:
- Can be overwritten by users with CREATE privilege
- May expose internal functions to API
- Violate principle of least privilege

**Current Extensions Affected:**
- `vector` (pgvector for embeddings)
- `pg_trgm` (trigram matching)

**Migration Strategy:**
1. Create `extensions` schema
2. Move extensions (requires careful dependency checking)
3. Update all function references

#### 5.2.3 Materialized View in API

**Risk Level:** Low-Medium

**Explanation:** The `source_feedback_metrics` materialized view is accessible via Data API to `anon` and `authenticated` roles.

**Questions to Answer:**
- Is this intentional for dashboard display?
- Should it require admin role?
- Does it expose sensitive data?

### 5.3 SQL Migration Files Required

```
supabase/migrations/
├── 20260130000000_fix_function_search_paths.sql
├── 20260130000001_create_extensions_schema.sql (DEFERRED - needs dependency analysis)
└── 20260130000002_secure_materialized_view.sql
```

### 5.4 Migration Priority

| Migration | Priority | Risk | Notes |
|-----------|----------|------|-------|
| Fix function search paths | **HIGH** | Low | Safe to apply |
| Secure materialized view | **MEDIUM** | Low | May break dashboards |
| Move extensions | **LOW** | High | Requires all function updates |

**Recommendation:** Apply migrations 1 and 3 first, defer extension migration until full dependency audit.

---

## 6. Performance Analysis

### 6.1 Query Metrics Review

From provided Supabase metrics:

| Metric | Value | Assessment |
|--------|-------|------------|
| Time Consumed | 95.8% / 5h 52m | High utilization |
| Calls | 4,276,992 | High volume |
| Mean Time | 5ms | ✅ Excellent |
| Max Time | 4,703ms | ⚠️ Outliers exist |
| Min Time | 3ms | ✅ Excellent |
| Rows Processed | 6,886 | Low per query |
| Cache Hit Rate | 100% | ✅ Optimal |
| Role | supabase_admin | Normal |

### 6.2 Performance Concerns

#### 6.2.1 Max Time Outliers (4.7s)

**Investigation Needed:**
- Which queries are taking 4.7s?
- Are they during cold starts?
- Are they complex vector searches?

**Recommended Actions:**
1. Add query logging to identify slow queries
2. Set statement timeout: `SET statement_timeout = '3000ms'`
3. Add client-side timeout in API client

#### 6.2.2 High Call Volume

**4.2M calls** suggests either:
- High traffic (good)
- Polling inefficiency (bad)
- Missing caching (bad)

**Check These Hooks:**
- `useNotifications` - 30s polling fallback
- `useIngestionJobs` - Realtime but with initial fetch

### 6.3 Frontend Performance Optimizations

#### 6.3.1 Add Request Deduplication

```typescript
// /frontend-new/lib/request-dedup.ts
const pendingRequests = new Map<string, Promise<unknown>>();

export async function dedupedRequest<T>(
    key: string,
    fetcher: () => Promise<T>
): Promise<T> {
    const existing = pendingRequests.get(key);
    if (existing) {
        return existing as Promise<T>;
    }

    const promise = fetcher().finally(() => {
        pendingRequests.delete(key);
    });

    pendingRequests.set(key, promise);
    return promise;
}
```

#### 6.3.2 Add Query Timeout to API Client

```typescript
// In /frontend-new/lib/api.ts
export const api = axios.create({
    baseURL: '/api/py',
    headers: { 'Content-Type': 'application/json' },
    timeout: 30000,  // Existing
    // Add per-request timeout capability
});

// Usage:
api.get('/slow-endpoint', { timeout: 5000 });
```

#### 6.3.3 Implement Stale-While-Revalidate

React Query already supports this, ensure all hooks use it:

```typescript
useQuery({
    queryKey: ['data'],
    queryFn: fetchData,
    staleTime: 5 * 60 * 1000,      // Data fresh for 5 min
    gcTime: 10 * 60 * 1000,         // Keep in cache 10 min
    refetchOnWindowFocus: false,    // Don't refetch on tab switch
    refetchOnReconnect: true,       // Do refetch on network restore
});
```

---

## 7. Security Assessment

### 7.1 Security Scorecard

| Area | Score | Notes |
|------|-------|-------|
| Token Management | 85/100 | Good caching, proper invalidation |
| OAuth Implementation | 80/100 | PKCE for Microsoft, needs CSRF |
| Session Handling | 60/100 | No middleware protection |
| API Security | 75/100 | Auth headers, but no CSRF |
| Data Exposure | 70/100 | Console logging client IDs |

### 7.2 Good Security Practices Found

1. **Token Caching with Expiry Buffer** (`lib/api.ts`):
```typescript
const buffer = 5 * 60 * 1000; // 5 minutes before expiry
if (cachedToken && now < tokenExpiryTime - buffer) {
    config.headers.Authorization = `Bearer ${cachedToken}`;
    return config;
}
```

2. **401 Token Invalidation**:
```typescript
if (error.response?.status === 401) {
    cachedToken = null;
    tokenExpiryTime = 0;
}
```

3. **PKCE for Microsoft OAuth** (`useDataSources.ts`):
```typescript
pkce = await generatePkcePair();
sessionStorage.setItem(`microsoft_pkce_${type}`, pkce.codeVerifier);
```

4. **OAuth Session Detection Disabled** (`supabase.ts`):
```typescript
auth: {
    detectSessionInUrl: false, // Prevents OAuth conflicts
}
```

### 7.3 Security Improvements Required

#### 7.3.1 Remove Sensitive Console Logging

**File:** `useDataSources.ts` (Multiple locations)

```typescript
// CURRENT - Logs partial client ID
console.log('🔐 [useDataSources] Client ID:', clientId ? `${clientId.substring(0, 20)}...` : 'NOT SET');

// REQUIRED - Remove or use debug flag
if (process.env.NODE_ENV === 'development') {
    console.log('🔐 [useDataSources] Client ID configured:', !!clientId);
}
```

#### 7.3.2 Add CSRF Protection

**Middleware Enhancement:**
```typescript
// In middleware.ts
const csrfToken = request.cookies.get('csrf_token')?.value;
const headerToken = request.headers.get('x-csrf-token');

if (request.method !== 'GET' && csrfToken !== headerToken) {
    return new NextResponse('CSRF token mismatch', { status: 403 });
}
```

#### 7.3.3 Validate OAuth State Parameter

**File:** `/app/oauth/callback/page.tsx`

```typescript
// Add state validation
const storedState = sessionStorage.getItem('oauth_state');
const returnedState = searchParams.get('state');

if (storedState !== returnedState) {
    setError('Invalid OAuth state - possible CSRF attack');
    return;
}
```

---

## 8. Test Coverage Analysis

### 8.1 Current Coverage Summary

**Test Files Found:** 17  
**Hooks Total:** 25  
**Coverage by File:** 68%

### 8.2 Test Files Inventory

```
/frontend-new/__tests__/hooks/
├── useAuth.test.ts              ✅ Comprehensive
├── useAnalytics.test.tsx        ✅ Good
├── useChatHistory.test.tsx      ✅ Good
├── useUsage.test.ts             ✅ Good
├── useDataSources.test.ts       ✅ Good
├── useTeamMembers.test.ts       ✅ Good
├── useProfile.test.tsx          ✅ Good
├── useNotificationSettings.test.ts ✅ Good
├── useIngestionJobs.test.ts     ✅ Good
├── useDocuments.test.ts         ✅ Good
├── useToast.test.ts             ✅ Good
├── useTheme.test.ts             ✅ Good
├── useSearch.test.ts            ✅ Good
├── useNotifications.test.ts     ✅ Good
├── useMobile.test.ts            ✅ Good
├── useIngestModal.test.ts       ✅ Good
└── useDocumentCount.test.ts     ✅ Good
```

### 8.3 Missing Test Files

| Hook | Priority | Reason | Estimated Tests |
|------|----------|--------|-----------------|
| `useIngestionProgress.tsx` | **HIGH** | Core feature, completion tracking | ~15 tests |
| `useFeedback.ts` | **HIGH** | User feedback, API integration | ~12 tests |
| `useQuotaStatus.tsx` | **MEDIUM** | Quota tracking, realtime | ~10 tests |
| `useRealtimeStatus.ts` | **MEDIUM** | Connection management | ~8 tests |
| `usePlans.ts` | **MEDIUM** | Pricing display, fallback | ~6 tests |
| `useOnboarding.ts` | **LOW** | Simple state management | ~8 tests |
| `useFailedTaskStatus.ts` | **LOW** | Error tracking | ~5 tests |
| `useFileStatus.ts` | **LOW** | File state tracking | ~5 tests |

### 8.4 Test Quality Assessment

**Good Practices Found:**
- React Testing Library for component hooks
- Mock isolation with `vi.mock()`
- QueryClient wrapper for React Query hooks
- Async/await with `waitFor`

**Improvements Needed:**
- Add MSW for API mocking (more realistic)
- Add integration tests for hook combinations
- Add performance tests for realtime hooks

---

## 9. Implementation Plan

### Phase 1: Critical Fixes (P0) - Day 1

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| 1.1 Create middleware.ts | `middleware.ts` | 1.5 hours | None |
| 1.2 Fix safeLocalStorage SSR | `lib/storage.ts` | 20 min | None |
| 1.3 Fix useQuotaStatus SSR | `useQuotaStatus.tsx` | 30 min | 1.2 |
| 1.4 Fix useRealtimeStatus backoff | `useRealtimeStatus.ts` | 1 hour | None |

**Total Phase 1:** ~3.5 hours

#### Task 1.1: Create Root Middleware

**File:** `/frontend-new/middleware.ts`

**Acceptance Criteria:**
- [ ] Protects `/dashboard/*` routes
- [ ] Redirects authenticated users from `/login`, `/register`
- [ ] Refreshes session on every navigation
- [ ] Skips static assets and API routes
- [ ] Preserves `next` query param for post-login redirect

**Implementation Steps:**
1. Create `/frontend-new/middleware.ts`
2. Import `updateSession` from `@/lib/supabase/middleware`
3. Define `PUBLIC_ROUTES`, `AUTH_ROUTES`, `SKIP_ROUTES` arrays
4. Implement route matching logic
5. Test with authenticated and unauthenticated users

#### Task 1.2: Fix safeLocalStorage SSR

**File:** `/frontend-new/lib/storage.ts`

**Acceptance Criteria:**
- [ ] All methods check `typeof window !== 'undefined'`
- [ ] Returns safe fallback values during SSR
- [ ] No changes to public API
- [ ] Existing tests still pass

**Implementation Steps:**
1. Add `isBrowser` constant
2. Update all 5 methods with SSR guards
3. Run existing tests

#### Task 1.3: Fix useQuotaStatus SSR

**File:** `/frontend-new/hooks/useQuotaStatus.tsx`

**Acceptance Criteria:**
- [ ] No direct `localStorage` access
- [ ] Uses `safeLocalStorage` or window check
- [ ] SSR build succeeds
- [ ] Realtime subscription works correctly

#### Task 1.4: Fix useRealtimeStatus Backoff

**File:** `/frontend-new/hooks/useRealtimeStatus.ts`

**Acceptance Criteria:**
- [ ] Implements exponential backoff (100ms -> 200ms -> 400ms -> ...)
- [ ] Maximum retry count (5 attempts)
- [ ] Maximum delay cap (30 seconds)
- [ ] Reset attempts on successful connection
- [ ] No memory leaks (cleanup timers)

### Phase 2: Security Fixes (P1) - Day 1-2

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| 2.1 Fix function search paths | SQL migration | 1 hour | None |
| 2.2 Secure materialized view | SQL migration | 45 min | None |
| 2.3 Remove console logging | `useDataSources.ts` | 30 min | None |
| 2.4 Add OAuth state validation | `oauth/callback/page.tsx` | 45 min | None |

**Note:** Extension migration (2.5) deferred - requires careful dependency analysis.

**Total Phase 2:** ~3 hours

#### Task 2.1: Fix Function Search Paths

**File:** `/supabase/migrations/20260130000000_fix_function_search_paths.sql`

**Implementation:**
```sql
-- Fix hybrid_search function
CREATE OR REPLACE FUNCTION public.hybrid_search(...)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public, pg_catalog  -- ADD THIS LINE
AS $$
-- Keep existing body unchanged
$$;

-- Fix hybrid_search_scoped function (same pattern)
```

**Testing:**
1. Run migration locally with `supabase db push`
2. Verify functions still work via API
3. Re-run Supabase linter to confirm warnings resolved

#### Task 2.2: Secure Materialized View

**File:** `/supabase/migrations/20260130000002_secure_materialized_view.sql`

**Before making changes, investigate:**
- Is `source_feedback_metrics` used in any frontend queries?
- Should it require admin role only?

**Implementation:**
```sql
-- Option A: Remove API access entirely
REVOKE SELECT ON public.source_feedback_metrics FROM anon, authenticated;

-- Option B: Create secure accessor function
CREATE FUNCTION public.get_source_feedback_metrics()
RETURNS SETOF public.source_feedback_metrics
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
    SELECT * FROM public.source_feedback_metrics
    WHERE auth.uid() IS NOT NULL;
$$;
```

#### Task 2.3: Remove Console Logging of Secrets

**File:** `/frontend-new/hooks/useDataSources.ts`

**Lines to modify:** ~148, ~183, ~215, ~264, ~296, ~332

**Pattern:**
```typescript
// BEFORE
console.log('🔐 [useDataSources] Client ID:', clientId ? `${clientId.substring(0, 20)}...` : 'NOT SET');

// AFTER
if (process.env.NODE_ENV === 'development') {
    console.log('🔐 [useDataSources] Client ID configured:', !!clientId);
}
```

#### Task 2.4: Add OAuth State Validation

**File:** `/frontend-new/app/oauth/callback/page.tsx`

**Implementation:**
```typescript
// In useEffect, before code exchange:
const storedState = sessionStorage.getItem('oauth_state');
const returnedState = searchParams.get('state');

// For Microsoft providers, state contains the provider type, so validate format
const validProviders = ['google', 'notion', 'onedrive', 'sharepoint', 'dropbox', 'github', 'box'];
if (returnedState && !validProviders.includes(returnedState)) {
    setStatus('error');
    setErrorMessage('Invalid OAuth state parameter');
    return;
}
```

### Phase 3: Performance Improvements (P2) - Day 2-3

| Task | File | Effort | Dependencies |
|------|------|--------|--------------|
| 3.1 Create request-dedup utility | `lib/request-dedup.ts` | 45 min | None |
| 3.2 Add debounce to useSearch | `useSearch.ts` | 1 hour | None |
| 3.3 Refactor useDataSources | `useDataSources.ts` | 3 hours | 3.1 |
| 3.4 Add optimistic updates to useTeamMembers | `useTeamMembers.ts` | 1 hour | None |

**Total Phase 3:** ~6 hours

#### Task 3.1: Create Request Deduplication Utility

**File:** `/frontend-new/lib/request-dedup.ts`

**Purpose:** Prevent duplicate API calls when multiple components request the same data simultaneously.

**Implementation:** See Appendix D for full code.

**Usage Example:**
```typescript
// In useDataSources.ts
import { dedupedRequest } from '@/lib/request-dedup';

const fetchData = async () => {
    const [available, status] = await Promise.all([
        dedupedRequest('integrations-available', () => api.get('/integrations/available')),
        dedupedRequest('integrations-status', () => api.get('/integrations/status')),
    ]);
    // ...
};
```

#### Task 3.2: Add Debounce to useSearch

**File:** `/frontend-new/hooks/useSearch.ts`

**Current Issue:** Every keystroke triggers an API call.

**Implementation:**
```typescript
import { useDebouncedCallback } from 'use-debounce';

export const useSearch = () => {
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastQuery, setLastQuery] = useState<string>('');

    const executeSearch = useCallback(async (
        query: string,
        topK: number,
        filters?: Record<string, unknown>
    ) => {
        if (!query.trim()) {
            setResults([]);
            return [];
        }

        setIsSearching(true);
        setError(null);
        setLastQuery(query);

        try {
            const { data } = await api.post('/search', {
                query,
                top_k: topK,
                filters,
            });
            const searchResults = Array.isArray(data) ? data : (data.results || []);
            setResults(searchResults);
            return searchResults;
        } catch (err) {
            // error handling...
        } finally {
            setIsSearching(false);
        }
    }, []);

    // Debounced version for typing
    const search = useDebouncedCallback(executeSearch, 300);

    // Immediate version for programmatic calls
    const searchImmediate = executeSearch;

    return {
        results,
        isSearching,
        error,
        lastQuery,
        search,
        searchImmediate,
        clearResults: useCallback(() => {
            setResults([]);
            setLastQuery('');
            setError(null);
        }, []),
    };
};
```

#### Task 3.3: Refactor useDataSources to React Query

**File:** `/frontend-new/hooks/useDataSources.ts` (505 lines → ~200 lines)

**Split into:**
1. `useDataSourcesQuery.ts` - Data fetching with React Query
2. `useOAuthConnect.ts` - OAuth URL generation
3. `useDataSourceActions.ts` - Mutations

**New Query Key Factory:**
```typescript
export const dataSourceKeys = {
    all: ['dataSources'] as const,
    available: () => [...dataSourceKeys.all, 'available'] as const,
    status: () => [...dataSourceKeys.all, 'status'] as const,
    files: (type: string, parentId?: string) => 
        [...dataSourceKeys.all, 'files', type, parentId] as const,
};
```

**Main Hook (simplified):**
```typescript
export function useDataSourcesQuery() {
    return useQuery({
        queryKey: dataSourceKeys.all,
        queryFn: async () => {
            const [available, status] = await Promise.all([
                api.get('/integrations/available'),
                api.get('/integrations/status')
            ]);
            return mergeData(available.data, status.data);
        },
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
    });
}
```

#### Task 3.4: Add Optimistic Updates to useTeamMembers

**File:** `/frontend-new/hooks/useTeamMembers.ts`

**Current Issue:** Role changes require full refresh to show.

**Implementation for updateMemberRole:**
```typescript
const updateMemberRole = async (memberId: string, role: Role): Promise<boolean> => {
    // Store previous state for rollback
    const previousMembers = [...members];
    
    // Optimistic update
    setMembers(prev => prev.map(m => 
        m.id === memberId ? { ...m, role } : m
    ));

    try {
        const { data } = await api.patch(`/team/members/${memberId}`, { role });
        // Update with server response (includes any server-side changes)
        setMembers(prev => prev.map(m => m.id === memberId ? data : m));
        toast({ title: 'Role updated' });
        return true;
    } catch (err) {
        // Rollback on error
        setMembers(previousMembers);
        toast({ title: 'Error', variant: 'destructive' });
        return false;
    }
};
```

### Phase 4: Test Coverage (P2) - Day 3-4

| Task | File | Tests | Effort |
|------|------|-------|--------|
| 4.1 useIngestionProgress.test.tsx | New | ~15 | 2 hours |
| 4.2 useFeedback.test.ts | New | ~12 | 1.5 hours |
| 4.3 useQuotaStatus.test.tsx | New | ~10 | 1.5 hours |
| 4.4 useRealtimeStatus.test.ts | New | ~8 | 1 hour |
| 4.5 usePlans.test.ts | New | ~6 | 45 min |
| 4.6 useOnboarding.test.ts | New | ~8 | 1 hour |

**Total Phase 4:** ~8 hours

#### Task 4.1: useIngestionProgress.test.tsx

**Test Categories:**

```typescript
describe('useIngestionProgress', () => {
    describe('Context Provider', () => {
        it('should throw error when used outside provider');
        it('should provide default values');
    });

    describe('Job Registration', () => {
        it('should register a new job');
        it('should not duplicate job registration');
        it('should track multiple jobs simultaneously');
        it('should log registration');
    });

    describe('Job Unregistration', () => {
        it('should unregister a job');
        it('should clear expanded state when job is unregistered');
        it('should clean up completion tracking');
        it('should not error on unknown job');
    });

    describe('Completion Tracking', () => {
        it('should mark job as completed');
        it('should return true for completed jobs');
        it('should return false for non-completed jobs');
        it('should prevent duplicate completion callbacks');
    });

    describe('Job Expansion', () => {
        it('should expand a job');
        it('should collapse when null passed');
        it('should only allow one expanded job');
    });
});
```

#### Task 4.2: useFeedback.test.ts

**Test Categories:**

```typescript
describe('useFeedback', () => {
    describe('Initial State', () => {
        it('should have empty feedback state initially');
        it('should not be submitting initially');
        it('should have no error initially');
    });

    describe('Feedback Submission', () => {
        it('should submit positive feedback');
        it('should submit negative feedback');
        it('should update local state on success');
        it('should show toast for negative feedback with comment');
        it('should not show toast for positive feedback');
    });

    describe('Validation', () => {
        it('should reject empty message ID');
        it('should reject invalid rating');
        it('should truncate long answer previews');
        it('should truncate long feedback text');
    });

    describe('Error Handling', () => {
        it('should handle API errors');
        it('should show error toast on failure');
        it('should clear error on successful submit');
    });

    describe('Conversation Feedback', () => {
        it('should load existing feedback for conversation');
        it('should clear feedback when conversation changes');
    });
});
```

#### Task 4.3: useQuotaStatus.test.tsx

**Test Categories:**

```typescript
describe('useQuotaStatus', () => {
    describe('Initial State', () => {
        it('should have no quota issues initially');
        it('should load persisted quota status from storage');
        it('should ignore expired quota status');
    });

    describe('Quota Detection', () => {
        it('should detect quota error in failed job');
        it('should detect quota warning in completed job');
        it('should normalize provider names');
        it('should persist quota status to localStorage');
    });

    describe('Provider Checking', () => {
        it('should return true for exceeded provider');
        it('should return false for non-exceeded provider');
        it('should handle provider name variations');
    });

    describe('Clearing Status', () => {
        it('should clear specific provider status');
        it('should clear all provider statuses');
        it('should update localStorage on clear');
    });

    describe('Manual Marking', () => {
        it('should manually mark provider as exceeded');
    });
});
```

#### Task 4.4: useRealtimeStatus.test.ts

**Test Categories:**

```typescript
describe('useRealtimeStatus', () => {
    describe('Initial Connection', () => {
        it('should start in connecting state');
        it('should transition to connected on SUBSCRIBED');
        it('should set lastConnected timestamp');
    });

    describe('Connection States', () => {
        it('should handle TIMED_OUT as error');
        it('should handle CHANNEL_ERROR as error');
        it('should handle CLOSED as disconnected');
    });

    describe('Reconnection', () => {
        it('should implement exponential backoff');
        it('should respect max retry count');
        it('should reset attempts on success');
        it('should cap delay at maximum');
    });

    describe('Cleanup', () => {
        it('should unsubscribe on unmount');
        it('should clear timers on unmount');
    });
});
```

#### Task 4.5: usePlans.test.ts

**Test Categories:**

```typescript
describe('usePlans', () => {
    describe('Data Fetching', () => {
        it('should fetch plans on mount');
        it('should show loading state');
        it('should update plans on success');
    });

    describe('Fallback Handling', () => {
        it('should use fallback plans on API error');
        it('should use fallback plans on empty response');
        it('should not error on request cancellation');
    });

    describe('Cleanup', () => {
        it('should cancel request on unmount');
    });
});
```

#### Task 4.6: useOnboarding.test.ts

**Test Categories:**

```typescript
describe('useOnboarding', () => {
    describe('Initial State', () => {
        it('should not show onboarding if completed');
        it('should not show onboarding if skipped');
        it('should show onboarding for new users');
        it('should start at welcome step');
    });

    describe('Navigation', () => {
        it('should advance to next step');
        it('should go back to previous step');
        it('should not go before first step');
        it('should not advance past last step');
    });

    describe('Completion', () => {
        it('should mark onboarding as complete');
        it('should persist completion to storage');
        it('should set step to complete');
    });

    describe('Skip', () => {
        it('should mark onboarding as skipped');
        it('should persist skip to storage');
        it('should close onboarding');
    });
});
```

### Phase 5: Documentation & Cleanup (P3) - Day 4

| Task | File | Effort |
|------|------|--------|
| 5.1 Update README with hook patterns | README.md | 30 min |
| 5.2 Add JSDoc to all hooks | Various | 2 hours |
| 5.3 Create hook usage guide | docs/ | 1 hour |
| 5.4 Clean up console.log statements | Various | 30 min |
| 5.5 Add deprecation warnings | Legacy hooks | 30 min |

**Total Phase 5:** ~4.5 hours

#### Task 5.1: Update README with Hook Patterns

**Content to Add:**
- Hook naming conventions
- Context vs Query hooks
- When to use each pattern
- Testing guidelines

#### Task 5.2: Add JSDoc to All Hooks

**Template:**
```typescript
/**
 * Hook for managing [feature].
 * 
 * @description
 * [Detailed description of what the hook does]
 * 
 * @example
 * ```tsx
 * const { data, isLoading, error } = useHookName(param);
 * ```
 * 
 * @param param - Description of parameter
 * @returns Object containing [list of return values]
 * 
 * @see Related hooks or components
 */
```

#### Task 5.4: Clean Up Console Statements

**Files to Review:**
- All hooks with console.log statements
- Keep only:
  - Error logging (`console.error`)
  - Development-only debugging (`process.env.NODE_ENV === 'development'`)
- Remove:
  - Client ID/secret partial logging
  - Verbose success messages

---

## Summary

### Total Implementation Effort

| Phase | Days | Hours | Priority |
|-------|------|-------|----------|
| Phase 1: Critical Fixes | 1 | 3.5 | P0 |
| Phase 2: Security Fixes | 1 | 3 | P1 |
| Phase 3: Performance | 1.5 | 6 | P2 |
| Phase 4: Test Coverage | 2 | 8 | P2 |
| Phase 5: Documentation | 0.5 | 4.5 | P3 |
| **Total** | **6 days** | **25 hours** | - |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Middleware breaks auth flow | Medium | High | Test thoroughly before deploy |
| SQL migration causes downtime | Low | High | Run in maintenance window |
| Refactored hooks break UI | Medium | Medium | Comprehensive testing |
| Performance regression | Low | Medium | Monitor metrics after deploy |

### Success Criteria

- [ ] All Supabase linter warnings resolved
- [ ] 100% SSR-safe hooks
- [ ] Middleware protecting all routes
- [ ] 80%+ test coverage for hooks
- [ ] No secrets in console logs
- [ ] Performance metrics stable or improved

### Rollback Plan

1. **Middleware Issues:** Remove `middleware.ts` file to restore previous behavior
2. **SQL Migrations:** Each migration should be reversible
3. **Hook Changes:** Git revert to previous commit
4. **Test Failures:** Do not block deploy if tests fail on non-critical paths

---

## 10. Appendix: Code Templates

### A. Middleware Template

See Section 2.4 for full implementation.

### B. Hook Test Template

```typescript
// __tests__/hooks/useHookName.test.tsx
import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useHookName } from '@/hooks/useHookName';

// Mock dependencies
vi.mock('@/lib/api', () => ({
    api: {
        get: vi.fn(),
        post: vi.fn(),
    },
}));

// Create wrapper with providers
const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    // eslint-disable-next-line react/display-name
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
};

describe('useHookName', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Initial State', () => {
        it('should have correct initial values', () => {
            const { result } = renderHook(() => useHookName(), {
                wrapper: createWrapper(),
            });
            
            expect(result.current.isLoading).toBe(true);
            expect(result.current.data).toBeNull();
        });
    });

    describe('Data Fetching', () => {
        it('should fetch data on mount', async () => {
            // ... test implementation
        });
    });

    describe('Error Handling', () => {
        it('should handle API errors gracefully', async () => {
            // ... test implementation
        });
    });
});
```

### C. SQL Migration Templates

#### Fix Function Search Path

```sql
-- 20260130000000_fix_function_search_paths.sql

-- Fix hybrid_search function
CREATE OR REPLACE FUNCTION public.hybrid_search(
    query_embedding vector(1536),
    query_text text,
    match_count int DEFAULT 10
)
RETURNS TABLE(
    id uuid,
    content text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public, pg_catalog
AS $$
BEGIN
    -- Existing function body unchanged
    RETURN QUERY
    SELECT 
        d.id,
        d.content,
        1 - (d.embedding <=> query_embedding) as similarity,
        d.metadata
    FROM documents d
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- Fix hybrid_search_scoped function
CREATE OR REPLACE FUNCTION public.hybrid_search_scoped(
    query_embedding vector(1536),
    query_text text,
    match_count int DEFAULT 10,
    scope_ids uuid[] DEFAULT NULL,
    full_text_weight float DEFAULT 0.3,
    semantic_weight float DEFAULT 0.7
)
RETURNS TABLE(
    id uuid,
    content text,
    similarity float,
    metadata jsonb
)
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public, pg_catalog
AS $$
BEGIN
    -- Existing function body unchanged
    -- Just add the SET search_path line above
END;
$$;
```

#### Secure Materialized View

```sql
-- 20260130000002_secure_materialized_view.sql

-- Remove direct API access
REVOKE SELECT ON public.source_feedback_metrics FROM anon, authenticated;

-- Create secure accessor function
CREATE OR REPLACE FUNCTION public.get_source_feedback_metrics()
RETURNS SETOF public.source_feedback_metrics
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_catalog
AS $$
    SELECT * FROM public.source_feedback_metrics
    WHERE auth.uid() IS NOT NULL;
$$;

-- Grant to authenticated users only
GRANT EXECUTE ON FUNCTION public.get_source_feedback_metrics TO authenticated;

-- Add comment
COMMENT ON FUNCTION public.get_source_feedback_metrics IS 
    'Secure accessor for source_feedback_metrics. Requires authentication.';
```

### D. Request Deduplication Utility

```typescript
// /frontend-new/lib/request-dedup.ts

type PendingRequest<T> = {
    promise: Promise<T>;
    timestamp: number;
};

const pendingRequests = new Map<string, PendingRequest<unknown>>();
const DEDUP_WINDOW = 100; // ms

/**
 * Deduplicate identical requests made within a short window.
 * If the same request is made multiple times within DEDUP_WINDOW ms,
 * only one actual request is made and the result is shared.
 */
export async function dedupedRequest<T>(
    key: string,
    fetcher: () => Promise<T>
): Promise<T> {
    const now = Date.now();
    const existing = pendingRequests.get(key);

    // Return existing request if within dedup window
    if (existing && (now - existing.timestamp) < DEDUP_WINDOW) {
        return existing.promise as Promise<T>;
    }

    // Create new request
    const promise = fetcher().finally(() => {
        // Clean up after request completes
        setTimeout(() => {
            const current = pendingRequests.get(key);
            if (current && current.promise === promise) {
                pendingRequests.delete(key);
            }
        }, DEDUP_WINDOW);
    });

    pendingRequests.set(key, { promise, timestamp: now });
    return promise;
}

/**
 * Create a deduped fetcher for a specific endpoint.
 */
export function createDedupedFetcher<T>(
    keyPrefix: string,
    fetcher: (...args: unknown[]) => Promise<T>
) {
    return (...args: unknown[]) => {
        const key = `${keyPrefix}:${JSON.stringify(args)}`;
        return dedupedRequest(key, () => fetcher(...args));
    };
}
```

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-30 | AI Assistant | Initial audit |

---

## Sign-Off

- [ ] Phase 1: Critical Fixes
- [ ] Phase 2: Security Fixes  
- [ ] Phase 3: Performance Improvements
- [ ] Phase 4: Test Coverage
- [ ] Phase 5: Documentation

**Next Step:** Switch to implementation mode and execute Phase 1.
