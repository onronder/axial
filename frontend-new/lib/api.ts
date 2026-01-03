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

// =============================================================================
// USAGE & PLAN API
// =============================================================================

import type { UserUsage, EffectivePlan, Team, TeamMember, InviteRequest, BulkInviteResult } from '@/types';

/**
 * Get user usage stats and limits
 * GET /api/v1/usage
 */
export const getUsageStats = async (): Promise<UserUsage> => {
    const response = await api.get<UserUsage>('/usage');
    return response.data;
};

/**
 * Get user's effective plan (may be inherited from team owner)
 * GET /api/v1/team/effective-plan
 */
export const getEffectivePlan = async (): Promise<EffectivePlan> => {
    const response = await api.get<EffectivePlan>('/team/effective-plan');
    return response.data;
};

// =============================================================================
// TEAM API
// =============================================================================

/**
 * Get current user's team
 * GET /api/v1/team
 */
export const getMyTeam = async (): Promise<Team> => {
    const response = await api.get<Team>('/team');
    return response.data;
};

/**
 * Get team members
 * GET /api/v1/team/members
 */
export const getTeamMembers = async (): Promise<TeamMember[]> => {
    const response = await api.get<TeamMember[]>('/team/members');
    return response.data;
};

/**
 * Invite a new team member
 * POST /api/v1/team/invite
 */
export const inviteMember = async (request: InviteRequest): Promise<{ success: boolean; member?: TeamMember }> => {
    const response = await api.post('/team/invite', request);
    return response.data;
};

/**
 * Bulk invite team members from CSV file
 * POST /api/v1/team/bulk-invite
 */
export const bulkInvite = async (file: File): Promise<BulkInviteResult> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<BulkInviteResult>('/team/bulk-invite', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

/**
 * Remove a team member
 * DELETE /api/v1/team/members/{memberId}
 */
export const removeMember = async (memberId: string): Promise<{ success: boolean }> => {
    const response = await api.delete(`/team/members/${memberId}`);
    return response.data;
};

/**
 * Update a team member's role
 * PATCH /api/v1/team/members/{memberId}
 */
export const updateMemberRole = async (memberId: string, role: string): Promise<TeamMember> => {
    const response = await api.patch<TeamMember>(`/team/members/${memberId}`, { role });
    return response.data;
};

// =============================================================================
// PRESIGNED URL UPLOAD API
// =============================================================================

export interface UploadUrlResponse {
    upload_url: string;
    storage_path: string;
    expires_in: number;
}

export interface IngestReferenceResponse {
    status: string;
    doc_id: string;
}

/**
 * Get a presigned URL for direct-to-storage file upload
 * POST /api/v1/ingest/upload-url
 */
export const getUploadUrl = async (
    filename: string,
    fileType: string,
    fileSize: number
): Promise<UploadUrlResponse> => {
    const response = await api.post<UploadUrlResponse>('/ingest/upload-url', {
        filename,
        file_type: fileType,
        file_size: fileSize,
    });
    return response.data;
};

/**
 * Trigger ingestion for an already-uploaded file
 * POST /api/v1/ingest/file/reference
 */
export const ingestFileReference = async (
    storagePath: string,
    filename: string,
    fileSize: number,
    metadata: Record<string, unknown> = {}
): Promise<IngestReferenceResponse> => {
    const response = await api.post<IngestReferenceResponse>('/ingest/file/reference', {
        storage_path: storagePath,
        filename,
        file_size: fileSize,
        metadata,
    });
    return response.data;
};

/**
 * Upload file directly to storage using presigned URL
 * (Uses native fetch, not axios, for binary upload)
 */
export const uploadToStorage = async (
    uploadUrl: string,
    file: File
): Promise<boolean> => {
    const response = await fetch(uploadUrl, {
        method: 'PUT',
        headers: {
            'Content-Type': file.type || 'application/octet-stream',
        },
        body: file,
    });
    return response.ok;
};
