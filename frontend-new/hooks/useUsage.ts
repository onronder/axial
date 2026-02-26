'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef, useMemo, ReactNode } from 'react';
import { getUsageStats, getEffectivePlan } from '@/lib/api';
import type { UserUsage, EffectivePlan, PlanType } from '@/types';
import { AxiosError } from 'axios';
import { extractErrorMessage } from '@/lib/error-handling';

/**
 * Usage Context - Singleton pattern for usage data
 * 
 * This prevents duplicate API calls when multiple components use useUsage().
 * Data is fetched once and shared across all consumers.
 * 
 * Plan Flow:
 * - 'none': New user who hasn't selected a plan (shows paywall)
 * - 'free': User after trial/cancellation (shows paywall)
 * - 'starter', 'pro', 'enterprise': Paid plans with full access
 */

interface UsageContextValue {
    usage: UserUsage | null;
    effectivePlan: EffectivePlan | null;
    isLoading: boolean;
    error: string | null;
    plan: PlanType | null;
    isPlanInherited: boolean;
    filesUsed: number;
    filesLimit: number;
    filesPercent: number;
    storageUsed: number;
    storageLimit: number;
    storagePercent: number;
    canWebCrawl: boolean;
    premiumModels: boolean;
    teamEnabled: boolean;
    modelTier: string | null;
    refresh: (force?: boolean) => Promise<void>;
    refreshPlan: (force?: boolean) => Promise<void>;
}

const UsageContext = createContext<UsageContextValue | undefined>(undefined);

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

interface UsageProviderProps {
    children: ReactNode;
}

/**
 * Extract plan from 402 error response
 * Backend returns: { error: "SUBSCRIPTION_REQUIRED", current_plan: "none"|"free", message: "..." }
 */
function extractPlanFrom402Error(error: unknown): PlanType | null {
    if (error instanceof AxiosError && error.response?.status === 402) {
        const detail = error.response.data?.detail;
        if (detail?.current_plan) {
            return detail.current_plan as PlanType;
        }
    }
    return null;
}

export function UsageProvider({ children }: UsageProviderProps) {
    const [usage, setUsage] = useState<UserUsage | null>(null);
    const [effectivePlan, setEffectivePlan] = useState<EffectivePlan | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const hasFetched = useRef(false);
    const lastFetchTime = useRef<number>(0);
    const fetchInProgress = useRef(false);
    const abortControllerRef = useRef<AbortController | null>(null);

    const fetchAll = useCallback(async (force: boolean = false) => {
        if (fetchInProgress.current) return;

        const now = Date.now();
        if (!force && lastFetchTime.current && (now - lastFetchTime.current) < CACHE_DURATION) {
            return;
        }

        // Abort any in-flight request
        abortControllerRef.current?.abort();
        const controller = new AbortController();
        abortControllerRef.current = controller;

        fetchInProgress.current = true;
        setIsLoading(true);
        setError(null);

        try {
            // Fire both requests in parallel — they are independent endpoints
            const [planResult, usageResult] = await Promise.allSettled([
                getEffectivePlan(),
                getUsageStats(),
            ]);

            if (controller.signal.aborted) return;

            // Handle plan result
            if (planResult.status === 'fulfilled') {
                if (planResult.value) setEffectivePlan(planResult.value);
            } else {
                // If even effective-plan fails, extract plan from 402 error if available
                const planFromError = extractPlanFrom402Error(planResult.reason);
                if (planFromError) {
                    setEffectivePlan({ plan: planFromError, inherited: false, team_id: null, team_name: null });
                } else {
                    throw planResult.reason;
                }
            }

            // Handle usage result
            if (usageResult.status === 'fulfilled') {
                if (usageResult.value) setUsage(usageResult.value);
            } else {
                // 402 is expected for free/none users — don't treat as error
                if (usageResult.reason instanceof AxiosError && usageResult.reason.response?.status === 402) {
                    if (process.env.NODE_ENV !== 'production') {
                        console.log('[useUsage] Usage endpoint returned 402 (expected for free/none plan)');
                    }
                } else {
                    throw usageResult.reason;
                }
            }

        } catch (err: unknown) {
            if (!controller.signal.aborted) {
                setError(extractErrorMessage(err, 'Failed to fetch usage'));
            }
        } finally {
            if (!controller.signal.aborted) {
                setIsLoading(false);
                lastFetchTime.current = Date.now();
            }
            fetchInProgress.current = false;
        }
    }, []);

    useEffect(() => {
        if (hasFetched.current) return;
        hasFetched.current = true;
        fetchAll();
        return () => {
            abortControllerRef.current?.abort();
        };
    }, [fetchAll]);

    const refresh = useCallback((force: boolean = true) => fetchAll(force), [fetchAll]);

    const value = useMemo<UsageContextValue>(() => {
        const plan: PlanType | null = isLoading ? null : (effectivePlan?.plan ?? usage?.plan ?? 'free');
        const isPlanInherited = effectivePlan?.inherited ?? false;
        const filesUsed = usage?.files.used ?? 0;
        const filesLimit = usage?.files.limit ?? 10;
        const storageUsed = usage?.storage.used_bytes ?? 0;
        const storageLimit = usage?.storage.limit_bytes ?? 100 * 1024 * 1024;
        // Backend uses `features.team`; keep `team_enabled` for legacy compatibility
        const canWebCrawl = usage?.features.web_crawl ?? false;
        const teamEnabled = usage?.features.team ?? usage?.features.team_enabled ?? false;
        const premiumModels = usage?.features.premium_models ?? false;
        const modelTier = usage?.model_tier ?? null;
        const filesPercent = filesLimit > 0 ? (filesUsed / filesLimit) * 100 : 0;
        const storagePercent = storageLimit > 0 ? (storageUsed / storageLimit) * 100 : 0;

        return {
            usage,
            effectivePlan,
            isLoading,
            error,
            plan,
            isPlanInherited,
            filesUsed,
            filesLimit,
            filesPercent,
            storageUsed,
            storageLimit,
            storagePercent,
            canWebCrawl,
            teamEnabled,
            premiumModels,
            modelTier,
            refresh,
            refreshPlan: refresh,
        };
    }, [usage, effectivePlan, isLoading, error, refresh]);

    return React.createElement(UsageContext.Provider, { value }, children);
}

export const useUsage = (): UsageContextValue => {
    const context = useContext(UsageContext);
    if (context === undefined) {
        throw new Error('useUsage must be used within a UsageProvider');
    }
    return context;
};

export const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`;
};
