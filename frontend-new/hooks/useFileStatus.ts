"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { RealtimeChannel } from "@supabase/supabase-js";

/**
 * File status types matching backend status field
 */
export type FileStatusType =
    | "pending"
    | "uploading"
    | "parsing"
    | "processing" // legacy alias for parsing
    | "embedding"
    | "indexing"
    | "indexed" // completed but still receives legacy status upstream
    | "completed"
    | "failed"
    | "skipped"
    | "skipped_unsupported"
    | "skipped_file_too_large"
    | "skipped_unchanged"
    | "cancelled"
    | (string & {});

const SKIPPED_STATUSES = [
    "skipped",
    "skipped_unsupported",
    "skipped_file_too_large",
    "skipped_unchanged",
] as const;

const TERMINAL_STATUSES = [
    "completed",
    "failed",
    "cancelled",
    "indexed",
    ...SKIPPED_STATUSES,
] as const;

const TERMINAL_STATUS_SET = new Set<string>(TERMINAL_STATUSES);
const TERMINAL_STATUS_SQL = `(${TERMINAL_STATUSES.map((status) => `"${status}"`).join(",")})`;

function isTerminalStatus(status: FileStatusType): boolean {
    return TERMINAL_STATUS_SET.has(status);
}

/**
 * Per-file ingestion status record
 */
export interface FileStatus {
    id: string;
    job_id: string;
    user_id: string;
    filename: string;
    file_size_bytes: number;
    status: FileStatusType;
    progress: number;
    status_message: string | null;
    error_message: string | null;
    chunks_total: number;
    chunks_processed: number;
    document_id: string | null;
    created_at: string;
    updated_at: string;
}

interface UseFileStatusReturn {
    files: FileStatus[];
    isLoading: boolean;
    error: string | null;
    refresh: () => Promise<void>;
}

/**
 * Throttle interval for batching realtime updates (ms)
 * This prevents excessive re-renders when many files update rapidly
 */
const THROTTLE_INTERVAL = 150;

/**
 * Hook for tracking per-file ingestion status with real-time updates.
 * 
 * Uses THROTTLED BATCHING to prevent UI thrashing when many files update.
 * Updates are collected and applied in batches every 150ms.
 * 
 * @param jobId - The parent ingestion job ID
 */
export function useFileStatus(jobId: string | null): UseFileStatusReturn {
    const [files, setFiles] = useState<FileStatus[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Batching refs for throttled updates
    const pendingUpdates = useRef<Map<string, FileStatus>>(new Map());
    const pendingInserts = useRef<FileStatus[]>([]);
    const pendingDeletes = useRef<Set<string>>(new Set());
    const throttleTimer = useRef<NodeJS.Timeout | null>(null);

    /**
     * Apply all pending changes in a single batch update
     */
    const flushPendingChanges = useCallback(() => {
        const hasUpdates = pendingUpdates.current.size > 0;
        const hasInserts = pendingInserts.current.length > 0;
        const hasDeletes = pendingDeletes.current.size > 0;

        if (!hasUpdates && !hasInserts && !hasDeletes) return;

        setFiles((prev) => {
            let result = [...prev];

            // Apply deletes
            if (hasDeletes) {
                result = result.filter((f) => !pendingDeletes.current.has(f.id));
                pendingDeletes.current.clear();
            }

            // Apply updates
            if (hasUpdates) {
                result = result.map((f) => {
                    const update = pendingUpdates.current.get(f.id);
                    return update || f;
                });
                pendingUpdates.current.clear();
            }

            // Apply inserts (avoid duplicates)
            if (hasInserts) {
                const existingIds = new Set(result.map((f) => f.id));
                const newFiles = pendingInserts.current.filter(
                    (f) => !existingIds.has(f.id)
                );
                result = [...result, ...newFiles];
                pendingInserts.current = [];
            }

            return result;
        });
    }, []);

    /**
     * Schedule a batched flush (debounced)
     */
    const scheduleFlush = useCallback(() => {
        if (throttleTimer.current) return; // Already scheduled

        throttleTimer.current = setTimeout(() => {
            flushPendingChanges();
            throttleTimer.current = null;
        }, THROTTLE_INTERVAL);
    }, [flushPendingChanges]);

    const fetchFiles = useCallback(async () => {
        if (!jobId) {
            setFiles([]);
            setIsLoading(false);
            return;
        }

        try {
            const { data, error: fetchError } = await supabase
                .from("ingestion_file_status")
                .select("*")
                .eq("job_id", jobId)
                .order("created_at", { ascending: true });

            if (fetchError) throw fetchError;
            setFiles(data || []);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch file status:", err);
            setError(err instanceof Error ? err.message : "Failed to fetch");
        } finally {
            setIsLoading(false);
        }
    }, [jobId]);

    useEffect(() => {
        if (!jobId) {
            setFiles([]);
            setIsLoading(false);
            return;
        }

        // Fetch initial data
        fetchFiles();

        // Subscribe to real-time updates for this job's files
        const channel: RealtimeChannel = supabase
            .channel(`file_status_${jobId}`)
            .on(
                "postgres_changes",
                {
                    event: "*",
                    schema: "public",
                    table: "ingestion_file_status",
                    filter: `job_id=eq.${jobId}`,
                },
                (payload) => {
                    const newFile = payload.new as FileStatus;
                    const oldFile = payload.old as FileStatus;

                    if (payload.eventType === "INSERT") {
                        pendingInserts.current.push(newFile);
                        scheduleFlush();
                    }

                    if (payload.eventType === "UPDATE") {
                        // For terminal statuses, apply immediately for better UX
                        if (isTerminalStatus(newFile.status)) {
                            pendingUpdates.current.set(newFile.id, newFile);
                            flushPendingChanges(); // Immediate flush for completion
                        } else {
                            pendingUpdates.current.set(newFile.id, newFile);
                            scheduleFlush();
                        }
                    }

                    if (payload.eventType === "DELETE") {
                        pendingDeletes.current.add(oldFile?.id);
                        scheduleFlush();
                    }
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    console.log(`🔔 Subscribed to file status for job ${jobId.slice(0, 8)}...`);
                }
            });

        // ✅ CLEANUP - Prevent memory leaks
        return () => {
            if (throttleTimer.current) {
                clearTimeout(throttleTimer.current);
                throttleTimer.current = null;
            }
            // Flush any remaining changes before unmount
            flushPendingChanges();
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [jobId, fetchFiles, scheduleFlush, flushPendingChanges]);

    return {
        files,
        isLoading,
        error,
        refresh: fetchFiles,
    };
}

/**
 * Hook for tracking all active file statuses for the current user.
 * 
 * Uses THROTTLED BATCHING to prevent UI thrashing.
 */
export function useAllActiveFiles(): UseFileStatusReturn {
    const [files, setFiles] = useState<FileStatus[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Batching refs for throttled updates
    const pendingUpdates = useRef<Map<string, FileStatus | null>>(new Map());
    const pendingInserts = useRef<FileStatus[]>([]);
    const throttleTimer = useRef<NodeJS.Timeout | null>(null);

    const flushPendingChanges = useCallback(() => {
        const hasUpdates = pendingUpdates.current.size > 0;
        const hasInserts = pendingInserts.current.length > 0;

        if (!hasUpdates && !hasInserts) return;

        setFiles((prev) => {
            let result = [...prev];

            // Apply updates (null means remove)
            if (hasUpdates) {
                const toRemove = new Set<string>();
                pendingUpdates.current.forEach((file, id) => {
                    if (file === null) {
                        toRemove.add(id);
                    } else {
                        const idx = result.findIndex((f) => f.id === id);
                        if (idx >= 0) {
                            result[idx] = file;
                        } else {
                            result = [file, ...result];
                        }
                    }
                });
                if (toRemove.size > 0) {
                    result = result.filter((f) => !toRemove.has(f.id));
                }
                pendingUpdates.current.clear();
            }

            // Apply inserts
            if (hasInserts) {
                const existingIds = new Set(result.map((f) => f.id));
                const newFiles = pendingInserts.current.filter(
                    (f) => !existingIds.has(f.id)
                );
                result = [...newFiles, ...result].slice(0, 20);
                pendingInserts.current = [];
            }

            return result;
        });
    }, []);

    const scheduleFlush = useCallback(() => {
        if (throttleTimer.current) return;

        throttleTimer.current = setTimeout(() => {
            flushPendingChanges();
            throttleTimer.current = null;
        }, THROTTLE_INTERVAL);
    }, [flushPendingChanges]);

    const fetchFiles = useCallback(async () => {
        try {
            const { data, error: fetchError } = await supabase
                .from("ingestion_file_status")
                .select("*")
                .not("status", "in", TERMINAL_STATUS_SQL)
                .order("created_at", { ascending: false })
                .limit(20);

            if (fetchError) throw fetchError;
            setFiles(data || []);
            setError(null);
        } catch (err) {
            console.error("Failed to fetch active files:", err);
            setError(err instanceof Error ? err.message : "Failed to fetch");
        } finally {
            setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchFiles();

        // Subscribe to all file status changes
        const channel = supabase
            .channel("all_file_status")
            .on(
                "postgres_changes",
                {
                    event: "*",
                    schema: "public",
                    table: "ingestion_file_status",
                },
                (payload) => {
                    const newFile = payload.new as FileStatus;

                    if (payload.eventType === "INSERT") {
                        if (!isTerminalStatus(newFile.status)) {
                            pendingInserts.current.push(newFile);
                            scheduleFlush();
                        }
                    }

                    if (payload.eventType === "UPDATE") {
                        if (isTerminalStatus(newFile.status)) {
                            // Remove completed files
                            pendingUpdates.current.set(newFile.id, null);
                        } else {
                            pendingUpdates.current.set(newFile.id, newFile);
                        }
                        scheduleFlush();
                    }
                }
            )
            .subscribe();

        // ✅ CLEANUP
        return () => {
            if (throttleTimer.current) {
                clearTimeout(throttleTimer.current);
                throttleTimer.current = null;
            }
            flushPendingChanges();
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [fetchFiles, scheduleFlush, flushPendingChanges]);

    return {
        files,
        isLoading,
        error,
        refresh: fetchFiles,
    };
}

/**
 * Get a human-readable status label
 */
export function getStatusLabel(status: FileStatusType): string {
    const labels: Record<string, string> = {
        pending: "Queued",
        uploading: "Uploading...",
        parsing: "Parsing...",
        processing: "Parsing...",
        embedding: "Embedding...",
        indexing: "Indexing...",
        indexed: "Indexed",
        completed: "Complete",
        failed: "Failed",
        skipped: "Skipped",
        skipped_unsupported: "Unsupported",
        skipped_file_too_large: "Too Large",
        skipped_unchanged: "Unchanged",
        cancelled: "Cancelled",
    };
    if (typeof status === "string" && status.startsWith("skipped") && !labels[status]) {
        return "Skipped";
    }
    return labels[status] || status;
}

/**
 * Get status color for UI
 */
export function getStatusColor(status: FileStatusType): string {
    const colors: Record<string, string> = {
        pending: "text-muted-foreground",
        uploading: "text-blue-500",
        parsing: "text-amber-500",
        processing: "text-amber-500",
        embedding: "text-purple-500",
        indexing: "text-cyan-500",
        indexed: "text-green-500",
        completed: "text-green-500",
        failed: "text-red-500",
        skipped: "text-amber-500",
        skipped_unsupported: "text-orange-500",
        skipped_file_too_large: "text-orange-500",
        skipped_unchanged: "text-amber-500",
        cancelled: "text-amber-500",
    };
    if (typeof status === "string" && status.startsWith("skipped") && !colors[status]) {
        return "text-amber-500";
    }
    return colors[status] || "text-muted-foreground";
}
