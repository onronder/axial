// Sentry configuration for Edge Runtime (Middleware, Edge API routes)
// This file configures Sentry for edge functions in your Next.js app.

import * as Sentry from "@sentry/nextjs";

Sentry.init({
    dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,

    // Performance Monitoring
    tracesSampleRate: 0.1,

    // Debugging
    debug: false,
});
