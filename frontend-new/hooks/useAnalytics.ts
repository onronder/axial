/**
 * Analytics Hooks
 * 
 * Provides React Query hooks for fetching analytics data including:
 * - Feedback statistics and items
 * - Source quality metrics
 * 
 * Related Files:
 * - app/dashboard/settings/analytics/page.tsx (Analytics page)
 * - backend/api/v1/feedback.py (API endpoints)
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

export interface FeedbackSummary {
    positive_count: number;
    negative_count: number;
    total_count: number;
    negative_rate_pct: number;
}

export interface FeedbackItem {
    id: string;
    rating: 'positive' | 'negative';
    feedback_text: string | null;
    query_text: string;
    answer_preview: string;
    sources: Array<{
        label?: string;
        type?: string;
        url?: string;
    }>;
    user_email: string;
    created_at: string;
}

export interface FeedbackResponse {
    items: FeedbackItem[];
    total: number;
    has_more: boolean;
    summary: FeedbackSummary;
}

export interface SourceMetric {
    source_label: string;
    source_type: string | null;
    source_url: string | null;
    positive_count: number;
    negative_count: number;
    total_feedback: number;
    negative_rate_pct: number;
    last_feedback_at: string | null;
}

export interface SourceMetricsResponse {
    items: SourceMetric[];
    total: number;
}

// =============================================================================
// Query Key Factory
// =============================================================================

export const analyticsKeys = {
    all: ['analytics'] as const,
    feedback: () => [...analyticsKeys.all, 'feedback'] as const,
    feedbackList: (rating?: string, limit?: number) => [...analyticsKeys.feedback(), { rating, limit }] as const,
    sourceMetrics: () => [...analyticsKeys.all, 'sourceMetrics'] as const,
};

// =============================================================================
// API Functions
// =============================================================================

async function fetchFeedback(rating?: string, limit: number = 20): Promise<FeedbackResponse> {
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (rating) params.set('rating', rating);
    
    const response = await api.get(`/analytics/feedback?${params.toString()}`);
    return response.data;
}

async function fetchSourceMetrics(minFeedbackCount: number = 3, limit: number = 10): Promise<SourceMetricsResponse> {
    const response = await api.get(`/analytics/feedback/sources?min_feedback_count=${minFeedbackCount}&limit=${limit}`);
    return response.data;
}

// =============================================================================
// Hooks
// =============================================================================

export interface UseFeedbackOptions {
    rating?: string;
    limit?: number;
    enabled?: boolean;
}

/**
 * Hook to fetch feedback data
 */
export function useFeedback(options: UseFeedbackOptions = {}) {
    const { rating, limit = 20, enabled = true } = options;
    
    return useQuery({
        queryKey: analyticsKeys.feedbackList(rating, limit),
        queryFn: () => fetchFeedback(rating, limit),
        staleTime: 60_000, // 1 minute
        enabled,
    });
}

export interface UseSourceMetricsOptions {
    minFeedbackCount?: number;
    limit?: number;
    enabled?: boolean;
}

/**
 * Hook to fetch source quality metrics
 */
export function useSourceMetrics(options: UseSourceMetricsOptions = {}) {
    const { minFeedbackCount = 3, limit = 10, enabled = true } = options;
    
    return useQuery({
        queryKey: analyticsKeys.sourceMetrics(),
        queryFn: () => fetchSourceMetrics(minFeedbackCount, limit),
        staleTime: 60_000, // 1 minute
        enabled,
    });
}
