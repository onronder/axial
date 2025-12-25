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
