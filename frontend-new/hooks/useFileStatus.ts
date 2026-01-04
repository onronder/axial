"use client";

import { useEffect, useState, useCallback } from "react";
import { supabase } from "@/lib/supabase";
import { RealtimeChannel } from "@supabase/supabase-js";

/**
 * File status types matching backend status field
 */
export type FileStatusType =
    | "pending"
    | "uploading"
    | "processing"
    | "embedding"
    | "indexing"
    | "completed"
    | "failed";

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
 * Hook for tracking per-file ingestion status with real-time updates.
 * 
 * Subscribes to the ingestion_file_status table for a specific job
 * and receives instant updates as files are processed.
 * 
 * @param jobId - The parent ingestion job ID
 */
export function useFileStatus(jobId: string | null): UseFileStatusReturn {
    const [files, setFiles] = useState<FileStatus[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

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
                        setFiles((prev) => [...prev, newFile]);
                    }

                    if (payload.eventType === "UPDATE") {
                        setFiles((prev) =>
                            prev.map((f) => (f.id === newFile.id ? newFile : f))
                        );
                    }

                    if (payload.eventType === "DELETE") {
                        setFiles((prev) => prev.filter((f) => f.id !== oldFile?.id));
                    }
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    console.log(`🔔 Subscribed to file status for job ${jobId.slice(0, 8)}...`);
                }
            });

        return () => {
            channel.unsubscribe();
        };
    }, [jobId, fetchFiles]);

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
 * Useful for a global progress panel that shows all files being processed.
 */
export function useAllActiveFiles(): UseFileStatusReturn {
    const [files, setFiles] = useState<FileStatus[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchFiles = useCallback(async () => {
        try {
            const { data, error: fetchError } = await supabase
                .from("ingestion_file_status")
                .select("*")
                .not("status", "in", '("completed","failed")')
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
                        // Add new files that aren't completed
                        if (newFile.status !== "completed" && newFile.status !== "failed") {
                            setFiles((prev) => [newFile, ...prev].slice(0, 20));
                        }
                    }

                    if (payload.eventType === "UPDATE") {
                        setFiles((prev) => {
                            // If completed/failed, remove from active list
                            if (newFile.status === "completed" || newFile.status === "failed") {
                                return prev.filter((f) => f.id !== newFile.id);
                            }
                            // Otherwise update in place
                            const idx = prev.findIndex((f) => f.id === newFile.id);
                            if (idx >= 0) {
                                return [...prev.slice(0, idx), newFile, ...prev.slice(idx + 1)];
                            }
                            return [newFile, ...prev].slice(0, 20);
                        });
                    }
                }
            )
            .subscribe();

        return () => {
            channel.unsubscribe();
        };
    }, [fetchFiles]);

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
    const labels: Record<FileStatusType, string> = {
        pending: "Queued",
        uploading: "Downloading...",
        processing: "Processing...",
        embedding: "Embedding...",
        indexing: "Indexing...",
        completed: "Complete",
        failed: "Failed",
    };
    return labels[status] || status;
}

/**
 * Get status color for UI
 */
export function getStatusColor(status: FileStatusType): string {
    const colors: Record<FileStatusType, string> = {
        pending: "text-muted-foreground",
        uploading: "text-blue-500",
        processing: "text-amber-500",
        embedding: "text-purple-500",
        indexing: "text-cyan-500",
        completed: "text-green-500",
        failed: "text-red-500",
    };
    return colors[status] || "text-muted-foreground";
}
