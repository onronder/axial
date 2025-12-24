"use client";

/**
 * GlobalProgress Component
 * 
 * Polls the backend for active ingestion jobs and displays
 * a progress bar at the bottom of the screen during ingestion.
 * 
 * Uses polling (not WebSockets) for simplicity and reliability.
 */

import { useState, useEffect, useCallback } from "react";
import { Progress } from "@/components/ui/progress";
import { CheckCircle2, Loader2, XCircle, FileText, X } from "lucide-react";
import { authFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface IngestionJob {
    id: string;
    provider: string;
    total_files: number;
    processed_files: number;
    status: "pending" | "processing" | "completed" | "failed";
    percent: number;
    error_message?: string;
}

const POLL_INTERVAL = 3000; // 3 seconds
const COMPLETION_DISPLAY_TIME = 5000; // Show success for 5 seconds

export function GlobalProgress() {
    const [job, setJob] = useState<IngestionJob | null>(null);
    const [isVisible, setIsVisible] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);
    const [isPolling, setIsPolling] = useState(true);

    const fetchActiveJob = useCallback(async () => {
        if (!isPolling) return;

        try {
            const response = await authFetch.get("/jobs/active");
            const data = response.data;

            if (data) {
                setJob(data);
                setIsVisible(true);

                // If job just completed, show success and schedule hide
                if (data.status === "completed" && !showSuccess) {
                    setShowSuccess(true);
                    setTimeout(() => {
                        setIsVisible(false);
                        setJob(null);
                        setShowSuccess(false);
                    }, COMPLETION_DISPLAY_TIME);
                }

                // If job failed, keep visible until dismissed
                if (data.status === "failed") {
                    setIsPolling(false);
                }
            } else {
                // No active job
                if (!showSuccess) {
                    setIsVisible(false);
                    setJob(null);
                }
            }
        } catch (error) {
            // Silently fail - don't disrupt UX for polling errors
            console.debug("Failed to fetch job status:", error);
        }
    }, [isPolling, showSuccess]);

    // Polling effect (pause when tab is hidden for performance)
    useEffect(() => {
        fetchActiveJob(); // Initial fetch

        const interval = setInterval(() => {
            // Only poll when tab is visible
            if (!document.hidden) {
                fetchActiveJob();
            }
        }, POLL_INTERVAL);

        // Resume immediately when tab becomes visible
        const handleVisibilityChange = () => {
            if (!document.hidden) {
                fetchActiveJob();
            }
        };
        document.addEventListener("visibilitychange", handleVisibilityChange);

        return () => {
            clearInterval(interval);
            document.removeEventListener("visibilitychange", handleVisibilityChange);
        };
    }, [fetchActiveJob]);

    // Resume polling when needed
    useEffect(() => {
        if (!job && !showSuccess) {
            setIsPolling(true);
        }
    }, [job, showSuccess]);

    const handleDismiss = () => {
        setIsVisible(false);
        setJob(null);
        setShowSuccess(false);
        setIsPolling(true);
    };

    if (!isVisible || !job) return null;

    const getStatusIcon = () => {
        switch (job.status) {
            case "pending":
                return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
            case "processing":
                return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
            case "completed":
                return <CheckCircle2 className="h-4 w-4 text-green-500" />;
            case "failed":
                return <XCircle className="h-4 w-4 text-red-500" />;
        }
    };

    const getStatusText = () => {
        switch (job.status) {
            case "pending":
                return "Preparing ingestion...";
            case "processing":
                return `Processing ${job.processed_files} of ${job.total_files} files...`;
            case "completed":
                return `Successfully ingested ${job.total_files} files!`;
            case "failed":
                return job.error_message || "Ingestion failed";
        }
    };

    const getProviderLabel = () => {
        const providers: Record<string, string> = {
            google_drive: "Google Drive",
            drive: "Google Drive",
            notion: "Notion",
            file: "File Upload",
            web: "Web Crawler",
        };
        return providers[job.provider] || job.provider;
    };

    return (
        <div
            className={cn(
                "fixed bottom-0 left-0 right-0 z-50 transition-all duration-300",
                "bg-white dark:bg-slate-900 border-t border-slate-200 dark:border-slate-700",
                "shadow-lg backdrop-blur-sm"
            )}
        >
            <div className="max-w-screen-xl mx-auto px-4 py-3">
                <div className="flex items-center gap-4">
                    {/* Icon */}
                    <div className="flex items-center gap-2">
                        <FileText className="h-5 w-5 text-slate-500" />
                        <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                            {getProviderLabel()}
                        </span>
                    </div>

                    {/* Progress Section */}
                    <div className="flex-1 flex items-center gap-3">
                        <Progress
                            value={job.percent}
                            className={cn(
                                "h-2 flex-1",
                                job.status === "failed" && "opacity-50"
                            )}
                        />
                        <span className="text-sm font-medium text-slate-600 dark:text-slate-400 min-w-[60px] text-right">
                            {Math.round(job.percent)}%
                        </span>
                    </div>

                    {/* Status */}
                    <div className="flex items-center gap-2">
                        {getStatusIcon()}
                        <span
                            className={cn(
                                "text-sm",
                                job.status === "completed" && "text-green-600 dark:text-green-400",
                                job.status === "failed" && "text-red-600 dark:text-red-400",
                                (job.status === "pending" || job.status === "processing") && "text-slate-600 dark:text-slate-400"
                            )}
                        >
                            {getStatusText()}
                        </span>
                    </div>

                    {/* Dismiss button for failed/completed */}
                    {(job.status === "completed" || job.status === "failed") && (
                        <button
                            onClick={handleDismiss}
                            className="p-1 rounded-full hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                            aria-label="Dismiss"
                        >
                            <X className="h-4 w-4 text-slate-500" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
