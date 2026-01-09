'use client';

import { useState, useCallback } from 'react';
import { api } from '@/lib/api';

export interface SearchResult {
    id: string;
    content: string;
    metadata: Record<string, unknown>;
    similarity: number;
    source_type: string;
    document_id: string;
}

export interface SearchResponse {
    results: SearchResult[];
    query: string;
    count: number;
}

/**
 * Hook for performing vector search across ingested documents.
 * Uses the /api/v1/search endpoint.
 */
export const useSearch = () => {
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastQuery, setLastQuery] = useState<string>('');

    /**
     * Perform a vector search
     * @param query - The search query text
     * @param topK - Number of results to return (default: 5)
     * @param filters - Optional filters to apply
     */
    const search = useCallback(async (
        query: string,
        topK: number = 5,
        filters?: Record<string, unknown>
    ): Promise<SearchResult[]> => {
        if (!query.trim()) {
            setResults([]);
            return [];
        }

        setIsSearching(true);
        setError(null);
        setLastQuery(query);

        try {
            const { data } = await api.post('/search', {
                query,
                top_k: topK,
                filters,
            });

            // Handle different response formats
            const searchResults = Array.isArray(data) ? data : (data.results || []);
            setResults(searchResults);
            return searchResults;
        } catch (err: unknown) {
            console.error('Search failed:', err);
            const message = err instanceof Error ? err.message : 'Search failed';
            const errorMessage = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || message;
            setError(errorMessage);
            setResults([]);
            return [];
        } finally {
            setIsSearching(false);
        }
    }, []);

    /**
     * Clear search results
     */
    const clearResults = useCallback(() => {
        setResults([]);
        setLastQuery('');
        setError(null);
    }, []);

    return {
        results,
        isSearching,
        error,
        lastQuery,
        search,
        clearResults,
    };
};
