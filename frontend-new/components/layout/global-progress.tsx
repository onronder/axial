
"use client";

/**
 * GlobalProgress Component - SINGLE SOURCE OF TRUTH
 * 
 * This is the ONLY component that should render ingestion progress UI.
 * Uses Supabase Realtime to display ingestion progress instantly.
 * 
 * All other components (IngestModal, FileUploadZone, YoutubeInput, etc.)
 * should use the useIngestionProgress() hook to register jobs, NOT render
 * their own progress modals.
 * 
 * TOAST DEDUPLICATION:
 * - Uses refs to track which jobs have already shown toasts
 * - Prevents duplicate toasts from rapid realtime updates
 * - Only GlobalProgress shows ingestion toasts (not useNotifications)
 */

import { useEffect, useRef, useState, useCallback, memo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, FileText, ChevronRight, X, Upload, Globe, Database } from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { useUsage } from "@/hooks/useUsage";
import { useFileStatus } from "@/hooks/useFileStatus";
import { useIngestionProgress } from "@/hooks/useIngestionProgress";
import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal";
import { formatSourceTypeLabel, normalizeSourceType } from "@/lib/sourceType";
import { Spinner } from "@/components/ui/spinner";

interface IngestionJob {
    id: string;
    user_id: string;
    provider: string;
    total_files: number;
    processed_files: number;
    status: "pending" | "processing" | "completed" | "failed" | "cancelled";
    error_message?: string;
    progress?: number;
    message?: string;
    status_message?: string;
    created_at: string;
    updated_at: string;
}

const COMPLETION_DISPLAY_TIME = 5000;

const providerIcons: Record<string, typeof FileText> = {
    file_upload: Upload,
    web: Globe,
    google_drive: FileText,
    notion: Database,
};

export function GlobalProgress() {
    const { user } = useAuth();
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const { refresh } = useUsage();
    
    const { expandedJobId, expandJob, registerJob, unregisterJob } = useIngestionProgress();
    
    const [jobs, setJobs] = useState<IngestionJob[]>([]);
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
    const [activeJob, setActiveJob] = useState<IngestionJob | null>(null);
    const expandedJobIdRef = useRef<string | null>(null);
    const { files: activeFiles } = useFileStatus(expandedJobId);

    /**
     * TOAST DEDUPLICATION REFS
     * Track which jobs have already shown each type of toast to prevent duplicates
     */
    const completionToastsShown = useRef<Set<string>>(new Set());
    const failureToastsShown = useRef<Set<string>>(new Set());
    const cancelledToastsShown = useRef<Set<string>>(new Set());
    const startToastsShown = useRef<Set<string>>(new Set());

    /**
     * THROTTLE JOB UPDATES
     * Batch rapid updates to prevent UI thrashing
     */
    const pendingJobUpdates = useRef<Map<string, IngestionJob>>(new Map());
    const jobUpdateTimer = useRef<NodeJS.Timeout | null>(null);
    const JOB_UPDATE_THROTTLE = 100; // ms

    /**
     * Apply pending job updates in a batch
     */
    const flushJobUpdates = useCallback(() => {
        if (pendingJobUpdates.current.size === 0) return;

        setJobs((prev) => {
            const updated = prev.map((job) => {
                const update = pendingJobUpdates.current.get(job.id);
                return update || job;
            });
            pendingJobUpdates.current.clear();
            return updated;
        });
    }, []);

    /**
     * Schedule a throttled job update
     */
    const scheduleJobUpdate = useCallback((job: IngestionJob) => {
        pendingJobUpdates.current.set(job.id, job);

        if (!jobUpdateTimer.current) {
            jobUpdateTimer.current = setTimeout(() => {
                flushJobUpdates();
                jobUpdateTimer.current = null;
            }, JOB_UPDATE_THROTTLE);
        }
    }, [flushJobUpdates]);

    /**
     * Show toast only once per job per status
     */
    const showCompletionToast = useCallback((job: IngestionJob) => {
        if (completionToastsShown.current.has(job.id)) return;
        completionToastsShown.current.add(job.id);

        const completionMessage = job.message || job.status_message;
        const provider = normalizeSourceType(job.provider) || job.provider;
        
        toast({
            title: "Ingestion Complete! 🎉",
            description: completionMessage ||
                `Successfully processed ${job.processed_files} files from ${formatSourceTypeLabel(provider)}.`,
        });

        // Auto-dismiss after delay
        setTimeout(() => {
            setJobs((prev) =>
                prev.filter((j) => j.id !== job.id || expandedJobIdRef.current === job.id)
            );
            unregisterJob(job.id);
        }, COMPLETION_DISPLAY_TIME);
    }, [toast, unregisterJob]);

    const showFailureToast = useCallback((job: IngestionJob) => {
        if (failureToastsShown.current.has(job.id)) return;
        failureToastsShown.current.add(job.id);

        toast({
            title: "Ingestion Failed",
            description: job.error_message || "An error occurred during processing.",
            variant: "destructive",
        });

        setTimeout(() => unregisterJob(job.id), COMPLETION_DISPLAY_TIME);
    }, [toast, unregisterJob]);

    const showCancelledToast = useCallback((job: IngestionJob) => {
        if (cancelledToastsShown.current.has(job.id)) return;
        cancelledToastsShown.current.add(job.id);

        const provider = normalizeSourceType(job.provider) || job.provider;
        toast({
            title: "Ingestion Cancelled",
            description: `${formatSourceTypeLabel(provider)} ingestion was cancelled.`,
            variant: "default",
        });

        setTimeout(() => {
            setJobs((prev) =>
                prev.filter((j) => j.id !== job.id || expandedJobIdRef.current === job.id)
            );
            unregisterJob(job.id);
        }, COMPLETION_DISPLAY_TIME);
    }, [toast, unregisterJob]);

    /**
     * Called when ingestion completes - refresh data caches
     */
    const handleIngestionComplete = useCallback(() => {
        if (process.env.NODE_ENV !== 'production') {
            console.log("📊 [GlobalProgress] Ingestion complete - refreshing data...");
        }
        // Immediate refresh
        refresh(true);
        queryClient.invalidateQueries({ queryKey: ["documents"] });
        queryClient.invalidateQueries({ queryKey: ["documentCount"] });

        // Delayed second refresh to catch backend write delays
        setTimeout(() => {
            refresh(true);
            queryClient.invalidateQueries({ queryKey: ["documents"] });
            queryClient.invalidateQueries({ queryKey: ["documentCount"] });
        }, 2000);
    }, [refresh, queryClient]);

    // Setup realtime subscription
    useEffect(() => {
        if (!user?.id) return;

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
                        // Only show start toast once
                        if (!startToastsShown.current.has(newJob.id)) {
                            startToastsShown.current.add(newJob.id);
                            setJobs((prev) => [newJob, ...prev].slice(0, 5));
                            registerJob(newJob.id);
                        }
                    }

                    if (payload.eventType === "UPDATE") {
                        // Check for terminal status changes BEFORE throttled update
                        const wasNotCompleted = oldJob?.status !== "completed";
                        const wasNotFailed = oldJob?.status !== "failed";
                        const wasNotCancelled = oldJob?.status !== "cancelled";

                        // Handle terminal statuses immediately (no throttle)
                        if (newJob.status === "completed" && wasNotCompleted) {
                            // Immediately update job state for terminal status
                            setJobs((prev) =>
                                prev.map((job) => (job.id === newJob.id ? newJob : job))
                            );
                            showCompletionToast(newJob);
                            handleIngestionComplete();
                        } else if (newJob.status === "failed" && wasNotFailed) {
                            setJobs((prev) =>
                                prev.map((job) => (job.id === newJob.id ? newJob : job))
                            );
                            showFailureToast(newJob);
                        } else if (newJob.status === "cancelled" && wasNotCancelled) {
                            setJobs((prev) =>
                                prev.map((job) => (job.id === newJob.id ? newJob : job))
                            );
                            showCancelledToast(newJob);
                        } else {
                            // Throttle non-terminal updates
                            scheduleJobUpdate(newJob);
                        }

                        // Update active job ref if expanded
                        if (expandedJobIdRef.current === newJob.id) {
                            setActiveJob(newJob);
                        }
                    }
                }
            )
            .subscribe((status) => {
                if (status === "SUBSCRIBED") {
                    if (process.env.NODE_ENV !== 'production') {
                        console.log("🔔 GlobalProgress: Realtime connected");
                    }
                }
            });

        return () => {
            if (jobUpdateTimer.current) {
                clearTimeout(jobUpdateTimer.current);
                jobUpdateTimer.current = null;
            }
            flushJobUpdates();
            channel.unsubscribe();
        };
    }, [user?.id, registerJob, showCompletionToast, showFailureToast, showCancelledToast, scheduleJobUpdate, flushJobUpdates, handleIngestionComplete]);

    // Sync expanded job ref
    useEffect(() => {
        expandedJobIdRef.current = expandedJobId;
        if (!expandedJobId) {
            setActiveJob(null);
            return;
        }
        const job = jobs.find((j) => j.id === expandedJobId) || null;
        if (job) {
            setActiveJob(job);
        }
    }, [expandedJobId, jobs]);

    const visibleJobs = jobs.filter(
        (job) => !dismissedIds.has(job.id) && job.id !== expandedJobId
    );

    const handleDismiss = useCallback((jobId: string) => {
        setDismissedIds((prev) => new Set([...prev, jobId]));
        setJobs((prev) => prev.filter((j) => j.id !== jobId));
        unregisterJob(jobId);
    }, [unregisterJob]);

    const handleOpenDetails = useCallback((job: IngestionJob) => {
        expandJob(job.id);
        setActiveJob(job);
    }, [expandJob]);

    const handleCloseDetails = useCallback(() => {
        expandJob(null);
        setActiveJob(null);
    }, [expandJob]);

    if (visibleJobs.length === 0 && !expandedJobId) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {expandedJobId && (
                <IngestionProgressModal
                    jobId={expandedJobId}
                    files={activeFiles}
                    totalFiles={activeJob?.total_files || activeFiles.length}
                    overallProgress={
                        activeJob?.progress ??
                        (activeJob?.total_files
                            ? Math.round((activeJob.processed_files / activeJob.total_files) * 100)
                            : 0)
                    }
                    onClose={handleCloseDetails}
                    onComplete={handleIngestionComplete}
                />
            )}
            <AnimatePresence mode="popLayout">
                {visibleJobs.map((job) => (
                    <JobCard
                        key={job.id}
                        job={job}
                        onDismiss={() => handleDismiss(job.id)}
                        onOpenDetails={() => handleOpenDetails(job)}
                    />
                ))}
            </AnimatePresence>
        </div>
    );
}

/**
 * Memoized JobCard to prevent unnecessary re-renders
 */
const JobCard = memo(function JobCard({
    job,
    onDismiss,
    onOpenDetails,
}: {
    job: IngestionJob;
    onDismiss: () => void;
    onOpenDetails: () => void;
}) {
    const normalizedProvider = normalizeSourceType(job.provider) || job.provider;
    const Icon = providerIcons[normalizedProvider] || FileText;
    const label = formatSourceTypeLabel(normalizedProvider);

    const progress = job.progress ?? (
        job.total_files > 0
            ? Math.round((job.processed_files / job.total_files) * 100)
            : 0
    );

    const isActive = job.status === "pending" || job.status === "processing";
    const isComplete = job.status === "completed";
    const isFailed = job.status === "failed";
    const isCancelled = job.status === "cancelled";

    const statusText = job.message ||
        job.status_message ||
        (job.status === "pending" ? "Starting..." :
            job.processed_files === job.total_files
                ? "Completing..."
                : `Processing ${job.processed_files + 1}/${job.total_files} files`);

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100, scale: 0.95 }}
            role="button"
            tabIndex={0}
            onClick={onOpenDetails}
            onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onOpenDetails();
                }
            }}
            className={cn(
                "relative flex items-center gap-3 rounded-lg border p-3 shadow-lg backdrop-blur-sm min-w-[300px]",
                "bg-card/95 dark:bg-card/95 cursor-pointer",
                isActive && "border-primary/30",
                isComplete && "border-green-500/30 bg-green-50/50 dark:bg-green-950/20",
                isFailed && "border-red-500/30 bg-red-50/50 dark:bg-red-950/20",
                isCancelled && "border-amber-500/30 bg-amber-50/50 dark:bg-amber-950/20"
            )}
        >
            {(isComplete || isFailed || isCancelled) && (
                <button
                    onClick={(event) => {
                        event.stopPropagation();
                        onDismiss();
                    }}
                    className="absolute top-1 right-1 p-1 rounded-full hover:bg-muted transition-colors"
                >
                    <X className="h-3 w-3 text-muted-foreground" />
                </button>
            )}

            <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                isActive && "bg-primary/10",
                isComplete && "bg-green-100 dark:bg-green-900/30",
                isFailed && "bg-red-100 dark:bg-red-900/30",
                isCancelled && "bg-amber-100 dark:bg-amber-900/30"
            )}>
                {isActive ? (
                    <Spinner className="h-5 w-5 animate-spin text-primary" />
                ) : isComplete ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : isCancelled ? (
                    <XCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                ) : (
                    <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
            </div>

            <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium truncate">{label}</span>
                </div>

                {isActive && (
                    <>
                        <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted">
                            <motion.div
                                className="h-full bg-gradient-to-r from-primary to-primary/80 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                            />
                        </div>
                        <div className="mt-1 flex items-center justify-between">
                            <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                                {statusText}
                            </p>
                            <span className="text-xs font-medium text-primary">
                                {progress}%
                            </span>
                        </div>
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

                {isCancelled && (
                    <p className="mt-0.5 text-xs text-amber-600 dark:text-amber-400">
                        Cancelled
                    </p>
                )}
            </div>
            <ChevronRight className="h-4 w-4 text-muted-foreground/70" />
        </motion.div>
    );
});