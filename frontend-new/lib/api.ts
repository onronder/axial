/**
 * Axios API Client with Token Caching
 * 
 * PERFORMANCE OPTIMIZATION: Caches the JWT token in memory and only
 * refreshes when it's close to expiring (5 minute buffer).
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { supabase } from '@/lib/supabase';

// Debug mode - set to false for production
const DEBUG_MODE = process.env.NODE_ENV === 'development';

const log = {
    request: (config: InternalAxiosRequestConfig) => {
        if (!DEBUG_MODE) return;
        console.log(`🌐 ${config.method?.toUpperCase()} ${config.url}`);
    },
    response: (response: AxiosResponse) => {
        if (!DEBUG_MODE) return;
        console.log(`✅ ${response.status} ${response.config.url}`);
    },
    error: (error: AxiosError) => {
        console.error(`❌ ${error.response?.status || 'ERR'} ${error.config?.url}:`, error.message);
    }
};

export const api = axios.create({
    baseURL: '/api/py',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000,
});

// --- PERFORMANCE OPTIMIZATION: TOKEN CACHING ---
let cachedToken: string | null = null;
let tokenExpiryTime: number = 0; // Timestamp in ms

/**
 * Request interceptor with token caching
 * 
 * Only fetches new session from Supabase when:
 * 1. No cached token exists
 * 2. Token is within 5 minutes of expiring
 */
api.interceptors.request.use(
    async (config) => {
        const now = Date.now();
        const buffer = 5 * 60 * 1000; // 5 minutes before expiry

        // Check if cached token is still valid
        if (cachedToken && now < tokenExpiryTime - buffer) {
            config.headers.Authorization = `Bearer ${cachedToken}`;
            log.request(config);
            return config;
        }

        // Token missing or expiring soon: fetch fresh session
        try {
            const { data: { session } } = await supabase.auth.getSession();

            if (session?.access_token) {
                cachedToken = session.access_token;
                // Set expiry based on session (default to 1 hour if missing)
                const expiresIn = session.expires_in || 3600;
                tokenExpiryTime = now + (expiresIn * 1000);

                config.headers.Authorization = `Bearer ${session.access_token}`;

                if (DEBUG_MODE) {
                    console.log('🔑 Token refreshed, expires in:', Math.round(expiresIn / 60), 'minutes');
                }
            }
        } catch (error) {
            console.error('❌ Auth error:', error);
        }

        log.request(config);
        return config;
    },
    (error) => Promise.reject(error)
);

/**
 * Response interceptor for logging and token invalidation
 */
api.interceptors.response.use(
    (response) => {
        log.response(response);
        return response;
    },
    async (error: AxiosError) => {
        log.error(error);

        // If 401 Unauthorized, clear cached token so next request refreshes
        if (error.response?.status === 401) {
            cachedToken = null;
            tokenExpiryTime = 0;
            if (DEBUG_MODE) {
                console.log('🔑 Token invalidated due to 401');
            }
        }

        return Promise.reject(error);
    }
);

// Legacy export alias
export const authFetch = api;

/**
 * Clear cached token (call on logout)
 */
export const clearAuthCache = () => {
    cachedToken = null;
    tokenExpiryTime = 0;
};
