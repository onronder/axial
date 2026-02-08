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

import { createContext, useContext, useEffect, useState, useMemo } from "react";
import {
    useDataInvalidation,
    type DataInvalidationReturn,
} from "@/hooks/useDataInvalidation";
import { useSession } from "@/components/providers/SessionProvider";
import { supabase } from "@/lib/supabase";

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
    const [organizationId, setOrganizationId] = useState<string | null>(null);

    // Fetch user's organization ID
    useEffect(() => {
        if (!user?.id) {
            setOrganizationId(null);
            return;
        }

        const fetchOrganizationId = async () => {
            try {
                // Get user's team membership to find organization
                const { data, error } = await supabase
                    .from("team_members")
                    .select("team_id")
                    .eq("member_user_id", user.id)
                    .single();

                if (error) {
                    // User might not be in a team yet, use user ID as fallback
                    if (process.env.NODE_ENV === "development") {
                        console.log(
                            "[DataInvalidationProvider] No team found, using user ID"
                        );
                    }
                    setOrganizationId(user.id);
                    return;
                }

                setOrganizationId(data?.team_id || user.id);
            } catch (e) {
                if (process.env.NODE_ENV !== 'production') {
                    console.warn("[DataInvalidationProvider] Failed to fetch org:", e);
                }
                setOrganizationId(user.id);
            }
        };

        fetchOrganizationId();
    }, [user?.id]);

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
