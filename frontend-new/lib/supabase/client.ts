import { createBrowserClient } from '@supabase/ssr'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY

if (!supabaseUrl) throw new Error('NEXT_PUBLIC_SUPABASE_URL is required')
if (!supabaseAnonKey) throw new Error('NEXT_PUBLIC_SUPABASE_ANON_KEY is required')

const validatedUrl: string = supabaseUrl
const validatedAnonKey: string = supabaseAnonKey

let client: ReturnType<typeof createBrowserClient> | undefined

export function createClient() {
    if (client) return client

    client = createBrowserClient(validatedUrl, validatedAnonKey)

    return client
}
