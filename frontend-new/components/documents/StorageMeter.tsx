"use client";

/**
 * Storage Meter Component
 * 
 * Displays file count and storage usage with premium visuals.
 * Features circular progress for desktop and refined indicators.
 */

import { HardDrive, Files, Database, ArrowUpRight, CheckCircle2, AlertTriangle, Cloud } from "lucide-react";
import { useUsage, formatBytes } from "@/hooks/useUsage";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface StorageMeterProps {
    className?: string;
    showUpgradePrompt?: boolean;
    variant?: 'vertical' | 'horizontal';
}

export function StorageMeter({ className, showUpgradePrompt = true, variant = 'vertical' }: StorageMeterProps) {
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
            <Card className={cn("animate-pulse border-border/50",
                variant === 'vertical' ? "h-full" : "w-full",
                className
            )}>
                <CardContent className={cn("p-6", variant === 'horizontal' && "flex items-center gap-4")}>
                    <div className="h-12 w-12 bg-muted rounded-full" />
                    <div className="space-y-2 flex-1">
                        <div className="h-4 w-32 bg-muted rounded" />
                        <div className="h-3 w-48 bg-muted rounded" />
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Enterprise users have unlimited storage
    if (plan === "enterprise") {
        if (variant === 'horizontal') {
            return (
                <Card className={cn("border-emerald-500/20 bg-emerald-500/5", className)}>
                    <CardContent className="p-6 flex items-center justify-between gap-6">
                        <div className="flex items-center gap-4">
                            <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
                                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
                            </div>
                            <div>
                                <h3 className="text-lg font-bold text-emerald-950">Unlimited Storage Active</h3>
                                <p className="text-emerald-700/80 text-sm">
                                    Enterprise plan includes unlimited file storage and indexing.
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-8 text-sm">
                            <div>
                                <span className="text-muted-foreground mr-2">Files:</span>
                                <span className="font-bold text-emerald-900">{filesUsed.toLocaleString()}</span>
                            </div>
                            <div>
                                <span className="text-muted-foreground mr-2">Used:</span>
                                <span className="font-bold text-emerald-900">{formatBytes(storageUsed)}</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            );
        }

        return (
            <Card className={cn("border-emerald-500/20 bg-emerald-500/5 h-full", className)}>
                <CardContent className="pt-6 flex flex-col items-center text-center h-full justify-center">
                    <div className="h-16 w-16 rounded-full bg-emerald-500/10 flex items-center justify-center mb-4">
                        <CheckCircle2 className="h-8 w-8 text-emerald-600" />
                    </div>
                    <h3 className="text-xl font-bold text-emerald-950 mb-1">Unlimited Storage</h3>
                    <p className="text-emerald-700/80 mb-4 text-sm max-w-[200px]">
                        Your Enterprise plan includes unlimited file storage and indexing.
                    </p>
                    <div className="grid grid-cols-2 gap-4 w-full mt-4">
                        <div className="bg-background/50 p-3 rounded-lg border border-emerald-500/10">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Files</div>
                            <div className="text-lg font-bold text-emerald-900">{filesUsed.toLocaleString()}</div>
                        </div>
                        <div className="bg-background/50 p-3 rounded-lg border border-emerald-500/10">
                            <div className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Size</div>
                            <div className="text-lg font-bold text-emerald-900">{formatBytes(storageUsed)}</div>
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    const worstPercent = Math.max(filesPercent, storagePercent);
    const isCritical = worstPercent >= 90;
    const isWarning = worstPercent >= 75;

    // Horizontal Variant (Banner style)
    if (variant === 'horizontal') {
        return (
            <Card className={cn("overflow-hidden border-border/60 shadow-sm", className)}>
                <CardContent className="p-6">
                    <div className="flex flex-col md:flex-row md:items-center gap-6 justify-between">
                        {/* Left: Status & Icon */}
                        <div className="flex items-center gap-4 min-w-[240px]">
                            <div className="relative h-14 w-14 shrink-0">
                                {/* Circular Chart Small */}
                                <svg className="h-full w-full rotate-[-90deg]" viewBox="0 0 100 100">
                                    <circle className="text-muted/20" strokeWidth="10" stroke="currentColor" fill="transparent" r="40" cx="50" cy="50" />
                                    <circle
                                        className={cn("transition-all duration-1000 ease-out", isCritical ? "text-red-500" : isWarning ? "text-amber-500" : "text-primary")}
                                        strokeWidth="10"
                                        strokeDasharray={2 * Math.PI * 40}
                                        strokeDashoffset={(2 * Math.PI * 40) - (Math.min(100, worstPercent) / 100) * (2 * Math.PI * 40)}
                                        strokeLinecap="round" stroke="currentColor" fill="transparent" r="40" cx="50" cy="50"
                                    />
                                </svg>
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <span className={cn("text-sm font-bold", isCritical ? "text-red-600" : isWarning ? "text-amber-600" : "text-primary")}>
                                        {Math.round(worstPercent)}%
                                    </span>
                                </div>
                            </div>
                            <div>
                                <h3 className="font-semibold text-lg text-foreground">Storage Status</h3>
                                <p className="text-sm text-muted-foreground">
                                    {isCritical ? "Plan limits reached" : isWarning ? "Approaching limits" : "Healthy usage"}
                                </p>
                            </div>
                        </div>

                        {/* Middle: Bars */}
                        <div className="flex-1 space-y-4 max-w-2xl px-4 border-l border-r border-border/40 mx-4 hidden md:block">
                            <div className="space-y-1.5">
                                <div className="flex justify-between text-xs font-medium">
                                    <span className="flex items-center gap-1.5 text-muted-foreground">
                                        <Database className="h-3.5 w-3.5" /> Storage
                                    </span>
                                    <span>{formatBytes(storageUsed)} / {formatBytes(storageLimit)}</span>
                                </div>
                                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className={cn("h-full rounded-full transition-all duration-500", storagePercent > 90 ? "bg-red-500" : "bg-primary")}
                                        style={{ width: `${Math.min(100, storagePercent)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="space-y-1.5">
                                <div className="flex justify-between text-xs font-medium">
                                    <span className="flex items-center gap-1.5 text-muted-foreground">
                                        <Files className="h-3.5 w-3.5" /> Files
                                    </span>
                                    <span>{filesUsed} / {filesLimit}</span>
                                </div>
                                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                                    <div
                                        className={cn("h-full rounded-full transition-all duration-500", filesPercent > 90 ? "bg-red-500" : "bg-blue-500")}
                                        style={{ width: `${Math.min(100, filesPercent)}%` }}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* Right: Action */}
                        <div className="flex flex-col gap-2 min-w-[160px] items-center md:items-end justify-center">
                            {showUpgradePrompt && (isWarning || isCritical) ? (
                                <>
                                    <Button size="default" variant={isCritical ? "destructive" : "default"} asChild className="w-full">
                                        <Link href="/dashboard/settings/billing">
                                            Upgrade Plan <ArrowUpRight className="ml-2 h-4 w-4" />
                                        </Link>
                                    </Button>
                                    <p className="text-xs text-muted-foreground text-center md:text-right">
                                        {isCritical ? "Unlock more storage" : "Get ahead of your limits"}
                                    </p>
                                </>
                            ) : (
                                <Button variant="outline" asChild className="w-full">
                                    <Link href="/dashboard/settings/billing">
                                        Manage Plan
                                    </Link>
                                </Button>
                            )}
                        </div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    // Default Vertical Layout
    const radius = 36;
    const circumference = 2 * Math.PI * radius;
    const fileOffset = circumference - (Math.min(100, filesPercent) / 100) * circumference;
    const storageOffset = circumference - (Math.min(100, storagePercent) / 100) * circumference;

    return (
        <Card className={cn("h-full overflow-hidden border-border/60", className)}>
            <CardHeader className="pb-2">
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                    <Database className="h-4 w-4 text-primary" />
                    Storage Status
                </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="flex items-center gap-6">
                    {/* Circular Chart */}
                    <div className="relative h-24 w-24 shrink-0">
                        {/* Background Circle */}
                        <svg className="h-full w-full rotate-[-90deg]" viewBox="0 0 100 100">
                            <circle
                                className="text-muted/20"
                                strokeWidth="8"
                                stroke="currentColor"
                                fill="transparent"
                                r={radius}
                                cx="50"
                                cy="50"
                            />
                            {/* Storage Ring (Outer) */}
                            <circle
                                className={cn(
                                    "transition-all duration-1000 ease-out",
                                    isCritical ? "text-red-500" : isWarning ? "text-amber-500" : "text-primary"
                                )}
                                strokeWidth="8"
                                strokeDasharray={circumference}
                                strokeDashoffset={storageOffset}
                                strokeLinecap="round"
                                stroke="currentColor"
                                fill="transparent"
                                r={radius}
                                cx="50"
                                cy="50"
                            />
                        </svg>
                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                            <span className={cn(
                                "text-xl font-bold font-mono",
                                isCritical ? "text-red-600" : isWarning ? "text-amber-600" : "text-primary"
                            )}>
                                {Math.round(worstPercent)}%
                            </span>
                        </div>
                    </div>

                    {/* Stats List */}
                    <div className="flex-1 space-y-3">
                        <div className="space-y-1">
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span className="flex items-center gap-1.5">
                                    <HardDrive className="h-3.5 w-3.5" /> Storage
                                </span>
                                <span>{formatBytes(storageUsed)} / {formatBytes(storageLimit)}</span>
                            </div>
                            <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                                <div
                                    className={cn("h-full rounded-full transition-all duration-500",
                                        storagePercent > 90 ? "bg-red-500" : "bg-primary"
                                    )}
                                    style={{ width: `${Math.min(100, storagePercent)}%` }}
                                />
                            </div>
                        </div>

                        <div className="space-y-1">
                            <div className="flex justify-between text-xs text-muted-foreground">
                                <span className="flex items-center gap-1.5">
                                    <Files className="h-3.5 w-3.5" /> Files
                                </span>
                                <span>{filesUsed} / {filesLimit}</span>
                            </div>
                            <div className="h-1.5 w-full bg-secondary rounded-full overflow-hidden">
                                <div
                                    className={cn("h-full rounded-full transition-all duration-500",
                                        filesPercent > 90 ? "bg-red-500" : "bg-blue-500"
                                    )}
                                    style={{ width: `${Math.min(100, filesPercent)}%` }}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {isWarning && showUpgradePrompt && (
                    <div className={cn(
                        "bg-card rounded-md p-3 border text-xs flex flex-col gap-2",
                        isCritical ? "bg-red-50 border-red-100 dark:bg-red-950/20 dark:border-red-900/50" : "bg-amber-50 border-amber-100 dark:bg-amber-950/20 dark:border-amber-900/50"
                    )}>
                        <div className="flex items-start gap-2">
                            <AlertTriangle className={cn("h-4 w-4 shrink-0 mt-0.5", isCritical ? "text-red-600" : "text-amber-600")} />
                            <p className={cn("leading-tight", isCritical ? "text-red-800 dark:text-red-200" : "text-amber-800 dark:text-amber-200")}>
                                {isCritical ? "You have reached your plan limits." : "You are approaching your storage limits."}
                            </p>
                        </div>
                        <Button size="sm" variant={isCritical ? "destructive" : "secondary"} className="w-full h-8 text-xs">
                            <Link href="/dashboard/settings/billing" className="flex items-center gap-1 w-full justify-center">
                                Upgrade Plan <ArrowUpRight className="h-3 w-3" />
                            </Link>
                        </Button>
                    </div>
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
    const colorClass = worstPercent >= 90 ? "text-red-500" : worstPercent >= 75 ? "text-amber-500" : "text-primary";

    return (
        <div className={cn("flex items-center gap-2", className)}>
            <div className="relative h-4 w-4 shrink-0">
                <svg className="h-full w-full rotate-[-90deg]" viewBox="0 0 100 100">
                    <circle
                        className="text-muted/20"
                        strokeWidth="16"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                    />
                    <circle
                        className={colorClass}
                        strokeWidth="16"
                        strokeDasharray={2 * Math.PI * 42}
                        strokeDashoffset={(2 * Math.PI * 42) - (Math.min(100, worstPercent) / 100) * (2 * Math.PI * 42)}
                        strokeLinecap="round"
                        stroke="currentColor"
                        fill="transparent"
                        r="42"
                        cx="50"
                        cy="50"
                    />
                </svg>
            </div>
            <span className={cn("text-xs font-medium", colorClass)}>
                {Math.round(worstPercent)}%
            </span>
        </div>
    );
}
