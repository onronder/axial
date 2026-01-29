# Settings Page Complete Implementation Plan

## Document Information
- **Created:** January 29, 2026
- **Completed:** January 29, 2026
- **Author:** AI Assistant
- **Scope:** All 8 Settings Tabs - Bug Fixes, Code Quality, and Test Coverage
- **Target:** Production-Grade Implementation with 100% Test Coverage
- **Status:** ✅ COMPLETED

---

## Executive Summary

This plan addresses **23 issues** across 8 settings tabs:
- **8 Critical Bugs** requiring immediate fixes
- **9 Code Quality Improvements** for maintainability  
- **6 Missing Test Suites** requiring full implementation

### Settings Tabs Overview

| Tab | Route | Component | Current Grade | Target Grade |
|-----|-------|-----------|---------------|--------------|
| 1. General | `/dashboard/settings/general` | `GeneralSettings.tsx` | A+ | A+ |
| 2. Data Sources | `/dashboard/settings/data-sources` | `DataSourcesGrid.tsx` | A | A+ |
| 3. Knowledge Base | `/dashboard/settings/knowledge-base` | `KnowledgeBaseBrowser.tsx` | A+ | A+ |
| 4. Team | `/dashboard/settings/team` | `TeamSettings.tsx` | B | A |
| 5. Analytics | `/dashboard/settings/analytics` | `FeedbackAnalyticsPage` | C+ | A |
| 6. Notifications | `/dashboard/settings/notifications` | `NotificationSettings.tsx` | A | A+ |
| 7. Billing | `/dashboard/settings/billing` | `BillingSettings.tsx` | A+ | A+ |
| 8. Failed Tasks | `/dashboard/settings/failed-tasks` | `DLQDashboard.tsx` | B- | A |

---

## Phase 1: Critical Bug Fixes (P0)

### 1.1 Analytics Page - Missing Authorization Check

**File:** `frontend-new/app/dashboard/settings/analytics/page.tsx`

**Problem:** Component renders for any user, relies only on nav-level `adminOnly` flag which only hides the nav item but doesn't prevent direct URL access.

**Solution:** Add runtime authorization check at component level.

**Implementation:**
```typescript
// Add imports
import { useProfile } from '@/hooks/useProfile';
import { ShieldAlert } from 'lucide-react';

// Add at start of component
const { profile, isLoading: profileLoading } = useProfile();

// Add authorization check before main return
if (profileLoading) {
    return (
        <div className="flex items-center justify-center min-h-[400px]">
            <Spinner className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
    );
}

const isAdmin = profile?.role === 'admin' || !profile?.role; // Owner has no role field
if (profile?.role === 'viewer' || profile?.role === 'editor') {
    return (
        <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
                <ShieldAlert className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
                <p className="text-muted-foreground">
                    Analytics are only available to team admins.
                </p>
            </div>
        </div>
    );
}
```

**Acceptance Criteria:**
- [ ] Non-admin users see access denied message
- [ ] Loading state shown while checking permissions
- [ ] Admin users see analytics normally
- [ ] Direct URL access is protected

---

### 1.2 Analytics Page - Load More Button Non-Functional

**File:** `frontend-new/app/dashboard/settings/analytics/page.tsx`

**Problem:** "Load More" button exists but has no onClick handler.

**Solution:** Add pagination state and handler.

**Implementation:**
```typescript
// Add state
const [feedbackLimit, setFeedbackLimit] = useState(20);

// Update fetchFeedback call
async function fetchFeedback(rating?: string, limit: number = 20): Promise<FeedbackResponse> {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (rating) params.set('rating', rating);
    const response = await api.get(`/analytics/feedback?${params.toString()}`);
    return response.data;
}

// Update useQuery
const { data: feedbackData, ... } = useQuery({
    queryKey: ['feedback', ratingFilter, feedbackLimit],
    queryFn: () => fetchFeedback(ratingFilter === 'all' ? undefined : ratingFilter, feedbackLimit),
    staleTime: 60_000,
});

// Fix button
{feedbackData?.has_more && (
    <div className="text-center pt-4">
        <Button 
            variant="outline" 
            size="sm"
            onClick={() => setFeedbackLimit(prev => prev + 20)}
            disabled={feedbackLoading}
        >
            {feedbackLoading && <Spinner className="h-4 w-4 mr-2 animate-spin" />}
            Load More
        </Button>
    </div>
)}
```

**Acceptance Criteria:**
- [ ] Clicking "Load More" fetches additional items
- [ ] Loading state shown during fetch
- [ ] Button hidden when no more items
- [ ] Limit resets when filter changes

---

### 1.3 Team Settings - Last Admin Protection Incomplete

**File:** `frontend-new/components/settings/TeamSettings.tsx`

**Problem:** User can demote themselves even if they're the last admin.

**Solution:** Add self-check to last admin protection.

**Implementation:**
```typescript
// Add helper functions after existing code around line 115
const isLastAdmin = (memberId: string): boolean => {
    const activeAdmins = members.filter(m => m.role === 'admin' && m.status === 'active');
    return activeAdmins.length === 1 && activeAdmins[0].id === memberId;
};

const isSelf = (memberId: string): boolean => {
    // profile.id from useProfile is the user's profile id
    // member.id from useTeamMembers is the team_member id
    // Need to compare by user_id or check if email matches
    return member.email === profile?.email;
};

// Update the disabled check on role Select (around line 637)
disabled={
    !canManageMembers ||
    isLastAdmin(member.id) // Prevent demoting last admin regardless of who
}

// Add tooltip explaining why disabled
{isLastAdmin(member.id) && (
    <TooltipProvider>
        <Tooltip>
            <TooltipTrigger asChild>
                <span className="cursor-help">🔒</span>
            </TooltipTrigger>
            <TooltipContent>
                Cannot change role of the last admin
            </TooltipContent>
        </Tooltip>
    </TooltipProvider>
)}
```

**Acceptance Criteria:**
- [ ] Last admin's role dropdown is disabled
- [ ] Tooltip explains why
- [ ] Other members can still be modified
- [ ] Multiple admins can be modified

---

### 1.4 DLQ Dashboard - Visibility-Aware Polling

**File:** `frontend-new/components/admin/DLQDashboard.tsx`

**Problem:** Polls every 30s even when tab is hidden, wasting bandwidth.

**Solution:** Use Page Visibility API to pause/resume polling.

**Implementation:**
```typescript
// Replace the existing useEffect for polling (around line 191-196)
useEffect(() => {
    fetchData();
    
    let interval: NodeJS.Timeout | null = null;
    
    const startPolling = () => {
        if (!interval) {
            interval = setInterval(fetchData, 30000);
        }
    };
    
    const stopPolling = () => {
        if (interval) {
            clearInterval(interval);
            interval = null;
        }
    };
    
    const handleVisibilityChange = () => {
        if (document.visibilityState === 'visible') {
            fetchData(); // Immediate refresh when tab becomes visible
            startPolling();
        } else {
            stopPolling();
        }
    };
    
    // Start polling initially
    startPolling();
    
    // Listen for visibility changes
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        stopPolling();
    };
}, [fetchData]);
```

**Acceptance Criteria:**
- [ ] Polling stops when tab hidden
- [ ] Polling resumes when tab visible
- [ ] Immediate refresh on visibility change
- [ ] Proper cleanup on unmount

---

### 1.5 General Settings - Missing Form Validation

**File:** `frontend-new/components/settings/GeneralSettings.tsx`

**Problem:** Profile can be saved with empty names, no error feedback.

**Solution:** Add validation with error display.

**Implementation:**
```typescript
// Add error state after existing state declarations (around line 38)
const [errors, setErrors] = useState<{ firstName?: string; lastName?: string }>({});

// Add validation function
const validateForm = (): boolean => {
    const newErrors: typeof errors = {};
    
    if (!firstName.trim()) {
        newErrors.firstName = 'First name is required';
    } else if (firstName.trim().length < 2) {
        newErrors.firstName = 'First name must be at least 2 characters';
    }
    
    if (!lastName.trim()) {
        newErrors.lastName = 'Last name is required';
    } else if (lastName.trim().length < 2) {
        newErrors.lastName = 'Last name must be at least 2 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
};

// Update handleSaveProfile (around line 49)
const handleSaveProfile = async () => {
    if (!validateForm()) return;
    
    setIsSaving(true);
    try {
        await updateProfile({
            first_name: firstName.trim(),
            last_name: lastName.trim(),
        });
    } finally {
        setIsSaving(false);
    }
};

// Update Input components to show errors
<div className="space-y-2">
    <Label htmlFor="firstName" className="text-sm font-medium">First Name</Label>
    <Input
        id="firstName"
        value={firstName}
        onChange={(e) => {
            setFirstName(e.target.value);
            if (errors.firstName) setErrors(prev => ({ ...prev, firstName: undefined }));
        }}
        placeholder="John"
        className={cn(
            "transition-all focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            errors.firstName && "border-destructive focus-visible:ring-destructive"
        )}
    />
    {errors.firstName && (
        <p className="text-xs text-destructive">{errors.firstName}</p>
    )}
</div>
```

**Acceptance Criteria:**
- [ ] Empty names show validation error
- [ ] Names under 2 chars show error
- [ ] Error clears on input change
- [ ] Save blocked until valid
- [ ] Visual indication of error fields

---

### 1.6 Team Settings - Email Validation Enhancement

**File:** `frontend-new/components/settings/TeamSettings.tsx`

**Problem:** Basic regex allows invalid emails like "a@b.c".

**Solution:** Enhanced validation with real-time feedback.

**Implementation:**
```typescript
// Replace EMAIL_REGEX (around line 86)
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// Add error state
const [emailError, setEmailError] = useState<string | null>(null);

// Add validation function
const validateEmail = (email: string): string | null => {
    if (!email.trim()) return null; // Don't show error for empty
    if (!EMAIL_REGEX.test(email.trim())) {
        return 'Please enter a valid email address';
    }
    return null;
};

// Update email input handler
const handleEmailChange = (value: string) => {
    setInviteEmail(value);
    setEmailError(validateEmail(value));
};

// Update Input in dialog
<Input
    id="invite-email"
    type="email"
    placeholder="colleague@company.com"
    value={inviteEmail}
    onChange={(e) => handleEmailChange(e.target.value)}
    className={cn(emailError && "border-destructive")}
/>
{emailError && (
    <p className="text-xs text-destructive mt-1">{emailError}</p>
)}

// Update submit button disabled state
disabled={isInviting || !inviteEmail.trim() || !!emailError || !canManageMembers}
```

**Acceptance Criteria:**
- [ ] "a@b.c" shows validation error
- [ ] "user@domain.com" passes
- [ ] Error message displayed inline
- [ ] Submit button disabled for invalid email

---

### 1.7 Billing Settings - Invoice Fetch Error Display

**File:** `frontend-new/components/settings/BillingSettings.tsx`

**Problem:** Invoice fetch errors are logged but not shown to user.

**Solution:** Add error state and retry UI.

**Implementation:**
```typescript
// Add error state (around line 147)
const [invoiceError, setInvoiceError] = useState<string | null>(null);

// Update fetchInvoices (around line 164)
const fetchInvoices = useCallback(async () => {
    try {
        setIsLoadingInvoices(true);
        setInvoiceError(null);
        const response = await api.get("/billing/invoices");
        setInvoices(response.data || []);
    } catch (error) {
        console.error("[Billing] Failed to fetch invoices:", error);
        setInvoiceError("Failed to load billing history");
    } finally {
        setIsLoadingInvoices(false);
    }
}, []);

// Update Billing History CardContent to show error
<CardContent>
    {isLoadingInvoices ? (
        <div className="flex items-center justify-center py-8">
            <Spinner className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
    ) : invoiceError ? (
        <div className="text-center py-8">
            <AlertTriangle className="h-8 w-8 mx-auto text-destructive mb-2" />
            <p className="text-sm text-destructive mb-4">{invoiceError}</p>
            <Button variant="outline" size="sm" onClick={fetchInvoices}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Retry
            </Button>
        </div>
    ) : invoices.length === 0 ? (
        // existing empty state
    ) : (
        // existing invoice list
    )}
</CardContent>
```

**Acceptance Criteria:**
- [ ] Error message shown on invoice fetch failure
- [ ] Retry button available
- [ ] Loading state shows during retry
- [ ] Success clears error state

---

### 1.8 Notification Settings - Reset Confirmation Timeout

**File:** `frontend-new/components/settings/NotificationSettings.tsx`

**Problem:** "Click again to confirm" stays forever if user doesn't complete action.

**Solution:** Auto-clear confirmation after 5 seconds.

**Implementation:**
```typescript
// Add ref for timeout (after useState declarations, around line 15)
const confirmTimeoutRef = useRef<NodeJS.Timeout | null>(null);

// Update reset button onClick handler (around line 74)
onClick={async () => {
    if (!confirming) {
        setConfirming(true);
        // Auto-cancel after 5 seconds
        confirmTimeoutRef.current = setTimeout(() => {
            setConfirming(false);
        }, 5000);
        return;
    }
    
    // Clear timeout on actual reset
    if (confirmTimeoutRef.current) {
        clearTimeout(confirmTimeoutRef.current);
        confirmTimeoutRef.current = null;
    }
    
    const ok = await resetToDefaults();
    if (ok) {
        setConfirming(false);
    }
}}

// Add cleanup effect
useEffect(() => {
    return () => {
        if (confirmTimeoutRef.current) {
            clearTimeout(confirmTimeoutRef.current);
        }
    };
}, []);

// Add useRef import at top
import { useState, useEffect, useRef } from "react";
```

**Acceptance Criteria:**
- [ ] Confirmation state auto-clears after 5 seconds
- [ ] Immediate clear on successful reset
- [ ] Cleanup on unmount prevents memory leaks
- [ ] Cancel button still works immediately

---

## Phase 2: Code Quality Improvements (P1)

### 2.1 Create useAnalytics Hook

**File:** `frontend-new/hooks/useAnalytics.ts` (new file)

Extract API functions from analytics page into dedicated hook for better testability and reusability.

**Implementation:** Create new hook file with:
- Type definitions
- Query key factory
- useFeedback hook
- useSourceMetrics hook

### 2.2 Data Sources - Create Source Adapter Utility

**File:** `frontend-new/lib/data-source-utils.ts` (new file)

Create utility function to convert MergedDataSource to card props consistently.

### 2.3 DLQ Dashboard - Add Pagination Support

**File:** `frontend-new/components/admin/DLQDashboard.tsx`

Add page/limit parameters to API calls and pagination UI.

---

## Phase 3: Missing Test Suites (P1)

### 3.1 TeamSettings.test.tsx - Full Rewrite

**File:** `frontend-new/__tests__/components/TeamSettings.test.tsx`

**Current State:** Only data structure tests (134 lines)
**Target:** Full component tests (400+ lines)

**Test Categories:**
1. Rendering (5 tests)
2. Invite Flow (6 tests)
3. Bulk Import (4 tests)
4. Role Management (4 tests)
5. Member Actions (3 tests)
6. Search and Filter (5 tests)
7. Pagination (3 tests)
8. Permissions (3 tests)

### 3.2 FeedbackAnalytics.test.tsx - New File

**File:** `frontend-new/__tests__/pages/FeedbackAnalytics.test.tsx`

**Test Categories:**
1. Authorization (3 tests)
2. Summary Cards (6 tests)
3. Problem Sources (4 tests)
4. Recent Feedback (5 tests)
5. Refresh (1 test)
6. Error Handling (2 tests)

### 3.3 DLQDashboard.test.tsx - New File

**File:** `frontend-new/__tests__/components/DLQDashboard.test.tsx`

**Test Categories:**
1. Rendering (6 tests)
2. Stats Cards (4 tests)
3. Task Table (4 tests)
4. Retry Operations (4 tests)
5. Resolve Operations (2 tests)
6. Selection (4 tests)
7. Filtering (2 tests)
8. Polling (3 tests)
9. Permissions (3 tests)

### 3.4 useAnalytics.test.tsx - New File

**File:** `frontend-new/__tests__/hooks/useAnalytics.test.tsx`

Tests for the new useAnalytics hook.

### 3.5 Enhance Existing Tests

Update existing test files to cover new validation logic:
- GeneralSettings.test.tsx - Add form validation tests
- NotificationSettings.test.tsx - Add reset timeout tests
- BillingSettings.test.tsx - Add invoice error state tests

---

## Implementation Order

| Step | Task | Est. Time | Dependencies |
|------|------|-----------|--------------|
| 1 | Fix Analytics auth check | 15min | None |
| 2 | Fix Analytics load more | 15min | None |
| 3 | Fix Team last admin | 20min | None |
| 4 | Fix DLQ visibility polling | 20min | None |
| 5 | Fix General form validation | 25min | None |
| 6 | Fix Team email validation | 15min | None |
| 7 | Fix Billing invoice errors | 15min | None |
| 8 | Fix Notification reset timeout | 15min | None |
| 9 | Create useAnalytics hook | 30min | Steps 1-2 |
| 10 | Rewrite TeamSettings tests | 60min | Steps 3, 6 |
| 11 | Create Analytics tests | 45min | Step 9 |
| 12 | Create DLQ tests | 50min | Step 4 |
| 13 | Enhance existing tests | 30min | Steps 5, 7, 8 |
| 14 | Run full test suite | 10min | All |
| 15 | Fix any failures | Variable | Step 14 |

**Total Estimated Time: ~6 hours**

---

## Verification Checklist

After implementation:

- [ ] All 1347+ existing tests pass
- [ ] New tests pass
- [ ] No console errors
- [ ] No TypeScript errors
- [ ] ESLint passes with 0 warnings
- [ ] All user flows work:
  - [ ] Profile validation works
  - [ ] Theme changes persist
  - [ ] Account deletion works
  - [ ] Team invite validates emails
  - [ ] Last admin protected
  - [ ] Analytics auth check works
  - [ ] Analytics load more works
  - [ ] Notifications reset timeout works
  - [ ] Billing invoice error shown
  - [ ] DLQ polling is visibility-aware

---

## Files Modified/Created Summary

### Modified Files:
1. `frontend-new/app/dashboard/settings/analytics/page.tsx`
2. `frontend-new/components/settings/TeamSettings.tsx`
3. `frontend-new/components/admin/DLQDashboard.tsx`
4. `frontend-new/components/settings/GeneralSettings.tsx`
5. `frontend-new/components/settings/BillingSettings.tsx`
6. `frontend-new/components/settings/NotificationSettings.tsx`

### New Files:
1. `frontend-new/hooks/useAnalytics.ts`
2. `frontend-new/__tests__/hooks/useAnalytics.test.tsx`
3. `frontend-new/__tests__/pages/FeedbackAnalytics.test.tsx`
4. `frontend-new/__tests__/components/DLQDashboard.test.tsx`

### Rewritten Files:
1. `frontend-new/__tests__/components/TeamSettings.test.tsx`

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run tests after each change |
| Regression | Test each feature manually |
| API contract changes | Verify backend endpoints first |

---

*End of Implementation Plan*
