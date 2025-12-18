import { createClient } from '@/lib/supabase/client' // Ensure we use the browser client

export async function authFetch(endpoint: string, options: RequestInit = {}) {
    const supabase = createClient()
    const { data: { session } } = await supabase.auth.getSession()

    if (!session?.access_token) {
        console.error("authFetch: No active session token found.")
        throw new Error('Unauthorized: No session')
    }

    // Default to JSON only if not specified
    const defaultHeaders: Record<string, string> = {
        'Authorization': `Bearer ${session.access_token}`,
    }

    // Only set Content-Type to JSON if the caller hasn't set one (e.g. for FormData, it should be let alone)
    // However, options.headers might be Headers object or array. We assume simple object for now or handle cast.
    // Ideally, we just merge. If we are sending FormData, we shouldn't set Content-Type.
    // If we are sending URLSearchParams, caller sets it.

    // Simpler approach: Allow override.
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers, // This allows caller to override 'Content-Type' or unset it
        'Authorization': `Bearer ${session.access_token}`, // Always enforce auth
    }

    // Safety check: If body is FormData, we MUST NOT set Content-Type, 
    // to let the browser set it with the boundary.
    if (options.body instanceof FormData) {
        // @ts-ignore
        delete headers['Content-Type']
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') || 'http://localhost:8000/api/v1'
    const url = `${baseUrl}${endpoint.startsWith('/') ? endpoint : '/' + endpoint}`

    try {
        const response = await fetch(url, { ...options, headers })

        if (response.status === 401) {
            console.error("authFetch: Backend rejected token. Check JWT Secret match.")
            throw new Error('Unauthorized')
        }

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}))
            const errorMessage = typeof errorData.detail === 'object'
                ? JSON.stringify(errorData.detail)
                : (errorData.detail || `API Error: ${response.statusText}`)
            throw new Error(errorMessage)
        }

        return response.json()
    } catch (error) {
        console.error("authFetch Network Error:", error)
        throw error
    }
}
