"use client";

/**
 * DataInvalidationProvider - Ghost Protocol
 *
 * Provides compliance tombstone tracking across the application.
 * Subscribes to Supabase Realtime for immediate cache invalidation
 * when data is deleted.
 *
 * This provider should wrap the application inside SessionProvider
 * (needs user context to determine organization).
 *
 * @example
 * ```tsx
 * // In layout.tsx
 * <SessionProvider>
 *     <DataInvalidationProvider>
 *         {children}
 *     </DataInvalidationProvider>
 * </SessionProvider>
 * ```
 */

import { createContext, useContext, useMemo } from "react";
import {
    useDataInvalidation,
    type DataInvalidationReturn,
} from "@/hooks/useDataInvalidation";
import { useSession } from "@/components/providers/SessionProvider";
import { useProfile } from "@/hooks/useProfile";

// =============================================================================
// Context
// =============================================================================

interface DataInvalidationContextType extends DataInvalidationReturn {
    /**
     * Organization ID being tracked (if available).
     */
    organizationId: string | null;
}

const DataInvalidationContext = createContext<DataInvalidationContextType>({
    isDocumentTombstoned: () => false,
    tombstonedDocumentIds: new Set(),
    activeTombstoneCount: 0,
    isConnected: false,
    organizationId: null,
});

/**
 * Hook to access data invalidation context.
 */
export const useDataInvalidationContext = () => useContext(DataInvalidationContext);

// =============================================================================
// Provider Component
// =============================================================================

interface DataInvalidationProviderProps {
    children: React.ReactNode;
}

export function DataInvalidationProvider({
    children,
}: DataInvalidationProviderProps) {
    const { user } = useSession();
    const { profile } = useProfile();
    const organizationId = profile?.organization_id ?? user?.id ?? null;

    // Use the data invalidation hook with the organization ID
    const {
        isDocumentTombstoned,
        tombstonedDocumentIds,
        activeTombstoneCount,
        isConnected,
    } = useDataInvalidation(organizationId);

    // Memoize context value to prevent unnecessary re-renders
    const contextValue = useMemo<DataInvalidationContextType>(
        () => ({
            isDocumentTombstoned,
            tombstonedDocumentIds,
            activeTombstoneCount,
            isConnected,
            organizationId,
        }),
        [
            isDocumentTombstoned,
            tombstonedDocumentIds,
            activeTombstoneCount,
            isConnected,
            organizationId,
        ]
    );

    return (
        <DataInvalidationContext.Provider value={contextValue}>
            {children}
        </DataInvalidationContext.Provider>
    );
}
