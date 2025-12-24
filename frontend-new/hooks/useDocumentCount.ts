"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

interface DocumentStats {
    total_documents: number;
    last_updated: string | null;
}

/**
 * Hook to fetch the user's document statistics.
 * Uses the optimized /stats endpoint (O(1) count query).
 * Used to determine if onboarding should be shown.
 */
export function useDocumentCount() {
    const [count, setCount] = useState<number | null>(null);
    const [lastUpdated, setLastUpdated] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                // Use optimized /stats endpoint - only fetches count, not documents
                const { data } = await api.get<DocumentStats>('/api/v1/documents/stats');
                setCount(data.total_documents);
                setLastUpdated(data.last_updated);
            } catch (err: any) {
                console.error('[useDocumentCount] Error:', err);
                setError(err.message);
                setCount(0); // Assume 0 on error to show onboarding
            } finally {
                setIsLoading(false);
            }
        };

        fetchStats();
    }, []);

    return {
        count,
        lastUpdated,
        isLoading,
        error,
        isEmpty: count === 0,
        hasDocuments: count !== null && count > 0,
    };
}
