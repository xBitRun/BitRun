"use client";

import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ListPageErrorProps {
  /** Error message to display. */
  message: string;
  /** Called when user clicks Retry. */
  onRetry: () => void;
  /** Optional override for retry button label. Defaults to common.retry. */
  retryLabel?: string;
}

/**
 * Shared error state for list pages. Use with refresh() from data hooks.
 */
export function ListPageError({ message, onRetry, retryLabel }: ListPageErrorProps) {
  const t = useTranslations("common");
  const label = retryLabel ?? t("retry");

  return (
    <Card className="bg-destructive/10 border-destructive/30">
      <CardContent className="flex items-center gap-3 py-4">
        <AlertCircle className="w-5 h-5 shrink-0 text-destructive" />
        <p className="text-destructive flex-1">{message}</p>
        <Button variant="outline" size="sm" onClick={onRetry}>
          {label}
        </Button>
      </CardContent>
    </Card>
  );
}
