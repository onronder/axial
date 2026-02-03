'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// =============================================================================
// Types - Match backend response structure
// =============================================================================

interface ApprovalRaw {
  id: string;
  action_type: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  requested_by: string;
  requested_by_name?: string;
  requested_at: string;
  expires_at: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  request_context: {
    reason?: string;
    affected_count?: number;
    affected_documents?: Array<{ id: string; name: string }>;
  };
}

// Frontend-friendly camelCase interface
export interface Approval {
  id: string;
  actionType: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resourceType: string;
  resourceId: string;
  resourceName?: string;
  requestedBy: string;
  requestedByName?: string;
  requestedAt: string;
  expiresAt: string;
  status: 'pending' | 'approved' | 'rejected' | 'expired';
  requestContext: {
    reason?: string;
    affectedCount?: number;
    affectedDocuments?: Array<{ id: string; name: string }>;
  };
  // Keep snake_case aliases for components that use them directly
  action_type: 'delete_scope' | 'bulk_delete' | 'purge_all' | 'revoke_access';
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  expires_at: string;
  request_context: {
    reason?: string;
    affected_count?: number;
    affected_documents?: Array<{ id: string; name: string }>;
  };
}

interface UseApprovalsOptions {
  enabled?: boolean;
  refetchInterval?: number;
}

// =============================================================================
// API Functions
// =============================================================================

function transformApproval(raw: ApprovalRaw): Approval {
  return {
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
      affectedDocuments: raw.request_context?.affected_documents,
    },
    // Keep snake_case for backward compatibility with components
    action_type: raw.action_type,
    resource_type: raw.resource_type,
    resource_id: raw.resource_id,
    resource_name: raw.resource_name,
    expires_at: raw.expires_at,
    request_context: raw.request_context,
  };
}

async function fetchPendingApprovals(): Promise<Approval[]> {
  const response = await fetch('/api/py/approvals/pending', {
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
      throw new Error('Admin access required');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch pending approvals');
  }

  const data: ApprovalRaw[] = await response.json();
  return data.map(transformApproval);
}

async function approveAction(approvalId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`/api/py/approvals/${approvalId}/approve`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to approve action');
  }

  return response.json();
}

async function rejectAction(params: { approvalId: string; reason?: string }): Promise<{ status: string; message: string }> {
  const url = new URL(`/api/py/approvals/${params.approvalId}/reject`, window.location.origin);
  if (params.reason) {
    url.searchParams.set('reason', params.reason);
  }

  const response = await fetch(url.toString(), {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to reject action');
  }

  return response.json();
}

async function executeApproved(params: { approvalId: string; mandateSignature: string }): Promise<{ status: string; result: unknown }> {
  const response = await fetch(`/api/py/approvals/${params.approvalId}/execute`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      mandate_signature: params.mandateSignature,
    }),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to execute approved action');
  }

  return response.json();
}

async function getApproval(approvalId: string): Promise<Approval> {
  const response = await fetch(`/api/py/approvals/${approvalId}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    if (response.status === 404) {
      throw new Error('Approval not found');
    }
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch approval');
  }

  const data: ApprovalRaw = await response.json();
  return transformApproval(data);
}

// =============================================================================
// Hook
// =============================================================================

export function useApprovals(options: UseApprovalsOptions = {}) {
  const queryClient = useQueryClient();
  const { enabled = true, refetchInterval = 30000 } = options;

  // Query for pending approvals
  const pendingQuery = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: fetchPendingApprovals,
    enabled,
    refetchInterval,
    staleTime: 10000,
    retry: (failureCount, error) => {
      // Don't retry on auth errors
      if (error instanceof Error && (error.message.includes('Unauthorized') || error.message.includes('Admin'))) {
        return false;
      }
      return failureCount < 3;
    },
  });

  // Mutation for approving
  const approveMutation = useMutation({
    mutationFn: approveAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
  });

  // Mutation for rejecting
  const rejectMutation = useMutation({
    mutationFn: rejectAction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
  });

  // Mutation for executing
  const executeMutation = useMutation({
    mutationFn: executeApproved,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
  });

  return {
    // Data
    pending: pendingQuery.data ?? [],
    isLoading: pendingQuery.isLoading,
    isError: pendingQuery.isError,
    error: pendingQuery.error,
    refetch: pendingQuery.refetch,

    // Actions
    approve: (approvalId: string) => approveMutation.mutateAsync(approvalId),
    isApproving: approveMutation.isPending,
    approveError: approveMutation.error,

    reject: (approvalId: string, reason?: string) =>
      rejectMutation.mutateAsync({ approvalId, reason }),
    isRejecting: rejectMutation.isPending,
    rejectError: rejectMutation.error,

    execute: (approvalId: string, mandateSignature: string) =>
      executeMutation.mutateAsync({ approvalId, mandateSignature }),
    isExecuting: executeMutation.isPending,
    executeError: executeMutation.error,

    // Single approval fetch
    getApproval,
  };
}

export default useApprovals;
