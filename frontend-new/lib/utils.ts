/**
 * Utility Functions Library
 * 
 * Core utility functions used throughout the Axio frontend application.
 * Includes class name merging, OAuth helpers, and cryptographic utilities.
 * 
 * @module lib/utils
 */

import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

// =============================================================================
// Class Name Utilities
// =============================================================================

/**
 * Merges class names using clsx and tailwind-merge.
 * Handles conditional classes and resolves Tailwind CSS conflicts intelligently.
 * 
 * This is the primary utility for combining class names in React components.
 * It supports:
 * - String class names
 * - Arrays of class names
 * - Conditional objects ({ 'class-name': condition })
 * - Nested combinations of the above
 * 
 * Tailwind-merge ensures that conflicting utilities are resolved correctly,
 * so `cn('px-2', 'px-4')` returns 'px-4' (later wins).
 * 
 * @param inputs - Class names, arrays, or conditional objects to merge
 * @returns Merged and deduplicated class string with Tailwind conflicts resolved
 * 
 * @example
 * ```tsx
 * // Basic usage
 * cn('px-2 py-1', 'px-4') // Returns 'py-1 px-4'
 * 
 * // Conditional classes
 * cn('base-class', isActive && 'active-class', !isActive && 'inactive-class')
 * 
 * // Object syntax
 * cn({ 'bg-primary': isPrimary, 'bg-secondary': !isPrimary })
 * 
 * // Mixed usage in components
 * <div className={cn(
 *   'rounded-lg border',
 *   variant === 'primary' && 'bg-primary text-primary-foreground',
 *   variant === 'secondary' && 'bg-secondary text-secondary-foreground',
 *   className
 * )} />
 * ```
 */
export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

// =============================================================================
// OAuth Configuration Helpers
// =============================================================================

/**
 * Get the Google OAuth redirect URI.
 * Centralized helper to ensure consistent redirect URI across the app.
 * 
 * Priority: Environment variable > Auto-detected window origin
 * 
 * @returns Google OAuth redirect URI or undefined if not in browser
 * 
 * @example
 * ```ts
 * const redirectUri = getGoogleRedirectUri();
 * // Returns "https://app.example.com/oauth/callback" or undefined (SSR)
 * ```
 */
export function getGoogleRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

/**
 * Get the Google Client ID from environment.
 * 
 * @returns Google OAuth client ID or undefined if not configured
 */
export function getGoogleClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
}

/**
 * Get the Notion OAuth redirect URI.
 * Uses the same callback page as Google OAuth.
 * 
 * @returns Notion OAuth redirect URI or undefined if not in browser
 */
export function getNotionRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

/**
 * Get the Notion Client ID from environment.
 * 
 * @returns Notion OAuth client ID or undefined if not configured
 */
export function getNotionClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_NOTION_CLIENT_ID;
}

/**
 * Get the Microsoft OAuth redirect URI.
 * Used for OneDrive and SharePoint integrations.
 * 
 * @returns Microsoft OAuth redirect URI or undefined if not in browser
 */
export function getMicrosoftRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

/**
 * Get the Microsoft tenant for OAuth authorization.
 * Defaults to "common" for multi-tenant apps that accept personal
 * and organizational accounts.
 * 
 * @returns Microsoft tenant ID (defaults to "common")
 * 
 * @example
 * ```ts
 * const tenant = getMicrosoftTenantId();
 * const authUrl = `https://login.microsoftonline.com/${tenant}/oauth2/v2.0/authorize`;
 * ```
 */
export function getMicrosoftTenantId(): string {
    return process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID || "common";
}

/**
 * Get the Microsoft Client ID from environment.
 * Used for OneDrive and SharePoint OAuth flows.
 * 
 * @returns Microsoft OAuth client ID or undefined if not configured
 */
export function getMicrosoftClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID;
}

/**
 * Get the Dropbox Client ID from environment.
 * 
 * @returns Dropbox OAuth client ID or undefined if not configured
 */
export function getDropboxClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID;
}

/**
 * Get the Dropbox OAuth redirect URI.
 * Uses the same OAuth callback page as other providers.
 * 
 * @returns Dropbox OAuth redirect URI or undefined if not in browser
 */
export function getDropboxRedirectUri(): string | undefined {
    if (typeof window === "undefined") return undefined;
    return `${window.location.origin}/oauth/callback`;
}

/**
 * Get the GitHub Client ID from environment.
 * 
 * @returns GitHub OAuth client ID or undefined if not configured
 */
export function getGitHubClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
}

/**
 * Get the GitHub OAuth redirect URI.
 * Uses the same OAuth callback page as other providers.
 * 
 * @returns GitHub OAuth redirect URI or undefined if not in browser
 */
export function getGitHubRedirectUri(): string | undefined {
    if (typeof window === "undefined") return undefined;
    return `${window.location.origin}/oauth/callback`;
}

/**
 * Get the Box Client ID from environment.
 * 
 * @returns Box OAuth client ID or undefined if not configured
 */
export function getBoxClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_BOX_CLIENT_ID;
}

/**
 * Get the Box OAuth redirect URI.
 * Uses the same OAuth callback page as other providers.
 * 
 * @returns Box OAuth redirect URI or undefined if not in browser
 */
export function getBoxRedirectUri(): string | undefined {
    if (typeof window === "undefined") return undefined;
    return `${window.location.origin}/oauth/callback`;
}

// =============================================================================
// Cryptographic Utilities (PKCE)
// =============================================================================

/**
 * Encodes a Uint8Array to a URL-safe base64 string.
 * Removes padding and replaces non-URL-safe characters per RFC 4648.
 * 
 * Used internally for PKCE code challenge generation.
 * 
 * @param bytes - Byte array to encode
 * @returns URL-safe base64 encoded string (no padding)
 * 
 * @internal
 */
function base64UrlEncode(bytes: Uint8Array): string {
    let binary = '';
    bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
    });
    return btoa(binary)
        .replace(/\+/g, '-')  // Replace + with -
        .replace(/\//g, '_')  // Replace / with _
        .replace(/=+$/, '');  // Remove padding
}

/**
 * Computes SHA-256 hash of a string using Web Crypto API.
 * 
 * Used internally for PKCE code challenge generation.
 * 
 * @param value - String to hash
 * @returns SHA-256 hash as Uint8Array
 * 
 * @internal
 */
async function sha256(value: string): Promise<Uint8Array> {
    const encoder = new TextEncoder();
    const data = encoder.encode(value);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return new Uint8Array(hash);
}

/**
 * Generates a PKCE (Proof Key for Code Exchange) code verifier and challenge pair.
 * Used for secure OAuth 2.0 authorization flows to prevent authorization code
 * interception attacks.
 * 
 * PKCE Flow:
 * 1. Generate verifier and challenge using this function
 * 2. Store verifier in session/localStorage
 * 3. Send challenge with authorization request
 * 4. Send verifier with token exchange request
 * 
 * @returns Object containing codeVerifier and codeChallenge strings
 * @throws {Error} If Web Crypto API is not available (e.g., during SSR)
 * 
 * @example
 * ```ts
 * // During OAuth initiation
 * const { codeVerifier, codeChallenge } = await generatePkcePair();
 * sessionStorage.setItem('pkce_verifier', codeVerifier);
 * 
 * const authUrl = new URL('https://provider.com/authorize');
 * authUrl.searchParams.set('code_challenge', codeChallenge);
 * authUrl.searchParams.set('code_challenge_method', 'S256');
 * window.location.href = authUrl.toString();
 * 
 * // During callback/token exchange
 * const verifier = sessionStorage.getItem('pkce_verifier');
 * await exchangeCodeForToken(code, verifier);
 * ```
 * 
 * @see https://datatracker.ietf.org/doc/html/rfc7636 - PKCE RFC
 */
export async function generatePkcePair(): Promise<{ codeVerifier: string; codeChallenge: string }> {
    if (typeof window === 'undefined' || !window.crypto?.subtle) {
        throw new Error('Crypto API not available for PKCE');
    }
    
    // Generate 32 random bytes (256 bits of entropy)
    const randomBytes = new Uint8Array(32);
    window.crypto.getRandomValues(randomBytes);
    
    // Encode as URL-safe base64 for the verifier
    const codeVerifier = base64UrlEncode(randomBytes);
    
    // Generate challenge by hashing the verifier with SHA-256
    const challengeBytes = await sha256(codeVerifier);
    const codeChallenge = base64UrlEncode(challengeBytes);
    
    return { codeVerifier, codeChallenge };
}

// =============================================================================
// String Utilities
// =============================================================================

/**
 * Truncates a string to a maximum length with an ellipsis.
 * Returns the original string if it's shorter than maxLength.
 * 
 * @param str - String to truncate
 * @param maxLength - Maximum length including ellipsis (minimum 4)
 * @returns Truncated string with "..." suffix if truncated
 * 
 * @example
 * ```ts
 * truncate('Hello World', 8)  // Returns "Hello..."
 * truncate('Hi', 8)           // Returns "Hi"
 * truncate('', 8)             // Returns ""
 * ```
 */
export function truncate(str: string, maxLength: number): string {
    if (!str || str.length <= maxLength) return str;
    if (maxLength < 4) return str.slice(0, maxLength);
    return str.slice(0, maxLength - 3) + '...';
}

/**
 * Formats a file size in bytes to a human-readable string.
 * Automatically selects the appropriate unit (Bytes, KB, MB, GB, TB, PB).
 * 
 * @param bytes - File size in bytes
 * @param decimals - Number of decimal places (default: 2)
 * @returns Formatted string with appropriate unit
 * 
 * @example
 * ```ts
 * formatBytes(0)          // Returns "0 Bytes"
 * formatBytes(1024)       // Returns "1 KB"
 * formatBytes(1234567)    // Returns "1.18 MB"
 * formatBytes(1073741824) // Returns "1 GB"
 * formatBytes(500, 0)     // Returns "500 Bytes"
 * ```
 */
export function formatBytes(bytes: number, decimals: number = 2): string {
    if (bytes === 0) return '0 Bytes';
    if (bytes < 0) return 'Invalid size';

    const k = 1024;
    const dm = Math.max(0, decimals);
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB'];

    const i = Math.floor(Math.log(bytes) / Math.log(k));
    const index = Math.min(i, sizes.length - 1);

    return `${parseFloat((bytes / Math.pow(k, index)).toFixed(dm))} ${sizes[index]}`;
}

/**
 * Debounces a function call by delaying execution until after
 * a specified wait time has elapsed since the last call.
 * 
 * Useful for rate-limiting expensive operations like API calls
 * triggered by user input (search fields, form validation, etc.).
 * 
 * @param func - Function to debounce
 * @param wait - Milliseconds to wait before executing
 * @returns Debounced function with cancel method
 * 
 * @example
 * ```ts
 * // Basic usage
 * const debouncedSearch = debounce((query: string) => {
 *   fetchResults(query);
 * }, 300);
 * 
 * // In an input handler - only the last call within 300ms executes
 * <input onChange={(e) => debouncedSearch(e.target.value)} />
 * 
 * // Cancel pending execution
 * debouncedSearch.cancel();
 * ```
 */
export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
    func: T,
    wait: number
): ((...args: Parameters<T>) => void) & { cancel: () => void } {
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const debouncedFn = (...args: Parameters<T>) => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func(...args);
            timeoutId = null;
        }, wait);
    };

    debouncedFn.cancel = () => {
        if (timeoutId) {
            clearTimeout(timeoutId);
            timeoutId = null;
        }
    };

    return debouncedFn;
}

/**
 * Throttles a function call to execute at most once per specified interval.
 * Unlike debounce, throttle guarantees execution at regular intervals
 * during continuous calls.
 * 
 * Useful for rate-limiting frequent events like scroll, resize, or mousemove.
 * 
 * @param func - Function to throttle
 * @param limit - Minimum milliseconds between executions
 * @returns Throttled function
 * 
 * @example
 * ```ts
 * const throttledScroll = throttle(() => {
 *   console.log('Scroll position:', window.scrollY);
 * }, 100);
 * 
 * window.addEventListener('scroll', throttledScroll);
 * ```
 */
export function throttle<T extends (...args: Parameters<T>) => ReturnType<T>>(
    func: T,
    limit: number
): (...args: Parameters<T>) => void {
    let lastRun = 0;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    return (...args: Parameters<T>) => {
        const now = Date.now();

        if (now - lastRun >= limit) {
            func(...args);
            lastRun = now;
        } else if (!timeoutId) {
            timeoutId = setTimeout(() => {
                func(...args);
                lastRun = Date.now();
                timeoutId = null;
            }, limit - (now - lastRun));
        }
    };
}

/**
 * Capitalizes the first letter of a string.
 * 
 * @param str - String to capitalize
 * @returns String with first letter capitalized
 * 
 * @example
 * ```ts
 * capitalize('hello')  // Returns "Hello"
 * capitalize('HELLO')  // Returns "HELLO"
 * capitalize('')       // Returns ""
 * ```
 */
export function capitalize(str: string): string {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Converts a string to title case (capitalizes first letter of each word).
 * 
 * @param str - String to convert
 * @returns Title-cased string
 * 
 * @example
 * ```ts
 * toTitleCase('hello world')     // Returns "Hello World"
 * toTitleCase('HELLO WORLD')     // Returns "Hello World"
 * toTitleCase('hello-world')     // Returns "Hello-World"
 * ```
 */
export function toTitleCase(str: string): string {
    if (!str) return str;
    return str.replace(
        /\w\S*/g,
        (txt) => txt.charAt(0).toUpperCase() + txt.slice(1).toLowerCase()
    );
}
