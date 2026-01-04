"use client";

/**
 * IngestionProgressPanel - Per-File Progress Tracking UI
 * 
 * A persistent, minimizable panel that shows real-time progress for each file
 * being ingested. Provides granular status (uploading, processing, embedding, etc.)
 * with visual progress bars.
 */

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    ChevronUp,
    ChevronDown,
    X,
    FileText,
    Loader2,
    CheckCircle2,
    XCircle,
    AlertCircle,
    RotateCcw,
    StopCircle
} from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import { useIngestionJobs, IngestionJob } from "@/hooks/useIngestionJobs";
import {
    useFileStatus,
    FileStatus,
    getStatusLabel,
    getStatusColor
} from "@/hooks/useFileStatus";
import { useToast } from "@/hooks/use-toast";
import { supabase } from "@/lib/supabase";

/**
 * API helper for authenticated requests
 */
async function apiRequest(endpoint: string, method: "POST" | "GET" = "POST") {
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) throw new Error("Not authenticated");

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1${endpoint}`, {
        method,
        headers: {
            "Authorization": `Bearer ${session.access_token}`,
            "Content-Type": "application/json"
        }
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: "Request failed" }));
        throw new Error(error.detail || "Request failed");
    }

    return response.json();
}

/**
 * Format bytes to human-readable string
 */
function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Status icon based on file state
 */
function StatusIcon({ status }: { status: FileStatus["status"] }) {
    switch (status) {
        case "completed":
            return <CheckCircle2 className="h-4 w-4 text-green-500" />;
        case "failed":
            return <XCircle className="h-4 w-4 text-red-500" />;
        default:
            return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
    }
}

/**
 * Individual file status card with retry button
 */
function FileStatusCard({ file, onRetry }: { file: FileStatus; onRetry?: (id: string) => void }) {
    const isActive = !["completed", "failed", "cancelled"].includes(file.status);
    const [isRetrying, setIsRetrying] = useState(false);
    const { toast } = useToast();

    const handleRetry = useCallback(async () => {
        if (isRetrying) return;
        setIsRetrying(true);

        try {
            await apiRequest(`/jobs/files/${file.id}/retry`);
            toast({ title: "Retry queued", description: file.filename });
            onRetry?.(file.id);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to retry";
            toast({ title: "Retry failed", description: message, variant: "destructive" });
        } finally {
            setIsRetrying(false);
        }
    }, [file.id, file.filename, isRetrying, toast, onRetry]);

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className={cn(
                "flex items-start gap-3 p-3 rounded-lg border bg-card/50",
                file.status === "failed" && "border-red-500/30 bg-red-50/5",
                file.status === "completed" && "border-green-500/30 bg-green-50/5",
                file.status === "cancelled" && "border-amber-500/30 bg-amber-50/5"
            )}
        >
            {/* File Icon */}
            <div className="flex-shrink-0 mt-0.5">
                <FileText className="h-8 w-8 text-muted-foreground" />
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                {/* Filename */}
                <p className="text-sm font-medium truncate">{file.filename}</p>

                {/* Size and Status */}
                <div className="flex items-center gap-2 mt-0.5 text-xs">
                    {file.file_size_bytes > 0 && (
                        <>
                            <span className="text-muted-foreground">
                                {formatBytes(file.file_size_bytes)}
                            </span>
                            <span className="text-muted-foreground">•</span>
                        </>
                    )}
                    <span className={cn("font-medium", getStatusColor(file.status))}>
                        {file.status_message || getStatusLabel(file.status)}
                    </span>
                </div>

                {/* Progress bar for active files */}
                {isActive && (
                    <div className="mt-2">
                        <Progress value={file.progress} className="h-1.5" />
                    </div>
                )}

                {/* Chunk progress for embedding/indexing */}
                {file.chunks_total > 0 && isActive && (
                    <p className="mt-1 text-[10px] text-muted-foreground">
                        {file.chunks_processed}/{file.chunks_total} chunks
                    </p>
                )}

                {/* Error message */}
                {file.status === "failed" && file.error_message && (
                    <div className="mt-1 flex items-start gap-1">
                        <AlertCircle className="h-3 w-3 text-red-500 mt-0.5 flex-shrink-0" />
                        <p className="text-[10px] text-red-500 line-clamp-2">
                            {file.error_message}
                        </p>
                    </div>
                )}
            </div>

            {/* Actions */}
            <div className="flex flex-col items-center gap-1">
                <StatusIcon status={file.status} />

                {/* Retry button for failed files */}
                {file.status === "failed" && (
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6"
                        onClick={handleRetry}
                        disabled={isRetrying}
                        title="Retry"
                    >
                        <RotateCcw className={cn(
                            "h-3 w-3",
                            isRetrying && "animate-spin"
                        )} />
                    </Button>
                )}
            </div>
        </motion.div>
    );
}

/**
 * Files list for a single job
 */
/**
 * Job header with cancel button
 */
function JobHeader({ job, onCancel }: { job: IngestionJob; onCancel: (id: string) => void }) {
    const [isCancelling, setIsCancelling] = useState(false);
    const { toast } = useToast();
    const isActive = ["pending", "processing"].includes(job.status);

    const handleCancel = useCallback(async () => {
        if (!confirm("Cancel this ingestion? Files already processed will remain.")) return;
        setIsCancelling(true);

        try {
            await apiRequest(`/jobs/${job.id}/cancel`);
            toast({ title: "Job cancelled" });
            onCancel(job.id);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : "Failed to cancel";
            toast({ title: "Cancel failed", description: message, variant: "destructive" });
        } finally {
            setIsCancelling(false);
        }
    }, [job.id, toast, onCancel]);

    return (
        <div className="flex items-center justify-between mb-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
                <span className="capitalize font-medium">{job.provider}</span>
                <span>•</span>
                <span>{job.processed_files}/{job.total_files} complete</span>
            </div>
            {isActive && (
                <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 text-muted-foreground hover:text-destructive"
                    onClick={handleCancel}
                    disabled={isCancelling}
                    title="Cancel job"
                >
                    {isCancelling ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                        <StopCircle className="h-3 w-3" />
                    )}
                </Button>
            )}
        </div>
    );
}

/**
 * Files list for a single job
 */
function JobFilesList({ jobId }: { jobId: string }) {
    const { files, isLoading, refresh } = useFileStatus(jobId);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (files.length === 0) {
        return (
            <div className="text-center py-4 text-sm text-muted-foreground">
                No files in progress
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <AnimatePresence mode="popLayout">
                {files.map((file) => (
                    <FileStatusCard key={file.id} file={file} onRetry={refresh} />
                ))}
            </AnimatePresence>
        </div>
    );
}

/**
 * Main progress panel component
 */
export function IngestionProgressPanel() {
    const { activeJobs } = useIngestionJobs();
    const [isMinimized, setIsMinimized] = useState(false);
    const [isVisible, setIsVisible] = useState(true);

    // Auto-show when there are active jobs
    useEffect(() => {
        if (activeJobs.length > 0) {
            setIsVisible(true);
        }
    }, [activeJobs.length]);

    // Don't render if no active jobs or dismissed
    if (activeJobs.length === 0 || !isVisible) {
        return null;
    }

    const totalFiles = activeJobs.reduce((sum, job) => sum + job.total_files, 0);
    const processedFiles = activeJobs.reduce((sum, job) => sum + job.processed_files, 0);

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-4 right-4 z-50 w-[380px]"
        >
            <Card className="shadow-2xl border-primary/20 bg-card/95 backdrop-blur-sm">
                {/* Header */}
                <CardHeader className="p-3 border-b flex flex-row items-center justify-between">
                    <div className="flex items-center gap-2">
                        {processedFiles < totalFiles ? (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                        )}
                        <span className="font-semibold text-sm">
                            {processedFiles < totalFiles
                                ? `Ingesting ${processedFiles}/${totalFiles} files`
                                : `Completed ${totalFiles} files`
                            }
                        </span>
                    </div>

                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => setIsMinimized(!isMinimized)}
                            title={isMinimized ? "Expand" : "Minimize"}
                        >
                            {isMinimized ? (
                                <ChevronUp className="h-4 w-4" />
                            ) : (
                                <ChevronDown className="h-4 w-4" />
                            )}
                        </Button>
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6 text-muted-foreground hover:text-foreground"
                            onClick={() => setIsVisible(false)}
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                </CardHeader>

                {/* Content */}
                <AnimatePresence>
                    {!isMinimized && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                        >
                            <CardContent className="p-3 max-h-[400px] overflow-y-auto">
                                {activeJobs.map((job) => (
                                    <div key={job.id} className="mb-2 last:mb-0">
                                        <JobHeader
                                            job={job}
                                            onCancel={() => { /* Auto-updates via realtime */ }}
                                        />
                                        <JobFilesList jobId={job.id} />
                                    </div>
                                ))}
                            </CardContent>
                        </motion.div>
                    )}
                </AnimatePresence>
            </Card>
        </motion.div>
    );
}

export default IngestionProgressPanel;
