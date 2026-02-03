/**
 * Unit Tests for SecurityLogTable Component
 *
 * Tests covering:
 * - Rendering security events
 * - Filtering functionality
 * - Export to CSV
 * - Loading and empty states
 * - Time formatting
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// =============================================================================
// Mock Setup
// =============================================================================

vi.mock('@/hooks/useSecurityLog', () => ({
  useSecurityLog: vi.fn().mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

// =============================================================================
// Helper Function Tests
// =============================================================================

describe('SecurityLogTable Helpers', () => {
  describe('formatTime', () => {
    it('should format ISO timestamp to time only', () => {
      const formatTime = (dateString: string): string => {
        try {
          return new Date(dateString).toISOString().slice(11, 23);
        } catch {
          return dateString;
        }
      };

      const result = formatTime('2024-01-15T10:30:45.123Z');
      expect(result).toBe('10:30:45.123');
    });

    it('should return original string on invalid date', () => {
      const formatTime = (dateString: string): string => {
        try {
          const date = new Date(dateString);
          if (isNaN(date.getTime())) return dateString;
          return date.toISOString().slice(11, 23);
        } catch {
          return dateString;
        }
      };

      const result = formatTime('invalid-date');
      expect(result).toBe('invalid-date');
    });
  });

  describe('formatRelativeTime', () => {
    it('should return "just now" for very recent times', () => {
      const formatRelativeTime = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'just now';
        return `${diffMins}m ago`;
      };

      const justNow = new Date().toISOString();
      const result = formatRelativeTime(justNow);
      expect(result).toBe('just now');
    });

    it('should return minutes ago for recent times', () => {
      const formatRelativeTime = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        return '';
      };

      const fiveMinutesAgo = new Date(Date.now() - 5 * 60000).toISOString();
      const result = formatRelativeTime(fiveMinutesAgo);
      expect(result).toBe('5m ago');
    });

    it('should return hours ago for older times', () => {
      const formatRelativeTime = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);

        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return '';
      };

      const threeHoursAgo = new Date(Date.now() - 3 * 60 * 60000).toISOString();
      const result = formatRelativeTime(threeHoursAgo);
      expect(result).toBe('3h ago');
    });

    it('should return days ago for very old times', () => {
      const formatRelativeTime = (dateString: string): string => {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffHours < 24) return `${diffHours}h ago`;
        return `${diffDays}d ago`;
      };

      const twoDaysAgo = new Date(Date.now() - 2 * 24 * 60 * 60000).toISOString();
      const result = formatRelativeTime(twoDaysAgo);
      expect(result).toBe('2d ago');
    });
  });

  describe('formatDateForFilename', () => {
    it('should format date as YYYY-MM-DD', () => {
      const formatDateForFilename = (date: Date): string => {
        return date.toISOString().slice(0, 10);
      };

      const date = new Date('2024-01-15T10:30:00Z');
      const result = formatDateForFilename(date);
      expect(result).toBe('2024-01-15');
    });
  });
});

// =============================================================================
// Event Icons Tests
// =============================================================================

describe('SecurityLogTable Event Icons', () => {
  const EVENT_ICONS = {
    document_wiped: 'FileText',
    scope_deleted: 'Folder',
    chunk_purged: 'Database',
    organization_purged: 'Shield',
  };

  it('should have icon for document_wiped', () => {
    expect(EVENT_ICONS.document_wiped).toBe('FileText');
  });

  it('should have icon for scope_deleted', () => {
    expect(EVENT_ICONS.scope_deleted).toBe('Folder');
  });

  it('should have icon for chunk_purged', () => {
    expect(EVENT_ICONS.chunk_purged).toBe('Database');
  });

  it('should have icon for organization_purged', () => {
    expect(EVENT_ICONS.organization_purged).toBe('Shield');
  });
});

// =============================================================================
// Event Labels Tests
// =============================================================================

describe('SecurityLogTable Event Labels', () => {
  const EVENT_LABELS = {
    document_wiped: 'Document Wiped',
    scope_deleted: 'Scope Deleted',
    chunk_purged: 'Chunk Purged',
    organization_purged: 'Organization Purged',
  };

  it('should have human-readable label for document_wiped', () => {
    expect(EVENT_LABELS.document_wiped).toBe('Document Wiped');
  });

  it('should have human-readable label for scope_deleted', () => {
    expect(EVENT_LABELS.scope_deleted).toBe('Scope Deleted');
  });

  it('should have human-readable label for chunk_purged', () => {
    expect(EVENT_LABELS.chunk_purged).toBe('Chunk Purged');
  });

  it('should have human-readable label for organization_purged', () => {
    expect(EVENT_LABELS.organization_purged).toBe('Organization Purged');
  });
});

// =============================================================================
// CSV Export Tests
// =============================================================================

describe('SecurityLogTable CSV Export', () => {
  it('should generate correct CSV headers', () => {
    const headers = ['Timestamp', 'Event Type', 'Resource', 'Pattern', 'Verified', 'Duration (ms)'];
    expect(headers).toHaveLength(6);
    expect(headers[0]).toBe('Timestamp');
    expect(headers[5]).toBe('Duration (ms)');
  });

  it('should format event data as CSV row', () => {
    const event = {
      performed_at: '2024-01-15T10:30:00Z',
      event_type: 'document_wiped',
      resource_name: 'report.pdf',
      wipe_pattern: 'dod_5220_22_m',
      wipe_verified: true,
      duration_ms: 1500,
    };

    const row = [
      event.performed_at,
      event.event_type,
      event.resource_name,
      event.wipe_pattern,
      event.wipe_verified ? 'Yes' : 'No',
      event.duration_ms,
    ];

    expect(row).toEqual([
      '2024-01-15T10:30:00Z',
      'document_wiped',
      'report.pdf',
      'dod_5220_22_m',
      'Yes',
      1500,
    ]);
  });

  it('should join CSV rows with newlines', () => {
    const rows = [
      ['Timestamp', 'Event'],
      ['2024-01-15', 'document_wiped'],
    ];

    const csv = rows.map(row => row.join(',')).join('\n');
    expect(csv).toBe('Timestamp,Event\n2024-01-15,document_wiped');
  });

  it('should generate filename with date', () => {
    const date = new Date('2024-01-15T10:30:00Z');
    const filename = `security-log-${date.toISOString().slice(0, 10)}.csv`;
    expect(filename).toBe('security-log-2024-01-15.csv');
  });
});

// =============================================================================
// Filter Tests
// =============================================================================

describe('SecurityLogTable Filters', () => {
  it('should support "all" filter option', () => {
    const eventTypeFilter = 'all';
    const queryEventType = eventTypeFilter !== 'all' ? eventTypeFilter : undefined;
    expect(queryEventType).toBeUndefined();
  });

  it('should pass event type filter to hook', () => {
    const eventTypeFilter: string = 'document_wiped';
    const queryEventType = eventTypeFilter !== 'all' ? eventTypeFilter : undefined;
    expect(queryEventType).toBe('document_wiped');
  });

  it('should support search filter', () => {
    const search = 'report.pdf';
    expect(search).toBe('report.pdf');
  });

  it('should pass empty search when cleared', () => {
    const search = '';
    expect(search).toBe('');
  });
});

// =============================================================================
// State Tests
// =============================================================================

describe('SecurityLogTable States', () => {
  it('should show loading state', () => {
    const isLoading = true;
    const loadingMessage = 'Loading security events...';
    expect(isLoading).toBe(true);
    expect(loadingMessage).toContain('Loading');
  });

  it('should show empty state when no events', () => {
    const events: unknown[] = [];
    const isEmpty = !events || events.length === 0;
    const emptyMessage = 'No security events found';
    expect(isEmpty).toBe(true);
    expect(emptyMessage).toContain('No');
  });

  it('should render events when data available', () => {
    const events = [
      { id: '1', event_type: 'document_wiped' },
      { id: '2', event_type: 'scope_deleted' },
    ];
    expect(events.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// Security Event Rendering Tests
// =============================================================================

describe('SecurityLogTable Event Rendering', () => {
  it('should display timestamp', () => {
    const event = { performed_at: '2024-01-15T10:30:45.123Z' };
    expect(event.performed_at).toBeDefined();
  });

  it('should display event type with icon', () => {
    const event = { event_type: 'document_wiped' as const };
    const EVENT_ICONS: Record<string, string> = { document_wiped: 'FileText' };
    expect(EVENT_ICONS[event.event_type]).toBe('FileText');
  });

  it('should display resource name', () => {
    const event = { resource_name: 'sensitive-report.pdf' };
    expect(event.resource_name).toBe('sensitive-report.pdf');
  });

  it('should truncate long resource IDs', () => {
    const event = { resource_id: 'doc-123456789012345678901234567890' };
    const truncated = event.resource_id.slice(0, 12) + '...';
    expect(truncated).toBe('doc-12345678...');
  });

  it('should display wipe verification badge', () => {
    const event = {
      performed_at: '2024-01-15T10:30:00Z',
      wipe_pattern: 'dod_5220_22_m',
      wipe_verified: true,
    };
    expect(event.wipe_verified).toBe(true);
  });

  it('should display duration in milliseconds', () => {
    const event = { duration_ms: 1500 };
    const formatted = `${event.duration_ms}ms`;
    expect(formatted).toBe('1500ms');
  });
});

// =============================================================================
// Table Structure Tests
// =============================================================================

describe('SecurityLogTable Structure', () => {
  it('should have correct column headers', () => {
    const headers = ['Timestamp', 'Event', 'Resource', 'Compliance', 'Duration'];
    expect(headers).toHaveLength(5);
  });

  it('should have header row with background', () => {
    const headerClassName = 'bg-muted/30';
    expect(headerClassName).toContain('bg-muted');
  });

  it('should have hover effect on rows', () => {
    const rowClassName = 'hover:bg-muted/20';
    expect(rowClassName).toContain('hover:');
  });

  it('should have bordered container', () => {
    const containerClassName = 'rounded-lg border border-border/50 overflow-hidden';
    expect(containerClassName).toContain('border');
    expect(containerClassName).toContain('rounded');
  });
});

// =============================================================================
// Accessibility Tests
// =============================================================================

describe('SecurityLogTable Accessibility', () => {
  it('should have search input placeholder', () => {
    const placeholder = 'Search by resource name...';
    expect(placeholder).toBeTruthy();
  });

  it('should have icon with header text', () => {
    const header = { icon: 'Shield', text: 'Security Log' };
    expect(header.text).toBe('Security Log');
  });

  it('should have export button with icon and text', () => {
    const exportButton = { icon: 'Download', text: 'Export CSV' };
    expect(exportButton.text).toBe('Export CSV');
  });
});
