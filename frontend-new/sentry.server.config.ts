// This file configures the initialization of Sentry on the server.
// The config you add here will be used whenever the server handles a request.
// https://docs.sentry.io/platforms/javascript/guides/nextjs/

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://18f4a279a98e4442868e3cd724ead3a2@o4508223588663296.ingest.de.sentry.io/4510600366194768",

  // Performance Monitoring — 10% of transactions in production
  tracesSampleRate: 0.1,

  // Enable logs to be sent to Sentry
  enableLogs: true,

  // Do NOT send Personally Identifiable Information to Sentry (compliance)
  sendDefaultPii: false,
});
