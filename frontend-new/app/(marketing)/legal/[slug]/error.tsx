"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LegalPageError({
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
        <div className="flex items-center justify-center min-h-[40vh] p-8">
            <div className="text-center space-y-4 max-w-md">
                <div className="mx-auto w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center">
                    <AlertTriangle className="h-6 w-6 text-destructive" />
                </div>

                <h2 className="text-xl font-semibold text-foreground">
                    Failed to load page
                </h2>

                <p className="text-sm text-muted-foreground">
                    Something went wrong loading this page. Please try
                    again.
                </p>

                {error.digest && (
                    <p className="text-xs text-muted-foreground/60 font-mono">
                        Error ID: {error.digest}
                    </p>
                )}

                <Button onClick={() => reset()} variant="default" size="sm">
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Try Again
                </Button>
            </div>
        </div>
    );
}
