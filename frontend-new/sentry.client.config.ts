// Sentry configuration for the browser (Client Components)
// This file configures Sentry for the client-side of your Next.js app.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

    // Performance Monitoring
    // Capture 10% of transactions for performance monitoring
    tracesSampleRate: 0.1,

    // Session Replay (if needed, currently disabled for performance)
    // replaysSessionSampleRate: 0.1,
    // replaysOnErrorSampleRate: 1.0,

    // Set to true for development debugging
    debug: false,

    // Filter out common noise
    beforeSend(event, hint) {
        // Don't send events in development
        if (process.env.NODE_ENV === "development") {
            return null;
        }
        return event;
    },

    // Ignore common third-party errors
    ignoreErrors: [
        // Browser extensions
        "ResizeObserver loop limit exceeded",
        "ResizeObserver loop completed with undelivered notifications",
        // Network errors that are usually transient
        "Network request failed",
        "Failed to fetch",
        "Load failed",
    ],
});
