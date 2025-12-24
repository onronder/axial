/**
 * Unit Tests for useTeamMembers Hook
 * 
 * Tests team member CRUD operations, stats, and filtering.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useTeamMembers, TeamMember } from '@/hooks/useTeamMembers';

// Mock dependencies
const mockToast = vi.fn();
const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiPatch = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/lib/api', () => ({
    api: {
        get: (...args: any[]) => mockApiGet(...args),
        post: (...args: any[]) => mockApiPost(...args),
        patch: (...args: any[]) => mockApiPatch(...args),
        delete: (...args: any[]) => mockApiDelete(...args),
    },
}));

const mockMembers: TeamMember[] = [
    {
        id: '1',
        email: 'admin@test.com',
        name: 'Admin User',
        role: 'admin',
        status: 'active',
        last_active: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        invited_at: null,
    },
    {
        id: '2',
        email: 'viewer@test.com',
        name: 'Viewer User',
        role: 'viewer',
        status: 'pending',
        last_active: null,
        created_at: '2024-01-01T00:00:00Z',
        invited_at: '2024-01-01T00:00:00Z',
    },
];

const mockStats = {
    total_seats: 20,
    active_members: 1,
    pending_invites: 1,
};

describe('useTeamMembers', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockImplementation((url: string) => {
            if (url.includes('stats')) {
                return Promise.resolve({ data: mockStats });
            }
            return Promise.resolve({ data: mockMembers });
        });
    });

    describe('Initial State', () => {
        it('should start with loading true', () => {
            const { result } = renderHook(() => useTeamMembers());
            expect(result.current.isLoading).toBe(true);
        });

        it('should fetch members and stats on mount', async () => {
            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApiGet).toHaveBeenCalledWith('api/v1/team/members', { params: {} });
            expect(mockApiGet).toHaveBeenCalledWith('api/v1/team/stats');
            expect(result.current.members).toEqual(mockMembers);
            expect(result.current.stats).toEqual(mockStats);
        });

        it('should handle fetch error', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Network error');
        });
    });

    describe('inviteMember', () => {
        it('should invite a new member', async () => {
            const newMember: TeamMember = {
                id: '3',
                email: 'new@test.com',
                name: 'New User',
                role: 'editor',
                status: 'pending',
                last_active: null,
                created_at: '2024-01-02T00:00:00Z',
                invited_at: '2024-01-02T00:00:00Z',
            };
            mockApiPost.mockResolvedValue({ data: newMember });

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.inviteMember('new@test.com', 'editor', 'New User');
            });

            expect(success!).toBe(true);
            expect(mockApiPost).toHaveBeenCalledWith('api/v1/team/members', {
                email: 'new@test.com',
                role: 'editor',
                name: 'New User',
            });
            expect(result.current.members[0]).toEqual(newMember);
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Invitation sent' })
            );
        });

        it('should handle invite error', async () => {
            mockApiPost.mockRejectedValue({ response: { data: { detail: 'Email exists' } } });

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.inviteMember('existing@test.com');
            });

            expect(success!).toBe(false);
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });
    });

    describe('updateMemberRole', () => {
        it('should update member role', async () => {
            const updatedMember = { ...mockMembers[1], role: 'editor' as const };
            mockApiPatch.mockResolvedValue({ data: updatedMember });

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateMemberRole('2', 'editor');
            });

            expect(success!).toBe(true);
            expect(mockApiPatch).toHaveBeenCalledWith('api/v1/team/members/2', { role: 'editor' });
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Role updated' })
            );
        });

        it('should handle role update error', async () => {
            mockApiPatch.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateMemberRole('2', 'admin');
            });

            expect(success!).toBe(false);
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ variant: 'destructive' })
            );
        });
    });

    describe('updateMemberStatus', () => {
        it('should update member status', async () => {
            const updatedMember = { ...mockMembers[1], status: 'active' as const };
            mockApiPatch.mockResolvedValue({ data: updatedMember });

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateMemberStatus('2', 'active');
            });

            expect(success!).toBe(true);
            expect(mockApiPatch).toHaveBeenCalledWith('api/v1/team/members/2', { status: 'active' });
        });
    });

    describe('removeMember', () => {
        it('should remove a member', async () => {
            mockApiDelete.mockResolvedValue({});

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.members.length).toBe(2));

            let success: boolean;
            await act(async () => {
                success = await result.current.removeMember('1');
            });

            expect(success!).toBe(true);
            expect(mockApiDelete).toHaveBeenCalledWith('api/v1/team/members/1');
            expect(result.current.members.find(m => m.id === '1')).toBeUndefined();
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Access revoked' })
            );
        });

        it('should handle remove error', async () => {
            mockApiDelete.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.removeMember('1');
            });

            expect(success!).toBe(false);
        });
    });

    describe('resendInvite', () => {
        it('should resend invite', async () => {
            mockApiPost.mockResolvedValue({});

            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.resendInvite('2', 'viewer@test.com');
            });

            expect(success!).toBe(true);
            expect(mockApiPost).toHaveBeenCalledWith('api/v1/team/members/2/resend');
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Invitation resent' })
            );
        });
    });

    describe('refresh', () => {
        it('should re-fetch members with filters', async () => {
            const { result } = renderHook(() => useTeamMembers());

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                await result.current.refresh({ role: 'admin', status: 'active' });
            });

            expect(mockApiGet).toHaveBeenLastCalledWith('api/v1/team/members', {
                params: { role: 'admin', status: 'active' },
            });
        });
    });
});
