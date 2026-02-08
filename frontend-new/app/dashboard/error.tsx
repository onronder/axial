"use client";

/**
 * Dashboard Error Boundary Page
 *
 * Catches unhandled errors within the dashboard layout.
 * Uses Tailwind since it always renders inside the root layout.
 */

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function DashboardError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        Sentry.captureException(error);
    }, [error]);

    return (
        <div className="flex items-center justify-center min-h-[60vh] p-8">
            <div className="text-center space-y-4 max-w-md">
                <div className="mx-auto w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
                    <AlertTriangle className="h-6 w-6 text-destructive" />
                </div>

                <h2 className="text-2xl font-bold text-foreground">
                    Something went wrong
                </h2>

                <p className="text-muted-foreground">
                    An error occurred while loading this page. Our team has been
                    notified and is working on a fix.
                </p>

                {error.digest && (
                    <p className="text-xs text-muted-foreground/60 font-mono">
                        Error ID: {error.digest}
                    </p>
                )}

                <div className="flex gap-3 justify-center pt-2">
                    <Button onClick={() => reset()} variant="default">
                        <RotateCcw className="mr-2 h-4 w-4" />
                        Try Again
                    </Button>
                    <Button
                        variant="outline"
                        onClick={() => (window.location.href = "/dashboard")}
                    >
                        <Home className="mr-2 h-4 w-4" />
                        Dashboard
                    </Button>
                </div>
            </div>
        </div>
    );
}
