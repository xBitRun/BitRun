"use client";

import type { LucideIcon } from "lucide-react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface ListPageEmptyProps {
  /** Icon component (e.g. Bot, Wallet, Cpu). */
  icon: LucideIcon;
  /** Title text. */
  title: string;
  /** Description text. */
  description: string;
  /** Primary CTA button label. */
  actionLabel?: string;
  /** Primary CTA href. */
  actionHref?: string;
  /** Optional icon for the action button (e.g. Plus). */
  actionIcon?: LucideIcon;
}

/**
 * Shared empty state for list pages. Shown when list.length === 0; do not render grid alongside.
 */
export function ListPageEmpty({
  icon: Icon,
  title,
  description,
  actionLabel,
  actionHref,
  actionIcon: ActionIcon,
}: ListPageEmptyProps) {
  const hasAction = actionLabel && actionHref;

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardContent className="flex flex-col items-center justify-center py-16">
        <div className="p-4 rounded-full bg-primary/10 mb-6">
          <Icon className="w-12 h-12 text-primary" />
        </div>
        <h3 className="text-xl font-semibold mb-2">{title}</h3>
        <p className={`text-muted-foreground text-center max-w-md ${hasAction ? "mb-8" : "mb-0"}`}>
          {description}
        </p>
        {hasAction && (
          <Link href={actionHref}>
            <Button size="lg" className="glow-primary">
              {ActionIcon && <ActionIcon className="w-4 h-4 mr-2" />}
              {actionLabel}
            </Button>
          </Link>
        )}
      </CardContent>
    </Card>
  );
}
