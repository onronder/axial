'use client';

import { useQuery } from '@tanstack/react-query';

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
  const params = new URLSearchParams();

  if (options.search) {
    params.set('search', options.search);
  }
  if (options.eventType) {
    params.set('event_type', options.eventType);
  }
  if (options.fromDate) {
    params.set('from_date', options.fromDate);
  }
  if (options.toDate) {
    params.set('to_date', options.toDate);
  }
  if (options.limit) {
    params.set('limit', options.limit.toString());
  }
  if (options.offset) {
    params.set('offset', options.offset.toString());
  }

  const queryString = params.toString();
  const url = `/api/py/admin/security-log${queryString ? `?${queryString}` : ''}`;

  const response = await fetch(url, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error('Unauthorized - please log in');
    }
    if (response.status === 403) {
      throw new Error('Admin access required to view security logs');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch security log');
  }

  const data: SecurityLogResponse = await response.json();
  return data.items;
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
