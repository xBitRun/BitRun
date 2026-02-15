"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Bot,
  Check,
  FileText,
  Grid3X3,
  ArrowDownUp,
  Activity,
  Loader2,
  Rocket,
  Search,
  Zap,
  AlertTriangle,
  Plus,
  Wallet,
  Play,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";
import {
  useStrategies,
  useAccounts,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
} from "@/hooks";
import type { StrategyResponse, CreateAgentRequest } from "@/lib/api";
import type { StrategyType, ExecutionMode } from "@/types";

// ==================== Constants ====================

const STEPS = ["strategy", "model", "execution", "review"] as const;
type WizardStep = (typeof STEPS)[number];

const STRATEGY_TYPE_ICONS: Record<StrategyType, typeof Bot> = {
  ai: Bot,
  grid: Grid3X3,
  dca: ArrowDownUp,
  rsi: Activity,
};

const STRATEGY_TYPE_COLORS: Record<StrategyType, string> = {
  ai: "text-purple-500 bg-purple-500/10 border-purple-500/30",
  grid: "text-blue-500 bg-blue-500/10 border-blue-500/30",
  dca: "text-emerald-500 bg-emerald-500/10 border-emerald-500/30",
  rsi: "text-violet-500 bg-violet-500/10 border-violet-500/30",
};

const INTERVAL_OPTIONS = [
  { value: 5, label: "5 min" },
  { value: 15, label: "15 min" },
  { value: 30, label: "30 min" },
  { value: 60, label: "1 hr" },
  { value: 240, label: "4 hr" },
  { value: 1440, label: "24 hr" },
];

const TYPE_FILTERS: { value: StrategyType | "all"; labelKey: string }[] = [
  { value: "all", labelKey: "filterAll" },
  { value: "ai", labelKey: "filterAi" },
  { value: "grid", labelKey: "filterGrid" },
  { value: "dca", labelKey: "filterDca" },
  { value: "rsi", labelKey: "filterRsi" },
];

// ==================== StepIndicator ====================

function StepIndicator({
  steps,
  currentStep,
  skippedSteps,
  t,
}: {
  steps: typeof STEPS;
  currentStep: number;
  skippedSteps: Set<number>;
  t: ReturnType<typeof useTranslations>;
}) {
  const stepIcons = [FileText, Bot, Zap, Rocket];
  const stepKeys: WizardStep[] = ["strategy", "model", "execution", "review"];

  return (
    <div className="flex items-center justify-between mb-8">
      {steps.map((step, index) => {
        const Icon = stepIcons[index];
        const isActive = index === currentStep;
        const isComplete = index < currentStep;
        const isSkipped = skippedSteps.has(index);

        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all",
                  isActive
                    ? "border-primary bg-primary text-primary-foreground"
                    : isComplete
                      ? "border-primary bg-primary/10 text-primary"
                      : isSkipped
                        ? "border-muted-foreground/30 bg-muted text-muted-foreground"
                        : "border-border bg-background text-muted-foreground",
                )}
              >
                {isComplete || isSkipped ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Icon className="w-4 h-4" />
                )}
              </div>
              <span
                className={cn(
                  "text-xs mt-1.5 font-medium whitespace-nowrap",
                  isActive ? "text-primary" : "text-muted-foreground",
                )}
              >
                {t(`wizard.steps.${stepKeys[index]}`)}
              </span>
            </div>
            {index < steps.length - 1 && (
              <div
                className={cn(
                  "flex-1 h-0.5 mx-3 -mt-5",
                  index < currentStep ? "bg-primary" : "bg-border",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ==================== Wizard State ====================

interface WizardState {
  // Step 1
  selectedStrategyId: string | null;
  selectedStrategy: StrategyResponse | null;
  // Step 2
  aiModel: string;
  // Step 3
  executionMode: ExecutionMode;
  accountId: string;
  mockInitialBalance: number;
  capitalMode: "none" | "fixed" | "percent";
  allocatedCapital: number;
  allocatedCapitalPercent: number;
  // Step 4
  agentName: string;
  executionIntervalMinutes: number;
  autoExecute: boolean;
}

const initialState: WizardState = {
  selectedStrategyId: null,
  selectedStrategy: null,
  aiModel: "",
  executionMode: "live",
  accountId: "",
  mockInitialBalance: 10000,
  capitalMode: "none",
  allocatedCapital: 0,
  allocatedCapitalPercent: 30,
  agentName: "",
  executionIntervalMinutes: 60,
  autoExecute: true,
};

// ==================== Main Wizard Page ====================

export default function AgentWizardPage() {
  const t = useTranslations("agents");
  const tStrat = useTranslations("strategies");
  const router = useRouter();
  const searchParams = useSearchParams();
  const toast = useToast();

  const [currentStep, setCurrentStep] = useState(0);
  const [state, setState] = useState<WizardState>(initialState);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Data
  const { strategies, isLoading: strategiesLoading } = useStrategies();
  const { data: accounts } = useAccounts();
  const { models, isLoading: modelsLoading } = useUserModels();
  const groupedModels = groupModelsByProvider(models);

  // Is the selected strategy an AI strategy?
  const isAiStrategy = state.selectedStrategy?.type === "ai";

  // Steps that should be skipped
  const skippedSteps = useMemo(() => {
    const set = new Set<number>();
    if (state.selectedStrategy && !isAiStrategy) {
      set.add(1); // Skip model step for quant strategies
    }
    return set;
  }, [state.selectedStrategy, isAiStrategy]);

  // URL param: auto-select strategy
  useEffect(() => {
    const strategyId = searchParams.get("strategyId");
    if (strategyId && strategies.length > 0 && !state.selectedStrategyId) {
      const strategy = strategies.find((s) => s.id === strategyId);
      if (strategy) {
        setState((prev) => ({
          ...prev,
          selectedStrategyId: strategy.id,
          selectedStrategy: strategy,
          agentName: `${strategy.name} Agent`,
        }));
        // Auto-advance to next relevant step
        const nextStep = strategy.type === "ai" ? 1 : 2;
        setCurrentStep(nextStep);
      }
    }
  }, [searchParams, strategies, state.selectedStrategyId]);

  // Navigation
  const goNext = useCallback(() => {
    let next = currentStep + 1;
    while (next < STEPS.length && skippedSteps.has(next)) {
      next++;
    }
    if (next < STEPS.length) {
      setCurrentStep(next);
    }
  }, [currentStep, skippedSteps]);

  const goBack = useCallback(() => {
    let prev = currentStep - 1;
    while (prev >= 0 && skippedSteps.has(prev)) {
      prev--;
    }
    if (prev >= 0) {
      setCurrentStep(prev);
    }
  }, [currentStep, skippedSteps]);

  // Submit
  const handleCreateAgent = async () => {
    if (!state.selectedStrategyId || !state.agentName) return;

    setIsSubmitting(true);
    try {
      const { agentsApi } = await import("@/lib/api");
      const request: CreateAgentRequest = {
        name: state.agentName,
        strategy_id: state.selectedStrategyId,
        ai_model: isAiStrategy ? state.aiModel || undefined : undefined,
        execution_mode: state.executionMode,
        account_id:
          state.executionMode === "live"
            ? state.accountId || undefined
            : undefined,
        mock_initial_balance:
          state.executionMode === "mock" ? state.mockInitialBalance : undefined,
        allocated_capital:
          state.capitalMode === "fixed" ? state.allocatedCapital : undefined,
        allocated_capital_percent:
          state.capitalMode === "percent"
            ? state.allocatedCapitalPercent / 100
            : undefined,
        execution_interval_minutes: state.executionIntervalMinutes,
        auto_execute: state.autoExecute,
      };
      const agent = await agentsApi.create(request);
      toast.success(t("toast.created"));
      router.push(`/agents`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.createFailed");
      toast.error(t("toast.createFailed"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.push("/agents")}
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-gradient">
            {t("wizard.title")}
          </h1>
          <p className="text-muted-foreground">{t("wizard.subtitle")}</p>
        </div>
      </div>

      {/* Step Indicator */}
      <StepIndicator
        steps={STEPS}
        currentStep={currentStep}
        skippedSteps={skippedSteps}
        t={t}
      />

      {/* Step Content */}
      {currentStep === 0 && (
        <StrategyPickerStep
          state={state}
          setState={setState}
          strategies={strategies}
          isLoading={strategiesLoading}
          t={t}
          tStrat={tStrat}
          onNext={goNext}
        />
      )}
      {currentStep === 1 && (
        <ModelSelectStep
          state={state}
          setState={setState}
          models={models}
          groupedModels={groupedModels}
          isLoading={modelsLoading}
          t={t}
          onNext={goNext}
          onBack={goBack}
        />
      )}
      {currentStep === 2 && (
        <ExecutionModeStep
          state={state}
          setState={setState}
          accounts={accounts ?? []}
          t={t}
          onNext={goNext}
          onBack={goBack}
        />
      )}
      {currentStep === 3 && (
        <ReviewStep
          state={state}
          setState={setState}
          accounts={accounts ?? []}
          models={models}
          isAiStrategy={isAiStrategy}
          isSubmitting={isSubmitting}
          t={t}
          onBack={goBack}
          onSubmit={handleCreateAgent}
        />
      )}
    </div>
  );
}

// ==================== Step 1: Strategy Picker ====================

function StrategyPickerStep({
  state,
  setState,
  strategies,
  isLoading,
  t,
  tStrat,
  onNext,
}: {
  state: WizardState;
  setState: React.Dispatch<React.SetStateAction<WizardState>>;
  strategies: StrategyResponse[];
  isLoading: boolean;
  t: ReturnType<typeof useTranslations>;
  tStrat: ReturnType<typeof useTranslations>;
  onNext: () => void;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<StrategyType | "all">("all");

  const filteredStrategies = useMemo(() => {
    return strategies.filter((s) => {
      if (typeFilter !== "all" && s.type !== typeFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          s.name.toLowerCase().includes(q) ||
          s.description?.toLowerCase().includes(q) ||
          s.symbols.some((sym) => sym.toLowerCase().includes(q))
        );
      }
      return true;
    });
  }, [strategies, typeFilter, searchQuery]);

  const selectStrategy = (strategy: StrategyResponse) => {
    setState((prev) => ({
      ...prev,
      selectedStrategyId: strategy.id,
      selectedStrategy: strategy,
      agentName: prev.agentName || `${strategy.name} Agent`,
    }));
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">
          {t("wizard.strategyStep.title")}
        </h2>
        <p className="text-muted-foreground text-sm">
          {t("wizard.strategyStep.subtitle")}
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder={t("wizard.strategyStep.search")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="flex gap-1.5 flex-wrap">
          {TYPE_FILTERS.map(({ value, labelKey }) => (
            <Button
              key={value}
              variant={typeFilter === value ? "default" : "outline"}
              size="sm"
              onClick={() => setTypeFilter(value)}
              className="text-xs"
            >
              {t(`wizard.strategyStep.${labelKey}`)}
            </Button>
          ))}
        </div>
      </div>

      {/* Strategy Cards */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : filteredStrategies.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center py-12 text-center">
            <FileText className="w-10 h-10 text-muted-foreground mb-3" />
            <h3 className="font-semibold text-lg mb-1">
              {t("wizard.strategyStep.empty")}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {t("wizard.strategyStep.emptyDesc")}
            </p>
            <Button
              variant="outline"
              onClick={() => (window.location.href = "/strategies/new")}
            >
              <Plus className="w-4 h-4 mr-2" />
              {t("wizard.strategyStep.createStrategy")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-[480px] overflow-y-auto pr-1">
          {filteredStrategies.map((strategy) => {
            const isSelected = state.selectedStrategyId === strategy.id;
            const Icon =
              STRATEGY_TYPE_ICONS[strategy.type as StrategyType] || FileText;
            const colorClass =
              STRATEGY_TYPE_COLORS[strategy.type as StrategyType] || "";

            return (
              <Card
                key={strategy.id}
                className={cn(
                  "cursor-pointer transition-all hover:border-primary/40",
                  isSelected
                    ? "border-primary ring-2 ring-primary/20"
                    : "border-border/50",
                )}
                onClick={() => selectStrategy(strategy)}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div
                        className={cn("p-1.5 rounded-lg border", colorClass)}
                      >
                        <Icon className="w-4 h-4" />
                      </div>
                      <div>
                        <h4 className="font-semibold text-sm leading-tight">
                          {strategy.name}
                        </h4>
                        <Badge variant="outline" className="text-[10px] mt-0.5">
                          {tStrat(`type.${strategy.type}`)}
                        </Badge>
                      </div>
                    </div>
                    {isSelected && (
                      <div className="p-1 rounded-full bg-primary text-primary-foreground shrink-0">
                        <Check className="w-3 h-3" />
                      </div>
                    )}
                  </div>
                  {strategy.description && (
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                      {strategy.description}
                    </p>
                  )}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {strategy.symbols.slice(0, 4).map((sym) => (
                      <Badge
                        key={sym}
                        variant="secondary"
                        className="text-[10px]"
                      >
                        {sym}
                      </Badge>
                    ))}
                    {strategy.symbols.length > 4 && (
                      <span className="text-[10px] text-muted-foreground">
                        +{strategy.symbols.length - 4}
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-end pt-2">
        <Button onClick={onNext} disabled={!state.selectedStrategyId}>
          {t("wizard.next")}
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

// ==================== Step 2: Model Select ====================

interface AIModelInfo {
  id: string;
  provider: string;
  name: string;
  description: string;
  context_window: number;
}

function ModelSelectStep({
  state,
  setState,
  models,
  groupedModels,
  isLoading,
  t,
  onNext,
  onBack,
}: {
  state: WizardState;
  setState: React.Dispatch<React.SetStateAction<WizardState>>;
  models: AIModelInfo[];
  groupedModels: Record<string, AIModelInfo[]>;
  isLoading: boolean;
  t: ReturnType<typeof useTranslations>;
  onNext: () => void;
  onBack: () => void;
}) {
  // Auto-select if only one model
  useEffect(() => {
    if (models.length === 1 && !state.aiModel) {
      setState((prev) => ({ ...prev, aiModel: models[0].id }));
    }
  }, [models, state.aiModel, setState]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">{t("wizard.modelStep.title")}</h2>
        <p className="text-muted-foreground text-sm">
          {t("wizard.modelStep.subtitle")}
        </p>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : models.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Bot className="w-10 h-10 text-muted-foreground mb-3" />
            <h3 className="font-semibold text-lg mb-1">
              {t("wizard.modelStep.noModels")}
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              {t("wizard.modelStep.noModelsDesc")}
            </p>
            <Button
              variant="outline"
              onClick={() => (window.location.href = "/models")}
            >
              <Plus className="w-4 h-4 mr-2" />
              {t("wizard.modelStep.addModel")}
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
          {Object.entries(groupedModels).map(([provider, providerModels]) => (
            <div key={provider}>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">
                {getProviderDisplayName(provider)}
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {providerModels.map((model) => {
                  const isSelected = state.aiModel === model.id;
                  return (
                    <Card
                      key={model.id}
                      className={cn(
                        "cursor-pointer transition-all hover:border-primary/40",
                        isSelected
                          ? "border-primary ring-2 ring-primary/20"
                          : "border-border/50",
                      )}
                      onClick={() =>
                        setState((prev) => ({ ...prev, aiModel: model.id }))
                      }
                    >
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between">
                          <div className="min-w-0">
                            <h4 className="font-semibold text-sm truncate">
                              {model.name}
                            </h4>
                            {model.description && (
                              <p className="text-xs text-muted-foreground truncate mt-0.5">
                                {model.description}
                              </p>
                            )}
                          </div>
                          {isSelected && (
                            <div className="p-1 rounded-full bg-primary text-primary-foreground shrink-0 ml-2">
                              <Check className="w-3 h-3" />
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("wizard.back")}
        </Button>
        <Button onClick={onNext} disabled={!state.aiModel && models.length > 0}>
          {t("wizard.next")}
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

// ==================== Step 3: Execution Mode ====================

interface AccountInfo {
  id: string;
  name: string;
  exchange: string;
  is_testnet?: boolean;
}

function ExecutionModeStep({
  state,
  setState,
  accounts,
  t,
  onNext,
  onBack,
}: {
  state: WizardState;
  setState: React.Dispatch<React.SetStateAction<WizardState>>;
  accounts: AccountInfo[];
  t: ReturnType<typeof useTranslations>;
  onNext: () => void;
  onBack: () => void;
}) {
  const canProceed =
    state.executionMode === "mock" ||
    (state.executionMode === "live" && !!state.accountId);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">
          {t("wizard.executionStep.title")}
        </h2>
        <p className="text-muted-foreground text-sm">
          {t("wizard.executionStep.subtitle")}
        </p>
      </div>

      {/* Mode Toggle Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Live */}
        <Card
          className={cn(
            "cursor-pointer transition-all hover:border-primary/40",
            state.executionMode === "live"
              ? "border-primary ring-2 ring-primary/20"
              : "border-border/50",
          )}
          onClick={() =>
            setState((prev) => ({ ...prev, executionMode: "live" }))
          }
        >
          <CardContent className="p-6 text-center">
            <div className="inline-flex p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-500 mb-3">
              <Wallet className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-lg mb-1">
              {t("wizard.executionStep.live")}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t("wizard.executionStep.liveDesc")}
            </p>
            {state.executionMode === "live" && (
              <div className="mt-3 p-1 rounded-full bg-primary text-primary-foreground inline-flex">
                <Check className="w-4 h-4" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Mock */}
        <Card
          className={cn(
            "cursor-pointer transition-all hover:border-primary/40",
            state.executionMode === "mock"
              ? "border-primary ring-2 ring-primary/20"
              : "border-border/50",
          )}
          onClick={() =>
            setState((prev) => ({ ...prev, executionMode: "mock" }))
          }
        >
          <CardContent className="p-6 text-center">
            <div className="inline-flex p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 mb-3">
              <Play className="w-6 h-6" />
            </div>
            <h3 className="font-semibold text-lg mb-1">
              {t("wizard.executionStep.mock")}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t("wizard.executionStep.mockDesc")}
            </p>
            {state.executionMode === "mock" && (
              <div className="mt-3 p-1 rounded-full bg-primary text-primary-foreground inline-flex">
                <Check className="w-4 h-4" />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Live Mode: Account Selection */}
      {state.executionMode === "live" && (
        <Card>
          <CardContent className="p-4 space-y-4">
            {/* Risk Warning */}
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
              <p className="text-xs text-amber-700 dark:text-amber-400">
                {t("wizard.executionStep.riskWarning")}
              </p>
            </div>

            {/* Account Select */}
            <div className="space-y-2">
              <Label className="flex items-center gap-1">
                {t("wizard.executionStep.selectAccount")}
                <span className="text-destructive">*</span>
              </Label>
              {accounts.length === 0 ? (
                <div className="flex items-center justify-between p-3 rounded-lg border border-dashed">
                  <span className="text-sm text-muted-foreground">
                    {t("wizard.executionStep.noAccounts")}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => (window.location.href = "/accounts/new")}
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    {t("wizard.executionStep.addAccount")}
                  </Button>
                </div>
              ) : (
                <Select
                  value={state.accountId}
                  onValueChange={(v) =>
                    setState((prev) => ({ ...prev, accountId: v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue
                      placeholder={t(
                        "wizard.executionStep.selectAccountPlaceholder",
                      )}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {accounts.map((acc) => (
                      <SelectItem key={acc.id} value={acc.id}>
                        {acc.name} ({acc.exchange})
                        {acc.is_testnet && " [Testnet]"}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Mock Mode: Initial Balance */}
      {state.executionMode === "mock" && (
        <Card>
          <CardContent className="p-4 space-y-4">
            <div className="space-y-2">
              <Label>{t("wizard.executionStep.mockBalance")}</Label>
              <Input
                type="number"
                value={state.mockInitialBalance}
                onChange={(e) =>
                  setState((prev) => ({
                    ...prev,
                    mockInitialBalance: parseFloat(e.target.value) || 10000,
                  }))
                }
                placeholder={t("wizard.executionStep.mockBalancePlaceholder")}
                min={100}
              />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("wizard.back")}
        </Button>
        <Button onClick={onNext} disabled={!canProceed}>
          {t("wizard.next")}
          <ArrowRight className="w-4 h-4 ml-2" />
        </Button>
      </div>
    </div>
  );
}

// ==================== Step 4: Review & Launch ====================

function ReviewStep({
  state,
  setState,
  accounts,
  models,
  isAiStrategy,
  isSubmitting,
  t,
  onBack,
  onSubmit,
}: {
  state: WizardState;
  setState: React.Dispatch<React.SetStateAction<WizardState>>;
  accounts: AccountInfo[];
  models: AIModelInfo[];
  isAiStrategy: boolean;
  isSubmitting: boolean;
  t: ReturnType<typeof useTranslations>;
  onBack: () => void;
  onSubmit: () => void;
}) {
  const accountName = accounts.find((a) => a.id === state.accountId)?.name;
  const modelName = models.find((m) => m.id === state.aiModel)?.name;

  const canSubmit = !!state.agentName && !!state.selectedStrategyId;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">
          {t("wizard.reviewStep.title")}
        </h2>
        <p className="text-muted-foreground text-sm">
          {t("wizard.reviewStep.subtitle")}
        </p>
      </div>

      {/* Agent Name & Settings */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="space-y-2">
            <Label className="flex items-center gap-1">
              {t("wizard.reviewStep.agentName")}
              <span className="text-destructive">*</span>
            </Label>
            <Input
              value={state.agentName}
              onChange={(e) =>
                setState((prev) => ({ ...prev, agentName: e.target.value }))
              }
              placeholder={t("wizard.reviewStep.agentNamePlaceholder")}
            />
          </div>

          <div className="space-y-2">
            <Label>{t("wizard.reviewStep.interval")}</Label>
            <Select
              value={String(state.executionIntervalMinutes)}
              onValueChange={(v) =>
                setState((prev) => ({
                  ...prev,
                  executionIntervalMinutes: parseInt(v),
                }))
              }
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {INTERVAL_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={String(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <Label>{t("wizard.reviewStep.autoExecute")}</Label>
              <p className="text-xs text-muted-foreground">
                {t("wizard.reviewStep.autoExecuteDesc")}
              </p>
            </div>
            <Switch
              checked={state.autoExecute}
              onCheckedChange={(v) =>
                setState((prev) => ({ ...prev, autoExecute: v }))
              }
            />
          </div>
        </CardContent>
      </Card>

      {/* Configuration Summary */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {t("wizard.reviewStep.summary")}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <div className="space-y-2.5 text-sm">
            <SummaryRow
              label={t("wizard.reviewStep.summaryStrategy")}
              value={state.selectedStrategy?.name || "-"}
            />
            <SummaryRow
              label={t("wizard.reviewStep.summaryType")}
              value={
                <Badge variant="outline" className="text-xs">
                  {state.selectedStrategy?.type?.toUpperCase() || "-"}
                </Badge>
              }
            />
            {isAiStrategy && (
              <SummaryRow
                label={t("wizard.reviewStep.summaryModel")}
                value={modelName || "-"}
              />
            )}
            <SummaryRow
              label={t("wizard.reviewStep.summaryMode")}
              value={
                <Badge
                  variant={
                    state.executionMode === "live" ? "default" : "secondary"
                  }
                  className="text-xs"
                >
                  {t(`executionMode.${state.executionMode}`)}
                </Badge>
              }
            />
            {state.executionMode === "live" && (
              <SummaryRow
                label={t("wizard.reviewStep.summaryAccount")}
                value={accountName || "-"}
              />
            )}
            {state.executionMode === "mock" && (
              <SummaryRow
                label={t("wizard.executionStep.mockBalance")}
                value={`$${state.mockInitialBalance.toLocaleString()}`}
              />
            )}
          </div>
        </CardContent>
      </Card>

      {/* Navigation */}
      <div className="flex justify-between pt-2">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("wizard.back")}
        </Button>
        <Button
          onClick={onSubmit}
          disabled={!canSubmit || isSubmitting}
          className="glow-primary"
        >
          {isSubmitting ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Rocket className="w-4 h-4 mr-2" />
          )}
          {isSubmitting
            ? t("wizard.reviewStep.creating")
            : t("wizard.reviewStep.createAgent")}
        </Button>
      </div>
    </div>
  );
}

// ==================== Helper Components ====================

function SummaryRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
