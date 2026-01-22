"use client";

/**
 * IngestionProgressModal - Per-file progress display
 * 
 * OPTIMIZATIONS:
 * - FileProgressCard is memoized to prevent re-renders when other files update
 * - useMemo for derived calculations (completedFiles, etc.)
 * - onComplete callback is debounced to prevent multiple triggers
 */

import { useState, useEffect, useRef, memo, useMemo, useCallback } from "react";
import { ChevronDown, ChevronUp, X, FileText, Loader2, CheckCircle2, XCircle, Clock, SkipForward } from "lucide-react";
import { cn } from "@/lib/utils";
import { FileStatus, getStatusLabel } from "@/hooks/useFileStatus";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Collapsible, CollapsibleContent } from "@/components/ui/collapsible";
import { ChunkProgress } from "./ChunkProgress";
import { ProcessingStages } from "./ProcessingStages";
import { ErrorDetails } from "./ErrorDetails";
import { RetryStatus } from "./RetryStatus";
import {
    announceToScreenReader,
    KeyboardShortcuts,
    FocusTrap,
    getProgressLabel,
    getFileStatusLabel
} from "@/lib/accessibility";

interface IngestionProgressModalProps {
    jobId: string;
    files: FileStatus[];
    totalFiles: number;
    overallProgress: number;
    onClose: () => void;
    /** Called once when all files reach a terminal state (completed/failed/skipped) */
    onComplete?: () => void;
}

export function IngestionProgressModal({
    jobId,
    files,
    totalFiles,
    overallProgress,
    onClose,
    onComplete,
}: IngestionProgressModalProps) {
    const [isExpanded, setIsExpanded] = useState(true);
    const modalRef = useRef<HTMLDivElement>(null);
    const keyboardShortcuts = useRef<KeyboardShortcuts | null>(null);
    const focusTrap = useRef<FocusTrap | null>(null);
    const hasCalledComplete = useRef(false);
    const completeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    /**
     * MEMOIZED DERIVED VALUES
     * Prevents recalculation on every render
     */
    const { completedFiles, failedFiles, skippedFiles, processingFiles, allComplete } = useMemo(() => {
        const isSkippedStatus = (status: string) => status.startsWith("skipped");
        
        const completed = files.filter((f) => f.status === "completed" || f.status === "indexed").length;
        const failed = files.filter((f) => f.status === "failed").length;
        const skipped = files.filter((f) => isSkippedStatus(f.status)).length;
        const processing = files.filter((f) => {
            if (isSkippedStatus(f.status)) return false;
            return !["completed", "indexed", "failed", "cancelled"].includes(f.status);
        }).length;

        return {
            completedFiles: completed,
            failedFiles: failed,
            skippedFiles: skipped,
            processingFiles: processing,
            allComplete: totalFiles > 0 && completed + failed + skipped === totalFiles,
        };
    }, [files, totalFiles]);

    /**
     * Memoized close handler
     */
    const handleClose = useCallback(() => {
        onClose();
    }, [onClose]);

    /**
     * Memoized expand toggle
     */
    const toggleExpand = useCallback(() => {
        setIsExpanded((prev) => !prev);
    }, []);

    // Setup keyboard shortcuts and focus trap
    useEffect(() => {
        if (!modalRef.current) return;

        const shortcuts = new KeyboardShortcuts();
        shortcuts.register('escape', handleClose);
        shortcuts.register('ctrl+e', toggleExpand);
        shortcuts.start();
        keyboardShortcuts.current = shortcuts;

        const trap = new FocusTrap(modalRef.current);
        trap.activate();
        focusTrap.current = trap;

        announceToScreenReader('File processing progress modal opened', 'polite');

        return () => {
            shortcuts.stop();
            trap.deactivate();
        };
    }, [handleClose, toggleExpand]);

    // Trigger completion callback ONCE when all files finish
    useEffect(() => {
        if (allComplete && !hasCalledComplete.current && onComplete) {
            hasCalledComplete.current = true;
            
            announceToScreenReader(
                `Processing complete. ${completedFiles} files completed${failedFiles > 0 ? `, ${failedFiles} failed` : ''}`,
                'assertive'
            );
            
            // Debounced completion callback - prevents double triggers
            if (completeTimeoutRef.current) {
                clearTimeout(completeTimeoutRef.current);
            }
            
            completeTimeoutRef.current = setTimeout(() => {
                onComplete();
                completeTimeoutRef.current = null;
            }, 500);
        }

        return () => {
            if (completeTimeoutRef.current) {
                clearTimeout(completeTimeoutRef.current);
            }
        };
    }, [allComplete, completedFiles, failedFiles, onComplete]);

    return (
        <div
            ref={modalRef}
            className="fixed bottom-4 right-4 z-50 w-[420px] max-w-[92vw] shadow-2xl animate-slide-in"
            role="dialog"
            aria-modal="true"
            aria-labelledby="progress-modal-title"
            aria-describedby="progress-modal-description"
        >
            <Card className="border border-border/60 bg-card/95 backdrop-blur-md rounded-2xl overflow-hidden shadow-[0_20px_60px_-28px_rgba(0,0,0,0.65)] ring-1 ring-white/5">
                {/* Header - Always Visible */}
                <div className="flex items-center justify-between border-b bg-gradient-to-r from-muted/70 via-muted/30 to-transparent p-4">
                    <div className="flex items-center gap-3 flex-1">
                        <div className="relative">
                            {allComplete ? (
                                <CheckCircle2 className="h-5 w-5 text-green-500" />
                            ) : (
                                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                            )}
                        </div>
                        <div className="flex-1">
                            <h3 className="text-sm font-semibold tracking-tight">
                                {allComplete
                                    ? "Processing Complete"
                                    : `Processing ${processingFiles} ${processingFiles === 1 ? "file" : "files"}...`}
                            </h3>
                            <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px]">
                                <span className="rounded-full border border-green-500/20 bg-green-500/10 px-2 py-0.5 text-green-400">
                                    {completedFiles}/{totalFiles} completed
                                </span>
                                {failedFiles > 0 && (
                                    <span className="rounded-full border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-red-400">
                                        {failedFiles} failed
                                    </span>
                                )}
                                {skippedFiles > 0 && (
                                    <span className="rounded-full border border-amber-500/20 bg-amber-500/10 px-2 py-0.5 text-amber-400">
                                        {skippedFiles} skipped
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => setIsExpanded(!isExpanded)}
                            aria-label={isExpanded ? "Collapse" : "Expand"}
                        >
                            {isExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                            ) : (
                                <ChevronUp className="h-4 w-4" />
                            )}
                        </Button>
                        {allComplete && (
                            <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8"
                                onClick={onClose}
                                aria-label="Close"
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>

                {/* Overall Progress Bar */}
                <div className="px-4 py-3 border-b bg-background/60">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium">Overall Progress</span>
                        <span className="text-xs text-muted-foreground tabular-nums">{Math.round(overallProgress)}%</span>
                    </div>
                    <Progress
                        value={overallProgress}
                        className="h-2.5 transition-all duration-300"
                        aria-label={getProgressLabel(Math.round(overallProgress), "Overall progress")}
                    />
                </div>

                {/* Expandable File List */}
                {isExpanded && (
                    <div className="max-h-96 overflow-y-auto">
                        {files.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground">
                                <Clock className="h-8 w-8 mx-auto mb-2 opacity-50" />
                                <p>Preparing files...</p>
                            </div>
                        ) : (
                            <div className="divide-y">
                                {files.map((file) => (
                                    <FileProgressCard key={file.id} file={file} jobId={jobId} />
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </Card>
        </div>
    );
}

interface FileProgressCardProps {
    file: FileStatus;
    jobId: string;
}

type ProcessingStage = "uploading" | "parsing" | "chunking" | "embedding" | "indexing";
type StageStatus = "pending" | "in_progress" | "complete" | "failed";

/**
 * MEMOIZED FileProgressCard
 * 
 * Only re-renders when the specific file's data changes, not when
 * sibling files update. This is critical for performance when
 * processing many files simultaneously.
 */
const FileProgressCard = memo(function FileProgressCard({ file, jobId }: FileProgressCardProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const statusLabel = getStatusLabel(file.status);
    const isSkipped = file.status.startsWith("skipped");
    const isProcessing = !["completed", "indexed", "failed", "cancelled"].includes(file.status) && !isSkipped;
    const isFailed = file.status === "failed";
    const isCompleted = file.status === "completed" || file.status === "indexed";
    const isUnsupported = file.status === "skipped_unsupported" || file.status === "skipped_file_too_large";
    const isCancelled = file.status === "cancelled";
    const hasChunks = file.chunks_total > 0;
    const hasError = !!file.error_message;

    const statusPillClass = cn(
        "text-[11px] font-semibold px-2 py-0.5 rounded-full border",
        isCompleted && "text-green-400 border-green-500/25 bg-green-500/10",
        isFailed && "text-red-400 border-red-500/25 bg-red-500/10",
        isUnsupported && "text-orange-400 border-orange-500/25 bg-orange-500/10",
        isSkipped && !isUnsupported && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isCancelled && "text-amber-400 border-amber-500/25 bg-amber-500/10",
        isProcessing && "text-primary border-primary/25 bg-primary/10"
    );

    // Determine processing stages based on status
    const getProcessingStages = (): Record<ProcessingStage, StageStatus> => {
        const stages: Record<ProcessingStage, StageStatus> = {
            uploading: 'pending',
            parsing: 'pending',
            chunking: 'pending',
            embedding: 'pending',
            indexing: 'pending',
        };

        if (file.status === 'uploading') {
            stages.uploading = 'in_progress';
        } else if (file.status === 'parsing' || file.status === 'processing') {
            stages.uploading = 'complete';
            stages.parsing = 'in_progress';
            stages.chunking = 'in_progress';
        } else if (file.status === 'embedding') {
            stages.uploading = 'complete';
            stages.parsing = 'complete';
            stages.chunking = 'complete';
            stages.embedding = 'in_progress';
        } else if (file.status === 'indexing') {
            stages.uploading = 'complete';
            stages.parsing = 'complete';
            stages.chunking = 'complete';
            stages.embedding = 'complete';
            stages.indexing = 'in_progress';
        } else if (file.status === 'completed' || file.status === 'indexed' || isSkipped) {
            stages.uploading = 'complete';
            stages.parsing = 'complete';
            stages.chunking = 'complete';
            stages.embedding = 'complete';
            stages.indexing = 'complete';
        } else if (file.status === 'failed') {
            if (file.status_message?.toLowerCase().includes('index')) {
                stages.indexing = 'failed';
            } else if (file.status_message?.toLowerCase().includes('embed')) {
                stages.embedding = 'failed';
            } else if (file.status_message?.toLowerCase().includes('parse')) {
                stages.parsing = 'failed';
            } else if (file.status_message?.toLowerCase().includes('upload')) {
                stages.uploading = 'failed';
            }
        }

        return stages;
    };

    const getCurrentStage = (): ProcessingStage => {
        if (file.status === 'uploading') return 'uploading';
        if (file.status === 'parsing' || file.status === 'processing') return 'parsing';
        if (file.status === 'embedding') return 'embedding';
        if (file.status === 'indexing' || file.status === 'indexed') return 'indexing';
        return 'parsing';
    };

    return (
        <div
            className={cn(
                "p-4 transition-colors",
                isCompleted && "bg-green-500/5",
                isFailed && "bg-red-500/5",
                isUnsupported && "bg-orange-500/5",
                isSkipped && !isUnsupported && "bg-amber-500/5",
                isCancelled && "bg-amber-500/5",
                !isCompleted && !isFailed && !isSkipped && !isCancelled && "hover:bg-muted/40"
            )}
            aria-label={getFileStatusLabel(file.status, file.filename)}
        >
            <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="mt-0.5">
                    {isCompleted ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : isUnsupported ? (
                        <SkipForward className="h-4 w-4 text-orange-500" />
                    ) : isSkipped ? (
                        <SkipForward className="h-4 w-4 text-amber-500" />
                    ) : isFailed ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                    ) : (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-2">
                    {/* Filename and basic info */}
                    <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate" title={file.filename}>
                                {file.filename}
                            </p>
                            <div className="flex items-center gap-2 mt-1">
                                <span className={statusPillClass}>
                                    {statusLabel}
                                </span>
                                {file.file_size_bytes > 0 && (
                                    <>
                                        <span className="text-xs text-muted-foreground">•</span>
                                        <span className="text-xs text-muted-foreground">
                                            {formatBytes(file.file_size_bytes)}
                                        </span>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Expand button (only if has details to show) */}
                        {(isProcessing && hasChunks) || isFailed ? (
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0"
                                onClick={() => setIsExpanded(!isExpanded)}
                                aria-label={isExpanded ? "Collapse details" : "Expand details"}
                            >
                                {isExpanded ? (
                                    <ChevronUp className="h-3 w-3" />
                                ) : (
                                    <ChevronDown className="h-3 w-3" />
                                )}
                            </Button>
                        ) : null}
                    </div>

                    {/* Progress Bar (only for active files) */}
                    {isProcessing && file.progress > 0 && (
                        <div>
                            <div className="flex items-center justify-between text-[11px] text-muted-foreground mb-1">
                                <span>{file.status_message || "Processing..."}</span>
                                <span className="tabular-nums">{file.progress}%</span>
                            </div>
                            <Progress
                                value={file.progress}
                                className="h-1.5 transition-all duration-300"
                                aria-label={getProgressLabel(file.progress, `${file.filename} progress`)}
                            />
                        </div>
                    )}

                    {/* Status Message */}
                    {file.status_message && (!isExpanded || isSkipped || isFailed) && (
                        <p className={cn(
                            "text-xs line-clamp-2",
                            isUnsupported ? "text-orange-400" : isSkipped ? "text-amber-400" : "text-muted-foreground"
                        )}>
                            {file.status_message}
                        </p>
                    )}

                    {/* Error Message (collapsed) */}
                    {hasError && !isExpanded && (
                        <p className="text-xs text-red-500 line-clamp-1">
                            {file.error_message}
                        </p>
                    )}

                    {/* Chunk count (collapsed) */}
                    {hasChunks && !isExpanded && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <FileText className="h-3 w-3" />
                            <span className="tabular-nums">
                                {file.chunks_processed}/{file.chunks_total} chunks
                            </span>
                        </div>
                    )}

                    {/* Expandable Details */}
                    <Collapsible open={isExpanded}>
                        <CollapsibleContent className="space-y-3 pt-2 animate-accordion-down">
                            {/* Processing file details */}
                            {isProcessing && hasChunks && (
                                <>
                                    <ChunkProgress
                                        processed={file.chunks_processed}
                                        total={file.chunks_total}
                                    />

                                    <ProcessingStages
                                        currentStage={getCurrentStage()}
                                        stages={getProcessingStages()}
                                    />
                                </>
                            )}

                            {/* Failed file details */}
                            {isFailed && hasError && (
                                <>
                                    <ErrorDetails
                                        error={{
                                            type: file.error_message?.split(':')[0] || 'Error',
                                            message: file.error_message || 'An error occurred',
                                            timestamp: file.updated_at,
                                        }}
                                    />

                                    {/* Retry Status Integration */}
                                    <div className="pt-2">
                                        <RetryStatus jobId={jobId} />
                                    </div>
                                </>
                            )}
                        </CollapsibleContent>
                    </Collapsible>
                </div>
            </div>
        </div>
    );
});

function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
