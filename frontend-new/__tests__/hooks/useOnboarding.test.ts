/**
 * useOnboarding Hook Tests
 * 
 * Tests for the onboarding state management hook.
 * Covers initial state, navigation, completion, skip, and storage persistence.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useOnboarding, OnboardingStep } from '@/hooks/useOnboarding';

// =============================================================================
// Mocks
// =============================================================================

const mockGetItem = vi.fn();
const mockSetItem = vi.fn();
const mockRemoveItem = vi.fn();

vi.mock('@/lib/storage', () => ({
    safeLocalStorage: {
        getItem: (...args: unknown[]) => mockGetItem(...args),
        setItem: (...args: unknown[]) => mockSetItem(...args),
        removeItem: (...args: unknown[]) => mockRemoveItem(...args),
    },
}));

// =============================================================================
// Tests
// =============================================================================

describe('useOnboarding', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.useFakeTimers();
        mockGetItem.mockReturnValue(null);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    describe('Initial State', () => {
        it('should not show onboarding if completed', () => {
            mockGetItem.mockImplementation((key: string) => {
                if (key === 'onboarding_complete') return 'true';
                return null;
            });

            const { result } = renderHook(() => useOnboarding());

            // Advance timers to trigger the setTimeout
            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(false);
        });

        it('should not show onboarding if skipped', () => {
            mockGetItem.mockImplementation((key: string) => {
                if (key === 'onboarding_skipped') return 'true';
                return null;
            });

            const { result } = renderHook(() => useOnboarding());

            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(false);
        });

        it('should show onboarding for new users after delay', () => {
            mockGetItem.mockReturnValue(null);

            const { result } = renderHook(() => useOnboarding());

            // Initially not shown
            expect(result.current.showOnboarding).toBe(false);

            // After delay, should show
            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(true);
        });

        it('should start at welcome step', () => {
            const { result } = renderHook(() => useOnboarding());

            expect(result.current.currentStep).toBe('welcome');
        });

        it('should not be complete initially', () => {
            const { result } = renderHook(() => useOnboarding());

            expect(result.current.isComplete).toBe(false);
        });
    });

    describe('Navigation', () => {
        it('should advance to next step', () => {
            const { result } = renderHook(() => useOnboarding());

            expect(result.current.currentStep).toBe('welcome');

            act(() => {
                result.current.nextStep();
            });

            expect(result.current.currentStep).toBe('connect');

            act(() => {
                result.current.nextStep();
            });

            expect(result.current.currentStep).toBe('upload');

            act(() => {
                result.current.nextStep();
            });

            expect(result.current.currentStep).toBe('complete');
        });

        it('should go back to previous step', () => {
            const { result } = renderHook(() => useOnboarding());

            // Move forward first - each step needs its own act
            act(() => {
                result.current.nextStep();
            });
            act(() => {
                result.current.nextStep();
            });

            expect(result.current.currentStep).toBe('upload');

            // Go back
            act(() => {
                result.current.prevStep();
            });

            expect(result.current.currentStep).toBe('connect');

            act(() => {
                result.current.prevStep();
            });

            expect(result.current.currentStep).toBe('welcome');
        });

        it('should not go before first step', () => {
            const { result } = renderHook(() => useOnboarding());

            expect(result.current.currentStep).toBe('welcome');

            act(() => {
                result.current.prevStep();
            });

            // Should still be at welcome
            expect(result.current.currentStep).toBe('welcome');
        });

        it('should not advance past last step', () => {
            const { result } = renderHook(() => useOnboarding());

            // Move to the last step - each step needs its own act
            act(() => {
                result.current.nextStep(); // -> connect
            });
            act(() => {
                result.current.nextStep(); // -> upload
            });
            act(() => {
                result.current.nextStep(); // -> complete
            });

            expect(result.current.currentStep).toBe('complete');

            act(() => {
                result.current.nextStep(); // Should stay at complete
            });

            expect(result.current.currentStep).toBe('complete');
        });

        it('should follow correct step order', () => {
            const { result } = renderHook(() => useOnboarding());
            const expectedSteps: OnboardingStep[] = ['welcome', 'connect', 'upload', 'complete'];

            expectedSteps.forEach((step, index) => {
                if (index === 0) {
                    expect(result.current.currentStep).toBe(step);
                } else {
                    act(() => {
                        result.current.nextStep();
                    });
                    expect(result.current.currentStep).toBe(step);
                }
            });
        });
    });

    describe('Completion', () => {
        it('should mark onboarding as complete', () => {
            const { result } = renderHook(() => useOnboarding());

            act(() => {
                result.current.completeOnboarding();
            });

            expect(result.current.isComplete).toBe(true);
        });

        it('should persist completion to storage', () => {
            const { result } = renderHook(() => useOnboarding());

            act(() => {
                result.current.completeOnboarding();
            });

            expect(mockSetItem).toHaveBeenCalledWith('onboarding_complete', 'true');
        });

        it('should set step to complete', () => {
            const { result } = renderHook(() => useOnboarding());

            act(() => {
                result.current.completeOnboarding();
            });

            expect(result.current.currentStep).toBe('complete');
        });
    });

    describe('Skip', () => {
        it('should mark onboarding as skipped', () => {
            const { result } = renderHook(() => useOnboarding());

            // First show onboarding
            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(true);

            act(() => {
                result.current.skipOnboarding();
            });

            expect(result.current.showOnboarding).toBe(false);
        });

        it('should persist skip to storage', () => {
            const { result } = renderHook(() => useOnboarding());

            act(() => {
                result.current.skipOnboarding();
            });

            expect(mockSetItem).toHaveBeenCalledWith('onboarding_skipped', 'true');
        });

        it('should close onboarding', () => {
            const { result } = renderHook(() => useOnboarding());

            // First show onboarding
            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(true);

            act(() => {
                result.current.skipOnboarding();
            });

            expect(result.current.showOnboarding).toBe(false);
        });
    });

    describe('Close Onboarding', () => {
        it('should close onboarding without marking as skipped', () => {
            const { result } = renderHook(() => useOnboarding());

            // First show onboarding
            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(result.current.showOnboarding).toBe(true);

            act(() => {
                result.current.closeOnboarding();
            });

            expect(result.current.showOnboarding).toBe(false);
            // Should NOT have called setItem for 'onboarding_skipped'
            expect(mockSetItem).not.toHaveBeenCalledWith('onboarding_skipped', 'true');
        });
    });

    describe('Return Values', () => {
        it('should return all expected properties and functions', () => {
            const { result } = renderHook(() => useOnboarding());

            expect(result.current).toHaveProperty('showOnboarding');
            expect(result.current).toHaveProperty('currentStep');
            expect(result.current).toHaveProperty('isComplete');
            expect(result.current).toHaveProperty('nextStep');
            expect(result.current).toHaveProperty('prevStep');
            expect(result.current).toHaveProperty('completeOnboarding');
            expect(result.current).toHaveProperty('skipOnboarding');
            expect(result.current).toHaveProperty('closeOnboarding');

            expect(typeof result.current.showOnboarding).toBe('boolean');
            expect(typeof result.current.currentStep).toBe('string');
            expect(typeof result.current.isComplete).toBe('boolean');
            expect(typeof result.current.nextStep).toBe('function');
            expect(typeof result.current.prevStep).toBe('function');
            expect(typeof result.current.completeOnboarding).toBe('function');
            expect(typeof result.current.skipOnboarding).toBe('function');
            expect(typeof result.current.closeOnboarding).toBe('function');
        });
    });

    describe('Storage Integration', () => {
        it('should check both completion and skip status on mount', () => {
            renderHook(() => useOnboarding());

            act(() => {
                vi.advanceTimersByTime(1500);
            });

            expect(mockGetItem).toHaveBeenCalledWith('onboarding_complete');
            expect(mockGetItem).toHaveBeenCalledWith('onboarding_skipped');
        });
    });
});
