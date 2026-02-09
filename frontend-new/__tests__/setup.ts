/**
 * Test Setup - Vitest Configuration
 * 
 * Sets up:
 * - Jest DOM matchers for React Testing Library
 * - Global mocks for browser APIs
 * - Mock implementations for external services
 */

import { vi } from 'vitest';
import '@testing-library/jest-dom';

// =============================================================================
// Global Mocks
// =============================================================================

// Mock next/navigation
vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: vi.fn(),
        replace: vi.fn(),
        back: vi.fn(),
        forward: vi.fn(),
        refresh: vi.fn(),
        prefetch: vi.fn(),
    }),
    usePathname: () => '/dashboard/chat/new',
    useSearchParams: () => new URLSearchParams(),
}));

// Mock Supabase client
vi.mock('@/lib/supabase', () => ({
    supabase: {
        auth: {
            getSession: vi.fn().mockResolvedValue({
                data: {
                    session: {
                        access_token: 'mock-token',
                        user: {
                            id: 'test-user-id',
                            email: 'test@example.com',
                        },
                    },
                },
                error: null,
            }),
            onAuthStateChange: vi.fn().mockReturnValue({
                data: { subscription: { unsubscribe: vi.fn() } },
            }),
        },
    },
}));

// Mock API client
vi.mock('@/lib/api', () => ({
    api: {
        get: vi.fn().mockResolvedValue({ data: [] }),
        post: vi.fn().mockResolvedValue({ data: {} }),
        patch: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    },
    authFetch: {
        get: vi.fn().mockResolvedValue({ data: [] }),
        post: vi.fn().mockResolvedValue({ data: {} }),
        delete: vi.fn().mockResolvedValue({ data: {} }),
    },
    clearAuthCache: vi.fn(),
}));

// Mock useToast hook
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({
        toast: vi.fn(),
    }),
}));

// =============================================================================
// DOM API Mocks
// =============================================================================

// Mock ResizeObserver as a proper class
class ResizeObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}
global.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;

// Mock IntersectionObserver as a proper class
class IntersectionObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
}
global.IntersectionObserver = IntersectionObserverMock as unknown as typeof IntersectionObserver;

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

Object.defineProperty(window, 'scrollTo', {
    writable: true,
    value: vi.fn(),
});

Object.defineProperty(HTMLElement.prototype, 'setPointerCapture', {
    writable: true,
    value: vi.fn(),
});

Object.defineProperty(HTMLElement.prototype, 'releasePointerCapture', {
    writable: true,
    value: vi.fn(),
});

Object.defineProperty(HTMLElement.prototype, 'hasPointerCapture', {
    writable: true,
    value: vi.fn().mockReturnValue(false),
});

Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {
    writable: true,
    value: vi.fn(),
});
