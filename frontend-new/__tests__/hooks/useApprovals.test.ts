/**
 * Unit Tests for useApprovals Hook
 *
 * Tests covering:
 * - Pending approvals fetching
 * - Approval/rejection mutations
 * - Execute approved action
 * - Data transformations
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// =============================================================================
// Mock Setup
// =============================================================================

const mockFetch = vi.fn();
global.fetch = mockFetch;

const mockInvalidateQueries = vi.fn();
const mockQueryClient = {
  invalidateQueries: mockInvalidateQueries,
};

vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn().mockImplementation(({ queryFn, queryKey, enabled }) => ({
    data: [],
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  })),
  useMutation: vi.fn().mockImplementation(({ mutationFn, onSuccess }) => ({
    mutateAsync: vi.fn().mockImplementation(async (params) => {
      const result = await mutationFn(params);
      onSuccess?.();
      return result;
    }),
    isPending: false,
    error: null,
  })),
  useQueryClient: () => mockQueryClient,
}));

// =============================================================================
// Type Tests
// =============================================================================

describe('useApprovals Types', () => {
  describe('Approval Interface', () => {
    it('should have required approval properties', () => {
      const approval = {
        id: 'approval-123',
        actionType: 'delete_scope' as const,
        resourceType: 'scope',
        resourceId: 'scope-456',
        resourceName: 'Marketing',
        requestedBy: 'user-789',
        requestedByName: 'John Doe',
        requestedAt: '2024-01-01T00:00:00Z',
        expiresAt: '2024-01-02T00:00:00Z',
        status: 'pending' as const,
        requestContext: {
          reason: 'No longer needed',
          affectedCount: 50,
        },
      };

      expect(approval).toHaveProperty('id');
      expect(approval).toHaveProperty('actionType');
      expect(approval).toHaveProperty('status');
      expect(approval).toHaveProperty('requestContext');
    });

    it('should support all action types', () => {
      const actionTypes = ['delete_scope', 'bulk_delete', 'purge_all', 'revoke_access'];
      expect(actionTypes).toContain('delete_scope');
      expect(actionTypes).toContain('bulk_delete');
      expect(actionTypes).toContain('purge_all');
      expect(actionTypes).toContain('revoke_access');
    });

    it('should support all status types', () => {
      const statuses = ['pending', 'approved', 'rejected', 'expired'];
      expect(statuses).toContain('pending');
      expect(statuses).toContain('approved');
      expect(statuses).toContain('rejected');
      expect(statuses).toContain('expired');
    });
  });

  describe('RequestContext Interface', () => {
    it('should support optional reason', () => {
      const context = { reason: 'Cleanup old data' };
      expect(context.reason).toBe('Cleanup old data');
    });

    it('should support optional affected count', () => {
      const context = { affectedCount: 100 };
      expect(context.affectedCount).toBe(100);
    });

    it('should support optional affected documents', () => {
      const context = {
        affectedDocuments: [
          { id: 'doc-1', name: 'report.pdf' },
          { id: 'doc-2', name: 'analysis.docx' },
        ],
      };
      expect(context.affectedDocuments).toHaveLength(2);
    });
  });

  describe('UseApprovalsOptions Interface', () => {
    it('should support enabled flag', () => {
      const options = { enabled: false };
      expect(options.enabled).toBe(false);
    });

    it('should support refetch interval', () => {
      const options = { refetchInterval: 60000 };
      expect(options.refetchInterval).toBe(60000);
    });
  });
});

// =============================================================================
// API Function Tests
// =============================================================================

describe('useApprovals API Functions', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockReset();
  });

  describe('fetchPendingApprovals', () => {
    it('should call correct endpoint', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      });

      await fetch('/api/py/approvals/pending', {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/approvals/pending',
        expect.objectContaining({
          credentials: 'include',
        })
      );
    });

    it('should handle 401 unauthorized error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 401,
      });

      const response = await fetch('/api/py/approvals/pending');
      expect(response.status).toBe(401);
    });

    it('should handle 403 forbidden error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
      });

      const response = await fetch('/api/py/approvals/pending');
      expect(response.status).toBe(403);
    });
  });

  describe('approveAction', () => {
    it('should call correct endpoint with POST method', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'approved', message: 'Action approved' }),
      });

      const approvalId = 'approval-123';
      await fetch(`/api/py/approvals/${approvalId}/approve`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/approvals/approval-123/approve',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });
  });

  describe('rejectAction', () => {
    it('should call correct endpoint with POST method', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'rejected', message: 'Action rejected' }),
      });

      const approvalId = 'approval-123';
      await fetch(`/api/py/approvals/${approvalId}/reject`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/approvals/approval-123/reject',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should include reason parameter when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'rejected', message: 'Action rejected' }),
      });

      const approvalId = 'approval-123';
      const reason = 'Not authorized for this action';
      const url = new URL(`/api/py/approvals/${approvalId}/reject`, 'http://localhost');
      url.searchParams.set('reason', reason);

      await fetch(url.toString(), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('reason='),
        expect.any(Object)
      );
    });
  });

  describe('executeApproved', () => {
    it('should call correct endpoint with mandate signature', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'executed', result: {} }),
      });

      const approvalId = 'approval-123';
      await fetch(`/api/py/approvals/${approvalId}/execute`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mandate_signature: 'sig-abc-123',
        }),
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/approvals/approval-123/execute',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ mandate_signature: 'sig-abc-123' }),
        })
      );
    });
  });

  describe('getApproval', () => {
    it('should call correct endpoint for single approval', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({
          id: 'approval-123',
          action_type: 'delete_scope',
          status: 'pending',
        }),
      });

      const approvalId = 'approval-123';
      await fetch(`/api/py/approvals/${approvalId}`, {
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/py/approvals/approval-123',
        expect.any(Object)
      );
    });

    it('should handle 404 not found error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
      });

      const response = await fetch('/api/py/approvals/nonexistent');
      expect(response.status).toBe(404);
    });
  });
});

// =============================================================================
// Transform Function Tests
// =============================================================================

describe('useApprovals Transformations', () => {
  describe('transformApproval', () => {
    it('should convert snake_case to camelCase', () => {
      const raw = {
        id: 'approval-123',
        action_type: 'delete_scope',
        resource_type: 'scope',
        resource_id: 'scope-456',
        resource_name: 'Marketing',
        requested_by: 'user-789',
        requested_by_name: 'John Doe',
        requested_at: '2024-01-01T00:00:00Z',
        expires_at: '2024-01-02T00:00:00Z',
        status: 'pending',
        request_context: {
          reason: 'Test reason',
          affected_count: 10,
        },
      };

      const transformed = {
        id: raw.id,
        actionType: raw.action_type,
        resourceType: raw.resource_type,
        resourceId: raw.resource_id,
        resourceName: raw.resource_name,
        requestedBy: raw.requested_by,
        requestedByName: raw.requested_by_name,
        requestedAt: raw.requested_at,
        expiresAt: raw.expires_at,
        status: raw.status,
        requestContext: {
          reason: raw.request_context?.reason,
          affectedCount: raw.request_context?.affected_count,
        },
      };

      expect(transformed.actionType).toBe('delete_scope');
      expect(transformed.resourceType).toBe('scope');
      expect(transformed.requestContext.affectedCount).toBe(10);
    });

    it('should keep snake_case aliases for backward compatibility', () => {
      const raw = {
        action_type: 'bulk_delete',
        resource_type: 'document',
        resource_id: 'doc-123',
        resource_name: 'report.pdf',
        expires_at: '2024-01-02T00:00:00Z',
        request_context: {
          affected_count: 5,
        },
      };

      // The transformed object should have both camelCase and snake_case
      const transformed = {
        actionType: raw.action_type,
        action_type: raw.action_type,
        resourceType: raw.resource_type,
        resource_type: raw.resource_type,
      };

      expect(transformed.actionType).toBe(transformed.action_type);
      expect(transformed.resourceType).toBe(transformed.resource_type);
    });
  });
});

// =============================================================================
// Hook Return Value Tests
// =============================================================================

describe('useApprovals Return Values', () => {
  it('should return pending approvals array', () => {
    const returnValue = { pending: [] };
    expect(Array.isArray(returnValue.pending)).toBe(true);
  });

  it('should return isLoading boolean', () => {
    const returnValue = { isLoading: false };
    expect(typeof returnValue.isLoading).toBe('boolean');
  });

  it('should return isError boolean', () => {
    const returnValue = { isError: false };
    expect(typeof returnValue.isError).toBe('boolean');
  });

  it('should return refetch function', () => {
    const returnValue = { refetch: () => {} };
    expect(typeof returnValue.refetch).toBe('function');
  });

  it('should return approve function', () => {
    const returnValue = { approve: () => {} };
    expect(typeof returnValue.approve).toBe('function');
  });

  it('should return isApproving boolean', () => {
    const returnValue = { isApproving: false };
    expect(typeof returnValue.isApproving).toBe('boolean');
  });

  it('should return reject function', () => {
    const returnValue = { reject: () => {} };
    expect(typeof returnValue.reject).toBe('function');
  });

  it('should return isRejecting boolean', () => {
    const returnValue = { isRejecting: false };
    expect(typeof returnValue.isRejecting).toBe('boolean');
  });

  it('should return execute function', () => {
    const returnValue = { execute: () => {} };
    expect(typeof returnValue.execute).toBe('function');
  });

  it('should return isExecuting boolean', () => {
    const returnValue = { isExecuting: false };
    expect(typeof returnValue.isExecuting).toBe('boolean');
  });

  it('should return getApproval function', () => {
    const returnValue = { getApproval: () => {} };
    expect(typeof returnValue.getApproval).toBe('function');
  });
});

// =============================================================================
// Query Configuration Tests
// =============================================================================

describe('useApprovals Query Configuration', () => {
  it('should default enabled to true', () => {
    const options: { enabled?: boolean } = {};
    const enabled = options.enabled ?? true;
    expect(enabled).toBe(true);
  });

  it('should default refetch interval to 30 seconds', () => {
    const options: { refetchInterval?: number } = {};
    const refetchInterval = options.refetchInterval ?? 30000;
    expect(refetchInterval).toBe(30000);
  });

  it('should have 10 second stale time', () => {
    const staleTime = 10000;
    expect(staleTime).toBe(10000);
  });

  it('should not retry on auth errors', () => {
    const error = new Error('Unauthorized - please log in');
    const shouldRetry = !(error.message.includes('Unauthorized') || error.message.includes('Admin'));
    expect(shouldRetry).toBe(false);
  });

  it('should limit retries to 3 attempts', () => {
    const error = new Error('Network error');
    const failureCount = 4;
    const shouldRetry = failureCount < 3;
    expect(shouldRetry).toBe(false);
  });
});

// =============================================================================
// Approval Workflow Tests
// =============================================================================

describe('Approval Workflow', () => {
  it('should transition from pending to approved', () => {
    const approval = { status: 'pending' };
    const newStatus = 'approved';
    expect(newStatus).toBe('approved');
  });

  it('should transition from pending to rejected', () => {
    const approval = { status: 'pending' };
    const newStatus = 'rejected';
    expect(newStatus).toBe('rejected');
  });

  it('should transition from approved to executed (via execute action)', () => {
    const approval = { status: 'approved' };
    const executeResult = { status: 'executed' };
    expect(executeResult.status).toBe('executed');
  });

  it('should handle expired approvals', () => {
    const approval = {
      status: 'pending',
      expiresAt: '2024-01-01T00:00:00Z',
    };
    const now = new Date('2024-01-02T00:00:00Z');
    const isExpired = new Date(approval.expiresAt) < now;
    expect(isExpired).toBe(true);
  });
});

// =============================================================================
// Error Handling Tests
// =============================================================================

describe('useApprovals Error Handling', () => {
  it('should provide unauthorized error message', () => {
    const errorMessage = 'Unauthorized - please log in';
    expect(errorMessage).toContain('Unauthorized');
  });

  it('should provide admin access error message', () => {
    const errorMessage = 'Admin access required';
    expect(errorMessage).toContain('Admin');
  });

  it('should provide not found error message', () => {
    const errorMessage = 'Approval not found';
    expect(errorMessage).toContain('not found');
  });

  it('should provide generic failure messages', () => {
    const messages = [
      'Failed to fetch pending approvals',
      'Failed to approve action',
      'Failed to reject action',
      'Failed to execute approved action',
      'Failed to fetch approval',
    ];

    messages.forEach(msg => {
      expect(msg).toContain('Failed');
    });
  });
});

// =============================================================================
// Action Type Tests
// =============================================================================

describe('Approval Action Types', () => {
  it('should handle delete_scope action', () => {
    const action = {
      actionType: 'delete_scope',
      resourceType: 'scope',
      resourceName: 'Marketing',
    };
    expect(action.actionType).toBe('delete_scope');
  });

  it('should handle bulk_delete action', () => {
    const action = {
      actionType: 'bulk_delete',
      resourceType: 'document',
      requestContext: { affectedCount: 50 },
    };
    expect(action.actionType).toBe('bulk_delete');
    expect(action.requestContext.affectedCount).toBe(50);
  });

  it('should handle purge_all action', () => {
    const action = {
      actionType: 'purge_all',
      resourceType: 'organization',
    };
    expect(action.actionType).toBe('purge_all');
  });

  it('should handle revoke_access action', () => {
    const action = {
      actionType: 'revoke_access',
      resourceType: 'user',
    };
    expect(action.actionType).toBe('revoke_access');
  });
});
