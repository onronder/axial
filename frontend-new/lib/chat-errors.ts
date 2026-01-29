/**
 * Centralized Chat Error Handling
 *
 * Provides consistent error messages and display formatting for chat-related errors.
 * Maps backend error codes to user-friendly messages.
 *
 * Related files:
 * - lib/chat-utils.ts (ChatApiError class)
 * - app/dashboard/chat/[chatId]/page.tsx (error display)
 */

import { isChatApiError, ChatApiError } from './chat-utils';

// =============================================================================
// ERROR MESSAGE DEFINITIONS
// =============================================================================

export interface ErrorDisplay {
    /** Short title for the error toast/banner */
    title: string;
    /** Longer description explaining the issue */
    description: string;
    /** Whether user action is required to resolve */
    requiresAction?: boolean;
    /** Action button text (if applicable) */
    actionText?: string;
    /** Action route (if applicable) */
    actionRoute?: string;
}

/**
 * Mapping of backend error codes to user-friendly display messages.
 * Keys match the `error` field from backend API responses.
 */
export const CHAT_ERROR_MESSAGES: Record<string, ErrorDisplay> = {
    // LLM/Model errors
    LLM_TIMEOUT: {
        title: 'Response Timeout',
        description: 'The AI took too long to respond. Please try again.',
    },
    LLM_RATE_LIMIT: {
        title: 'Too Many Requests',
        description: 'Please wait a moment before sending another message.',
    },
    LLM_CONTEXT_LENGTH: {
        title: 'Message Too Long',
        description: 'Your conversation history is too long. Try starting a new chat.',
    },

    // Plan/Billing errors
    PLAN_LIMIT_EXCEEDED: {
        title: 'Usage Limit Reached',
        description: "You've reached your plan's message limit. Upgrade to continue.",
        requiresAction: true,
        actionText: 'Upgrade Plan',
        actionRoute: '/dashboard/settings/billing',
    },
    STORAGE_LIMIT_EXCEEDED: {
        title: 'Storage Limit Reached',
        description: "You've reached your plan's storage limit. Upgrade or remove files.",
        requiresAction: true,
        actionText: 'Manage Storage',
        actionRoute: '/dashboard/knowledge-base',
    },

    // Integration/Auth errors
    INTEGRATION_AUTH_FAILED: {
        title: 'Connection Expired',
        description: 'Your data source connection has expired. Please reconnect.',
        requiresAction: true,
        actionText: 'Reconnect',
        actionRoute: '/dashboard/data-sources',
    },
    AUTHENTICATION_REQUIRED: {
        title: 'Session Expired',
        description: 'Please sign in again to continue.',
        requiresAction: true,
        actionText: 'Sign In',
        actionRoute: '/auth/login',
    },

    // Connector/Service errors
    CONNECTOR_UNAVAILABLE: {
        title: 'Service Unavailable',
        description: 'This data source is temporarily unavailable. Try again later.',
    },
    INDEX_NOT_READY: {
        title: 'Knowledge Base Processing',
        description: 'Your documents are still being processed. Please wait.',
    },
    NO_DOCUMENTS: {
        title: 'No Documents Found',
        description: 'Add documents to your knowledge base to start chatting.',
        requiresAction: true,
        actionText: 'Add Documents',
        actionRoute: '/dashboard/knowledge-base',
    },

    // Network errors
    NETWORK_ERROR: {
        title: 'Connection Failed',
        description: 'Unable to connect. Check your internet connection.',
    },
    REQUEST_ABORTED: {
        title: 'Request Cancelled',
        description: 'The request was cancelled.',
    },
};

// =============================================================================
// ERROR DISPLAY FUNCTIONS
// =============================================================================

/**
 * Get user-friendly error display from any error type.
 *
 * @param error - The error to get display for (ChatApiError, Error, or unknown)
 * @returns ErrorDisplay object with title and description
 */
export function getChatErrorDisplay(error: unknown): ErrorDisplay {
    // Handle ChatApiError with known codes
    if (isChatApiError(error)) {
        const chatError = error as ChatApiError;
        const code = chatError.code;

        if (code && CHAT_ERROR_MESSAGES[code]) {
            return CHAT_ERROR_MESSAGES[code];
        }

        // Handle HTTP status codes without specific error codes
        if (chatError.status === 401 || chatError.status === 403) {
            return CHAT_ERROR_MESSAGES.AUTHENTICATION_REQUIRED;
        }
        if (chatError.status === 429) {
            return CHAT_ERROR_MESSAGES.LLM_RATE_LIMIT;
        }
        if (chatError.status >= 500) {
            return {
                title: 'Server Error',
                description: chatError.message || 'Something went wrong on our end. Please try again.',
            };
        }

        // Use message from error if available
        return {
            title: 'Chat Error',
            description: chatError.message || 'An error occurred. Please try again.',
        };
    }

    // Handle AbortError (request cancelled)
    if (error instanceof Error && error.name === 'AbortError') {
        return CHAT_ERROR_MESSAGES.REQUEST_ABORTED;
    }

    // Handle TypeError (usually network issues)
    if (error instanceof TypeError && error.message.includes('fetch')) {
        return CHAT_ERROR_MESSAGES.NETWORK_ERROR;
    }

    // Handle generic Error
    if (error instanceof Error) {
        return {
            title: 'Something went wrong',
            description: error.message || 'An unexpected error occurred. Please try again.',
        };
    }

    // Fallback for unknown error types
    return {
        title: 'Something went wrong',
        description: 'An unexpected error occurred. Please try again.',
    };
}

/**
 * Check if an error requires user action to resolve.
 *
 * @param error - The error to check
 * @returns true if the error requires user action
 */
export function errorRequiresAction(error: unknown): boolean {
    const display = getChatErrorDisplay(error);
    return display.requiresAction === true;
}

/**
 * Get the action route for an error (if applicable).
 *
 * @param error - The error to get action for
 * @returns The route to navigate to, or undefined if no action needed
 */
export function getErrorActionRoute(error: unknown): string | undefined {
    const display = getChatErrorDisplay(error);
    return display.actionRoute;
}
