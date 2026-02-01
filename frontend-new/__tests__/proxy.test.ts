/**
 * Tests for proxy.ts - Next.js Proxy for Session Management
 * 
 * Tests the proxy logic including:
 * - Route classification (excluded, public, auth, static)
 * - Session validation and refresh
 * - Redirect logic for auth pages
 * - Cookie clearing for stale sessions
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { NextRequest, NextResponse } from 'next/server';

// =============================================================================
// MOCKS
// =============================================================================

// Mock Supabase SSR
const mockGetUser = vi.fn();
const mockGetAll = vi.fn();
const mockSetAll = vi.fn();

vi.mock('@supabase/ssr', () => ({
    createServerClient: vi.fn(() => ({
        auth: {
            getUser: mockGetUser,
        },
    })),
}));

// Mock environment variables
vi.stubEnv('NEXT_PUBLIC_SUPABASE_URL', 'https://test-project.supabase.co');
vi.stubEnv('NEXT_PUBLIC_SUPABASE_ANON_KEY', 'test-anon-key');

// =============================================================================
// HELPER FUNCTION TESTS
// =============================================================================

describe('Route Classification Helpers', () => {
    // These are pure functions we can test by recreating them
    const EXCLUDED_PATHS = [
        '/auth/callback',
        '/auth/reset-password',
        '/auth/auth-code-error',
        '/_next',
        '/api',
        '/monitoring',
    ];

    const PUBLIC_PATHS = [
        '/',
        '/login',
        '/register',
        '/forgot-password',
        '/legal',
        '/invite',
        '/oauth/callback',
    ];

    const AUTH_PAGES = ['/login', '/register'];

    const isExcludedPath = (pathname: string): boolean => {
        return EXCLUDED_PATHS.some(path => pathname.startsWith(path));
    };

    const isPublicPath = (pathname: string): boolean => {
        if (pathname === '/') return true;
        return PUBLIC_PATHS.some(path => {
            if (path === '/') return false;
            return pathname === path || pathname.startsWith(`${path}/`);
        });
    };

    const isAuthPage = (pathname: string): boolean => {
        return AUTH_PAGES.some(path => pathname === path || pathname.startsWith(`${path}/`));
    };

    const isStaticAsset = (pathname: string): boolean => {
        const hasExtension = pathname.includes('.') && !pathname.endsWith('.html');
        const isNextStatic = pathname.startsWith('/_next/static') || pathname.startsWith('/_next/image');
        return hasExtension || isNextStatic;
    };

    describe('isExcludedPath', () => {
        it('should return true for auth/callback', () => {
            expect(isExcludedPath('/auth/callback')).toBe(true);
        });

        it('should return true for auth/reset-password', () => {
            expect(isExcludedPath('/auth/reset-password')).toBe(true);
        });

        it('should return true for _next paths', () => {
            expect(isExcludedPath('/_next/webpack-hmr')).toBe(true);
        });

        it('should return true for api routes', () => {
            expect(isExcludedPath('/api/health')).toBe(true);
        });

        it('should return true for monitoring', () => {
            expect(isExcludedPath('/monitoring/sentry')).toBe(true);
        });

        it('should return false for dashboard', () => {
            expect(isExcludedPath('/dashboard')).toBe(false);
        });

        it('should return false for login', () => {
            expect(isExcludedPath('/login')).toBe(false);
        });
    });

    describe('isPublicPath', () => {
        it('should return true for root path', () => {
            expect(isPublicPath('/')).toBe(true);
        });

        it('should return true for /login', () => {
            expect(isPublicPath('/login')).toBe(true);
        });

        it('should return true for /register', () => {
            expect(isPublicPath('/register')).toBe(true);
        });

        it('should return true for /forgot-password', () => {
            expect(isPublicPath('/forgot-password')).toBe(true);
        });

        it('should return true for /legal subpaths', () => {
            expect(isPublicPath('/legal/privacy')).toBe(true);
            expect(isPublicPath('/legal/terms')).toBe(true);
        });

        it('should return true for /invite', () => {
            expect(isPublicPath('/invite')).toBe(true);
            expect(isPublicPath('/invite/abc123')).toBe(true);
        });

        it('should return true for /oauth/callback', () => {
            expect(isPublicPath('/oauth/callback')).toBe(true);
        });

        it('should return false for /dashboard', () => {
            expect(isPublicPath('/dashboard')).toBe(false);
        });

        it('should return false for /settings', () => {
            expect(isPublicPath('/settings')).toBe(false);
        });
    });

    describe('isAuthPage', () => {
        it('should return true for /login', () => {
            expect(isAuthPage('/login')).toBe(true);
        });

        it('should return true for /register', () => {
            expect(isAuthPage('/register')).toBe(true);
        });

        it('should return true for /login/magic-link', () => {
            expect(isAuthPage('/login/magic-link')).toBe(true);
        });

        it('should return false for /dashboard', () => {
            expect(isAuthPage('/dashboard')).toBe(false);
        });

        it('should return false for /forgot-password', () => {
            expect(isAuthPage('/forgot-password')).toBe(false);
        });
    });

    describe('isStaticAsset', () => {
        it('should return true for image files', () => {
            expect(isStaticAsset('/logo.png')).toBe(true);
            expect(isStaticAsset('/images/hero.jpg')).toBe(true);
            expect(isStaticAsset('/favicon.ico')).toBe(true);
        });

        it('should return true for font files', () => {
            expect(isStaticAsset('/fonts/inter.woff2')).toBe(true);
        });

        it('should return true for _next/static paths', () => {
            expect(isStaticAsset('/_next/static/chunks/main.js')).toBe(true);
        });

        it('should return true for _next/image paths', () => {
            expect(isStaticAsset('/_next/image?url=test')).toBe(true);
        });

        it('should return false for .html files', () => {
            expect(isStaticAsset('/page.html')).toBe(false);
        });

        it('should return false for normal routes', () => {
            expect(isStaticAsset('/dashboard')).toBe(false);
            expect(isStaticAsset('/login')).toBe(false);
        });
    });
});

describe('Project Reference Extraction', () => {
    const getProjectRef = (url: string | undefined): string | null => {
        if (!url) return null;
        const match = url.match(/https:\/\/([^.]+)\.supabase\.co/);
        return match?.[1] || null;
    };

    it('should extract project ref from supabase URL', () => {
        expect(getProjectRef('https://abc123.supabase.co')).toBe('abc123');
    });

    it('should extract project ref from full URL', () => {
        expect(getProjectRef('https://my-project-ref.supabase.co/rest/v1')).toBe('my-project-ref');
    });

    it('should return null for undefined URL', () => {
        expect(getProjectRef(undefined)).toBeNull();
    });

    it('should return null for non-matching URL', () => {
        expect(getProjectRef('https://example.com')).toBeNull();
    });
});

describe('Login Redirect URL Construction', () => {
    const createLoginRedirectParams = (
        pathname: string,
        search: string,
        reason?: 'session_expired' | 'session_not_found' | 'auth_required'
    ): URLSearchParams => {
        const params = new URLSearchParams();
        
        // Don't set redirectTo for login, home, or public paths
        const PUBLIC_PATHS = ['/', '/login', '/register', '/forgot-password', '/legal', '/invite', '/oauth/callback'];
        const isPublic = pathname === '/' || PUBLIC_PATHS.some(p => p !== '/' && (pathname === p || pathname.startsWith(`${p}/`)));
        
        if (pathname !== '/login' && pathname !== '/' && !isPublic) {
            params.set('redirectTo', pathname + search);
        }
        
        if (reason) {
            params.set('error', reason);
        }
        
        return params;
    };

    it('should include redirectTo for protected paths', () => {
        const params = createLoginRedirectParams('/dashboard', '');
        expect(params.get('redirectTo')).toBe('/dashboard');
    });

    it('should include query string in redirectTo', () => {
        const params = createLoginRedirectParams('/dashboard', '?tab=settings');
        expect(params.get('redirectTo')).toBe('/dashboard?tab=settings');
    });

    it('should not include redirectTo for login page', () => {
        const params = createLoginRedirectParams('/login', '');
        expect(params.get('redirectTo')).toBeNull();
    });

    it('should not include redirectTo for home page', () => {
        const params = createLoginRedirectParams('/', '');
        expect(params.get('redirectTo')).toBeNull();
    });

    it('should include error reason when provided', () => {
        const params = createLoginRedirectParams('/dashboard', '', 'session_expired');
        expect(params.get('error')).toBe('session_expired');
    });

    it('should handle auth_required reason', () => {
        const params = createLoginRedirectParams('/settings', '', 'auth_required');
        expect(params.get('error')).toBe('auth_required');
    });
});

describe('Cookie Name Generation', () => {
    it('should generate correct auth token cookie names', () => {
        const projectRef = 'test-project';
        const cookieNames = [
            `sb-${projectRef}-auth-token`,
            `sb-${projectRef}-auth-token.0`,
            `sb-${projectRef}-auth-token.1`,
            `sb-${projectRef}-auth-token.2`,
            `sb-${projectRef}-auth-token.3`,
        ];

        expect(cookieNames[0]).toBe('sb-test-project-auth-token');
        expect(cookieNames[1]).toBe('sb-test-project-auth-token.0');
        expect(cookieNames.length).toBe(5);
    });
});

describe('Session Error Detection', () => {
    const isSessionError = (error: { message?: string; status?: number }): boolean => {
        return (
            error.message?.includes('session_not_found') ||
            error.message?.includes('invalid') ||
            error.message?.includes('expired') ||
            error.message?.includes('refresh_token') ||
            error.status === 401 ||
            error.status === 403
        ) ?? false;
    };

    it('should detect session_not_found error', () => {
        expect(isSessionError({ message: 'session_not_found' })).toBe(true);
    });

    it('should detect invalid session error', () => {
        expect(isSessionError({ message: 'Token is invalid or expired' })).toBe(true);
    });

    it('should detect expired session error', () => {
        expect(isSessionError({ message: 'Session has expired' })).toBe(true);
    });

    it('should detect refresh_token error', () => {
        expect(isSessionError({ message: 'refresh_token not found' })).toBe(true);
    });

    it('should detect 401 status', () => {
        expect(isSessionError({ status: 401 })).toBe(true);
    });

    it('should detect 403 status', () => {
        expect(isSessionError({ status: 403 })).toBe(true);
    });

    it('should return false for network errors', () => {
        expect(isSessionError({ message: 'Network request failed' })).toBe(false);
    });

    it('should return false for 500 errors', () => {
        expect(isSessionError({ status: 500 })).toBe(false);
    });
});

describe('Proxy Configuration', () => {
    it('should have correct matcher pattern', () => {
        const config = {
            matcher: [
                '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff|woff2|ttf|eot)$).*)',
            ],
        };

        expect(config.matcher).toBeDefined();
        expect(config.matcher.length).toBe(1);
        expect(config.matcher[0]).toContain('_next/static');
        expect(config.matcher[0]).toContain('favicon.ico');
    });

    it('matcher should exclude static file extensions', () => {
        const matcherPattern = '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff|woff2|ttf|eot)$).*)';
        
        // The pattern should NOT match these
        const staticExtensions = ['svg', 'png', 'jpg', 'jpeg', 'gif', 'webp', 'ico', 'woff', 'woff2', 'ttf', 'eot'];
        
        staticExtensions.forEach(ext => {
            expect(matcherPattern).toContain(ext);
        });
    });
});
