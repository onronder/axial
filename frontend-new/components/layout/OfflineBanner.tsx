"use client";

/**
 * OfflineBanner
 *
 * Renders a sticky banner at the top of the viewport when the browser is offline.
 * Automatically hides when connectivity is restored.
 */

import { WifiOff } from "lucide-react";
import { useNetworkStatus } from "@/hooks/useNetworkStatus";

export function OfflineBanner() {
    const isOnline = useNetworkStatus();

    if (isOnline) return null;

    return (
        <div
            role="alert"
            className="sticky top-0 z-50 flex items-center justify-center gap-2 bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground"
        >
            <WifiOff className="h-4 w-4" />
            You are offline. Some features may be unavailable.
        </div>
    );
}
