"use client";

/**
 * useQuotaStatus Hook
 * 
 * Tracks which data sources have encountered quota/limit issues.
 * Stores the provider type when a job fails due to quota exceeded.
 * This allows showing warning indicators on specific data source cards.
 * 
 * Features:
 * - SSR-safe localStorage access
 * - Realtime subscription to ingestion job updates
 * - 24-hour TTL on quota exceeded status
 * - Automatic cleanup on unmount
 * 
 * @example
 * ```tsx
 * const { isProviderQuotaExceeded, clearQuotaStatus } = useQuotaStatus();
 * 
 * // Check if a provider has quota issues
 * if (isProviderQuotaExceeded('google_drive')) {
 *     showUpgradePrompt();
 * }
 * 
 * // Clear after upgrade
 * clearQuotaStatus('google_drive');
 * ```
 */

import { useEffect, useState, useCallback, createContext, useContext, ReactNode, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { normalizeSourceType } from "@/lib/sourceType";
import { safeLocalStorage } from "@/lib/storage";

// =============================================================================
// Constants
// =============================================================================

/**
 * Keywords that indicate a quota/limit error in job messages.
 */
const QUOTA_ERROR_KEYWORDS = [
    "quota",
    "limit",
    "exceeded",
    "file limit",
    "storage limit",
    "upgrade",
    "plan",
] as const;

/**
 * Local storage key for persisting quota status across sessions.
 */
const STORAGE_KEY = "axio_quota_exceeded_providers";

/**
 * How long to persist quota exceeded status (24 hours in milliseconds).
 * After this time, the status is considered stale and cleared.
 */
const QUOTA_STATUS_TTL = 24 * 60 * 60 * 1000;

// =============================================================================
// Types
// =============================================================================

interface QuotaStatus {
    /** Set of provider types that have hit quota limits */
    quotaExceededProviders: Set<string>;
    /** Whether any provider has quota issues */
    hasQuotaIssue: boolean;
    /** Check if a specific provider has quota issues */
    isProviderQuotaExceeded: (provider: string) => boolean;
    /** Clear quota status for a provider (e.g., after upgrade) */
    clearQuotaStatus: (provider?: string) => void;
    /** Manually mark a provider as quota exceeded */
    markQuotaExceeded: (provider: string) => void;
}

interface StoredQuotaData {
    providers: string[];
    timestamp: number;
}

// =============================================================================
// Context
// =============================================================================

const QuotaStatusContext = createContext<QuotaStatus | null>(null);

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if an error message indicates quota exceeded.
 * 
 * @param message - The error or status message to check
 * @returns true if the message contains quota-related keywords
 */
function isQuotaError(message: string | undefined | null): boolean {
    if (!message) return false;
    const lowerMessage = message.toLowerCase();
    return QUOTA_ERROR_KEYWORDS.some(keyword => lowerMessage.includes(keyword));
}

/**
 * Load quota status from localStorage.
 * Returns an empty set if no valid data exists or if data is expired.
 */
function loadStoredQuotaStatus(): Set<string> {
    const stored = safeLocalStorage.getItem(STORAGE_KEY);
    if (!stored) {
        return new Set();
    }

    try {
        const data: StoredQuotaData = JSON.parse(stored);
        
        // Check if data is still valid (within TTL)
        if (Date.now() - data.timestamp < QUOTA_STATUS_TTL) {
            return new Set(data.providers);
        }
        
        // Data is expired, remove it
        safeLocalStorage.removeItem(STORAGE_KEY);
        return new Set();
    } catch {
        // Invalid data, remove it
        safeLocalStorage.removeItem(STORAGE_KEY);
        return new Set();
    }
}

/**
 * Save quota status to localStorage.
 * 
 * @param providers - Set of provider names with quota issues
 */
function saveQuotaStatus(providers: Set<string>): void {
    if (providers.size === 0) {
        safeLocalStorage.removeItem(STORAGE_KEY);
        return;
    }

    const data: StoredQuotaData = {
        providers: Array.from(providers),
        timestamp: Date.now(),
    };
    safeLocalStorage.setJson(STORAGE_KEY, data);
}

// =============================================================================
// Provider Component
// =============================================================================

interface QuotaStatusProviderProps {
    children: ReactNode;
}

/**
 * Provider component for quota status context.
 * Wrap your app with this to enable quota tracking.
 */
export function QuotaStatusProvider({ children }: QuotaStatusProviderProps) {
    const { user } = useAuth();
    const [quotaExceededProviders, setQuotaExceededProviders] = useState<Set<string>>(new Set());
    const initializedRef = useRef(false);

    // Load persisted quota status on mount (client-side only)
    useEffect(() => {
        if (initializedRef.current) return;
        initializedRef.current = true;

        const stored = loadStoredQuotaStatus();
        if (stored.size > 0) {
            setQuotaExceededProviders(stored);
        }
    }, []);

    // Persist quota status changes to localStorage
    useEffect(() => {
        // Skip persistence until initial load is complete
        if (!initializedRef.current) return;
        
        saveQuotaStatus(quotaExceededProviders);
    }, [quotaExceededProviders]);

    // Subscribe to ingestion job updates to detect quota issues
    useEffect(() => {
        if (!user?.id) return;

        const channel = supabase
            .channel(`quota_status_${user.id}`)
            .on(
                "postgres_changes",
                {
                    event: "UPDATE",
                    schema: "public",
                    table: "ingestion_jobs",
                    filter: `user_id=eq.${user.id}`,
                },
                (payload) => {
                    const newJob = payload.new as {
                        status: string;
                        provider: string;
                        error_message?: string;
                        message?: string;
                    };

                    // Check for failed jobs with quota-related errors
                    if (newJob.status === "failed") {
                        const errorMsg = newJob.error_message || newJob.message;
                        if (isQuotaError(errorMsg)) {
                            const normalizedProvider = normalizeSourceType(newJob.provider) || newJob.provider;
                            if (process.env.NODE_ENV === 'development') {
                                console.log(`📊 [QuotaStatus] Detected quota exceeded for: ${normalizedProvider}`);
                            }
                            setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
                        }
                    }

                    // Also check completed jobs that mention limit in their message
                    if (newJob.status === "completed" && newJob.message) {
                        if (isQuotaError(newJob.message)) {
                            const normalizedProvider = normalizeSourceType(newJob.provider) || newJob.provider;
                            if (process.env.NODE_ENV === 'development') {
                                console.log(`📊 [QuotaStatus] Detected quota warning for: ${normalizedProvider}`);
                            }
                            setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
                        }
                    }
                }
            )
            .subscribe();

        return () => {
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [user?.id]);

    // ==========================================================================
    // Context Methods
    // ==========================================================================

    /**
     * Check if a specific provider has quota issues.
     */
    const isProviderQuotaExceeded = useCallback((provider: string): boolean => {
        const normalizedProvider = normalizeSourceType(provider) || provider;
        return quotaExceededProviders.has(normalizedProvider);
    }, [quotaExceededProviders]);

    /**
     * Clear quota status for a specific provider or all providers.
     * Call this after a user upgrades their plan.
     */
    const clearQuotaStatus = useCallback((provider?: string) => {
        if (provider) {
            const normalizedProvider = normalizeSourceType(provider) || provider;
            setQuotaExceededProviders(prev => {
                const next = new Set(prev);
                next.delete(normalizedProvider);
                return next;
            });
        } else {
            setQuotaExceededProviders(new Set());
        }
    }, []);

    /**
     * Manually mark a provider as having quota issues.
     * Use this when detecting quota errors outside of realtime subscriptions.
     */
    const markQuotaExceeded = useCallback((provider: string) => {
        const normalizedProvider = normalizeSourceType(provider) || provider;
        setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
    }, []);

    // ==========================================================================
    // Render
    // ==========================================================================

    const value: QuotaStatus = {
        quotaExceededProviders,
        hasQuotaIssue: quotaExceededProviders.size > 0,
        isProviderQuotaExceeded,
        clearQuotaStatus,
        markQuotaExceeded,
    };

    return (
        <QuotaStatusContext.Provider value={value}>
            {children}
        </QuotaStatusContext.Provider>
    );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access quota status context.
 * 
 * Returns a no-op implementation if used outside the provider,
 * preventing crashes in isolated components or tests.
 */
export function useQuotaStatus(): QuotaStatus {
    const context = useContext(QuotaStatusContext);
    
    if (!context) {
        // Return a no-op implementation if used outside provider
        // This prevents crashes and allows gradual adoption
        return {
            quotaExceededProviders: new Set(),
            hasQuotaIssue: false,
            isProviderQuotaExceeded: () => false,
            clearQuotaStatus: () => {},
            markQuotaExceeded: () => {},
        };
    }
    
    return context;
}
