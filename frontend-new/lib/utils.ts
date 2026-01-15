import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

/**
 * Get the Google OAuth redirect URI.
 * Centralized helper to ensure consistent redirect URI across the app.
 * 
 * Priority: Environment variable > Auto-detected window origin
 */
export function getGoogleRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

/**
 * Get the Google Client ID from environment.
 */
export function getGoogleClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
}

/**
 * Get the Notion OAuth redirect URI.
 * Uses the same callback page as Google OAuth.
 */
export function getNotionRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

/**
 * Get the Notion Client ID from environment.
 */
export function getNotionClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_NOTION_CLIENT_ID;
}

/**
 * Get the Microsoft OAuth redirect URI.
 */
export function getMicrosoftRedirectUri(): string | undefined {
    if (typeof window === 'undefined') return undefined;

    const envUri = process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI;
    const autoUri = `${window.location.origin}/oauth/callback`;

    return envUri || autoUri;
}

function base64UrlEncode(bytes: Uint8Array): string {
    let binary = '';
    bytes.forEach((byte) => {
        binary += String.fromCharCode(byte);
    });
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function sha256(value: string): Promise<Uint8Array> {
    const encoder = new TextEncoder();
    const data = encoder.encode(value);
    const hash = await crypto.subtle.digest('SHA-256', data);
    return new Uint8Array(hash);
}

export async function generatePkcePair(): Promise<{ codeVerifier: string; codeChallenge: string }> {
    if (typeof window === 'undefined' || !window.crypto?.subtle) {
        throw new Error('Crypto API not available for PKCE');
    }
    const randomBytes = new Uint8Array(32);
    window.crypto.getRandomValues(randomBytes);
    const codeVerifier = base64UrlEncode(randomBytes);
    const challengeBytes = await sha256(codeVerifier);
    const codeChallenge = base64UrlEncode(challengeBytes);
    return { codeVerifier, codeChallenge };
}

/**
 * Get the Microsoft tenant for OAuth authorization.
 * Defaults to "common" for multi-tenant apps.
 */
export function getMicrosoftTenantId(): string {
    return process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID || "common";
}

/**
 * Get the Microsoft Client ID from environment.
 */
export function getMicrosoftClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID;
}

/**
 * Get the Dropbox Client ID from environment.
 */
export function getDropboxClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID;
}

/**
 * Get the Dropbox OAuth redirect URI.
 * Uses the same OAuth callback page as other providers.
 */
export function getDropboxRedirectUri(): string | undefined {
    if (typeof window === "undefined") return undefined;
    return `${window.location.origin}/oauth/callback`;
}

/**
 * Get the GitHub Client ID from environment.
 */
export function getGitHubClientId(): string | undefined {
    return process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;
}

/**
 * Get the GitHub OAuth redirect URI.
 * Uses the same OAuth callback page as other providers.
 */
export function getGitHubRedirectUri(): string | undefined {
    if (typeof window === "undefined") return undefined;
    return `${window.location.origin}/oauth/callback`;
}
