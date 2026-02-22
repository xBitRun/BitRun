"use client";

import { useState, useCallback, useEffect } from "react";
import { useTranslations, useLocale } from "next-intl";
import { Card, CardContent } from "@/components/ui/card";
import { StrategyStudioTabs } from "@/components/strategy-studio";
import { useStrategyStudio, apiResponseToConfig } from "@/hooks";
import {
  StrategyStudioConfig,
  RiskProfile,
  TimeHorizon,
  getStrategyPreset,
  getDefaultPromptSections,
} from "@/types";

interface AIStrategyConfigEditorProps {
  initialConfig: Record<string, unknown>;
  onConfigChange: (config: Record<string, unknown>) => void;
  disabled?: boolean;
}

export function AIStrategyConfigEditor({
  initialConfig,
  onConfigChange,
  disabled = false,
}: AIStrategyConfigEditorProps) {
  const t = useTranslations("strategies");
  const locale = useLocale();

  // Parse preset from config if exists
  const presetValue = initialConfig?.preset as string | undefined;
  let initialRiskProfile: RiskProfile | null = null;
  let initialTimeHorizon: TimeHorizon | null = null;
  let initialIsCustom = true;

  if (presetValue && presetValue !== "custom") {
    const [profile, horizon] = presetValue.split("_") as [
      RiskProfile,
      TimeHorizon,
    ];
    if (profile && horizon) {
      initialRiskProfile = profile;
      initialTimeHorizon = horizon;
      initialIsCustom = false;
    }
  }

  const [selectedRiskProfile] =
    useState<RiskProfile | null>(initialRiskProfile);
  const [selectedTimeHorizon] =
    useState<TimeHorizon | null>(initialTimeHorizon);
  const [isCustomPreset, setIsCustomPreset] = useState(initialIsCustom);

  // Convert API config to StrategyStudioConfig format
  const studioInitialConfig = apiResponseToConfig(initialConfig);

  // Use Strategy Studio hook
  const {
    config: studioConfig,
    setConfig: setStudioConfig,
    activeTab,
    setActiveTab,
    promptPreview,
    isPreviewLoading,
    refreshPreview,
    toApiFormat,
  } = useStrategyStudio({
    initialConfig: studioInitialConfig,
    autoPreview: true,
    locale,
  });

  // Wrap setConfig to auto-switch to custom mode when config changes
  const handleStudioConfigChange = useCallback(
    (newConfig: StrategyStudioConfig) => {
      if (!isCustomPreset && selectedRiskProfile && selectedTimeHorizon) {
        const preset = getStrategyPreset(
          selectedRiskProfile,
          selectedTimeHorizon
        );
        if (preset) {
          const defaultPromptSections = getDefaultPromptSections(locale);
          const indicatorsChanged =
            JSON.stringify(newConfig.indicators) !==
            JSON.stringify(preset.values.indicators);
          const riskControlsChanged =
            JSON.stringify(newConfig.riskControls) !==
            JSON.stringify(preset.values.riskControls);
          const promptSectionsChanged =
            JSON.stringify(newConfig.promptSections) !==
            JSON.stringify(defaultPromptSections);
          const advancedPromptChanged =
            newConfig.promptMode === "advanced" &&
            newConfig.advancedPrompt.trim() !== "";

          if (
            indicatorsChanged ||
            riskControlsChanged ||
            promptSectionsChanged ||
            advancedPromptChanged
          ) {
            setIsCustomPreset(true);
          }
        }
      }
      setStudioConfig(newConfig);
    },
    [
      isCustomPreset,
      selectedRiskProfile,
      selectedTimeHorizon,
      setStudioConfig,
      locale,
    ]
  );

  // Sync config changes back to parent
  useEffect(() => {
    if (disabled) return;

    const apiFormat = toApiFormat();
    const configObj = apiFormat.config as Record<string, unknown>;

    // Include preset info
    configObj.preset = isCustomPreset
      ? "custom"
      : `${selectedRiskProfile}_${selectedTimeHorizon}`;

    onConfigChange(configObj);
  }, [
    studioConfig,
    isCustomPreset,
    selectedRiskProfile,
    selectedTimeHorizon,
    onConfigChange,
    toApiFormat,
    disabled,
  ]);

  return (
    <div className="space-y-4">
      {disabled && (
        <p className="text-sm text-muted-foreground">
          {t("edit.configEditor.aiConfigDesc")}
        </p>
      )}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className={disabled ? "opacity-50 pointer-events-none" : ""}>
          <StrategyStudioTabs
            config={studioConfig}
            onConfigChange={handleStudioConfigChange}
            activeTab={activeTab}
            onTabChange={setActiveTab}
            promptPreview={promptPreview}
            isPreviewLoading={isPreviewLoading}
            onRefreshPreview={refreshPreview}
            riskProfile={isCustomPreset ? null : selectedRiskProfile}
            timeHorizon={isCustomPreset ? null : selectedTimeHorizon}
          />
        </CardContent>
      </Card>
    </div>
  );
}
