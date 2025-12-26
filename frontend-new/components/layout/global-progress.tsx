"use client";

/**
 * GlobalProgress Component - REALTIME VERSION
 * 
 * Uses Supabase Realtime to display ingestion progress instantly.
 * No more polling - updates arrive via WebSocket!
 */

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Progress } from "@/components/ui/progress";
import {
    CheckCircle2,
    Loader2,
    XCircle,
    FileText,
    X,
    Upload,
    Globe,
    Database
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";

interface IngestionJob {
    id: string;
    user_id: string;
    provider: string;
    total_files: number;
    processed_files: number;
    status: "pending" | "processing" | "completed" | "failed";
    error_message?: string;
    created_at: string;
    updated_at: string;
}

const COMPLETION_DISPLAY_TIME = 5000;

const providerIcons: Record<string, typeof FileText> = {
    file: Upload,
    web: Globe,
    drive: FileText,
    notion: Database,
};

const providerLabels: Record<string, string> = {
    file: "File Upload",
    web: "Web Crawl",
    drive: "Google Drive",
    google_drive: "Google Drive",
    notion: "Notion",
};

export function GlobalProgress() {
    const { user } = useAuth();
    const { toast } = useToast();
    const [jobs, setJobs] = useState<IngestionJob[]>([]);
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

    // Setup realtime subscription
    useEffect(() => {
        if (!user?.id) return;

        // Fetch initial active jobs
        const fetchJobs = async () => {
            const { data } = await supabase
                .from("ingestion_jobs")
                .select("*")
                .eq("user_id", user.id)
                .in("status", ["pending", "processing"])
                .order("created_at", { ascending: false })
                .limit(5);

            if (data) setJobs(data);
        };

        fetchJobs();

        // Subscribe to realtime updates
        const channel = supabase
            .channel(`progress_${user.id}`)
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
                    const oldJob = payload.old as IngestionJob;

                    if (payload.eventType === "INSERT") {
                        setJobs((prev) => [newJob, ...prev].slice(0, 5));
                    }

                    if (payload.eventType === "UPDATE") {
                        setJobs((prev) =>
                            prev.map((job) => (job.id === newJob.id ? newJob : job))
                        );

                        // Show completion toast
                        if (newJob.status === "completed" && oldJob?.status !== "completed") {
                            toast({
                                title: "Ingestion Complete! 🎉",
                                description: `Successfully processed ${newJob.processed_files} files from ${providerLabels[newJob.provider] || newJob.provider}.`,
                            });

                            // Auto-dismiss after delay
                            setTimeout(() => {
                                setJobs((prev) => prev.filter((j) => j.id !== newJob.id));
                            }, COMPLETION_DISPLAY_TIME);
                        }

                        if (newJob.status === "failed" && oldJob?.status !== "failed") {
                            toast({
                                title: "Ingestion Failed",
                                description: newJob.error_message || "An error occurred during processing.",
                                variant: "destructive",
                            });
                        }
                    }
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    console.log("🔔 GlobalProgress: Realtime connected");
                }
            });

        return () => {
            channel.unsubscribe();
        };
    }, [user?.id, toast]);

    // Filter out dismissed jobs
    const visibleJobs = jobs.filter(
        (job) => !dismissedIds.has(job.id)
    );

    const handleDismiss = (jobId: string) => {
        setDismissedIds((prev) => new Set([...prev, jobId]));
        setJobs((prev) => prev.filter((j) => j.id !== jobId));
    };

    if (visibleJobs.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            <AnimatePresence mode="popLayout">
                {visibleJobs.map((job) => (
                    <JobCard
                        key={job.id}
                        job={job}
                        onDismiss={() => handleDismiss(job.id)}
                    />
                ))}
            </AnimatePresence>
        </div>
    );
}

function JobCard({ job, onDismiss }: { job: IngestionJob; onDismiss: () => void }) {
    const Icon = providerIcons[job.provider] || FileText;
    const label = providerLabels[job.provider] || job.provider;

    const progress = job.total_files > 0
        ? Math.round((job.processed_files / job.total_files) * 100)
        : 0;

    const isActive = job.status === "pending" || job.status === "processing";
    const isComplete = job.status === "completed";
    const isFailed = job.status === "failed";

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            className={cn(
                "relative flex items-center gap-3 rounded-lg border p-3 shadow-lg backdrop-blur-sm min-w-[280px]",
                "bg-card/95 dark:bg-card/95",
                isActive && "border-primary/30",
                isComplete && "border-green-500/30 bg-green-50/50 dark:bg-green-950/20",
                isFailed && "border-red-500/30 bg-red-50/50 dark:bg-red-950/20"
            )}
        >
            {/* Dismiss button */}
            {(isComplete || isFailed) && (
                <button
                    onClick={onDismiss}
                    className="absolute top-1 right-1 p-1 rounded-full hover:bg-muted transition-colors"
                >
                    <X className="h-3 w-3 text-muted-foreground" />
                </button>
            )}

            {/* Status Icon */}
            <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                isActive && "bg-primary/10",
                isComplete && "bg-green-100 dark:bg-green-900/30",
                isFailed && "bg-red-100 dark:bg-red-900/30"
            )}>
                {isActive ? (
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : isComplete ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : (
                    <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
            </div>

            {/* Content */}
            <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium truncate">{label}</span>
                </div>

                {isActive && (
                    <>
                        <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                            <motion.div
                                className="h-full bg-primary rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                                transition={{ duration: 0.4, ease: "easeOut" }}
                            />
                        </div>
                        <p className="mt-1 text-xs text-muted-foreground">
                            {job.processed_files} / {job.total_files} files • {progress}%
                        </p>
                    </>
                )}

                {isComplete && (
                    <p className="mt-0.5 text-xs text-green-600 dark:text-green-400">
                        ✓ {job.processed_files} files ingested
                    </p>
                )}

                {isFailed && (
                    <p className="mt-0.5 text-xs text-red-600 dark:text-red-400 truncate pr-4">
                        {job.error_message || "Processing failed"}
                    </p>
                )}
            </div>
        </motion.div>
    );
}
