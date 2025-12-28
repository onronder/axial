'use client';

import { useState, useEffect, useCallback } from 'react';
import { getUsageStats, getEffectivePlan } from '@/lib/api';
import type { UserUsage, EffectivePlan, PlanType } from '@/types';

/**
 * Hook for managing user usage stats and plan information.
 * 
 * Provides access to:
 * - Current plan (inherited from team owner if applicable)
 * - File and storage usage
 * - Feature flags (web_crawl, team_enabled)
 */
export const useUsage = () => {
    const [usage, setUsage] = useState<UserUsage | null>(null);
    const [effectivePlan, setEffectivePlan] = useState<EffectivePlan | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchUsage = useCallback(async () => {
        setIsLoading(true);
        setError(null);
        try {
            const data = await getUsageStats();
            setUsage(data);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Failed to fetch usage';
            console.error('Failed to fetch usage:', err);
            setError(message);
        } finally {
            setIsLoading(false);
        }
    }, []);

    const fetchEffectivePlan = useCallback(async () => {
        try {
            const data = await getEffectivePlan();
            setEffectivePlan(data);
        } catch (err) {
            console.error('Failed to fetch effective plan:', err);
        }
    }, []);

    useEffect(() => {
        fetchUsage();
        fetchEffectivePlan();
    }, [fetchUsage, fetchEffectivePlan]);

    // Derived values for convenience
    const plan: PlanType = effectivePlan?.plan ?? usage?.plan ?? 'free';
    const isPlanInherited = effectivePlan?.inherited ?? false;

    const filesUsed = usage?.files.used ?? 0;
    const filesLimit = usage?.files.limit ?? 10;
    const storageUsed = usage?.storage.used_bytes ?? 0;
    const storageLimit = usage?.storage.limit_bytes ?? 100 * 1024 * 1024; // 100MB default

    const canWebCrawl = usage?.features.web_crawl ?? false;
    const teamEnabled = usage?.features.team_enabled ?? false;

    // Calculate percentages
    const filesPercent = filesLimit > 0 ? (filesUsed / filesLimit) * 100 : 0;
    const storagePercent = storageLimit > 0 ? (storageUsed / storageLimit) * 100 : 0;

    return {
        // Raw data
        usage,
        effectivePlan,
        isLoading,
        error,

        // Derived convenience values
        plan,
        isPlanInherited,

        // Files
        filesUsed,
        filesLimit,
        filesPercent,

        // Storage
        storageUsed,
        storageLimit,
        storagePercent,

        // Features
        canWebCrawl,
        teamEnabled,

        // Actions
        refresh: fetchUsage,
        refreshPlan: fetchEffectivePlan,
    };
};

/**
 * Format bytes to human-readable string
 */
export const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 B';

    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const k = 1024;
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${units[i]}`;
};
