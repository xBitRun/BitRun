/**
 * Sentry Server Configuration
 *
 * This file configures the Sentry SDK for server-side error tracking.
 * https://docs.sentry.io/platforms/javascript/guides/nextjs/
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.SENTRY_DSN || process.env.NEXT_PUBLIC_SENTRY_DSN;

Sentry.init({
  dsn: SENTRY_DSN,

  // Environment and release
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0",

  // Performance Monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Only enable with a DSN
  enabled: !!SENTRY_DSN,

  // Don't send PII by default
  sendDefaultPii: false,

  // Filter events
  beforeSend(event, hint) {
    const error = hint.originalException;

    // Filter out expected errors
    if (error instanceof Error) {
      // Authentication errors
      if (error.message.includes("401") || error.message.includes("403")) {
        return null;
      }

      // Not found errors
      if (error.message.includes("404")) {
        return null;
      }
    }

    return event;
  },

  // Ignore specific errors
  ignoreErrors: [
    "NEXT_NOT_FOUND",
    "NEXT_REDIRECT",
  ],
});
