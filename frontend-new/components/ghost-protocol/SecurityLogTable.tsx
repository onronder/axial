'use client';

/**
 * SecurityLogTable Component
 * 
 * Displays a paginated, filterable table of security events from Ghost Protocol.
 * Shows document wipes, scope deletions, chunk purges, and organization purges
 * with DoD 5220.22-M compliance verification badges.
 * 
 * Features:
 * - Real-time search with debounced API calls
 * - Event type filtering
 * - Configurable pagination
 * - CSV export functionality
 * - Compliance verification badges
 * 
 * @example
 * ```tsx
 * <SecurityLogTable />
 * ```
 */

import { useState, useCallback, useRef, useEffect, useDeferredValue } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Shield,
  FileText,
  Folder,
  Database,
  Download,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Loader2,
} from 'lucide-react';
import { WipeVerificationBadge } from './WipeVerificationBadge';
import { useSecurityLog, SecurityEvent } from '@/hooks/useSecurityLog';

// =============================================================================
// Constants
// =============================================================================

/** Icon mapping for event types */
const EVENT_ICONS: Record<string, typeof Shield> = {
  document_wiped: FileText,
  scope_deleted: Folder,
  chunk_purged: Database,
  organization_purged: Shield,
};

/** Human-readable labels for event types */
const EVENT_LABELS: Record<string, string> = {
  document_wiped: 'Document Wiped',
  scope_deleted: 'Scope Deleted',
  chunk_purged: 'Chunk Purged',
  organization_purged: 'Organization Purged',
};

/** Available page size options */
const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;

/** Debounce delay for search input (ms) */
const SEARCH_DEBOUNCE_MS = 300;

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Formats an ISO date string to display time (HH:MM:SS.mmm).
 * 
 * @param dateString - ISO date string
 * @returns Formatted time string
 */
function formatTime(dateString: string): string {
  try {
    return new Date(dateString).toISOString().slice(11, 23);
  } catch {
    return dateString;
  }
}

/**
 * Formats an ISO date string to a relative time description.
 * 
 * @param dateString - ISO date string
 * @returns Relative time string (e.g., "5m ago", "2h ago", "3d ago")
 */
function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    return `${diffDays}d ago`;
  } catch {
    return '';
  }
}

/**
 * Formats a Date object to YYYY-MM-DD for filenames.
 * 
 * @param date - Date object
 * @returns Formatted date string
 */
function formatDateForFilename(date: Date): string {
  return date.toISOString().slice(0, 10);
}

// =============================================================================
// Component
// =============================================================================

export function SecurityLogTable() {
  // Pagination state
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(20);

  // Filter state - use controlled input with deferred search for smooth UX
  const [searchInput, setSearchInput] = useState('');
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('all');
  
  // Debounce ref for cleanup
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Use deferred value as backup for smoother transitions
  const deferredSearch = useDeferredValue(debouncedSearch);

  /**
   * Handle search input changes with proper debouncing.
   * Resets pagination immediately for better UX while debouncing the API call.
   * 
   * @param value - New search input value
   */
  const handleSearchChange = useCallback((value: string) => {
    setSearchInput(value);
    setPage(0); // Reset to first page immediately for better UX
    
    // Clear existing timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    
    // Set new debounced search after delay
    debounceTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
    }, SEARCH_DEBOUNCE_MS);
  }, []);

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  /**
   * Handle event type filter changes.
   * Resets pagination to first page when filter changes.
   * 
   * @param value - New event type filter value
   */
  const handleEventTypeChange = useCallback((value: string) => {
    setEventTypeFilter(value);
    setPage(0);
  }, []);

  /**
   * Handle page size changes.
   * Resets pagination to first page when page size changes.
   * 
   * @param value - New page size as string
   */
  const handlePageSizeChange = useCallback((value: string) => {
    const newPageSize = parseInt(value, 10);
    setPageSize(newPageSize);
    setPage(0);
  }, []);

  const {
    data: events,
    total,
    isLoading,
    isFetching,
    totalPages,
    hasNextPage,
    hasPreviousPage,
  } = useSecurityLog({
    search: deferredSearch, // Use deferred value for smoother API transitions
    eventType: eventTypeFilter !== 'all' ? eventTypeFilter : undefined,
    page,
    pageSize,
  });

  // Show subtle loading indicator when input doesn't match API search
  const isSearchPending = searchInput !== deferredSearch;

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Event Type', 'Resource', 'Pattern', 'Verified', 'Duration (ms)'],
      ...(events || []).map((e: SecurityEvent) => [
        e.performed_at,
        e.event_type,
        e.resource_name,
        e.wipe_pattern,
        e.wipe_verified ? 'Yes' : 'No',
        e.duration_ms,
      ]),
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `security-log-${formatDateForFilename(new Date())}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Pagination handlers
  const goToFirstPage = () => setPage(0);
  const goToPreviousPage = () => setPage((prev) => Math.max(0, prev - 1));
  const goToNextPage = () => setPage((prev) => Math.min(totalPages - 1, prev + 1));
  const goToLastPage = () => setPage(totalPages - 1);

  const startItem = page * pageSize + 1;
  const endItem = Math.min((page + 1) * pageSize, total);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-cyan-400" />
          <h2 className="text-lg font-semibold">Security Log</h2>
          {total > 0 && (
            <span className="text-sm text-muted-foreground">
              ({total.toLocaleString()} events)
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          className="gap-2"
          disabled={!events || events.length === 0}
        >
          <Download className="h-4 w-4" />
          Export CSV
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by resource name..."
            value={searchInput}
            onChange={(e) => handleSearchChange(e.target.value)}
            className="pl-9 pr-8"
            aria-label="Search security events"
          />
          {/* Show subtle loading indicator while search is pending */}
          {isSearchPending && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
          )}
        </div>
        <Select value={eventTypeFilter} onValueChange={handleEventTypeChange}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Event type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Events</SelectItem>
            <SelectItem value="document_wiped">Document Wiped</SelectItem>
            <SelectItem value="scope_deleted">Scope Deleted</SelectItem>
            <SelectItem value="chunk_purged">Chunk Purged</SelectItem>
            <SelectItem value="organization_purged">Organization Purged</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border/50 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead className="w-48">Timestamp</TableHead>
              <TableHead>Event</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead className="text-center">Compliance</TableHead>
              <TableHead className="text-right">Duration</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8">
                  <div className="flex items-center justify-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Loading security events...</span>
                  </div>
                </TableCell>
              </TableRow>
            ) : !events || events.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center py-8 text-muted-foreground">
                  {deferredSearch || eventTypeFilter !== 'all'
                    ? 'No security events match your filters'
                    : 'No security events found'}
                </TableCell>
              </TableRow>
            ) : (
              events.map((event: SecurityEvent) => {
                const Icon = EVENT_ICONS[event.event_type] || Shield;
                return (
                  <TableRow key={event.id} className="hover:bg-muted/20">
                    <TableCell className="font-mono text-xs">
                      <div>{formatTime(event.performed_at)}</div>
                      <div className="text-muted-foreground">
                        {formatRelativeTime(event.performed_at)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 text-muted-foreground" />
                        <span className="text-sm">{EVENT_LABELS[event.event_type] || event.event_type}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="max-w-[200px]">
                        <div className="truncate text-sm">{event.resource_name}</div>
                        <div className="text-[10px] font-mono text-muted-foreground">
                          {event.resource_id.slice(0, 12)}...
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-center">
                      <WipeVerificationBadge
                        wipedAt={event.performed_at}
                        pattern={event.wipe_pattern}
                        verified={event.wipe_verified}
                        variant="compact"
                      />
                    </TableCell>
                    <TableCell className="text-right font-mono text-xs">
                      {event.duration_ms}ms
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination Controls */}
      {total > 0 && (
        <div className="flex items-center justify-between px-2">
          {/* Page size selector */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-muted-foreground">Rows per page:</span>
            <Select value={pageSize.toString()} onValueChange={handlePageSizeChange}>
              <SelectTrigger className="w-16 h-8">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <SelectItem key={size} value={size.toString()}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Page info and navigation */}
          <div className="flex items-center gap-4">
            <span className="text-sm text-muted-foreground">
              {total > 0 ? (
                <>
                  {startItem}-{endItem} of {total.toLocaleString()}
                </>
              ) : (
                '0 results'
              )}
            </span>

            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={goToFirstPage}
                disabled={!hasPreviousPage || isFetching}
                aria-label="First page"
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={goToPreviousPage}
                disabled={!hasPreviousPage || isFetching}
                aria-label="Previous page"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              <span className="mx-2 text-sm">
                Page {page + 1} of {totalPages || 1}
              </span>

              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={goToNextPage}
                disabled={!hasNextPage || isFetching}
                aria-label="Next page"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={goToLastPage}
                disabled={!hasNextPage || isFetching}
                aria-label="Last page"
              >
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </div>

            {/* Loading indicator during pagination */}
            {isFetching && !isLoading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default SecurityLogTable;
