"use client";

import Link from "next/link";
import { ArrowLeft, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FormPageHeaderProps {
  /** URL to navigate back to */
  backHref: string;
  /** Page title */
  title: string;
  /** Page subtitle/description */
  subtitle?: string;
  /** Icon to display next to title */
  icon?: React.ReactNode;
  /** Cancel button click handler (if provided, renders cancel button) */
  onCancel?: () => void;
  /** Cancel button label */
  cancelLabel?: string;
  /** Submit button click handler (if provided, renders submit button) */
  onSubmit?: () => void;
  /** Submit button label */
  submitLabel?: string;
  /** Submit button loading state */
  isSubmitting?: boolean;
  /** Submit button disabled state (in addition to isSubmitting) */
  isValid?: boolean;
  /** Custom submit button icon */
  submitIcon?: React.ReactNode;
}

/**
 * Unified form page header component
 *
 * Features:
 * - Back button with navigation
 * - Title with optional icon
 * - Optional subtitle
 * - Action buttons (Cancel + Submit)
 *
 * @example
 * ```tsx
 * <FormPageHeader
 *   backHref="/agents"
 *   title="Create AI Agent"
 *   subtitle="Configure your new trading agent"
 *   icon={<Bot className="w-6 h-6 text-primary" />}
 *   cancelLabel="Cancel"
 *   submitLabel="Create"
 *   onSubmit={handleSubmit}
 *   isSubmitting={isLoading}
 *   isValid={isFormValid}
 * />
 * ```
 */
export function FormPageHeader({
  backHref,
  title,
  subtitle,
  icon,
  onCancel,
  cancelLabel = "Cancel",
  onSubmit,
  submitLabel = "Submit",
  isSubmitting = false,
  isValid = true,
  submitIcon,
}: FormPageHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Link href={backHref}>
          <Button variant="ghost" size="icon" className="h-9 w-9">
            <ArrowLeft className="w-4 h-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gradient flex items-center gap-2">
            {icon}
            {title}
          </h1>
          {subtitle && (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          )}
        </div>
      </div>

      {(onCancel || onSubmit) && (
        <div className="flex items-center gap-3">
          {onCancel ? (
            <Button variant="outline" onClick={onCancel}>
              {cancelLabel}
            </Button>
          ) : (
            <Link href={backHref}>
              <Button variant="outline">{cancelLabel}</Button>
            </Link>
          )}

          {onSubmit && (
            <Button
              onClick={onSubmit}
              disabled={isSubmitting || !isValid}
              className="min-w-[120px]"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                submitIcon || <CheckCircle className="w-4 h-4 mr-2" />
              )}
              {submitLabel}
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
