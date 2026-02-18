"use client";

import { useState, useEffect } from "react";
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
  ExternalLink,
  FileText,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { cn } from "@/lib/utils";
import {
  useAccount,
  useAccounts,
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
  useStrategy,
} from "@/hooks";
import { useAgent, useUpdateAgent } from "@/hooks/use-agents";
import type { ExecutionMode } from "@/types";

function LoadingSkeleton() {
  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <Skeleton className="h-8 w-32" />
      <div>
        <Skeleton className="h-8 w-64 mb-2" />
        <Skeleton className="h-5 w-96" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Skeleton className="h-48" />
        <Skeleton className="h-48" />
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}

export default function EditAgentPage() {
  const t = useTranslations("agents");
  const tEdit = useTranslations("agents.editPage");
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const { mutate } = useSWRConfig();
  const agentId = params.id as string;

  const { data: agent, isLoading, error } = useAgent(agentId);
  const { data: account } = useAccount(agent?.account_id ?? null);
  const { data: strategy } = useStrategy(agent?.strategy_id ?? null);
  const { accounts } = useAccounts();
  const { models } = useUserModels();
  const groupedModels = groupModelsByProvider(models);
  const updateAgent = useUpdateAgent(agentId);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [aiModel, setAiModel] = useState("");
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("mock");
  const [accountId, setAccountId] = useState("");
  const [mockInitialBalance, setMockInitialBalance] = useState(10000);
  const [executionIntervalMinutes, setExecutionIntervalMinutes] = useState(15);
  const [autoExecute, setAutoExecute] = useState(true);

  // Check if strategy is AI type
  const isAiStrategy = agent?.strategy_type === "ai";

  // Populate form when agent data loads
  useEffect(() => {
    if (agent && !isInitialized) {
      setName(agent.name || "");
      setAiModel(agent.ai_model || "");
      setExecutionMode(agent.execution_mode || "mock");
      setAccountId(agent.account_id || "");
      setMockInitialBalance(agent.mock_initial_balance || 10000);
      setExecutionIntervalMinutes(agent.execution_interval_minutes || 15);
      setAutoExecute(agent.auto_execute ?? true);
      setIsInitialized(true);
    }
  }, [agent, isInitialized]);

  const handleSave = async () => {
    if (!agent) return;

    setIsSubmitting(true);
    setSubmitError(null);

    try {
      const { agentsApi } = await import("@/lib/api");

      if (!name.trim()) {
        throw new Error(t("create.nameRequired"));
      }

      if (isAiStrategy && !aiModel) {
        throw new Error(t("create.aiModelRequired"));
      }

      if (executionMode === "live" && !accountId) {
        throw new Error(t("create.accountRequired"));
      }

      await updateAgent.trigger({
        name: name.trim(),
        ai_model: isAiStrategy ? aiModel : null,
        execution_mode: executionMode,
        account_id: executionMode === "live" ? accountId : null,
        mock_initial_balance:
          executionMode === "mock" ? mockInitialBalance : null,
        execution_interval_minutes: executionIntervalMinutes,
        auto_execute: autoExecute,
      });

      toast.success(tEdit("success"));
      await mutate(`/agents/${agent.id}`);
      router.push(`/agents/${agent.id}`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : tEdit("failedToUpdate");
      setSubmitError(message);
      toast.error(tEdit("failed"), message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormValid =
    name.trim() !== "" &&
    (!isAiStrategy || aiModel) &&
    (executionMode === "mock" || accountId);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error || !agent) {
    return (
      <div className="space-y-6 max-w-4xl mx-auto">
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
              {error?.message || tEdit("notFound")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Back Button */}
      <Link href={`/agents/${agent.id}`}>
        <Button variant="ghost" size="sm" className="gap-2">
          <ArrowLeft className="w-4 h-4" />
          {tEdit("backToAgent")}
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
            onClick={handleSave}
            disabled={isSubmitting || !isFormValid}
            className="min-w-[140px]"
          >
            {isSubmitting ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4 mr-2" />
            )}
            {tEdit("saveChanges")}
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Form Area */}
        <div className="md:col-span-2 space-y-6">
          {/* Basic Info Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="text-base">{tEdit("basicInfo")}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name" className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-primary" />
                  {t("create.name")}
                  <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="name"
                  placeholder={t("create.namePlaceholder")}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>

          {/* AI Model Card - Only for AI strategies */}
          {isAiStrategy && (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Zap className="w-4 h-4 text-primary" />
                  {t("create.aiModel")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="ai_model" className="flex items-center gap-1">
                    {t("create.aiModel")}
                    <span className="text-destructive">*</span>
                  </Label>
                  <Select value={aiModel} onValueChange={setAiModel}>
                    <SelectTrigger>
                      <SelectValue
                        placeholder={t("create.aiModelPlaceholder")}
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.keys(groupedModels).length > 0 ? (
                        Object.entries(groupedModels).map(
                          ([provider, providerModels]) => (
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
                          ),
                        )
                      ) : (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          {t("create.noModels")}
                        </div>
                      )}
                    </SelectContent>
                  </Select>
                  {!aiModel && (
                    <p className="text-xs text-destructive">
                      {t("create.aiModelRequired")}
                    </p>
                  )}
                  {models.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      <Link
                        href="/models"
                        className="text-primary hover:underline"
                      >
                        {t("create.addModelLink")}
                      </Link>
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Execution Settings Card */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader>
              <CardTitle className="text-base">
                {tEdit("tradingConfig")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Execution Mode */}
              <div className="space-y-2">
                <Label>{t("fields.executionMode")}</Label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setExecutionMode("live")}
                    className={cn(
                      "p-4 rounded-lg border text-left transition-all",
                      executionMode === "live"
                        ? "border-primary bg-primary/10"
                        : "border-border/50 hover:border-primary/30",
                    )}
                  >
                    <div className="font-medium">{t("executionMode.live")}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {t("create.steps.executionStep.liveDesc")}
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setExecutionMode("mock")}
                    className={cn(
                      "p-4 rounded-lg border text-left transition-all",
                      executionMode === "mock"
                        ? "border-primary bg-primary/10"
                        : "border-border/50 hover:border-primary/30",
                    )}
                  >
                    <div className="font-medium">{t("executionMode.mock")}</div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {t("create.steps.executionStep.mockDesc")}
                    </div>
                  </button>
                </div>
              </div>

              {/* Account Selection (Live Mode) */}
              {executionMode === "live" && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-1">
                    {t("fields.account")}
                    <span className="text-destructive">*</span>
                  </Label>
                  <Select value={accountId} onValueChange={setAccountId}>
                    <SelectTrigger>
                      <SelectValue
                        placeholder={t(
                          "create.steps.executionStep.selectAccountPlaceholder",
                        )}
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {accounts && accounts.length > 0 ? (
                        accounts.map((acc) => (
                          <SelectItem key={acc.id} value={acc.id}>
                            {acc.name} ({acc.exchange})
                          </SelectItem>
                        ))
                      ) : (
                        <div className="px-2 py-1.5 text-sm text-muted-foreground">
                          {t("create.steps.executionStep.noAccounts")}
                        </div>
                      )}
                    </SelectContent>
                  </Select>
                  {accounts && accounts.length === 0 && (
                    <p className="text-xs text-muted-foreground">
                      <Link
                        href="/accounts"
                        className="text-primary hover:underline"
                      >
                        {t("create.steps.executionStep.addAccount")}
                      </Link>
                    </p>
                  )}
                </div>
              )}

              {/* Mock Initial Balance (Mock Mode) */}
              {executionMode === "mock" && (
                <div className="space-y-2">
                  <Label>{t("fields.mockBalance")}</Label>
                  <Input
                    type="number"
                    value={mockInitialBalance}
                    onChange={(e) =>
                      setMockInitialBalance(parseFloat(e.target.value) || 0)
                    }
                    placeholder="10000"
                  />
                </div>
              )}

              {/* Execution Interval */}
              <div className="space-y-2">
                <Label>{t("fields.interval")}</Label>
                <Select
                  value={executionIntervalMinutes.toString()}
                  onValueChange={(v) =>
                    setExecutionIntervalMinutes(parseInt(v))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5 {t("create.minutes")}</SelectItem>
                    <SelectItem value="15">15 {t("create.minutes")}</SelectItem>
                    <SelectItem value="30">30 {t("create.minutes")}</SelectItem>
                    <SelectItem value="60">1 {t("create.hour")}</SelectItem>
                    <SelectItem value="240">4 {t("create.hours")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Auto Execute */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>{t("fields.autoExecute")}</Label>
                  <p className="text-xs text-muted-foreground">
                    {t("create.steps.reviewStep.autoExecuteDesc")}
                  </p>
                </div>
                <Switch
                  checked={autoExecute}
                  onCheckedChange={setAutoExecute}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Strategy Info Card (Read-only) */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                {tEdit("strategyInfo")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  {tEdit("strategyName")}
                </span>
                {agent.strategy_id ? (
                  <Link
                    href={`/strategies/${agent.strategy_id}`}
                    className="text-primary hover:underline text-sm flex items-center gap-1"
                  >
                    {agent.strategy_name || agent.strategy_id}
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                ) : (
                  <span className="text-sm">-</span>
                )}
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  {tEdit("strategyType")}
                </span>
                <Badge variant="outline" className="text-xs">
                  {agent.strategy_type?.toUpperCase() || "-"}
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground text-sm">
                  {tEdit("symbols")}
                </span>
                <div className="flex gap-1 flex-wrap justify-end">
                  {strategy?.symbols?.slice(0, 3).map((s) => (
                    <Badge
                      key={s}
                      variant="outline"
                      className="bg-primary/10 text-primary border-primary/30 font-mono text-xs py-0"
                    >
                      {s}
                    </Badge>
                  ))}
                  {(strategy?.symbols?.length ?? 0) > 3 &&
                    strategy?.symbols && (
                      <Badge
                        variant="outline"
                        className="bg-primary/10 text-primary border-primary/30 font-mono text-xs py-0"
                      >
                        +{strategy.symbols.length - 3}
                      </Badge>
                    )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground pt-2 border-t">
                {tEdit("strategyModifyHint")}
              </p>
            </CardContent>
          </Card>

          {/* Agent Info */}
          <Card className="bg-muted/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Info className="w-4 h-4 text-primary" />
                {tEdit("agentInfo")}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{tEdit("status")}</span>
                <span className="font-medium">
                  {t(`status.${agent.status}`)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {tEdit("created")}
                </span>
                <span className="font-medium text-xs">
                  {new Date(agent.created_at).toLocaleDateString()}
                </span>
              </div>
              {agent.total_pnl !== undefined && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    {t("stats.totalPL")}
                  </span>
                  <span
                    className={cn(
                      "font-medium font-mono text-xs",
                      agent.total_pnl >= 0 ? "text-profit" : "text-loss",
                    )}
                  >
                    {agent.total_pnl >= 0 ? "+" : ""}$
                    {agent.total_pnl.toFixed(2)}
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
                    {tEdit("changeWarningTitle")}
                  </p>
                  <p className="text-muted-foreground text-xs mt-1">
                    {tEdit("changeWarningDesc")}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

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
          onClick={handleSave}
          disabled={!isFormValid || isSubmitting}
        >
          {isSubmitting ? "Saving..." : tEdit("saveChanges")}
        </Button>
      </div>
    </div>
  );
}
