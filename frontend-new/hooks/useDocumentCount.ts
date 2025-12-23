"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

/**
 * Hook to fetch the user's document count.
 * Used to determine if onboarding should be shown.
 */
export function useDocumentCount() {
    const [count, setCount] = useState<number | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchCount = async () => {
            try {
                const { data } = await api.get('/api/v1/documents');
                // API returns array of documents
                const documents = Array.isArray(data) ? data : data?.documents || [];
                setCount(documents.length);
            } catch (err: any) {
                console.error('[useDocumentCount] Error:', err);
                setError(err.message);
                setCount(0); // Assume 0 on error to show onboarding
            } finally {
                setIsLoading(false);
            }
        };

        fetchCount();
    }, []);

    return {
        count,
        isLoading,
        error,
        isEmpty: count === 0,
        hasDocuments: count !== null && count > 0,
    };
}
