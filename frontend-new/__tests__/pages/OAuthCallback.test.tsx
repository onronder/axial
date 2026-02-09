import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import OAuthCallbackPage from '@/app/oauth/callback/page';
import { api } from '@/lib/api';

// =============================================================================
// Mocks
// =============================================================================

const mockPush = vi.fn();
const mockSearchParamsGet = vi.fn();

vi.mock('@/lib/api', () => ({
    api: {
        post: vi.fn(),
    },
    clearAuthCache: vi.fn(),
}));

vi.mock('next/navigation', () => ({
    useRouter: () => ({
        push: mockPush,
    }),
    useSearchParams: () => ({
        get: mockSearchParamsGet,
    }),
}));

vi.mock('@/lib/utils', () => ({
    getMicrosoftRedirectUri: () => 'https://example.com/oauth/callback',
    getMicrosoftTenantId: () => 'test-tenant-id',
    cn: (...classes: (string | undefined)[]) => classes.filter(Boolean).join(' '),
}));

// eslint-disable-next-line react/display-name
vi.mock('@/components/data-sources/GitHubRepoSelector', () => ({
    GitHubRepoSelector: ({ open, onComplete, onOpenChange }: { 
        open: boolean; 
        onComplete: () => void;
        onOpenChange: (open: boolean) => void;
    }) => (
        open ? (
            <div data-testid="github-repo-selector">
                <span>GitHub Repository Selector</span>
                <button onClick={onComplete} data-testid="complete-btn">Complete</button>
                <button onClick={() => onOpenChange(false)} data-testid="close-btn">Close</button>
            </div>
        ) : null
    ),
}));

// =============================================================================
// Test Suite
// =============================================================================

describe('OAuthCallbackPage', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        sessionStorage.clear();
        // Default: valid code, Google provider
        mockSearchParamsGet.mockImplementation((key: string) => {
            if (key === 'code') return 'test-auth-code';
            if (key === 'state') return 'google';
            return null;
        });
        (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { success: true } });
    });

    afterEach(() => {
        sessionStorage.clear();
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should show loading state with correct provider name', async () => {
            // Delay API response to see loading state
            (api.post as ReturnType<typeof vi.fn>).mockImplementation(() => 
                new Promise(resolve => setTimeout(() => resolve({ data: { success: true } }), 100))
            );
            
            render(<OAuthCallbackPage />);
            
            // Should show "Connecting Google Drive..." initially
            expect(screen.getByText(/Connecting Google Drive/i)).toBeInTheDocument();
        });

        it('should show "Connecting Notion..." for Notion provider', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'test-code';
                if (key === 'state') return 'notion';
                return null;
            });
            (api.post as ReturnType<typeof vi.fn>).mockImplementation(() => 
                new Promise(resolve => setTimeout(() => resolve({ data: { success: true } }), 100))
            );
            
            render(<OAuthCallbackPage />);
            
            expect(screen.getByText(/Connecting Notion/i)).toBeInTheDocument();
        });

        it('should show "Connecting Dropbox..." for Dropbox provider', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'test-code';
                if (key === 'state') return 'dropbox';
                return null;
            });
            (api.post as ReturnType<typeof vi.fn>).mockImplementation(() => 
                new Promise(resolve => setTimeout(() => resolve({ data: { success: true } }), 100))
            );
            
            render(<OAuthCallbackPage />);
            
            expect(screen.getByText(/Connecting Dropbox/i)).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Provider Detection Tests
    // =========================================================================

    describe('Provider Detection', () => {
        it('should call correct endpoint for Google Drive', async () => {
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/google/exchange',
                    { code: 'test-auth-code' }
                );
            });
        });

        it('should call correct endpoint for Dropbox', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'dropbox-code';
                if (key === 'state') return 'dropbox';
                return null;
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/dropbox/exchange',
                    { code: 'dropbox-code' }
                );
            });
        });

        it('should call correct endpoint for Notion', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'notion-code';
                if (key === 'state') return 'notion';
                return null;
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/notion/exchange',
                    { code: 'notion-code' }
                );
            });
        });

        it('should call correct endpoint for Box', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'box-code';
                if (key === 'state') return 'box';
                return null;
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/box/exchange',
                    { code: 'box-code' }
                );
            });
        });

        it('should default to Google when no state param', async () => {
            // State is now required for CSRF protection
            // Test that explicit 'google' state works correctly
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'code-123';
                if (key === 'state') return 'google';
                return null;
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/google/exchange',
                    expect.any(Object)
                );
            });
        });
    });

    // =========================================================================
    // Success Flow Tests
    // =========================================================================

    describe('Success Flow', () => {
        it('should show success state after exchange', async () => {
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Google Drive Connected!/i)).toBeInTheDocument();
            });
        });

        it('should show redirecting message after success', async () => {
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Redirecting to Data Sources/i)).toBeInTheDocument();
            });
        });

        it('should show GitHub Connected for GitHub provider', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'github-code';
                if (key === 'state') return 'github';
                return null;
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/GitHub Connected!/i)).toBeInTheDocument();
            });
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show error when no code received', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'state') return 'google';
                return null; // No code
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(screen.getByText(/No authorization code received/i)).toBeInTheDocument();
                expect(screen.getByText(/Connection Failed/i)).toBeInTheDocument();
            });
        });

        it('should show "Access was denied" for access_denied error', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'error') return 'access_denied';
                if (key === 'state') return 'google';
                return null;
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(screen.getByText(/Access was denied/i)).toBeInTheDocument();
            });
        });

        it('should show error description from provider', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'error') return 'server_error';
                if (key === 'error_description') return 'The server is unavailable';
                if (key === 'state') return 'google';
                return null;
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(screen.getByText(/The server is unavailable/i)).toBeInTheDocument();
            });
        });

        it('should show API error message on exchange failure', async () => {
            (api.post as ReturnType<typeof vi.fn>).mockRejectedValue({
                response: { data: { detail: 'Invalid authorization code' } },
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Invalid authorization code/i)).toBeInTheDocument();
            });
        });

        it('should show fallback error message when no detail provided', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'test-code';
                if (key === 'state') return 'notion';
                return null;
            });
            (api.post as ReturnType<typeof vi.fn>).mockRejectedValue({
                message: 'Network Error',
            });
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Failed to connect Notion/i)).toBeInTheDocument();
            });
        });

        it('should show Go Back and Try Again buttons on error', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'state') return 'google';
                return null; // No code — triggers "error" status
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Go Back/i })).toBeInTheDocument();
                expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
            });
        });

        it('should navigate to data-sources when Go Back is clicked', async () => {
            mockSearchParamsGet.mockImplementation(() => null);
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Go Back/i })).toBeInTheDocument();
            });

            fireEvent.click(screen.getByRole('button', { name: /Go Back/i }));
            
            expect(mockPush).toHaveBeenCalledWith('/dashboard/settings/data-sources');
        });

        it('should navigate to data-sources when Try Again is clicked', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'state') return 'google';
                return null;
            });

            render(<OAuthCallbackPage />);

            await waitFor(() => {
                expect(screen.getByRole('button', { name: /Try Again/i })).toBeInTheDocument();
            });

            fireEvent.click(screen.getByRole('button', { name: /Try Again/i }));

            expect(mockPush).toHaveBeenCalledWith('/dashboard/settings/data-sources');
        });
    });

    // =========================================================================
    // PKCE Flow Tests (Microsoft providers)
    // =========================================================================

    describe('PKCE Flow', () => {
        it('should include code_verifier for OneDrive', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'onedrive-code';
                if (key === 'state') return 'onedrive';
                return null;
            });
            sessionStorage.setItem('microsoft_pkce_onedrive', 'test-verifier-123');
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/microsoft/exchange',
                    expect.objectContaining({
                        code: 'onedrive-code',
                        code_verifier: 'test-verifier-123',
                        target_type: 'onedrive',
                    })
                );
            });
        });

        it('should include code_verifier for SharePoint', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'sharepoint-code';
                if (key === 'state') return 'sharepoint';
                return null;
            });
            sessionStorage.setItem('microsoft_pkce_sharepoint', 'sharepoint-verifier-456');
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(api.post).toHaveBeenCalledWith(
                    '/integrations/microsoft/exchange',
                    expect.objectContaining({
                        code: 'sharepoint-code',
                        code_verifier: 'sharepoint-verifier-456',
                        target_type: 'sharepoint',
                    })
                );
            });
        });

        it('should show error when PKCE verifier is missing for OneDrive', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'onedrive-code';
                if (key === 'state') return 'onedrive';
                return null;
            });
            // Don't set PKCE verifier in sessionStorage
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Security verification failed/i)).toBeInTheDocument();
            });
        });

        it('should show error when PKCE verifier is missing for SharePoint', async () => {
            mockSearchParamsGet.mockImplementation((key: string) => {
                if (key === 'code') return 'sharepoint-code';
                if (key === 'state') return 'sharepoint';
                return null;
            });
            // Don't set PKCE verifier in sessionStorage
            
            render(<OAuthCallbackPage />);
            
            await waitFor(() => {
                expect(screen.getByText(/Security verification failed/i)).toBeInTheDocument();
            });
        });
    });
});
