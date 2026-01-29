/**
 * Unit Tests for useAnalytics Hooks
 * 
 * Tests for the analytics hooks including:
 * - Query key factory
 * - useFeedback hook
 * - useSourceMetrics hook
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { 
    analyticsKeys, 
    useFeedback, 
    useSourceMetrics,
    type FeedbackResponse,
    type SourceMetricsResponse,
} from '@/hooks/useAnalytics';

// Mock API
const mockApiGet = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        get: (url: string) => mockApiGet(url),
    },
}));

// Mock data
const mockFeedbackResponse: FeedbackResponse = {
    items: [
        {
            id: 'f1',
            rating: 'positive',
            feedback_text: null,
            query_text: 'Test query',
            answer_preview: 'Test answer',
            sources: [],
            user_email: 'test@example.com',
            created_at: '2024-01-15T10:00:00Z',
        },
    ],
    total: 1,
    has_more: false,
    summary: {
        positive_count: 1,
        negative_count: 0,
        total_count: 1,
        negative_rate_pct: 0,
    },
};

const mockSourceMetricsResponse: SourceMetricsResponse = {
    items: [
        {
            source_label: 'Test Source',
            source_type: 'pdf',
            source_url: null,
            positive_count: 10,
            negative_count: 2,
            total_feedback: 12,
            negative_rate_pct: 16.67,
            last_feedback_at: '2024-01-15T10:00:00Z',
        },
    ],
    total: 1,
};

function createWrapper() {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
        },
    });
    const Wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
    Wrapper.displayName = 'TestWrapper';
    return Wrapper;
}

describe('useAnalytics Hooks', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    describe('analyticsKeys Factory', () => {
        it('should generate all key', () => {
            expect(analyticsKeys.all).toEqual(['analytics']);
        });

        it('should generate feedback key', () => {
            expect(analyticsKeys.feedback()).toEqual(['analytics', 'feedback']);
        });

        it('should generate feedbackList key without params', () => {
            expect(analyticsKeys.feedbackList()).toEqual(['analytics', 'feedback', { rating: undefined, limit: undefined }]);
        });

        it('should generate feedbackList key with rating', () => {
            expect(analyticsKeys.feedbackList('negative')).toEqual(['analytics', 'feedback', { rating: 'negative', limit: undefined }]);
        });

        it('should generate feedbackList key with rating and limit', () => {
            expect(analyticsKeys.feedbackList('positive', 50)).toEqual(['analytics', 'feedback', { rating: 'positive', limit: 50 }]);
        });

        it('should generate sourceMetrics key', () => {
            expect(analyticsKeys.sourceMetrics()).toEqual(['analytics', 'sourceMetrics']);
        });
    });

    describe('useFeedback Hook', () => {
        beforeEach(() => {
            mockApiGet.mockResolvedValue({ data: mockFeedbackResponse });
        });

        it('should fetch feedback data', async () => {
            const { result } = renderHook(() => useFeedback(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true);
            });

            expect(result.current.data).toEqual(mockFeedbackResponse);
        });

        it('should fetch with default limit of 20', async () => {
            renderHook(() => useFeedback(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=20'));
            });
        });

        it('should fetch with custom limit', async () => {
            renderHook(() => useFeedback({ limit: 50 }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=50'));
            });
        });

        it('should fetch with rating filter', async () => {
            renderHook(() => useFeedback({ rating: 'negative' }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('rating=negative'));
            });
        });

        it('should not fetch when disabled', async () => {
            renderHook(() => useFeedback({ enabled: false }), { wrapper: createWrapper() });

            // Give some time for potential fetch
            await new Promise(resolve => setTimeout(resolve, 100));

            expect(mockApiGet).not.toHaveBeenCalled();
        });

        it('should handle fetch error', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useFeedback(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isError).toBe(true);
            });

            expect(result.current.error).toBeDefined();
        });
    });

    describe('useSourceMetrics Hook', () => {
        beforeEach(() => {
            mockApiGet.mockResolvedValue({ data: mockSourceMetricsResponse });
        });

        it('should fetch source metrics', async () => {
            const { result } = renderHook(() => useSourceMetrics(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true);
            });

            expect(result.current.data).toEqual(mockSourceMetricsResponse);
        });

        it('should fetch with default parameters', async () => {
            renderHook(() => useSourceMetrics(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('min_feedback_count=3'));
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=10'));
            });
        });

        it('should fetch with custom minFeedbackCount', async () => {
            renderHook(() => useSourceMetrics({ minFeedbackCount: 5 }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('min_feedback_count=5'));
            });
        });

        it('should fetch with custom limit', async () => {
            renderHook(() => useSourceMetrics({ limit: 20 }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=20'));
            });
        });

        it('should not fetch when disabled', async () => {
            renderHook(() => useSourceMetrics({ enabled: false }), { wrapper: createWrapper() });

            // Give some time for potential fetch
            await new Promise(resolve => setTimeout(resolve, 100));

            expect(mockApiGet).not.toHaveBeenCalled();
        });

        it('should handle fetch error', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useSourceMetrics(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isError).toBe(true);
            });

            expect(result.current.error).toBeDefined();
        });
    });

    describe('Type Exports', () => {
        it('should export FeedbackSummary type fields', () => {
            const summary: FeedbackResponse['summary'] = {
                positive_count: 10,
                negative_count: 5,
                total_count: 15,
                negative_rate_pct: 33.33,
            };

            expect(summary.positive_count).toBe(10);
            expect(summary.negative_count).toBe(5);
            expect(summary.total_count).toBe(15);
            expect(summary.negative_rate_pct).toBe(33.33);
        });

        it('should export FeedbackItem type fields', () => {
            const item: FeedbackResponse['items'][0] = {
                id: 'test',
                rating: 'positive',
                feedback_text: 'Great!',
                query_text: 'Query',
                answer_preview: 'Answer',
                sources: [{ label: 'Source', type: 'pdf' }],
                user_email: 'user@test.com',
                created_at: '2024-01-15',
            };

            expect(item.id).toBe('test');
            expect(item.rating).toBe('positive');
            expect(item.sources).toHaveLength(1);
        });

        it('should export SourceMetric type fields', () => {
            const metric: SourceMetricsResponse['items'][0] = {
                source_label: 'Doc',
                source_type: 'pdf',
                source_url: 'https://example.com',
                positive_count: 10,
                negative_count: 2,
                total_feedback: 12,
                negative_rate_pct: 16.67,
                last_feedback_at: '2024-01-15',
            };

            expect(metric.source_label).toBe('Doc');
            expect(metric.negative_rate_pct).toBe(16.67);
        });
    });
});
