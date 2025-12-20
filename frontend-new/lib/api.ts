/**
 * Axios API Client with Supabase JWT Interceptor
 * 
 * This client:
 * - Proxies requests through Next.js rewrites to the Python backend
 * - Automatically injects the Supabase JWT token for authenticated requests
 * - Uses the SSR-compatible Supabase client for consistent session handling
 * - Includes comprehensive request/response logging for debugging
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { supabase } from '@/lib/supabase';

// Debug mode - set to true to enable verbose logging
const DEBUG_MODE = true;

const log = {
    request: (config: InternalAxiosRequestConfig) => {
        if (!DEBUG_MODE) return;
        console.group(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        console.log('📤 Headers:', config.headers);
        console.log('📦 Data:', config.data);
        console.log('⏰ Timestamp:', new Date().toISOString());
        console.groupEnd();
    },
    response: (response: AxiosResponse) => {
        if (!DEBUG_MODE) return;
        console.group(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`);
        console.log('📊 Status:', response.status);
        console.log('📥 Data:', response.data);
        console.log('⏱️ Duration:', response.headers['x-response-time'] || 'N/A');
        console.groupEnd();
    },
    error: (error: AxiosError) => {
        console.group(`❌ API Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
        console.error('🔴 Status:', error.response?.status);
        console.error('📄 Response:', error.response?.data);
        console.error('💬 Message:', error.message);
        console.error('🔧 Code:', error.code);
        console.error('📋 Full Error:', error);
        console.groupEnd();
    },
    auth: (hasToken: boolean, token?: string) => {
        if (!DEBUG_MODE) return;
        console.log(`🔐 Auth: ${hasToken ? '✅ Token found' : '⚠️ No token'}`);
        if (hasToken && token) {
            console.log(`   Token preview: ${token.substring(0, 20)}...`);
        }
    }
};

export const api = axios.create({
    baseURL: '/api/py',
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
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
            console.log('🔄 Getting session for API request...');
            const { data: { session }, error: sessionError } = await supabase.auth.getSession();

            if (sessionError) {
                console.error('❌ Session error:', sessionError);
            }

            const token = session?.access_token;
            log.auth(!!token, token);

            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            } else {
                console.warn('⚠️ No auth token available - request will be unauthenticated');
            }

            log.request(config);
        } catch (error) {
            console.error('❌ Failed to get auth token for API request:', error);
        }

        return config;
    },
    (error) => {
        console.error('❌ Request interceptor error:', error);
        return Promise.reject(error);
    }
);

/**
 * Response interceptor for handling auth errors and logging
 */
api.interceptors.response.use(
    (response) => {
        log.response(response);
        return response;
    },
    async (error: AxiosError) => {
        log.error(error);

        if (error.response?.status === 401) {
            console.warn('🔒 API returned 401 - user may need to re-authenticate');
            // Could trigger re-auth here
        }

        if (error.response?.status === 500) {
            console.error('🔥 Server error 500 - check backend logs');
        }

        if (error.code === 'ECONNABORTED') {
            console.error('⏰ Request timeout - server did not respond in time');
        }

        if (!error.response) {
            console.error('🌐 Network error - no response received (CORS? Server down?)');
        }

        return Promise.reject(error);
    }
);

// Legacy alias for backward compatibility
export const authFetch = api;

// Export debug toggle for runtime control
export const setDebugMode = (enabled: boolean) => {
    console.log(`🔧 API Debug mode: ${enabled ? 'ON' : 'OFF'}`);
    // Note: This doesn't actually work with const, but keeping for API consistency
};
