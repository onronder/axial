/**
 * useQuotaStatus Hook Tests
 * 
 * Tests for the quota status tracking hook and provider.
 * Covers initial state, quota detection, provider checking, clearing, and manual marking.
 */

import React from 'react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { QuotaStatusProvider, useQuotaStatus } from '@/hooks/useQuotaStatus';

// =============================================================================
// Mocks (using vi.hoisted for proper hoisting)
// =============================================================================

const { 
    mockGetItem, 
    mockSetItem, 
    mockRemoveItem, 
    mockSetJson,
    mockSubscribe,
    mockUnsubscribe,
    mockRemoveChannel,
    mockChannel,
} = vi.hoisted(() => {
    const mockGetItem = vi.fn();
    const mockSetItem = vi.fn();
    const mockRemoveItem = vi.fn();
    const mockSetJson = vi.fn();
    const mockSubscribe = vi.fn();
    const mockUnsubscribe = vi.fn();
    const mockRemoveChannel = vi.fn();
    
    // Create channel mock that supports proper chaining: channel().on().subscribe()
    const createChannelInstance = () => {
        const instance: Record<string, unknown> = {};
        
        // .on() returns an object with .subscribe()
        const onResult = {
            subscribe: mockSubscribe.mockReturnValue(instance),
        };
        
        instance.on = vi.fn().mockReturnValue(onResult);
        instance.subscribe = mockSubscribe;
        instance.unsubscribe = mockUnsubscribe;
        
        return instance;
    };
    
    const mockChannel = vi.fn(() => createChannelInstance());
    
    return {
        mockGetItem,
        mockSetItem,
        mockRemoveItem,
        mockSetJson,
        mockSubscribe,
        mockUnsubscribe,
        mockRemoveChannel,
        mockChannel,
    };
});

vi.mock('@/lib/storage', () => ({
    safeLocalStorage: {
        getItem: (...args: unknown[]) => mockGetItem(...args),
        setItem: (...args: unknown[]) => mockSetItem(...args),
        removeItem: (...args: unknown[]) => mockRemoveItem(...args),
        setJson: (...args: unknown[]) => mockSetJson(...args),
    },
}));

const mockUser = { id: 'user-123', email: 'test@example.com' };
vi.mock('@/hooks/useAuth', () => ({
    useAuth: () => ({ user: mockUser }),
}));

vi.mock('@/lib/supabase', () => ({
    supabase: {
        channel: mockChannel,
        removeChannel: mockRemoveChannel,
    },
}));

vi.mock('@/lib/sourceType', () => ({
    normalizeSourceType: (type: string) => type.toLowerCase().replace(/_/g, '-'),
}));

// =============================================================================
// Test Helpers
// =============================================================================

const createWrapper = () => {
    function Wrapper({ children }: { children: React.ReactNode }) {
        return <QuotaStatusProvider>{children}</QuotaStatusProvider>;
    }
    Wrapper.displayName = 'TestWrapper';
    return Wrapper;
};

// =============================================================================
// Tests
// =============================================================================

describe('useQuotaStatus', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        mockGetItem.mockReturnValue(null);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    describe('Context Provider', () => {
        it('should provide default values when used outside provider', () => {
            // Without provider, should return no-op implementation
            const { result } = renderHook(() => useQuotaStatus());

            expect(result.current.quotaExceededProviders.size).toBe(0);
            expect(result.current.hasQuotaIssue).toBe(false);
            expect(typeof result.current.isProviderQuotaExceeded).toBe('function');
            expect(typeof result.current.clearQuotaStatus).toBe('function');
            expect(typeof result.current.markQuotaExceeded).toBe('function');
        });

        it('should provide context values within provider', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.quotaExceededProviders).toBeInstanceOf(Set);
            expect(result.current.hasQuotaIssue).toBe(false);
            expect(typeof result.current.isProviderQuotaExceeded).toBe('function');
            expect(typeof result.current.clearQuotaStatus).toBe('function');
            expect(typeof result.current.markQuotaExceeded).toBe('function');
        });
    });

    describe('Initial State', () => {
        it('should have no quota issues initially', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.quotaExceededProviders.size).toBe(0);
            expect(result.current.hasQuotaIssue).toBe(false);
        });

        it('should load persisted quota status from storage', () => {
            const storedData = JSON.stringify({
                providers: ['google-drive', 'dropbox'],
                timestamp: Date.now(),
            });
            mockGetItem.mockReturnValue(storedData);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.quotaExceededProviders.size).toBe(2);
            expect(result.current.hasQuotaIssue).toBe(true);
        });

        it('should ignore expired quota status', () => {
            const expiredTimestamp = Date.now() - (25 * 60 * 60 * 1000); // 25 hours ago
            const storedData = JSON.stringify({
                providers: ['google-drive'],
                timestamp: expiredTimestamp,
            });
            mockGetItem.mockReturnValue(storedData);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.quotaExceededProviders.size).toBe(0);
            expect(result.current.hasQuotaIssue).toBe(false);
            expect(mockRemoveItem).toHaveBeenCalledWith('axio_quota_exceeded_providers');
        });

        it('should clear invalid stored data', () => {
            mockGetItem.mockReturnValue('invalid-json');

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.quotaExceededProviders.size).toBe(0);
            expect(mockRemoveItem).toHaveBeenCalledWith('axio_quota_exceeded_providers');
        });
    });

    describe('Provider Checking', () => {
        it('should return true for exceeded provider', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.markQuotaExceeded('google_drive');
            });

            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(true);
        });

        it('should return false for non-exceeded provider', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(false);
        });

        it('should handle provider name normalization', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.markQuotaExceeded('Google_Drive');
            });

            // Should be normalized and found
            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(true);
        });
    });

    describe('Clearing Status', () => {
        it('should clear specific provider status', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Add multiple providers
            act(() => {
                result.current.markQuotaExceeded('google_drive');
                result.current.markQuotaExceeded('dropbox');
            });

            expect(result.current.quotaExceededProviders.size).toBe(2);

            // Clear one provider
            act(() => {
                result.current.clearQuotaStatus('google_drive');
            });

            expect(result.current.quotaExceededProviders.size).toBe(1);
            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(false);
            expect(result.current.isProviderQuotaExceeded('dropbox')).toBe(true);
        });

        it('should clear all provider statuses when no provider specified', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Add multiple providers
            act(() => {
                result.current.markQuotaExceeded('google_drive');
                result.current.markQuotaExceeded('dropbox');
                result.current.markQuotaExceeded('onedrive');
            });

            expect(result.current.quotaExceededProviders.size).toBe(3);

            // Clear all
            act(() => {
                result.current.clearQuotaStatus();
            });

            expect(result.current.quotaExceededProviders.size).toBe(0);
            expect(result.current.hasQuotaIssue).toBe(false);
        });
    });

    describe('Manual Marking', () => {
        it('should manually mark provider as exceeded', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.hasQuotaIssue).toBe(false);

            act(() => {
                result.current.markQuotaExceeded('notion');
            });

            expect(result.current.hasQuotaIssue).toBe(true);
            expect(result.current.isProviderQuotaExceeded('notion')).toBe(true);
        });

        it('should not duplicate providers when marked multiple times', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            act(() => {
                result.current.markQuotaExceeded('google_drive');
                result.current.markQuotaExceeded('google_drive');
                result.current.markQuotaExceeded('google_drive');
            });

            expect(result.current.quotaExceededProviders.size).toBe(1);
        });
    });

    describe('Realtime Subscription', () => {
        it('should subscribe to ingestion job updates', () => {
            renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(mockChannel).toHaveBeenCalledWith(`quota_status_${mockUser.id}`);
            expect(mockSubscribe).toHaveBeenCalled();
        });

        it('should unsubscribe on unmount', () => {
            const { unmount } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            unmount();

            expect(mockUnsubscribe).toHaveBeenCalled();
            expect(mockRemoveChannel).toHaveBeenCalled();
        });

        it('should detect quota exceeded from failed job updates', async () => {
            // Capture the callback passed to .on()
            let capturedCallback: ((payload: unknown) => void) | null = null;
            
            const channelInstance = {
                on: vi.fn((event, config, callback) => {
                    capturedCallback = callback;
                    return {
                        subscribe: vi.fn().mockReturnValue(channelInstance),
                    };
                }),
                unsubscribe: vi.fn(),
            };
            mockChannel.mockReturnValue(channelInstance);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Simulate a failed job with quota error
            act(() => {
                if (capturedCallback) {
                    capturedCallback({
                        new: {
                            status: 'failed',
                            provider: 'google_drive',
                            error_message: 'File limit exceeded. Please upgrade your plan.',
                        },
                    });
                }
            });

            await waitFor(() => {
                expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(true);
            });
        });

        it('should detect quota warning from completed job with limit message', async () => {
            let capturedCallback: ((payload: unknown) => void) | null = null;
            
            const channelInstance = {
                on: vi.fn((event, config, callback) => {
                    capturedCallback = callback;
                    return {
                        subscribe: vi.fn().mockReturnValue(channelInstance),
                    };
                }),
                unsubscribe: vi.fn(),
            };
            mockChannel.mockReturnValue(channelInstance);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Simulate a completed job with quota warning
            act(() => {
                if (capturedCallback) {
                    capturedCallback({
                        new: {
                            status: 'completed',
                            provider: 'dropbox',
                            message: 'Completed with storage limit warning',
                        },
                    });
                }
            });

            await waitFor(() => {
                expect(result.current.isProviderQuotaExceeded('dropbox')).toBe(true);
            });
        });

        it('should not mark quota exceeded for non-quota errors', async () => {
            let capturedCallback: ((payload: unknown) => void) | null = null;
            
            const channelInstance = {
                on: vi.fn((event, config, callback) => {
                    capturedCallback = callback;
                    return {
                        subscribe: vi.fn().mockReturnValue(channelInstance),
                    };
                }),
                unsubscribe: vi.fn(),
            };
            mockChannel.mockReturnValue(channelInstance);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Simulate a failed job with non-quota error
            act(() => {
                if (capturedCallback) {
                    capturedCallback({
                        new: {
                            status: 'failed',
                            provider: 'google_drive',
                            error_message: 'Network timeout',
                        },
                    });
                }
            });

            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(false);
        });

        it('should not mark quota exceeded when no error message', async () => {
            let capturedCallback: ((payload: unknown) => void) | null = null;
            
            const channelInstance = {
                on: vi.fn((event, config, callback) => {
                    capturedCallback = callback;
                    return {
                        subscribe: vi.fn().mockReturnValue(channelInstance),
                    };
                }),
                unsubscribe: vi.fn(),
            };
            mockChannel.mockReturnValue(channelInstance);

            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            // Simulate a failed job with no error message
            act(() => {
                if (capturedCallback) {
                    capturedCallback({
                        new: {
                            status: 'failed',
                            provider: 'google_drive',
                        },
                    });
                }
            });

            expect(result.current.isProviderQuotaExceeded('google_drive')).toBe(false);
        });
    });

    describe('Return Values', () => {
        it('should return all expected properties', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current).toHaveProperty('quotaExceededProviders');
            expect(result.current).toHaveProperty('hasQuotaIssue');
            expect(result.current).toHaveProperty('isProviderQuotaExceeded');
            expect(result.current).toHaveProperty('clearQuotaStatus');
            expect(result.current).toHaveProperty('markQuotaExceeded');
        });

        it('should have hasQuotaIssue reflect provider count', () => {
            const { result } = renderHook(() => useQuotaStatus(), {
                wrapper: createWrapper(),
            });

            expect(result.current.hasQuotaIssue).toBe(false);

            act(() => {
                result.current.markQuotaExceeded('google_drive');
            });

            expect(result.current.hasQuotaIssue).toBe(true);

            act(() => {
                result.current.clearQuotaStatus('google_drive');
            });

            expect(result.current.hasQuotaIssue).toBe(false);
        });
    });

    describe('No-op Implementation Outside Provider', () => {
        it('should return false for isProviderQuotaExceeded without provider', () => {
            const { result } = renderHook(() => useQuotaStatus());

            expect(result.current.isProviderQuotaExceeded('anything')).toBe(false);
        });

        it('should have no-op functions that do not throw', () => {
            const { result } = renderHook(() => useQuotaStatus());

            // These should not throw
            expect(() => {
                result.current.clearQuotaStatus();
                result.current.clearQuotaStatus('google_drive');
                result.current.markQuotaExceeded('google_drive');
            }).not.toThrow();
        });
    });
});
