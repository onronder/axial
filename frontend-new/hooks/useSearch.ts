'use client';

/**
 * useSearch Hook
 * 
 * Provides vector search functionality across ingested documents.
 * 
 * Features:
 * - Debounced search for typing (300ms default)
 * - Immediate search for programmatic calls
 * - Abort controller for cancellation
 * - Request deduplication
 * - Error handling with user-friendly messages
 * 
 * @example
 * ```tsx
 * const { results, isSearching, search, searchDebounced, clearResults } = useSearch();
 * 
 * // For controlled inputs (debounced)
 * <input onChange={(e) => searchDebounced(e.target.value, 5)} />
 * 
 * // For immediate search (e.g., button click)
 * <button onClick={() => search(query, 10)}>Search</button>
 * ```
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { api } from '@/lib/api';
import { dedupedRequest } from '@/lib/request-dedup';
import { extractErrorMessage } from '@/lib/error-handling';

// =============================================================================
// Types
// =============================================================================

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

export interface UseSearchOptions {
    /** Debounce delay in milliseconds (default: 300) */
    debounceMs?: number;
}

export interface UseSearchReturn {
    /** Search results */
    results: SearchResult[];
    /** Whether a search is in progress */
    isSearching: boolean;
    /** Error message if search failed */
    error: string | null;
    /** The last query that was searched */
    lastQuery: string;
    /** Execute search immediately (no debounce) */
    search: (query: string, topK?: number, filters?: Record<string, unknown>) => Promise<SearchResult[]>;
    /** Execute search with debounce (for typing) */
    searchDebounced: (query: string, topK?: number, filters?: Record<string, unknown>) => void;
    /** Clear search results and reset state */
    clearResults: () => void;
    /** Cancel any pending search */
    cancelSearch: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_DEBOUNCE_MS = 300;
const DEFAULT_TOP_K = 5;

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for performing vector search across ingested documents.
 * Uses the /api/v1/search endpoint.
 */
export const useSearch = (options: UseSearchOptions = {}): UseSearchReturn => {
    const { debounceMs = DEFAULT_DEBOUNCE_MS } = options;

    // State
    const [results, setResults] = useState<SearchResult[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastQuery, setLastQuery] = useState<string>('');

    // Refs for debounce and abort
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const mountedRef = useRef(true);

    // Cleanup on unmount
    useEffect(() => {
        mountedRef.current = true;
        
        return () => {
            mountedRef.current = false;
            
            // Clear debounce timer
            if (debounceTimerRef.current) {
                clearTimeout(debounceTimerRef.current);
            }
            
            // Abort any in-flight request
            if (abortControllerRef.current) {
                abortControllerRef.current.abort();
            }
        };
    }, []);

    /**
     * Cancel any pending search (both debounced and in-flight).
     */
    const cancelSearch = useCallback(() => {
        // Clear debounce timer
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
            debounceTimerRef.current = null;
        }
        
        // Abort in-flight request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
            abortControllerRef.current = null;
        }
    }, []);

    /**
     * Perform a vector search immediately (no debounce).
     * 
     * @param query - The search query text
     * @param topK - Number of results to return (default: 5)
     * @param filters - Optional filters to apply
     */
    const search = useCallback(async (
        query: string,
        topK: number = DEFAULT_TOP_K,
        filters?: Record<string, unknown>
    ): Promise<SearchResult[]> => {
        // Handle empty query
        if (!query.trim()) {
            setResults([]);
            setLastQuery('');
            return [];
        }

        // Cancel any previous request
        cancelSearch();

        // Create new abort controller
        const abortController = new AbortController();
        abortControllerRef.current = abortController;

        setIsSearching(true);
        setError(null);
        setLastQuery(query);

        try {
            // Use deduplication to prevent duplicate requests
            const dedupKey = `search:${query}:${topK}:${JSON.stringify(filters || {})}`;
            const scopeIds = Array.isArray(filters?.scope_ids)
                ? (filters.scope_ids as string[])
                : undefined;
            const threshold = typeof filters?.threshold === 'number'
                ? (filters.threshold as number)
                : undefined;
            const includeScopeAnalysis = typeof filters?.include_scope_analysis === 'boolean'
                ? (filters.include_scope_analysis as boolean)
                : undefined;
            
            const data = await dedupedRequest(dedupKey, async () => {
                const response = await api.post('/search', {
                    query,
                    limit: topK,
                    ...(scopeIds ? { scope_ids: scopeIds } : {}),
                    ...(typeof threshold === 'number' ? { threshold } : {}),
                    ...(typeof includeScopeAnalysis === 'boolean'
                        ? { include_scope_analysis: includeScopeAnalysis }
                        : {}),
                }, {
                    signal: abortController.signal,
                });
                return response.data;
            });

            // Check if component is still mounted and request wasn't aborted
            if (!mountedRef.current || abortController.signal.aborted) {
                return [];
            }

            // Handle different response formats
            const searchResults = Array.isArray(data) ? data : (data.results || []);
            setResults(searchResults);
            return searchResults;
            
        } catch (err: unknown) {
            // Don't handle abort errors
            if (err instanceof Error && err.name === 'AbortError') {
                return [];
            }
            
            // Don't update state if unmounted
            if (!mountedRef.current) {
                return [];
            }

            if (process.env.NODE_ENV !== 'production') {
                console.error('Search failed:', extractErrorMessage(err));
            }
            const errorMessage = extractErrorMessage(err, 'Search failed');
            setError(errorMessage);
            setResults([]);
            return [];
            
        } finally {
            // Only update state if mounted and not aborted
            if (mountedRef.current && !abortController.signal.aborted) {
                setIsSearching(false);
            }
        }
    }, [cancelSearch]);

    /**
     * Perform a debounced search.
     * 
     * Multiple calls within the debounce window will only trigger one search
     * with the last query value.
     * 
     * @param query - The search query text
     * @param topK - Number of results to return (default: 5)
     * @param filters - Optional filters to apply
     */
    const searchDebounced = useCallback((
        query: string,
        topK: number = DEFAULT_TOP_K,
        filters?: Record<string, unknown>
    ): void => {
        // Clear any existing debounce timer
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }

        // Handle empty query immediately (no debounce needed)
        if (!query.trim()) {
            setResults([]);
            setLastQuery('');
            return;
        }

        // Set up debounced search
        debounceTimerRef.current = setTimeout(() => {
            search(query, topK, filters);
        }, debounceMs);
    }, [search, debounceMs]);

    /**
     * Clear search results and reset state.
     */
    const clearResults = useCallback(() => {
        cancelSearch();
        setResults([]);
        setLastQuery('');
        setError(null);
        setIsSearching(false);
    }, [cancelSearch]);

    return {
        results,
        isSearching,
        error,
        lastQuery,
        search,
        searchDebounced,
        clearResults,
        cancelSearch,
    };
};
