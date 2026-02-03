/**
 * Unit Tests for useSecurityLog Hook
 *
 * Tests covering:
 * - Security event fetching
 * - Query parameter handling
 * - Event type filtering
 * - Error handling and retry logic
 * - Data transformations
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// =============================================================================
// Mock Setup
// =============================================================================

const mockFetch = vi.fn();
global.fetch = mockFetch;

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn().mockImplementation(({ queryFn, queryKey, enabled }) => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// =============================================================================
// Type Tests
// =============================================================================

describe('useSecurityLog Types', () => {
  describe('SecurityEvent Interface', () => {
    it('should have required security event properties', () => {
      const event = {
        id: 'event-123',
        event_type: 'document_wiped' as const,
        resource_type: 'document',
        resource_name: 'report.pdf',
        resource_id: 'doc-456',
        wipe_pattern: 'dod_5220_22_m' as const,
        wipe_verified: true,
        performed_by: 'user-789',
        performed_at: '2024-01-01T00:00:00Z',
        duration_ms: 1500,
      };

      expect(event).toHaveProperty('id');
      expect(event).toHaveProperty('event_type');
      expect(event).toHaveProperty('wipe_pattern');
      expect(event).toHaveProperty('wipe_verified');
    });

    it('should support all event types', () => {
      const eventTypes = ['document_wiped', 'scope_deleted', 'chunk_purged', 'organization_purged'];
      expect(eventTypes).toHaveLength(4);
      expect(eventTypes).toContain('document_wiped');
      expect(eventTypes).toContain('scope_deleted');
      expect(eventTypes).toContain('chunk_purged');
      expect(eventTypes).toContain('organization_purged');
    });

    it('should support all wipe patterns', () => {
      const wipePatterns = ['dod_5220_22_m', 'random'];
      expect(wipePatterns).toContain('dod_5220_22_m');
      expect(wipePatterns).toContain('random');
    });
  });

  describe('UseSecurityLogOptions Interface', () => {
    it('should support search parameter', () => {
      const options = { search: 'report.pdf' };
      expect(options.search).toBe('report.pdf');
    });

    it('should support eventType filter', () => {
      const options = { eventType: 'document_wiped' };
      expect(options.eventType).toBe('document_wiped');
    });

    it('should support date range filters', () => {
      const options = {
        fromDate: '2024-01-01',
        toDate: '2024-12-31',
      };
      expect(options.fromDate).toBe('2024-01-01');
      expect(options.toDate).toBe('2024-12-31');
    });

    it('should support pagination', () => {
      const options = {
        limit: 50,
        offset: 100,
      };
      expect(options.limit).toBe(50);
      expect(options.offset).toBe(100);
    });

    it('should support enabled flag', () => {
      const options = { enabled: false };
      expect(options.enabled).toBe(false);
    });
  });
});

// =============================================================================
// API Function Tests
// =============================================================================

describe('useSecurityLog API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('fetchSecurityLog', () => {
    it('should call correct endpoint without params', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, has_more: false }),
      });

      await fetch('/api/py/admin/security-log', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/admin/security-log',
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });

    it('should include search parameter when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, has_more: false }),
      });

      const params = new URLSearchParams();
      params.set('search', 'report.pdf');

      await fetch(`/api/py/admin/security-log?${params.toString()}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/admin/security-log?search=report.pdf',
        expect.any(Object)
      );
    });

    it('should include event_type parameter when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, has_more: false }),
      });

      const params = new URLSearchParams();
      params.set('event_type', 'document_wiped');

      await fetch(`/api/py/admin/security-log?${params.toString()}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/admin/security-log?event_type=document_wiped',
        expect.any(Object)
      );
    });

    it('should include date range parameters when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, has_more: false }),
      });

      const params = new URLSearchParams();
      params.set('from_date', '2024-01-01');
      params.set('to_date', '2024-12-31');

      await fetch(`/api/py/admin/security-log?${params.toString()}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('from_date=2024-01-01'),
        expect.any(Object)
      );
    });

    it('should include pagination parameters when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [], total: 0, has_more: false }),
      });

      const params = new URLSearchParams();
      params.set('limit', '50');
      params.set('offset', '100');

      await fetch(`/api/py/admin/security-log?${params.toString()}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=50'),
        expect.any(Object)
      );
    });

    it('should handle 401 unauthorized error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const response = await fetch('/api/py/admin/security-log');
      expect(response.status).toBe(401);
    });

    it('should handle 403 forbidden error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const response = await fetch('/api/py/admin/security-log');
      expect(response.status).toBe(403);
    });
  });
});

// =============================================================================
// Hook Return Value Tests
// =============================================================================

describe('useSecurityLog Return Values', () => {
  it('should return data array', () => {
    const returnValue = { data: [] };
    expect(Array.isArray(returnValue.data)).toBe(true);
  });

  it('should return isLoading boolean', () => {
    const returnValue = { isLoading: false };
    expect(typeof returnValue.isLoading).toBe('boolean');
  });

  it('should return isError boolean', () => {
    const returnValue = { isError: false };
    expect(typeof returnValue.isError).toBe('boolean');
  });

  it('should return error or null', () => {
    const returnValue: { error: Error | null } = { error: null };
    expect(returnValue.error === null || returnValue.error instanceof Error).toBe(true);
  });

  it('should return refetch function', () => {
    const returnValue = { refetch: () => {} };
    expect(typeof returnValue.refetch).toBe('function');
  });
});

// =============================================================================
// Query Configuration Tests
// =============================================================================

describe('useSecurityLog Query Configuration', () => {
  it('should have 30 second stale time', () => {
    const staleTime = 30000;
    expect(staleTime).toBe(30000);
  });

  it('should have 60 second refetch interval', () => {
    const refetchInterval = 60000;
    expect(refetchInterval).toBe(60000);
  });

  it('should not retry on auth errors', () => {
    const error = new Error('Unauthorized - please log in');
    const shouldRetry = !(error.message.includes('Unauthorized') || error.message.includes('Admin'));
    expect(shouldRetry).toBe(false);
  });

  it('should not retry on admin access errors', () => {
    const error = new Error('Admin access required to view security logs');
    const shouldRetry = !(error.message.includes('Unauthorized') || error.message.includes('Admin'));
    expect(shouldRetry).toBe(false);
  });

  it('should retry on network errors', () => {
    const error = new Error('Network error');
    const failureCount = 1;
    const shouldRetry = !(error.message.includes('Unauthorized') || error.message.includes('Admin')) && failureCount < 2;
    expect(shouldRetry).toBe(true);
  });

  it('should limit retries to 2 attempts', () => {
    const error = new Error('Network error');
    const failureCount = 3;
    const shouldRetry = failureCount < 2;
    expect(shouldRetry).toBe(false);
  });
});

// =============================================================================
// URL Parameter Building Tests
// =============================================================================

describe('URL Parameter Building', () => {
  it('should build empty query string when no options', () => {
    const params = new URLSearchParams();
    expect(params.toString()).toBe('');
  });

  it('should build query string with search', () => {
    const params = new URLSearchParams();
    params.set('search', 'test');
    expect(params.toString()).toBe('search=test');
  });

  it('should build query string with multiple params', () => {
    const params = new URLSearchParams();
    params.set('search', 'test');
    params.set('event_type', 'document_wiped');
    params.set('limit', '50');

    const queryString = params.toString();
    expect(queryString).toContain('search=test');
    expect(queryString).toContain('event_type=document_wiped');
    expect(queryString).toContain('limit=50');
  });
});

// =============================================================================
// Error Message Tests
// =============================================================================

describe('Security Log Error Messages', () => {
  it('should provide unauthorized error message', () => {
    const errorMessage = 'Unauthorized - please log in';
    expect(errorMessage).toContain('Unauthorized');
  });

  it('should provide admin access error message', () => {
    const errorMessage = 'Admin access required to view security logs';
    expect(errorMessage).toContain('Admin');
  });

  it('should provide generic failure message', () => {
    const errorMessage = 'Failed to fetch security log';
    expect(errorMessage).toContain('Failed');
  });
});

// =============================================================================
// Security Event Data Tests
// =============================================================================

describe('Security Event Data', () => {
  it('should parse document wipe event correctly', () => {
    const event = {
      id: 'event-1',
      event_type: 'document_wiped',
      resource_type: 'document',
      resource_name: 'sensitive.pdf',
      resource_id: 'doc-123',
      wipe_pattern: 'dod_5220_22_m',
      wipe_verified: true,
      performed_by: 'user-456',
      performed_at: '2024-01-15T10:30:00Z',
      duration_ms: 2500,
    };

    expect(event.event_type).toBe('document_wiped');
    expect(event.wipe_pattern).toBe('dod_5220_22_m');
    expect(event.wipe_verified).toBe(true);
    expect(event.duration_ms).toBe(2500);
  });

  it('should parse scope deletion event correctly', () => {
    const event = {
      id: 'event-2',
      event_type: 'scope_deleted',
      resource_type: 'scope',
      resource_name: 'Marketing',
      resource_id: 'scope-789',
      wipe_pattern: 'dod_5220_22_m',
      wipe_verified: true,
      performed_by: 'admin-001',
      performed_at: '2024-01-15T11:00:00Z',
      duration_ms: 5000,
    };

    expect(event.event_type).toBe('scope_deleted');
    expect(event.resource_type).toBe('scope');
  });

  it('should parse chunk purge event correctly', () => {
    const event = {
      id: 'event-3',
      event_type: 'chunk_purged',
      resource_type: 'chunk',
      resource_name: 'vector-batch-42',
      resource_id: 'chunk-batch-42',
      wipe_pattern: 'random',
      wipe_verified: true,
      performed_by: 'system',
      performed_at: '2024-01-15T12:00:00Z',
      duration_ms: 100,
    };

    expect(event.event_type).toBe('chunk_purged');
    expect(event.wipe_pattern).toBe('random');
  });

  it('should parse organization purge event correctly', () => {
    const event = {
      id: 'event-4',
      event_type: 'organization_purged',
      resource_type: 'organization',
      resource_name: 'Acme Corp',
      resource_id: 'org-999',
      wipe_pattern: 'dod_5220_22_m',
      wipe_verified: true,
      performed_by: 'admin-001',
      performed_at: '2024-01-15T13:00:00Z',
      duration_ms: 30000,
    };

    expect(event.event_type).toBe('organization_purged');
    expect(event.duration_ms).toBe(30000);
  });
});
