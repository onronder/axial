"use client";

import { HardDrive, Files } from "lucide-react";
import { useUsage, formatBytes } from "@/hooks/useUsage";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

/**
 * Color coding thresholds for usage indicators
 */
const getColorClass = (percent: number): string => {
    if (percent >= 90) return "bg-destructive";
    if (percent >= 75) return "bg-warning";
    return "bg-success";
};

const getTextColorClass = (percent: number): string => {
    if (percent >= 90) return "text-destructive";
    if (percent >= 75) return "text-warning";
    return "text-success";
};

/**
 * Custom colored progress bar component
 */
function ColoredProgressBar({ value, colorClass }: { value: number; colorClass: string }) {
    return (
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-secondary">
            <div
                className={cn("h-full transition-all duration-300", colorClass)}
                style={{ width: `${Math.min(100, Math.max(0, value))}%` }}
            />
        </div>
    );
}

/**
 * UsageIndicator - compact usage display for sidebar
 * 
 * Shows file count and storage usage with color-coded progress bars.
 * Enterprise users see "Unlimited" instead of limits.
 */
export function UsageIndicator() {
    const {
        plan,
        filesUsed,
        filesLimit,
        filesPercent,
        storageUsed,
        storageLimit,
        storagePercent,
        isLoading,
    } = useUsage();

    // Enterprise users have unlimited resources
    const isEnterprise = plan === "enterprise";

    if (isLoading) {
        return (
            <div className="px-3 py-2 space-y-2">
                <div className="h-4 bg-muted animate-pulse rounded" />
                <div className="h-4 bg-muted animate-pulse rounded" />
            </div>
        );
    }

    // Enterprise: show simplified "Unlimited" UI
    if (isEnterprise) {
        return (
            <div className="px-3 py-3 border-t border-border/50">
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="font-medium text-success">Enterprise</span>
                    <span>•</span>
                    <span>Unlimited resources</span>
                </div>
            </div>
        );
    }

    return (
        <div className="px-3 py-3 space-y-3 border-t border-border/50">
            {/* Files Usage */}
            <Tooltip>
                <TooltipTrigger asChild>
                    <div className="space-y-1.5 cursor-default">
                        <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                                <Files className="h-3 w-3" />
                                <span>Files</span>
                            </div>
                            <span className={cn("font-medium", getTextColorClass(filesPercent))}>
                                {filesUsed}/{filesLimit}
                            </span>
                        </div>
                        <ColoredProgressBar
                            value={filesPercent}
                            colorClass={getColorClass(filesPercent)}
                        />
                    </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                    <p>{filesUsed} of {filesLimit} files used ({Math.round(filesPercent)}%)</p>
                </TooltipContent>
            </Tooltip>

            {/* Storage Usage */}
            <Tooltip>
                <TooltipTrigger asChild>
                    <div className="space-y-1.5 cursor-default">
                        <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1.5 text-muted-foreground">
                                <HardDrive className="h-3 w-3" />
                                <span>Storage</span>
                            </div>
                            <span className={cn("font-medium", getTextColorClass(storagePercent))}>
                                {formatBytes(storageUsed)}/{formatBytes(storageLimit)}
                            </span>
                        </div>
                        <ColoredProgressBar
                            value={storagePercent}
                            colorClass={getColorClass(storagePercent)}
                        />
                    </div>
                </TooltipTrigger>
                <TooltipContent side="right">
                    <p>{formatBytes(storageUsed)} of {formatBytes(storageLimit)} used ({Math.round(storagePercent)}%)</p>
                </TooltipContent>
            </Tooltip>
        </div>
    );
}

/**
 * UsageIndicatorCompact - minimal version for mobile/narrow spaces
 */
export function UsageIndicatorCompact() {
    const { filesPercent, storagePercent, plan, isLoading } = useUsage();

    if (isLoading || plan === "enterprise") return null;

    const worstPercent = Math.max(filesPercent, storagePercent);

    return (
        <Tooltip>
            <TooltipTrigger asChild>
                <div className={cn(
                    "w-2 h-2 rounded-full",
                    getColorClass(worstPercent)
                )} />
            </TooltipTrigger>
            <TooltipContent>
                <p>Files: {Math.round(filesPercent)}% • Storage: {Math.round(storagePercent)}%</p>
            </TooltipContent>
        </Tooltip>
    );
}
