/**
 * Processing Stages Component
 * 
 * Shows the current stage of file processing with visual indicators.
 * Stages: Uploading → Parsing → Chunking → Embedding → Indexing
 */

import React from 'react';
import { Activity, Upload, FileText, Scissors, Sparkles, Database, CheckCircle2, Loader2, Clock, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

type Stage = 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'indexing';
type StageStatus = 'pending' | 'in_progress' | 'complete' | 'failed';

interface ProcessingStagesProps {
    currentStage: Stage;
    stages: Partial<Record<Stage, StageStatus>>;
    className?: string;
}

const stageConfig = {
    uploading: { label: 'Uploading', icon: Upload },
    parsing: { label: 'Parsing', icon: FileText },
    chunking: { label: 'Chunking', icon: Scissors },
    embedding: { label: 'Embedding', icon: Sparkles },
    indexing: { label: 'Indexing', icon: Database },
} as const;

function getStatusIcon(status: StageStatus) {
    switch (status) {
        case 'complete':
            return <CheckCircle2 className="h-4 w-4 text-green-500" />;
        case 'in_progress':
            return <Loader2 className="h-4 w-4 animate-spin text-primary" />;
        case 'failed':
            return <XCircle className="h-4 w-4 text-red-500" />;
        case 'pending':
        default:
            return <Clock className="h-4 w-4 text-muted-foreground" />;
    }
}

function getStatusLabel(status: StageStatus): string {
    switch (status) {
        case 'complete':
            return 'Complete';
        case 'in_progress':
            return 'In Progress';
        case 'failed':
            return 'Failed';
        case 'pending':
        default:
            return 'Pending';
    }
}

export function ProcessingStages({ currentStage, stages, className }: ProcessingStagesProps) {
    return (
        <div className={cn("space-y-2 p-3 rounded-lg bg-muted/30 border border-border/50", className)}>
            {/* Header */}
            <div className="flex items-center gap-2 mb-3">
                <Activity className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Processing Stages</span>
            </div>

            {/* Stage list */}
            <div className="space-y-2">
                {(Object.entries(stageConfig) as [Stage, typeof stageConfig[Stage]][]).map(([key, config]) => {
                    const status = stages[key] || 'pending';
                    const Icon = config.icon;
                    const isCurrent = key === currentStage;

                    return (
                        <div
                            key={key}
                            className={cn(
                                "flex items-center gap-3 p-2 rounded-md transition-colors",
                                isCurrent && "bg-primary/5"
                            )}
                        >
                            {/* Status icon */}
                            {getStatusIcon(status)}

                            {/* Stage icon and label */}
                            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                            <span
                                className={cn(
                                    "text-sm flex-1",
                                    status === 'complete' && "text-muted-foreground",
                                    status === 'in_progress' && "font-medium",
                                    status === 'pending' && "text-muted-foreground",
                                    status === 'failed' && "text-red-500"
                                )}
                            >
                                {config.label}
                            </span>

                            {/* Status label */}
                            <span className="text-xs text-muted-foreground tabular-nums">
                                {getStatusLabel(status)}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
