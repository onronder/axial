# Axio Hub Frontend

Modern React/Next.js frontend for Axio Hub - an AI-powered knowledge management platform with RAG capabilities.

## Tech Stack

- **Framework:** Next.js 14+ (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS + shadcn/ui
- **State Management:** React Query (TanStack Query) + Context API
- **Auth:** Supabase Auth
- **Realtime:** Supabase Realtime
- **Testing:** Vitest + React Testing Library

## Getting Started

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Run tests
npm test

# Run tests with coverage
npm run test:coverage
```

Open [http://localhost:3000](http://localhost:3000) to view the application.

## Project Structure

```
frontend-new/
├── app/                    # Next.js App Router pages
│   ├── dashboard/          # Protected dashboard routes
│   ├── auth/               # Authentication pages
│   └── oauth/              # OAuth callback handlers
├── components/             # React components
│   ├── ui/                 # shadcn/ui components
│   ├── auth/               # Authentication forms
│   └── settings/           # Settings components
├── hooks/                  # Custom React hooks
├── lib/                    # Utilities and configurations
│   ├── supabase/           # Supabase client setup
│   └── api.ts              # API client
├── __tests__/              # Test files
│   ├── hooks/              # Hook tests
│   ├── components/         # Component tests
│   └── pages/              # Page tests
└── middleware.ts           # Edge middleware for auth
```

## Hooks Architecture

### Hook Categories

| Category | Pattern | Use Case | Examples |
|----------|---------|----------|----------|
| **Context Hooks** | Provider + Consumer | Shared state across tree | `useAuth`, `useProfile`, `useUsage` |
| **Query Hooks** | React Query | Server state | `useDocuments`, `useChatHistory` |
| **State Hooks** | useState + useEffect | Local component state | `usePlans`, `useOnboarding` |
| **Realtime Hooks** | Supabase channels | Live updates | `useNotifications`, `useQuotaStatus` |

### Query Key Factory Pattern

For React Query hooks, use the query key factory pattern:

```typescript
// hooks/useDocuments.ts
export const documentKeys = {
    all: ['documents'] as const,
    lists: () => [...documentKeys.all, 'list'] as const,
    list: (filter?: string) => [...documentKeys.lists(), filter] as const,
    detail: (id: string) => [...documentKeys.all, 'detail', id] as const,
};
```

### Context Hook Pattern

For shared state, create a Context with Provider:

```typescript
// hooks/useMyFeature.tsx
const MyContext = createContext<MyContextValue | null>(null);

export function MyProvider({ children }: { children: ReactNode }) {
    const [state, setState] = useState<State>(initialState);
    
    const value = useMemo(() => ({ state, setState }), [state]);
    
    return (
        <MyContext.Provider value={value}>
            {children}
        </MyContext.Provider>
    );
}

export function useMyFeature() {
    const context = useContext(MyContext);
    if (!context) {
        throw new Error('useMyFeature must be used within MyProvider');
    }
    return context;
}
```

### SSR-Safe Hooks

Always guard browser-specific APIs:

```typescript
// ❌ Bad - crashes on SSR
const [value, setValue] = useState(localStorage.getItem('key'));

// ✅ Good - SSR safe
import { safeLocalStorage } from '@/lib/storage';

useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = safeLocalStorage.getItem('key');
    setValue(stored);
}, []);
```

### Realtime Hook Pattern

For Supabase realtime subscriptions:

```typescript
useEffect(() => {
    if (!user?.id) return;

    const channel = supabase
        .channel(`my-channel-${user.id}`)
        .on('postgres_changes', {
            event: 'UPDATE',
            schema: 'public',
            table: 'my_table',
            filter: `user_id=eq.${user.id}`,
        }, (payload) => {
            handleChange(payload.new);
        })
        .subscribe();

    return () => {
        channel.unsubscribe();
        supabase.removeChannel(channel);
    };
}, [user?.id]);
```

## Available Hooks

### Authentication & User

| Hook | Description |
|------|-------------|
| `useAuth` | Authentication state and methods (login, logout, OAuth) |
| `useProfile` | User profile data and updates |
| `useOnboarding` | Onboarding flow state |

### Data Management

| Hook | Description |
|------|-------------|
| `useDocuments` | Document CRUD operations |
| `useChatHistory` | Chat conversations and messages |
| `useSearch` | Vector search with debouncing |
| `useFeedback` | User feedback submission |

### Data Sources

| Hook | Description |
|------|-------------|
| `useDataSources` | Connected data source management |
| `useIngestionJobs` | Ingestion job tracking |
| `useIngestionProgress` | Real-time ingestion progress |
| `useQuotaStatus` | Quota limit tracking |

### Settings & Billing

| Hook | Description |
|------|-------------|
| `useUsage` | Usage metrics and limits |
| `usePlans` | Pricing plans |
| `useTeamMembers` | Team management |
| `useNotificationSettings` | Notification preferences |

### Utilities

| Hook | Description |
|------|-------------|
| `useRealtimeStatus` | Supabase connection status |
| `useNotifications` | Real-time notifications |
| `useToast` | Toast notifications |
| `useTheme` | Theme preferences |

## Testing Guidelines

### Test File Structure

```typescript
// __tests__/hooks/useMyHook.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMyHook } from '@/hooks/useMyHook';

// Mock dependencies at the top
vi.mock('@/lib/api', () => ({
    api: { get: vi.fn(), post: vi.fn() },
}));

// Create wrapper for providers
const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return ({ children }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
};

describe('useMyHook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Initial State', () => {
        it('should have correct initial values', () => {
            const { result } = renderHook(() => useMyHook(), {
                wrapper: createWrapper(),
            });
            expect(result.current.isLoading).toBe(true);
        });
    });

    describe('Data Fetching', () => {
        it('should fetch data on mount', async () => {
            // Test implementation
        });
    });
});
```

### Testing Context Hooks

```typescript
// Create a wrapper with the provider
const createWrapper = () => {
    return ({ children }) => (
        <MyProvider>{children}</MyProvider>
    );
};

it('should throw when used outside provider', () => {
    expect(() => renderHook(() => useMyHook())).toThrow(
        'useMyHook must be used within MyProvider'
    );
});
```

### Running Tests

```bash
# Run all tests
npm test

# Run specific test file
npm test -- __tests__/hooks/useAuth.test.ts

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

## Middleware

The application uses Next.js middleware for:

- **Route Protection:** Redirects unauthenticated users from `/dashboard/*`
- **Auth Redirects:** Redirects authenticated users from `/login`, `/register`
- **Session Refresh:** Keeps Supabase session tokens fresh

See `middleware.ts` for implementation.

## Environment Variables

```env
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your_google_client_id
NEXT_PUBLIC_MICROSOFT_CLIENT_ID=your_microsoft_client_id
```

## Code Style

- Use TypeScript strict mode
- Follow ESLint rules
- Use Prettier for formatting
- Prefer named exports over default exports
- Use `@/` alias for absolute imports

## Contributing

1. Create a feature branch
2. Write tests for new features
3. Ensure all tests pass
4. Submit PR for review

## License

Proprietary - All rights reserved.
