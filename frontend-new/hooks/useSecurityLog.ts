'use client';

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { api } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

export type SecurityEventType = 'document_wiped' | 'scope_deleted' | 'chunk_purged' | 'organization_purged';
export type WipePattern = 'dod_5220_22_m' | 'random';

export interface SecurityEvent {
  id: string;
  event_type: SecurityEventType;
  resource_type: string;
  resource_name: string;
  resource_id: string;
  wipe_pattern: WipePattern | null;
  wipe_verified: boolean;
  performed_by: string;
  performed_at: string;
  duration_ms: number;
}

export interface SecurityLogResponse {
  items: SecurityEvent[];
  total: number;
  has_more: boolean;
}

export interface UseSecurityLogOptions {
  search?: string;
  eventType?: string;
  fromDate?: string;
  toDate?: string;
  limit?: number;
  offset?: number;
  page?: number;
  pageSize?: number;
  enabled?: boolean;
}

// =============================================================================
// API Function
// =============================================================================

async function fetchSecurityLog(options: UseSecurityLogOptions): Promise<SecurityLogResponse> {
  const params: Record<string, string> = {};

  if (options.search) params.search = options.search;
  if (options.eventType) params.event_type = options.eventType;
  if (options.fromDate) params.from_date = options.fromDate;
  if (options.toDate) params.to_date = options.toDate;

  // Handle pagination: prefer page/pageSize, fall back to limit/offset
  const pageSize = options.pageSize ?? options.limit ?? 20;
  const page = options.page ?? 0;
  const offset = options.offset ?? page * pageSize;

  params.limit = pageSize.toString();
  params.offset = offset.toString();

  const response = await api.get<SecurityLogResponse>('/admin/security-log', { params });
  return response.data;
}

// =============================================================================
// Hook
// =============================================================================

export function useSecurityLog(options: UseSecurityLogOptions = {}) {
  const { enabled = true, pageSize = 20, page = 0, ...queryOptions } = options;

  const query = useQuery({
    queryKey: ['security-log', { ...queryOptions, page, pageSize }],
    queryFn: () => fetchSecurityLog({ ...queryOptions, page, pageSize }),
    enabled,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    placeholderData: keepPreviousData, // Keep showing old data while fetching new page
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      if (error instanceof Error && (error.message.includes('Unauthorized') || error.message.includes('Admin'))) {
        return false;
      }
      return failureCount < 2;
    },
  });

  const response = query.data;
  const totalPages = response ? Math.ceil(response.total / pageSize) : 0;

  return {
    // Data
    data: response?.items ?? [],
    total: response?.total ?? 0,
    hasMore: response?.has_more ?? false,

    // Pagination info
    page,
    pageSize,
    totalPages,
    hasNextPage: page < totalPages - 1,
    hasPreviousPage: page > 0,

    // Query state
    isLoading: query.isLoading,
    isFetching: query.isFetching,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

export default useSecurityLog;
