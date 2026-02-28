/**
 * Axios API Client with Token Caching
 * 
 * PERFORMANCE OPTIMIZATION: Caches the JWT token in memory and only
 * refreshes when it's close to expiring (5 minute buffer).
 */

import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import axiosRetry from 'axios-retry';
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
        if (!DEBUG_MODE) return;
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

// Retry transient errors with exponential backoff
axiosRetry(api, {
    retries: 3,
    retryDelay: axiosRetry.exponentialDelay,
    retryCondition: (error) =>
        axiosRetry.isNetworkOrIdempotentRequestError(error)
        || [502, 503, 504].includes(error.response?.status ?? 0),
});

// --- PERFORMANCE OPTIMIZATION: TOKEN CACHING ---
let cachedToken: string | null = null;
let tokenExpiryTime: number = 0; // Timestamp in ms
let refreshPromise: Promise<string | null> | null = null;

// Guard to prevent multiple concurrent 401 redirects
let isRedirectingTo401 = false;

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

        // Token missing or expiring soon: fetch fresh session (dedup'd)
        try {
            if (!refreshPromise) {
                refreshPromise = supabase.auth.getSession().then(({ data: { session } }) => {
                    if (session?.access_token) {
                        cachedToken = session.access_token;
                        const expiresIn = session.expires_in || 3600;
                        tokenExpiryTime = Date.now() + (expiresIn * 1000);
                        if (DEBUG_MODE) {
                            console.log('🔑 Token refreshed, expires in:', Math.round(expiresIn / 60), 'minutes');
                        }
                        return session.access_token;
                    }
                    return null;
                }).finally(() => {
                    refreshPromise = null;
                });
            }

            const token = await refreshPromise;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
        } catch (error) {
            if (DEBUG_MODE) {
                console.error('❌ Auth error:', error);
            }
            refreshPromise = null;
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

        // If 403 with TEAM_ACCESS_DENIED, dispatch custom event
        if (error.response?.status === 403) {
            const detail = (error.response.data as Record<string, unknown>)?.detail;
            if (typeof detail === 'object' && detail !== null && (detail as Record<string, unknown>).error === 'TEAM_ACCESS_DENIED') {
                if (typeof window !== 'undefined') {
                    window.dispatchEvent(new CustomEvent('team-access-denied', {
                        detail: { reason: (detail as Record<string, unknown>).reason, message: (detail as Record<string, unknown>).message }
                    }));
                }
            }
        }

        // If 401 Unauthorized, clear cached token and redirect to login
        if (error.response?.status === 401) {
            cachedToken = null;
            tokenExpiryTime = 0;
            if (DEBUG_MODE) {
                console.log('🔑 Token invalidated due to 401');
            }
            if (typeof window !== 'undefined'
                && !isRedirectingTo401
                && !window.location.pathname.startsWith('/login')
                && !window.location.pathname.startsWith('/auth')) {
                isRedirectingTo401 = true;
                const currentPath = window.location.pathname + window.location.search;
                window.location.href = `/login?redirectTo=${encodeURIComponent(currentPath)}`;
            }
        }

        return Promise.reject(error);
    }
);

// Legacy export alias
export const authFetch = api;

/**
 * Extract a user-friendly error message from an API error response.
 * Handles both structured {error, detail, message} and plain string formats.
 */
export function extractErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
    if (error && typeof error === 'object' && 'response' in error) {
        const axiosErr = error as AxiosError<Record<string, unknown>>;
        const data = axiosErr.response?.data;
        if (data) {
            // Structured format: {error: "CODE", detail: "message"} or {error: "CODE", message: "message"}
            if (typeof data.detail === 'string') return data.detail;
            if (typeof data.message === 'string') return data.message;
            // Array format from validation errors: {detail: [{loc: [...], msg: "...", type: "..."}]}
            if (Array.isArray(data.detail) && data.detail.length > 0) {
                const first = data.detail[0];
                if (typeof first === 'object' && first !== null && typeof (first as Record<string, unknown>).msg === 'string') {
                    return (first as Record<string, unknown>).msg as string;
                }
            }
            // Nested structured format: {detail: {error: "CODE", message: "..."}}
            if (typeof data.detail === 'object' && data.detail !== null) {
                const nested = data.detail as Record<string, unknown>;
                if (typeof nested.message === 'string') return nested.message;
                if (typeof nested.detail === 'string') return nested.detail;
            }
        }
        if (axiosErr.message) return axiosErr.message;
    }
    if (error instanceof Error) return error.message;
    return fallback;
}

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

import type { UserUsage, EffectivePlan, Team, TeamMember, InviteRequest, BulkInviteResult, TeamUpdate, SubscriptionCancelResponse, SubscriptionDetail } from '@/types';

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

/**
 * Update team details (name, slug)
 * PATCH /api/v1/team
 */
export const updateTeam = async (data: TeamUpdate): Promise<Team> => {
    const response = await api.patch<Team>('/team', data);
    return response.data;
};

/**
 * Delete the team (owner only)
 * DELETE /api/v1/team
 */
export const deleteTeam = async (): Promise<{ success: boolean; message: string }> => {
    const response = await api.delete('/team');
    return response.data;
};

// =============================================================================
// BILLING API
// =============================================================================

/**
 * Cancel the current subscription
 * Sets cancel_at_period_end=true, access continues until period ends
 * DELETE /api/v1/billing/subscription
 */
export const cancelSubscription = async (): Promise<SubscriptionCancelResponse> => {
    const response = await api.delete<SubscriptionCancelResponse>('/billing/subscription');
    return response.data;
};

/**
 * Get current subscription details
 * GET /api/v1/billing/subscription
 */
export const getCurrentSubscription = async (): Promise<SubscriptionDetail> => {
    const response = await api.get<SubscriptionDetail>('/billing/subscription');
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
    job_id?: string;  // Optional: returned when file is queued for processing
}

// =============================================================================
// DUPLICATE FILE DETECTION API
// =============================================================================

export interface ExistingDocument {
    id: string;
    title: string;
    created_at: string;
    file_size_bytes?: number;
}

export interface DuplicateCheckResponse {
    is_duplicate: boolean;
    existing_document?: ExistingDocument;
    action_required: "none" | "confirm_overwrite";
}

/**
 * Check if a file with the same content already exists
 * POST /api/v1/uploads/check-duplicates
 * 
 * Call this BEFORE uploading to show user a confirmation modal if duplicate exists.
 */
export const checkDuplicates = async (
    contentHash: string,
    filename: string,
    fileSize: number
): Promise<DuplicateCheckResponse> => {
    const response = await api.post<DuplicateCheckResponse>('/uploads/check-duplicates', {
        content_hash: contentHash,
        filename,
        file_size: fileSize,
    });
    return response.data;
};

/**
 * Get a presigned URL for direct-to-storage file upload
 * POST /api/v1/uploads/upload-url
 * 
 * @param contentHash - Optional SHA-256 hash for stable path generation (enables dedup)
 * @param forceOverwrite - Set to true if user confirmed overwrite of duplicate
 */
export const getUploadUrl = async (
    filename: string,
    fileType: string,
    fileSize: number,
    contentHash?: string,
    forceOverwrite: boolean = false
): Promise<UploadUrlResponse> => {
    const response = await api.post<UploadUrlResponse>('/uploads/upload-url', {
        filename,
        file_type: fileType,
        file_size: fileSize,
        content_hash: contentHash,
        force_overwrite: forceOverwrite,
    });
    return response.data;
};

/**
 * Trigger ingestion for an already-uploaded file
 * POST /api/v1/uploads/file/reference
 */
export const ingestFileReference = async (
    storagePath: string,
    filename: string,
    fileSize: number,
    metadata: Record<string, unknown> = {}
): Promise<IngestReferenceResponse> => {
    const response = await api.post<IngestReferenceResponse>('/uploads/file/reference', {
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
