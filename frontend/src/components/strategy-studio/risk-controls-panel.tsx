"use client";

import { Shield, AlertTriangle, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  RiskControlsConfig,
  TradingMode,
  RiskProfile,
  TimeHorizon,
  getStrategyPreset,
} from "@/types";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface RiskControlsPanelProps {
  value: RiskControlsConfig;
  onChange: (config: RiskControlsConfig) => void;
  tradingMode: TradingMode;
  /** Optional preset dimensions for richer recommendations */
  riskProfile?: RiskProfile | null;
  timeHorizon?: TimeHorizon | null;
}

// Risk level calculation based on settings
function calculateRiskLevel(config: RiskControlsConfig): {
  level: "low" | "medium" | "high";
  score: number;
} {
  let score = 0;

  // Leverage contributes 0-40 points
  score += Math.min((config.maxLeverage / 50) * 40, 40);

  // Position ratio contributes 0-25 points
  score += Math.min((config.maxPositionRatio / 0.5) * 25, 25);

  // Total exposure contributes 0-20 points
  score += Math.min((config.maxTotalExposure / 1.0) * 20, 20);

  // Lower confidence threshold increases risk (0-15 points)
  score += Math.max(((100 - config.minConfidence) / 100) * 15, 0);

  if (score <= 30) return { level: "low", score };
  if (score <= 60) return { level: "medium", score };
  return { level: "high", score };
}

export function RiskControlsPanel({
  value,
  onChange,
  tradingMode,
  riskProfile,
  timeHorizon,
}: RiskControlsPanelProps) {
  const t = useTranslations("strategyStudio");
  const riskAssessment = calculateRiskLevel(value);

  const update = (key: keyof RiskControlsConfig, newValue: number) => {
    onChange({ ...value, [key]: newValue });
  };

  // Get recommended values – prefer preset-based when available, fallback to tradingMode
  const getRecommendation = (key: keyof RiskControlsConfig): string => {
    // If we have preset dimensions, show the exact preset value as recommendation
    if (riskProfile && timeHorizon) {
      const preset = getStrategyPreset(riskProfile, timeHorizon);
      if (preset) {
        const rc = preset.values.riskControls;
        const map: Record<string, string> = {
          maxLeverage: `${rc.maxLeverage}x`,
          maxPositionRatio: `${(rc.maxPositionRatio * 100).toFixed(0)}%`,
          maxTotalExposure: `${(rc.maxTotalExposure * 100).toFixed(0)}%`,
          minConfidence: `${rc.minConfidence}%`,
        };
        return map[key] || "";
      }
    }
    // Fallback to legacy tradingMode recommendations
    const recommendations: Record<TradingMode, Record<string, string>> = {
      conservative: {
        maxLeverage: "3-5x",
        maxPositionRatio: "10-15%",
        maxTotalExposure: "50-60%",
        minConfidence: "70-80%",
      },
      aggressive: {
        maxLeverage: "10-20x",
        maxPositionRatio: "20-30%",
        maxTotalExposure: "80-100%",
        minConfidence: "50-60%",
      },
      balanced: {
        maxLeverage: "5-8x",
        maxPositionRatio: "10-15%",
        maxTotalExposure: "50-65%",
        minConfidence: "60-70%",
      },
    };
    return recommendations[tradingMode][key] || "";
  };

  const tPreset = useTranslations("strategyPreset");

  // Build preset-based mismatch warning with details, or fall back to legacy check
  const presetMismatchMessage = (() => {
    // --- Preset-based dynamic check ---
    if (riskProfile && timeHorizon) {
      const preset = getStrategyPreset(riskProfile, timeHorizon);
      if (!preset) return null;
      const rc = preset.values.riskControls;
      const { maxLeverage, maxPositionRatio, maxTotalExposure, minConfidence } = value;

      // Tolerance: flag when actual deviates > 50% from preset value (relative)
      const deviates = (actual: number, expected: number) => {
        if (expected === 0) return actual !== 0;
        return Math.abs(actual - expected) / expected > 0.5;
      };

      const details: string[] = [];
      if (deviates(maxLeverage, rc.maxLeverage)) {
        details.push(
          t("riskControls.deviationLeverage", { actual: maxLeverage, expected: rc.maxLeverage })
        );
      }
      if (deviates(maxPositionRatio, rc.maxPositionRatio)) {
        details.push(
          t("riskControls.deviationPosition", {
            actual: (maxPositionRatio * 100).toFixed(0),
            expected: (rc.maxPositionRatio * 100).toFixed(0),
          })
        );
      }
      if (deviates(maxTotalExposure, rc.maxTotalExposure)) {
        details.push(
          t("riskControls.deviationExposure", {
            actual: (maxTotalExposure * 100).toFixed(0),
            expected: (rc.maxTotalExposure * 100).toFixed(0),
          })
        );
      }
      if (deviates(minConfidence, rc.minConfidence)) {
        details.push(
          t("riskControls.deviationConfidence", { actual: minConfidence, expected: rc.minConfidence })
        );
      }

      if (details.length === 0) return null;

      const presetLabel = `${tPreset(`riskProfile.${riskProfile}`)} · ${tPreset(`timeHorizon.${timeHorizon}`)}`;
      return t("riskControls.presetMismatch", {
        preset: presetLabel,
        details: details.join("; "),
      });
    }

    // --- Legacy tradingMode-based check (custom mode / no preset) ---
    const { maxLeverage, maxPositionRatio, maxTotalExposure, minConfidence } = value;
    if (tradingMode === "conservative") {
      if (maxLeverage > 8 || maxPositionRatio > 0.2 || maxTotalExposure > 0.7 || minConfidence < 65) {
        return t("riskControls.modeMismatchConservative");
      }
    }
    if (tradingMode === "aggressive") {
      if (maxLeverage < 5 || maxPositionRatio < 0.15 || maxTotalExposure < 0.6 || minConfidence > 72) {
        return t("riskControls.modeMismatchAggressive");
      }
    }
    if (tradingMode === "balanced") {
      if (maxLeverage > 12 || maxLeverage < 3 || maxPositionRatio > 0.2 || maxTotalExposure > 0.7 || minConfidence < 55 || minConfidence > 78) {
        return t("riskControls.modeMismatchBalanced");
      }
    }
    return null;
  })();

  return (
    <TooltipProvider>
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Shield className="h-5 w-5 text-primary" />
            {t("riskControls.title")}
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {t("riskControls.description")}
          </p>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Risk Level Indicator */}
          <div className="p-4 rounded-lg border border-border/50 bg-background/30">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                {t("riskControls.riskLevel")}
              </span>
              <span
                className={cn(
                  "text-sm font-semibold px-2 py-0.5 rounded",
                  riskAssessment.level === "low" &&
                    "bg-green-500/20 text-green-500",
                  riskAssessment.level === "medium" &&
                    "bg-yellow-500/20 text-yellow-500",
                  riskAssessment.level === "high" &&
                    "bg-red-500/20 text-red-500"
                )}
              >
                {t(`riskControls.levels.${riskAssessment.level}`)}
              </span>
            </div>
            <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full transition-all duration-500",
                  riskAssessment.level === "low" && "bg-green-500",
                  riskAssessment.level === "medium" && "bg-yellow-500",
                  riskAssessment.level === "high" && "bg-red-500"
                )}
                style={{ width: `${riskAssessment.score}%` }}
              />
            </div>
          </div>

          {/* Mode / preset consistency warning */}
          {presetMismatchMessage && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-500 mt-0.5 shrink-0" />
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                {presetMismatchMessage}
              </p>
            </div>
          )}

          {/* Max Leverage */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.maxLeverage")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.maxLeverageTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <div className="flex items-center gap-2">
                <Input
                  type="number"
                  value={value.maxLeverage}
                  onChange={(e) =>
                    update("maxLeverage", parseInt(e.target.value) || 1)
                  }
                  min={1}
                  max={50}
                  className="w-16 h-8 text-right"
                />
                <span className="text-sm text-muted-foreground">x</span>
              </div>
            </div>
            <Slider
              value={[value.maxLeverage]}
              onValueChange={([v]) => update("maxLeverage", v)}
              min={1}
              max={50}
              step={1}
            />
            <p className="text-xs text-muted-foreground">
              {t("riskControls.recommended")}: {getRecommendation("maxLeverage")}
            </p>
          </div>

          {/* Max Position Ratio */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.maxPositionRatio")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.maxPositionRatioTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">
                {(value.maxPositionRatio * 100).toFixed(0)}%
              </span>
            </div>
            <Slider
              value={[value.maxPositionRatio * 100]}
              onValueChange={([v]) => update("maxPositionRatio", v / 100)}
              min={1}
              max={50}
              step={1}
            />
            <p className="text-xs text-muted-foreground">
              {t("riskControls.recommended")}:{" "}
              {getRecommendation("maxPositionRatio")}
            </p>
          </div>

          {/* Max Total Exposure */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.maxTotalExposure")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.maxTotalExposureTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">
                {(value.maxTotalExposure * 100).toFixed(0)}%
              </span>
            </div>
            <Slider
              value={[value.maxTotalExposure * 100]}
              onValueChange={([v]) => update("maxTotalExposure", v / 100)}
              min={10}
              max={100}
              step={5}
            />
            <p className="text-xs text-muted-foreground">
              {t("riskControls.recommended")}:{" "}
              {getRecommendation("maxTotalExposure")}
            </p>
          </div>

          {/* Min Risk/Reward Ratio */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.minRiskReward")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.minRiskRewardTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">
                1:{value.minRiskRewardRatio.toFixed(1)}
              </span>
            </div>
            <Slider
              value={[value.minRiskRewardRatio * 10]}
              onValueChange={([v]) => update("minRiskRewardRatio", v / 10)}
              min={10}
              max={50}
              step={1}
            />
          </div>

          {/* Max Drawdown */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.maxDrawdown")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.maxDrawdownTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium text-destructive">
                {(value.maxDrawdownPercent * 100).toFixed(0)}%
              </span>
            </div>
            <Slider
              value={[value.maxDrawdownPercent * 100]}
              onValueChange={([v]) => update("maxDrawdownPercent", v / 100)}
              min={5}
              max={50}
              step={1}
            />
          </div>

          {/* Min Confidence */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.minConfidence")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.minConfidenceTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">{value.minConfidence}%</span>
            </div>
            <Slider
              value={[value.minConfidence]}
              onValueChange={([v]) => update("minConfidence", v)}
              min={30}
              max={95}
              step={5}
            />
            <p className="text-xs text-muted-foreground">
              {t("riskControls.recommended")}:{" "}
              {getRecommendation("minConfidence")}
            </p>
          </div>

          {/* Stop Loss ATR Multiplier */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.defaultSlAtr")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.defaultSlAtrTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">
                {value.defaultSlAtrMultiplier.toFixed(1)}x ATR
              </span>
            </div>
            <Slider
              value={[value.defaultSlAtrMultiplier * 10]}
              onValueChange={([v]) => update("defaultSlAtrMultiplier", v / 10)}
              min={5}
              max={50}
              step={1}
            />
          </div>

          {/* Take Profit ATR Multiplier */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.defaultTpAtr")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.defaultTpAtrTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium">
                {value.defaultTpAtrMultiplier.toFixed(1)}x ATR
              </span>
            </div>
            <Slider
              value={[value.defaultTpAtrMultiplier * 10]}
              onValueChange={([v]) => update("defaultTpAtrMultiplier", v / 10)}
              min={10}
              max={100}
              step={1}
            />
          </div>

          {/* Max Stop Loss Percent */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Label className="text-sm font-medium">
                  {t("riskControls.maxSlPercent")}
                </Label>
                <Tooltip>
                  <TooltipTrigger>
                    <Info className="h-3.5 w-3.5 text-muted-foreground" />
                  </TooltipTrigger>
                  <TooltipContent>
                    <p className="max-w-xs">
                      {t("riskControls.maxSlPercentTooltip")}
                    </p>
                  </TooltipContent>
                </Tooltip>
              </div>
              <span className="text-sm font-medium text-destructive">
                {(value.maxSlPercent * 100).toFixed(0)}%
              </span>
            </div>
            <Slider
              value={[value.maxSlPercent * 100]}
              onValueChange={([v]) => update("maxSlPercent", v / 100)}
              min={1}
              max={30}
              step={1}
            />
          </div>

          {/* Warning */}
          {riskAssessment.level === "high" && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
              <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" />
              <p className="text-xs text-destructive">
                {t("riskControls.highRiskWarning")}
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </TooltipProvider>
  );
}
