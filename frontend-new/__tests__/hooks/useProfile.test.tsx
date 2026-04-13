/**
 * Unit Tests for useProfile Hook
 * 
 * Tests the profile context provider and update functionality.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
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
    clearAuthCache: vi.fn(),
}));

// Create a fresh wrapper for each test to avoid cross-test cache pollution
const createWrapper = () => {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    const Wrapper = ({ children }: { children: ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            <ProfileProvider>{children}</ProfileProvider>
        </QueryClientProvider>
    );
    Wrapper.displayName = 'TestWrapper';
    return Wrapper;
};

const mockProfile: UserProfile = {
    id: 'profile-1',
    user_id: 'user-1',
    first_name: 'John',
    last_name: 'Doe',
    plan: 'pro',
    theme: 'dark',
    organization_id: 'org-1',
    team_id: 'team-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
};

describe('useProfile', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockApiGet.mockResolvedValue({ data: mockProfile });
    });

    describe('Initial State', () => {
        it('should start with loading state', async () => {
            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });
            expect(result.current.isLoading).toBe(true);
            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });

        it('should fetch profile on mount', async () => {
            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApiGet).toHaveBeenCalledWith('/settings/profile', expect.objectContaining({ signal: expect.any(AbortSignal) }));
            expect(result.current.profile).toEqual(mockProfile);
        });

        it('should handle fetch error', async () => {
            mockApiGet.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Network error');
            expect(result.current.profile).toBeNull();
        });

        it('should use fallback error message for unknown errors', async () => {
            mockApiGet.mockRejectedValue({});

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Failed to fetch profile');
        });

        it('should use API detail message when provided', async () => {
            mockApiGet.mockRejectedValue({
                response: { status: 403, data: { detail: 'Access denied' } },
                message: 'Forbidden',
            });

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Access denied');
        });
    });

    describe('updateProfile', () => {
        it('should update profile successfully', async () => {
            const updatedProfile = { ...mockProfile, first_name: 'Jane' };
            mockApiPatch.mockResolvedValue({ data: updatedProfile });

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            let success: boolean;
            await act(async () => {
                success = await result.current.updateProfile({ first_name: 'Jane' });
            });

            expect(success!).toBe(true);
            expect(mockApiPatch).toHaveBeenCalledWith('/settings/profile', { first_name: 'Jane' });
            await waitFor(() => {
                expect(result.current.profile?.first_name).toBe('Jane');
            });
            expect(mockToast).toHaveBeenCalledWith(
                expect.objectContaining({ title: 'Profile updated' })
            );
        });

        it('should handle update error', async () => {
            mockApiPatch.mockRejectedValue({ message: 'Update failed', response: { data: { detail: 'Server error' } } });

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

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

            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            await act(async () => {
                await result.current.updateProfile({ theme: 'light' });
            });

            await waitFor(() => {
                expect(result.current.profile?.theme).toBe('light');
            });
        });
    });

    describe('refresh', () => {
        it('should re-fetch profile', async () => {
            const { result } = renderHook(() => useProfile(), { wrapper: createWrapper() });

            await waitFor(() => expect(result.current.isLoading).toBe(false));

            const newProfile = { ...mockProfile, first_name: 'Updated' };
            mockApiGet.mockResolvedValue({ data: newProfile });

            await act(async () => {
                await result.current.refresh();
            });

            await waitFor(() => {
                expect(result.current.profile?.first_name).toBe('Updated');
            });
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
