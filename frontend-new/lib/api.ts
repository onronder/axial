/**
 * Axios API Client with Supabase JWT Interceptor
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

/**
 * Request interceptor to inject Authorization header
 */
api.interceptors.request.use(
    async (config) => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            const token = session?.access_token;

            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }

            log.request(config);
        } catch (error) {
            console.error('❌ Auth error:', error);
        }

        return config;
    },
    (error) => Promise.reject(error)
);

/**
 * Response interceptor for logging
 */
api.interceptors.response.use(
    (response) => {
        log.response(response);
        return response;
    },
    async (error: AxiosError) => {
        log.error(error);
        return Promise.reject(error);
    }
);

export const authFetch = api;
