import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

/**
 * Auth Callback Route Handler
 * 
 * This route handles OAuth callbacks from providers (Google, GitHub, etc.)
 * and email confirmation links. It:
 * 
 * 1. Exchanges the authorization code for a session
 * 2. Syncs OAuth provider metadata (name, avatar) to user_profiles
 * 3. Redirects to the intended destination or dashboard
 * 
 * The database trigger `handle_new_user` creates the initial profile,
 * but this route ensures OAuth metadata is properly synced.
 */
export async function GET(request: Request) {
    const { searchParams, origin } = new URL(request.url)
    const code = searchParams.get('code')
    // Support 'next' param for post-auth redirect
    const next = searchParams.get('next') ?? '/dashboard'

    if (code) {
        const supabase = await createClient()
        
        try {
            const { data, error } = await supabase.auth.exchangeCodeForSession(code)
            
            if (error) {
                console.error('🔐 [Auth Callback] Code exchange failed:', error.message)
                return NextResponse.redirect(`${origin}/auth/auth-code-error`)
            }
            
            if (data.user) {
                const metadata = data.user.user_metadata || {}
                const appMetadata = data.user.app_metadata || {}
                const provider = appMetadata.provider || 'email'
                
                console.log(`🔐 [Auth Callback] User authenticated via ${provider}`)
                
                // For OAuth users, ensure profile has names from provider metadata
                // The DB trigger handles initial creation, but we sync any missing data
                if (provider !== 'email') {
                    const firstName = metadata.first_name || metadata.given_name || ''
                    const lastName = metadata.last_name || metadata.family_name || ''
                    
                    // Only sync if we have name data from the provider
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
                                
                                console.log(`🔐 [Auth Callback] Synced OAuth names to profile: ${firstName} ${lastName}`)
                            }
                        } catch (syncError) {
                            // Non-fatal error - profile might not exist yet (trigger still running)
                            console.warn('🔐 [Auth Callback] Profile sync warning:', syncError)
                        }
                    }
                }
            }
            
            // Successful auth - redirect to destination
            const redirectUrl = next.startsWith('/') ? `${origin}${next}` : next
            return NextResponse.redirect(redirectUrl)
            
        } catch (error) {
            console.error('🔐 [Auth Callback] Unexpected error:', error)
            return NextResponse.redirect(`${origin}/auth/auth-code-error`)
        }
    }

    // No code provided - redirect to error page
    console.warn('🔐 [Auth Callback] No authorization code received')
    return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}
