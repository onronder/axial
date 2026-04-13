"use client";

/**
 * IngestionProgressContext - Single Source of Truth
 * 
 * This context provides a centralized way to track and display ingestion progress.
 * All ingestion-triggering components should register their jobs here instead of
 * rendering their own progress modals.
 * 
 * USAGE:
 * 1. Wrap your app in <IngestionProgressProvider>
 * 2. Use registerJob(jobId) when starting an ingestion
 * 3. GlobalProgress component handles all UI rendering
 */

import {
    createContext,
    useContext,
    useState,
    useCallback,
    useMemo,
    ReactNode,
} from "react";

// =============================================================================
// Types
// =============================================================================

interface IngestionProgressContextValue {
    /** Set of all active job IDs being tracked */
    activeJobIds: Set<string>;
    
    /** Currently expanded job ID (shown in modal) */
    expandedJobId: string | null;
    
    /** Register a new job to track (call when ingestion starts) */
    registerJob: (jobId: string) => void;
    
    /** Unregister a job (call when job completes or is dismissed) */
    unregisterJob: (jobId: string) => void;
    
    /** Expand a job to show detailed modal */
    expandJob: (jobId: string | null) => void;
    
    /** Check if a job is currently registered */
    isJobRegistered: (jobId: string) => boolean;
    
    /** Mark a job as having triggered its completion callback (prevents duplicate triggers) */
    markJobCompleted: (jobId: string) => void;
    
    /** Check if a job has already triggered its completion callback */
    hasJobCompleted: (jobId: string) => boolean;
}

// =============================================================================
// Context
// =============================================================================

const IngestionProgressContext = createContext<IngestionProgressContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface IngestionProgressProviderProps {
    children: ReactNode;
}

export function IngestionProgressProvider({ children }: IngestionProgressProviderProps) {
    const [activeJobIds, setActiveJobIds] = useState<Set<string>>(new Set());
    const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
    
    // Track jobs that have already triggered their completion callback
    // This prevents infinite refresh loops when components remount
    const [completedJobIds, setCompletedJobIds] = useState<Set<string>>(new Set());
    
    /**
     * Register a new job to be tracked.
     * Called by ingestion components when they start a new job.
     */
    const registerJob = useCallback((jobId: string) => {
        if (!jobId) return;
        
        if (process.env.NODE_ENV === 'development') {
            console.log(`📊 [IngestionProgress] Registering job: ${jobId.slice(0, 8)}...`);
        }
        
        setActiveJobIds(prev => {
            if (prev.has(jobId)) return prev;
            const next = new Set(prev);
            next.add(jobId);
            return next;
        });
    }, []);

    /**
     * Unregister a job (when completed/failed/dismissed).
     * Usually called automatically by GlobalProgress when job reaches terminal state.
     */
    const unregisterJob = useCallback((jobId: string) => {
        if (!jobId) return;
        
        if (process.env.NODE_ENV === 'development') {
            console.log(`📊 [IngestionProgress] Unregistering job: ${jobId.slice(0, 8)}...`);
        }
        
        setActiveJobIds(prev => {
            if (!prev.has(jobId)) return prev;
            const next = new Set(prev);
            next.delete(jobId);
            return next;
        });
        
        // Clear expanded if this job was expanded
        setExpandedJobId(prev => prev === jobId ? null : prev);
        
        // Clean up completion tracking for this job
        setCompletedJobIds(prev => {
            if (!prev.has(jobId)) return prev;
            const next = new Set(prev);
            next.delete(jobId);
            return next;
        });
    }, []);
    
    /**
     * Mark a job as having triggered its completion callback.
     * This prevents infinite refresh loops when components remount.
     */
    const markJobCompleted = useCallback((jobId: string) => {
        if (!jobId) return;
        
        setCompletedJobIds(prev => {
            if (prev.has(jobId)) return prev;
            const next = new Set(prev);
            next.add(jobId);
            return next;
        });
    }, []);
    
    /**
     * Check if a job has already triggered its completion callback.
     */
    const hasJobCompleted = useCallback((jobId: string): boolean => {
        return completedJobIds.has(jobId);
    }, [completedJobIds]);

    /**
     * Expand a job to show the detailed progress modal.
     * Pass null to collapse.
     */
    const expandJob = useCallback((jobId: string | null) => {
        setExpandedJobId(jobId);
    }, []);

    /**
     * Check if a job is currently registered.
     */
    const isJobRegistered = useCallback((jobId: string): boolean => {
        return activeJobIds.has(jobId);
    }, [activeJobIds]);

    const value = useMemo<IngestionProgressContextValue>(
        () => ({
            activeJobIds,
            expandedJobId,
            registerJob,
            unregisterJob,
            expandJob,
            isJobRegistered,
            markJobCompleted,
            hasJobCompleted,
        }),
        [
            activeJobIds,
            expandedJobId,
            expandJob,
            hasJobCompleted,
            isJobRegistered,
            markJobCompleted,
            registerJob,
            unregisterJob,
        ]
    );

    return (
        <IngestionProgressContext.Provider value={value}>
            {children}
        </IngestionProgressContext.Provider>
    );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access the ingestion progress context.
 * 
 * @example
 * ```tsx
 * const { registerJob } = useIngestionProgress();
 * 
 * const handleUpload = async () => {
 *     const jobId = await startIngestion(files);
 *     registerJob(jobId); // Register job - GlobalProgress handles the UI
 * };
 * ```
 */
export function useIngestionProgress(): IngestionProgressContextValue {
    const context = useContext(IngestionProgressContext);
    
    if (!context) {
        throw new Error(
            "useIngestionProgress must be used within an IngestionProgressProvider. " +
            "Make sure to wrap your dashboard layout with <IngestionProgressProvider>."
        );
    }
    
    return context;
}

// =============================================================================
// Export types for consumers
// =============================================================================

export type { IngestionProgressContextValue };
