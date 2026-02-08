/**
 * Error Boundary Components
 *
 * Export all error boundary components for easy importing.
 *
 * Usage:
 *   import { ErrorBoundary, PageErrorBoundary, SectionErrorBoundary } from "@/components/error-boundary";
 */

export { ErrorBoundary } from "./error-boundary";
export { PageErrorBoundary, PageErrorFallback } from "./page-error-boundary";
export {
  SectionErrorBoundary,
  SectionErrorFallback,
} from "./section-error-boundary";
