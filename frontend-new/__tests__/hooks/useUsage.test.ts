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

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { UsageProvider, useUsage, formatBytes } from '@/hooks/useUsage';

// Mock the API module
const mockGetUsageStats = vi.fn();
const mockGetEffectivePlan = vi.fn();

vi.mock('@/lib/api', () => ({
    getUsageStats: () => mockGetUsageStats(),
    getEffectivePlan: () => mockGetEffectivePlan(),
    clearAuthCache: vi.fn(),
}));

describe('useUsage Hook', () => {
const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(UsageProvider, null, children);

const createDeferred = <T,>() => {
    let resolve!: (value: T) => void;
    let reject!: (reason?: unknown) => void;
    const promise = new Promise<T>((res, rej) => {
        resolve = res;
        reject = rej;
    });
    return { promise, resolve, reject };
};

    beforeEach(() => {
        vi.clearAllMocks();
        // Default successful responses
        mockGetUsageStats.mockResolvedValue({
            plan: 'pro',
            files: { used: 25, limit: 100 },
            storage: { used_bytes: 52428800, limit_bytes: 1073741824 }, // 50MB / 1GB
            features: { web_crawl: true, team: false, premium_models: false },
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
        it('should start with loading state', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });
            expect(result.current.isLoading).toBe(true);
            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });

        it('should have null usage initially', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });
            expect(result.current.usage).toBeNull();
            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });

        it('should have no error initially', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });
            expect(result.current.error).toBeNull();
            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });
    });

    describe('Successful Data Fetch', () => {
        it('should fetch usage stats on mount', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);
        });

        it('should fetch effective plan on mount', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetEffectivePlan).toHaveBeenCalledTimes(1);
        });

        it('should populate usage data correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.usage).not.toBeNull();
            });

            expect(result.current.usage?.plan).toBe('pro');
            expect(result.current.usage?.files.used).toBe(25);
            expect(result.current.usage?.files.limit).toBe(100);
        });

        it('should set loading to false after fetch', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
            expect(result.current.isLoading).toBe(false);
        });
    });

    describe('Fetch Coordination', () => {
        it('should avoid duplicate fetch while a fetch is in progress', async () => {
            const usageDeferred = createDeferred<any>();
            const planDeferred = createDeferred<any>();

            mockGetUsageStats.mockReturnValue(usageDeferred.promise);
            mockGetEffectivePlan.mockReturnValue(planDeferred.promise);

            const { result } = renderHook(() => useUsage(), { wrapper });

            // getEffectivePlan is called first (before getUsageStats can be called)
            await waitFor(() => {
                expect(mockGetEffectivePlan).toHaveBeenCalledTimes(1);
            });

            // While fetch is in progress, refresh should be a no-op
            await act(async () => {
                await result.current.refresh();
            });

            // Should still be only 1 call (refresh was blocked by fetchInProgress guard)
            expect(mockGetEffectivePlan).toHaveBeenCalledTimes(1);

            // Resolve the deferred promises so the test cleans up
            planDeferred.resolve({ plan: 'pro', inherited: false });
            usageDeferred.resolve({
                plan: 'pro',
                files: { used: 25, limit: 100 },
                storage: { used_bytes: 52428800, limit_bytes: 1073741824 },
                features: { web_crawl: true, team: false },
            });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });
        });

        it('should not refetch on rerender once fetched', async () => {
            const { result, rerender } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const callsAfterFirstRender = mockGetUsageStats.mock.calls.length;
            rerender();

            expect(mockGetUsageStats.mock.calls.length).toBe(callsAfterFirstRender);
        });

        it('should guard against duplicate fetch in StrictMode', async () => {
            const strictWrapper = ({ children }: { children: React.ReactNode }) =>
                React.createElement(
                    React.StrictMode,
                    null,
                    React.createElement(UsageProvider, null, children)
                );

            renderHook(() => useUsage(), { wrapper: strictWrapper });

            await waitFor(() => {
                expect(mockGetUsageStats).toHaveBeenCalledTimes(1);
            });
        });

        it('should short-circuit repeated effect runs when fetchAll changes', async () => {
            vi.resetModules();
            vi.doMock('react', async () => {
                const actual = await vi.importActual<typeof import('react')>('react');
                return {
                    ...actual,
                    useEffect: (effect: any, deps?: any[]) => {
                        actual.useEffect(effect, deps);
                        actual.useEffect(effect, deps);
                    },
                };
            });

            const { UsageProvider: IsolatedUsageProvider, useUsage: isolatedUseUsage } =
                await import('@/hooks/useUsage');

            const isolatedWrapper = ({ children }: { children: React.ReactNode }) =>
                React.createElement(IsolatedUsageProvider, null, children);

            const { result } = renderHook(() => isolatedUseUsage(), { wrapper: isolatedWrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);

            vi.unmock('react');
        });
    });
    });

    describe('Error Handling', () => {
        it('should handle usage fetch error gracefully', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Network error'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('Network error');
            expect(result.current.usage).toBeNull();
        });

        it('should handle non-Error objects in catch', async () => {
            mockGetUsageStats.mockRejectedValue('String error');

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBe('String error');
        });

        it('should handle effective plan fetch error', async () => {
            mockGetEffectivePlan.mockRejectedValue(new Error('Plan error'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // When getEffectivePlan throws, the outer catch sets the error
            // (getUsageStats is never called because getEffectivePlan is called first)
            expect(result.current.error).toBe('Plan error');
            expect(result.current.effectivePlan).toBeNull();
        });
    });

    describe('Derived Values', () => {
        it('should calculate filesUsed correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesUsed).toBe(25);
        });

        it('should calculate filesLimit correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesLimit).toBe(100);
        });

        it('should calculate storageUsed correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.storageUsed).toBe(52428800);
        });

        it('should calculate storageLimit correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.storageLimit).toBe(1073741824);
        });

        it('should extract canWebCrawl feature flag', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.canWebCrawl).toBe(true);
        });

        it('should extract teamEnabled feature flag', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.teamEnabled).toBe(false);
        });
    });

    describe('Percentage Calculations', () => {
        it('should calculate filesPercent correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // 25/100 = 25%
            expect(result.current.filesPercent).toBe(25);
        });

        it('should calculate storagePercent correctly', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

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
                features: { web_crawl: false, team: false },
            });

            const { result } = renderHook(() => useUsage(), { wrapper });

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
                features: { web_crawl: false, team: false },
            });

            const { result } = renderHook(() => useUsage(), { wrapper });

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

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.effectivePlan).not.toBeNull();
            });

            expect(result.current.plan).toBe('enterprise');
            expect(result.current.isPlanInherited).toBe(true);
        });

        it('should fall back to free plan when effective plan fails', async () => {
            mockGetEffectivePlan.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // When getEffectivePlan throws, it hits the outer catch before getUsageStats runs.
            // So both effectivePlan and usage remain null, and plan falls back to 'free'.
            expect(result.current.plan).toBe('free');
            expect(result.current.isPlanInherited).toBe(false);
        });

        it('should default to free when both fail', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));
            mockGetEffectivePlan.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.plan).toBe('free');
        });
    });

    describe('Default Values', () => {
        it('should use default filesLimit when usage is null', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.filesLimit).toBe(10);
        });

        it('should use default storageLimit when usage is null', async () => {
            mockGetUsageStats.mockRejectedValue(new Error('Failed'));

            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // 100MB default
            expect(result.current.storageLimit).toBe(104857600);
        });
    });

    describe('Refresh Functions', () => {
        it('should provide refresh function', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(typeof result.current.refresh).toBe('function');
        });

        it('should provide refreshPlan function', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(typeof result.current.refreshPlan).toBe('function');
        });

        it('should re-fetch usage when refresh is called', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);

            await act(async () => {
                await result.current.refresh();
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(2);
        });

        it('should skip fetch when cache is fresh', async () => {
            const { result } = renderHook(() => useUsage(), { wrapper });

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);

            await act(async () => {
                await result.current.refresh(false);
            });

            expect(mockGetUsageStats).toHaveBeenCalledTimes(1);
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

describe('useUsage outside provider', () => {
    it('should throw when used outside UsageProvider', () => {
        expect(() => {
            renderHook(() => useUsage());
        }).toThrow('useUsage must be used within a UsageProvider');
    });
});
