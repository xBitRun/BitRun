"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { GridConfig } from "@/types";

interface GridStrategyFormProps {
  value: GridConfig;
  onChange: (config: GridConfig) => void;
  disabled?: boolean;
}

export function GridStrategyForm({
  value,
  onChange,
  disabled = false,
}: GridStrategyFormProps) {
  const t = useTranslations("quantStrategies");

  const handleChange = (field: keyof GridConfig, inputValue: string) => {
    const numValue = parseFloat(inputValue) || 0;
    onChange({ ...value, [field]: numValue });
  };

  // Validation: upper_price must be greater than lower_price
  const priceError =
    value.upper_price <= value.lower_price
      ? t("edit.validation.upperPriceGreaterThanLower")
      : null;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Upper Price */}
        <div className="space-y-2">
          <Label
            htmlFor="grid-upper-price"
            className={cn(priceError && "text-destructive")}
          >
            {t("grid.upperPrice")}
          </Label>
          <Input
            id="grid-upper-price"
            type="number"
            step="0.01"
            min="0"
            value={value.upper_price || ""}
            onChange={(e) => handleChange("upper_price", e.target.value)}
            placeholder="50000"
            disabled={disabled}
            className={cn(priceError && "border-destructive")}
          />
        </div>

        {/* Lower Price */}
        <div className="space-y-2">
          <Label
            htmlFor="grid-lower-price"
            className={cn(priceError && "text-destructive")}
          >
            {t("grid.lowerPrice")}
          </Label>
          <Input
            id="grid-lower-price"
            type="number"
            step="0.01"
            min="0"
            value={value.lower_price || ""}
            onChange={(e) => handleChange("lower_price", e.target.value)}
            placeholder="40000"
            disabled={disabled}
            className={cn(priceError && "border-destructive")}
          />
        </div>
      </div>

      {priceError && (
        <p className="text-sm text-destructive">{priceError}</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Grid Count */}
        <div className="space-y-2">
          <Label htmlFor="grid-count">{t("grid.gridCount")}</Label>
          <Input
            id="grid-count"
            type="number"
            min="2"
            max="200"
            value={value.grid_count || ""}
            onChange={(e) => handleChange("grid_count", e.target.value)}
            placeholder="10"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">2 - 200</p>
        </div>

        {/* Total Investment */}
        <div className="space-y-2">
          <Label htmlFor="grid-total-investment">
            {t("grid.totalInvestment")}
          </Label>
          <Input
            id="grid-total-investment"
            type="number"
            step="0.01"
            min="0"
            value={value.total_investment || ""}
            onChange={(e) => handleChange("total_investment", e.target.value)}
            placeholder="1000"
            disabled={disabled}
          />
        </div>

        {/* Leverage */}
        <div className="space-y-2">
          <Label htmlFor="grid-leverage">{t("grid.leverage")}</Label>
          <Input
            id="grid-leverage"
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
