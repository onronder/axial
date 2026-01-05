"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, X, FileText, Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { FileStatus, getStatusLabel, getStatusColor } from "@/hooks/useFileStatus";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface IngestionProgressModalProps {
    jobId: string;
    files: FileStatus[];
    totalFiles: number;
    overallProgress: number;
    onClose: () => void;
}

export function IngestionProgressModal({
    jobId,
    files,
    totalFiles,
    overallProgress,
    onClose,
}: IngestionProgressModalProps) {
    const [isExpanded, setIsExpanded] = useState(true);

    const completedFiles = files.filter((f) => f.status === "completed").length;
    const failedFiles = files.filter((f) => f.status === "failed").length;
    const processingFiles = files.filter(
        (f) => !["completed", "failed", "cancelled"].includes(f.status)
    ).length;

    const allComplete = completedFiles + failedFiles === totalFiles;

    return (
        <div className="fixed bottom-4 right-4 z-50 w-96 shadow-2xl">
            <Card className="border-2">
                {/* Header - Always Visible */}
                <div className="flex items-center justify-between border-b bg-muted/30 p-4">
                    <div className="flex items-center gap-3 flex-1">
                        <div className="relative">
                            {allComplete ? (
                                <CheckCircle2 className="h-5 w-5 text-green-500" />
                            ) : (
                                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                            )}
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-sm">
                                {allComplete
                                    ? "Processing Complete"
                                    : `Processing ${processingFiles} ${processingFiles === 1 ? "file" : "files"}...`}
                            </h3>
                            <p className="text-xs text-muted-foreground">
                                {completedFiles}/{totalFiles} completed
                                {failedFiles > 0 && ` • ${failedFiles} failed`}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-1">
                        <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => setIsExpanded(!isExpanded)}
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
                            >
                                <X className="h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>

                {/* Overall Progress Bar */}
                <div className="px-4 py-3 border-b bg-background">
                    <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium">Overall Progress</span>
                        <span className="text-xs text-muted-foreground">{Math.round(overallProgress)}%</span>
                    </div>
                    <Progress value={overallProgress} className="h-2" />
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
                                    <FileProgressCard key={file.id} file={file} />
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
}

function FileProgressCard({ file }: FileProgressCardProps) {
    const statusColor = getStatusColor(file.status);
    const statusLabel = getStatusLabel(file.status);
    const isProcessing = !["completed", "failed", "cancelled"].includes(file.status);

    return (
        <div className="p-4 hover:bg-muted/30 transition-colors">
            <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="mt-0.5">
                    {file.status === "completed" ? (
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : file.status === "failed" ? (
                        <XCircle className="h-4 w-4 text-red-500" />
                    ) : (
                        <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-2">
                    {/* Filename */}
                    <div>
                        <p className="text-sm font-medium truncate" title={file.filename}>
                            {file.filename}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                            <span className={cn("text-xs font-medium", statusColor)}>
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

                    {/* Progress Bar (only for active files) */}
                    {isProcessing && file.progress > 0 && (
                        <div>
                            <Progress value={file.progress} className="h-1.5" />
                        </div>
                    )}

                    {/* Status Message */}
                    {file.status_message && (
                        <p className="text-xs text-muted-foreground line-clamp-2">
                            {file.status_message}
                        </p>
                    )}

                    {/* Error Message */}
                    {file.error_message && (
                        <p className="text-xs text-red-500 line-clamp-2">
                            {file.error_message}
                        </p>
                    )}

                    {/* Chunk Progress (if available) */}
                    {file.chunks_total > 0 && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <FileText className="h-3 w-3" />
                            <span>
                                {file.chunks_processed}/{file.chunks_total} chunks
                            </span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
