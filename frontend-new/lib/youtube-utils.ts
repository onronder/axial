/**
 * YouTube URL Utilities - Single Source of Truth
 * 
 * This module provides all YouTube URL validation, normalization, and parsing utilities.
 * Used by YoutubeInput, IngestModal, and any other component that handles YouTube URLs.
 */

// =============================================================================
// Constants
// =============================================================================

/**
 * Comprehensive YouTube URL validation regex patterns.
 * Supports:
 * - Standard watch URLs: youtube.com/watch?v=VIDEO_ID
 * - Short URLs: youtu.be/VIDEO_ID
 * - Embed URLs: youtube.com/embed/VIDEO_ID
 * - v/ URLs: youtube.com/v/VIDEO_ID (legacy)
 * - Shorts: youtube.com/shorts/VIDEO_ID
 * - With or without www prefix
 * - With or without https:// prefix
 * - With additional query parameters (e.g., &t=120 for timestamp)
 */
export const YOUTUBE_URL_PATTERNS = [
    // Standard watch URL
    /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]{11}/i,
    // Short URL
    /^(https?:\/\/)?(www\.)?youtu\.be\/[\w-]{11}/i,
    // Embed URL
    /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[\w-]{11}/i,
    // v/ URL (legacy)
    /^(https?:\/\/)?(www\.)?youtube\.com\/v\/[\w-]{11}/i,
    // Shorts URL
    /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]{11}/i,
] as const;

// =============================================================================
// Validation
// =============================================================================

/**
 * Validates if a given URL is a valid YouTube video URL.
 * 
 * @param url - The URL to validate
 * @returns true if the URL is a valid YouTube video URL
 * 
 * @example
 * isValidYoutubeUrl("https://youtube.com/watch?v=dQw4w9WgXcQ") // true
 * isValidYoutubeUrl("https://youtu.be/dQw4w9WgXcQ") // true
 * isValidYoutubeUrl("https://example.com") // false
 */
export function isValidYoutubeUrl(url: string): boolean {
    const trimmedUrl = url.trim();
    if (!trimmedUrl) return false;
    return YOUTUBE_URL_PATTERNS.some((pattern) => pattern.test(trimmedUrl));
}

// =============================================================================
// Normalization
// =============================================================================

/**
 * Normalizes a YouTube URL to ensure it has proper HTTPS protocol.
 * 
 * @param url - The YouTube URL to normalize
 * @returns Normalized URL with https:// prefix
 * 
 * @example
 * normalizeYoutubeUrl("youtube.com/watch?v=abc123") // "https://youtube.com/watch?v=abc123"
 * normalizeYoutubeUrl("http://youtube.com/watch?v=abc123") // "https://youtube.com/watch?v=abc123"
 */
export function normalizeYoutubeUrl(url: string): string {
    const trimmedUrl = url.trim();
    
    // Add https:// if missing
    if (!trimmedUrl.startsWith('http://') && !trimmedUrl.startsWith('https://')) {
        return `https://${trimmedUrl}`;
    }
    
    // Convert http to https
    if (trimmedUrl.startsWith('http://')) {
        return trimmedUrl.replace('http://', 'https://');
    }
    
    return trimmedUrl;
}

// =============================================================================
// Parsing
// =============================================================================

/**
 * Extracts the video ID from a YouTube URL.
 * 
 * @param url - The YouTube URL
 * @returns The 11-character video ID or null if not found
 * 
 * @example
 * extractYoutubeVideoId("https://youtube.com/watch?v=dQw4w9WgXcQ") // "dQw4w9WgXcQ"
 * extractYoutubeVideoId("https://youtu.be/dQw4w9WgXcQ") // "dQw4w9WgXcQ"
 * extractYoutubeVideoId("invalid-url") // null
 */
export function extractYoutubeVideoId(url: string): string | null {
    const trimmedUrl = url.trim();
    
    // Try to extract from watch URL (?v= parameter)
    const watchMatch = trimmedUrl.match(/[?&]v=([\w-]{11})/);
    if (watchMatch) return watchMatch[1];
    
    // Try to extract from short URL, embed, v/, or shorts path
    const pathMatch = trimmedUrl.match(/(?:youtu\.be\/|embed\/|v\/|shorts\/)([\w-]{11})/);
    if (pathMatch) return pathMatch[1];
    
    return null;
}

// =============================================================================
// Error Messages
// =============================================================================

export const YOUTUBE_ERROR_MESSAGES = {
    INVALID_URL: "Please enter a valid YouTube video URL",
    INVALID_URL_DETAILED: "Please enter a valid YouTube video URL (e.g., youtube.com/watch?v=... or youtu.be/...)",
    EMPTY_URL: "Please enter a YouTube video URL",
} as const;
