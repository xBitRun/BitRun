"use client";

/**
 * Page-level Error Boundary
 *
 * Full-page error fallback for route-level errors.
 * Provides navigation options and a more prominent UI.
 */

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Home, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "./error-boundary";

interface PageErrorFallbackProps {
  error?: Error | null;
  reset?: () => void;
}

export function PageErrorFallback({ error, reset }: PageErrorFallbackProps) {
  const router = useRouter();

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4">
      <div className="text-center max-w-md">
        <div className="mb-6 flex justify-center">
          <div className="rounded-full bg-destructive/10 p-4">
            <AlertTriangle className="h-12 w-12 text-destructive" />
          </div>
        </div>

        <h1 className="text-2xl font-bold text-foreground mb-2">
          Page Error
        </h1>
        <p className="text-muted-foreground mb-6">
          We encountered an error while loading this page. This has been
          automatically reported to our team.
        </p>

        {process.env.NODE_ENV === "development" && error && (
          <div className="mb-6 rounded-lg bg-muted p-4 text-left">
            <p className="text-sm font-mono text-destructive break-all">
              {error.message}
            </p>
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          {reset && (
            <Button onClick={reset} variant="default" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Try Again
            </Button>
          )}

          <Button
            onClick={() => router.back()}
            variant="outline"
            className="gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </Button>

          <Button asChild variant="outline" className="gap-2">
            <Link href="/overview">
              <Home className="h-4 w-4" />
              Home
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

interface PageErrorBoundaryProps {
  children: React.ReactNode;
}

export function PageErrorBoundary({ children }: PageErrorBoundaryProps) {
  return (
    <ErrorBoundary
      fallback={<PageErrorFallback />}
      showDetails={process.env.NODE_ENV === "development"}
    >
      {children}
    </ErrorBoundary>
  );
}

export default PageErrorBoundary;
