"use client";

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState, ReactNode } from "react";
import { toast } from "sonner"; // Using sonner as per package.json
import { AxiosError } from "axios";

interface QueryProviderProps {
    children: ReactNode;
}

/**
 * Handle global API errors (e.g., 500 Internal Server Error)
 */
function handleGlobalError(error: unknown) {
    if (error instanceof AxiosError) {
        if (error.response?.status === 500) {
            toast.error("Something went wrong on our end.", {
                description: "Our team has been notified. Please try again later.",
            });
        }
    }
}

/**
 * React Query Provider with optimized default settings.
 * 
 * Features:
 * - Automatic caching (5 min stale time)
 * - Background refetching on window focus
 * - Retry logic with exponential backoff
 * - DevTools in development
 * - GLOBAL ERROR HANDLING (500s)
 */
export function QueryProvider({ children }: QueryProviderProps) {
    const [queryClient] = useState(
        () =>
            new QueryClient({
                // Global Error Handling
                queryCache: new QueryCache({
                    onError: handleGlobalError,
                }),
                mutationCache: new MutationCache({
                    onError: handleGlobalError,
                }),
                defaultOptions: {
                    queries: {
                        // Cache data for 5 minutes before marking stale
                        staleTime: 5 * 60 * 1000,
                        // Keep unused data in cache for 10 minutes
                        gcTime: 10 * 60 * 1000,
                        // Retry failed requests 3 times with exponential backoff
                        retry: 3,
                        retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
                        // Refetch on window focus for fresh data
                        refetchOnWindowFocus: true,
                        // Don't refetch on mount if data is fresh
                        refetchOnMount: false,
                    },
                    mutations: {
                        // Retry mutations once
                        retry: 1,
                    },
                },
            })
    );

    return (
        <QueryClientProvider client={queryClient}>
            {children}
            {process.env.NODE_ENV === "development" && (
                <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
            )}
        </QueryClientProvider>
    );
}
