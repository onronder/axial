'use client';

/**
 * useTeamMembers Hook
 * 
 * Manages team members with optimistic updates for instant UI feedback.
 * 
 * Features:
 * - Optimistic updates for role changes and removals
 * - Automatic rollback on API failure
 * - Team statistics tracking
 * - Filtering by role, status, and search
 * - Toast notifications for all operations
 * 
 * @example
 * ```tsx
 * const { members, inviteMember, updateMemberRole, removeMember } = useTeamMembers();
 * 
 * // Invite a new member
 * await inviteMember('user@example.com', 'editor');
 * 
 * // Update role (shows instantly, reverts on error)
 * await updateMemberRole('member-id', 'admin');
 * 
 * // Remove member (optimistic)
 * await removeMember('member-id');
 * ```
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

// =============================================================================
// Types
// =============================================================================

export type Role = 'admin' | 'editor' | 'viewer';
export type MemberStatus = 'active' | 'pending' | 'suspended';

export interface TeamMember {
    id: string;
    email: string;
    name: string | null;
    role: Role;
    status: MemberStatus;
    last_active: string | null;
    created_at: string;
    invited_at: string | null;
}

export interface TeamStats {
    total_seats: number;
    active_members: number;
    pending_invites: number;
}

export interface TeamFilters {
    role: Role | 'all';
    status: MemberStatus | 'all';
    search: string;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_STATS: TeamStats = {
    total_seats: 20,
    active_members: 0,
    pending_invites: 0,
};

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for managing team members with optimistic updates.
 * Provides full CRUD operations with filtering and stats.
 */
export const useTeamMembers = () => {
    const { toast } = useToast();
    
    // State
    const [members, setMembers] = useState<TeamMember[]>([]);
    const [stats, setStats] = useState<TeamStats>(DEFAULT_STATS);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    
    // Track mounted state for async operations
    const mountedRef = useRef(true);

    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    // =========================================================================
    // Fetch Operations
    // =========================================================================

    /**
     * Fetch team members with optional filters.
     */
    const fetchMembers = useCallback(async (filters?: Partial<TeamFilters>) => {
        setIsLoading(true);
        setError(null);
        
        try {
            const params: Record<string, string> = {};
            if (filters?.role && filters.role !== 'all') params.role = filters.role;
            if (filters?.status && filters.status !== 'all') params.status = filters.status;
            if (filters?.search) params.search = filters.search;

            const { data } = await api.get('/team/members', { params });
            
            if (mountedRef.current) {
                setMembers(data);
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Failed to fetch team';
            console.error('Failed to fetch team members:', message);
            
            if (mountedRef.current) {
                setError(message);
            }
        } finally {
            if (mountedRef.current) {
                setIsLoading(false);
            }
        }
    }, []);

    /**
     * Fetch team statistics.
     */
    const fetchStats = useCallback(async () => {
        try {
            const { data } = await api.get('/team/stats');
            
            if (mountedRef.current) {
                setStats(data);
            }
        } catch (err) {
            console.error('Failed to fetch team stats:', err instanceof Error ? err.message : err);
        }
    }, []);

    // Initial fetch
    useEffect(() => {
        fetchMembers();
        fetchStats();
    }, [fetchMembers, fetchStats]);

    // =========================================================================
    // Mutation Operations (with Optimistic Updates)
    // =========================================================================

    /**
     * Invite a new team member.
     */
    const inviteMember = async (email: string, role: Role = 'viewer', name?: string): Promise<boolean> => {
        // Optimistically add a pending member
        const tempId = `temp-${Date.now()}`;
        const optimisticMember: TeamMember = {
            id: tempId,
            email,
            name: name || null,
            role,
            status: 'pending',
            last_active: null,
            created_at: new Date().toISOString(),
            invited_at: new Date().toISOString(),
        };
        
        setMembers(prev => [optimisticMember, ...prev]);
        setStats(prev => ({ ...prev, pending_invites: prev.pending_invites + 1 }));

        try {
            const { data } = await api.post('/team/members', { email, role, name });
            
            if (mountedRef.current) {
                // Replace optimistic member with real data
                setMembers(prev => prev.map(m => m.id === tempId ? data : m));
            }
            
            toast({
                title: 'Invitation sent',
                description: `Invitation sent to ${email}`,
            });
            
            return true;
        } catch (err) {
            const axiosErr = err as { response?: { data?: { detail?: string } } };
            const message = axiosErr.response?.data?.detail || 'Failed to send invitation';
            console.error('Failed to invite member:', message);
            
            if (mountedRef.current) {
                // Rollback optimistic update
                setMembers(prev => prev.filter(m => m.id !== tempId));
                setStats(prev => ({ ...prev, pending_invites: prev.pending_invites - 1 }));
            }
            
            toast({
                title: 'Error',
                description: message,
                variant: 'destructive',
            });
            
            return false;
        }
    };

    /**
     * Update a team member's role with optimistic update.
     */
    const updateMemberRole = async (memberId: string, role: Role): Promise<boolean> => {
        // Store previous state for rollback
        const previousMembers = [...members];
        const previousMember = members.find(m => m.id === memberId);
        
        if (!previousMember) {
            toast({
                title: 'Error',
                description: 'Member not found.',
                variant: 'destructive',
            });
            return false;
        }

        // Optimistically update
        setMembers(prev => prev.map(m => 
            m.id === memberId ? { ...m, role } : m
        ));

        try {
            const { data } = await api.patch(`/team/members/${memberId}`, { role });
            
            if (mountedRef.current) {
                // Update with server response (may include additional changes)
                setMembers(prev => prev.map(m => m.id === memberId ? data : m));
            }
            
            toast({
                title: 'Role updated',
                description: `${previousMember.email}'s role changed from ${previousMember.role} to ${role}.`,
            });
            
            return true;
        } catch (err) {
            console.error('Failed to update role:', err instanceof Error ? err.message : err);
            
            if (mountedRef.current) {
                // Rollback to previous state
                setMembers(previousMembers);
            }
            
            toast({
                title: 'Error',
                description: 'Failed to update role. Changes have been reverted.',
                variant: 'destructive',
            });
            
            return false;
        }
    };

    /**
     * Update a team member's status with optimistic update.
     */
    const updateMemberStatus = async (memberId: string, status: MemberStatus): Promise<boolean> => {
        // Store previous state for rollback
        const previousMembers = [...members];
        const previousStats = { ...stats };

        // Optimistically update
        setMembers(prev => prev.map(m => 
            m.id === memberId ? { ...m, status } : m
        ));
        
        // Update stats optimistically
        const member = members.find(m => m.id === memberId);
        if (member) {
            setStats(prev => {
                const newStats = { ...prev };
                
                // Decrement old status count
                if (member.status === 'active') newStats.active_members--;
                if (member.status === 'pending') newStats.pending_invites--;
                
                // Increment new status count
                if (status === 'active') newStats.active_members++;
                if (status === 'pending') newStats.pending_invites++;
                
                return newStats;
            });
        }

        try {
            const { data } = await api.patch(`/team/members/${memberId}`, { status });
            
            if (mountedRef.current) {
                setMembers(prev => prev.map(m => m.id === memberId ? data : m));
                // Refresh stats from server for accuracy
                fetchStats();
            }
            
            return true;
        } catch (err) {
            console.error('Failed to update status:', err instanceof Error ? err.message : err);
            
            if (mountedRef.current) {
                // Rollback to previous state
                setMembers(previousMembers);
                setStats(previousStats);
            }
            
            toast({
                title: 'Error',
                description: 'Failed to update member status. Changes have been reverted.',
                variant: 'destructive',
            });
            
            return false;
        }
    };

    /**
     * Remove a team member with optimistic update.
     */
    const removeMember = async (memberId: string): Promise<boolean> => {
        // Store previous state for rollback
        const previousMembers = [...members];
        const previousStats = { ...stats };
        const removedMember = members.find(m => m.id === memberId);
        
        if (!removedMember) {
            toast({
                title: 'Error',
                description: 'Member not found.',
                variant: 'destructive',
            });
            return false;
        }

        // Optimistically remove
        setMembers(prev => prev.filter(m => m.id !== memberId));
        
        // Update stats optimistically
        setStats(prev => ({
            ...prev,
            active_members: removedMember.status === 'active' 
                ? prev.active_members - 1 
                : prev.active_members,
            pending_invites: removedMember.status === 'pending' 
                ? prev.pending_invites - 1 
                : prev.pending_invites,
        }));

        try {
            await api.delete(`/team/members/${memberId}`);
            
            toast({
                title: 'Access revoked',
                description: `${removedMember.email} has been removed from the team.`,
            });
            
            return true;
        } catch (err) {
            console.error('Failed to remove member:', err instanceof Error ? err.message : err);
            
            if (mountedRef.current) {
                // Rollback to previous state
                setMembers(previousMembers);
                setStats(previousStats);
            }
            
            toast({
                title: 'Error',
                description: 'Failed to remove member. Changes have been reverted.',
                variant: 'destructive',
            });
            
            return false;
        }
    };

    /**
     * Resend invitation to a pending member.
     */
    const resendInvite = async (memberId: string, email: string): Promise<boolean> => {
        try {
            await api.post(`/team/members/${memberId}/resend`);
            
            toast({
                title: 'Invitation resent',
                description: `Invitation resent to ${email}`,
            });
            
            return true;
        } catch (err) {
            console.error('Failed to resend invite:', err instanceof Error ? err.message : err);
            
            toast({
                title: 'Error',
                description: 'Failed to resend invitation.',
                variant: 'destructive',
            });
            
            return false;
        }
    };

    // =========================================================================
    // Return
    // =========================================================================

    return {
        // Data
        members,
        stats,
        isLoading,
        error,
        
        // Mutations
        inviteMember,
        updateMemberRole,
        updateMemberStatus,
        removeMember,
        resendInvite,
        
        // Refresh
        refresh: fetchMembers,
        refreshStats: fetchStats,
    };
};
