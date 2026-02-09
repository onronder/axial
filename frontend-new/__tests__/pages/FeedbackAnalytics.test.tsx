/**
 * Unit Tests for Feedback Analytics Page
 * 
 * Tests for the analytics data structures and hooks
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Mock the api module
const mockApiGet = vi.fn();
vi.mock('@/lib/api', () => ({
    api: {
        get: (url: string) => mockApiGet(url),
    },
    clearAuthCache: vi.fn(),
}));

// Mock data
const mockFeedbackResponse = {
    items: [
        {
            id: 'f1',
            rating: 'positive',
            feedback_text: null,
            query_text: 'What is React?',
            answer_preview: 'React is a JavaScript library...',
            sources: [{ label: 'React Docs', type: 'website' }],
            user_email: 'user1@test.com',
            created_at: '2024-01-15T10:00:00Z',
        },
        {
            id: 'f2',
            rating: 'negative',
            feedback_text: 'Answer was incomplete',
            query_text: 'How to deploy Next.js?',
            answer_preview: 'To deploy Next.js...',
            sources: [{ label: 'Next Docs', type: 'website' }],
            user_email: 'user2@test.com',
            created_at: '2024-01-14T10:00:00Z',
        },
    ],
    total: 10,
    has_more: true,
    summary: {
        positive_count: 8,
        negative_count: 2,
        total_count: 10,
        negative_rate_pct: 20,
    },
};

const mockSourceMetricsResponse = {
    items: [
        {
            source_label: 'Old Documentation',
            source_type: 'pdf',
            source_url: null,
            positive_count: 5,
            negative_count: 10,
            total_feedback: 15,
            negative_rate_pct: 66.67,
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

describe('Feedback Analytics Data Structures', () => {
    describe('FeedbackItem', () => {
        it('should have required properties', () => {
            const item = mockFeedbackResponse.items[0];
            
            expect(item).toHaveProperty('id');
            expect(item).toHaveProperty('rating');
            expect(item).toHaveProperty('query_text');
            expect(item).toHaveProperty('answer_preview');
            expect(item).toHaveProperty('sources');
            expect(item).toHaveProperty('user_email');
            expect(item).toHaveProperty('created_at');
        });
        
        it('should support positive and negative ratings', () => {
            expect(mockFeedbackResponse.items[0].rating).toBe('positive');
            expect(mockFeedbackResponse.items[1].rating).toBe('negative');
        });
        
        it('should support optional feedback text', () => {
            expect(mockFeedbackResponse.items[0].feedback_text).toBeNull();
            expect(mockFeedbackResponse.items[1].feedback_text).toBe('Answer was incomplete');
        });
    });
    
    describe('FeedbackSummary', () => {
        it('should have summary statistics', () => {
            const summary = mockFeedbackResponse.summary;
            
            expect(summary.positive_count).toBe(8);
            expect(summary.negative_count).toBe(2);
            expect(summary.total_count).toBe(10);
            expect(summary.negative_rate_pct).toBe(20);
        });
        
        it('should calculate negative rate correctly', () => {
            const { positive_count, negative_count, negative_rate_pct } = mockFeedbackResponse.summary;
            const total = positive_count + negative_count;
            const calculatedRate = Math.round((negative_count / total) * 100);
            expect(calculatedRate).toBe(negative_rate_pct);
        });
    });
    
    describe('SourceMetric', () => {
        it('should have required properties', () => {
            const metric = mockSourceMetricsResponse.items[0];
            
            expect(metric).toHaveProperty('source_label');
            expect(metric).toHaveProperty('source_type');
            expect(metric).toHaveProperty('positive_count');
            expect(metric).toHaveProperty('negative_count');
            expect(metric).toHaveProperty('total_feedback');
            expect(metric).toHaveProperty('negative_rate_pct');
        });
        
        it('should identify problematic sources', () => {
            const metric = mockSourceMetricsResponse.items[0];
            const isProblematic = metric.negative_rate_pct > 50;
            expect(isProblematic).toBe(true);
        });
    });
    
    describe('Pagination', () => {
        it('should indicate more items available', () => {
            expect(mockFeedbackResponse.has_more).toBe(true);
            expect(mockFeedbackResponse.total).toBe(10);
        });
    });
});

describe('useAnalytics Hook', () => {
    describe('Query Key Factory', () => {
        it('should create correct query keys', async () => {
            const { analyticsKeys } = await import('@/hooks/useAnalytics');
            
            expect(analyticsKeys.all).toEqual(['analytics']);
            expect(analyticsKeys.feedback()).toEqual(['analytics', 'feedback']);
            expect(analyticsKeys.feedbackList('negative', 20)).toEqual(['analytics', 'feedback', { rating: 'negative', limit: 20 }]);
            expect(analyticsKeys.sourceMetrics()).toEqual(['analytics', 'sourceMetrics']);
        });
    });

    describe('useFeedback Hook', () => {
        beforeEach(() => {
            vi.clearAllMocks();
            mockApiGet.mockResolvedValue({ data: mockFeedbackResponse });
        });

        it('should fetch feedback data', async () => {
            const { useFeedback } = await import('@/hooks/useAnalytics');
            const { result } = renderHook(() => useFeedback(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true);
            });

            expect(result.current.data).toEqual(mockFeedbackResponse);
        });

        it('should fetch with default limit', async () => {
            const { useFeedback } = await import('@/hooks/useAnalytics');
            renderHook(() => useFeedback(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=20'));
            });
        });

        it('should fetch with custom limit', async () => {
            const { useFeedback } = await import('@/hooks/useAnalytics');
            renderHook(() => useFeedback({ limit: 50 }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('limit=50'));
            });
        });

        it('should filter by rating', async () => {
            const { useFeedback } = await import('@/hooks/useAnalytics');
            renderHook(() => useFeedback({ rating: 'negative' }), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('rating=negative'));
            });
        });

        it('should not fetch when disabled', async () => {
            const { useFeedback } = await import('@/hooks/useAnalytics');
            renderHook(() => useFeedback({ enabled: false }), { wrapper: createWrapper() });

            await new Promise(resolve => setTimeout(resolve, 100));
            expect(mockApiGet).not.toHaveBeenCalled();
        });
    });

    describe('useSourceMetrics Hook', () => {
        beforeEach(() => {
            vi.clearAllMocks();
            mockApiGet.mockResolvedValue({ data: mockSourceMetricsResponse });
        });

        it('should fetch source metrics', async () => {
            const { useSourceMetrics } = await import('@/hooks/useAnalytics');
            const { result } = renderHook(() => useSourceMetrics(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isSuccess).toBe(true);
            });

            expect(result.current.data).toEqual(mockSourceMetricsResponse);
        });

        it('should fetch with default parameters', async () => {
            const { useSourceMetrics } = await import('@/hooks/useAnalytics');
            renderHook(() => useSourceMetrics(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(mockApiGet).toHaveBeenCalledWith(expect.stringContaining('min_feedback_count=3'));
            });
        });

        it('should not fetch when disabled', async () => {
            const { useSourceMetrics } = await import('@/hooks/useAnalytics');
            renderHook(() => useSourceMetrics({ enabled: false }), { wrapper: createWrapper() });

            await new Promise(resolve => setTimeout(resolve, 100));
            expect(mockApiGet).not.toHaveBeenCalled();
        });
    });
});

describe('Authorization Logic', () => {
    it('should identify authorized roles', () => {
        const profiles = [
            { role: 'admin' },
            { role: 'editor' },
            { role: 'viewer' },
            { role: null }, // Owner
        ];
        
        const isAuthorized = (profile: { role: string | null }) => 
            profile.role === 'admin' || profile.role === null;
        
        expect(isAuthorized(profiles[0])).toBe(true);  // Admin
        expect(isAuthorized(profiles[1])).toBe(false); // Editor
        expect(isAuthorized(profiles[2])).toBe(false); // Viewer
        expect(isAuthorized(profiles[3])).toBe(true);  // Owner
    });
});

describe('Filtering Logic', () => {
    it('should filter feedback by rating', () => {
        const items = mockFeedbackResponse.items;
        
        const positive = items.filter(i => i.rating === 'positive');
        const negative = items.filter(i => i.rating === 'negative');
        
        expect(positive).toHaveLength(1);
        expect(negative).toHaveLength(1);
    });
    
    it('should filter sources by negative rate', () => {
        const sources = mockSourceMetricsResponse.items;
        
        const problematic = sources.filter(s => s.negative_rate_pct > 50);
        const acceptable = sources.filter(s => s.negative_rate_pct <= 50);
        
        expect(problematic).toHaveLength(1);
        expect(acceptable).toHaveLength(0);
    });
});
