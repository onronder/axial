import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { IngestionProgressProvider, useIngestionProgress } from '@/hooks/useIngestionProgress';

// =============================================================================
// Test Setup
// =============================================================================

// Create wrapper with provider
const createWrapper = () => {
    // eslint-disable-next-line react/display-name
    return ({ children }: { children: React.ReactNode }) => (
        <IngestionProgressProvider>{children}</IngestionProgressProvider>
    );
};

// Mock console.log to avoid noisy output during tests
beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {});
});

// =============================================================================
// Tests
// =============================================================================

describe('useIngestionProgress', () => {
    // =========================================================================
    // Context Provider Tests
    // =========================================================================
    
    describe('Context Provider', () => {
        it('should throw error when used outside provider', () => {
            // Suppress console.error for this test
            const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
            
            expect(() => {
                renderHook(() => useIngestionProgress());
            }).toThrow('useIngestionProgress must be used within an IngestionProgressProvider');
            
            spy.mockRestore();
        });

        it('should provide default values within provider', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            expect(result.current.activeJobIds.size).toBe(0);
            expect(result.current.expandedJobId).toBeNull();
            expect(typeof result.current.registerJob).toBe('function');
            expect(typeof result.current.unregisterJob).toBe('function');
            expect(typeof result.current.expandJob).toBe('function');
            expect(typeof result.current.isJobRegistered).toBe('function');
            expect(typeof result.current.markJobCompleted).toBe('function');
            expect(typeof result.current.hasJobCompleted).toBe('function');
        });
    });

    // =========================================================================
    // Job Registration Tests
    // =========================================================================
    
    describe('Job Registration', () => {
        it('should register a new job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
            });

            expect(result.current.activeJobIds.has('job-123')).toBe(true);
            expect(result.current.activeJobIds.size).toBe(1);
        });

        it('should not duplicate job registration', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.registerJob('job-123');
                result.current.registerJob('job-123');
            });

            expect(result.current.activeJobIds.size).toBe(1);
        });

        it('should track multiple jobs simultaneously', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-1');
                result.current.registerJob('job-2');
                result.current.registerJob('job-3');
            });

            expect(result.current.activeJobIds.size).toBe(3);
            expect(result.current.activeJobIds.has('job-1')).toBe(true);
            expect(result.current.activeJobIds.has('job-2')).toBe(true);
            expect(result.current.activeJobIds.has('job-3')).toBe(true);
        });

        it('should ignore empty job ID', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('');
            });

            expect(result.current.activeJobIds.size).toBe(0);
        });

        it('should return true for registered jobs via isJobRegistered', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
            });

            expect(result.current.isJobRegistered('job-123')).toBe(true);
            expect(result.current.isJobRegistered('other-job')).toBe(false);
        });
    });

    // =========================================================================
    // Job Unregistration Tests
    // =========================================================================
    
    describe('Job Unregistration', () => {
        it('should unregister a job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
            });

            expect(result.current.activeJobIds.has('job-123')).toBe(true);

            act(() => {
                result.current.unregisterJob('job-123');
            });

            expect(result.current.activeJobIds.has('job-123')).toBe(false);
            expect(result.current.activeJobIds.size).toBe(0);
        });

        it('should clear expanded state when unregistering expanded job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.expandJob('job-123');
            });

            expect(result.current.expandedJobId).toBe('job-123');

            act(() => {
                result.current.unregisterJob('job-123');
            });

            expect(result.current.expandedJobId).toBeNull();
        });

        it('should not affect expanded state when unregistering different job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-1');
                result.current.registerJob('job-2');
                result.current.expandJob('job-1');
            });

            act(() => {
                result.current.unregisterJob('job-2');
            });

            expect(result.current.expandedJobId).toBe('job-1');
        });

        it('should clean up completion tracking when unregistering', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.markJobCompleted('job-123');
            });

            expect(result.current.hasJobCompleted('job-123')).toBe(true);

            act(() => {
                result.current.unregisterJob('job-123');
            });

            expect(result.current.hasJobCompleted('job-123')).toBe(false);
        });

        it('should not error on unregistering unknown job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            expect(() => {
                act(() => {
                    result.current.unregisterJob('unknown-job');
                });
            }).not.toThrow();
        });

        it('should ignore empty job ID for unregistration', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
            });

            act(() => {
                result.current.unregisterJob('');
            });

            // Job should still be registered
            expect(result.current.activeJobIds.has('job-123')).toBe(true);
        });
    });

    // =========================================================================
    // Completion Tracking Tests
    // =========================================================================
    
    describe('Completion Tracking', () => {
        it('should mark job as completed', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.markJobCompleted('job-123');
            });

            expect(result.current.hasJobCompleted('job-123')).toBe(true);
        });

        it('should return true for completed jobs', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.markJobCompleted('job-completed');
            });

            expect(result.current.hasJobCompleted('job-completed')).toBe(true);
        });

        it('should return false for non-completed jobs', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-active');
            });

            expect(result.current.hasJobCompleted('job-active')).toBe(false);
        });

        it('should prevent duplicate completion marks', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            // Mark completed multiple times
            act(() => {
                result.current.markJobCompleted('job-123');
                result.current.markJobCompleted('job-123');
                result.current.markJobCompleted('job-123');
            });

            // Should still work correctly
            expect(result.current.hasJobCompleted('job-123')).toBe(true);
        });

        it('should ignore empty job ID for completion marking', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.markJobCompleted('');
            });

            expect(result.current.hasJobCompleted('')).toBe(false);
        });
    });

    // =========================================================================
    // Job Expansion Tests
    // =========================================================================
    
    describe('Job Expansion', () => {
        it('should expand a job', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.expandJob('job-123');
            });

            expect(result.current.expandedJobId).toBe('job-123');
        });

        it('should collapse when null is passed', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-123');
                result.current.expandJob('job-123');
            });

            expect(result.current.expandedJobId).toBe('job-123');

            act(() => {
                result.current.expandJob(null);
            });

            expect(result.current.expandedJobId).toBeNull();
        });

        it('should only allow one expanded job at a time', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-1');
                result.current.registerJob('job-2');
                result.current.expandJob('job-1');
            });

            expect(result.current.expandedJobId).toBe('job-1');

            act(() => {
                result.current.expandJob('job-2');
            });

            expect(result.current.expandedJobId).toBe('job-2');
        });

        it('should allow expanding unregistered job (for late registration)', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            // Expand before registering
            act(() => {
                result.current.expandJob('job-123');
            });

            expect(result.current.expandedJobId).toBe('job-123');
        });
    });

    // =========================================================================
    // Integration Tests
    // =========================================================================
    
    describe('Integration', () => {
        it('should handle full job lifecycle', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            // 1. Register job
            act(() => {
                result.current.registerJob('job-lifecycle');
            });
            expect(result.current.isJobRegistered('job-lifecycle')).toBe(true);

            // 2. Expand job
            act(() => {
                result.current.expandJob('job-lifecycle');
            });
            expect(result.current.expandedJobId).toBe('job-lifecycle');

            // 3. Mark as completed (prevents re-triggering)
            act(() => {
                result.current.markJobCompleted('job-lifecycle');
            });
            expect(result.current.hasJobCompleted('job-lifecycle')).toBe(true);

            // 4. Unregister job
            act(() => {
                result.current.unregisterJob('job-lifecycle');
            });
            expect(result.current.isJobRegistered('job-lifecycle')).toBe(false);
            expect(result.current.expandedJobId).toBeNull();
            expect(result.current.hasJobCompleted('job-lifecycle')).toBe(false);
        });

        it('should handle multiple jobs with different states', () => {
            const { result } = renderHook(() => useIngestionProgress(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.registerJob('job-1');
                result.current.registerJob('job-2');
                result.current.registerJob('job-3');
                
                result.current.markJobCompleted('job-2');
                result.current.expandJob('job-1');
                result.current.unregisterJob('job-3');
            });

            expect(result.current.activeJobIds.size).toBe(2); // job-1 and job-2
            expect(result.current.isJobRegistered('job-1')).toBe(true);
            expect(result.current.isJobRegistered('job-2')).toBe(true);
            expect(result.current.isJobRegistered('job-3')).toBe(false);
            expect(result.current.hasJobCompleted('job-2')).toBe(true);
            expect(result.current.expandedJobId).toBe('job-1');
        });
    });
});
