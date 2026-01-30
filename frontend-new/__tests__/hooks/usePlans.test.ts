/**
 * usePlans Hook Tests
 * 
 * Tests for the pricing plans fetching hook.
 * Covers data fetching, fallback handling, loading states, and cleanup.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { usePlans, PricingPlan } from '@/hooks/usePlans';
import { api } from '@/lib/api';

// =============================================================================
// Mocks
// =============================================================================

vi.mock('@/lib/api', () => ({
    api: {
        get: vi.fn(),
    },
}));

const mockApiGet = vi.mocked(api.get);

// =============================================================================
// Test Data
// =============================================================================

const mockPlans: PricingPlan[] = [
    {
        id: 'starter',
        name: 'Starter',
        description: 'Perfect for getting started',
        price_amount: 499,
        price_currency: 'usd',
        interval: 'month',
        type: 'starter',
        features: ['100 queries/month', '2 connected sources'],
        button_text: 'Get Started',
        button_variant: 'outline',
        popular: false,
    },
    {
        id: 'pro',
        name: 'Pro',
        description: 'For professionals',
        price_amount: 2900,
        price_currency: 'usd',
        interval: 'month',
        type: 'pro',
        features: ['Unlimited queries', 'Unlimited sources', 'Priority support'],
        button_text: 'Start Free Trial',
        button_variant: 'default',
        popular: true,
    },
];

const FALLBACK_PLANS: PricingPlan[] = [
    {
        id: 'starter',
        name: 'Starter',
        description: 'Perfect for trying out Axio Hub',
        price_amount: 499,
        price_currency: 'usd',
        interval: 'month',
        type: 'starter',
        features: ['100 queries/month', '2 connected sources', 'Basic RAG search'],
        button_text: 'Get Started',
        button_variant: 'outline',
        popular: false,
    },
    {
        id: 'pro',
        name: 'Pro',
        description: 'For professionals who need more',
        price_amount: 2900,
        price_currency: 'usd',
        interval: 'month',
        type: 'pro',
        features: ['Unlimited queries', 'Unlimited sources', 'Hybrid RAG + semantic', 'Priority support'],
        button_text: 'Start Free Trial',
        button_variant: 'default',
        popular: true,
    },
];

// =============================================================================
// Tests
// =============================================================================

describe('usePlans', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('Data Fetching', () => {
        it('should fetch plans on mount', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(mockApiGet).toHaveBeenCalledWith('/billing/plans', expect.any(Object));
            expect(result.current.plans).toHaveLength(2);
            expect(result.current.plans[0].name).toBe('Starter');
            expect(result.current.plans[1].name).toBe('Pro');
        });

        it('should show loading state initially', () => {
            mockApiGet.mockImplementation(() => new Promise(() => {})); // Never resolves

            const { result } = renderHook(() => usePlans());

            expect(result.current.isLoading).toBe(true);
            expect(result.current.plans).toEqual([]);
        });

        it('should update plans on success', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            expect(result.current.plans).toEqual([]);

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.plans).toEqual(mockPlans);
            expect(result.current.error).toBeNull();
        });

        it('should include abort signal in API request', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            renderHook(() => usePlans());

            expect(mockApiGet).toHaveBeenCalledWith('/billing/plans', {
                signal: expect.any(AbortSignal),
            });
        });
    });

    describe('Fallback Handling', () => {
        it('should use fallback plans on API error', async () => {
            const error = new Error('Network error');
            mockApiGet.mockRejectedValueOnce(error);

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Should have fallback plans
            expect(result.current.plans).toHaveLength(2);
            expect(result.current.plans[0].id).toBe('starter');
            expect(result.current.plans[1].id).toBe('pro');
            
            // Should have error set
            expect(result.current.error).not.toBeNull();
            expect(result.current.error?.message).toBe('Network error');
        });

        it('should use fallback plans on empty response', async () => {
            mockApiGet.mockResolvedValueOnce({ data: [] });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Should have fallback plans due to empty array
            expect(result.current.plans).toHaveLength(2);
            expect(result.current.error).not.toBeNull();
        });

        it('should use fallback plans when API returns null', async () => {
            mockApiGet.mockResolvedValueOnce({ data: null });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            // Should have fallback plans
            expect(result.current.plans).toHaveLength(2);
        });

        it('should not error on request cancellation', async () => {
            const cancelError = new Error('Request cancelled');
            (cancelError as any).code = 'ERR_CANCELED';
            mockApiGet.mockRejectedValueOnce(cancelError);

            const { result, unmount } = renderHook(() => usePlans());

            // Unmount immediately to trigger abort
            unmount();

            // Plans should remain empty (not fallback) because cancellation is ignored
            expect(result.current.plans).toEqual([]);
        });
    });

    describe('Cleanup', () => {
        it('should cancel request on unmount', async () => {
            let abortSignal: AbortSignal | undefined;

            mockApiGet.mockImplementation((_url, config) => {
                abortSignal = config?.signal;
                return new Promise((_, reject) => {
                    // Simulate abort handling
                    if (abortSignal) {
                        abortSignal.addEventListener('abort', () => {
                            const error = new Error('Request cancelled');
                            (error as any).code = 'ERR_CANCELED';
                            reject(error);
                        });
                    }
                });
            });

            const { unmount } = renderHook(() => usePlans());

            expect(abortSignal).toBeDefined();
            expect(abortSignal?.aborted).toBe(false);

            unmount();

            expect(abortSignal?.aborted).toBe(true);
        });
    });

    describe('Return Values', () => {
        it('should return correct shape', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current).toHaveProperty('plans');
            expect(result.current).toHaveProperty('isLoading');
            expect(result.current).toHaveProperty('error');
            expect(Array.isArray(result.current.plans)).toBe(true);
            expect(typeof result.current.isLoading).toBe('boolean');
        });

        it('should have null error on successful fetch', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            expect(result.current.error).toBeNull();
        });
    });

    describe('Plan Data Validation', () => {
        it('should correctly map plan properties', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const proPlan = result.current.plans.find(p => p.id === 'pro');
            expect(proPlan).toBeDefined();
            expect(proPlan?.name).toBe('Pro');
            expect(proPlan?.popular).toBe(true);
            expect(proPlan?.price_amount).toBe(2900);
            expect(proPlan?.features).toContain('Unlimited queries');
        });

        it('should preserve plan features array', async () => {
            mockApiGet.mockResolvedValueOnce({ data: mockPlans });

            const { result } = renderHook(() => usePlans());

            await waitFor(() => {
                expect(result.current.isLoading).toBe(false);
            });

            const starterPlan = result.current.plans.find(p => p.id === 'starter');
            expect(starterPlan?.features).toHaveLength(2);
            expect(starterPlan?.features).toEqual(['100 queries/month', '2 connected sources']);
        });
    });
});
