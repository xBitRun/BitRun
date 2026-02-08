"use client";

/**
 * Global Error Page
 *
 * This is Next.js App Router's error.tsx file.
 * It catches all unhandled errors in the application.
 */

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";
import { PageErrorFallback } from "@/components/error-boundary";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    // Log error to Sentry
    Sentry.captureException(error);

    // Log to console in development
    if (process.env.NODE_ENV === "development") {
      console.error("Global error:", error);
    }
  }, [error]);

  return <PageErrorFallback error={error} reset={reset} />;
}
