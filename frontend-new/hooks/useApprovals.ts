'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';

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
  const response = await api.get<ApprovalRaw[]>('/approvals/pending');
  return response.data.map(transformApproval);
}

async function approveAction(approvalId: string): Promise<{ status: string; message: string }> {
  const response = await api.post<{ status: string; message: string }>(`/approvals/${approvalId}/approve`);
  return response.data;
}

async function rejectAction(params: { approvalId: string; reason?: string }): Promise<{ status: string; message: string }> {
  const queryParams = params.reason ? `?reason=${encodeURIComponent(params.reason)}` : '';
  const response = await api.post<{ status: string; message: string }>(`/approvals/${params.approvalId}/reject${queryParams}`);
  return response.data;
}

async function executeApproved(params: { approvalId: string; mandateSignature: string }): Promise<{ status: string; result: unknown }> {
  const response = await api.post<{ status: string; result: unknown }>(`/approvals/${params.approvalId}/execute`, {
    mandate_signature: params.mandateSignature,
  });
  return response.data;
}

async function getApproval(approvalId: string): Promise<Approval> {
  const response = await api.get<ApprovalRaw>(`/approvals/${approvalId}`);
  return transformApproval(response.data);
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
