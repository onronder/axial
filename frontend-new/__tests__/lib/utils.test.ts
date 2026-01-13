import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    getGoogleRedirectUri,
    getGoogleClientId,
    getNotionRedirectUri,
    getNotionClientId,
    getMicrosoftRedirectUri,
    getMicrosoftClientId,
    getMicrosoftTenantId,
} from '@/lib/utils';

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

    beforeEach(() => {
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_MICROSOFT_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_MICROSOFT_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_MICROSOFT_TENANT_ID = '';
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
});
