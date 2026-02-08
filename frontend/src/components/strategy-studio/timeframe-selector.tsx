"use client";

import { Clock, Check } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Timeframe, TIMEFRAME_OPTIONS } from "@/types";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface TimeframeSelectorProps {
  value: Timeframe[];
  onChange: (timeframes: Timeframe[]) => void;
  maxTimeframes?: number;
}

export function TimeframeSelector({
  value,
  onChange,
  maxTimeframes = 5,
}: TimeframeSelectorProps) {
  const t = useTranslations("strategyStudio");

  const handleToggleTimeframe = (timeframe: Timeframe) => {
    if (value.includes(timeframe)) {
      // Remove if already selected (but keep at least one)
      if (value.length > 1) {
        onChange(value.filter((t) => t !== timeframe));
      }
    } else if (value.length < maxTimeframes) {
      // Add if not at max
      onChange([...value, timeframe].sort((a, b) => {
        const indexA = TIMEFRAME_OPTIONS.findIndex((o) => o.value === a);
        const indexB = TIMEFRAME_OPTIONS.findIndex((o) => o.value === b);
        return indexA - indexB;
      }));
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Clock className="h-5 w-5 text-primary" />
          {t("timeframes.title")}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("timeframes.description")}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {t("timeframes.selected")}: {value.length}/{maxTimeframes}
          </span>
          <span className="text-xs text-muted-foreground">
            {t("timeframes.hint")}
          </span>
        </div>

        <div className="grid grid-cols-4 sm:grid-cols-7 gap-2">
          {TIMEFRAME_OPTIONS.map((option) => {
            const isSelected = value.includes(option.value);
            const isDisabled = !isSelected && value.length >= maxTimeframes;

            return (
              <Button
                key={option.value}
                variant={isSelected ? "default" : "outline"}
                size="sm"
                onClick={() => handleToggleTimeframe(option.value)}
                disabled={isDisabled}
                className={cn(
                  "relative h-12 flex flex-col items-center justify-center gap-0.5",
                  isSelected && "ring-2 ring-primary ring-offset-2 ring-offset-background"
                )}
              >
                {isSelected && (
                  <Check className="absolute top-1 right-1 h-3 w-3" />
                )}
                <span className="font-semibold">{option.value}</span>
                <span className="text-[10px] opacity-70">{option.label}</span>
              </Button>
            );
          })}
        </div>

        {/* Quick presets */}
        <div className="pt-2 border-t border-border/50">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">
              {t("timeframes.presets")}:
            </span>
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onChange(["15m", "1h", "4h"])}
                className="text-xs"
              >
                {t("timeframes.presetSwing")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onChange(["1m", "5m", "15m"])}
                className="text-xs"
              >
                {t("timeframes.presetScalp")}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onChange(["1h", "4h", "1d"])}
                className="text-xs"
              >
                {t("timeframes.presetPosition")}
              </Button>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
