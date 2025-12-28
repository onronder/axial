"use client";

/**
 * Usage Warning Banner
 * 
 * Global dismissible banner that appears when usage exceeds 90%.
 * Shows upgrade CTA and links to billing.
 */

import { useState, useEffect } from "react";
import { X, AlertTriangle, TrendingUp } from "lucide-react";
import { useUsage } from "@/hooks/useUsage";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import Link from "next/link";

const DISMISSED_KEY = "usage_warning_dismissed";
const DISMISSED_EXPIRY_HOURS = 24;

export function UsageWarningBanner() {
    const { filesPercent, storagePercent, plan, isLoading } = useUsage();
    const [isDismissed, setIsDismissed] = useState(true); // Start hidden

    // Check localStorage for dismissal
    useEffect(() => {
        const dismissed = localStorage.getItem(DISMISSED_KEY);
        if (dismissed) {
            const expiry = parseInt(dismissed, 10);
            if (Date.now() < expiry) {
                setIsDismissed(true);
                return;
            }
        }
        setIsDismissed(false);
    }, []);

    const worstPercent = Math.max(filesPercent, storagePercent);
    const shouldShow = !isLoading && !isDismissed && worstPercent >= 90 && plan !== "enterprise";

    const handleDismiss = () => {
        // Dismiss for 24 hours
        const expiry = Date.now() + DISMISSED_EXPIRY_HOURS * 60 * 60 * 1000;
        localStorage.setItem(DISMISSED_KEY, expiry.toString());
        setIsDismissed(true);
    };

    if (!shouldShow) return null;

    const isFiles = filesPercent > storagePercent;
    const usageType = isFiles ? "files" : "storage";
    const percent = Math.round(worstPercent);

    return (
        <Alert
            variant="destructive"
            className="rounded-none border-x-0 border-t-0 bg-destructive/10 relative"
        >
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between flex-wrap gap-2">
                <span className="flex-1">
                    <strong>Warning:</strong> You have used {percent}% of your {usageType}.{" "}
                    {percent >= 100
                        ? "Uploads are blocked until you free up space or upgrade."
                        : "Upgrade now for unlimited capacity."}
                </span>
                <div className="flex items-center gap-2">
                    <Button asChild size="sm" variant="destructive">
                        <Link href="/dashboard/settings/billing">
                            <TrendingUp className="h-4 w-4 mr-1" />
                            Upgrade Plan
                        </Link>
                    </Button>
                    <Button
                        size="sm"
                        variant="ghost"
                        onClick={handleDismiss}
                        className="text-destructive hover:text-destructive hover:bg-destructive/20"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
            </AlertDescription>
        </Alert>
    );
}
