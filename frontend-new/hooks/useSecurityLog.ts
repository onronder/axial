'use client';

import { useQuery } from '@tanstack/react-query';
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
  wipe_pattern: WipePattern;
  wipe_verified: boolean;
  performed_by: string;
  performed_at: string;
  duration_ms: number;
}

interface SecurityLogResponse {
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
  enabled?: boolean;
}

// =============================================================================
// API Function
// =============================================================================

async function fetchSecurityLog(options: UseSecurityLogOptions): Promise<SecurityEvent[]> {
  const params: Record<string, string> = {};

  if (options.search) params.search = options.search;
  if (options.eventType) params.event_type = options.eventType;
  if (options.fromDate) params.from_date = options.fromDate;
  if (options.toDate) params.to_date = options.toDate;
  if (options.limit) params.limit = options.limit.toString();
  if (options.offset) params.offset = options.offset.toString();

  const response = await api.get<SecurityLogResponse>('/admin/security-log', { params });
  return response.data.items;
}

// =============================================================================
// Hook
// =============================================================================

export function useSecurityLog(options: UseSecurityLogOptions = {}) {
  const { enabled = true, ...queryOptions } = options;

  const query = useQuery({
    queryKey: ['security-log', queryOptions],
    queryFn: () => fetchSecurityLog(queryOptions),
    enabled,
    staleTime: 30000, // 30 seconds
    refetchInterval: 60000, // Refetch every minute
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      if (error instanceof Error && (error.message.includes('Unauthorized') || error.message.includes('Admin'))) {
        return false;
      }
      return failureCount < 2;
    },
  });

  return {
    data: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
  };
}

export default useSecurityLog;
