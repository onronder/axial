/**
 * Unified Error Handling Utilities
 *
 * Provides consistent error message extraction across the application.
 * Handles Axios errors, standard errors, and unknown error types.
 */

import { AxiosError, isAxiosError } from 'axios';

/**
 * API error response structure from backend
 */
interface ApiErrorDetail {
    detail?: string | { message?: string };
    message?: string;
    error?: string;
}

/**
 * Extracts a user-friendly error message from various error types.
 *
 * @param error - The error to extract a message from
 * @param fallback - Default message if extraction fails
 * @returns A user-friendly error message string
 *
 * Handles:
 * - Axios errors with various response formats
 * - HTTP status code fallbacks (401, 403, 404, 500)
 * - Standard Error objects
 * - Unknown error types
 */
export function extractErrorMessage(error: unknown, fallback = 'An error occurred'): string {
    // Handle Axios errors
    if (isAxiosError(error)) {
        const axiosError = error as AxiosError<ApiErrorDetail>;
        const data = axiosError.response?.data;

        // Try to extract message from response data
        if (data) {
            // Handle { detail: "message" } format
            if (typeof data.detail === 'string') {
                return data.detail;
            }

            // Handle { detail: { message: "..." } } format
            if (data.detail && typeof data.detail === 'object' && data.detail.message) {
                return data.detail.message;
            }

            // Handle { message: "..." } format
            if (data.message) {
                return data.message;
            }

            // Handle { error: "..." } format
            if (data.error) {
                return data.error;
            }
        }

        // HTTP status code fallbacks
        const status = axiosError.response?.status;
        if (status === 401) {
            return 'Please log in to continue';
        }
        if (status === 403) {
            return 'You do not have permission to perform this action';
        }
        if (status === 404) {
            return 'The requested resource was not found';
        }
        if (status === 402) {
            return 'An active subscription is required';
        }
        if (status === 429) {
            return 'Too many requests. Please try again later';
        }
        if (status && status >= 500) {
            return 'A server error occurred. Please try again later';
        }

        // Fall back to axios error message
        if (axiosError.message) {
            return axiosError.message;
        }
    }

    // Handle standard Error objects
    if (error instanceof Error) {
        return error.message;
    }

    // Handle string errors
    if (typeof error === 'string') {
        return error;
    }

    // Unknown error type
    return fallback;
}

/**
 * Type guard to check if an error is an Axios error with a specific status code
 */
export function isHttpError(error: unknown, status: number): boolean {
    return isAxiosError(error) && error.response?.status === status;
}

/**
 * Check if error is a network/connection error
 */
export function isNetworkError(error: unknown): boolean {
    if (isAxiosError(error)) {
        return !error.response && error.code === 'ERR_NETWORK';
    }
    return false;
}
