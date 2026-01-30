"use client";

/**
 * useRealtimeStatus Hook
 * 
 * Monitors Supabase Realtime connection status with:
 * - Automatic reconnection with exponential backoff
 * - Connection state tracking (connected, connecting, disconnected, error)
 * - Last connected timestamp
 * - Manual reconnect capability
 * 
 * @example
 * ```tsx
 * const { status, isConnected, lastConnected, reconnect } = useRealtimeStatus();
 * 
 * if (!isConnected) {
 *     showReconnectBanner();
 * }
 * ```
 */

import { useCallback, useEffect, useState, useRef } from "react";
import type { RealtimeChannel } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";

// =============================================================================
// Types
// =============================================================================

/**
 * Possible connection states for realtime.
 */
type ConnectionStatus = "connected" | "connecting" | "disconnected" | "error";

/**
 * Return type for the useRealtimeStatus hook.
 */
interface RealtimeStatusReturn {
    /** Current connection status */
    status: ConnectionStatus;
    /** Timestamp of last successful connection */
    lastConnected: Date | null;
    /** Whether currently connected */
    isConnected: boolean;
    /** Number of reconnection attempts made */
    reconnectAttempts: number;
    /** Manually trigger a reconnection */
    reconnect: () => void;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Base delay for exponential backoff (in milliseconds).
 * First retry: 500ms, second: 1000ms, third: 2000ms, etc.
 */
const BASE_DELAY_MS = 500;

/**
 * Maximum delay between reconnection attempts (30 seconds).
 * Prevents extremely long wait times.
 */
const MAX_DELAY_MS = 30_000;

/**
 * Maximum number of automatic reconnection attempts.
 * After this, manual reconnection is required.
 */
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Delay before resetting reconnect attempts after successful connection (5 seconds).
 * This ensures the connection is stable before resetting.
 */
const RECONNECT_RESET_DELAY_MS = 5_000;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Calculate delay for exponential backoff.
 * 
 * @param attempt - Current attempt number (0-indexed)
 * @returns Delay in milliseconds, capped at MAX_DELAY_MS
 */
function calculateBackoffDelay(attempt: number): number {
    const delay = BASE_DELAY_MS * Math.pow(2, attempt);
    return Math.min(delay, MAX_DELAY_MS);
}

/**
 * Map Supabase channel status to our ConnectionStatus type.
 * 
 * @param state - Supabase channel state string
 * @returns Mapped ConnectionStatus
 */
function mapChannelState(state: string): ConnectionStatus {
    switch (state) {
        case "SUBSCRIBED":
            return "connected";
        case "TIMED_OUT":
        case "CHANNEL_ERROR":
            return "error";
        case "CLOSED":
            return "disconnected";
        default:
            return "connecting";
    }
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for monitoring Supabase Realtime connection status.
 * 
 * Features:
 * - Automatic reconnection with exponential backoff
 * - Capped retry attempts to prevent infinite loops
 * - Manual reconnect capability
 * - Proper cleanup on unmount
 */
export function useRealtimeStatus(): RealtimeStatusReturn {
    // Connection state
    const [status, setStatus] = useState<ConnectionStatus>("connecting");
    const [lastConnected, setLastConnected] = useState<Date | null>(null);
    const [reconnectAttempts, setReconnectAttempts] = useState(0);
    
    // Force re-subscribe by changing this token
    const [reconnectToken, setReconnectToken] = useState(0);
    
    // Refs for cleanup
    const channelRef = useRef<RealtimeChannel | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const resetAttemptsTimeoutRef = useRef<NodeJS.Timeout | null>(null);
    const mountedRef = useRef(true);

    /**
     * Clean up any pending timeouts.
     */
    const clearTimeouts = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }
        if (resetAttemptsTimeoutRef.current) {
            clearTimeout(resetAttemptsTimeoutRef.current);
            resetAttemptsTimeoutRef.current = null;
        }
    }, []);

    /**
     * Handle successful connection.
     */
    const handleConnected = useCallback(() => {
        if (!mountedRef.current) return;
        
        setStatus("connected");
        setLastConnected(new Date());
        
        // Reset reconnect attempts after connection is stable
        clearTimeouts();
        resetAttemptsTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
                setReconnectAttempts(0);
            }
        }, RECONNECT_RESET_DELAY_MS);
    }, [clearTimeouts]);

    /**
     * Handle connection error with automatic retry.
     */
    const handleError = useCallback((currentAttempts: number) => {
        if (!mountedRef.current) return;
        
        setStatus("error");
        
        // Check if we should attempt automatic reconnection
        if (currentAttempts < MAX_RECONNECT_ATTEMPTS) {
            const delay = calculateBackoffDelay(currentAttempts);
            
            if (process.env.NODE_ENV === 'development') {
                console.log(
                    `🔌 [Realtime] Connection failed. Retrying in ${delay}ms ` +
                    `(attempt ${currentAttempts + 1}/${MAX_RECONNECT_ATTEMPTS})`
                );
            }
            
            clearTimeouts();
            reconnectTimeoutRef.current = setTimeout(() => {
                if (mountedRef.current) {
                    setReconnectAttempts(prev => prev + 1);
                    setReconnectToken(prev => prev + 1);
                }
            }, delay);
        } else {
            if (process.env.NODE_ENV === 'development') {
                console.log(
                    `🔌 [Realtime] Max reconnection attempts (${MAX_RECONNECT_ATTEMPTS}) reached. ` +
                    `Manual reconnection required.`
                );
            }
        }
    }, [clearTimeouts]);

    /**
     * Manual reconnect function.
     * Resets attempt counter and forces a new connection.
     */
    const reconnect = useCallback(() => {
        if (process.env.NODE_ENV === 'development') {
            console.log("🔌 [Realtime] Manual reconnection triggered");
        }
        
        clearTimeouts();
        setStatus("connecting");
        setReconnectAttempts(0);
        
        // Force reconnect by disconnecting and reconnecting
        supabase.realtime.disconnect();
        
        // Small delay before reconnecting to ensure clean state
        setTimeout(() => {
            if (mountedRef.current) {
                supabase.realtime.connect();
                setReconnectToken(prev => prev + 1);
            }
        }, 100);
    }, [clearTimeouts]);

    // ==========================================================================
    // Effect: Subscribe to realtime status channel
    // ==========================================================================
    
    useEffect(() => {
        mountedRef.current = true;
        setStatus("connecting");

        // Create a status monitoring channel
        const channel = supabase.channel(`realtime-status-${reconnectToken}`);
        channelRef.current = channel;

        channel.subscribe((state: string) => {
            if (!mountedRef.current) return;
            
            const mappedStatus = mapChannelState(state);
            
            if (mappedStatus === "connected") {
                handleConnected();
            } else if (mappedStatus === "error") {
                handleError(reconnectAttempts);
            } else {
                setStatus(mappedStatus);
            }
        });

        // Cleanup on unmount or reconnect
        return () => {
            mountedRef.current = false;
            clearTimeouts();
            
            if (channelRef.current) {
                channelRef.current.unsubscribe();
                supabase.removeChannel(channelRef.current);
                channelRef.current = null;
            }
        };
    }, [reconnectToken, reconnectAttempts, handleConnected, handleError, clearTimeouts]);

    return {
        status,
        lastConnected,
        isConnected: status === "connected",
        reconnectAttempts,
        reconnect,
    };
}
