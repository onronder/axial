"use client";

/**
 * useQuotaStatus Hook
 * 
 * Tracks which data sources have encountered quota/limit issues.
 * Stores the provider type when a job fails due to quota exceeded.
 * This allows showing warning indicators on specific data source cards.
 */

import { useEffect, useState, useCallback, createContext, useContext, ReactNode, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { normalizeSourceType } from "@/lib/sourceType";

// Keywords that indicate a quota/limit error
const QUOTA_ERROR_KEYWORDS = [
  "quota",
  "limit",
  "exceeded",
  "file limit",
  "storage limit",
  "upgrade",
  "plan",
];

interface QuotaStatus {
  /** Provider types that have hit quota limits */
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

const QuotaStatusContext = createContext<QuotaStatus | null>(null);

// Local storage key for persisting quota status
const STORAGE_KEY = "axio_quota_exceeded_providers";

// How long to persist quota exceeded status (24 hours)
const QUOTA_STATUS_TTL = 24 * 60 * 60 * 1000;

interface StoredQuotaData {
  providers: string[];
  timestamp: number;
}

export function QuotaStatusProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [quotaExceededProviders, setQuotaExceededProviders] = useState<Set<string>>(new Set());
  const initializedRef = useRef(false);

  // Load persisted quota status on mount
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const data: StoredQuotaData = JSON.parse(stored);
        // Check if data is still valid (within TTL)
        if (Date.now() - data.timestamp < QUOTA_STATUS_TTL) {
          setQuotaExceededProviders(new Set(data.providers));
        } else {
          // Clear expired data
          localStorage.removeItem(STORAGE_KEY);
        }
      }
    } catch {
      // Ignore storage errors
    }
  }, []);

  // Persist quota status changes
  useEffect(() => {
    if (!initializedRef.current) return;
    
    try {
      if (quotaExceededProviders.size > 0) {
        const data: StoredQuotaData = {
          providers: Array.from(quotaExceededProviders),
          timestamp: Date.now(),
        };
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // Ignore storage errors
    }
  }, [quotaExceededProviders]);

  // Check if an error message indicates quota exceeded
  const isQuotaError = useCallback((message: string | undefined | null): boolean => {
    if (!message) return false;
    const lowerMessage = message.toLowerCase();
    return QUOTA_ERROR_KEYWORDS.some(keyword => lowerMessage.includes(keyword));
  }, []);

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
              console.log(`📊 [QuotaStatus] Detected quota exceeded for: ${normalizedProvider}`);
              setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
            }
          }

          // Also check completed jobs that mention limit in their message
          if (newJob.status === "completed" && newJob.message) {
            if (isQuotaError(newJob.message)) {
              const normalizedProvider = normalizeSourceType(newJob.provider) || newJob.provider;
              console.log(`📊 [QuotaStatus] Detected quota warning for: ${normalizedProvider}`);
              setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
            }
          }
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [user?.id, isQuotaError]);

  const isProviderQuotaExceeded = useCallback((provider: string): boolean => {
    const normalizedProvider = normalizeSourceType(provider) || provider;
    return quotaExceededProviders.has(normalizedProvider);
  }, [quotaExceededProviders]);

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

  const markQuotaExceeded = useCallback((provider: string) => {
    const normalizedProvider = normalizeSourceType(provider) || provider;
    setQuotaExceededProviders(prev => new Set([...prev, normalizedProvider]));
  }, []);

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

export function useQuotaStatus(): QuotaStatus {
  const context = useContext(QuotaStatusContext);
  if (!context) {
    // Return a no-op implementation if used outside provider
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
