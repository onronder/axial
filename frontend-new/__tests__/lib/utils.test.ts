import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
    cn,
    getGoogleRedirectUri,
    getGoogleClientId,
    getNotionRedirectUri,
    getNotionClientId,
    getMicrosoftRedirectUri,
    getMicrosoftClientId,
    getMicrosoftTenantId,
    getGitHubClientId,
    getGitHubRedirectUri,
    getDropboxClientId,
    getDropboxRedirectUri,
    getBoxClientId,
    getBoxRedirectUri,
    generatePkcePair,
} from '@/lib/utils';

// =============================================================================
// cn (class name merge) Tests
// =============================================================================

describe('cn', () => {
    it('merges multiple class names', () => {
        expect(cn('class1', 'class2')).toBe('class1 class2');
    });

    it('handles conditional classes', () => {
        expect(cn('base', true && 'conditional')).toBe('base conditional');
        expect(cn('base', false && 'hidden')).toBe('base');
    });

    it('merges tailwind classes correctly', () => {
        // twMerge should handle conflicting tailwind classes
        expect(cn('p-4', 'p-8')).toBe('p-8');
        expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
    });

    it('handles array of classes', () => {
        expect(cn(['class1', 'class2'])).toBe('class1 class2');
    });

    it('handles undefined and null', () => {
        expect(cn('base', undefined, null, 'end')).toBe('base end');
    });

    it('handles empty string', () => {
        expect(cn('base', '', 'end')).toBe('base end');
    });

    it('handles object syntax', () => {
        expect(cn({ active: true, disabled: false })).toBe('active');
    });
});

describe('utils', () => {
    const globalAny = global as any;
    const originalWindow = globalAny.window as Window | undefined;
    const originalGoogleRedirect = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI;
    const originalNotionRedirect = process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI;
    const originalGoogleClient = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const originalNotionClient = process.env.NEXT_PUBLIC_NOTION_CLIENT_ID;
    const originalMicrosoftRedirect = process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI;
    const originalMicrosoftClient = process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID;
    const originalMicrosoftTenant = process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID;
    const originalGitHubClient = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID;

    beforeEach(() => {
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID = '';
        process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID = '';
    });

    afterEach(() => {
        globalAny.window = originalWindow;
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = originalGoogleRedirect;
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = originalNotionRedirect;
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = originalGoogleClient;
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = originalNotionClient;
        process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI = originalMicrosoftRedirect;
        process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID = originalMicrosoftClient;
        process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID = originalMicrosoftTenant;
        process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID = originalGitHubClient;
    });

    it('returns undefined when window is not available', () => {
        globalAny.window = undefined;

        expect(getGoogleRedirectUri()).toBeUndefined();
        expect(getNotionRedirectUri()).toBeUndefined();
        expect(getMicrosoftRedirectUri()).toBeUndefined();
    });

    it('returns env redirect URIs when provided', () => {
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = 'https://example.com/google';
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = 'https://example.com/notion';
        process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI = 'https://example.com/microsoft';

        expect(getGoogleRedirectUri()).toBe('https://example.com/google');
        expect(getNotionRedirectUri()).toBe('https://example.com/notion');
        expect(getMicrosoftRedirectUri()).toBe('https://example.com/microsoft');
    });

    it('builds redirect URI from window origin when env is missing', () => {
        const originalLocation = window.location;
        Object.defineProperty(window, 'location', {
            value: { origin: 'https://axiohub.io' },
            configurable: true,
        });

        expect(getGoogleRedirectUri()).toBe('https://axiohub.io/oauth/callback');
        expect(getNotionRedirectUri()).toBe('https://axiohub.io/oauth/callback');
        expect(getMicrosoftRedirectUri()).toBe('https://axiohub.io/oauth/callback');

        Object.defineProperty(window, 'location', {
            value: originalLocation,
            configurable: true,
        });
    });

    it('returns client IDs from env', () => {
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'google-client';
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = 'notion-client';
        process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID = 'microsoft-client';

        expect(getGoogleClientId()).toBe('google-client');
        expect(getNotionClientId()).toBe('notion-client');
        expect(getMicrosoftClientId()).toBe('microsoft-client');
    });

    it('returns microsoft tenant id from env or common', () => {
        expect(getMicrosoftTenantId()).toBe('common');
        process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID = 'tenant-123';
        expect(getMicrosoftTenantId()).toBe('tenant-123');
    });

    // =========================================================================
    // GitHub OAuth Tests
    // =========================================================================

    describe('GitHub OAuth', () => {
        it('returns GitHub client ID from env', () => {
            process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID = 'github-client-id-123';
            expect(getGitHubClientId()).toBe('github-client-id-123');
        });

        it('returns undefined for GitHub client ID when not set', () => {
            process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID = '';
            expect(getGitHubClientId()).toBeFalsy();
        });

        it('returns undefined for GitHub redirect URI when window is not available', () => {
            globalAny.window = undefined;
            expect(getGitHubRedirectUri()).toBeUndefined();
        });

        it('builds GitHub redirect URI from window origin', () => {
            const originalLocation = window.location;
            Object.defineProperty(window, 'location', {
                value: { origin: 'https://app.axiohub.io' },
                configurable: true,
            });

            expect(getGitHubRedirectUri()).toBe('https://app.axiohub.io/oauth/callback');

            Object.defineProperty(window, 'location', {
                value: originalLocation,
                configurable: true,
            });
        });

        it('includes GitHub redirect URI in window undefined check', () => {
            globalAny.window = undefined;

            expect(getGoogleRedirectUri()).toBeUndefined();
            expect(getNotionRedirectUri()).toBeUndefined();
            expect(getMicrosoftRedirectUri()).toBeUndefined();
            expect(getGitHubRedirectUri()).toBeUndefined();
        });
    });

    // =========================================================================
    // Dropbox OAuth Tests
    // =========================================================================

    describe('Dropbox OAuth', () => {
        const originalDropboxClient = process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID;

        beforeEach(() => {
            process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID = '';
        });

        afterEach(() => {
            process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID = originalDropboxClient;
        });

        it('returns Dropbox client ID from env', () => {
            process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID = 'dropbox-client-id-123';
            expect(getDropboxClientId()).toBe('dropbox-client-id-123');
        });

        it('returns undefined for Dropbox client ID when not set', () => {
            process.env.NEXT_PUBLIC_DROPBOX_CLIENT_ID = '';
            expect(getDropboxClientId()).toBeFalsy();
        });

        it('returns undefined for Dropbox redirect URI when window is not available', () => {
            globalAny.window = undefined;
            expect(getDropboxRedirectUri()).toBeUndefined();
        });

        it('builds Dropbox redirect URI from window origin', () => {
            const originalLocation = window.location;
            Object.defineProperty(window, 'location', {
                value: { origin: 'https://app.axiohub.io' },
                configurable: true,
            });

            expect(getDropboxRedirectUri()).toBe('https://app.axiohub.io/oauth/callback');

            Object.defineProperty(window, 'location', {
                value: originalLocation,
                configurable: true,
            });
        });
    });

    // =========================================================================
    // Box OAuth Tests
    // =========================================================================

    describe('Box OAuth', () => {
        const originalBoxClient = process.env.NEXT_PUBLIC_BOX_CLIENT_ID;

        beforeEach(() => {
            process.env.NEXT_PUBLIC_BOX_CLIENT_ID = '';
        });

        afterEach(() => {
            process.env.NEXT_PUBLIC_BOX_CLIENT_ID = originalBoxClient;
        });

        it('returns Box client ID from env', () => {
            process.env.NEXT_PUBLIC_BOX_CLIENT_ID = 'box-client-id-123';
            expect(getBoxClientId()).toBe('box-client-id-123');
        });

        it('returns undefined for Box client ID when not set', () => {
            process.env.NEXT_PUBLIC_BOX_CLIENT_ID = '';
            expect(getBoxClientId()).toBeFalsy();
        });

        it('returns undefined for Box redirect URI when window is not available', () => {
            globalAny.window = undefined;
            expect(getBoxRedirectUri()).toBeUndefined();
        });

        it('builds Box redirect URI from window origin', () => {
            const originalLocation = window.location;
            Object.defineProperty(window, 'location', {
                value: { origin: 'https://app.axiohub.io' },
                configurable: true,
            });

            expect(getBoxRedirectUri()).toBe('https://app.axiohub.io/oauth/callback');

            Object.defineProperty(window, 'location', {
                value: originalLocation,
                configurable: true,
            });
        });
    });

    // =========================================================================
    // PKCE Generation Tests
    // =========================================================================

    describe('generatePkcePair', () => {
        it('generates valid PKCE pair', async () => {
            const { codeVerifier, codeChallenge } = await generatePkcePair();

            // Code verifier should be base64url encoded 32 bytes
            expect(codeVerifier).toBeDefined();
            expect(typeof codeVerifier).toBe('string');
            expect(codeVerifier.length).toBeGreaterThan(30); // ~43 chars for 32 bytes

            // Code challenge should be base64url encoded SHA-256 hash
            expect(codeChallenge).toBeDefined();
            expect(typeof codeChallenge).toBe('string');
            expect(codeChallenge.length).toBeGreaterThan(30); // ~43 chars for 32 bytes hash
        });

        it('generates different values on each call', async () => {
            const pair1 = await generatePkcePair();
            const pair2 = await generatePkcePair();

            expect(pair1.codeVerifier).not.toBe(pair2.codeVerifier);
            expect(pair1.codeChallenge).not.toBe(pair2.codeChallenge);
        });

        it('generates base64url-safe characters only', async () => {
            const { codeVerifier, codeChallenge } = await generatePkcePair();

            // Base64url should not contain +, /, or = padding
            const base64UrlRegex = /^[A-Za-z0-9_-]+$/;
            expect(codeVerifier).toMatch(base64UrlRegex);
            expect(codeChallenge).toMatch(base64UrlRegex);
        });

        it('throws error when crypto API is not available', async () => {
            const originalCrypto = globalAny.window?.crypto;
            
            // Mock window with no crypto.subtle
            Object.defineProperty(globalAny, 'window', {
                value: { crypto: {} },
                configurable: true,
            });

            await expect(generatePkcePair()).rejects.toThrow('Crypto API not available for PKCE');

            // Restore
            if (originalCrypto) {
                Object.defineProperty(globalAny.window, 'crypto', {
                    value: originalCrypto,
                    configurable: true,
                });
            }
        });
    });
});
