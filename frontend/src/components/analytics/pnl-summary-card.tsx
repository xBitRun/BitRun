"use client";

import { useTranslations } from "next-intl";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface PnLSummaryCardProps {
  title: string;
  value: number;
  percent?: number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: "up" | "down" | "neutral";
  className?: string;
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function PnLSummaryCard({
  title,
  value,
  percent,
  subtitle,
  icon,
  trend,
  className,
}: PnLSummaryCardProps) {
  // Auto-detect trend based on value if not provided
  const detectedTrend = trend ?? (value > 0 ? "up" : value < 0 ? "down" : "neutral");

  const TrendIcon =
    detectedTrend === "up"
      ? TrendingUp
      : detectedTrend === "down"
        ? TrendingDown
        : Minus;

  const trendColor =
    detectedTrend === "up"
      ? "text-[var(--profit)]"
      : detectedTrend === "down"
        ? "text-[var(--loss)]"
        : "text-muted-foreground";

  return (
    <Card className={cn("bg-card/50 backdrop-blur-sm border-border/50", className)}>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
          {icon}
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-2">
          <TrendIcon className={cn("w-5 h-5", trendColor)} />
          <span className={cn("text-2xl font-bold font-mono", trendColor)}>
            {formatCurrency(value)}
          </span>
        </div>
        {percent !== undefined && (
          <p className={cn("text-sm mt-1 font-mono", trendColor)}>
            {formatPercent(percent)}
          </p>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}
