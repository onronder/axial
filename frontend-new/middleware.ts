/**
 * Next.js Middleware for Authentication and Route Protection
 * 
 * This middleware runs on every request and handles:
 * 1. Session refresh - Updates Supabase auth tokens via cookies
 * 2. Route protection - Redirects unauthenticated users from protected routes
 * 3. Auth redirect - Redirects authenticated users away from login/register pages
 * 
 * @see https://nextjs.org/docs/app/building-your-application/routing/middleware
 * @see https://supabase.com/docs/guides/auth/server-side/nextjs
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { updateSession } from '@/lib/supabase/middleware';

// =============================================================================
// Route Configuration
// =============================================================================

/**
 * Routes that don't require authentication.
 * These pages are accessible to everyone.
 */
const PUBLIC_ROUTES = [
    '/',                    // Landing page
    '/login',               // Login page
    '/register',            // Registration page
    '/forgot-password',     // Password reset request
    '/auth/callback',       // Supabase auth callback
    '/auth/reset-password', // Password reset form
    '/oauth/callback',      // Data source OAuth callback
    '/pricing',             // Pricing page
    '/terms',               // Terms of service
    '/privacy',             // Privacy policy
] as const;

/**
 * Routes that authenticated users should NOT access.
 * Redirects to dashboard if user is already logged in.
 */
const AUTH_ROUTES = [
    '/login',
    '/register',
    '/forgot-password',
] as const;

/**
 * Route prefixes that should skip middleware entirely.
 * These are typically static assets or API routes handled elsewhere.
 */
const SKIP_PREFIXES = [
    '/_next',           // Next.js internals
    '/api/py',          // Python backend proxy
    '/favicon.ico',     // Favicon
    '/public',          // Public assets
    '/images',          // Image assets
    '/icons',           // Icon assets
] as const;

/**
 * File extensions that should skip middleware.
 */
const SKIP_EXTENSIONS = [
    '.ico',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.svg',
    '.webp',
    '.woff',
    '.woff2',
    '.ttf',
    '.eot',
    '.css',
    '.js',
    '.map',
] as const;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if pathname should skip middleware.
 */
function shouldSkipMiddleware(pathname: string): boolean {
    // Skip if pathname starts with a skip prefix
    if (SKIP_PREFIXES.some(prefix => pathname.startsWith(prefix))) {
        return true;
    }

    // Skip if pathname has a static file extension
    if (SKIP_EXTENSIONS.some(ext => pathname.endsWith(ext))) {
        return true;
    }

    return false;
}

/**
 * Check if pathname is a public route.
 */
function isPublicRoute(pathname: string): boolean {
    return PUBLIC_ROUTES.some(route => 
        pathname === route || pathname.startsWith(`${route}/`)
    );
}

/**
 * Check if pathname is an auth route (login, register, etc).
 */
function isAuthRoute(pathname: string): boolean {
    return AUTH_ROUTES.some(route => 
        pathname === route || pathname.startsWith(`${route}/`)
    );
}

/**
 * Check if pathname is a protected route requiring authentication.
 */
function isProtectedRoute(pathname: string): boolean {
    return pathname.startsWith('/dashboard');
}

// =============================================================================
// Middleware Handler
// =============================================================================

/**
 * Main middleware function.
 * 
 * Flow:
 * 1. Skip middleware for static assets and API routes
 * 2. Update Supabase session (refresh tokens if needed)
 * 3. Redirect authenticated users away from auth pages
 * 4. Redirect unauthenticated users to login for protected routes
 * 5. Allow access to public routes
 */
export async function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Step 1: Skip middleware for static assets and API routes
    if (shouldSkipMiddleware(pathname)) {
        return NextResponse.next();
    }

    // Step 2: Update Supabase session
    // This refreshes tokens and sets cookies for subsequent requests
    let user = null;
    let response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    });

    try {
        const sessionResult = await updateSession(request);
        user = sessionResult.user;
        response = sessionResult.response;
    } catch (error) {
        // Log error but don't block the request
        console.error('[Middleware] Session update failed:', error);
        // Continue without user - they'll be treated as unauthenticated
    }

    // Step 3: Redirect authenticated users away from auth pages
    if (user && isAuthRoute(pathname)) {
        // Check for 'next' query param to redirect to intended destination
        const next = request.nextUrl.searchParams.get('next');
        const redirectUrl = new URL(next || '/dashboard', request.url);
        
        // Ensure we don't redirect to external URLs
        if (redirectUrl.origin !== request.nextUrl.origin) {
            return NextResponse.redirect(new URL('/dashboard', request.url));
        }
        
        return NextResponse.redirect(redirectUrl);
    }

    // Step 4: Protect dashboard routes - require authentication
    if (!user && isProtectedRoute(pathname)) {
        const redirectUrl = new URL('/login', request.url);
        
        // Preserve the intended destination for post-login redirect
        redirectUrl.searchParams.set('next', pathname);
        
        // Also preserve any query params from the original request
        const searchParams = request.nextUrl.searchParams.toString();
        if (searchParams) {
            redirectUrl.searchParams.set('next', `${pathname}?${searchParams}`);
        }
        
        return NextResponse.redirect(redirectUrl);
    }

    // Step 5: Allow the request to proceed
    return response;
}

// =============================================================================
// Middleware Configuration
// =============================================================================

/**
 * Configure which routes the middleware should run on.
 * 
 * We use a negative lookahead to exclude static files and internal routes,
 * while matching all other routes.
 */
export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - public folder files
         * - API routes to Python backend
         * 
         * Note: This matcher uses a regex pattern for efficiency.
         * The actual logic in the middleware function provides more
         * granular control over route handling.
         */
        '/((?!_next/static|_next/image|favicon.ico|public/|api/py/).*)',
    ],
};
