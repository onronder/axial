# Axio Hub Hooks Usage Guide

This guide provides detailed documentation for all custom React hooks in the Axio Hub frontend.

## Table of Contents

1. [Authentication Hooks](#authentication-hooks)
2. [Data Management Hooks](#data-management-hooks)
3. [Data Source Hooks](#data-source-hooks)
4. [Settings & Billing Hooks](#settings--billing-hooks)
5. [Utility Hooks](#utility-hooks)
6. [Best Practices](#best-practices)

---

## Authentication Hooks

### `useAuth`

Central authentication hook managing user sessions, login, registration, and OAuth.

```typescript
import { useAuth } from '@/hooks/useAuth';

function MyComponent() {
    const { 
        user,           // Current user object
        isLoading,      // Auth state loading
        isAuthenticated, // Boolean auth status
        signIn,         // Email/password login
        signUp,         // New user registration
        signInWithOAuth, // OAuth providers (Google, etc.)
        resetPassword,  // Send password reset email
        updatePassword, // Change password
        signOut,        // Logout
    } = useAuth();

    // Login with email/password
    const handleLogin = async () => {
        await signIn('user@example.com', 'password');
    };

    // Login with Google
    const handleGoogleLogin = async () => {
        await signInWithOAuth('google', {
            redirectTo: '/dashboard',
        });
    };
}
```

**Features:**
- Token caching with automatic refresh
- OAuth support (Google, Microsoft)
- Rate limit error handling
- Session persistence

---

### `useProfile`

User profile data and updates. Must be used within `ProfileProvider`.

```typescript
import { useProfile } from '@/hooks/useProfile';

function ProfileSettings() {
    const { 
        profile,     // User profile data
        isLoading,   // Loading state
        updateProfile, // Update profile fields
        refreshProfile, // Force refresh
    } = useProfile();

    const handleSave = async () => {
        await updateProfile({
            first_name: 'John',
            last_name: 'Doe',
        });
    };
}
```

---

### `useOnboarding`

Manages the onboarding flow for new users.

```typescript
import { useOnboarding } from '@/hooks/useOnboarding';

function OnboardingModal() {
    const {
        showOnboarding, // Whether to show onboarding
        currentStep,    // 'welcome' | 'connect' | 'upload' | 'complete'
        isComplete,     // Onboarding finished
        nextStep,       // Go to next step
        prevStep,       // Go to previous step
        completeOnboarding, // Mark as complete
        skipOnboarding,  // Skip (persisted)
        closeOnboarding, // Close without persisting
    } = useOnboarding();

    if (!showOnboarding) return null;

    return (
        <div>
            <p>Current step: {currentStep}</p>
            <button onClick={nextStep}>Next</button>
            <button onClick={skipOnboarding}>Skip</button>
        </div>
    );
}
```

**Notes:**
- Automatically shows for new users after 1 second delay
- Persists completion/skip status to localStorage
- SSR-safe

---

## Data Management Hooks

### `useDocuments`

Document CRUD operations with React Query.

```typescript
import { useDocuments } from '@/hooks/useDocuments';

function DocumentList() {
    const {
        documents,      // Document list
        isLoading,      // Loading state
        error,          // Error state
        deleteDocument, // Delete by ID
        refreshDocuments, // Force refresh
    } = useDocuments();

    const handleDelete = async (id: string) => {
        await deleteDocument(id);
        // Optimistic update happens automatically
    };
}
```

**Query Keys:**
```typescript
documentKeys.all        // ['documents']
documentKeys.lists()    // ['documents', 'list']
documentKeys.detail(id) // ['documents', 'detail', id]
```

---

### `useChatHistory`

Chat conversations and message history with React Query.

```typescript
import { useChatHistory } from '@/hooks/useChatHistory';

function ChatSidebar() {
    const {
        conversations,      // List of conversations
        currentConversation, // Active conversation
        isLoading,
        createConversation, // Start new chat
        selectConversation, // Switch conversation
        deleteConversation, // Remove conversation
    } = useChatHistory();
}
```

**Query Keys:**
```typescript
chatKeys.all           // ['chat']
chatKeys.lists()       // ['chat', 'list']
chatKeys.messages()    // ['chat', 'messages']
chatKeys.message(id)   // ['chat', 'messages', id]
```

---

### `useSearch`

Vector search with automatic debouncing.

```typescript
import { useSearch } from '@/hooks/useSearch';

function SearchBar() {
    const {
        results,     // Search results
        isSearching, // Loading state
        error,       // Error state
        lastQuery,   // Last search query
        search,      // Debounced search (300ms)
        clearResults, // Clear results
    } = useSearch();

    const handleInput = (query: string) => {
        search(query, 10); // topK = 10
    };

    return (
        <input 
            onChange={(e) => handleInput(e.target.value)}
            placeholder="Search..."
        />
    );
}
```

**Notes:**
- 300ms debounce built-in
- Automatically clears results for empty queries

---

### `useFeedback`

Submit user feedback on chat responses.

```typescript
import { useFeedback } from '@/hooks/useFeedback';

function ChatMessage({ messageId, answer }) {
    const {
        feedbackState,  // Map of messageId -> feedback
        isSubmitting,   // Submission in progress
        error,          // Error state
        submitFeedback, // Submit new feedback
        getFeedback,    // Get feedback for message
    } = useFeedback(conversationId);

    const handleThumbsUp = async () => {
        await submitFeedback({
            message_id: messageId,
            rating: 'positive',
            answer_preview: answer.slice(0, 200),
        });
    };

    const handleThumbsDown = async (comment: string) => {
        await submitFeedback({
            message_id: messageId,
            rating: 'negative',
            feedback_text: comment,
            answer_preview: answer.slice(0, 200),
        });
    };
}
```

---

## Data Source Hooks

### `useDataSources`

Manage connected data sources (Google Drive, Notion, etc.).

```typescript
import { useDataSources } from '@/hooks/useDataSources';

function DataSourcesPage() {
    const {
        dataSources,    // Available sources
        status,         // Connection status per source
        isLoading,
        connect,        // Start OAuth connection
        disconnect,     // Remove connection
        sync,           // Trigger sync
        refresh,        // Refresh data
    } = useDataSources();

    const handleConnect = async (provider: string) => {
        await connect(provider); // Redirects to OAuth
    };
}
```

---

### `useIngestionJobs`

Track ingestion job status in real-time.

```typescript
import { useIngestionJobs } from '@/hooks/useIngestionJobs';

function IngestionStatus() {
    const {
        jobs,         // Active ingestion jobs
        isLoading,
        hasActiveJobs, // Boolean for any active jobs
    } = useIngestionJobs();

    return (
        <div>
            {jobs.map(job => (
                <div key={job.id}>
                    {job.document_title}: {job.status} ({job.progress}%)
                </div>
            ))}
        </div>
    );
}
```

**Notes:**
- Uses Supabase Realtime for live updates
- Throttled to prevent render storms (100ms)

---

### `useIngestionProgress`

Context for tracking ingestion progress across components.

```typescript
import { useIngestionProgress, IngestionProgressProvider } from '@/hooks/useIngestionProgress';

// In your app layout
function App() {
    return (
        <IngestionProgressProvider>
            <Dashboard />
        </IngestionProgressProvider>
    );
}

// In components
function UploadButton() {
    const {
        activeJobIds,     // Set of active job IDs
        registerJob,      // Register new job
        unregisterJob,    // Remove job tracking
        markJobCompleted, // Mark as done (prevents duplicate callbacks)
        hasJobCompleted,  // Check if job completed
        expandJob,        // Expand job details
        expandedJobId,    // Currently expanded job
    } = useIngestionProgress();

    const handleUpload = (jobId: string) => {
        registerJob(jobId);
    };
}
```

---

### `useQuotaStatus`

Track which data sources have hit quota limits.

```typescript
import { useQuotaStatus, QuotaStatusProvider } from '@/hooks/useQuotaStatus';

// Wrap app with provider
function App() {
    return (
        <QuotaStatusProvider>
            <DataSourcesPage />
        </QuotaStatusProvider>
    );
}

// In components
function DataSourceCard({ provider }) {
    const {
        isProviderQuotaExceeded, // Check if provider hit limits
        markQuotaExceeded,       // Manually mark exceeded
        clearQuotaStatus,        // Clear after upgrade
        hasQuotaIssue,           // Any provider has issues
    } = useQuotaStatus();

    if (isProviderQuotaExceeded(provider)) {
        return <UpgradePrompt />;
    }
}
```

**Notes:**
- Persists to localStorage with 24-hour TTL
- Auto-detects quota errors from ingestion jobs
- SSR-safe

---

## Settings & Billing Hooks

### `useUsage`

Current usage metrics and plan limits.

```typescript
import { useUsage, UsageProvider } from '@/hooks/useUsage';

function UsageDisplay() {
    const {
        plan,           // 'starter' | 'pro' | 'enterprise'
        filesUsed,      // Current file count
        filesLimit,     // Plan file limit
        filesPercent,   // Usage percentage
        storageUsed,    // Storage in bytes
        storageLimit,   // Storage limit in bytes
        storagePercent, // Storage percentage
        isLoading,
    } = useUsage();

    return (
        <div>
            <p>Files: {filesUsed} / {filesLimit}</p>
            <ProgressBar value={filesPercent} />
        </div>
    );
}
```

---

### `usePlans`

Fetch pricing plans for billing display.

```typescript
import { usePlans } from '@/hooks/usePlans';

function PricingPage() {
    const { plans, isLoading, error } = usePlans();

    // Plans includes: id, name, price_amount, features, etc.
    return (
        <div>
            {plans.map(plan => (
                <PlanCard key={plan.id} plan={plan} />
            ))}
        </div>
    );
}
```

**Notes:**
- Falls back to static plans on API failure
- Cancels request on unmount

---

### `useTeamMembers`

Team management with optimistic updates.

```typescript
import { useTeamMembers } from '@/hooks/useTeamMembers';

function TeamSettings() {
    const {
        members,          // Team member list
        isLoading,
        inviteMember,     // Send invite
        updateMemberRole, // Change role (optimistic)
        removeMember,     // Remove from team (optimistic)
    } = useTeamMembers();

    const handleRoleChange = async (memberId: string, role: string) => {
        // Updates immediately in UI, reverts on error
        await updateMemberRole(memberId, role);
    };
}
```

---

### `useNotificationSettings`

Notification preferences management.

```typescript
import { useNotificationSettings } from '@/hooks/useNotificationSettings';

function NotificationSettings() {
    const {
        settings,        // Current settings
        isLoading,
        updateSettings,  // Update preferences
        resetToDefaults, // Reset all settings
    } = useNotificationSettings();

    const handleToggle = async (key: string, value: boolean) => {
        await updateSettings({ [key]: value });
    };
}
```

---

## Utility Hooks

### `useRealtimeStatus`

Monitor Supabase Realtime connection.

```typescript
import { useRealtimeStatus } from '@/hooks/useRealtimeStatus';

function ConnectionIndicator() {
    const {
        status,          // 'connecting' | 'connected' | 'disconnected' | 'error'
        error,           // Error message
        reconnectAttempts, // Current retry count
        lastConnected,   // Last successful connection timestamp
        reconnect,       // Manual reconnect
    } = useRealtimeStatus();

    return (
        <div>
            {status === 'connected' ? '🟢' : '🔴'} {status}
            {status === 'error' && (
                <button onClick={reconnect}>Reconnect</button>
            )}
        </div>
    );
}
```

**Notes:**
- Implements exponential backoff (up to 30s)
- Max 10 reconnection attempts
- Resets attempts on successful connection

---

### `useNotifications`

Real-time notifications with polling fallback.

```typescript
import { useNotifications } from '@/hooks/useNotifications';

function NotificationBell() {
    const {
        notifications,    // Notification list
        unreadCount,      // Unread count
        isLoading,
        markAsRead,       // Mark single as read
        markAllAsRead,    // Mark all as read
        deleteNotification, // Remove notification
    } = useNotifications();

    return (
        <div>
            <Bell />
            {unreadCount > 0 && <Badge>{unreadCount}</Badge>}
        </div>
    );
}
```

---

### `useToast`

Toast notification system.

```typescript
import { useToast } from '@/hooks/use-toast';

function MyComponent() {
    const { toast } = useToast();

    const handleSuccess = () => {
        toast({
            title: 'Success!',
            description: 'Your changes have been saved.',
        });
    };

    const handleError = () => {
        toast({
            title: 'Error',
            description: 'Something went wrong.',
            variant: 'destructive',
        });
    };
}
```

---

### `useTheme`

Theme preference management.

```typescript
import { useTheme } from '@/hooks/useTheme';

function ThemeToggle() {
    const { theme, setTheme } = useTheme();

    return (
        <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️' : '🌙'}
        </button>
    );
}
```

---

## Best Practices

### 1. SSR Safety

Always guard browser-specific APIs:

```typescript
// ❌ Bad
const [value] = useState(localStorage.getItem('key'));

// ✅ Good
import { safeLocalStorage } from '@/lib/storage';

const [value, setValue] = useState<string | null>(null);

useEffect(() => {
    setValue(safeLocalStorage.getItem('key'));
}, []);
```

### 2. Cleanup Effects

Always clean up subscriptions and timers:

```typescript
useEffect(() => {
    const channel = supabase.channel('my-channel');
    channel.subscribe();

    return () => {
        channel.unsubscribe();
        supabase.removeChannel(channel);
    };
}, []);
```

### 3. Optimistic Updates

Update UI immediately, revert on error:

```typescript
const updateItem = async (id: string, data: Partial<Item>) => {
    const previous = items;
    setItems(items.map(i => i.id === id ? { ...i, ...data } : i));

    try {
        await api.patch(`/items/${id}`, data);
    } catch (error) {
        setItems(previous); // Revert
        toast({ title: 'Error', variant: 'destructive' });
    }
};
```

### 4. Error Boundaries

Handle hook failures gracefully:

```typescript
export function useMyHook() {
    const context = useContext(MyContext);
    
    // Return no-op implementation if outside provider
    if (!context) {
        return {
            data: [],
            isLoading: false,
            doSomething: () => {},
        };
    }
    
    return context;
}
```

### 5. Debounce User Input

Prevent excessive API calls:

```typescript
import { useDebouncedCallback } from 'use-debounce';

const debouncedSearch = useDebouncedCallback(
    (query: string) => search(query),
    300
);
```

---

## Testing Hooks

See `__tests__/hooks/` for test examples. Key patterns:

1. **Mock dependencies** at the module level
2. **Create provider wrappers** for context hooks
3. **Use `waitFor`** for async operations
4. **Use `act`** for state updates
5. **Clear mocks** in `beforeEach`

```typescript
describe('useMyHook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should fetch data', async () => {
        const { result } = renderHook(() => useMyHook(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });

        expect(result.current.data).toHaveLength(2);
    });
});
```

---

## Related Documentation

- [MIDDLEWARE_HOOKS_AUDIT.md](./MIDDLEWARE_HOOKS_AUDIT.md) - Full audit report
- [Frontend README](../README.md) - Project overview
- [API Documentation](./API.md) - Backend API reference
