"use client";

import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export type TimeRange = "7d" | "30d" | "90d" | "1y" | "all";

interface TimeRangeSelectorProps {
  value: TimeRange;
  onChange: (value: TimeRange) => void;
  className?: string;
}

export function TimeRangeSelector({
  value,
  onChange,
  className,
}: TimeRangeSelectorProps) {
  const t = useTranslations("analytics.equityCurve.timeRange");

  const options: { value: TimeRange; label: string }[] = [
    { value: "7d", label: t("7d") },
    { value: "30d", label: t("30d") },
    { value: "90d", label: t("90d") },
    { value: "1y", label: t("1y") },
    { value: "all", label: t("all") },
  ];

  return (
    <div className={cn("flex gap-1", className)}>
      {options.map((option) => (
        <Button
          key={option.value}
          variant={value === option.value ? "default" : "outline"}
          size="sm"
          onClick={() => onChange(option.value)}
          className="h-8 px-3 text-xs"
        >
          {option.label}
        </Button>
      ))}
    </div>
  );
}
