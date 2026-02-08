import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

/**
 * Auth Callback Route Handler (Server-Side)
 * 
 * This handles OAuth callbacks from Supabase Auth providers (Google, GitHub, etc.)
 * Using a Route Handler instead of a client-side page ensures proper cookie access
 * for PKCE code exchange in Next.js App Router.
 * 
 * Flow:
 * 1. User authenticates with OAuth provider (Google, etc.)
 * 2. Provider redirects to Supabase callback
 * 3. Supabase redirects here with authorization code
 * 4. This handler exchanges the code for a session (server-side)
 * 5. Redirects user to dashboard or intended destination
 */
export async function GET(request: NextRequest) {
    const { searchParams, origin } = new URL(request.url)
    
    const code = searchParams.get('code')
    const nextRaw = searchParams.get('next') ?? '/dashboard'
    // Validate redirect target to prevent open redirects (e.g. //evil.com, javascript:, etc.)
    const next = (nextRaw.startsWith('/') && !nextRaw.startsWith('//') && !nextRaw.includes(':'))
        ? nextRaw
        : '/dashboard'
    const error = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')

    // Handle OAuth error from provider
    if (error) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('[Auth Route] OAuth error:', error, errorDescription)
        }
        return NextResponse.redirect(`${origin}/auth/auth-code-error?error=${encodeURIComponent(error)}`)
    }

    // If no code provided, redirect to error page
    if (!code) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('[Auth Route] No code provided in callback')
        }
        return NextResponse.redirect(`${origin}/auth/auth-code-error?error=no_code`)
    }

    // Create Supabase client with cookie access
    const cookieStore = await cookies()
    
    const supabase = createServerClient(
        process.env.NEXT_PUBLIC_SUPABASE_URL!,
        process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
        {
            cookies: {
                getAll() {
                    return cookieStore.getAll()
                },
                setAll(cookiesToSet) {
                    try {
                        cookiesToSet.forEach(({ name, value, options }) => {
                            cookieStore.set(name, value, options)
                        })
                    } catch {
                        // The `setAll` method was called from a Server Component.
                        // This can be ignored if you have middleware refreshing sessions.
                    }
                },
            },
        }
    )

    // Exchange the code for a session
    if (process.env.NODE_ENV !== 'production') {
        console.log('[Auth Route] Exchanging code for session...')
    }
    const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)

    if (exchangeError) {
        if (process.env.NODE_ENV !== 'production') {
            console.error('[Auth Route] Code exchange failed:', exchangeError.message)
        }
        return NextResponse.redirect(
            `${origin}/auth/auth-code-error?error=${encodeURIComponent(exchangeError.message)}`
        )
    }

    if (process.env.NODE_ENV !== 'production') {
        console.log('[Auth Route] Session created, redirecting to:', next)
    }
    
    // Successful authentication - redirect to destination
    // Use 303 See Other to ensure browser does a GET request
    return NextResponse.redirect(`${origin}${next}`, { status: 303 })
}
