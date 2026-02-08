"use client";

/**
 * Section-level Error Boundary
 *
 * Compact error fallback for individual sections/cards.
 * Allows the rest of the page to continue functioning.
 */

import React from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "./error-boundary";
import { cn } from "@/lib/utils";

interface SectionErrorFallbackProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
  compact?: boolean;
}

export function SectionErrorFallback({
  title = "Error loading section",
  message = "This section couldn't be loaded. Please try again.",
  onRetry,
  className,
  compact = false,
}: SectionErrorFallbackProps) {
  if (compact) {
    return (
      <div
        className={cn(
          "flex items-center gap-2 rounded-md border border-destructive/20 bg-destructive/5 px-3 py-2 text-sm",
          className
        )}
      >
        <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
        <span className="text-muted-foreground flex-1 truncate">{message}</span>
        {onRetry && (
          <Button
            onClick={onRetry}
            variant="ghost"
            size="sm"
            className="h-6 px-2"
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-center",
        className
      )}
    >
      <AlertCircle className="h-8 w-8 text-destructive mb-2" />
      <h3 className="text-sm font-medium text-foreground mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground mb-3">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} variant="outline" size="sm" className="gap-1">
          <RefreshCw className="h-3 w-3" />
          Retry
        </Button>
      )}
    </div>
  );
}

interface SectionErrorBoundaryProps {
  children: React.ReactNode;
  title?: string;
  message?: string;
  className?: string;
  compact?: boolean;
  resetKeys?: unknown[];
}

export function SectionErrorBoundary({
  children,
  title,
  message,
  className,
  compact = false,
  resetKeys,
}: SectionErrorBoundaryProps) {
  const [resetKey, setResetKey] = React.useState(0);

  const handleRetry = () => {
    setResetKey((prev) => prev + 1);
  };

  return (
    <ErrorBoundary
      key={resetKey}
      resetKeys={resetKeys}
      fallback={
        <SectionErrorFallback
          title={title}
          message={message}
          onRetry={handleRetry}
          className={className}
          compact={compact}
        />
      }
    >
      {children}
    </ErrorBoundary>
  );
}

export default SectionErrorBoundary;
