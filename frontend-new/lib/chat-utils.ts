/**
 * Chat-related utility functions
 * 
 * Includes Universal Context support for HTTP 300 clarification handling.
 */

import { supabase } from '@/lib/supabase';
import { ModelId } from '@/lib/types';
import type { ClarificationResponse, ScopeContext } from '@/types';

export type ApiErrorDetail = {
    error?: string;
    message?: string;
    details?: unknown;
};

export class ChatApiError extends Error {
    status: number;
    code?: string;
    details?: unknown;

    constructor(status: number, payload: ApiErrorDetail) {
        super(payload.message || 'Chat request failed');
        this.name = 'ChatApiError';
        this.status = status;
        this.code = payload.error;
        this.details = payload.details;
    }
}

const parseErrorDetail = async (response: Response): Promise<ApiErrorDetail> => {
    try {
        const data = await response.json();
        const detail = (data as { detail?: unknown }).detail ?? data;
        if (typeof detail === 'string') {
            return { message: detail };
        }
        if (detail && typeof detail === 'object') {
            return detail as ApiErrorDetail;
        }
        return { message: response.statusText || 'Request failed' };
    } catch {
        return { message: response.statusText || 'Request failed' };
    }
};

export const isChatApiError = (error: unknown): error is ChatApiError =>
    error instanceof ChatApiError;

/**
 * Generate a smart, concise title from the user's first message.
 * Similar to how Claude, Gemini, and ChatGPT auto-name conversations.
 */
export function generateSmartTitle(message: string): string {
    let title = message.trim();

    // Remove common question starters for cleaner titles
    const questionPrefixes = [
        /^(what is|what's|what are|whats)\s+/i,
        /^(how do i|how can i|how to)\s+/i,
        /^(can you|could you|would you)\s+/i,
        /^(tell me about|explain|describe)\s+/i,
        /^(i want to|i need to|i'm trying to)\s+/i,
        /^(help me|please help)\s+/i,
        /^(hi,?\s*|hello,?\s*|hey,?\s*)/i,
    ];

    for (const prefix of questionPrefixes) {
        title = title.replace(prefix, '');
    }

    // Capitalize first letter
    title = title.charAt(0).toUpperCase() + title.slice(1);

    // Truncate to reasonable length (max 50 chars)
    if (title.length > 50) {
        const truncated = title.substring(0, 50);
        const lastSpace = truncated.lastIndexOf(' ');
        title = lastSpace > 30 ? truncated.substring(0, lastSpace) + '...' : truncated + '...';
    }

    // Remove trailing punctuation for cleaner look
    title = title.replace(/[?.!,;:]+$/, '');

    // Fallback for empty/short titles
    return title.length < 3 ? 'New conversation' : title;
}

/**
 * Chat request payload with optional scope selection
 */
export interface ChatPayload {
    query: string;
    conversation_id: string | null;
    history: { role: string; content: string }[];
    model: ModelId;
    /** Optional: explicit scope ID to search within (bypasses Dominance Guard) */
    scope_id?: string;
}

/**
 * Stream events from the chat API
 */
export type StreamEvent =
    | { type: 'token'; content: string }
    | { type: 'sources'; sources: unknown[] }
    | { type: 'scope_context'; scope_context: ScopeContext }
    | { type: 'done'; message_id?: string }
    | { type: 'error'; message: string; error?: string; details?: unknown }
    | { type: 'clarification'; data: ClarificationResponse }
    | { type: 'status'; step: string; message: string; details?: Record<string, unknown> };

/**
 * Result from a non-streaming chat request
 */
export interface ChatResult {
    answer: string;
    sources: unknown[];
    conversation_id?: string;
    message_id?: string;
    scope_context?: ScopeContext;
}

/**
 * HTTP 300 clarification result
 */
export interface ClarificationResult {
    requires_clarification: true;
    data: ClarificationResponse;
}

/**
 * Send a non-streaming chat request (for scope-selected retry)
 * Returns either a normal response or clarification request
 */
export async function sendChatRequest(
    payload: ChatPayload
): Promise<ChatResult | ClarificationResult> {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    if (!token) {
        throw new Error("No authentication token found");
    }

    const response = await fetch('/api/py/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ...payload, stream: false }),
    });

    // Handle HTTP 300 Multiple Choices (clarification needed)
    if (response.status === 300) {
        const clarification = await response.json() as ClarificationResponse;
        console.log('🔍 [Chat] Clarification needed:', clarification.candidates.length, 'scopes');
        return {
            requires_clarification: true,
            data: clarification,
        };
    }

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new ChatApiError(response.status, detail);
    }

    return await response.json() as ChatResult;
}

/**
 * Options for stream retry behavior.
 */
export interface StreamOptions {
    /** Maximum number of retry attempts (default: 2) */
    maxRetries?: number;
    /** Base delay between retries in ms (default: 1000) */
    retryDelay?: number;
    /** AbortSignal for cancellation */
    signal?: AbortSignal;
}

/**
 * Error codes that should NOT be retried (user needs to take action).
 */
const NON_RETRYABLE_ERRORS = [
    'PLAN_LIMIT_EXCEEDED',
    'INTEGRATION_AUTH_FAILED',
    'CONNECTOR_UNAVAILABLE',
    'AUTHENTICATION_REQUIRED',
];

/**
 * Stream chat response with automatic retry on transient failures.
 *
 * Retry behavior:
 * - Retries on network errors and server errors (5xx)
 * - Does NOT retry on client errors (4xx) or specific error codes
 * - Exponential backoff between retries
 * - Emits 'status' events for retry progress
 *
 * @param payload - Chat request payload
 * @param options - Retry and cancellation options
 */
export async function* streamChatResponseWithRetry(
    payload: ChatPayload,
    options: StreamOptions = {}
): AsyncGenerator<StreamEvent, void, unknown> {
    const { maxRetries = 2, retryDelay = 1000, signal } = options;
    let attempt = 0;

    while (attempt <= maxRetries) {
        try {
            yield* streamChatResponse(payload, signal);
            return; // Success, exit
        } catch (error) {
            attempt++;

            // Don't retry if aborted or max retries reached
            if (signal?.aborted || attempt > maxRetries) {
                throw error;
            }

            // Don't retry certain error types that require user action
            if (isChatApiError(error)) {
                const code = (error as ChatApiError).code;
                if (code && NON_RETRYABLE_ERRORS.includes(code)) {
                    throw error;
                }
                // Don't retry client errors (4xx) except for specific cases
                if (error.status >= 400 && error.status < 500 && error.status !== 408 && error.status !== 429) {
                    throw error;
                }
            }

            // Wait before retry with exponential backoff
            const delay = retryDelay * Math.pow(2, attempt - 1);
            await new Promise(resolve => setTimeout(resolve, delay));

            // Emit retry status event
            yield {
                type: 'status',
                step: 'retrying',
                message: `Connection issue, retrying... (${attempt}/${maxRetries})`,
            };
        }
    }
}

/**
 * Stream chat response from backend using SSE.
 * Yields tokens as they arrive.
 *
 * Supports cancellation via AbortSignal for:
 * - Concurrent stream prevention (cancel previous when new starts)
 * - Component unmount cleanup
 *
 * NOTE: HTTP 300 (clarification) is not supported in streaming mode.
 * The backend will not stream if clarification is needed.
 */
export async function* streamChatResponse(
    payload: ChatPayload,
    signal?: AbortSignal
): AsyncGenerator<StreamEvent, void, unknown> {
    const { data: { session } } = await supabase.auth.getSession();
    const token = session?.access_token;

    if (!token) {
        throw new Error("No authentication token found");
    }

    // Check if already aborted before starting
    if (signal?.aborted) {
        return;
    }

    const response = await fetch('/api/py/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ...payload, stream: true }),
        signal, // Pass abort signal to fetch
    });

    // Handle HTTP 300 Multiple Choices (clarification needed)
    // Even in streaming mode, backend returns JSON for clarification
    if (response.status === 300) {
        const clarification = await response.json() as ClarificationResponse;
        if (process.env.NODE_ENV !== 'production') {
            console.log('🔍 [Chat] Clarification needed (streaming):', clarification.candidates.length, 'scopes');
        }
        yield { type: 'clarification', data: clarification };
        return;
    }

    if (!response.ok) {
        const detail = await parseErrorDetail(response);
        throw new ChatApiError(response.status, detail);
    }

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
        while (true) {
            // Check abort signal before each read
            if (signal?.aborted) {
                break;
            }

            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || ""; // Keep incomplete chunk

            for (const line of lines) {
                // Check abort signal between processing lines
                if (signal?.aborted) {
                    return;
                }

                if (line.startsWith('data: ')) {
                    const jsonStr = line.slice(6);
                    if (jsonStr.trim() === '[DONE]') continue; // Standard SSE done

                    try {
                        const event = JSON.parse(jsonStr) as StreamEvent;
                        yield event;
                    } catch {
                        if (process.env.NODE_ENV !== 'production') {
                            console.warn("Failed to parse SSE event:", jsonStr);
                        }
                    }
                }
            }
        }
    } finally {
        reader.releaseLock();
    }
}

// =============================================================================
// SCOPE UTILITY FUNCTIONS
// =============================================================================

/**
 * Get icon name for a scope type
 */
export function getScopeIcon(scopeType: string): string {
    const iconMap: Record<string, string> = {
        'github_repo': 'github',
        's3_bucket': 'cloud',
        'box_folder': 'folder',
        'dropbox_folder': 'dropbox',
        'gdrive_folder': 'google-drive',
        'notion_workspace': 'book-open',
        'web_domain': 'globe',
        'file_upload': 'file',
    };
    return iconMap[scopeType] || 'folder';
}

/**
 * Get display name for a scope type
 */
export function getScopeTypeName(scopeType: string): string {
    const nameMap: Record<string, string> = {
        'github_repo': 'GitHub Repository',
        's3_bucket': 'S3 Bucket',
        'box_folder': 'Box Folder',
        'dropbox_folder': 'Dropbox Folder',
        'gdrive_folder': 'Google Drive',
        'notion_workspace': 'Notion Workspace',
        'web_domain': 'Web Domain',
        'file_upload': 'Uploaded Files',
    };
    return nameMap[scopeType] || scopeType;
}

/**
 * Extract readable name from scope ID URI
 */
export function extractScopeName(scopeId: string): string {
    if (!scopeId) return 'Unknown Source';

    try {
        // github://org/repo@branch -> repo
        if (scopeId.startsWith('github://')) {
            const parts = scopeId.replace('github://', '').split('@')[0];
            return parts.includes('/') ? parts.split('/').pop() || parts : parts;
        }

        // s3://bucket/prefix/ -> bucket/prefix
        if (scopeId.startsWith('s3://')) {
            return scopeId.replace('s3://', '').replace(/\/$/, '') || 'S3 Bucket';
        }

        // box://folder/123:Name -> Name
        if (scopeId.startsWith('box://')) {
            return scopeId.includes(':') ? scopeId.split(':').pop() || 'Box Folder' : 'Box Folder';
        }

        // gdrive://drive/folder:Name -> Name
        if (scopeId.startsWith('gdrive://')) {
            return scopeId.includes(':') ? scopeId.split(':').pop() || 'Google Drive' : 'Google Drive';
        }

        // notion://workspace/page:Title -> Title
        if (scopeId.startsWith('notion://')) {
            return scopeId.includes(':') ? scopeId.split(':').pop() || 'Notion' : 'Notion';
        }

        // dropbox://namespace/path -> path
        if (scopeId.startsWith('dropbox://')) {
            const parts = scopeId.replace('dropbox://', '').split('/');
            return parts.length > 1 ? parts.slice(1).join('/') : 'Dropbox';
        }

        // Fallback: return last part
        return scopeId.split('/').pop()?.split(':').pop() || scopeId;
    } catch {
        return scopeId.substring(0, 50);
    }
}
