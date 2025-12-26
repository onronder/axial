// Sentry configuration for the server (Server Components, API routes)
// This file configures Sentry for the server-side of your Next.js app.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

    // Performance Monitoring
    tracesSampleRate: 0.1,

    // Debugging (set to true in development if needed)
    debug: false,
});
