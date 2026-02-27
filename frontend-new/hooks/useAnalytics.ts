'use client';

/**
 * useAnalytics Hook
 * 
 * Provides feedback analytics data for monitoring AI response quality.
 * Manages fetching, caching, and refreshing of feedback and source metrics.
 * 
 * Features:
 * - Feedback items with pagination and filtering
 * - Summary statistics (positive/negative counts, rates)
 * - Source quality metrics for identifying problematic documents
 * - Date range filtering with preset options
 * - Automatic cache invalidation
 * 
 * @example
 * ```tsx
 * const {
 *   feedbackData,
 *   sourceMetrics,
 *   isLoadingFeedback,
 *   refetchAll
 * } = useAnalytics({
 *   rating: 'negative',
 *   limit: 20,
 *   dateRange: { from: subDays(new Date(), 30), to: new Date() }
 * });
 * ```
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { startOfDay, endOfDay } from 'date-fns';
import { api } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

/**
 * Summary statistics for feedback analytics.
 */
export interface FeedbackSummary {
  /** Number of positive feedback ratings */
  positive_count: number;
  /** Number of negative feedback ratings */
  negative_count: number;
  /** Total feedback count */
  total_count: number;
  /** Percentage of negative feedback (0-100) */
  negative_rate_pct: number;
}

/**
 * Individual feedback item from users.
 */
export interface FeedbackItem {
  /** Unique feedback ID */
  id: string;
  /** User's rating of the response */
  rating: 'positive' | 'negative';
  /** Optional text feedback from user */
  feedback_text: string | null;
  /** The user's original question */
  query_text: string;
  /** Preview of the AI's response */
  answer_preview: string;
  /** Sources used in the response */
  sources: Array<{
    label?: string;
    type?: string;
    url?: string;
  }>;
  /** Email of the user who gave feedback */
  user_email: string;
  /** ISO timestamp of when feedback was given */
  created_at: string;
}

/**
 * Paginated feedback response from API.
 */
export interface FeedbackResponse {
  /** List of feedback items */
  items: FeedbackItem[];
  /** Total number of feedback items matching filters */
  total: number;
  /** Whether more items are available */
  has_more: boolean;
  /** Aggregated summary statistics */
  summary: FeedbackSummary;
}

/**
 * Metrics for a source that appears in feedback.
 */
export interface SourceMetric {
  /** Display label for the source */
  source_label: string;
  /** Type of source (e.g., 'pdf', 'notion') */
  source_type: string | null;
  /** URL to the source if available */
  source_url: string | null;
  /** Number of positive feedback mentions */
  positive_count: number;
  /** Number of negative feedback mentions */
  negative_count: number;
  /** Total feedback count for this source */
  total_feedback: number;
  /** Percentage of negative feedback (0-100) */
  negative_rate_pct: number;
  /** ISO timestamp of last feedback */
  last_feedback_at: string | null;
}

/**
 * Response for source metrics endpoint.
 */
export interface SourceMetricsResponse {
  /** List of source metrics */
  items: SourceMetric[];
  /** Total number of sources with feedback */
  total: number;
}

/**
 * Daily trend data point for the feedback trend chart.
 */
export interface TrendDataPoint {
  date: string;
  positive_count: number;
  negative_count: number;
}

/**
 * Date range for filtering analytics data.
 */
export interface DateRange {
  /** Start date (inclusive) */
  from: Date | null;
  /** End date (inclusive) */
  to: Date | null;
}

/**
 * Options for the useAnalytics hook.
 */
export interface UseAnalyticsOptions {
  /** Filter by feedback rating */
  rating?: 'positive' | 'negative';
  /** Maximum number of feedback items to fetch */
  limit?: number;
  /** Date range filter */
  dateRange?: DateRange;
  /** Whether to enable the queries */
  enabled?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

/** Default number of feedback items to fetch */
const DEFAULT_LIMIT = 20;

/** Cache duration for analytics data (1 minute) */
const STALE_TIME = 60_000;

/** Minimum feedback count for source to appear in metrics */
const MIN_FEEDBACK_COUNT = 3;

/** Maximum sources to show in metrics */
const MAX_SOURCE_METRICS = 10;

// =============================================================================
// Query Keys Factory
// =============================================================================

/**
 * Query key factory for analytics queries.
 * Provides consistent query keys for cache management and invalidation.
 * 
 * @example
 * ```ts
 * // Invalidate all analytics queries
 * queryClient.invalidateQueries({ queryKey: analyticsKeys.all });
 * 
 * // Invalidate specific feedback query
 * queryClient.invalidateQueries({ 
 *   queryKey: analyticsKeys.feedbackList('negative', 20) 
 * });
 * ```
 */
export const analyticsKeys = {
  /** Base key for all analytics queries */
  all: ['analytics'] as const,
  
  /** Base key for feedback queries */
  feedback: () => ['analytics', 'feedback'] as const,
  
  /** Key for feedback list queries with optional filters */
  feedbackList: (rating?: string, limit?: number) => 
    ['analytics', 'feedback', { rating, limit }] as const,
  
  /** Key for source metrics queries */
  sourceMetrics: () => ['analytics', 'sourceMetrics'] as const,
};

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetches feedback data from the analytics API.
 * 
 * @param rating - Filter by feedback rating ('positive' | 'negative')
 * @param limit - Maximum number of items to return
 * @param fromDate - Start of date range filter
 * @param toDate - End of date range filter
 * @returns Paginated feedback response with summary statistics
 * 
 * @throws {Error} If the API request fails
 */
async function fetchFeedback(
  rating?: string,
  limit: number = DEFAULT_LIMIT,
  fromDate?: Date | null,
  toDate?: Date | null
): Promise<FeedbackResponse> {
  const params = new URLSearchParams();
  params.set('limit', String(limit));
  
  if (rating) {
    params.set('rating', rating);
  }
  if (fromDate) {
    params.set('from_date', startOfDay(fromDate).toISOString());
  }
  if (toDate) {
    params.set('to_date', endOfDay(toDate).toISOString());
  }

  const response = await api.get<FeedbackResponse>(
    `/analytics/feedback?${params.toString()}`
  );
  return response.data;
}

/**
 * Fetches source quality metrics from the analytics API.
 * Returns sources that appear frequently in feedback, sorted by negative rate.
 * 
 * @param fromDate - Start of date range filter
 * @param toDate - End of date range filter
 * @returns List of sources with feedback metrics
 * 
 * @throws {Error} If the API request fails
 */
async function fetchSourceMetrics(
  fromDate?: Date | null,
  toDate?: Date | null
): Promise<SourceMetricsResponse> {
  const params = new URLSearchParams();
  params.set('min_feedback_count', String(MIN_FEEDBACK_COUNT));
  params.set('limit', String(MAX_SOURCE_METRICS));
  
  if (fromDate) {
    params.set('from_date', startOfDay(fromDate).toISOString());
  }
  if (toDate) {
    params.set('to_date', endOfDay(toDate).toISOString());
  }

  const response = await api.get<SourceMetricsResponse>(
    `/analytics/feedback/sources?${params.toString()}`
  );
  return response.data;
}

/**
 * Fetches daily feedback trend data from the analytics API.
 */
async function fetchTrend(
  fromDate?: Date | null,
  toDate?: Date | null
): Promise<TrendDataPoint[]> {
  const params = new URLSearchParams();
  if (fromDate) {
    params.set('from_date', startOfDay(fromDate).toISOString());
  }
  if (toDate) {
    params.set('to_date', endOfDay(toDate).toISOString());
  }

  const response = await api.get<TrendDataPoint[]>(
    `/analytics/feedback/trend?${params.toString()}`
  );
  return response.data;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for fetching and managing feedback analytics data.
 * 
 * Provides:
 * - Feedback items with pagination
 * - Summary statistics (positive/negative counts, rates)
 * - Source quality metrics for problematic documents
 * 
 * @param options - Configuration options for the hook
 * @returns Analytics data with loading/error states and refetch functions
 */
export function useAnalytics(options: UseAnalyticsOptions = {}) {
  const queryClient = useQueryClient();
  const {
    rating,
    limit = DEFAULT_LIMIT,
    dateRange = { from: null, to: null },
    enabled = true,
  } = options;

  // Query key components for cache management
  const dateFromKey = dateRange.from?.toISOString() ?? 'all';
  const dateToKey = dateRange.to?.toISOString() ?? 'all';

  // Feedback query
  const feedbackQuery = useQuery({
    queryKey: ['analytics-feedback', rating ?? 'all', limit, dateFromKey, dateToKey],
    queryFn: () => fetchFeedback(rating, limit, dateRange.from, dateRange.to),
    staleTime: STALE_TIME,
    enabled,
    retry: (failureCount, error) => {
      // Don't retry on permission errors
      if (error instanceof Error && error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
  });

  // Source metrics query
  const metricsQuery = useQuery({
    queryKey: ['analytics-source-metrics', dateFromKey, dateToKey],
    queryFn: () => fetchSourceMetrics(dateRange.from, dateRange.to),
    staleTime: STALE_TIME,
    enabled,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
  });

  // Trend query (daily counts from dedicated endpoint)
  const trendQuery = useQuery({
    queryKey: ['analytics-trend', dateFromKey, dateToKey],
    queryFn: () => fetchTrend(dateRange.from, dateRange.to),
    staleTime: STALE_TIME,
    enabled,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
  });

  /**
   * Refetch all analytics data.
   */
  const refetchAll = async () => {
    await Promise.all([
      feedbackQuery.refetch(),
      metricsQuery.refetch(),
      trendQuery.refetch(),
    ]);
  };

  /**
   * Invalidate all analytics queries to force fresh data on next access.
   */
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['analytics-feedback'] });
    queryClient.invalidateQueries({ queryKey: ['analytics-source-metrics'] });
    queryClient.invalidateQueries({ queryKey: ['analytics-trend'] });
  };

  return {
    // Feedback data
    feedbackData: feedbackQuery.data ?? null,
    summary: feedbackQuery.data?.summary ?? null,
    feedbackItems: feedbackQuery.data?.items ?? [],
    hasMoreFeedback: feedbackQuery.data?.has_more ?? false,
    totalFeedback: feedbackQuery.data?.total ?? 0,

    // Source metrics data
    sourceMetrics: metricsQuery.data ?? null,
    sourceItems: metricsQuery.data?.items ?? [],
    totalSources: metricsQuery.data?.total ?? 0,

    // Trend data
    trendData: trendQuery.data ?? [],
    isLoadingTrend: trendQuery.isLoading,

    // Loading states
    isLoadingFeedback: feedbackQuery.isLoading,
    isFetchingFeedback: feedbackQuery.isFetching,
    isLoadingMetrics: metricsQuery.isLoading,
    isFetchingMetrics: metricsQuery.isFetching,
    isLoading: feedbackQuery.isLoading || metricsQuery.isLoading,

    // Error states
    feedbackError: feedbackQuery.error,
    metricsError: metricsQuery.error,
    isError: feedbackQuery.isError || metricsQuery.isError,

    // Actions
    refetchFeedback: feedbackQuery.refetch,
    refetchMetrics: metricsQuery.refetch,
    refetchAll,
    invalidateAll,
  };
}

// =============================================================================
// Individual Hooks (for granular usage)
// =============================================================================

/**
 * Options for the useFeedback hook.
 */
export interface UseFeedbackOptions {
  /** Filter by feedback rating */
  rating?: 'positive' | 'negative';
  /** Maximum number of items to fetch */
  limit?: number;
  /** Start date for filtering (ISO string) */
  fromDate?: string | null;
  /** End date for filtering (ISO string) */
  toDate?: string | null;
  /** Whether to enable the query */
  enabled?: boolean;
}

/**
 * Hook for fetching feedback data only.
 * Use this when you only need feedback items without source metrics.
 * 
 * @param options - Configuration options
 * @returns Feedback data with loading/error states
 * 
 * @example
 * ```tsx
 * const { data, isLoading, refetch } = useFeedback({
 *   rating: 'negative',
 *   limit: 20,
 *   fromDate: '2024-01-01T00:00:00Z',
 * });
 * ```
 */
export function useFeedback(options: UseFeedbackOptions = {}) {
  const {
    rating,
    limit = DEFAULT_LIMIT,
    fromDate,
    toDate,
    enabled = true,
  } = options;

  return useQuery({
    queryKey: analyticsKeys.feedbackList(rating, limit),
    queryFn: () => fetchFeedback(
      rating,
      limit,
      fromDate ? new Date(fromDate) : null,
      toDate ? new Date(toDate) : null
    ),
    staleTime: STALE_TIME,
    enabled,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

/**
 * Options for the useSourceMetrics hook.
 */
export interface UseSourceMetricsOptions {
  /** Start date for filtering (ISO string) */
  fromDate?: string | null;
  /** End date for filtering (ISO string) */
  toDate?: string | null;
  /** Minimum feedback count for source to appear (default: 3) */
  minFeedbackCount?: number;
  /** Maximum sources to return (default: 10) */
  limit?: number;
  /** Whether to enable the query */
  enabled?: boolean;
}

/**
 * Fetches source quality metrics with custom parameters.
 */
async function fetchSourceMetricsWithOptions(
  fromDate?: Date | null,
  toDate?: Date | null,
  minFeedbackCount: number = MIN_FEEDBACK_COUNT,
  limit: number = MAX_SOURCE_METRICS
): Promise<SourceMetricsResponse> {
  const params = new URLSearchParams();
  params.set('min_feedback_count', String(minFeedbackCount));
  params.set('limit', String(limit));
  
  if (fromDate) {
    params.set('from_date', startOfDay(fromDate).toISOString());
  }
  if (toDate) {
    params.set('to_date', endOfDay(toDate).toISOString());
  }

  const response = await api.get<SourceMetricsResponse>(
    `/analytics/feedback/sources?${params.toString()}`
  );
  return response.data;
}

/**
 * Hook for fetching source quality metrics only.
 * Use this when you only need source metrics without feedback items.
 * 
 * @param options - Configuration options
 * @returns Source metrics data with loading/error states
 * 
 * @example
 * ```tsx
 * const { data, isLoading, refetch } = useSourceMetrics({
 *   fromDate: '2024-01-01T00:00:00Z',
 *   toDate: '2024-01-31T23:59:59Z',
 *   minFeedbackCount: 5,
 *   limit: 20,
 * });
 * ```
 */
export function useSourceMetrics(options: UseSourceMetricsOptions = {}) {
  const {
    fromDate,
    toDate,
    minFeedbackCount = MIN_FEEDBACK_COUNT,
    limit = MAX_SOURCE_METRICS,
    enabled = true,
  } = options;

  return useQuery({
    queryKey: analyticsKeys.sourceMetrics(),
    queryFn: () => fetchSourceMetricsWithOptions(
      fromDate ? new Date(fromDate) : null,
      toDate ? new Date(toDate) : null,
      minFeedbackCount,
      limit
    ),
    staleTime: STALE_TIME,
    enabled,
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes('403')) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

export default useAnalytics;
