/**
 * Unit Tests for useProfile Hook
 * 
 * Tests the profile context provider and update functionality.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { ProfileProvider, useProfile, UserProfile } from '@/hooks/useProfile';

// Mock dependencies
const mockToast = vi.fn();
const mockApiGet = vi.fn();
const mockApiPatch = vi.fn();

vi.mock('@/hooks/use-toast', () => ({
    useToast: () => ({ toast: mockToast }),
}));

vi.mock('@/lib/api', () => ({
    api: {
        get: (...args: any[]) => mockApiGet(...args),
        patch: (...args: any[]) => mockApiPatch(...args),
    },
}));

// Test wrapper
const wrapper = ({ children }: { children: ReactNode }) => (
    <ProfileProvider>{children} </ProfileProvider>
);

const mockProfile: UserProfile = {
    id: 'profile-1',
    user_id: 'user-1',
    first_name: 'John',
    last_name: 'Doe',
    plan: 'pro',
    theme: 'dark',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
};

describe('useProfile', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockResolvedValue({ data: mockProfile });
    });

    describe('Initial State', () => {
        it('should start with loading state', () => {
            const { result } = renderHook(() => useProfile(), { wrapper });
            expect(result.current.isLoading).toBe(true);
        });

        it('should fetch profile on mount', async () => {
            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApiGet).toHaveBeenCalledWith('/settings/profile');
            expect(result.current.profile).toEqual(mockProfile);
        });

        it('should handle fetch error', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Network error');
            expect(result.current.profile).toBeNull();
        });
    });

    describe('updateProfile', () => {
        it('should update profile successfully', async () => {
            const updatedProfile = { ...mockProfile, first_name: 'Jane' };
            mockApiPatch.mockResolvedValue({ data: updatedProfile });

            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateProfile({ first_name: 'Jane' });
            });

            expect(success!).toBe(true);
            expect(mockApiPatch).toHaveBeenCalledWith('/settings/profile', { first_name: 'Jane' });
            expect(result.current.profile?.first_name).toBe('Jane');
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Profile updated' })
            );
        });

        it('should handle update error', async () => {
            mockApiPatch.mockRejectedValue({ message: 'Update failed', response: { data: { detail: 'Server error' } } });

            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateProfile({ first_name: 'Jane' });
            });

            expect(success!).toBe(false);
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({
                    title: 'Error',
                    variant: 'destructive',
                })
            );
        });

        it('should update theme', async () => {
            const updatedProfile = { ...mockProfile, theme: 'light' as const };
            mockApiPatch.mockResolvedValue({ data: updatedProfile });

            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                await result.current.updateProfile({ theme: 'light' });
            });

            expect(result.current.profile?.theme).toBe('light');
        });
    });

    describe('refresh', () => {
        it('should re-fetch profile', async () => {
            const { result } = renderHook(() => useProfile(), { wrapper });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            const newProfile = { ...mockProfile, first_name: 'Updated' };
            mockApiGet.mockResolvedValue({ data: newProfile });

            await act(async () => {
                await result.current.refresh();
            });

            expect(result.current.profile?.first_name).toBe('Updated');
        });
    });
});

describe('useProfile outside provider', () => {
    it('should return default state with warning', () => {
        const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => { });

        const { result } = renderHook(() => useProfile());

        expect(result.current.profile).toBeNull();
        expect(result.current.isLoading).toBe(false);
        expect(result.current.error).toBeNull();
        expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Used outside ProfileProvider'));

        consoleSpy.mockRestore();
    });

    it('should return no-op functions outside provider', async () => {
        vi.spyOn(console, 'warn').mockImplementation(() => { });

        const { result } = renderHook(() => useProfile());

        const success = await result.current.updateProfile({ first_name: 'Test' });
        expect(success).toBe(false);

        // refresh should not throw
        await result.current.refresh();
    });
});
