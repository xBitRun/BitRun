"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import type { RSIConfig, Timeframe } from "@/types";

interface RSIStrategyFormProps {
  value: RSIConfig;
  onChange: (config: RSIConfig) => void;
  disabled?: boolean;
}

const TIMEFRAME_OPTIONS: { value: Timeframe; label: string }[] = [
  { value: "1m", label: "1m" },
  { value: "5m", label: "5m" },
  { value: "15m", label: "15m" },
  { value: "30m", label: "30m" },
  { value: "1h", label: "1h" },
  { value: "4h", label: "4h" },
  { value: "1d", label: "1d" },
];

export function RSIStrategyForm({
  value,
  onChange,
  disabled = false,
}: RSIStrategyFormProps) {
  const t = useTranslations("quantStrategies");

  const handleChange = (field: keyof RSIConfig, inputValue: string) => {
    const numValue = parseFloat(inputValue) || 0;
    onChange({ ...value, [field]: numValue });
  };

  const handleTimeframeChange = (timeframe: string) => {
    onChange({ ...value, timeframe });
  };

  // Validation: overbought must be greater than oversold
  const thresholdError =
    value.overbought_threshold <= value.oversold_threshold
      ? t("edit.validation.overboughtGreaterThanOversold")
      : null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* RSI Period */}
        <div className="space-y-2">
          <Label htmlFor="rsi-period">{t("rsi.rsiPeriod")}</Label>
          <Input
            id="rsi-period"
            type="number"
            min="2"
            max="100"
            value={value.rsi_period || ""}
            onChange={(e) => handleChange("rsi_period", e.target.value)}
            placeholder="14"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">2 - 100</p>
        </div>

        {/* Overbought Threshold */}
        <div className="space-y-2">
          <Label
            htmlFor="rsi-overbought"
            className={cn(thresholdError && "text-destructive")}
          >
            {t("rsi.overboughtThreshold")}
          </Label>
          <Input
            id="rsi-overbought"
            type="number"
            min="50"
            max="95"
            value={value.overbought_threshold || ""}
            onChange={(e) =>
              handleChange("overbought_threshold", e.target.value)
            }
            placeholder="70"
            disabled={disabled}
            className={cn(thresholdError && "border-destructive")}
          />
          <p className="text-xs text-muted-foreground">50 - 95</p>
        </div>

        {/* Oversold Threshold */}
        <div className="space-y-2">
          <Label
            htmlFor="rsi-oversold"
            className={cn(thresholdError && "text-destructive")}
          >
            {t("rsi.oversoldThreshold")}
          </Label>
          <Input
            id="rsi-oversold"
            type="number"
            min="5"
            max="50"
            value={value.oversold_threshold || ""}
            onChange={(e) => handleChange("oversold_threshold", e.target.value)}
            placeholder="30"
            disabled={disabled}
            className={cn(thresholdError && "border-destructive")}
          />
          <p className="text-xs text-muted-foreground">5 - 50</p>
        </div>
      </div>

      {thresholdError && (
        <p className="text-sm text-destructive">{thresholdError}</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Order Amount */}
        <div className="space-y-2">
          <Label htmlFor="rsi-order-amount">{t("rsi.orderAmount")}</Label>
          <Input
            id="rsi-order-amount"
            type="number"
            step="0.01"
            min="0"
            value={value.order_amount || ""}
            onChange={(e) => handleChange("order_amount", e.target.value)}
            placeholder="100"
            disabled={disabled}
          />
        </div>

        {/* Timeframe */}
        <div className="space-y-2">
          <Label htmlFor="rsi-timeframe">{t("rsi.timeframe")}</Label>
          <Select
            value={value.timeframe || "1h"}
            onValueChange={handleTimeframeChange}
            disabled={disabled}
          >
            <SelectTrigger id="rsi-timeframe">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TIMEFRAME_OPTIONS.map(({ value: tf, label }) => (
                <SelectItem key={tf} value={tf}>
                  {label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Leverage */}
        <div className="space-y-2">
          <Label htmlFor="rsi-leverage">{t("rsi.leverage")}</Label>
          <Input
            id="rsi-leverage"
            type="number"
            min="1"
            max="50"
            value={value.leverage || ""}
            onChange={(e) => handleChange("leverage", e.target.value)}
            placeholder="1"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">1 - 50x</p>
        </div>
      </div>
    </div>
  );
}
