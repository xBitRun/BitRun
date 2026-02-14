"use client";

import { useState, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useRouter, Link } from "@/i18n/navigation";
import {
  ArrowLeft,
  Grid3X3,
  ArrowDownUp,
  Activity,
  Bot,
  Check,
  Loader2,
  CheckCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
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
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import { StrategyStudioTabs, StrategyPresetSelector } from "@/components/strategy-studio";
import {
  useStrategyStudio,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
} from "@/hooks";
import type { StrategyType, RiskProfile, TimeHorizon, StrategyStudioConfig } from "@/types";
import { getStrategyPreset, DEFAULT_PROMPT_SECTIONS } from "@/types";

const STRATEGY_TYPES: {
  type: StrategyType;
  icon: typeof Grid3X3;
  color: string;
}[] = [
  { type: "ai", icon: Bot, color: "text-purple-500 bg-purple-500/10 border-purple-500/30" },
  { type: "grid", icon: Grid3X3, color: "text-blue-500 bg-blue-500/10 border-blue-500/30" },
  { type: "dca", icon: ArrowDownUp, color: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30" },
  { type: "rsi", icon: Activity, color: "text-violet-500 bg-violet-500/10 border-violet-500/30" },
];

export default function CreateStrategyPage() {
  const t = useTranslations("quantStrategies");
  const tStudio = useTranslations("agents");
  const router = useRouter();
  const toast = useToast();

  const [step, setStep] = useState(0); // 0: type, 1: basic info / AI studio, 2: params (quant only)
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state (shared)
  const [selectedType, setSelectedType] = useState<StrategyType | null>(null);

  // Quant-only form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [symbol, setSymbol] = useState("BTC");

  // Grid params
  const [gridUpperPrice, setGridUpperPrice] = useState("50000");
  const [gridLowerPrice, setGridLowerPrice] = useState("40000");
  const [gridCount, setGridCount] = useState("10");
  const [gridTotalInvestment, setGridTotalInvestment] = useState("1000");
  const [gridLeverage, setGridLeverage] = useState("1");

  // DCA params
  const [dcaOrderAmount, setDcaOrderAmount] = useState("100");
  const [dcaIntervalMinutes, setDcaIntervalMinutes] = useState("60");
  const [dcaTakeProfitPercent, setDcaTakeProfitPercent] = useState("5");
  const [dcaTotalBudget, setDcaTotalBudget] = useState("0");
  const [dcaMaxOrders, setDcaMaxOrders] = useState("0");

  // RSI params
  const [rsiPeriod, setRsiPeriod] = useState("14");
  const [rsiOverbought, setRsiOverbought] = useState("70");
  const [rsiOversold, setRsiOversold] = useState("30");
  const [rsiOrderAmount, setRsiOrderAmount] = useState("100");
  const [rsiTimeframe, setRsiTimeframe] = useState("1h");
  const [rsiLeverage, setRsiLeverage] = useState("1");

  // ============ AI Strategy Studio ============
  const { models } = useUserModels();
  const groupedModels = groupModelsByProvider(models);

  // Strategy preset state
  const [selectedRiskProfile, setSelectedRiskProfile] = useState<RiskProfile | null>(null);
  const [selectedTimeHorizon, setSelectedTimeHorizon] = useState<TimeHorizon | null>(null);
  const [isCustomPreset, setIsCustomPreset] = useState(true);

  // Strategy Studio hook
  const {
    config: studioConfig,
    setConfig: setStudioConfig,
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

  // Handle preset selection
  const handlePresetSelect = (profile: RiskProfile, horizon: TimeHorizon) => {
    setSelectedRiskProfile(profile);
    setSelectedTimeHorizon(horizon);
    setIsCustomPreset(false);
    applyPreset(profile, horizon);
  };

  const handleCustomPreset = () => {
    setIsCustomPreset(true);
  };

  // Wrap setConfig to auto-switch to custom mode when config changes
  const handleStudioConfigChange = useCallback((newConfig: StrategyStudioConfig) => {
    if (!isCustomPreset && selectedRiskProfile && selectedTimeHorizon) {
      const preset = getStrategyPreset(selectedRiskProfile, selectedTimeHorizon);
      if (preset) {
        const indicatorsChanged = JSON.stringify(newConfig.indicators) !== JSON.stringify(preset.values.indicators);
        const riskControlsChanged = JSON.stringify(newConfig.riskControls) !== JSON.stringify(preset.values.riskControls);
        const promptSectionsChanged = JSON.stringify(newConfig.promptSections) !== JSON.stringify(DEFAULT_PROMPT_SECTIONS);
        const advancedPromptChanged = newConfig.promptMode === "advanced" && newConfig.advancedPrompt.trim() !== "";

        if (indicatorsChanged || riskControlsChanged || promptSectionsChanged || advancedPromptChanged) {
          setIsCustomPreset(true);
        }
      }
    }
    setStudioConfig(newConfig);
  }, [isCustomPreset, selectedRiskProfile, selectedTimeHorizon, setStudioConfig]);

  const isAiType = selectedType === "ai";

  // ============ Quant Config Builder ============
  const buildQuantConfig = (): Record<string, unknown> => {
    switch (selectedType) {
      case "grid":
        return {
          upper_price: parseFloat(gridUpperPrice),
          lower_price: parseFloat(gridLowerPrice),
          grid_count: parseInt(gridCount),
          total_investment: parseFloat(gridTotalInvestment),
          leverage: parseFloat(gridLeverage),
        };
      case "dca":
        return {
          order_amount: parseFloat(dcaOrderAmount),
          interval_minutes: parseInt(dcaIntervalMinutes),
          take_profit_percent: parseFloat(dcaTakeProfitPercent),
          total_budget: parseFloat(dcaTotalBudget),
          max_orders: parseInt(dcaMaxOrders),
        };
      case "rsi":
        return {
          rsi_period: parseInt(rsiPeriod),
          overbought_threshold: parseFloat(rsiOverbought),
          oversold_threshold: parseFloat(rsiOversold),
          order_amount: parseFloat(rsiOrderAmount),
          timeframe: rsiTimeframe,
          leverage: parseFloat(rsiLeverage),
        };
      default:
        return {};
    }
  };

  // ============ Submit Handlers ============
  const handleAiSubmit = async () => {
    if (!studioConfig.name.trim()) return;
    if (studioConfig.symbols.length === 0) return;

    setIsSubmitting(true);
    try {
      const { strategiesApi } = await import("@/lib/api");
      const apiData = toApiFormat();

      // Build config with preset info
      const configObj = apiData.config as Record<string, unknown>;
      configObj.preset = isCustomPreset
        ? "custom"
        : `${selectedRiskProfile}_${selectedTimeHorizon}`;
      configObj.prompt = apiData.prompt as string;
      configObj.trading_mode = apiData.trading_mode as string;

      const strategy = await strategiesApi.create({
        type: "ai",
        name: apiData.name as string,
        description: apiData.description as string,
        symbols: (configObj.symbols as string[]) || studioConfig.symbols,
        config: configObj,
      });

      toast.success(t("toast.createSuccess"));
      router.push(`/agents/new?strategyId=${strategy.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.createFailed");
      toast.error(t("toast.createFailed"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuantSubmit = async () => {
    if (!selectedType || !name) return;
    const symbols = [symbol.toUpperCase()];
    if (symbols.length === 0) return;

    setIsSubmitting(true);
    try {
      const { strategiesApi } = await import("@/lib/api");
      const strategy = await strategiesApi.create({
        type: selectedType,
        name,
        description,
        symbols,
        config: buildQuantConfig(),
      });
      toast.success(t("toast.createSuccess"));
      router.push(`/agents/new?strategyId=${strategy.id}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.createFailed");
      toast.error(t("toast.createFailed"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const canProceedQuantStep1 = () => {
    if (!name) return false;
    return !!symbol;
  };

  const isAiFormValid = studioConfig.name.trim() !== "" && studioConfig.symbols.length > 0;

  return (
    <div className={cn("space-y-6 mx-auto", isAiType && step === 1 ? "max-w-5xl" : "max-w-3xl")}>
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => {
          if (step > 0) {
            setStep(step - 1);
          } else {
            router.push("/strategies");
          }
        }}>
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold text-gradient">{t("create.title")}</h1>
          <p className="text-muted-foreground">{t("create.description")}</p>
        </div>
        {/* AI submit button in header when on step 1 */}
        {isAiType && step === 1 && (
          <Button
            onClick={handleAiSubmit}
            disabled={isSubmitting || !isAiFormValid}
            className="min-w-[140px]"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-2" />
            )}
            {t("create.submit")}
          </Button>
        )}
      </div>

      {/* Step 0: Select Strategy Type */}
      {step === 0 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">{t("create.selectType")}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {STRATEGY_TYPES.map(({ type, icon: Icon, color }) => (
              <Card
                key={type}
                className={cn(
                  "cursor-pointer transition-all hover:scale-[1.02]",
                  selectedType === type
                    ? "border-primary ring-2 ring-primary/20"
                    : "border-border/50 hover:border-primary/30"
                )}
                onClick={() => setSelectedType(type)}
              >
                <CardContent className="flex flex-col items-center py-8 text-center">
                  <div className={cn("p-4 rounded-xl mb-4 border", color)}>
                    <Icon className="w-8 h-8" />
                  </div>
                  <h3 className="font-semibold text-lg mb-2">{t(`types.${type}`)}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t(`typeDescriptions.${type}`)}
                  </p>
                  {selectedType === type && (
                    <div className="mt-4 p-1 rounded-full bg-primary text-primary-foreground">
                      <Check className="w-4 h-4" />
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => setStep(1)}
              disabled={!selectedType}
            >
              {t("create.next")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 1 for AI: Full Strategy Studio */}
      {step === 1 && isAiType && (
        <div className="space-y-6">
          {/* Basic Info + AI Model Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="pt-6 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Strategy Name */}
                <div className="space-y-2">
                  <Label htmlFor="ai-name" className="flex items-center gap-2">
                    <Bot className="w-4 h-4 text-primary" />
                    {t("create.name")}
                  </Label>
                  <Input
                    id="ai-name"
                    placeholder={t("create.namePlaceholder")}
                    value={studioConfig.name}
                    onChange={(e) => setStudioConfig({ ...studioConfig, name: e.target.value })}
                  />
                </div>

                {/* Description */}
                <div className="space-y-2">
                  <Label htmlFor="ai-description">{t("create.descriptionLabel")}</Label>
                  <Input
                    id="ai-description"
                    placeholder={t("create.descriptionPlaceholder")}
                    value={studioConfig.description}
                    onChange={(e) => setStudioConfig({ ...studioConfig, description: e.target.value })}
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
                <Label htmlFor="ai_model">{tStudio("create.aiModel")}</Label>
                <Select
                  value={studioConfig.aiModel || ""}
                  onValueChange={(v) => setStudioConfig({ ...studioConfig, aiModel: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={tStudio("create.aiModelPlaceholder")} />
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
                        {tStudio("create.noModels")}
                      </div>
                    )}
                  </SelectContent>
                </Select>
                {models.length === 0 && (
                  <p className="text-xs text-muted-foreground">
                    <Link href="/models" className="text-primary hover:underline">
                      {tStudio("create.addModelLink")}
                    </Link>
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Strategy Studio Tabs */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="pt-6">
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

          {/* Bottom Action Buttons */}
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(0)}>
              {t("create.back")}
            </Button>
            <Button
              onClick={handleAiSubmit}
              disabled={isSubmitting || !isAiFormValid}
              className="glow-primary min-w-[140px]"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle className="w-4 h-4 mr-2" />
              )}
              {t("create.submit")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 1 for Quant: Basic Info */}
      {step === 1 && !isAiType && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t("create.basicInfo")}</CardTitle>
              <CardDescription>{t("create.basicInfoDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>{t("create.name")}</Label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("create.namePlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label>{t("create.descriptionLabel")}</Label>
                <Input
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("create.descriptionPlaceholder")}
                />
              </div>
              {/* Quant: single symbol */}
              <div className="space-y-2">
                <Label>{t("create.symbol")}</Label>
                <Input
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  placeholder={t("create.symbolPlaceholder")}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(0)}>
              {t("create.back")}
            </Button>
            <Button
              onClick={() => setStep(2)}
              disabled={!canProceedQuantStep1()}
            >
              {t("create.next")}
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Strategy Parameters (quant only) */}
      {step === 2 && !isAiType && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>
                {selectedType === "grid" && t("grid.title")}
                {selectedType === "dca" && t("dca.title")}
                {selectedType === "rsi" && t("rsi.title")}
              </CardTitle>
              <CardDescription>{t("create.parametersDesc")}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Grid Parameters */}
              {selectedType === "grid" && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{t("grid.upperPrice")}</Label>
                      <Input
                        type="number"
                        value={gridUpperPrice}
                        onChange={(e) => setGridUpperPrice(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.lowerPrice")}</Label>
                      <Input
                        type="number"
                        value={gridLowerPrice}
                        onChange={(e) => setGridLowerPrice(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("grid.gridCount")}</Label>
                      <Input
                        type="number"
                        value={gridCount}
                        onChange={(e) => setGridCount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.totalInvestment")}</Label>
                      <Input
                        type="number"
                        value={gridTotalInvestment}
                        onChange={(e) => setGridTotalInvestment(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("grid.leverage")}</Label>
                      <Input
                        type="number"
                        value={gridLeverage}
                        onChange={(e) => setGridLeverage(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              {/* DCA Parameters */}
              {selectedType === "dca" && (
                <>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>{t("dca.orderAmount")}</Label>
                      <Input
                        type="number"
                        value={dcaOrderAmount}
                        onChange={(e) => setDcaOrderAmount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.intervalMinutes")}</Label>
                      <Input
                        type="number"
                        value={dcaIntervalMinutes}
                        onChange={(e) => setDcaIntervalMinutes(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("dca.takeProfitPercent")}</Label>
                      <Input
                        type="number"
                        value={dcaTakeProfitPercent}
                        onChange={(e) => setDcaTakeProfitPercent(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.totalBudget")}</Label>
                      <Input
                        type="number"
                        value={dcaTotalBudget}
                        onChange={(e) => setDcaTotalBudget(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("dca.maxOrders")}</Label>
                      <Input
                        type="number"
                        value={dcaMaxOrders}
                        onChange={(e) => setDcaMaxOrders(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              {/* RSI Parameters */}
              {selectedType === "rsi" && (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("rsi.rsiPeriod")}</Label>
                      <Input
                        type="number"
                        value={rsiPeriod}
                        onChange={(e) => setRsiPeriod(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.overboughtThreshold")}</Label>
                      <Input
                        type="number"
                        value={rsiOverbought}
                        onChange={(e) => setRsiOverbought(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.oversoldThreshold")}</Label>
                      <Input
                        type="number"
                        value={rsiOversold}
                        onChange={(e) => setRsiOversold(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    <div className="space-y-2">
                      <Label>{t("rsi.orderAmount")}</Label>
                      <Input
                        type="number"
                        value={rsiOrderAmount}
                        onChange={(e) => setRsiOrderAmount(e.target.value)}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.timeframe")}</Label>
                      <Select value={rsiTimeframe} onValueChange={setRsiTimeframe}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1m">1m</SelectItem>
                          <SelectItem value="5m">5m</SelectItem>
                          <SelectItem value="15m">15m</SelectItem>
                          <SelectItem value="30m">30m</SelectItem>
                          <SelectItem value="1h">1h</SelectItem>
                          <SelectItem value="4h">4h</SelectItem>
                          <SelectItem value="1d">1d</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>{t("rsi.leverage")}</Label>
                      <Input
                        type="number"
                        value={rsiLeverage}
                        onChange={(e) => setRsiLeverage(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
          <div className="flex justify-between">
            <Button variant="outline" onClick={() => setStep(1)}>
              {t("create.back")}
            </Button>
            <Button
              onClick={handleQuantSubmit}
              disabled={isSubmitting}
              className="glow-primary"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : null}
              {t("create.submit")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
