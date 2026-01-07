"use client";

import { useEffect, useState, useCallback } from "react";
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
    // NEW: Granular progress tracking from backend
    progress?: number;           // 0-100 percentage
    message?: string;            // e.g., "Indexing chunk 45/200..."
    status_message?: string;     // legacy alias
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
 * Hook for realtime ingestion job tracking.
 * 
 * Uses Supabase Realtime to subscribe to job updates.
 * No polling needed - updates arrive instantly!
 */
export function useIngestionJobs(): UseIngestionJobsReturn {
    const { user } = useAuth();
    const { toast } = useToast();
    const [jobs, setJobs] = useState<IngestionJob[]>([]);
    const [isLoading, setIsLoading] = useState(true);

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

    // Handle realtime updates
    const handleRealtimeUpdate = useCallback(
        (payload: { eventType: string; new: IngestionJob; old?: Partial<IngestionJob> }) => {
            const { eventType, new: newJob, old: oldJob } = payload;

            if (eventType === "INSERT") {
                setJobs((prev) => [newJob, ...prev].slice(0, 20));

                toast({
                    title: "Ingestion Started",
                    description: `Processing ${newJob.provider} files...`,
                });
            }

            if (eventType === "UPDATE") {
                setJobs((prev) =>
                    prev.map((job) => (job.id === newJob.id ? newJob : job))
                );

                // Show completion toast
                if (newJob.status === "completed" && oldJob?.status !== "completed") {
                    const completionMessage = newJob.message || newJob.status_message;
                    toast({
                        title: "Ingestion Complete! 🎉",
                        description: completionMessage ||
                            `Successfully processed ${newJob.processed_files} files.`,
                    });
                }

                if (newJob.status === "failed" && oldJob?.status !== "failed") {
                    toast({
                        title: "Ingestion Failed",
                        description: newJob.error_message || "An error occurred.",
                        variant: "destructive",
                    });
                }

                if (newJob.status === "cancelled" && oldJob?.status !== "cancelled") {
                    toast({
                        title: "Ingestion Cancelled",
                        description: "Job was cancelled by user.",
                    });
                }
            }

            if (eventType === "DELETE") {
                setJobs((prev) => prev.filter((job) => job.id !== oldJob?.id));
            }
        },
        [toast]
    );

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
                    // Cast via unknown to handle Supabase realtime payload variance
                    const typed = payload as unknown as { eventType: string; new?: IngestionJob; old?: Partial<IngestionJob> };
                    if (typed.new) handleRealtimeUpdate({ ...typed, new: typed.new });
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    console.log("🔔 Subscribed to ingestion_jobs realtime updates");
                }
            });

        // Cleanup on unmount
        return () => {
            channel.unsubscribe();
        };
    }, [user?.id, fetchJobs, handleRealtimeUpdate]);

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

            // Refresh jobs to show updated status
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
