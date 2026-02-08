/**
 * Sentry Client Configuration
 *
 * This file configures the Sentry SDK for client-side error tracking.
 * https://docs.sentry.io/platforms/javascript/guides/nextjs/
 */

import * as Sentry from "@sentry/nextjs";

const SENTRY_DSN = process.env.NEXT_PUBLIC_SENTRY_DSN;

Sentry.init({
  dsn: SENTRY_DSN,

  // Environment and release
  environment: process.env.NODE_ENV,
  release: process.env.NEXT_PUBLIC_APP_VERSION || "0.1.0",

  // Performance Monitoring
  tracesSampleRate: process.env.NODE_ENV === "production" ? 0.1 : 1.0,

  // Session Replay (optional - captures user sessions for debugging)
  replaysSessionSampleRate: 0.1,
  replaysOnErrorSampleRate: 1.0,

  // Only enable in production with a DSN
  enabled: !!SENTRY_DSN,

  // Don't send PII by default
  sendDefaultPii: false,

  // Integrations
  integrations: [
    // Capture console errors
    Sentry.captureConsoleIntegration({
      levels: ["error"],
    }),
    // Performance monitoring
    Sentry.browserTracingIntegration(),
  ],

  // Filter out common non-errors
  beforeSend(event, hint) {
    const error = hint.originalException;

    // Filter out network errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return null;
    }

    // Filter out canceled requests
    if (error instanceof Error && error.name === "AbortError") {
      return null;
    }

    // Filter out chunk loading errors (common during deployments)
    if (
      error instanceof Error &&
      error.message.includes("Loading chunk")
    ) {
      return null;
    }

    return event;
  },

  // Breadcrumb filtering
  beforeBreadcrumb(breadcrumb) {
    // Filter out noisy breadcrumbs
    if (breadcrumb.category === "console" && breadcrumb.level === "log") {
      return null;
    }
    return breadcrumb;
  },

  // Ignore specific errors
  ignoreErrors: [
    // Random plugins/extensions
    "top.GLOBALS",
    // Chrome extensions
    /extensions\//i,
    /^chrome:\/\//i,
    // Firefox extensions
    /^resource:\/\//i,
    // Network errors
    "Network request failed",
    "Failed to fetch",
    // User cancelled
    "AbortError",
    // Third party scripts
    /Script error\.?/,
  ],

  // Ignore specific URLs
  denyUrls: [
    // Chrome extensions
    /extensions\//i,
    /^chrome:\/\//i,
    // Safari extensions
    /safari-(web-)?extension:/i,
    // Firefox extensions
    /^moz-extension:\/\//i,
  ],
});
