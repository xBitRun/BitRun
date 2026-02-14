"use client";

import {
  Shield,
  Scale,
  Flame,
  Zap,
  TrendingUp,
  Clock,
  Settings2,
  Check,
  ChevronRight,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import type {
  RiskProfile,
  TimeHorizon,
  StrategyPreset,
} from "@/types";
import { getStrategyPreset, DEFAULT_RISK_CONTROLS } from "@/types";

interface StrategyPresetSelectorProps {
  riskProfile: RiskProfile | null;
  timeHorizon: TimeHorizon | null;
  isCustom: boolean;
  onSelect: (riskProfile: RiskProfile, timeHorizon: TimeHorizon) => void;
  onCustom: () => void;
}

const RISK_PROFILES: {
  value: RiskProfile;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  borderColor: string;
  ringColor: string;
}[] = [
  {
    value: "conservative",
    icon: Shield,
    color: "text-emerald-500",
    bgColor: "bg-emerald-500/10",
    borderColor: "border-emerald-500/30",
    ringColor: "ring-emerald-500/40",
  },
  {
    value: "balanced",
    icon: Scale,
    color: "text-blue-500",
    bgColor: "bg-blue-500/10",
    borderColor: "border-blue-500/30",
    ringColor: "ring-blue-500/40",
  },
  {
    value: "aggressive",
    icon: Flame,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/30",
    ringColor: "ring-red-500/40",
  },
];

const TIME_HORIZONS: {
  value: TimeHorizon;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  borderColor: string;
  ringColor: string;
}[] = [
  {
    value: "scalp",
    icon: Zap,
    color: "text-amber-500",
    bgColor: "bg-amber-500/10",
    borderColor: "border-amber-500/30",
    ringColor: "ring-amber-500/40",
  },
  {
    value: "swing",
    icon: TrendingUp,
    color: "text-violet-500",
    bgColor: "bg-violet-500/10",
    borderColor: "border-violet-500/30",
    ringColor: "ring-violet-500/40",
  },
  {
    value: "position",
    icon: Clock,
    color: "text-cyan-500",
    bgColor: "bg-cyan-500/10",
    borderColor: "border-cyan-500/30",
    ringColor: "ring-cyan-500/40",
  },
];

function formatMinutes(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  if (minutes < 1440) return `${minutes / 60}h`;
  return `${minutes / 1440}d`;
}

export function StrategyPresetSelector({
  riskProfile,
  timeHorizon,
  isCustom,
  onSelect,
  onCustom,
}: StrategyPresetSelectorProps) {
  const t = useTranslations("strategyPreset");

  // Get current preset for summary display
  const currentPreset: StrategyPreset | undefined =
    riskProfile && timeHorizon
      ? getStrategyPreset(riskProfile, timeHorizon)
      : undefined;

  const handleRiskProfileClick = (profile: RiskProfile) => {
    // If selecting same profile, keep current timeHorizon or default to swing
    const horizon = timeHorizon || "swing";
    onSelect(profile, horizon);
  };

  const handleTimeHorizonClick = (horizon: TimeHorizon) => {
    // If selecting time horizon, keep current riskProfile or default to balanced
    const profile = riskProfile || "balanced";
    onSelect(profile, horizon);
  };

  return (
    <div className="space-y-4">
      {/* Section Title */}
      <div>
        <h3 className="text-sm font-semibold">{t("title")}</h3>
        <p className="text-xs text-muted-foreground mt-0.5">{t("description")}</p>
      </div>

      {/* Risk Profile Selection */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground">
          {t("riskProfile.title")}
        </p>
        <div className="grid grid-cols-3 gap-2">
          {RISK_PROFILES.map((profile) => {
            const Icon = profile.icon;
            const isSelected = riskProfile === profile.value && !isCustom;
            return (
              <button
                key={profile.value}
                type="button"
                onClick={() => handleRiskProfileClick(profile.value)}
                className={cn(
                  "relative p-3 rounded-lg border-2 text-left transition-all",
                  isSelected
                    ? `${profile.borderColor} ${profile.bgColor} ring-2 ${profile.ringColor}`
                    : "border-border/50 hover:border-border hover:bg-muted/30"
                )}
              >
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5">
                    <Check className={cn("h-3.5 w-3.5", profile.color)} />
                  </div>
                )}
                <Icon className={cn("h-5 w-5 mb-1.5", profile.color)} />
                <p className={cn("font-semibold text-xs", isSelected ? profile.color : "")}>
                  {t(`riskProfile.${profile.value}`)}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                  {t(`riskProfile.${profile.value}Desc`)}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Time Horizon Selection */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground">
          {t("timeHorizon.title")}
        </p>
        <div className="grid grid-cols-3 gap-2">
          {TIME_HORIZONS.map((horizon) => {
            const Icon = horizon.icon;
            const isSelected = timeHorizon === horizon.value && !isCustom;
            return (
              <button
                key={horizon.value}
                type="button"
                onClick={() => handleTimeHorizonClick(horizon.value)}
                className={cn(
                  "relative p-3 rounded-lg border-2 text-left transition-all",
                  isSelected
                    ? `${horizon.borderColor} ${horizon.bgColor} ring-2 ${horizon.ringColor}`
                    : "border-border/50 hover:border-border hover:bg-muted/30"
                )}
              >
                {isSelected && (
                  <div className="absolute top-1.5 right-1.5">
                    <Check className={cn("h-3.5 w-3.5", horizon.color)} />
                  </div>
                )}
                <Icon className={cn("h-5 w-5 mb-1.5", horizon.color)} />
                <p className={cn("font-semibold text-xs", isSelected ? horizon.color : "")}>
                  {t(`timeHorizon.${horizon.value}`)}
                </p>
                <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-2">
                  {t(`timeHorizon.${horizon.value}Desc`)}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Option */}
      <button
        type="button"
        onClick={onCustom}
        className={cn(
          "w-full flex items-center gap-3 p-3 rounded-lg border-2 text-left transition-all",
          isCustom
            ? "border-primary/30 bg-primary/5 ring-2 ring-primary/20"
            : "border-border/50 hover:border-border hover:bg-muted/30"
        )}
      >
        <Settings2 className={cn("h-5 w-5 shrink-0", isCustom ? "text-primary" : "text-muted-foreground")} />
        <div className="flex-1 min-w-0">
          <p className={cn("font-semibold text-xs", isCustom ? "text-primary" : "")}>
            {t("custom")}
          </p>
          <p className="text-[10px] text-muted-foreground">{t("customDesc")}</p>
        </div>
        {isCustom && <Check className="h-4 w-4 text-primary shrink-0" />}
      </button>

      {/* Preset Summary */}
      {currentPreset && !isCustom && (() => {
        const rc = { ...DEFAULT_RISK_CONTROLS, ...currentPreset.values.riskControls };
        return (
        <Card className="bg-muted/30 border-border/50">
          <CardContent className="py-3 px-4">
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
              <ChevronRight className="h-3 w-3" />
              {t("summary.title")}
            </p>
            <div className="grid grid-cols-3 gap-x-4 gap-y-1.5">
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.leverage")}</p>
                <p className="text-xs font-semibold font-mono">
                  {rc.maxLeverage}x
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.positionSize")}</p>
                <p className="text-xs font-semibold font-mono">
                  {(rc.maxPositionRatio * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.exposure")}</p>
                <p className="text-xs font-semibold font-mono">
                  {(rc.maxTotalExposure * 100).toFixed(0)}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.confidence")}</p>
                <p className="text-xs font-semibold font-mono">
                  {rc.minConfidence}%
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.interval")}</p>
                <p className="text-xs font-semibold font-mono">
                  {formatMinutes(currentPreset.values.executionIntervalMinutes)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-muted-foreground">{t("summary.timeframes")}</p>
                <p className="text-xs font-semibold font-mono">
                  {currentPreset.values.timeframes.join("/")}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        );
      })()}
    </div>
  );
}
