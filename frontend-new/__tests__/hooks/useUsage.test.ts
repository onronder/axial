/**
 * Unit Tests for useUsage Hook
 * 
 * Comprehensive tests covering:
 * - Initial loading state
 * - Successful API calls
 * - Error handling
 * - Derived values calculation
 * - Plan inheritance
 * - Percentage calculations
 * - formatBytes utility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { useUsage, formatBytes } from '@/hooks/useUsage';

// Mock the API module
const mockGetUsageStats = vi.fn();
const mockGetEffectivePlan = vi.fn();

vi.mock('@/lib/api', () => ({
    getUsageStats: () => mockGetUsageStats(),
    getEffectivePlan: () => mockGetEffectivePlan(),
}));

describe('useUsage Hook', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        // Default successful responses
        mockGetUsageStats.mockResolvedValue({
            plan: 'pro',
            files: { used: 25, limit: 100 },
            storage: { used_bytes: 52428800, limit_bytes: 1073741824 }, // 50MB / 1GB
            features: { web_crawl: true, team_enabled: false },
        });
        mockGetEffectivePlan.mockResolvedValue({
            plan: 'pro',
            inherited: false,
        });
    });

    afterEach(() => {
        vi.resetAllMocks();
    });

    describe('Initial State', () => {
        it('should start with loading state', () => {
            const { result } = renderHook(() => useUsage());
            expect(result.current.isLoading).toBe(true);
        });

        it('should have null usage initially', () => {
            const { result } = renderHook(() => useUsage());
            expect(result.current.usage).toBeNull();
        });

        it('should have no error initially', () => {
            const { result } = renderHook(() => useUsage());
            expect(result.current.error).toBeNull();
        });
    });

    describe('Successful Data Fetch', () => {
        it('should fetch usage stats on mount', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);
        });

        it('should fetch effective plan on mount', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetEffectivePlan).toHaveBeenCalledTimes(1);
        });

        it('should populate usage data correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.usage).not.toBeNull();
            });

            expect(result.current.usage?.plan).toBe('pro');
            expect(result.current.usage?.files.used).toBe(25);
            expect(result.current.usage?.files.limit).toBe(100);
        });

        it('should set loading to false after fetch', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });
    });

    describe('Error Handling', () => {
        it('should handle usage fetch error gracefully', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Network error');
            expect(result.current.usage).toBeNull();
        });

        it('should handle non-Error objects in catch', async () => {
            mockGetUsageStats.mockRejectedValue('String error');

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Failed to fetch usage');
        });

        it('should handle effective plan fetch error silently', async () => {
            mockGetEffectivePlan.mockRejectedValue(new Error('Plan error'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Should not affect loading or error state
            expect(result.current.error).toBeNull();
            expect(result.current.effectivePlan).toBeNull();
        });
    });

    describe('Derived Values', () => {
        it('should calculate filesUsed correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesUsed).toBe(25);
        });

        it('should calculate filesLimit correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesLimit).toBe(100);
        });

        it('should calculate storageUsed correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.storageUsed).toBe(52428800);
        });

        it('should calculate storageLimit correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.storageLimit).toBe(1073741824);
        });

        it('should extract canWebCrawl feature flag', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.canWebCrawl).toBe(true);
        });

        it('should extract teamEnabled feature flag', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.teamEnabled).toBe(false);
        });
    });

    describe('Percentage Calculations', () => {
        it('should calculate filesPercent correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // 25/100 = 25%
            expect(result.current.filesPercent).toBe(25);
        });

        it('should calculate storagePercent correctly', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // 52428800 / 1073741824 ≈ 4.88%
            expect(result.current.storagePercent).toBeCloseTo(4.88, 1);
        });

        it('should handle zero limit without division error', async () => {
            mockGetUsageStats.mockResolvedValue({
                plan: 'free',
                files: { used: 0, limit: 0 },
                storage: { used_bytes: 0, limit_bytes: 0 },
                features: { web_crawl: false, team_enabled: false },
            });

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesPercent).toBe(0);
            expect(result.current.storagePercent).toBe(0);
        });

        it('should handle 100% usage', async () => {
            mockGetUsageStats.mockResolvedValue({
                plan: 'starter',
                files: { used: 50, limit: 50 },
                storage: { used_bytes: 1000, limit_bytes: 1000 },
                features: { web_crawl: false, team_enabled: false },
            });

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesPercent).toBe(100);
            expect(result.current.storagePercent).toBe(100);
        });
    });

    describe('Plan Inheritance', () => {
        it('should use effective plan when available', async () => {
            mockGetEffectivePlan.mockResolvedValue({
                plan: 'enterprise',
                inherited: true,
            });

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.effectivePlan).not.toBeNull();
            });

            expect(result.current.plan).toBe('enterprise');
            expect(result.current.isPlanInherited).toBe(true);
        });

        it('should fall back to usage plan when effective plan fails', async () => {
            mockGetEffectivePlan.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.plan).toBe('pro');
            expect(result.current.isPlanInherited).toBe(false);
        });

        it('should default to free when both fail', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));
            mockGetEffectivePlan.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.plan).toBe('free');
        });
    });

    describe('Default Values', () => {
        it('should use default filesLimit when usage is null', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesLimit).toBe(10);
        });

        it('should use default storageLimit when usage is null', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // 100MB default
            expect(result.current.storageLimit).toBe(104857600);
        });
    });

    describe('Refresh Functions', () => {
        it('should provide refresh function', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(typeof result.current.refresh).toBe('function');
        });

        it('should provide refreshPlan function', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(typeof result.current.refreshPlan).toBe('function');
        });

        it('should re-fetch usage when refresh is called', async () => {
            const { result } = renderHook(() => useUsage());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);

            await act(async () => {
                await result.current.refresh();
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(2);
        });
    });
});

describe('formatBytes Utility', () => {
    it('should format 0 bytes', () => {
        expect(formatBytes(0)).toBe('0 B');
    });

    it('should format bytes', () => {
        expect(formatBytes(500)).toBe('500 B');
    });

    it('should format kilobytes', () => {
        expect(formatBytes(1024)).toBe('1 KB');
        expect(formatBytes(1536)).toBe('1.5 KB');
    });

    it('should format megabytes', () => {
        expect(formatBytes(1048576)).toBe('1 MB');
        expect(formatBytes(52428800)).toBe('50 MB');
    });

    it('should format gigabytes', () => {
        expect(formatBytes(1073741824)).toBe('1 GB');
        expect(formatBytes(5368709120)).toBe('5 GB');
    });

    it('should format terabytes', () => {
        expect(formatBytes(1099511627776)).toBe('1 TB');
    });

    it('should round to one decimal place', () => {
        expect(formatBytes(1536)).toBe('1.5 KB');
        expect(formatBytes(1843)).toBe('1.8 KB');
    });
});
