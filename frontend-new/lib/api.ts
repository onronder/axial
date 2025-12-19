/**
 * Axios API Client with Supabase JWT Interceptor
 * 
 * This client:
 * - Proxies requests through Next.js rewrites to the Python backend
 * - Automatically injects the Supabase JWT token for authenticated requests
 * - Uses the SSR-compatible Supabase client for consistent session handling
 */

import axios from 'axios';
import { supabase } from '@/lib/supabase';

export const api = axios.create({
    baseURL: '/api/py',
    headers: {
        'Content-Type': 'application/json',
    },
});

/**
 * Request interceptor to inject Authorization header
 * 
 * This runs before every request to the Python backend,
 * fetching the current session token from Supabase.
 */
api.interceptors.request.use(
    async (config) => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch (error) {
            console.error('Failed to get auth token for API request:', error);
        }

        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

/**
 * Response interceptor for handling auth errors
 * 
 * If the backend returns 401, the token may be expired.
 * We could trigger a refresh here if needed.
 */
api.interceptors.response.use(
    (response) => response,
    async (error) => {
        if (error.response?.status === 401) {
            // Token expired or invalid - could trigger re-auth here
            console.warn('API returned 401 - user may need to re-authenticate');
        }
        return Promise.reject(error);
    }
);

// Legacy alias for backward compatibility
export const authFetch = api;
