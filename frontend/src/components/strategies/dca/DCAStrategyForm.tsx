"use client";

import { useTranslations } from "next-intl";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { DCAConfig } from "@/types";

interface DCAStrategyFormProps {
  value: DCAConfig;
  onChange: (config: DCAConfig) => void;
  disabled?: boolean;
}

export function DCAStrategyForm({
  value,
  onChange,
  disabled = false,
}: DCAStrategyFormProps) {
  const t = useTranslations("quantStrategies");

  const handleChange = (field: keyof DCAConfig, inputValue: string) => {
    const numValue = parseFloat(inputValue) || 0;
    onChange({ ...value, [field]: numValue });
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Order Amount */}
        <div className="space-y-2">
          <Label htmlFor="dca-order-amount">{t("dca.orderAmount")}</Label>
          <Input
            id="dca-order-amount"
            type="number"
            step="0.01"
            min="0"
            value={value.order_amount || ""}
            onChange={(e) => handleChange("order_amount", e.target.value)}
            placeholder="100"
            disabled={disabled}
          />
        </div>

        {/* Interval Minutes */}
        <div className="space-y-2">
          <Label htmlFor="dca-interval">{t("dca.intervalMinutes")}</Label>
          <Input
            id="dca-interval"
            type="number"
            min="1"
            max="43200"
            value={value.interval_minutes || ""}
            onChange={(e) => handleChange("interval_minutes", e.target.value)}
            placeholder="60"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">1 - 43200 min</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Take Profit Percent */}
        <div className="space-y-2">
          <Label htmlFor="dca-take-profit">
            {t("dca.takeProfitPercent")}
          </Label>
          <Input
            id="dca-take-profit"
            type="number"
            step="0.1"
            min="0.1"
            max="100"
            value={value.take_profit_percent || ""}
            onChange={(e) =>
              handleChange("take_profit_percent", e.target.value)
            }
            placeholder="5"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">0.1 - 100%</p>
        </div>

        {/* Total Budget */}
        <div className="space-y-2">
          <Label htmlFor="dca-total-budget">{t("dca.totalBudget")}</Label>
          <Input
            id="dca-total-budget"
            type="number"
            step="0.01"
            min="0"
            value={value.total_budget || ""}
            onChange={(e) => handleChange("total_budget", e.target.value)}
            placeholder="0"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">0 = unlimited</p>
        </div>

        {/* Max Orders */}
        <div className="space-y-2">
          <Label htmlFor="dca-max-orders">{t("dca.maxOrders")}</Label>
          <Input
            id="dca-max-orders"
            type="number"
            min="0"
            value={value.max_orders || ""}
            onChange={(e) => handleChange("max_orders", e.target.value)}
            placeholder="0"
            disabled={disabled}
          />
          <p className="text-xs text-muted-foreground">0 = unlimited</p>
        </div>
      </div>
    </div>
  );
}
