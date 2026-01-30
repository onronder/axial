/**
 * Request Deduplication Utility
 * 
 * Prevents duplicate API calls when multiple components request the same data
 * simultaneously. This is particularly useful for:
 * 
 * 1. Initial page loads where multiple components fetch the same data
 * 2. React Strict Mode causing double-fetches in development
 * 3. Multiple hooks calling the same API in parallel
 * 
 * @example
 * ```typescript
 * // Instead of:
 * const data1 = await api.get('/user');
 * const data2 = await api.get('/user'); // Duplicate call!
 * 
 * // Use:
 * const data1 = await dedupedRequest('user', () => api.get('/user'));
 * const data2 = await dedupedRequest('user', () => api.get('/user')); // Reuses first call!
 * ```
 */

// =============================================================================
// Types
// =============================================================================

interface PendingRequest<T> {
    promise: Promise<T>;
    timestamp: number;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Time window (in ms) during which duplicate requests will be coalesced.
 * Requests made within this window will share the same promise.
 */
const DEDUP_WINDOW_MS = 100;

/**
 * Maximum time (in ms) to keep a request in the pending map after completion.
 * This prevents the map from growing indefinitely.
 */
const CLEANUP_DELAY_MS = 100;

// =============================================================================
// State
// =============================================================================

/**
 * Map of pending requests keyed by request identifier.
 */
const pendingRequests = new Map<string, PendingRequest<unknown>>();

// =============================================================================
// Public API
// =============================================================================

/**
 * Execute a request with deduplication.
 * 
 * If an identical request (by key) is already in flight or was made within
 * the dedup window, the existing promise is returned instead of making
 * a new request.
 * 
 * @param key - Unique identifier for the request (e.g., URL + params)
 * @param fetcher - Function that performs the actual request
 * @returns Promise that resolves with the request result
 * 
 * @example
 * ```typescript
 * // Simple usage
 * const user = await dedupedRequest('user', () => api.get('/user'));
 * 
 * // With parameters in key
 * const docs = await dedupedRequest(
 *     `documents:${page}:${limit}`,
 *     () => api.get(`/documents?page=${page}&limit=${limit}`)
 * );
 * ```
 */
export async function dedupedRequest<T>(
    key: string,
    fetcher: () => Promise<T>
): Promise<T> {
    const now = Date.now();
    const existing = pendingRequests.get(key);

    // Check if there's an existing request within the dedup window
    if (existing && (now - existing.timestamp) < DEDUP_WINDOW_MS) {
        return existing.promise as Promise<T>;
    }

    // Create new request
    const promise = fetcher().finally(() => {
        // Clean up after request completes (with small delay to handle race conditions)
        setTimeout(() => {
            const current = pendingRequests.get(key);
            // Only delete if this is still our request
            if (current && current.promise === promise) {
                pendingRequests.delete(key);
            }
        }, CLEANUP_DELAY_MS);
    });

    // Store in pending map
    pendingRequests.set(key, { promise, timestamp: now });

    return promise;
}

/**
 * Create a deduped fetcher function for a specific endpoint pattern.
 * 
 * Useful when you want to create a reusable deduped fetch function.
 * 
 * @param keyPrefix - Prefix for the request key
 * @param fetcher - Function that performs the request with given args
 * @returns Deduped version of the fetcher
 * 
 * @example
 * ```typescript
 * // Create a deduped user fetcher
 * const fetchUser = createDedupedFetcher(
 *     'user',
 *     (userId: string) => api.get(`/users/${userId}`)
 * );
 * 
 * // Use it - calls with same userId will be deduped
 * const user1 = await fetchUser('123');
 * const user2 = await fetchUser('123'); // Reuses first call!
 * ```
 */
export function createDedupedFetcher<T, Args extends unknown[]>(
    keyPrefix: string,
    fetcher: (...args: Args) => Promise<T>
): (...args: Args) => Promise<T> {
    return (...args: Args) => {
        const key = `${keyPrefix}:${JSON.stringify(args)}`;
        return dedupedRequest(key, () => fetcher(...args));
    };
}

/**
 * Clear all pending requests.
 * 
 * Useful for testing or when you need to force fresh data.
 * Note: This doesn't cancel in-flight requests, just removes them from the map.
 */
export function clearPendingRequests(): void {
    pendingRequests.clear();
}

/**
 * Get the number of currently pending requests.
 * Useful for debugging and monitoring.
 */
export function getPendingRequestCount(): number {
    return pendingRequests.size;
}

/**
 * Check if a request is currently pending.
 * 
 * @param key - The request key to check
 * @returns true if request is pending, false otherwise
 */
export function isRequestPending(key: string): boolean {
    return pendingRequests.has(key);
}

// =============================================================================
// React Query Integration Helpers
// =============================================================================

/**
 * Create a query function wrapper that deduplicates requests.
 * 
 * For use with React Query's queryFn option.
 * 
 * @param queryKey - React Query key (will be stringified for dedup key)
 * @param fetcher - The actual query function
 * @returns Deduped query function
 * 
 * @example
 * ```typescript
 * useQuery({
 *     queryKey: ['user', userId],
 *     queryFn: createDedupedQueryFn(
 *         ['user', userId],
 *         () => api.get(`/users/${userId}`)
 *     ),
 * });
 * ```
 */
export function createDedupedQueryFn<T>(
    queryKey: readonly unknown[],
    fetcher: () => Promise<T>
): () => Promise<T> {
    const key = `query:${JSON.stringify(queryKey)}`;
    return () => dedupedRequest(key, fetcher);
}
