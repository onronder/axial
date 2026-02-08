"use client";

/**
 * useDataInvalidation Hook - Ghost Protocol
 *
 * Subscribes to compliance tombstone events via Supabase Realtime.
 * When a tombstone is created (data access revoked), this hook:
 * 1. Invalidates React Query cache for affected documents
 * 2. Shows a toast notification to the user
 * 3. Provides helper to check if a document is tombstoned
 *
 * Timeline:
 * - T+0ms:   Backend creates tombstone
 * - T+25ms:  Supabase Realtime broadcasts to all clients
 * - T+50ms:  This hook receives event, invalidates cache
 *
 * @example
 * ```tsx
 * // In a layout or provider component
 * const { isDocumentTombstoned, activeTombstones } = useDataInvalidation(organizationId);
 *
 * // Check if a specific document is blocked
 * if (isDocumentTombstoned("doc-123")) {
 *     showDeletedMessage();
 * }
 * ```
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { RealtimeChannel, RealtimePostgresChangesPayload } from "@supabase/supabase-js";
import { supabase } from "@/lib/supabase";
import { useToast } from "@/hooks/use-toast";

// =============================================================================
// Types
// =============================================================================

/**
 * Tombstone record from Supabase.
 */
interface ComplianceTombstone {
    id: string;
    resource_type: "document" | "scope" | "organization" | "user";
    resource_id: string;
    organization_id: string;
    document_ids: string[];
    scope_ids: string[];
    compliance_type: "gdpr_art17" | "ccpa_admt" | "kvkk" | "user_request";
    status: "active" | "completed" | "failed";
    created_at: string;
    completed_at: string | null;
}

/**
 * Return type for the useDataInvalidation hook.
 */
interface DataInvalidationReturn {
    /**
     * Check if a specific document ID is blocked by an active tombstone.
     */
    isDocumentTombstoned: (documentId: string) => boolean;

    /**
     * Set of all document IDs currently blocked by active tombstones.
     */
    tombstonedDocumentIds: Set<string>;

    /**
     * Number of active tombstones for the organization.
     */
    activeTombstoneCount: number;

    /**
     * Whether Realtime subscription is connected.
     */
    isConnected: boolean;
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook for subscribing to compliance tombstone events.
 *
 * When a tombstone is created (data marked for deletion), this hook:
 * 1. Receives the event via Supabase Realtime
 * 2. Invalidates React Query cache for affected documents
 * 3. Shows a notification to the user
 * 4. Tracks tombstoned document IDs for UI filtering
 *
 * @param organizationId - Organization ID to subscribe to tombstones for
 */
export function useDataInvalidation(
    organizationId: string | null
): DataInvalidationReturn {
    const queryClient = useQueryClient();
    const { toast } = useToast();

    // Track tombstoned document IDs
    const [tombstonedDocumentIds, setTombstonedDocumentIds] = useState<Set<string>>(
        new Set()
    );
    const [activeTombstoneCount, setActiveTombstoneCount] = useState(0);
    const [isConnected, setIsConnected] = useState(false);

    // Refs for cleanup
    const channelRef = useRef<RealtimeChannel | null>(null);
    const mountedRef = useRef(true);

    /**
     * Handle incoming tombstone INSERT event.
     */
    const handleTombstoneInsert = useCallback(
        (payload: RealtimePostgresChangesPayload<ComplianceTombstone>) => {
            if (!mountedRef.current) return;

            const tombstone = payload.new as ComplianceTombstone;
            if (!tombstone || tombstone.status !== "active") return;

            if (process.env.NODE_ENV === "development") {
                console.log(
                    "[DataInvalidation] Tombstone received:",
                    tombstone.id.slice(0, 8),
                    "blocking",
                    tombstone.document_ids?.length || 0,
                    "documents"
                );
            }

            // Update tombstoned document IDs
            setTombstonedDocumentIds((prev) => {
                const updated = new Set(prev);
                (tombstone.document_ids || []).forEach((id) => updated.add(id));
                return updated;
            });

            setActiveTombstoneCount((prev) => prev + 1);

            // Invalidate React Query cache for affected documents
            (tombstone.document_ids || []).forEach((docId) => {
                queryClient.invalidateQueries({ queryKey: ["document", docId] });
            });

            // Invalidate document list queries
            queryClient.invalidateQueries({ queryKey: ["documents"] });

            // Invalidate search results (may contain deleted docs)
            queryClient.invalidateQueries({ queryKey: ["search"] });

            // Show notification
            const documentCount = tombstone.document_ids?.length || 0;
            const resourceLabel =
                tombstone.resource_type === "scope"
                    ? "Data source"
                    : tombstone.resource_type === "document"
                    ? `${documentCount} document${documentCount !== 1 ? "s" : ""}`
                    : "Data";

            toast({
                title: "Data removed",
                description: `${resourceLabel} has been removed and is no longer accessible.`,
                variant: "default",
            });
        },
        [queryClient, toast]
    );

    /**
     * Handle tombstone UPDATE event (completed/failed).
     */
    const handleTombstoneUpdate = useCallback(
        (payload: RealtimePostgresChangesPayload<ComplianceTombstone>) => {
            if (!mountedRef.current) return;

            const tombstone = payload.new as ComplianceTombstone;
            if (!tombstone) return;

            // When tombstone is completed, we can optionally remove from tracking
            // But we keep them for now since the data is still deleted
            if (tombstone.status === "completed") {
                if (process.env.NODE_ENV === "development") {
                    console.log(
                        "[DataInvalidation] Tombstone completed:",
                        tombstone.id.slice(0, 8)
                    );
                }
            } else if (tombstone.status === "failed") {
                // Failed tombstones still block access, but we should alert
                if (process.env.NODE_ENV !== 'production') {
                    console.warn(
                        "[DataInvalidation] Tombstone failed:",
                        tombstone.id.slice(0, 8),
                        "- data still blocked"
                    );
                }
            }
        },
        []
    );

    /**
     * Load initial active tombstones on mount.
     */
    const loadInitialTombstones = useCallback(async () => {
        if (!organizationId) return;

        try {
            const { data, error } = await supabase
                .from("compliance_tombstones")
                .select("document_ids")
                .eq("organization_id", organizationId)
                .eq("status", "active");

            if (error) {
                if (process.env.NODE_ENV !== 'production') {
                    console.warn("[DataInvalidation] Failed to load tombstones:", error);
                }
                return;
            }

            if (data && data.length > 0) {
                const allDocIds = new Set<string>();
                data.forEach((t) => {
                    (t.document_ids || []).forEach((id: string) => allDocIds.add(id));
                });

                setTombstonedDocumentIds(allDocIds);
                setActiveTombstoneCount(data.length);

                if (process.env.NODE_ENV === "development") {
                    console.log(
                        "[DataInvalidation] Loaded",
                        data.length,
                        "active tombstones blocking",
                        allDocIds.size,
                        "documents"
                    );
                }
            }
        } catch (e) {
            if (process.env.NODE_ENV !== 'production') {
                console.warn("[DataInvalidation] Error loading tombstones:", e);
            }
        }
    }, [organizationId]);

    // ==========================================================================
    // Effect: Subscribe to Realtime events
    // ==========================================================================

    useEffect(() => {
        mountedRef.current = true;

        if (!organizationId) {
            setIsConnected(false);
            return;
        }

        // Load initial tombstones
        loadInitialTombstones();

        // Create Realtime channel for this organization's tombstones
        const channelName = `compliance_tombstones_${organizationId}`;
        const channel = supabase.channel(channelName);
        channelRef.current = channel;

        // Subscribe to INSERT events (new tombstones)
        channel.on(
            "postgres_changes",
            {
                event: "INSERT",
                schema: "public",
                table: "compliance_tombstones",
                filter: `organization_id=eq.${organizationId}`,
            },
            handleTombstoneInsert
        );

        // Subscribe to UPDATE events (completed/failed)
        channel.on(
            "postgres_changes",
            {
                event: "UPDATE",
                schema: "public",
                table: "compliance_tombstones",
                filter: `organization_id=eq.${organizationId}`,
            },
            handleTombstoneUpdate
        );

        // Subscribe with status tracking
        channel.subscribe((status) => {
            if (!mountedRef.current) return;

            if (status === "SUBSCRIBED") {
                setIsConnected(true);
                if (process.env.NODE_ENV === "development") {
                    console.log("[DataInvalidation] Realtime connected");
                }
            } else if (status === "CLOSED" || status === "CHANNEL_ERROR") {
                setIsConnected(false);
            }
        });

        // Cleanup on unmount
        return () => {
            mountedRef.current = false;

            if (channelRef.current) {
                channelRef.current.unsubscribe();
                supabase.removeChannel(channelRef.current);
                channelRef.current = null;
            }

            setIsConnected(false);
        };
    }, [
        organizationId,
        handleTombstoneInsert,
        handleTombstoneUpdate,
        loadInitialTombstones,
    ]);

    /**
     * Check if a specific document is tombstoned.
     */
    const isDocumentTombstoned = useCallback(
        (documentId: string): boolean => {
            return tombstonedDocumentIds.has(documentId);
        },
        [tombstonedDocumentIds]
    );

    return {
        isDocumentTombstoned,
        tombstonedDocumentIds,
        activeTombstoneCount,
        isConnected,
    };
}

export type { ComplianceTombstone, DataInvalidationReturn };
