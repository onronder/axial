import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import {
    getGoogleRedirectUri,
    getGoogleClientId,
    getNotionRedirectUri,
    getNotionClientId,
} from '@/lib/utils';

describe('utils', () => {
    const originalWindow = global.window;
    const originalGoogleRedirect = process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI;
    const originalNotionRedirect = process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI;
    const originalGoogleClient = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    const originalNotionClient = process.env.NEXT_PUBLIC_NOTION_CLIENT_ID;

    beforeEach(() => {
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = '';
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = '';
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = '';
    });

    afterEach(() => {
        global.window = originalWindow;
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = originalGoogleRedirect;
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = originalNotionRedirect;
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = originalGoogleClient;
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = originalNotionClient;
    });

    it('returns undefined when window is not available', () => {
        global.window = undefined as unknown as Window;

        expect(getGoogleRedirectUri()).toBeUndefined();
        expect(getNotionRedirectUri()).toBeUndefined();
    });

    it('returns env redirect URIs when provided', () => {
        process.env.NEXT_PUBLIC_GOOGLE_REDIRECT_URI = 'https://example.com/google';
        process.env.NEXT_PUBLIC_NOTION_REDIRECT_URI = 'https://example.com/notion';

        expect(getGoogleRedirectUri()).toBe('https://example.com/google');
        expect(getNotionRedirectUri()).toBe('https://example.com/notion');
    });

    it('builds redirect URI from window origin when env is missing', () => {
        const originalLocation = window.location;
        Object.defineProperty(window, 'location', {
            value: { origin: 'https://axiohub.io' },
            configurable: true,
        });

        expect(getGoogleRedirectUri()).toBe('https://axiohub.io/oauth/callback');
        expect(getNotionRedirectUri()).toBe('https://axiohub.io/oauth/callback');

        Object.defineProperty(window, 'location', {
            value: originalLocation,
            configurable: true,
        });
    });

    it('returns client IDs from env', () => {
        process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID = 'google-client';
        process.env.NEXT_PUBLIC_NOTION_CLIENT_ID = 'notion-client';

        expect(getGoogleClientId()).toBe('google-client');
        expect(getNotionClientId()).toBe('notion-client');
    });
});
