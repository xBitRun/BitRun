"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useParams, useRouter } from "next/navigation";
import { useSWRConfig } from "swr";
import Link from "next/link";
import {
  ArrowLeft,
  Bot,
  Loader2,
  AlertCircle,
  CheckCircle,
  ShieldAlert,
  Info,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { StrategyStudioTabs, StrategyPresetSelector } from "@/components/strategy-studio";
import {
  useStrategy,
  useAccount,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
  useStrategyStudio,
  apiResponseToConfig,
} from "@/hooks";
import type { TradingMode, RiskProfile, TimeHorizon, StrategyStudioConfig } from "@/types";
import { getStrategyPreset, DEFAULT_PROMPT_SECTIONS } from "@/types";

function LoadingSkeleton() {
  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <Skeleton className="h-8 w-32" />
      <div>
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-5 w-96" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
      <Skeleton className="h-96" />
    </div>
  );
}

export default function EditAgentPage() {
  const t = useTranslations("agents");
  const tEdit = useTranslations("agents.editPage");
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const locale = useLocale();
  const { mutate } = useSWRConfig();
  const agentId = params.id as string;

  const { data: agent, isLoading, error } = useStrategy(agentId);
  const { data: account } = useAccount(agent?.account_id || null);
  const { models } = useUserModels();
  const groupedModels = groupModelsByProvider(models);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Strategy preset state – edit page starts in custom mode (existing agents have custom params)
  const [selectedRiskProfile, setSelectedRiskProfile] = useState<RiskProfile | null>(null);
  const [selectedTimeHorizon, setSelectedTimeHorizon] = useState<TimeHorizon | null>(null);
  const [isCustomPreset, setIsCustomPreset] = useState(true);

  // Strategy Studio hook
  const {
    config,
    setConfig,
    activeTab,
    setActiveTab,
    applyPreset,
    promptPreview,
    isPreviewLoading,
    refreshPreview,
    toApiFormat,
  } = useStrategyStudio({
    autoPreview: true,
  });

  // Handle preset selection in edit page
  const handlePresetSelect = (profile: RiskProfile, horizon: TimeHorizon) => {
    setSelectedRiskProfile(profile);
    setSelectedTimeHorizon(horizon);
    setIsCustomPreset(false);
    applyPreset(profile, horizon);
  };

  const handleCustomPreset = () => {
    setIsCustomPreset(true);
  };

  // Wrap setConfig to auto-switch to custom mode when indicators, riskControls, or prompts change
  const handleConfigChange = useCallback((newConfig: StrategyStudioConfig) => {
    // Detect if indicators, riskControls, or prompts have changed from preset values
    if (!isCustomPreset && selectedRiskProfile && selectedTimeHorizon) {
      const preset = getStrategyPreset(selectedRiskProfile, selectedTimeHorizon);
      if (preset) {
        const indicatorsChanged = JSON.stringify(newConfig.indicators) !== JSON.stringify(preset.values.indicators);
        const riskControlsChanged = JSON.stringify(newConfig.riskControls) !== JSON.stringify(preset.values.riskControls);
        
        // Check if prompt sections have been customized (differs from default)
        const promptSectionsChanged = JSON.stringify(newConfig.promptSections) !== JSON.stringify(DEFAULT_PROMPT_SECTIONS);
        
        // Check if advanced prompt has content
        const advancedPromptChanged = newConfig.promptMode === "advanced" && newConfig.advancedPrompt.trim() !== "";
        
        if (indicatorsChanged || riskControlsChanged || promptSectionsChanged || advancedPromptChanged) {
          setIsCustomPreset(true);
        }
      }
    }
    setConfig(newConfig);
  }, [isCustomPreset, selectedRiskProfile, selectedTimeHorizon, setConfig]);

  // Populate form when agent data loads
  useEffect(() => {
    if (agent && !isInitialized) {
      const convertedConfig = apiResponseToConfig(agent as unknown as Record<string, unknown>);
      // Use stored language if available, otherwise fall back to current locale
      const agentLanguage = convertedConfig.language || (locale === "zh" ? "zh" : "en");
      setConfig((prev) => ({
        ...prev,
        ...convertedConfig,
        language: agentLanguage,
        accountId: agent.account_id || "",
      }) as StrategyStudioConfig);

      // Restore preset state from stored config
      const agentConfig = agent.config as Record<string, unknown> | undefined;
      const storedPreset = agentConfig?.preset as string | undefined;
      if (storedPreset && storedPreset !== "custom") {
        const parts = storedPreset.split("_");
        if (parts.length === 2) {
          setSelectedRiskProfile(parts[0] as RiskProfile);
          setSelectedTimeHorizon(parts[1] as TimeHorizon);
          setIsCustomPreset(false);
        }
      }

      setIsInitialized(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent, isInitialized, setConfig]);

  const handleUpdateStrategy = async () => {
    if (!agent) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const { strategiesApi } = await import("@/lib/api");

      if (!config.name.trim()) {
        throw new Error("Agent name is required");
      }

      if (!config.aiModel) {
        throw new Error(t("create.aiModelRequired"));
      }

      // Convert to API format
      const apiData = toApiFormat();

      // Inject preset info into config
      const configObj = apiData.config as Record<string, unknown>;
      configObj.preset = isCustomPreset
        ? "custom"
        : `${selectedRiskProfile}_${selectedTimeHorizon}`;

      await strategiesApi.update(agent.id, {
        name: apiData.name as string,
        description: apiData.description as string,
        prompt: apiData.prompt as string,
        trading_mode: apiData.trading_mode as TradingMode,
        ai_model: apiData.ai_model as string,
        config: configObj,
      });

      toast.success(tEdit("success") || "Agent updated successfully");
      await mutate(`/strategies/${agent.id}`);
      router.push(`/agents/${agent.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to update agent";
      setSubmitError(message);
      toast.error(tEdit("failed") || "Failed to update agent", message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = config.name && config.symbols.length > 0 && !!config.aiModel;

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error || !agent) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto">
        <Link href="/agents">
          <Button variant="ghost" size="sm" className="gap-2">
            <ArrowLeft className="w-4 h-4" />
            {t("title")}
          </Button>
        </Link>
        <Card className="bg-destructive/10 border-destructive/30">
          <CardContent className="flex items-center gap-3 py-6">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <p className="text-destructive">
              {error?.message || tEdit("notFound") || "Agent not found"}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back Button */}
      <Link href={`/agents/${agent.id}`}>
        <Button variant="ghost" size="sm" className="gap-2">
          <ArrowLeft className="w-4 h-4" />
          {tEdit("backToAgent") || "Back to Agent"}
        </Button>
      </Link>

      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient flex items-center gap-2">
            <Bot className="w-6 h-6 text-primary" />
            {t("edit.title")}
          </h1>
          <p className="text-muted-foreground">{t("edit.description")}</p>
        </div>
        <div className="flex gap-3">
          <Link href={`/agents/${agent.id}`}>
            <Button variant="outline">{t("create.cancel")}</Button>
          </Link>
          <Button
            onClick={handleUpdateStrategy}
            disabled={isSubmitting || !isFormValid}
            className="min-w-[140px]"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-2" />
            )}
            {tEdit("saveChanges") || "Save Changes"}
          </Button>
        </div>
      </div>

      {/* Error Alert */}
      {submitError && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{submitError}</p>
        </div>
      )}

      {/* Basic Info + Account Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Basic Info Card */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50 md:col-span-2">
          <CardContent className="pt-6 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Agent Name */}
              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-primary" />
                  {t("create.name")}
                </Label>
                <Input
                  id="name"
                  placeholder={t("create.namePlaceholder")}
                  value={config.name}
                  onChange={(e) => setConfig({ ...config, name: e.target.value })}
                />
              </div>

              {/* Description */}
              <div className="space-y-2">
                <Label htmlFor="description">{t("create.descriptionLabel")}</Label>
                <Input
                  id="description"
                  placeholder={t("create.descriptionPlaceholder")}
                  value={config.description}
                  onChange={(e) => setConfig({ ...config, description: e.target.value })}
                />
              </div>
            </div>

            {/* Strategy Preset Selector */}
            <StrategyPresetSelector
              riskProfile={selectedRiskProfile}
              timeHorizon={selectedTimeHorizon}
              isCustom={isCustomPreset}
              onSelect={handlePresetSelect}
              onCustom={handleCustomPreset}
            />

            {/* AI Model */}
            <div className="space-y-2">
              <Label htmlFor="ai_model">{t("create.aiModel")}</Label>
              <Select
                value={config.aiModel || ""}
                onValueChange={(v) => setConfig({ ...config, aiModel: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("create.aiModelPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {Object.keys(groupedModels).length > 0 ? (
                    Object.entries(groupedModels).map(([provider, providerModels]) => (
                      <div key={provider}>
                        <div className="px-2 py-1.5 text-xs font-semibold text-muted-foreground">
                          {getProviderDisplayName(provider)}
                        </div>
                        {providerModels.map((model) => (
                          <SelectItem key={model.id} value={model.id}>
                            {model.name}
                          </SelectItem>
                        ))}
                      </div>
                    ))
                  ) : (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground">
                      {t("create.noModels")}
                    </div>
                  )}
                </SelectContent>
              </Select>
              {!config.aiModel && (
                <p className="text-xs text-destructive">
                  {t("create.aiModelRequired")}
                </p>
              )}
              {models.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  <Link href="/models" className="text-primary hover:underline">
                    {t("create.addModelLink")}
                  </Link>
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Info Sidebar */}
        <div className="space-y-4">
          {/* Account Info (Read-only) */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                {t("create.account")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="font-medium">{account?.name || tEdit("unknownAccount") || "Unknown Account"}</p>
              <p className="text-xs text-muted-foreground mt-1">
                {tEdit("accountNote") || "Account cannot be changed after creation"}
              </p>
            </CardContent>
          </Card>

          {/* Agent Info */}
          <Card className="bg-muted/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" />
                {tEdit("agentInfo") || "Agent Info"}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{tEdit("status") || "Status"}</span>
                <span className="font-medium">{t(`status.${agent.status}`)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{tEdit("created") || "Created"}</span>
                <span className="font-medium text-xs">
                  {new Date(agent.created_at).toLocaleDateString()}
                </span>
              </div>
              {agent.total_pnl !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t("stats.totalPL")}</span>
                  <span className={`font-medium font-mono text-xs ${agent.total_pnl >= 0 ? "text-profit" : "text-loss"}`}>
                    {agent.total_pnl >= 0 ? "+" : ""}${agent.total_pnl.toFixed(2)}
                  </span>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Warning Card */}
          <Card className="border-warning/30 bg-warning/5">
            <CardContent className="pt-4">
              <div className="flex gap-3">
                <ShieldAlert className="w-5 h-5 text-warning shrink-0" />
                <div className="text-sm">
                  <p className="font-medium text-warning">
                    {tEdit("changeWarningTitle") || "Changes Take Effect Immediately"}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {tEdit("changeWarningDesc") || "Any changes will be applied to the next trading decision."}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Strategy Studio Tabs */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardContent className="pt-6">
          <StrategyStudioTabs
            config={config}
            onConfigChange={handleConfigChange}
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

      {/* Bottom Action Buttons (Mobile) */}
      <div className="md:hidden flex gap-3 sticky bottom-4">
        <Button
          variant="outline"
          className="flex-1"
          onClick={() => router.push(`/agents/${agent.id}`)}
        >
          {t("create.cancel")}
        </Button>
        <Button
          className="flex-1"
          onClick={handleUpdateStrategy}
          disabled={!isFormValid || isSubmitting}
        >
          {isSubmitting ? "Saving..." : tEdit("saveChanges")}
        </Button>
      </div>
    </div>
  );
}
