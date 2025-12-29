"use client";

import { ErrorBoundary, FallbackProps } from "react-error-boundary";
import { ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface AppErrorBoundaryProps {
    children: ReactNode;
    name?: string;
}

/**
 * Error fallback component displayed when a component crashes.
 */
function ErrorFallback({ error, resetErrorBoundary }: FallbackProps) {
    return (
        <div className="flex flex-col items-center justify-center min-h-[200px] p-6 bg-destructive/5 border border-destructive/20 rounded-lg">
            <AlertTriangle className="h-10 w-10 text-destructive mb-4" />
            <h3 className="text-lg font-semibold text-foreground mb-2">
                Something went wrong
            </h3>
            <p className="text-sm text-muted-foreground mb-4 text-center max-w-md">
                {error.message || "An unexpected error occurred. Please try again."}
            </p>
            <Button
                variant="outline"
                onClick={resetErrorBoundary}
                className="gap-2"
            >
                <RefreshCw className="h-4 w-4" />
                Try again
            </Button>
        </div>
    );
}

import * as Sentry from "@sentry/nextjs";

/**
 * Reusable error boundary wrapper for isolating component failures.
 * 
 * Usage:
 * <AppErrorBoundary name="ChatList">
 *   <ChatHistoryList />
 * </AppErrorBoundary>
 */
export function AppErrorBoundary({ children, name }: AppErrorBoundaryProps) {
    return (
        <ErrorBoundary
            FallbackComponent={ErrorFallback}
            onError={(error, info) => {
                console.error(`[ErrorBoundary${name ? `:${name}` : ""}]`, error, info);
                // Send to Sentry
                Sentry.captureException(error, {
                    extra: {
                        componentStack: info.componentStack,
                        boundaryName: name,
                    }
                });
            }}
            onReset={() => {
                // Reset any state that may have caused the error
                window.location.reload();
            }}
        >
            {children}
        </ErrorBoundary>
    );
}

/**
 * Minimal error fallback for sidebar/small components.
 */
function MinimalFallback({ resetErrorBoundary }: FallbackProps) {
    return (
        <div className="flex items-center gap-2 p-2 text-xs text-muted-foreground">
            <AlertTriangle className="h-3 w-3" />
            <span>Error</span>
            <button
                onClick={resetErrorBoundary}
                className="underline hover:text-foreground"
            >
                Retry
            </button>
        </div>
    );
}

/**
 * Compact error boundary for sidebar items and small components.
 */
export function SidebarErrorBoundary({ children }: { children: ReactNode }) {
    return (
        <ErrorBoundary
            FallbackComponent={MinimalFallback}
            onReset={() => window.location.reload()}
        >
            {children}
        </ErrorBoundary>
    );
}
