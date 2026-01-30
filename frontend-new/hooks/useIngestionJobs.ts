"use client";

/**
 * useIngestionJobs Hook
 * 
 * Provides realtime tracking of ingestion jobs.
 * 
 * IMPORTANT: TOASTS ARE HANDLED BY GlobalProgress
 * 
 * This hook only manages job data state. All toast notifications for
 * ingestion events (start, complete, failed, cancelled) are handled
 * by the GlobalProgress component to prevent duplicate toasts.
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { supabase } from "@/lib/supabase";
import { api } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { RealtimeChannel } from "@supabase/supabase-js";

export interface IngestionJob {
    id: string;
    user_id: string;
    provider: string;
    status: "pending" | "processing" | "completed" | "failed" | "cancelled";
    total_files: number;
    processed_files: number;
    error_message?: string;
    progress?: number;
    message?: string;
    status_message?: string;
    created_at: string;
    updated_at: string;
}

interface UseIngestionJobsReturn {
    jobs: IngestionJob[];
    activeJobs: IngestionJob[];
    isLoading: boolean;
    refresh: () => Promise<void>;
    retryJob: (jobId: string) => Promise<void>;
}

/**
 * Throttle interval for batching realtime updates (ms)
 */
const THROTTLE_INTERVAL = 100;

/**
 * Hook for realtime ingestion job tracking.
 * 
 * Uses Supabase Realtime to subscribe to job updates.
 * No polling needed - updates arrive instantly!
 * 
 * NOTE: Toasts are NOT shown here - GlobalProgress handles all
 * ingestion-related toast notifications to prevent duplicates.
 */
export function useIngestionJobs(): UseIngestionJobsReturn {
    const { user } = useAuth();
    const { toast } = useToast();
    const [jobs, setJobs] = useState<IngestionJob[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // Throttling refs
    const pendingUpdates = useRef<Map<string, IngestionJob>>(new Map());
    const pendingInserts = useRef<IngestionJob[]>([]);
    const pendingDeletes = useRef<Set<string>>(new Set());
    const throttleTimer = useRef<NodeJS.Timeout | null>(null);

    /**
     * Flush all pending changes in a single batch
     */
    const flushPendingChanges = useCallback(() => {
        const hasUpdates = pendingUpdates.current.size > 0;
        const hasInserts = pendingInserts.current.length > 0;
        const hasDeletes = pendingDeletes.current.size > 0;

        if (!hasUpdates && !hasInserts && !hasDeletes) return;

        setJobs((prev) => {
            let result = [...prev];

            // Apply deletes
            if (hasDeletes) {
                result = result.filter((j) => !pendingDeletes.current.has(j.id));
                pendingDeletes.current.clear();
            }

            // Apply updates
            if (hasUpdates) {
                result = result.map((j) => {
                    const update = pendingUpdates.current.get(j.id);
                    return update || j;
                });
                pendingUpdates.current.clear();
            }

            // Apply inserts
            if (hasInserts) {
                const existingIds = new Set(result.map((j) => j.id));
                const newJobs = pendingInserts.current.filter(
                    (j) => !existingIds.has(j.id)
                );
                result = [...newJobs, ...result].slice(0, 20);
                pendingInserts.current = [];
            }

            return result;
        });
    }, []);

    /**
     * Schedule a throttled flush
     */
    const scheduleFlush = useCallback(() => {
        if (throttleTimer.current) return;

        throttleTimer.current = setTimeout(() => {
            flushPendingChanges();
            throttleTimer.current = null;
        }, THROTTLE_INTERVAL);
    }, [flushPendingChanges]);

    // Fetch initial jobs
    const fetchJobs = useCallback(async () => {
        if (!user?.id) return;

        try {
            const { data, error } = await supabase
                .from("ingestion_jobs")
                .select("*")
                .eq("user_id", user.id)
                .order("created_at", { ascending: false })
                .limit(20);

            if (error) throw error;
            setJobs(data || []);
        } catch (error) {
            console.error("Failed to fetch ingestion jobs:", error);
        } finally {
            setIsLoading(false);
        }
    }, [user?.id]);

    // Setup realtime subscription
    useEffect(() => {
        if (!user?.id) return;

        // Initial fetch
        fetchJobs();

        // Subscribe to realtime updates
        const channel: RealtimeChannel = supabase
            .channel(`ingestion_jobs_${user.id}`)
            .on(
                "postgres_changes",
                {
                    event: "*",
                    schema: "public",
                    table: "ingestion_jobs",
                    filter: `user_id=eq.${user.id}`,
                },
                (payload) => {
                    const newJob = payload.new as IngestionJob;
                    const oldJob = payload.old as Partial<IngestionJob>;

                    if (payload.eventType === "INSERT") {
                        pendingInserts.current.push(newJob);
                        // Immediate flush for new jobs so they appear quickly
                        flushPendingChanges();
                    }

                    if (payload.eventType === "UPDATE") {
                        // Terminal statuses should be applied immediately
                        const isTerminal = ["completed", "failed", "cancelled"].includes(newJob.status);
                        const wasNotTerminal = !["completed", "failed", "cancelled"].includes(oldJob?.status || "");

                        if (isTerminal && wasNotTerminal) {
                            // Immediate update for terminal status changes
                            setJobs((prev) =>
                                prev.map((job) => (job.id === newJob.id ? newJob : job))
                            );
                        } else {
                            // Throttle in-progress updates
                            pendingUpdates.current.set(newJob.id, newJob);
                            scheduleFlush();
                        }
                    }

                    if (payload.eventType === "DELETE") {
                        pendingDeletes.current.add(oldJob?.id || "");
                        scheduleFlush();
                    }
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    if (process.env.NODE_ENV === 'development') {
                        console.log("🔔 Subscribed to ingestion_jobs realtime updates");
                    }
                }
            });

        // Cleanup on unmount
        return () => {
            if (throttleTimer.current) {
                clearTimeout(throttleTimer.current);
                throttleTimer.current = null;
            }
            flushPendingChanges();
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [user?.id, fetchJobs, scheduleFlush, flushPendingChanges]);

    // Filter for active (in-progress) jobs
    const activeJobs = jobs.filter(
        (job) => job.status === "pending" || job.status === "processing"
    );

    // Retry entire failed job
    const retryJob = useCallback(async (jobId: string): Promise<void> => {
        try {
            const response = await api.post(`/jobs/${jobId}/retry`);
            const result = response.data;

            toast({
                title: "Job Retry Started",
                description: `Retrying ${result.files_queued} failed files...`,
            });

            await fetchJobs();
        } catch (err) {
            const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
            const message = axiosErr.response?.data?.detail || axiosErr.message || 'Could not retry the job.';
            console.error("Failed to retry job:", message);
            toast({
                title: "Retry Failed",
                description: message,
                variant: "destructive",
            });
            throw err;
        }
    }, [fetchJobs, toast]);

    return {
        jobs,
        activeJobs,
        isLoading,
        refresh: fetchJobs,
        retryJob,
    };
}

/**
 * Hook for tracking a single job's progress.
 * Useful for modal/inline progress displays.
 */
export function useIngestionJobProgress(jobId: string | null) {
    const { user } = useAuth();
    const [job, setJob] = useState<IngestionJob | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        if (!jobId || !user?.id) {
            setIsLoading(false);
            return;
        }

        // Fetch initial state
        const fetchJob = async () => {
            const { data, error } = await supabase
                .from("ingestion_jobs")
                .select("*")
                .eq("id", jobId)
                .single();

            if (!error && data) {
                setJob(data);
            }
            setIsLoading(false);
        };

        fetchJob();

        // Subscribe to this specific job
        const channel = supabase
            .channel(`job_${jobId}`)
            .on(
                "postgres_changes",
                {
                    event: "UPDATE",
                    schema: "public",
                    table: "ingestion_jobs",
                    filter: `id=eq.${jobId}`,
                },
                (payload) => {
                    setJob(payload.new as IngestionJob);
                }
            )
            .subscribe();

        return () => {
            channel.unsubscribe();
            supabase.removeChannel(channel);
        };
    }, [jobId, user?.id]);

    const progress = job
        ? job.total_files > 0
            ? Math.round((job.processed_files / job.total_files) * 100)
            : 0
        : 0;

    return {
        job,
        isLoading,
        progress,
        isComplete: job?.status === "completed",
        isFailed: job?.status === "failed",
        isActive: job?.status === "pending" || job?.status === "processing",
    };
}
