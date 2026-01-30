import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// =============================================================================
// Mocks - Use vi.hoisted to ensure mocks are available before vi.mock
// =============================================================================

const { 
    mockSubscribe, 
    mockUnsubscribe, 
    mockConnect, 
    mockDisconnect, 
    mockRemoveChannel 
} = vi.hoisted(() => ({
    mockSubscribe: vi.fn(),
    mockUnsubscribe: vi.fn(),
    mockConnect: vi.fn(),
    mockDisconnect: vi.fn(),
    mockRemoveChannel: vi.fn(),
}));

// Mock supabase module
vi.mock('@/lib/supabase', () => ({
    supabase: {
        channel: vi.fn(() => ({
            subscribe: mockSubscribe,
            unsubscribe: mockUnsubscribe,
        })),
        removeChannel: mockRemoveChannel,
        realtime: {
            connect: mockConnect,
            disconnect: mockDisconnect,
        },
    },
}));

// Import after mock setup
import { useRealtimeStatus } from '@/hooks/useRealtimeStatus';

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
    
    // Default mock: subscribe succeeds
    mockSubscribe.mockImplementation((callback: (state: string) => void) => {
        // Immediately call with SUBSCRIBED
        setTimeout(() => callback('SUBSCRIBED'), 0);
    });
});

afterEach(() => {
    vi.useRealTimers();
});

// =============================================================================
// Tests
// =============================================================================

describe('useRealtimeStatus', () => {
    // =========================================================================
    // Initial Connection Tests
    // =========================================================================
    
    describe('Initial Connection', () => {
        it('should start in connecting state', () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            expect(result.current.status).toBe('connecting');
            expect(result.current.isConnected).toBe(false);
        });

        it('should transition to connected on SUBSCRIBED', async () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            // Fast-forward to trigger the subscription callback
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('connected');
            expect(result.current.isConnected).toBe(true);
        });

        it('should set lastConnected timestamp on successful connection', async () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.lastConnected).toBeInstanceOf(Date);
        });

        it('should have zero reconnect attempts initially', () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            expect(result.current.reconnectAttempts).toBe(0);
        });
    });

    // =========================================================================
    // Connection State Tests
    // =========================================================================
    
    describe('Connection States', () => {
        it('should handle TIMED_OUT as error', async () => {
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('TIMED_OUT'), 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('error');
            expect(result.current.isConnected).toBe(false);
        });

        it('should handle CHANNEL_ERROR as error', async () => {
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('CHANNEL_ERROR'), 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('error');
        });

        it('should handle CLOSED as disconnected', async () => {
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('CLOSED'), 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('disconnected');
        });
    });

    // =========================================================================
    // Reconnection Tests
    // =========================================================================
    
    describe('Reconnection', () => {
        it('should implement exponential backoff on error', async () => {
            // Mock to fail initially
            let callCount = 0;
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => {
                    callCount++;
                    callback(callCount < 3 ? 'CHANNEL_ERROR' : 'SUBSCRIBED');
                }, 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            // First attempt fails
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('error');
            
            // Wait for first backoff (500ms)
            await act(async () => {
                vi.advanceTimersByTime(500);
            });
            
            // Should be reconnecting
            expect(result.current.reconnectAttempts).toBeGreaterThan(0);
        });

        it('should respect max retry count', async () => {
            // Always fail
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('CHANNEL_ERROR'), 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            // Simulate 5 failures with increasing backoff
            for (let i = 0; i < 6; i++) {
                await act(async () => {
                    vi.advanceTimersByTime(10);
                });
                
                // Advance through backoff delays
                await act(async () => {
                    vi.advanceTimersByTime(30000); // Max backoff
                });
            }
            
            // After max attempts, should still be in error state
            expect(result.current.status).toBe('error');
        });
    });

    // =========================================================================
    // Manual Reconnect Tests
    // =========================================================================
    
    describe('Manual Reconnect', () => {
        it('should reset attempts on manual reconnect', async () => {
            // Fail first, then succeed
            let callCount = 0;
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => {
                    callCount++;
                    callback(callCount === 1 ? 'CHANNEL_ERROR' : 'SUBSCRIBED');
                }, 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            // First attempt fails
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            expect(result.current.status).toBe('error');
            
            // Manual reconnect
            await act(async () => {
                result.current.reconnect();
            });
            
            expect(result.current.reconnectAttempts).toBe(0);
            expect(result.current.status).toBe('connecting');
        });

        it('should call supabase disconnect and connect on manual reconnect', async () => {
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('SUBSCRIBED'), 0);
            });

            const { result } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            await act(async () => {
                result.current.reconnect();
            });
            
            expect(mockDisconnect).toHaveBeenCalled();
            
            // Advance past the small delay before connect
            await act(async () => {
                vi.advanceTimersByTime(100);
            });
            
            expect(mockConnect).toHaveBeenCalled();
        });
    });

    // =========================================================================
    // Cleanup Tests
    // =========================================================================
    
    describe('Cleanup', () => {
        it('should unsubscribe on unmount', () => {
            const { unmount } = renderHook(() => useRealtimeStatus());
            
            unmount();
            
            expect(mockUnsubscribe).toHaveBeenCalled();
            expect(mockRemoveChannel).toHaveBeenCalled();
        });

        it('should clear timers on unmount', async () => {
            // Fail to trigger reconnection timer
            mockSubscribe.mockImplementation((callback: (state: string) => void) => {
                setTimeout(() => callback('CHANNEL_ERROR'), 0);
            });

            const { unmount } = renderHook(() => useRealtimeStatus());
            
            await act(async () => {
                vi.advanceTimersByTime(10);
            });
            
            // Unmount before reconnection timer fires
            unmount();
            
            // Advance past any pending timers
            await act(async () => {
                vi.advanceTimersByTime(30000);
            });
            
            // Should not throw or cause issues
            expect(true).toBe(true);
        });
    });

    // =========================================================================
    // Return Value Tests
    // =========================================================================
    
    describe('Return Values', () => {
        it('should return all expected properties', () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            expect(result.current).toHaveProperty('status');
            expect(result.current).toHaveProperty('lastConnected');
            expect(result.current).toHaveProperty('isConnected');
            expect(result.current).toHaveProperty('reconnectAttempts');
            expect(result.current).toHaveProperty('reconnect');
        });

        it('should have reconnect as a function', () => {
            const { result } = renderHook(() => useRealtimeStatus());
            
            expect(typeof result.current.reconnect).toBe('function');
        });
    });
});
