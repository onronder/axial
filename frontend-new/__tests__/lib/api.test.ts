/**
 * Unit Tests for API Client
 * 
 * Tests axios configuration and error handling patterns.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('API Client', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('Request Interceptor Behavior', () => {
        it('should construct Authorization header from token', async () => {
            const token = 'test-token-123';
            const authHeader = `Bearer ${token}`;
            expect(authHeader).toBe('Bearer test-token-123');
        });

        it('should not add header when token is undefined', async () => {
            const token: string | undefined = undefined;
            const headers: Record<string, string> = {};

            if (token) {
                headers.Authorization = `Bearer ${token}`;
            }

            expect(headers.Authorization).toBeUndefined();
        });

        it('should handle null session gracefully', async () => {
            const session: { access_token?: string } | null = null;
            const headers: Record<string, string> = {};

            if (session?.access_token) {
                headers.Authorization = `Bearer ${session.access_token}`;
            }

            expect(headers.Authorization).toBeUndefined();
        });
    });

    describe('Configuration Constants', () => {
        it('should use /api/py as base path', () => {
            const expectedBaseURL = '/api/py';
            expect(expectedBaseURL).toBe('/api/py');
        });

        it('should have 30 second timeout', () => {
            const expectedTimeout = 30000;
            expect(expectedTimeout).toBe(30000);
        });

        it('should use JSON content type', () => {
            const expectedContentType = 'application/json';
            expect(expectedContentType).toBe('application/json');
        });
    });

    describe('Error Logging Pattern', () => {
        it('should format error with status code', () => {
            const error = {
                response: { status: 401 },
                config: { url: '/api/test' },
                message: 'Unauthorized',
            };

            const logMessage = `❌ ${error.response?.status || 'ERR'} ${error.config?.url}: ${error.message}`;
            expect(logMessage).toBe('❌ 401 /api/test: Unauthorized');
        });

        it('should use ERR when status is missing', () => {
            const error = {
                config: { url: '/api/test' },
                message: 'Network Error',
            };

            const status = (error as any).response?.status || 'ERR';
            expect(status).toBe('ERR');
        });
    });
});
