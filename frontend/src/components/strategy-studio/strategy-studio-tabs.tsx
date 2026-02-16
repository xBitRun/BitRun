"use client";

import {
  Coins,
  Activity,
  Shield,
  FileText,
  Eye,
  Users,
  TrendingUp,
} from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  StudioTab,
  StrategyStudioConfig,
  PromptPreviewResponse,
  RiskProfile,
  TimeHorizon,
} from "@/types";
import { SymbolSelector } from "@/components/symbol-selector";
import { IndicatorConfig } from "./indicator-config";
import { TimeframeSelector } from "./timeframe-selector";
import { RiskControlsPanel } from "./risk-controls-panel";
import { PromptTemplateEditor } from "./prompt-template-editor";
import { PromptPreview } from "./prompt-preview";
import { DebateConfig } from "./debate-config";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface StrategyStudioTabsProps {
  config: StrategyStudioConfig;
  onConfigChange: (config: StrategyStudioConfig) => void;
  activeTab: StudioTab;
  onTabChange: (tab: StudioTab) => void;
  promptPreview: PromptPreviewResponse | null;
  isPreviewLoading: boolean;
  onRefreshPreview: () => void;
  onTestAI?: () => void;
  isTestLoading?: boolean;
  /** Optional preset dimensions for richer risk control recommendations */
  riskProfile?: RiskProfile | null;
  timeHorizon?: TimeHorizon | null;
}

const TAB_CONFIG: { value: StudioTab; icon: React.ElementType }[] = [
  { value: "coins", icon: Coins },
  { value: "indicators", icon: Activity },
  { value: "risk", icon: Shield },
  { value: "prompt", icon: FileText },
  { value: "debate", icon: Users },
  { value: "preview", icon: Eye },
];

export function StrategyStudioTabs({
  config,
  onConfigChange,
  activeTab,
  onTabChange,
  promptPreview,
  isPreviewLoading,
  onRefreshPreview,
  onTestAI,
  isTestLoading,
  riskProfile,
  timeHorizon,
}: StrategyStudioTabsProps) {
  const t = useTranslations("strategyStudio");

  const updateConfig = <K extends keyof StrategyStudioConfig>(
    key: K,
    value: StrategyStudioConfig[K],
  ) => {
    onConfigChange({ ...config, [key]: value });
  };

  return (
    <Tabs
      value={activeTab}
      onValueChange={(v) => onTabChange(v as StudioTab)}
      className="w-full"
    >
      <TabsList className="w-full grid grid-cols-6 h-auto p-1 bg-muted/50">
        {TAB_CONFIG.map(({ value, icon: Icon }) => (
          <TabsTrigger
            key={value}
            value={value}
            className={cn(
              "flex flex-col items-center gap-1 py-3 px-2",
              "data-[state=active]:bg-background data-[state=active]:shadow-sm",
            )}
          >
            <Icon className="h-5 w-5" />
            <span className="text-xs font-medium">{t(`tabs.${value}`)}</span>
          </TabsTrigger>
        ))}
      </TabsList>

      <div className="mt-6">
        <TabsContent value="coins" className="m-0 space-y-4">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-lg">
                <TrendingUp className="h-5 w-5 text-primary" />
                {t("coinSelector.title")}
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                {t("coinSelector.description")}
              </p>
            </CardHeader>
            <CardContent>
              <SymbolSelector
                value={config.symbols}
                onChange={(symbols) =>
                  updateConfig("symbols", symbols as string[])
                }
                mode="multiple"
                maxSelections={10}
                showMarketTypeTabs={true}
                allowCustomInput={true}
                placeholder={t("coinSelector.selectedCoins")}
              />
            </CardContent>
          </Card>
          <TimeframeSelector
            value={config.timeframes}
            onChange={(timeframes) => updateConfig("timeframes", timeframes)}
          />
        </TabsContent>

        <TabsContent value="indicators" className="m-0">
          <IndicatorConfig
            value={config.indicators}
            onChange={(indicators) => updateConfig("indicators", indicators)}
          />
        </TabsContent>

        <TabsContent value="risk" className="m-0">
          <RiskControlsPanel
            value={config.riskControls}
            onChange={(riskControls) =>
              updateConfig("riskControls", riskControls)
            }
            tradingMode={config.tradingMode}
            riskProfile={riskProfile}
            timeHorizon={timeHorizon}
          />
        </TabsContent>

        <TabsContent value="prompt" className="m-0">
          <PromptTemplateEditor
            promptMode={config.promptMode}
            onPromptModeChange={(mode) => updateConfig("promptMode", mode)}
            value={config.promptSections}
            onChange={(promptSections) =>
              updateConfig("promptSections", promptSections)
            }
            customPrompt={config.customPrompt}
            onCustomPromptChange={(customPrompt) =>
              updateConfig("customPrompt", customPrompt)
            }
            advancedPrompt={config.advancedPrompt}
            onAdvancedPromptChange={(advancedPrompt) =>
              updateConfig("advancedPrompt", advancedPrompt)
            }
            tradingMode={config.tradingMode}
          />
        </TabsContent>

        <TabsContent value="debate" className="m-0">
          <DebateConfig
            enabled={config.debateEnabled}
            onEnabledChange={(enabled) =>
              updateConfig("debateEnabled", enabled)
            }
            modelIds={config.debateModels}
            onModelIdsChange={(modelIds) =>
              updateConfig("debateModels", modelIds)
            }
            consensusMode={config.debateConsensusMode}
            onConsensusModeChange={(mode) =>
              updateConfig("debateConsensusMode", mode)
            }
            minParticipants={config.debateMinParticipants}
            onMinParticipantsChange={(min) =>
              updateConfig("debateMinParticipants", min)
            }
          />
        </TabsContent>

        <TabsContent value="preview" className="m-0">
          <PromptPreview
            preview={promptPreview}
            isLoading={isPreviewLoading}
            onRefresh={onRefreshPreview}
            onTest={onTestAI}
            isTestLoading={isTestLoading}
            promptMode={config.promptMode}
          />
        </TabsContent>
      </div>
    </Tabs>
  );
}
