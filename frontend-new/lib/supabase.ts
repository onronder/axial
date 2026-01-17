/**
 * Unified Supabase Browser Client
 * 
 * This module re-exports the SSR-compatible browser client from @supabase/ssr.
 * This ensures session cookies are properly managed and shared between
 * client components and middleware/server components.
 * 
 * IMPORTANT: Always use this import for client-side Supabase operations.
 * For server-side (Route Handlers, Server Components), use `lib/supabase/server.ts`.
 */

import { createBrowserClient } from '@supabase/ssr';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;

if (!supabaseUrl || !supabaseKey) {
    throw new Error('Missing Supabase environment variables: NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY');
}

/**
 * Singleton browser client instance for Supabase.
 * 
 * This client properly manages auth cookies for SSR compatibility with Next.js.
 * 
 * Configuration Notes:
 * - detectSessionInUrl: false
 *   This setting is INTENTIONALLY disabled to prevent Supabase from automatically
 *   detecting and exchanging OAuth tokens from URL fragments/query params.
 *   
 *   Reason: Axio Hub uses a backend-managed OAuth flow where:
 *   1. OAuth exchanges happen on the backend (FastAPI)
 *   2. Tokens are encrypted and stored server-side
 *   3. Only the Supabase session (not OAuth tokens) is managed client-side
 *   
 *   With detectSessionInUrl enabled, Supabase would incorrectly try to exchange
 *   third-party OAuth codes (Google, Microsoft, GitHub, etc.) meant for our
 *   backend, causing session conflicts and authentication failures.
 */
export const supabase = createBrowserClient(supabaseUrl, supabaseKey, {
    auth: {
        // INTENTIONAL: OAuth exchanges handled by backend, not Supabase client
        // See documentation above for detailed explanation
        detectSessionInUrl: false,
    },
});

// Re-export the factory function for cases where a fresh client is needed
export { createBrowserClient } from '@supabase/ssr';
