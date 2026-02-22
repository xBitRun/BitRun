"use client";

import { use, useState } from "react";
import { useTranslations } from "next-intl";
import { useLocale } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  Grid3X3,
  ArrowDownUp,
  Activity,
  LineChart,
  Loader2,
  Trash2,
  Bot,
  Zap,
  Pencil,
  Copy,
  Share2,
  Settings,
  FileText,
  Users,
  Globe,
  Lock,
  type LucideIcon,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useStrategy, useDeleteStrategy, useStrategyVersions, useDuplicateStrategy } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { DetailPageHeader } from "@/components/layout";
import type { StrategyType } from "@/types";

// Icon mapping - defined at module level to avoid creating components during render
const TYPE_ICONS: Record<StrategyType, LucideIcon> = {
  ai: Bot,
  grid: Grid3X3,
  dca: ArrowDownUp,
  rsi: Activity,
};

function getTypeColor(type: StrategyType) {
  switch (type) {
    case "ai":
      return "border-rose-500/30 text-rose-500";
    case "grid":
      return "border-blue-500/30 text-blue-500";
    case "dca":
      return "border-emerald-500/30 text-emerald-500";
    case "rsi":
      return "border-amber-500/30 text-amber-500";
    default:
      return "";
  }
}

function getVisibilityColor(visibility: string) {
  return visibility === "public"
    ? "border-emerald-500/30 text-emerald-500"
    : "border-muted-foreground/30 text-muted-foreground";
}

// Config key labels - translation keys for i18n
const configKeyTranslationKeys: Record<string, string> = {
  // AI 策略参数
  prompt: "prompt",
  trading_mode: "trading_mode",
  language: "language",
  prompt_mode: "prompt_mode",
  custom_prompt: "custom_prompt",
  advanced_prompt: "advanced_prompt",
  prompt_sections: "prompt_sections",
  debate_enabled: "debate_enabled",
  debate_models: "debate_models",
  debate_consensus_mode: "debate_consensus_mode",
  debate_min_participants: "debate_min_participants",
  symbols: "symbols",
  timeframes: "timeframes",
  indicators: "indicators",
  // 网格策略参数
  upper_price: "upper_price",
  lower_price: "lower_price",
  grid_count: "grid_count",
  total_investment: "total_investment",
  leverage: "leverage",
  // DCA 策略参数
  order_amount: "order_amount",
  interval_minutes: "interval_minutes",
  take_profit_percent: "take_profit_percent",
  total_budget: "total_budget",
  max_orders: "max_orders",
  // RSI 策略参数
  rsi_period: "rsi_period",
  overbought_threshold: "overbought_threshold",
  oversold_threshold: "oversold_threshold",
  timeframe: "timeframe",
  // 风控参数
  max_leverage: "max_leverage",
  max_position_ratio: "max_position_ratio",
  max_total_exposure: "max_total_exposure",
  min_risk_reward_ratio: "min_risk_reward_ratio",
  max_drawdown_percent: "max_drawdown_percent",
  min_confidence: "min_confidence",
  default_sl_atr_multiplier: "default_sl_atr_multiplier",
  default_tp_atr_multiplier: "default_tp_atr_multiplier",
  max_sl_percent: "max_sl_percent",
};

// Get translated config key label
function getConfigKeyLabel(
  key: string,
  t: ReturnType<typeof useTranslations<"strategies.configKeys">>,
): string {
  const translationKey = configKeyTranslationKeys[key];
  if (translationKey) {
    return t(translationKey);
  }
  return key.replace(/_/g, " ");
}

// Format date
function formatDate(dateString: string, locale: string): string {
  const localeCode = locale === "zh" ? "zh-CN" : "en-US";
  return new Date(dateString).toLocaleDateString(localeCode, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Info row component for consistent styling
function InfoRow({
  label,
  children,
  className,
}: {
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-center justify-between py-2", className)}>
      <span className="text-sm text-muted-foreground">{label}</span>
      <div className="text-sm">{children}</div>
    </div>
  );
}

export default function StrategyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("strategies");
  const tConfigKeys = useTranslations("strategies.configKeys");
  const tType = useTranslations("strategies.type");
  const locale = useLocale();
  const router = useRouter();
  const toast = useToast();

  const { data: strategy, error, isLoading } = useStrategy(id);
  const { trigger: deleteStrategy, isMutating: isDeleting } =
    useDeleteStrategy(id);
  const { data: versions } = useStrategyVersions(id);
  const { trigger: duplicateStrategy, isMutating: isDuplicating } =
    useDuplicateStrategy();

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  // Get icon component from static mapping
  const StrategyIcon = strategy ? TYPE_ICONS[strategy.type] : LineChart;

  // Config value renderer - supports JSON object formatting
  const renderConfigValue = (value: unknown): React.ReactNode => {
    if (value === null || value === undefined) return "-";
    if (typeof value === "boolean")
      return value ? tConfigKeys("yes") : tConfigKeys("no");
    if (typeof value === "number") return value.toLocaleString();
    if (Array.isArray(value)) {
      return (
        <code className="text-xs bg-muted/50 px-1.5 py-0.5 rounded">
          {JSON.stringify(value)}
        </code>
      );
    }
    if (typeof value === "object") {
      return (
        <code className="text-xs bg-muted/50 px-1.5 py-0.5 rounded block max-w-xs overflow-auto whitespace-pre">
          {JSON.stringify(value, null, 2)}
        </code>
      );
    }
    return String(value);
  };

  const handleDelete = async () => {
    try {
      await deleteStrategy();
      toast.success(t("toast.deleted"));
      router.push("/strategies");
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("error.deleteFailed");
      toast.error(t("error.deleteFailed"), message);
    }
  };

  const handleCopyId = () => {
    if (strategy) {
      navigator.clipboard.writeText(strategy.id);
      toast.success(t("detail.idCopied"));
    }
  };

  const handleShare = () => {
    if (strategy && typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      toast.success(t("detail.linkCopied"));
    }
  };

  const handleDuplicate = async () => {
    if (!strategy) return;
    try {
      const newStrategy = await duplicateStrategy({ strategyId: strategy.id });
      toast.success(t("detail.duplicateSuccess"));
      router.push(`/strategies/${newStrategy.id}/edit`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("detail.duplicateError");
      toast.error(t("detail.duplicateError"), message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !strategy) {
    return (
      <div className="space-y-4 max-w-3xl mx-auto">
        <Button variant="ghost" onClick={() => router.push("/strategies")}>
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t("detail.backToStrategies")}
        </Button>
        <Card className="bg-card/50">
          <CardContent className="flex items-center justify-center py-12">
            <p className="text-muted-foreground">{t("detail.notFound")}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const config = strategy.config || {};
  const hasCommonParams: boolean =
    Object.keys(config).filter((k) => k !== "riskControls").length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <DetailPageHeader
        backHref="/strategies"
        icon={<StrategyIcon className="w-6 h-6 text-primary" />}
        title={strategy.name}
        description={strategy.description ?? undefined}
        badges={[
          {
            label: tType(strategy.type),
            className: getTypeColor(strategy.type),
          },
          {
            label: t(`visibility.${strategy.visibility}`),
            className: getVisibilityColor(strategy.visibility),
          },
        ]}
        primaryActions={
          <>
            <Button variant="outline" asChild>
              <Link href={`/strategies/${strategy.id}/edit`}>
                <Pencil className="w-4 h-4 mr-2" />
                {t("detail.actions.edit")}
              </Link>
            </Button>
            <Button asChild>
              <Link href={`/agents/new?strategyId=${strategy.id}`}>
                <Zap className="w-4 h-4 mr-2" />
                {t("actions.createAgent")}
              </Link>
            </Button>
          </>
        }
        moreMenuItems={[
          {
            label: t("detail.actions.copyId"),
            icon: <Copy className="w-4 h-4" />,
            onClick: handleCopyId,
          },
          {
            label: t("detail.actions.duplicate"),
            icon: <Copy className="w-4 h-4" />,
            onClick: handleDuplicate,
            disabled: isDuplicating,
          },
          {
            label: t("detail.actions.share"),
            icon: <Share2 className="w-4 h-4" />,
            onClick: handleShare,
          },
        ]}
      />

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="overview">
            <FileText className="w-4 h-4 mr-1.5" />
            {t("detail.tabs.overview")}
          </TabsTrigger>
          <TabsTrigger value="config">
            <Settings className="w-4 h-4 mr-1.5" />
            {t("detail.tabs.config")}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="w-4 h-4 mr-1.5" />
            {t("detail.tabs.settings")}
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="mt-6">
          <>
            {/* Strategy Info Card */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  {t("detail.overview.strategyInfo")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <InfoRow label={t("detail.overview.strategyType")}>
                  <Badge
                    variant="outline"
                    className={cn("text-xs", getTypeColor(strategy.type))}
                  >
                    {tType(strategy.type)}
                  </Badge>
                </InfoRow>
                <InfoRow label={t("detail.overview.symbols")}>
                  <div className="flex flex-wrap gap-1.5 justify-end">
                    {strategy.symbols.length > 0 ? (
                      strategy.symbols.map((symbol) => (
                        <Badge
                          key={symbol}
                          variant="outline"
                          className="bg-primary/10 text-primary border-primary/30 font-mono text-xs py-0"
                        >
                          {symbol}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-muted-foreground">
                        {t("empty.noSymbol")}
                      </span>
                    )}
                  </div>
                </InfoRow>
                <InfoRow label={t("detail.sidebar.created")}>
                  <span className="font-mono text-xs">
                    {formatDate(strategy.created_at, locale)}
                  </span>
                </InfoRow>
                <InfoRow label={t("detail.sidebar.updated")}>
                  <span className="font-mono text-xs">
                    {formatDate(strategy.updated_at, locale)}
                  </span>
                </InfoRow>
              </CardContent>
            </Card>

            {/* Marketplace Info Card */}
            <Card className="bg-card/50 backdrop-blur-sm border-border/50 mt-4">
              <CardHeader className="pb-2">
                <CardTitle className="text-base">
                  {t("edit.marketplaceSection")}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-1">
                <InfoRow label={t("detail.overview.visibility")}>
                  <div className="flex items-center gap-1.5">
                    {strategy.visibility === "public" ? (
                      <Globe className="w-3.5 h-3.5 text-emerald-500" />
                    ) : (
                      <Lock className="w-3.5 h-3.5 text-muted-foreground" />
                    )}
                    <span>{t(`visibility.${strategy.visibility}`)}</span>
                  </div>
                </InfoRow>
                {strategy.category && (
                  <InfoRow label={t("edit.category")}>
                    <Badge variant="outline" className="text-xs">
                      {strategy.category}
                    </Badge>
                  </InfoRow>
                )}
                <InfoRow label={t("edit.tags")}>
                  <div className="flex flex-wrap gap-1.5 justify-end">
                    {strategy.tags.length > 0 ? (
                      strategy.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-muted-foreground">
                        {t("edit.noTags")}
                      </span>
                    )}
                  </div>
                </InfoRow>
                {strategy.visibility === "public" && (
                  <>
                    <InfoRow label={t("edit.isPaid")}>
                      <Badge variant={strategy.is_paid ? "default" : "outline"} className="text-xs">
                        {strategy.is_paid ? tConfigKeys("yes") : tConfigKeys("no")}
                      </Badge>
                    </InfoRow>
                    {strategy.is_paid && strategy.price_monthly && (
                      <InfoRow label={t("pricing.monthlyPrice")}>
                        <span className="font-semibold">
                          ${strategy.price_monthly}
                        </span>
                      </InfoRow>
                    )}
                  </>
                )}
                <div className="pt-2 border-t border-border/50 mt-2">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        {t("stats.forkCount")}:
                      </span>
                      <span className="text-sm font-medium">{strategy.fork_count}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm text-muted-foreground">
                        {t("stats.agentCount")}:
                      </span>
                      <span className="text-sm font-medium">{strategy.agent_count}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Version History */}
            {versions && versions.length > 0 && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50 mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    {t("versions.title")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1">
                    {versions.slice(0, 5).map((version) => (
                      <div
                        key={version.version}
                        className="flex items-center justify-between py-1.5 border-b border-border/30 last:border-0"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-medium">
                            v{version.version}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {formatDate(version.created_at, locale)}
                          </span>
                        </div>
                        {version.change_note && (
                          <span className="text-xs text-muted-foreground truncate max-w-[200px]">
                            {version.change_note}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        </TabsContent>

        {/* Config Tab */}
        <TabsContent value="config" className="mt-6">
          <>
            {/* Common Parameters */}
            {hasCommonParams && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    {t("detail.config.commonParams")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {Object.entries(config)
                    .filter(
                      ([key]) => key !== "riskControls" && key !== "prompt",
                    )
                    .map(([key, value]) => (
                      <InfoRow key={key} label={getConfigKeyLabel(key, tConfigKeys)}>
                        <span className="font-mono text-xs">
                          {renderConfigValue(value)}
                        </span>
                      </InfoRow>
                    ))}
                </CardContent>
              </Card>
            )}

            {/* Prompt Preview (AI Strategy Only) */}
            {strategy.type === "ai" && config.prompt && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50 mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    {t("detail.config.promptPreview")}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="p-3 rounded-lg bg-muted/30 max-h-64 overflow-auto">
                    <pre className="text-xs whitespace-pre-wrap break-words font-mono">
                      {config.prompt as string}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Risk Controls */}
            {config.riskControls && typeof config.riskControls === "object" && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50 mt-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">
                    {t("detail.config.riskControls")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1">
                  {Object.entries(
                    config.riskControls as Record<string, unknown>,
                  ).map(([key, value]) => (
                    <InfoRow key={key} label={getConfigKeyLabel(key, tConfigKeys)}>
                      <span className="font-mono text-xs">
                        {renderConfigValue(value)}
                      </span>
                    </InfoRow>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* No config message */}
            {Object.keys(config).length === 0 && (
              <Card className="bg-card/50 backdrop-blur-sm border-border/50">
                <CardContent className="flex items-center justify-center py-12">
                  <p className="text-sm text-muted-foreground">
                    {t("detail.config.noConfig")}
                  </p>
                </CardContent>
              </Card>
            )}
          </>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="mt-6">
          <Card className="bg-card/50 border-[var(--loss)]/30">
            <CardHeader>
              <CardTitle className="text-base text-[var(--loss)]">
                {t("detail.settings.dangerZone")}
              </CardTitle>
              <CardDescription className="text-sm">
                {t("detail.settings.deleteConfirm")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                onClick={() => setShowDeleteConfirm(true)}
                disabled={isDeleting}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t("detail.settings.deleteStrategy")}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Delete Confirm Dialog */}
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>{t("detail.settings.deleteConfirmTitle")}</DialogTitle>
            <DialogDescription>
              {t("detail.settings.deleteConfirmDesc")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteConfirm(false)}
            >
              {t("actions.cancel")}
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                setShowDeleteConfirm(false);
                handleDelete();
              }}
              disabled={isDeleting}
            >
              {isDeleting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Trash2 className="w-4 h-4 mr-2" />
              )}
              {t("detail.settings.confirmDelete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
