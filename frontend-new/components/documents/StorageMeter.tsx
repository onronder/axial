"use client";

/**
 * Storage Meter Component
 * 
 * Displays file count and storage usage with color-coded progress bars.
 * Shows warnings at 75% and 90% thresholds.
 */

import { HardDrive, Files, AlertTriangle, TrendingUp } from "lucide-react";
import { useUsage, formatBytes } from "@/hooks/useUsage";
import { Progress } from "@/components/ui/progress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface StorageMeterProps {
    className?: string;
    showUpgradePrompt?: boolean;
}

/**
 * Get color class based on usage percentage
 */
const getColorClass = (percent: number): string => {
    if (percent >= 90) return "text-destructive";
    if (percent >= 75) return "text-warning";
    return "text-success";
};

const getProgressColor = (percent: number): string => {
    if (percent >= 90) return "bg-destructive";
    if (percent >= 75) return "bg-warning";
    return "bg-success";
};

const getStatusText = (percent: number): string => {
    if (percent >= 100) return "Limit Reached";
    if (percent >= 90) return "Critical";
    if (percent >= 75) return "Approaching Limit";
    return "Healthy";
};

export function StorageMeter({ className, showUpgradePrompt = true }: StorageMeterProps) {
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

    if (isLoading) {
        return (
            <Card className={cn("animate-pulse", className)}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg">Storage Usage</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="h-4 bg-muted rounded" />
                    <div className="h-4 bg-muted rounded" />
                </CardContent>
            </Card>
        );
    }

    // Enterprise users have unlimited storage
    if (plan === "enterprise") {
        return (
            <Card className={cn("border-success/20 bg-success/5", className)}>
                <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <HardDrive className="h-5 w-5 text-success" />
                        Storage Usage
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-2 text-success">
                        <span className="text-2xl font-bold">Unlimited</span>
                        <span className="text-sm text-muted-foreground">Enterprise Plan</span>
                    </div>
                    <div className="mt-2 text-sm text-muted-foreground">
                        Files: {filesUsed.toLocaleString()} • Storage: {formatBytes(storageUsed)}
                    </div>
                </CardContent>
            </Card>
        );
    }

    const worstPercent = Math.max(filesPercent, storagePercent);
    const showWarning = worstPercent >= 75;
    const showCritical = worstPercent >= 90;

    return (
        <Card className={cn(
            showCritical ? "border-destructive/30 bg-destructive/5" :
                showWarning ? "border-warning/30 bg-warning/5" : "",
            className
        )}>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <HardDrive className="h-5 w-5" />
                        Storage Usage
                    </CardTitle>
                    <span className={cn(
                        "text-xs font-medium px-2 py-1 rounded-full",
                        showCritical ? "bg-destructive/10 text-destructive" :
                            showWarning ? "bg-warning/10 text-warning" :
                                "bg-success/10 text-success"
                    )}>
                        {getStatusText(worstPercent)}
                    </span>
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {/* Files Usage */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <Files className="h-4 w-4" />
                            <span>Files</span>
                        </div>
                        <span className={cn("font-medium", getColorClass(filesPercent))}>
                            {filesUsed} / {filesLimit}
                        </span>
                    </div>
                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
                        <div
                            className={cn("h-full transition-all duration-500", getProgressColor(filesPercent))}
                            style={{ width: `${Math.min(100, filesPercent)}%` }}
                        />
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {Math.round(filesPercent)}% used
                    </p>
                </div>

                {/* Storage Usage */}
                <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                        <div className="flex items-center gap-2 text-muted-foreground">
                            <HardDrive className="h-4 w-4" />
                            <span>Storage</span>
                        </div>
                        <span className={cn("font-medium", getColorClass(storagePercent))}>
                            {formatBytes(storageUsed)} / {formatBytes(storageLimit)}
                        </span>
                    </div>
                    <div className="relative h-2 w-full overflow-hidden rounded-full bg-secondary">
                        <div
                            className={cn("h-full transition-all duration-500", getProgressColor(storagePercent))}
                            style={{ width: `${Math.min(100, storagePercent)}%` }}
                        />
                    </div>
                    <p className="text-xs text-muted-foreground">
                        {Math.round(storagePercent)}% used
                    </p>
                </div>

                {/* Warning Message */}
                {showWarning && showUpgradePrompt && (
                    <Alert variant={showCritical ? "destructive" : "default"} className="mt-4">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription className="flex items-center justify-between">
                            <span>
                                {showCritical
                                    ? "You've almost reached your limit!"
                                    : "You're approaching your storage limit."}
                            </span>
                            <Button asChild size="sm" variant={showCritical ? "destructive" : "default"}>
                                <Link href="/dashboard/settings/billing">
                                    <TrendingUp className="h-4 w-4 mr-1" />
                                    Upgrade
                                </Link>
                            </Button>
                        </AlertDescription>
                    </Alert>
                )}
            </CardContent>
        </Card>
    );
}

/**
 * Compact version for sidebar or inline use
 */
export function StorageMeterCompact({ className }: { className?: string }) {
    const { filesPercent, storagePercent, plan, isLoading } = useUsage();

    if (isLoading || plan === "enterprise") return null;

    const worstPercent = Math.max(filesPercent, storagePercent);

    return (
        <div className={cn("flex items-center gap-2", className)}>
            <div className={cn(
                "h-2 w-2 rounded-full",
                getProgressColor(worstPercent)
            )} />
            <span className={cn("text-xs", getColorClass(worstPercent))}>
                {Math.round(worstPercent)}% used
            </span>
        </div>
    );
}
