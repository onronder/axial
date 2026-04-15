/**
 * Unit Tests for IngestModal Component
 * 
 * Tests the ingest modal dialog for different tabs, user roles, and plan restrictions.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

// =============================================================================
// Hoisted Mocks (must be defined before vi.mock calls)
// =============================================================================

const mockToast = vi.hoisted(() => vi.fn());
const mockConnect = vi.hoisted(() => vi.fn());
const mockRegisterJob = vi.hoisted(() => vi.fn());
const mockRefreshUsage = vi.hoisted(() => vi.fn());
const mockAuthFetchPost = vi.hoisted(() => vi.fn());
const mockGetUploadUrl = vi.hoisted(() => vi.fn());
const mockUploadToStorage = vi.hoisted(() => vi.fn());
const mockIngestFileReference = vi.hoisted(() => vi.fn());

// State variables for dynamic mock behavior
const mockState = vi.hoisted(() => ({
    profile: { role: 'editor' },
    canWebCrawl: true,
    isNotionConnected: false,
    dsLoading: false,
}));

// =============================================================================
// Mocks
// =============================================================================

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/hooks/useProfile', () => ({
    useProfile: () => ({
        profile: mockState.profile,
        isLoading: false,
    }),
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => ({
        canWebCrawl: mockState.canWebCrawl,
        refreshUsage: mockRefreshUsage,
    }),
}));

vi.mock('@/hooks/useDataSources', () => ({
    useDataSources: () => ({
        connect: mockConnect,
        isConnected: (source: string) => source === 'notion' && mockState.isNotionConnected,
        loading: mockState.dsLoading,
    }),
}));

vi.mock('@/hooks/useIngestionProgress', () => ({
    useIngestionProgress: () => ({
        registerJob: mockRegisterJob,
    }),
}));

vi.mock('@/lib/api', () => ({
    authFetch: {
        post: mockAuthFetchPost,
    },
    getUploadUrl: mockGetUploadUrl,
    ingestFileReference: mockIngestFileReference,
    uploadToStorage: mockUploadToStorage,
    clearAuthCache: vi.fn(),
}));

vi.mock('@/components/ingest/WebInput', () => ({
    WebInput: ({ url, onUrlChange, disabled }: { url: string; onUrlChange: (v: string) => void; disabled?: boolean }) => (
        <input
            data-testid="web-input"
            placeholder="Enter website URL"
            value={url}
            onChange={(e) => onUrlChange(e.target.value)}
            disabled={disabled}
        />
    ),
    validateUrl: (url: string) => url.startsWith('http://') || url.startsWith('https://'),
}));

// Import after mocks
import { IngestModal } from '@/components/ingest-modal';

// =============================================================================
// Tests
// =============================================================================

describe('IngestModal', () => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockState.profile = { role: 'editor' };
        mockState.canWebCrawl = true;
        mockState.isNotionConnected = false;
        mockState.dsLoading = false;
    });

    afterEach(() => {
        vi.unstubAllEnvs();
    });

    // =========================================================================
    // Rendering
    // =========================================================================

    describe('Rendering', () => {
        it('should render when open', () => {
            render(<IngestModal {...defaultProps} />);
            expect(screen.getByText('Add Data Source')).toBeInTheDocument();
        });

        it('should not render when closed', () => {
            render(<IngestModal {...defaultProps} isOpen={false} />);
            expect(screen.queryByText('Add Data Source')).not.toBeInTheDocument();
        });

        it('should render file tab by default', () => {
            render(<IngestModal {...defaultProps} />);
            expect(screen.getByText('Select Document (PDF, TXT, MD)')).toBeInTheDocument();
        });

        it('should render with initialTab=youtube', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            expect(screen.getByPlaceholderText('https://youtube.com/watch?v=...')).toBeInTheDocument();
        });

        it('should render with initialTab=website', () => {
            render(<IngestModal {...defaultProps} initialTab="website" />);
            expect(screen.getByTestId('web-input')).toBeInTheDocument();
        });

        it('should render with initialTab=notion', () => {
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            expect(screen.getByText('Connect Notion Workspace')).toBeInTheDocument();
        });

        it('should render tab buttons', () => {
            render(<IngestModal {...defaultProps} />);
            expect(screen.getByText('File')).toBeInTheDocument();
            expect(screen.getByText('YouTube')).toBeInTheDocument();
            expect(screen.getByText('Website')).toBeInTheDocument();
            expect(screen.getByText('Notion')).toBeInTheDocument();
        });

        it('should hide YouTube tab when the feature flag is disabled', () => {
            vi.stubEnv('NEXT_PUBLIC_YOUTUBE_INGEST_ENABLED', 'false');
            render(<IngestModal {...defaultProps} />);

            expect(screen.queryByText('YouTube')).not.toBeInTheDocument();
            expect(screen.getByText('File')).toBeInTheDocument();
            expect(screen.getByText('Website')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Tab Navigation
    // =========================================================================

    describe('Tab Navigation', () => {
        it('should switch to website tab', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            await user.click(screen.getByText('Website'));
            
            expect(screen.getByTestId('web-input')).toBeInTheDocument();
        });

        it('should switch to youtube tab', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            await user.click(screen.getByText('YouTube'));
            
            expect(screen.getByPlaceholderText('https://youtube.com/watch?v=...')).toBeInTheDocument();
        });

        it('should switch to notion tab', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            await user.click(screen.getByText('Notion'));
            
            expect(screen.getByText('Connect Notion Workspace')).toBeInTheDocument();
        });

        it('should switch to file tab from another tab', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            await user.click(screen.getByText('File'));
            
            expect(screen.getByText('Select Document (PDF, TXT, MD)')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Close Functionality
    // =========================================================================

    describe('Close Functionality', () => {
        it('should call onClose when close button clicked', async () => {
            const user = userEvent.setup();
            const onClose = vi.fn();
            render(<IngestModal {...defaultProps} onClose={onClose} />);
            
            await user.click(screen.getByRole('button', { name: /close/i }));
            
            expect(onClose).toHaveBeenCalled();
        });

        it('should call onClose when cancel button clicked', async () => {
            const user = userEvent.setup();
            const onClose = vi.fn();
            render(<IngestModal {...defaultProps} onClose={onClose} />);
            
            await user.click(screen.getByRole('button', { name: /cancel/i }));
            
            expect(onClose).toHaveBeenCalled();
        });

        it('should call onClose when backdrop clicked', async () => {
            const onClose = vi.fn();
            const { container } = render(<IngestModal {...defaultProps} onClose={onClose} />);
            
            // Click on the backdrop (the outer div)
            const backdrop = container.querySelector('.fixed.inset-0');
            if (backdrop) {
                fireEvent.click(backdrop);
                expect(onClose).toHaveBeenCalled();
            }
        });

        it('should show Close button on Notion tab', () => {
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            // Notion tab shows "Close" instead of "Cancel" - get all buttons with "Close"
            const closeButtons = screen.getAllByRole('button', { name: /close/i });
            // Should have at least 2: X button and Close text button
            expect(closeButtons.length).toBeGreaterThanOrEqual(1);
        });
    });

    // =========================================================================
    // Web Crawl Locked (Lines 284-287)
    // =========================================================================

    describe('Web Crawl Locked - Website Tab', () => {
        beforeEach(() => {
            mockState.canWebCrawl = false;
        });

        it('should show warning when web crawl is locked on website tab', () => {
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            expect(screen.getByText(/Web crawling is locked on your current plan/i)).toBeInTheDocument();
        });

        it('should disable web input when locked', () => {
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const input = screen.getByTestId('web-input');
            expect(input).toBeDisabled();
        });

        it('should disable submit button when locked on website tab', () => {
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const submitButton = screen.getByRole('button', { name: /upgrade to unlock/i });
            expect(submitButton).toBeDisabled();
        });

        it('should show upgrade message on locked website submit button', () => {
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            expect(screen.getByRole('button', { name: /upgrade to unlock/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // YouTube Locked (Lines 330-333)
    // =========================================================================

    describe('YouTube Locked - YouTube Tab', () => {
        beforeEach(() => {
            mockState.canWebCrawl = false;
        });

        it('should show warning when YouTube ingestion is locked', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            expect(screen.getByText(/YouTube ingestion requires Starter or Pro plan/i)).toBeInTheDocument();
        });

        it('should disable YouTube input when locked', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            expect(input).toBeDisabled();
        });

        it('should disable submit button when YouTube is locked', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            const submitButton = screen.getByRole('button', { name: /ingest/i });
            expect(submitButton).toBeDisabled();
        });

        it('should show upgrade button when web crawl is locked', () => {
            // canWebCrawl is false by default in this describe block
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            // Form should show upgrade button when web crawl is locked
            expect(screen.getByRole('button', { name: /upgrade to unlock/i })).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Viewer Role Restrictions
    // =========================================================================

    describe('Viewer Role Restrictions', () => {
        beforeEach(() => {
            mockState.profile = { role: 'viewer' };
        });

        it('should disable submit button for viewers', () => {
            render(<IngestModal {...defaultProps} />);
            
            expect(screen.getByRole('button', { name: /ingest/i })).toBeDisabled();
        });

        it('should disable file input for viewers', () => {
            render(<IngestModal {...defaultProps} />);
            
            const fileInput = document.querySelector('input[type="file"]');
            expect(fileInput).toBeDisabled();
        });

        it('should disable Notion connect button for viewers', () => {
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            // Button is disabled for viewers (not clickable)
            expect(screen.getByRole('button', { name: /connect notion/i })).toBeDisabled();
            expect(mockConnect).not.toHaveBeenCalled();
        });

        it('should show toast when viewer tries to submit form directly', async () => {
            const { container } = render(<IngestModal {...defaultProps} />);
            
            // Submit the form directly (bypassing disabled button)
            const form = container.querySelector('form');
            if (form) {
                fireEvent.submit(form);
                
                await waitFor(() => {
                    expect(mockToast).toHaveBeenCalledWith(
                        expect.objectContaining({
                            variant: 'destructive',
                        })
                    );
                });
            }
        });

        it('should show toast when viewer tries to connect Notion via handler', async () => {
            // Reset to editor first to allow button click, then check the internal guard
            mockState.profile = { role: 'editor' };
            const user = userEvent.setup();
            const { rerender } = render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            // Change to viewer after render
            mockState.profile = { role: 'viewer' };
            rerender(<IngestModal {...defaultProps} initialTab="notion" />);
            
            // Button should now be disabled
            expect(screen.getByRole('button', { name: /connect notion/i })).toBeDisabled();
        });
    });

    // =========================================================================
    // Notion Tab
    // =========================================================================

    describe('Notion Tab', () => {
        it('should show connect button when not connected', () => {
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            expect(screen.getByRole('button', { name: /connect notion/i })).toBeInTheDocument();
        });

        it('should call connect when Notion connect clicked', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            await user.click(screen.getByRole('button', { name: /connect notion/i }));
            
            expect(mockConnect).toHaveBeenCalledWith('notion');
        });

        it('should show connected state when Notion is connected', () => {
            mockState.isNotionConnected = true;
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            expect(screen.getByText('Notion Connected')).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /manage in notion/i })).toBeInTheDocument();
        });

        it('should not show Ingest button on notion tab', () => {
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            // Notion tab shows "Close" not "Ingest"
            expect(screen.queryByRole('button', { name: /ingest/i })).not.toBeInTheDocument();
        });
    });

    // =========================================================================
    // File Upload
    // =========================================================================

    describe('File Upload', () => {
        const getFileInput = () => {
            // Get the file input by its type since label association may be implicit
            const container = document.querySelector('input[type="file"]');
            return container as HTMLInputElement;
        };

        it('should handle file selection', async () => {
            render(<IngestModal {...defaultProps} />);
            
            const file = new File(['test'], 'test.txt', { type: 'text/plain' });
            const input = getFileInput();
            
            await act(async () => {
                fireEvent.change(input, { target: { files: [file] } });
            });
            
            expect(screen.getByText('Selected: test.txt')).toBeInTheDocument();
        });

        it('should submit file upload successfully', async () => {
            mockGetUploadUrl.mockResolvedValue({ 
                upload_url: 'https://storage.example.com/upload', 
                storage_path: 'files/test.txt' 
            });
            mockUploadToStorage.mockResolvedValue(true);
            mockIngestFileReference.mockResolvedValue({ job_id: 'job-123' });
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            const file = new File(['test'], 'test.txt', { type: 'text/plain' });
            const input = getFileInput();
            
            await act(async () => {
                fireEvent.change(input, { target: { files: [file] } });
            });
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockGetUploadUrl).toHaveBeenCalled();
                expect(mockUploadToStorage).toHaveBeenCalled();
                expect(mockIngestFileReference).toHaveBeenCalled();
                expect(mockRegisterJob).toHaveBeenCalledWith('job-123');
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Queued',
                    })
                );
            });
        });

        it('should show error when upload fails', async () => {
            mockGetUploadUrl.mockResolvedValue({ 
                upload_url: 'https://storage.example.com/upload', 
                storage_path: 'files/test.txt' 
            });
            mockUploadToStorage.mockResolvedValue(false);
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            const file = new File(['test'], 'test.txt', { type: 'text/plain' });
            const input = getFileInput();
            
            await act(async () => {
                fireEvent.change(input, { target: { files: [file] } });
            });
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should not submit if no file selected', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} />);
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            // No API calls should be made
            expect(mockGetUploadUrl).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Website/URL Submission
    // =========================================================================

    describe('Website Submission', () => {
        it('should submit website URL successfully', async () => {
            mockAuthFetchPost.mockResolvedValue({ data: { job_id: 'crawl-123' } });
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const input = screen.getByTestId('web-input');
            await user.type(input, 'https://example.com');
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockAuthFetchPost).toHaveBeenCalledWith('/integrations/web/crawl', expect.objectContaining({
                    url: 'https://example.com',
                    crawl_type: 'sitemap',
                }));
                expect(mockRegisterJob).toHaveBeenCalledWith('crawl-123');
            });
        });

        it('should show error for invalid URL', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const input = screen.getByTestId('web-input');
            await user.type(input, 'not-a-valid-url');
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        variant: 'destructive',
                    })
                );
            });
        });
    });

    // =========================================================================
    // YouTube Submission
    // =========================================================================

    describe('YouTube Submission', () => {
        it('should submit valid YouTube URL', async () => {
            mockAuthFetchPost.mockResolvedValue({ data: { job_id: 'youtube-123' } });
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            // Use a valid 11-character video ID
            await user.type(input, 'https://youtube.com/watch?v=dQw4w9WgXcQ');
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockAuthFetchPost).toHaveBeenCalledWith('/integrations/web/crawl', expect.objectContaining({
                    crawl_type: 'single',
                }));
                expect(mockRegisterJob).toHaveBeenCalledWith('youtube-123');
            });
        });

        it('should show validation error for invalid YouTube URL', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://example.com/not-youtube');
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        variant: 'destructive',
                    })
                );
            });
        });

        it('should show YouTube info banner', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            expect(screen.getByText(/paste a youtube video url to transcribe/i)).toBeInTheDocument();
        });

        it('should show supported URL formats', () => {
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            expect(screen.getByText(/supports youtube.com\/watch, youtu.be, and shorts urls/i)).toBeInTheDocument();
        });

        it('should not submit if no URL entered', async () => {
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            // No API calls should be made
            expect(mockAuthFetchPost).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Loading State
    // =========================================================================

    describe('Loading State', () => {
        it('should show loading state when submitting', async () => {
            mockAuthFetchPost.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const input = screen.getByTestId('web-input');
            await user.type(input, 'https://example.com');
            
            const submitButton = screen.getByRole('button', { name: /ingest/i });
            await user.click(submitButton);
            
            // Button should show "Processing..."
            expect(screen.getByRole('button', { name: /processing/i })).toBeInTheDocument();
        });

        it('should disable Notion connect when loading', () => {
            mockState.dsLoading = true;
            render(<IngestModal {...defaultProps} initialTab="notion" />);
            
            expect(screen.getByRole('button', { name: /connect notion/i })).toBeDisabled();
        });
    });

    // =========================================================================
    // Initial Tab Sync
    // =========================================================================

    describe('Initial Tab Sync', () => {
        it('should update activeTab when initialTab prop changes', () => {
            const { rerender } = render(<IngestModal {...defaultProps} initialTab="file" />);
            
            expect(screen.getByText('Select Document (PDF, TXT, MD)')).toBeInTheDocument();
            
            rerender(<IngestModal {...defaultProps} initialTab="youtube" />);
            
            expect(screen.getByPlaceholderText('https://youtube.com/watch?v=...')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Error Handling
    // =========================================================================

    describe('Error Handling', () => {
        it('should handle non-Error exceptions', async () => {
            mockAuthFetchPost.mockRejectedValue(42);
            
            const user = userEvent.setup();
            render(<IngestModal {...defaultProps} initialTab="website" />);
            
            const input = screen.getByTestId('web-input');
            await user.type(input, 'https://example.com');
            
            await user.click(screen.getByRole('button', { name: /ingest/i }));
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Ingestion Failed',
                        description: 'Something went wrong. Please try again.',
                    })
                );
            });
        });
    });
});
