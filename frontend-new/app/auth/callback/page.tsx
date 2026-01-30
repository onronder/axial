'use client'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { Loader2 } from 'lucide-react'

/**
 * Auth Callback Content Component
 * 
 * Handles the actual OAuth callback logic. Separated from the page component
 * to allow proper Suspense boundary wrapping for useSearchParams().
 */
function AuthCallbackContent() {
    const router = useRouter()
    const searchParams = useSearchParams()
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        const handleAuthCallback = async () => {
            try {
                // Get the code and next URL from query params
                const code = searchParams.get('code')
                const next = searchParams.get('next') ?? '/dashboard'
                const errorParam = searchParams.get('error')
                const errorDescription = searchParams.get('error_description')

                // Handle OAuth error from provider
                if (errorParam) {
                    console.error('🔐 [Auth Callback] OAuth error:', errorParam, errorDescription)
                    router.replace('/auth/auth-code-error')
                    return
                }

                // If no code, check if Supabase already handled the session via hash fragment
                // This can happen with implicit grant flows
                if (!code) {
                    // Check for existing session (might have been set by hash fragment handling)
                    const { data: { session } } = await supabase.auth.getSession()
                    
                    if (session) {
                        console.log('🔐 [Auth Callback] Session found, redirecting to:', next)
                        router.replace(next)
                        return
                    }
                    
                    console.warn('🔐 [Auth Callback] No code or session found')
                    router.replace('/auth/auth-code-error')
                    return
                }

                // Exchange the code for a session using the browser client
                // The browser client has access to the PKCE verifier stored during signInWithOAuth()
                console.log('🔐 [Auth Callback] Exchanging code for session...')
                const { data, error: exchangeError } = await supabase.auth.exchangeCodeForSession(code)

                if (exchangeError) {
                    console.error('🔐 [Auth Callback] Code exchange failed:', exchangeError.message)
                    setError(exchangeError.message)
                    
                    // Small delay to show error before redirecting
                    setTimeout(() => {
                        router.replace('/auth/auth-code-error')
                    }, 1000)
                    return
                }

                if (data.user) {
                    const metadata = data.user.user_metadata || {}
                    const appMetadata = data.user.app_metadata || {}
                    const provider = appMetadata.provider || 'email'

                    console.log(`🔐 [Auth Callback] ✅ Authenticated via ${provider}`)

                    // For OAuth users, sync profile names if needed
                    // The DB trigger handles initial creation, but we ensure names are synced
                    if (provider !== 'email') {
                        const firstName = metadata.first_name || metadata.given_name || ''
                        const lastName = metadata.last_name || metadata.family_name || ''

                        if (firstName || lastName) {
                            try {
                                // Check current profile state
                                const { data: profile } = await supabase
                                    .from('user_profiles')
                                    .select('first_name, last_name')
                                    .eq('user_id', data.user.id)
                                    .single()

                                // Only update if current names are empty
                                const needsUpdate = profile && (
                                    (!profile.first_name || profile.first_name.trim() === '') ||
                                    (!profile.last_name || profile.last_name.trim() === '')
                                )

                                if (needsUpdate) {
                                    const updateData: Record<string, string> = {
                                        updated_at: new Date().toISOString(),
                                    }

                                    if (!profile.first_name || profile.first_name.trim() === '') {
                                        updateData.first_name = firstName
                                    }
                                    if (!profile.last_name || profile.last_name.trim() === '') {
                                        updateData.last_name = lastName
                                    }

                                    await supabase
                                        .from('user_profiles')
                                        .update(updateData)
                                        .eq('user_id', data.user.id)

                                    console.log(`🔐 [Auth Callback] Synced OAuth names: ${firstName} ${lastName}`)
                                }
                            } catch (syncError) {
                                // Non-fatal - profile might not exist yet (trigger still running)
                                console.warn('🔐 [Auth Callback] Profile sync warning:', syncError)
                            }
                        }
                    }
                }

                // Success - redirect to destination
                console.log('🔐 [Auth Callback] Redirecting to:', next)
                router.replace(next)

            } catch (err) {
                console.error('🔐 [Auth Callback] Unexpected error:', err)
                setError(err instanceof Error ? err.message : 'An unexpected error occurred')
                
                setTimeout(() => {
                    router.replace('/auth/auth-code-error')
                }, 1000)
            }
        }

        handleAuthCallback()
    }, [router, searchParams])

    return (
        <div className="text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">
                {error ? 'Authentication failed, redirecting...' : 'Completing sign in...'}
            </p>
            {error && (
                <p className="text-sm text-destructive max-w-xs mx-auto">
                    {error}
                </p>
            )}
        </div>
    )
}

/**
 * Loading fallback for Suspense boundary
 */
function AuthCallbackLoading() {
    return (
        <div className="text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Loading...</p>
        </div>
    )
}

/**
 * Auth Callback Page (Client-Side)
 * 
 * This page handles OAuth callbacks from Supabase Auth providers (Google, GitHub, etc.)
 * and email confirmation links.
 * 
 * IMPORTANT: This MUST be a client-side page (not a route handler) because:
 * - Supabase uses PKCE (Proof Key for Code Exchange) by default
 * - The PKCE verifier is stored in browser storage during signInWithOAuth()
 * - Only the browser client can access this verifier to complete the exchange
 * 
 * Flow:
 * 1. User clicks "Sign in with Google" → signInWithOAuth() stores PKCE verifier
 * 2. User authenticates with Google
 * 3. Google redirects here with authorization code
 * 4. This page uses browser client to exchange code (with stored verifier)
 * 5. On success, redirects to dashboard or intended destination
 */
export default function AuthCallbackPage() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
            <Suspense fallback={<AuthCallbackLoading />}>
                <AuthCallbackContent />
            </Suspense>
        </div>
    )
}
