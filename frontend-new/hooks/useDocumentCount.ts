"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

interface DocumentStats {
    total_documents: number;
    last_updated: string | null;
}

export const DOCUMENT_COUNT_KEY = ["documentCount"] as const;

async function fetchDocumentStats(signal?: AbortSignal): Promise<DocumentStats> {
    const { data } = await api.get<DocumentStats>("/documents/stats", { signal });
    return data;
}

/**
 * Hook to fetch the user's document statistics.
 * Uses the optimized /stats endpoint (O(1) count query).
 * Used to determine if onboarding should be shown.
 */
export function useDocumentCount() {
    const { data, isLoading, error, refetch } = useQuery({
        queryKey: DOCUMENT_COUNT_KEY,
        queryFn: ({ signal }) => fetchDocumentStats(signal),
        staleTime: 60 * 1000,
        refetchOnWindowFocus: true,
    });

    const errorMessage = error instanceof Error ? error.message : null;
    const count = data?.total_documents ?? (errorMessage ? 0 : null);
    const lastUpdated = data?.last_updated ?? null;

    return {
        count,
        lastUpdated,
        isLoading,
        error: errorMessage,
        isEmpty: count === 0,
        hasDocuments: count !== null && count > 0,
        refresh: refetch,
    };
}
