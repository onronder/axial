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

// Create a singleton browser client instance
// This client properly manages auth cookies for SSR compatibility
export const supabase = createBrowserClient(supabaseUrl, supabaseKey);

// Re-export the factory function for cases where a fresh client is needed
export { createBrowserClient } from '@supabase/ssr';
