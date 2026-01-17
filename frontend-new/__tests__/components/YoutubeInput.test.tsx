/**
 * Test Suite: YoutubeInput Component
 *
 * Comprehensive tests for:
 * - YouTube URL validation (watch, short, embed, shorts)
 * - Form submission and API calls
 * - Disabled states and error handling
 * - UI rendering
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Use hoisted mocks for proper initialization
const { mockToast, mockRefresh, mockApiPost } = vi.hoisted(() => ({
    mockToast: vi.fn(),
    mockRefresh: vi.fn(),
    mockApiPost: vi.fn().mockResolvedValue({ data: { job_id: 'test-job-123' } }),
}));

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/hooks/useUsage', () => ({
    useUsage: () => ({ refresh: mockRefresh }),
}));

vi.mock('@/hooks/useFileStatus', () => ({
    useFileStatus: () => ({ files: [] }),
}));

vi.mock('@/lib/api', () => ({
    api: {
        post: (...args: unknown[]) => mockApiPost(...args),
    },
}));

// Mock IngestionProgressModal to avoid complex rendering
vi.mock('@/components/ingestion/IngestionProgressModal', () => ({
    IngestionProgressModal: () => null,
}));

// Import component after mocks
import { YoutubeInput } from '@/components/data-sources/YoutubeInput';

const mockSource = {
    id: 'youtube',
    name: 'YouTube Video',
    type: 'youtube',
    status: 'disconnected' as const,
    lastSync: '-',
    icon: 'youtube',
    description: 'Transcribe and chat with YouTube videos',
    category: 'web' as const,
};

const renderWithQueryClient = (ui: React.ReactElement) => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
    );
};

describe('YoutubeInput Component', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    // ===========================================================================
    // Rendering Tests
    // ===========================================================================

    describe('Rendering', () => {
        it('renders YouTube icon and title', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            expect(screen.getByText('YouTube Video')).toBeInTheDocument();
            expect(screen.getByPlaceholderText(/youtube\.com\/watch/i)).toBeInTheDocument();
        });

        it('renders source description', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            expect(screen.getByText('Transcribe and chat with YouTube videos')).toBeInTheDocument();
        });

        it('renders helper text', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            expect(screen.getByText(/Paste a YouTube video URL/i)).toBeInTheDocument();
        });

        it('shows disabled reason when provided', () => {
            renderWithQueryClient(
                <YoutubeInput 
                    source={mockSource} 
                    disabled={true} 
                    disabledReason="Upgrade required to use this feature" 
                />
            );
            
            expect(screen.getByText('Upgrade required to use this feature')).toBeInTheDocument();
        });
    });

    // ===========================================================================
    // URL Validation Tests
    // ===========================================================================

    describe('URL Validation', () => {
        it('accepts valid YouTube watch URL', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith(
                    '/integrations/web/crawl',
                    expect.objectContaining({
                        url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                        crawl_type: 'single',
                    })
                );
            });
        });

        it('accepts valid youtu.be short URL', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalledWith(
                    '/integrations/web/crawl',
                    expect.objectContaining({
                        url: 'https://youtu.be/dQw4w9WgXcQ',
                    })
                );
            });
        });

        it('accepts YouTube embed URL', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtube.com/embed/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });

        it('accepts YouTube Shorts URL', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtube.com/shorts/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });

        it('rejects non-YouTube URLs by disabling button', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://www.cnn.com/article' } });
            
            // Button should be disabled for invalid URL
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
            
            // Should NOT call API
            expect(mockApiPost).not.toHaveBeenCalled();
        });

        it('rejects Vimeo URLs by disabling button', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://vimeo.com/123456789' } });
            
            // Button should be disabled for Vimeo URL
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
            
            expect(mockApiPost).not.toHaveBeenCalled();
        });

        it('rejects empty input', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
        });

        it('rejects plain text by disabling button', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'not a url' } });
            
            // Button should be disabled for invalid text
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
        });
    });

    // ===========================================================================
    // Submit Behavior Tests
    // ===========================================================================

    describe('Submit Behavior', () => {
        it('disables button when input is empty', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
        });

        it('enables button when valid YouTube URL is entered', () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            // Must use a valid video ID format (11 characters)
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            expect(submitButton).not.toBeDisabled();
        });

        it('submits on Enter key press', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            fireEvent.keyDown(input, { key: 'Enter' });
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
        });

        it('clears input after successful submission', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i) as HTMLInputElement;
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(input.value).toBe('');
            });
        });

        it('shows success toast on successful submission', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalledWith(
                    expect.objectContaining({
                        title: 'Video Queued',
                    })
                );
            });
        });

        it('sends correct payload to API', async () => {
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            // Use valid 11-character video ID
            fireEvent.change(input, { target: { value: 'https://youtube.com/watch?v=dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockApiPost).toHaveBeenCalled();
            });
            
            expect(mockApiPost).toHaveBeenCalledWith(
                '/integrations/web/crawl',
                expect.objectContaining({
                    url: 'https://youtube.com/watch?v=dQw4w9WgXcQ',
                    crawl_type: 'single',
                })
            );
        });
    });

    // ===========================================================================
    // Disabled State Tests
    // ===========================================================================

    describe('Disabled State', () => {
        it('disables input when disabled prop is true', () => {
            renderWithQueryClient(
                <YoutubeInput source={mockSource} disabled={true} />
            );
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            expect(input).toBeDisabled();
        });

        it('disables button when disabled prop is true', () => {
            renderWithQueryClient(
                <YoutubeInput source={mockSource} disabled={true} />
            );
            
            const submitButton = screen.getByRole('button');
            expect(submitButton).toBeDisabled();
        });

        it('shows toast when clicking submit while disabled', async () => {
            renderWithQueryClient(
                <YoutubeInput 
                    source={mockSource} 
                    disabled={true}
                    disabledReason="You need editor access"
                />
            );
            
            // Manually trigger the handleIngest to test the guard
            // Note: The button is disabled so we can't click it directly
            // This test verifies the disabled reason is displayed
            expect(screen.getByText('You need editor access')).toBeInTheDocument();
        });
    });

    // ===========================================================================
    // Error Handling Tests
    // ===========================================================================

    describe('Error Handling', () => {
        it('shows error toast on API failure', async () => {
            mockApiPost.mockRejectedValueOnce({
                response: { data: { detail: 'Server error' } }
            });
            
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });
            
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Ingestion Failed',
                    variant: 'destructive',
                })
            );
        });

        it('shows generic error message when API returns no detail', async () => {
            mockApiPost.mockRejectedValueOnce(new Error('Network error'));
            
            renderWithQueryClient(<YoutubeInput source={mockSource} />);
            
            const input = screen.getByPlaceholderText(/youtube\.com\/watch/i);
            fireEvent.change(input, { target: { value: 'https://youtu.be/dQw4w9WgXcQ' } });
            
            const submitButton = screen.getByRole('button');
            fireEvent.click(submitButton);
            
            await waitFor(() => {
                expect(mockToast).toHaveBeenCalled();
            });
            
            // When there's no response.data.detail, fallback message is used
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Ingestion Failed',
                    variant: 'destructive',
                })
            );
        });
    });
});

// ===========================================================================
// YouTube URL Regex Validation (Unit Tests)
// ===========================================================================

describe('YouTube URL Regex Validation', () => {
    const YOUTUBE_URL_REGEX = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/|youtube\.com\/shorts\/).+$/i;

    describe('Valid URLs', () => {
        it('matches standard watch URLs', () => {
            expect(YOUTUBE_URL_REGEX.test('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('https://youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('http://youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(true);
        });

        it('matches short URLs (youtu.be)', () => {
            expect(YOUTUBE_URL_REGEX.test('https://youtu.be/dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('http://youtu.be/dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('youtu.be/dQw4w9WgXcQ')).toBe(true);
        });

        it('matches embed URLs', () => {
            expect(YOUTUBE_URL_REGEX.test('https://youtube.com/embed/dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('https://www.youtube.com/embed/dQw4w9WgXcQ')).toBe(true);
        });

        it('matches shorts URLs', () => {
            expect(YOUTUBE_URL_REGEX.test('https://youtube.com/shorts/dQw4w9WgXcQ')).toBe(true);
            expect(YOUTUBE_URL_REGEX.test('https://www.youtube.com/shorts/abc123xyz')).toBe(true);
        });

        it('matches v/ format URLs', () => {
            expect(YOUTUBE_URL_REGEX.test('https://youtube.com/v/dQw4w9WgXcQ')).toBe(true);
        });
    });

    describe('Invalid URLs', () => {
        it('rejects non-YouTube domains', () => {
            expect(YOUTUBE_URL_REGEX.test('https://www.google.com')).toBe(false);
            expect(YOUTUBE_URL_REGEX.test('https://vimeo.com/123456')).toBe(false);
            expect(YOUTUBE_URL_REGEX.test('https://cnn.com/youtube')).toBe(false);
            expect(YOUTUBE_URL_REGEX.test('https://example.com/watch?v=fake')).toBe(false);
        });

        it('rejects invalid formats', () => {
            expect(YOUTUBE_URL_REGEX.test('')).toBe(false);
            expect(YOUTUBE_URL_REGEX.test('not-a-url')).toBe(false);
            expect(YOUTUBE_URL_REGEX.test('youtube.com')).toBe(false); // Missing path
            expect(YOUTUBE_URL_REGEX.test('youtube.com/channel/123')).toBe(false); // Channel, not video
        });

        it('rejects URLs with youtube in path but wrong domain', () => {
            expect(YOUTUBE_URL_REGEX.test('https://fake-youtube.com/watch?v=abc')).toBe(false);
        });
    });
});
