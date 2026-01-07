/**
 * Chunk Progress Component
 * 
 * Visual representation of chunk-level processing progress.
 * Shows progress bar, percentage, and chunk counts.
 */

import React from 'react';
import { FileText } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface ChunkProgressProps {
    processed: number;
    total: number;
    className?: string;
}

export function ChunkProgress({ processed, total, className }: ChunkProgressProps) {
    const percentage = total > 0 ? Math.round((processed / total) * 100) : 0;
    const remaining = total - processed;

    return (
        <div className={cn("space-y-2 p-3 rounded-lg bg-muted/20 border border-border/50", className)}>
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">Chunk Progress</span>
                </div>
                <span className="text-sm font-semibold tabular-nums">{percentage}%</span>
            </div>

            {/* Visual progress bar */}
            <Progress value={percentage} className="h-2.5" />

            {/* Text details */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="tabular-nums">
                    <span className="font-medium text-foreground">{processed}</span> of {total} chunks processed
                </span>
                {processed > 0 && remaining > 0 && (
                    <span className="tabular-nums">{remaining} remaining</span>
                )}
            </div>
        </div>
    );
}
