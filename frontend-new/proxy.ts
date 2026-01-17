/**
 * Next.js 16 Proxy - Production-Grade Session Management
 * 
 * This proxy handles:
 * 1. Session refresh for all authenticated requests
 * 2. Protection of private routes (redirect to login if no session)
 * 3. Graceful handling of session_not_found errors (clear stale cookies)
 * 4. Proper exclusion of auth callbacks to prevent breaking OAuth flows
 * 5. Redirect authenticated users away from auth pages
 * 
 * IMPORTANT: This proxy runs on EVERY request. Keep it fast and fail-safe.
 * 
 * @see https://nextjs.org/docs/messages/middleware-to-proxy
 * @see https://supabase.com/docs/guides/auth/server-side/nextjs
 */

import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

// =============================================================================
// ROUTE CONFIGURATION
// =============================================================================

/**
 * Routes that should NEVER go through session validation.
 * These are critical paths that handle their own authentication.
 * 
 * CRITICAL: These paths are skipped entirely - no session refresh, no validation.
 */
const EXCLUDED_PATHS = [
    '/auth/callback',       // Supabase email auth code exchange - CRITICAL
    '/auth/reset-password', // Password reset flow
    '/auth/auth-code-error', // Auth error display page
    '/_next',               // Next.js internals
    '/api',                 // API routes (if any)
    '/monitoring',          // Sentry tunnel
] as const

/**
 * Routes that don't require authentication but still benefit from session refresh.
 * Users can access these logged out, but if they have a session, it will be refreshed.
 */
const PUBLIC_PATHS = [
    '/',                    // Landing page
    '/login',               // Login page
    '/register',            // Registration page
    '/forgot-password',     // Password reset request
    '/legal',               // Legal pages (privacy, terms)
    '/invite',              // Team invite acceptance
    '/oauth/callback',      // OAuth provider callbacks
] as const

/**
 * Auth pages where authenticated users should be redirected to dashboard.
 */
const AUTH_PAGES = ['/login', '/register'] as const

// =============================================================================
// ENVIRONMENT VALIDATION
// =============================================================================

/**
 * Validate required environment variables at module load time.
 * This fails fast if configuration is missing.
 */
const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.error('[Proxy] CRITICAL: Missing Supabase environment variables')
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Check if a path should be completely excluded from proxy processing.
 */
function isExcludedPath(pathname: string): boolean {
    return EXCLUDED_PATHS.some(path => pathname.startsWith(path))
}

/**
 * Check if a path is public (doesn't require authentication).
 */
function isPublicPath(pathname: string): boolean {
    // Exact match for root
    if (pathname === '/') return true
    
    // Check if path matches or starts with any public path
    return PUBLIC_PATHS.some(path => {
        if (path === '/') return false // Already handled above
        return pathname === path || pathname.startsWith(`${path}/`)
    })
}

/**
 * Check if a path is an auth page (login/register).
 */
function isAuthPage(pathname: string): boolean {
    return AUTH_PAGES.some(path => pathname === path || pathname.startsWith(`${path}/`))
}

/**
 * Check if a path is a static asset that should skip proxy.
 */
function isStaticAsset(pathname: string): boolean {
    // Skip files with extensions (except .html)
    const hasExtension = pathname.includes('.') && !pathname.endsWith('.html')
    // Skip Next.js static directories
    const isNextStatic = pathname.startsWith('/_next/static') || pathname.startsWith('/_next/image')
    return hasExtension || isNextStatic
}

/**
 * Extract Supabase project reference from URL for cookie naming.
 */
function getProjectRef(): string | null {
    if (!SUPABASE_URL) return null
    
    const match = SUPABASE_URL.match(/https:\/\/([^.]+)\.supabase\.co/)
    return match?.[1] || null
}

/**
 * Clear all Supabase auth cookies to force re-authentication.
 * This is called when we detect an invalid/stale session.
 */
function clearAuthCookies(response: NextResponse): void {
    const projectRef = getProjectRef()
    if (!projectRef) return
    
    // Supabase stores auth tokens in multiple cookies (chunked for large tokens)
    const cookieNames = [
        `sb-${projectRef}-auth-token`,
        `sb-${projectRef}-auth-token.0`,
        `sb-${projectRef}-auth-token.1`,
        `sb-${projectRef}-auth-token.2`,
        `sb-${projectRef}-auth-token.3`, // Extra safety for very large tokens
    ]
    
    cookieNames.forEach(name => {
        response.cookies.delete(name)
    })
}

/**
 * Create redirect URL to login page with appropriate params.
 * Includes protection against redirect loops.
 */
function createLoginRedirect(
    request: NextRequest, 
    reason?: 'session_expired' | 'session_not_found' | 'auth_required'
): NextResponse {
    const loginUrl = new URL('/login', request.url)
    
    const { pathname, search } = request.nextUrl
    
    // PROTECTION: Prevent redirect loops - don't redirect to login if already there
    // Also don't set redirectTo for the home page
    if (pathname !== '/login' && pathname !== '/' && !isPublicPath(pathname)) {
        loginUrl.searchParams.set('redirectTo', pathname + search)
    }
    
    // Add error reason for user feedback
    if (reason) {
        loginUrl.searchParams.set('error', reason)
    }
    
    return NextResponse.redirect(loginUrl)
}

// =============================================================================
// MAIN PROXY
// =============================================================================

export async function proxy(request: NextRequest) {
    const { pathname } = request.nextUrl
    
    // ---------------------------------------------------------------------
    // 0. FAIL-SAFE: If Supabase is not configured, skip proxy
    // ---------------------------------------------------------------------
    if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
        console.warn('[Proxy] Supabase not configured - skipping auth checks')
        return NextResponse.next()
    }
    
    // ---------------------------------------------------------------------
    // 1. FAST PATH: Skip excluded paths entirely (no processing at all)
    // ---------------------------------------------------------------------
    if (isExcludedPath(pathname)) {
        return NextResponse.next()
    }
    
    // ---------------------------------------------------------------------
    // 2. FAST PATH: Skip static assets
    // ---------------------------------------------------------------------
    if (isStaticAsset(pathname)) {
        return NextResponse.next()
    }
    
    // ---------------------------------------------------------------------
    // 3. CREATE RESPONSE AND SUPABASE CLIENT
    // ---------------------------------------------------------------------
    const response = NextResponse.next({
        request: {
            headers: request.headers,
        },
    })
    
    const supabase = createServerClient(
        SUPABASE_URL,
        SUPABASE_ANON_KEY,
        {
            cookies: {
                getAll() {
                    return request.cookies.getAll()
                },
                setAll(cookiesToSet: { name: string; value: string; options: CookieOptions }[]) {
                    cookiesToSet.forEach(({ name, value, options }) => {
                        request.cookies.set(name, value)
                        response.cookies.set(name, value, options)
                    })
                },
            },
        }
    )
    
    // ---------------------------------------------------------------------
    // 4. VALIDATE AND REFRESH SESSION
    // ---------------------------------------------------------------------
    try {
        // getUser() validates the session with Supabase server
        // This is more secure than getSession() which only reads the cookie
        const { data: { user }, error } = await supabase.auth.getUser()
        
        // Handle specific auth errors
        if (error) {
            // Log for debugging (will appear in Vercel/server logs)
            // Only log for protected routes to reduce noise
            if (!isPublicPath(pathname)) {
                console.warn('[Proxy] Auth error:', error.message, 'Path:', pathname)
            }
            
            // Check if it's a session_not_found or similar invalid session error
            const isSessionError = 
                error.message?.includes('session_not_found') || 
                error.message?.includes('invalid') ||
                error.message?.includes('expired') ||
                error.message?.includes('refresh_token') ||
                error.status === 401 ||
                error.status === 403
            
            if (isSessionError) {
                // Clear stale cookies to prevent error loops
                clearAuthCookies(response)
                
                // For protected routes, redirect to login
                if (!isPublicPath(pathname)) {
                    return createLoginRedirect(request, 'session_expired')
                }
                
                // For public routes, just continue with cleared cookies
                return response
            }
            
            // For non-session errors (e.g., network issues), don't block
            // Just log and continue - better to allow access than break the app
            console.error('[Proxy] Non-session auth error:', error)
        }
        
        // ---------------------------------------------------------------------
        // 5. ENFORCE AUTHENTICATION FOR PROTECTED ROUTES
        // ---------------------------------------------------------------------
        if (!user && !isPublicPath(pathname)) {
            return createLoginRedirect(request, 'auth_required')
        }
        
        // ---------------------------------------------------------------------
        // 6. REDIRECT AUTHENTICATED USERS FROM AUTH PAGES
        // ---------------------------------------------------------------------
        if (user && isAuthPage(pathname)) {
            return NextResponse.redirect(new URL('/dashboard', request.url))
        }
        
        // Success - return response with any refreshed session cookies
        return response
        
    } catch (error) {
        // ---------------------------------------------------------------------
        // 7. HANDLE UNEXPECTED ERRORS GRACEFULLY
        // ---------------------------------------------------------------------
        console.error('[Proxy] Unexpected error:', error)
        
        // IMPORTANT: Don't break the app on proxy errors
        // Clear auth state and let the page handle authentication
        clearAuthCookies(response)
        
        // For protected routes, redirect to login
        if (!isPublicPath(pathname)) {
            return createLoginRedirect(request, 'session_expired')
        }
        
        // For public routes, continue but with cleared auth state
        return response
    }
}

// =============================================================================
// PROXY MATCHER CONFIGURATION
// =============================================================================

export const config = {
    matcher: [
        /*
         * Match all request paths except:
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         * - Static assets by extension
         * 
         * Note: We handle additional exclusions in the proxy function
         * for more fine-grained control and better error messages.
         */
        '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp|ico|woff|woff2|ttf|eot)$).*)',
    ],
}
