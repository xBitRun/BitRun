"use client";

/**
 * Global Error Page
 *
 * This is Next.js App Router's error.tsx file.
 * It catches all unhandled errors in the application.
 */

import { useEffect } from "react";
import { PageErrorFallback } from "@/components/error-boundary";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function GlobalError({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Global error:", error);
  }, [error]);

  return <PageErrorFallback error={error} reset={reset} />;
}
