'use client';

/**
 * useAuditLogs Hook
 * 
 * Provides audit log data for tracking administrative actions in the workspace.
 * Manages fetching, filtering, pagination, and caching of audit log entries.
 * 
 * Features:
 * - Server-side filtering by action type, resource type, and date range
 * - Pagination with configurable page size
 * - Client-side search for quick filtering
 * - User profile enrichment (email, name)
 * - CSV export capability
 * 
 * Security:
 * - Only team admins and owners can access audit logs
 * - Logs are organization-scoped (shows all team members' actions)
 * 
 * @example
 * ```tsx
 * const {
 *   logs,
 *   total,
 *   isLoading,
 *   goToPage,
 *   filterBySearch
 * } = useAuditLogs({
 *   action: 'document.delete',
 *   dateRange: '7d',
 *   page: 0
 * });
 * ```
 */

import { useQuery, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { subDays, format } from 'date-fns';
import { api } from '@/lib/api';

// =============================================================================
// Types
// =============================================================================

/**
 * Single audit log entry.
 */
export interface AuditLogEntry {
  /** Unique log entry ID */
  id: string;
  /** User ID who performed the action (null for system actions) */
  user_id: string | null;
  /** User's email address */
  user_email: string | null;
  /** User's display name */
  user_name: string | null;
  /** Action type (e.g., 'document.delete', 'team.member_invite') */
  action: string;
  /** Type of resource affected (e.g., 'document', 'team') */
  resource_type: string | null;
  /** ID of the affected resource */
  resource_id: string | null;
  /** Additional action details as key-value pairs */
  details: Record<string, unknown>;
  /** IP address of the request */
  ip_address: string | null;
  /** ISO timestamp of when the action occurred */
  created_at: string;
}

/**
 * Paginated audit log response from API.
 */
export interface AuditLogResponse {
  /** List of audit log entries */
  items: AuditLogEntry[];
  /** Total count of matching entries */
  total: number;
  /** Whether more entries exist beyond current page */
  has_more: boolean;
}

/**
 * Available action types for filtering.
 */
export interface AuditAction {
  /** Filter value to send to API */
  value: string;
  /** Human-readable label for UI */
  label: string;
}

/**
 * Available resource types for filtering.
 */
export interface ResourceType {
  /** Filter value to send to API */
  value: string;
  /** Human-readable label for UI */
  label: string;
}

/**
 * Date range preset configuration.
 */
export interface DateRangePreset {
  /** Preset identifier */
  value: string;
  /** Human-readable label */
  label: string;
  /** Number of days to look back (null for all time) */
  days: number | null;
}

/**
 * Options for the useAuditLogs hook.
 */
export interface UseAuditLogsOptions {
  /** Filter by action type (use 'all' for no filter) */
  action?: string;
  /** Filter by resource type (use 'all' for no filter) */
  resourceType?: string;
  /** Date range preset (e.g., '7d', '30d', 'all') */
  dateRange?: string;
  /** Current page (0-indexed) */
  page?: number;
  /** Number of items per page */
  pageSize?: number;
  /** Whether to enable the query */
  enabled?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

/** Default page size for audit logs */
const DEFAULT_PAGE_SIZE = 20;

/** Cache duration for audit log data (30 seconds) */
const STALE_TIME = 30_000;

/**
 * Available action types for filtering.
 * SYNC WARNING: This list should match backend/api/v1/admin.py AUDIT_ACTIONS
 */
export const AUDIT_ACTIONS: AuditAction[] = [
  { value: 'all', label: 'All Actions' },
  { value: 'document.delete', label: 'Document Delete' },
  { value: 'document.update', label: 'Document Update' },
  { value: 'document.wipe', label: 'Document Wipe' },
  { value: 'chat.delete', label: 'Chat Delete' },
  { value: 'connector.sync_start', label: 'Sync Started' },
  { value: 'connector.sync_success', label: 'Sync Success' },
  { value: 'connector.sync_fail', label: 'Sync Failed' },
  { value: 'scope.delete', label: 'Scope Delete' },
  { value: 'settings.update', label: 'Settings Update' },
  { value: 'team.member_invite', label: 'Team Invite' },
  { value: 'team.member_remove', label: 'Team Remove' },
  { value: 'gdpr.anonymization_requested', label: 'GDPR Request' },
  { value: 'gdpr.anonymization_completed', label: 'GDPR Completed' },
];

/**
 * Available resource types for filtering.
 */
export const RESOURCE_TYPES: ResourceType[] = [
  { value: 'all', label: 'All Resources' },
  { value: 'document', label: 'Documents' },
  { value: 'chat', label: 'Chats' },
  { value: 'connector', label: 'Connectors' },
  { value: 'user', label: 'Users' },
  { value: 'team', label: 'Team' },
  { value: 'scope', label: 'Scopes' },
];

/**
 * Date range presets for filtering.
 */
export const DATE_RANGE_PRESETS: DateRangePreset[] = [
  { value: '1d', label: 'Last 24 hours', days: 1 },
  { value: '7d', label: 'Last 7 days', days: 7 },
  { value: '30d', label: 'Last 30 days', days: 30 },
  { value: '90d', label: 'Last 90 days', days: 90 },
  { value: 'all', label: 'All time', days: null },
];

// =============================================================================
// API Functions
// =============================================================================

/**
 * Fetches audit logs from the admin API.
 * 
 * @param options - Filter and pagination options
 * @returns Paginated audit log response
 * 
 * @throws {Error} If the API request fails or user lacks permission
 */
async function fetchAuditLogs(options: {
  action?: string;
  resourceType?: string;
  dateRange?: string;
  limit: number;
  offset: number;
}): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  params.set('limit', options.limit.toString());
  params.set('offset', options.offset.toString());

  if (options.action && options.action !== 'all') {
    params.set('action', options.action);
  }
  if (options.resourceType && options.resourceType !== 'all') {
    params.set('resource_type', options.resourceType);
  }
  if (options.dateRange && options.dateRange !== 'all') {
    const preset = DATE_RANGE_PRESETS.find(p => p.value === options.dateRange);
    if (preset?.days) {
      const fromDate = subDays(new Date(), preset.days);
      params.set('from_date', fromDate.toISOString());
    }
  }

  const response = await api.get<AuditLogResponse>(
    `/admin/audit-logs?${params.toString()}`
  );
  return response.data;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Formats an action type for display.
 * Converts 'document.delete' to 'Document Delete'.
 * 
 * @param action - Action type string
 * @returns Formatted action string
 */
export function formatAction(action: string): string {
  return action
    .split('.')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

/**
 * Generates CSV content from audit log entries.
 * 
 * @param logs - Audit log entries to export
 * @returns CSV string ready for download
 */
export function generateAuditLogCSV(logs: AuditLogEntry[]): string {
  const headers = [
    'Timestamp',
    'User Name',
    'User Email',
    'Action',
    'Resource Type',
    'Resource ID',
    'Details',
    'IP Address',
  ];

  const rows = logs.map((log) => [
    log.created_at,
    log.user_name || '',
    log.user_email || '',
    log.action,
    log.resource_type || '',
    log.resource_id || '',
    JSON.stringify(log.details),
    log.ip_address || '',
  ]);

  const csvContent = [
    headers.join(','),
    ...rows.map((row) =>
      row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')
    ),
  ].join('\n');

  return csvContent;
}

/**
 * Downloads audit logs as a CSV file.
 * 
 * @param logs - Audit log entries to export
 * @param filename - Optional custom filename (without extension)
 */
export function downloadAuditLogCSV(
  logs: AuditLogEntry[],
  filename?: string
): void {
  const csvContent = generateAuditLogCSV(logs);
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = filename || `audit-logs-${format(new Date(), 'yyyy-MM-dd')}.csv`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for fetching and managing audit logs with filtering and pagination.
 * 
 * Features:
 * - Server-side filtering by action, resource type, and date range
 * - Pagination with configurable page size
 * - Automatic refetch on filter changes
 * - Client-side search capability
 * - CSV export utilities
 * 
 * @param options - Configuration options for the hook
 * @returns Audit log data with loading/error states and actions
 */
export function useAuditLogs(options: UseAuditLogsOptions = {}) {
  const queryClient = useQueryClient();
  const {
    action = 'all',
    resourceType = 'all',
    dateRange = '7d',
    page = 0,
    pageSize = DEFAULT_PAGE_SIZE,
    enabled = true,
  } = options;

  const offset = page * pageSize;

  const query = useQuery({
    queryKey: ['audit-logs', { action, resourceType, dateRange, page, pageSize }],
    queryFn: () =>
      fetchAuditLogs({
        action,
        resourceType,
        dateRange,
        limit: pageSize,
        offset,
      }),
    staleTime: STALE_TIME,
    enabled,
    placeholderData: keepPreviousData,
    retry: (failureCount, error) => {
      // Don't retry on auth/permission errors
      if (error instanceof Error) {
        const message = error.message.toLowerCase();
        if (message.includes('403') || message.includes('unauthorized')) {
          return false;
        }
      }
      return failureCount < 2;
    },
  });

  const totalPages = query.data ? Math.ceil(query.data.total / pageSize) : 0;

  /**
   * Invalidate and refetch audit logs.
   */
  const invalidateAndRefetch = async () => {
    await queryClient.invalidateQueries({ queryKey: ['audit-logs'] });
  };

  /**
   * Filter logs by search query (client-side).
   * Searches across action, resource type, resource ID, and details.
   * 
   * @param searchQuery - Text to search for
   * @returns Filtered audit log entries
   */
  const filterBySearch = (searchQuery: string): AuditLogEntry[] => {
    if (!query.data?.items || !searchQuery.trim()) {
      return query.data?.items ?? [];
    }

    const lowerQuery = searchQuery.toLowerCase().trim();
    return query.data.items.filter((log) =>
      log.action.toLowerCase().includes(lowerQuery) ||
      log.resource_type?.toLowerCase().includes(lowerQuery) ||
      log.resource_id?.toLowerCase().includes(lowerQuery) ||
      log.user_email?.toLowerCase().includes(lowerQuery) ||
      log.user_name?.toLowerCase().includes(lowerQuery) ||
      JSON.stringify(log.details).toLowerCase().includes(lowerQuery)
    );
  };

  /**
   * Export current logs as CSV file.
   * 
   * @param searchQuery - Optional search query to filter before export
   */
  const exportToCSV = (searchQuery?: string) => {
    const logsToExport = searchQuery
      ? filterBySearch(searchQuery)
      : query.data?.items ?? [];
    downloadAuditLogCSV(logsToExport);
  };

  return {
    // Data
    logs: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    hasMore: query.data?.has_more ?? false,

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

    // Actions
    refetch: query.refetch,
    invalidateAndRefetch,
    filterBySearch,
    exportToCSV,

    // Utilities (re-exported for convenience)
    formatAction,
  };
}

export default useAuditLogs;
