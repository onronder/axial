"use client";

/**
 * GlobalProgress Component - REALTIME VERSION
 * 
 * Uses Supabase Realtime to display ingestion progress instantly.
 * No more polling - updates arrive via WebSocket!
 */

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    CheckCircle2,
    Loader2,
    XCircle,
    FileText,
    ChevronRight,
    X,
    Upload,
    Globe,
    Database
} from "lucide-react";
import { cn } from "@/lib/utils";
import { supabase } from "@/lib/supabase";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { useFileStatus } from "@/hooks/useFileStatus";
import { IngestionProgressModal } from "@/components/ingestion/IngestionProgressModal";
import { formatSourceTypeLabel, normalizeSourceType } from "@/lib/sourceType";

interface IngestionJob {
    id: string;
    user_id: string;
    provider: string;
    total_files: number;
    processed_files: number;
    status: "pending" | "processing" | "completed" | "failed" | "cancelled";
    error_message?: string;
    // NEW: Granular progress tracking from backend
    progress?: number;           // 0-100 percentage  
    message?: string;            // e.g., "Indexing chunk 45/200..."
    status_message?: string;     // legacy alias
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
    const [jobs, setJobs] = useState<IngestionJob[]>([]);
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
    const [activeJobId, setActiveJobId] = useState<string | null>(null);
    const [activeJob, setActiveJob] = useState<IngestionJob | null>(null);
    const activeJobIdRef = useRef<string | null>(null);
    const { files: activeFiles } = useFileStatus(activeJobId);

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
                        if (activeJobIdRef.current === newJob.id) {
                            setActiveJob(newJob);
                        }

                        // Show completion toast
                        if (newJob.status === "completed" && oldJob?.status !== "completed") {
                            const completionMessage = newJob.message || newJob.status_message;
                            const provider = normalizeSourceType(newJob.provider) || newJob.provider;
                            toast({
                                title: "Ingestion Complete! 🎉",
                                description: completionMessage ||
                                    `Successfully processed ${newJob.processed_files} files from ${formatSourceTypeLabel(provider)}.`,
                            });

                            // Auto-dismiss after delay
                            setTimeout(() => {
                                setJobs((prev) =>
                                    prev.filter((j) => j.id !== newJob.id || activeJobIdRef.current === newJob.id)
                                );
                            }, COMPLETION_DISPLAY_TIME);
                        }

                        if (newJob.status === "failed" && oldJob?.status !== "failed") {
                            toast({
                                title: "Ingestion Failed",
                                description: newJob.error_message || "An error occurred during processing.",
                                variant: "destructive",
                            });
                        }

                        if (newJob.status === "cancelled" && oldJob?.status !== "cancelled") {
                            const provider = normalizeSourceType(newJob.provider) || newJob.provider;
                            toast({
                                title: "Ingestion Cancelled",
                                description: `${formatSourceTypeLabel(provider)} ingestion was cancelled.`,
                                variant: "default",
                            });

                            // Auto-dismiss after delay
                            setTimeout(() => {
                                setJobs((prev) =>
                                    prev.filter((j) => j.id !== newJob.id || activeJobIdRef.current === newJob.id)
                                );
                            }, COMPLETION_DISPLAY_TIME);
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

    useEffect(() => {
        activeJobIdRef.current = activeJobId;
        if (!activeJobId) {
            setActiveJob(null);
            return;
        }
        const job = jobs.find((j) => j.id === activeJobId) || null;
        if (job) {
            setActiveJob(job);
        }
    }, [activeJobId, jobs]);

    // Filter out dismissed jobs
    const visibleJobs = jobs.filter(
        (job) => !dismissedIds.has(job.id) && job.id !== activeJobId
    );

    const handleDismiss = (jobId: string) => {
        setDismissedIds((prev) => new Set([...prev, jobId]));
        setJobs((prev) => prev.filter((j) => j.id !== jobId));
    };

    const handleOpenDetails = (job: IngestionJob) => {
        setActiveJobId(job.id);
        setActiveJob(job);
    };

    const handleCloseDetails = () => {
        setActiveJobId(null);
        setActiveJob(null);
    };

    if (visibleJobs.length === 0 && !activeJobId) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
            {activeJobId && (
                <IngestionProgressModal
                    jobId={activeJobId}
                    files={activeFiles}
                    totalFiles={activeJob?.total_files || activeFiles.length}
                    overallProgress={
                        activeJob?.progress ??
                        (activeJob?.total_files
                            ? Math.round((activeJob.processed_files / activeJob.total_files) * 100)
                            : 0)
                    }
                    onClose={handleCloseDetails}
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

function JobCard({
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

    // Use backend progress if available, fallback to file-based calculation
    const progress = job.progress ?? (
        job.total_files > 0
            ? Math.round((job.processed_files / job.total_files) * 100)
            : 0
    );

    const isActive = job.status === "pending" || job.status === "processing";
    const isComplete = job.status === "completed";
    const isFailed = job.status === "failed";
    const isCancelled = job.status === "cancelled";

    // Status message from backend or fallback
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
            {/* Dismiss button */}
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

            {/* Status Icon */}
            <div className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg",
                isActive && "bg-primary/10",
                isComplete && "bg-green-100 dark:bg-green-900/30",
                isFailed && "bg-red-100 dark:bg-red-900/30",
                isCancelled && "bg-amber-100 dark:bg-amber-900/30"
            )}>
                {isActive ? (
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : isComplete ? (
                    <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : isCancelled ? (
                    <XCircle className="h-5 w-5 text-amber-600 dark:text-amber-400" />
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
                        {/* Progress Bar with smooth animation */}
                        <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-muted">
                            <motion.div
                                className="h-full bg-gradient-to-r from-primary to-primary/80 rounded-full"
                                initial={{ width: 0 }}
                                animate={{ width: `${progress}%` }}
                                transition={{ duration: 0.5, ease: "easeOut" }}
                            />
                        </div>
                        {/* Status Text with percentage */}
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
}
