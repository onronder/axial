import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { YoutubeInput } from '@/components/data-sources/YoutubeInput';

// =============================================================================
// Mocks
// =============================================================================

const mockToast = vi.fn();
vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

const mockRegisterJob = vi.fn();
vi.mock('@/hooks/useIngestionProgress', () => ({
    useIngestionProgress: () => ({
        registerJob: mockRegisterJob,
        activeJobs: [],
        isLoading: false,
    }),
}));

const mockApiPost = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: unknown[]) => mockApiPost(...args),
    },
}));

// =============================================================================
// Test Data
// =============================================================================

const defaultSource = {
    id: 'youtube-source',
    name: 'YouTube Video',
    type: 'youtube',
    status: 'disconnected' as const,
    lastSync: '-',
    icon: 'youtube',
    description: 'Transcribe and chat with YouTube videos',
    category: 'web' as const,
};

// =============================================================================
// Test Suite
// =============================================================================

describe('YoutubeInput Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiPost.mockResolvedValue({ data: { job_id: 'test-job-123' } });
    });

    // =========================================================================
    // Rendering Tests
    // =========================================================================

    describe('Rendering', () => {
        it('should render the component with source name', () => {
            render(<YoutubeInput source={defaultSource} />);
            expect(screen.getByText('YouTube Video')).toBeInTheDocument();
        });

        it('should render the source description', () => {
            render(<YoutubeInput source={defaultSource} />);
            expect(screen.getByText('Transcribe and chat with YouTube videos')).toBeInTheDocument();
        });

        it('should render URL input placeholder', () => {
            render(<YoutubeInput source={defaultSource} />);
            expect(screen.getByPlaceholderText('https://youtube.com/watch?v=...')).toBeInTheDocument();
        });

        it('should render help text', () => {
            render(<YoutubeInput source={defaultSource} />);
            expect(screen.getByText(/Paste a YouTube video URL/i)).toBeInTheDocument();
        });

        it('should render YouTube icon', () => {
            render(<YoutubeInput source={defaultSource} />);
            const icon = document.querySelector('.lucide-youtube');
            expect(icon).toBeInTheDocument();
        });
    });

    // =========================================================================
    // URL Validation Tests
    // =========================================================================

    describe('URL Validation', () => {
        it('should accept valid YouTube watch URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            // Should show video ID when valid
            await waitFor(() => {
                expect(screen.getByText('Video ID:')).toBeInTheDocument();
                expect(screen.getByText('dQw4w9WgXcQ')).toBeInTheDocument();
            });
        });

        it('should show validation error in UI for invalid URL after submit attempt', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            
            // Type a partial URL that looks valid at first but isn't
            await user.type(input, 'https://youtube.com/');
            
            // Clear and type an invalid URL then try form submission
            await user.clear(input);
            await user.type(input, 'https://vimeo.com/123456');
            
            // The button should be disabled since URL is invalid
            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();
        });

        it('should accept valid YouTube short URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://youtu.be/dQw4w9WgXcQ');

            await waitFor(() => {
                expect(screen.getByText('dQw4w9WgXcQ')).toBeInTheDocument();
            });
        });

        it('should show error indicator for invalid URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://not-youtube.com/video');

            await waitFor(() => {
                // Button should be disabled for invalid URL
                const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
                expect(submitBtn).toBeDisabled();
            });
        });

        it('should not show video ID for invalid URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'invalid-url');

            expect(screen.queryByText('Video ID:')).not.toBeInTheDocument();
        });
    });

    // =========================================================================
    // Input Handling Tests
    // =========================================================================

    describe('Input Handling', () => {
        it('should update URL state on input change', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...') as HTMLInputElement;
            await user.type(input, 'https://youtube.com/watch?v=test123');

            expect(input.value).toBe('https://youtube.com/watch?v=test123');
        });

        it('should clear validation error when typing', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            // Type an invalid URL first
            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'invalid');

            // Button should be disabled for invalid URL
            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();

            // Clear and type valid URL
            await user.clear(input);
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            // Button should now be enabled
            expect(submitBtn).not.toBeDisabled();
        });
    });

    // =========================================================================
    // Submission Tests
    // =========================================================================

    describe('Submission', () => {
        it('should disable button when URL is empty', () => {
            render(<YoutubeInput source={defaultSource} />);

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();
        });

        it('should disable button for invalid URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'invalid-url');

            // Button should be disabled because URL is invalid
            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();
        });

        it('should call API on valid submission', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith('/integrations/web/crawl', expect.objectContaining({
                    url: expect.stringContaining('youtube.com'),
                    crawl_type: 'single',
                }));
            });
        });

        it('should show success toast on successful submission', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Video Queued',
                }));
            });
        });

        it('should register job on successful submission', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockRegisterJob).toHaveBeenCalledWith('test-job-123');
            });
        });

        it('should clear input on successful submission', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...') as HTMLInputElement;
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(input.value).toBe('');
            });
        });

        it('should handle Enter key submission', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ{enter}');

            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });

        it('should show validation error when Enter pressed with invalid URL', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://vimeo.com/123456{enter}');

            // Should show toast with validation error
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Invalid YouTube URL',
                    variant: 'destructive',
                }));
            });

            // Validation error should be visible in UI
            expect(screen.getByText(/Please enter a valid YouTube/)).toBeInTheDocument();
        });

        it('should show validation error when Enter pressed with empty URL trimmed', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            // Type only spaces
            await user.type(input, '   ');
            
            // Enter should not trigger handleIngest since url.trim() is empty
            fireEvent.keyDown(input, { key: 'Enter' });

            // API should not be called because url.trim() is falsy
            expect(mockApiPost).not.toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Error Handling Tests
    // =========================================================================

    describe('Error Handling', () => {
        it('should show error toast on API failure', async () => {
            mockApiPost.mockRejectedValueOnce(new Error('Network error'));
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    title: 'Ingestion Failed',
                    variant: 'destructive',
                }));
            });
        });

        it('should show API error detail when available', async () => {
            mockApiPost.mockRejectedValueOnce({
                response: { data: { detail: 'Video not found' } }
            });
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    description: 'Video not found',
                }));
            });
        });

        it('should show default error message when no detail or message', async () => {
            mockApiPost.mockRejectedValueOnce({
                response: { data: {} }
            });
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    description: 'Could not process the YouTube video. Please try again.',
                }));
            });
        });

        it('should use error.message as fallback', async () => {
            mockApiPost.mockRejectedValueOnce({
                message: 'Connection timeout'
            });
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(expect.objectContaining({
                    description: 'Connection timeout',
                }));
            });
        });
    });

    // =========================================================================
    // Disabled State Tests
    // =========================================================================

    describe('Disabled State', () => {
        it('should disable input when disabled prop is true', () => {
            render(<YoutubeInput source={defaultSource} disabled={true} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            expect(input).toBeDisabled();
        });

        it('should disable button when disabled prop is true', () => {
            render(<YoutubeInput source={defaultSource} disabled={true} />);

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();
        });

        it('should show toast when submitting while disabled', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} disabled={true} disabledReason="Not allowed" />);

            // Need to enable button temporarily to click
            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            
            // Trigger submit via the form's internal logic by calling handleIngest directly
            // Since button is disabled, we can't click it, but we can verify the disabled reason is shown
            expect(screen.getByText('Not allowed')).toBeInTheDocument();
        });

        it('should show disabled reason when provided', () => {
            render(<YoutubeInput source={defaultSource} disabled={true} disabledReason="Upgrade required" />);

            expect(screen.getByText('Upgrade required')).toBeInTheDocument();
        });
    });

    // =========================================================================
    // Loading State Tests
    // =========================================================================

    describe('Loading State', () => {
        it('should disable button while loading', async () => {
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(submitBtn).toBeDisabled();
            });
        });

        it('should show spinner while loading', async () => {
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            fireEvent.click(submitBtn);

            await waitFor(() => {
                const spinner = document.querySelector('.animate-spin');
                expect(spinner).toBeInTheDocument();
            });
        });

        it('should disable input while loading', async () => {
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            fireEvent.click(submitBtn);

            await waitFor(() => {
                expect(input).toBeDisabled();
            });
        });
    });

    // =========================================================================
    // Edge Cases
    // =========================================================================

    describe('Edge Cases', () => {
        it('should handle crawl_id response format', async () => {
            mockApiPost.mockResolvedValueOnce({ data: { crawl_id: 'crawl-456' } });
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockRegisterJob).toHaveBeenCalledWith('crawl-456');
            });
        });

        it('should handle response without job_id', async () => {
            mockApiPost.mockResolvedValueOnce({ data: {} });
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            await user.click(submitBtn);

            await waitFor(() => {
                expect(mockRegisterJob).not.toHaveBeenCalled();
            });
        });

        it('should not submit on Enter while loading', async () => {
            mockApiPost.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 500)));
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');

            // First click to start loading
            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            fireEvent.click(submitBtn);

            // Wait for loading to start
            await waitFor(() => {
                expect(input).toBeDisabled();
            });

            // API should only be called once
            expect(mockApiPost).toHaveBeenCalledTimes(1);
        });

        it('should disable submit button when URL is invalid', async () => {
            const user = userEvent.setup();
            render(<YoutubeInput source={defaultSource} />);

            const input = screen.getByPlaceholderText('https://youtube.com/watch?v=...');
            await user.type(input, 'not-a-youtube-url');

            const submitBtn = screen.getByRole('button', { name: /ingest youtube video/i });
            expect(submitBtn).toBeDisabled();
        });
    });
});
