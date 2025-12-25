'use client';

import { useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';
import { useToast } from '@/hooks/use-toast';

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

/**
 * Hook for managing team members.
 * Provides full CRUD operations with filtering and stats.
 */
export const useTeamMembers = () => {
    const { toast } = useToast();
    const [members, setMembers] = useState<TeamMember[]>([]);
    const [stats, setStats] = useState<TeamStats>({ total_seats: 20, active_members: 0, pending_invites: 0 });
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchMembers = useCallback(async (filters?: Partial<TeamFilters>) => {
        setIsLoading(true);
        setError(null);
        try {
            const params: Record<string, string> = {};
            if (filters?.role && filters.role !== 'all') params.role = filters.role;
            if (filters?.status && filters.status !== 'all') params.status = filters.status;
            if (filters?.search) params.search = filters.search;

            const { data } = await api.get('/team/members', { params });
            setMembers(data);
        } catch (err: any) {
            console.error('Failed to fetch team members:', err);
            setError(err.message || 'Failed to fetch team');
        } finally {
            setIsLoading(false);
        }
    }, []);

    const fetchStats = useCallback(async () => {
        try {
            const { data } = await api.get('/team/stats');
            setStats(data);
        } catch (err: any) {
            console.error('Failed to fetch team stats:', err);
        }
    }, []);

    useEffect(() => {
        fetchMembers();
        fetchStats();
    }, [fetchMembers, fetchStats]);

    const inviteMember = async (email: string, role: Role = 'viewer', name?: string): Promise<boolean> => {
        try {
            const { data } = await api.post('/team/members', { email, role, name });
            setMembers(prev => [data, ...prev]);
            await fetchStats(); // Refresh stats
            toast({
                title: 'Invitation sent',
                description: `Invitation sent to ${email}`,
            });
            return true;
        } catch (err: any) {
            console.error('Failed to invite member:', err);
            const message = err.response?.data?.detail || 'Failed to send invitation';
            toast({
                title: 'Error',
                description: message,
                variant: 'destructive',
            });
            return false;
        }
    };

    const updateMemberRole = async (memberId: string, role: Role): Promise<boolean> => {
        try {
            const { data } = await api.patch(`/team/members/${memberId}`, { role });
            setMembers(prev => prev.map(m => m.id === memberId ? data : m));
            toast({
                title: 'Role updated',
                description: `Member's role has been changed to ${role}.`,
            });
            return true;
        } catch (err: any) {
            console.error('Failed to update role:', err);
            toast({
                title: 'Error',
                description: 'Failed to update role.',
                variant: 'destructive',
            });
            return false;
        }
    };

    const updateMemberStatus = async (memberId: string, status: MemberStatus): Promise<boolean> => {
        try {
            const { data } = await api.patch(`/team/members/${memberId}`, { status });
            setMembers(prev => prev.map(m => m.id === memberId ? data : m));
            await fetchStats();
            return true;
        } catch (err: any) {
            console.error('Failed to update status:', err);
            toast({
                title: 'Error',
                description: 'Failed to update member status.',
                variant: 'destructive',
            });
            return false;
        }
    };

    const removeMember = async (memberId: string): Promise<boolean> => {
        try {
            await api.delete(`/team/members/${memberId}`);
            setMembers(prev => prev.filter(m => m.id !== memberId));
            await fetchStats();
            toast({
                title: 'Access revoked',
                description: 'Team member has been removed.',
            });
            return true;
        } catch (err: any) {
            console.error('Failed to remove member:', err);
            toast({
                title: 'Error',
                description: 'Failed to remove member.',
                variant: 'destructive',
            });
            return false;
        }
    };

    const resendInvite = async (memberId: string, email: string): Promise<boolean> => {
        try {
            await api.post(`/team/members/${memberId}/resend`);
            toast({
                title: 'Invitation resent',
                description: `Invitation resent to ${email}`,
            });
            return true;
        } catch (err: any) {
            console.error('Failed to resend invite:', err);
            toast({
                title: 'Error',
                description: 'Failed to resend invitation.',
                variant: 'destructive',
            });
            return false;
        }
    };

    return {
        members,
        stats,
        isLoading,
        error,
        inviteMember,
        updateMemberRole,
        updateMemberStatus,
        removeMember,
        resendInvite,
        refresh: fetchMembers,
        refreshStats: fetchStats,
    };
};
