"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { PnLSummary } from "@/components/pnl";

interface PnLSummaryCardProps {
  title: string;
  value: number;
  percent?: number;
  subtitle?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function PnLSummaryCard({
  title,
  value,
  percent,
  subtitle,
  icon,
  className,
}: PnLSummaryCardProps) {
  return (
    <Card
      className={cn("bg-card/50 backdrop-blur-sm border-border/50", className)}
    >
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <PnLSummary
          value={value}
          percent={percent}
          subtitle={subtitle}
          mode={percent !== undefined ? "both" : "amount"}
        />
      </CardContent>
    </Card>
  );
}
