"use client";

import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ListPageFilterEmptyProps {
  /** Icon component (e.g. Bot, Search, LineChart). */
  icon: LucideIcon;
  /** Title text. */
  title: string;
  /** Description text (e.g. "Try adjusting your search or filters"). */
  description: string;
}

/**
 * Shared empty state for filtered / search results on list pages.
 * Shown when data exists but current filters yield 0 results.
 */
export function ListPageFilterEmpty({
  icon: Icon,
  title,
  description,
}: ListPageFilterEmptyProps) {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardContent className="flex flex-col items-center justify-center py-12">
        <div className="p-4 rounded-full bg-muted/50 mb-4">
          <Icon className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-semibold mb-2">{title}</h3>
        <p className="text-muted-foreground text-center">
          {description}
        </p>
      </CardContent>
    </Card>
  );
}
