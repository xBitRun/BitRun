"use client";

import { useState, useCallback } from "react";
import { useTranslations, useLocale } from "next-intl";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Bot,
  AlertCircle,
  Sparkles,
  ShieldAlert,
  Zap,
  DollarSign,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { FormPageHeader } from "@/components/layout";
import { StrategyStudioTabs, StrategyPresetSelector } from "@/components/strategy-studio";
import {
  useAccounts,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
  useStrategyStudio,
} from "@/hooks";
import type { CreateStrategyRequest } from "@/lib/api";
import type { TradingMode, RiskProfile, TimeHorizon, StrategyStudioConfig } from "@/types";
import { getStrategyPreset, DEFAULT_PROMPT_SECTIONS } from "@/types";

export default function NewAgentPage() {
  const t = useTranslations("agents");
  const tNew = useTranslations("agents.newPage");
  const tCap = useTranslations("strategyStudio.capitalAllocation");
  const router = useRouter();
  const toast = useToast();
  const locale = useLocale();

  const { data: accounts } = useAccounts();
  const { models } = useUserModels();
  const groupedModels = groupModelsByProvider(models);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Strategy preset state
  const [selectedRiskProfile, setSelectedRiskProfile] = useState<RiskProfile | null>("balanced");
  const [selectedTimeHorizon, setSelectedTimeHorizon] = useState<TimeHorizon | null>("swing");
  const [isCustomPreset, setIsCustomPreset] = useState(false);

  // Capital allocation state
  const [capitalMode, setCapitalMode] = useState<"none" | "fixed" | "percent">("none");
  const [allocatedCapital, setAllocatedCapital] = useState("");
  const [allocatedCapitalPercent, setAllocatedCapitalPercent] = useState("");

  // Strategy Studio hook – auto-set language & default preset values
  const defaultPreset = getStrategyPreset("balanced", "swing");
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
    initialConfig: {
      language: locale === "zh" ? "zh" : "en",
      ...(defaultPreset ? defaultPreset.values : {}),
    },
    autoPreview: true,
  });

  // Handle preset selection
  const handlePresetSelect = (profile: RiskProfile, horizon: TimeHorizon) => {
    setSelectedRiskProfile(profile);
    setSelectedTimeHorizon(horizon);
    setIsCustomPreset(false);
    applyPreset(profile, horizon);
  };

  // Handle custom mode
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

  const handleCreateStrategy = async () => {
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const { strategiesApi } = await import("@/lib/api");

      if (!config.name.trim()) {
        throw new Error("Agent name is required");
      }

      if (config.symbols.length === 0) {
        throw new Error(tNew("errorNoSymbols") || "At least one symbol is required");
      }

      if (!config.accountId) {
        throw new Error(tNew("errorNoAccount") || "Please select an account");
      }

      if (!config.aiModel) {
        throw new Error(t("create.aiModelRequired"));
      }

      // Convert to API format
      const apiData = toApiFormat();

      // Use customPrompt, fallback to auto-generated preview (backend requires min 10 chars)
      const rawPrompt = (apiData.prompt as string)?.trim() || "";
      const effectivePrompt = rawPrompt || (promptPreview?.systemPrompt ?? "") || "";
      if (!effectivePrompt) {
        throw new Error(tNew("errorNoPrompt") || "Please enter a prompt or open the Preview tab to generate one");
      }
      if (effectivePrompt.length < 10) {
        throw new Error(tNew("errorShortPrompt") || "Trading prompt must be at least 10 characters");
      }

      // Inject preset info into config
      const configObj = apiData.config as Record<string, unknown>;
      configObj.preset = isCustomPreset
        ? "custom"
        : `${selectedRiskProfile}_${selectedTimeHorizon}`;

      const request: CreateStrategyRequest = {
        name: apiData.name as string,
        description: apiData.description as string,
        prompt: effectivePrompt,
        trading_mode: apiData.trading_mode as TradingMode,
        symbols: (apiData.config as Record<string, unknown>).symbols as string[],
        account_id: apiData.account_id as string,
        ai_model: apiData.ai_model as string,
        config: configObj,
        allocated_capital: capitalMode === "fixed" ? parseFloat(allocatedCapital) : undefined,
        allocated_capital_percent: capitalMode === "percent" ? parseFloat(allocatedCapitalPercent) / 100 : undefined,
      };

      const created = await strategiesApi.create(request);
      toast.success(tNew("success") || "Agent created successfully");
      router.push(`/agents/${created.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to create agent";
      setSubmitError(message);
      toast.error(tNew("failed") || "Failed to create agent", message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid = !!(config.name && config.symbols.length > 0 && config.accountId);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <FormPageHeader
        backHref="/agents"
        title={t("create.title")}
        subtitle={t("create.description")}
        icon={<Sparkles className="w-6 h-6 text-primary" />}
        cancelLabel={t("create.cancel")}
        submitLabel={t("create.submit")}
        onSubmit={handleCreateStrategy}
        isSubmitting={isSubmitting}
        isValid={isFormValid}
      />

      {/* Error Alert */}
      {submitError && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{submitError}</p>
        </div>
      )}

      {/* Basic Info (left) + Strategy Preset (right) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Left: Name, Description, Account, AI Model */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="pt-6 space-y-4">
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

            {/* Account Selection */}
            <div className="space-y-2">
              <Label htmlFor="account" className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                {t("create.account")}
              </Label>
              <Select
                value={config.accountId}
                onValueChange={(v) => setConfig({ ...config, accountId: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t("create.accountPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {accounts && accounts.length > 0 ? (
                    accounts.map((account) => (
                      <SelectItem key={account.id} value={account.id}>
                        {account.name} ({account.exchange})
                        {account.is_testnet && " - Testnet"}
                      </SelectItem>
                    ))
                  ) : (
                    <div className="px-2 py-1.5 text-sm text-muted-foreground">
                      {t("create.noAccounts")}
                    </div>
                  )}
                </SelectContent>
              </Select>
              {(!accounts || accounts.length === 0) && (
                <p className="text-xs text-muted-foreground">
                  <Link href="/accounts/new" className="text-primary hover:underline">
                    {tNew("addAccountLink") || "Add an account"}
                  </Link>
                </p>
              )}
            </div>

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

            {/* Risk Warning */}
            <div className="flex items-center p-3 rounded-lg border border-warning/30 bg-warning/5">
              <ShieldAlert className="w-5 h-5 text-warning shrink-0 mr-3" />
              <div className="text-sm">
                <p className="font-medium text-warning">
                  {tNew("riskWarningTitle") || "Risk Warning"}
                </p>
                <p className="text-muted-foreground text-xs">
                  {tNew("riskWarningDesc") || "Start with testnet and conservative settings."}
                </p>
              </div>
            </div>

            {/* Capital Allocation */}
            <div className="space-y-3 pt-2 border-t border-border/50">
              <Label className="flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-primary" />
                {tCap("title")}
              </Label>
              <p className="text-xs text-muted-foreground">{tCap("description")}</p>
              <Select value={capitalMode} onValueChange={(v) => setCapitalMode(v as "none" | "fixed" | "percent")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">{tCap("modeNone")}</SelectItem>
                  <SelectItem value="fixed">{tCap("modeFixed")}</SelectItem>
                  <SelectItem value="percent">{tCap("modePercent")}</SelectItem>
                </SelectContent>
              </Select>
              {capitalMode === "fixed" && (
                <div className="space-y-2">
                  <Label>{tCap("fixedAmount")}</Label>
                  <Input
                    type="number"
                    value={allocatedCapital}
                    onChange={(e) => setAllocatedCapital(e.target.value)}
                    placeholder={tCap("fixedAmountPlaceholder")}
                    min="0"
                  />
                </div>
              )}
              {capitalMode === "percent" && (
                <div className="space-y-2">
                  <Label>{tCap("percentAmount")}</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      type="number"
                      value={allocatedCapitalPercent}
                      onChange={(e) => setAllocatedCapitalPercent(e.target.value)}
                      placeholder="30"
                      min="1"
                      max="100"
                    />
                    <span className="text-muted-foreground text-sm shrink-0">%</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{tCap("percentAmountTooltip")}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Right: Strategy Preset Selector */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="pt-6">
            <StrategyPresetSelector
              riskProfile={selectedRiskProfile}
              timeHorizon={selectedTimeHorizon}
              isCustom={isCustomPreset}
              onSelect={handlePresetSelect}
              onCustom={handleCustomPreset}
            />
          </CardContent>
        </Card>
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
          onClick={() => router.push("/agents")}
        >
          {t("create.cancel")}
        </Button>
        <Button
          className="flex-1"
          onClick={handleCreateStrategy}
          disabled={!isFormValid || isSubmitting}
        >
          {isSubmitting ? "Creating..." : t("create.submit")}
        </Button>
      </div>
    </div>
  );
}
