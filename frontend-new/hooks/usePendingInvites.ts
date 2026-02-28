'use client';

/**
 * usePendingInvites Hook
 * 
 * Fetches and manages pending team invites for the current user.
 * Allows users to accept or decline invites directly from the dashboard.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

// =============================================================================
// Types
// =============================================================================

export interface PendingInvite {
  id: string;
  team_id: string;
  team_name: string;
  role: string;
  invited_at: string;
  expires_at: string | null;
}

interface PendingInvitesResponse {
  invites: PendingInvite[];
  count: number;
}

interface AcceptInviteResponse {
  success: boolean;
  team_name?: string;
  team_id?: string;
  error?: string;
}

// =============================================================================
// API Functions
// =============================================================================

async function fetchPendingInvites(): Promise<PendingInvitesResponse> {
  const response = await api.get<PendingInvitesResponse>('/team/my-invites');
  return response.data;
}

async function acceptInviteApi(token: string): Promise<AcceptInviteResponse> {
  const response = await api.post<AcceptInviteResponse>('/team/accept', { token });
  return response.data;
}

async function declineInviteApi(inviteId: string): Promise<{ status: string }> {
  const response = await api.post<{ status: string }>('/team/decline', { token: inviteId });
  return response.data;
}

// =============================================================================
// Hook
// =============================================================================

export function usePendingInvites() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Fetch pending invites
  const query = useQuery({
    queryKey: ['pending-invites'],
    queryFn: fetchPendingInvites,
    staleTime: 60000, // 1 minute
    refetchInterval: 300000, // Refetch every 5 minutes
    retry: 1,
  });

  // Accept invite mutation
  const acceptMutation = useMutation({
    mutationFn: (inviteId: string) => acceptInviteApi(inviteId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['pending-invites'] });
      queryClient.invalidateQueries({ queryKey: ['team'] });
      queryClient.invalidateQueries({ queryKey: ['usage'] });
      
      toast({
        title: 'Invitation Accepted',
        description: `You've joined ${data.team_name || 'the team'}! 🎉`,
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Accept Invite',
        description: error.message || 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
    },
  });

  // Decline invite mutation
  const declineMutation = useMutation({
    mutationFn: (inviteId: string) => declineInviteApi(inviteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pending-invites'] });
      
      toast({
        title: 'Invitation Declined',
        description: 'The team invitation has been declined.',
      });
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to Decline Invite',
        description: error.message || 'Something went wrong. Please try again.',
        variant: 'destructive',
      });
    },
  });

  return {
    // Data
    invites: query.data?.invites ?? [],
    count: query.data?.count ?? 0,
    hasInvites: (query.data?.count ?? 0) > 0,

    // Loading states
    isLoading: query.isLoading,
    isAccepting: acceptMutation.isPending,
    isDeclining: declineMutation.isPending,

    // Error state
    error: query.error,

    // Actions
    acceptInvite: (inviteId: string) => acceptMutation.mutateAsync(inviteId),
    declineInvite: (inviteId: string) => declineMutation.mutateAsync(inviteId),
    refetch: query.refetch,
  };
}

export default usePendingInvites;
