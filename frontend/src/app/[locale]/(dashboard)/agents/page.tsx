"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Plus,
  Play,
  Pause,
  MoreHorizontal,
  TrendingUp,
  TrendingDown,
  Bot,
  Filter,
  Loader2,
  Square,
  Pencil,
} from "lucide-react";
import {
  ListPageSkeleton,
  ListPageError,
  ListPageEmpty,
} from "@/components/list-page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useStrategies } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { StrategyResponse } from "@/lib/api";
import type { StrategyStatus, TradingMode, Timeframe, TimeHorizon } from "@/types";

function getStatusColor(status: StrategyStatus) {
  switch (status) {
    case "active":
      return "bg-[var(--profit)]/20 text-[var(--profit)]";
    case "paused":
      return "bg-[var(--warning)]/20 text-[var(--warning)]";
    case "stopped":
      return "bg-muted text-muted-foreground";
    case "error":
      return "bg-[var(--loss)]/20 text-[var(--loss)]";
    default:
      return "bg-muted text-muted-foreground";
  }
}

// Map trading_mode to a risk-profile style color
function getRiskProfileColor(mode: TradingMode) {
  switch (mode) {
    case "aggressive":
      return "border-red-500/30 text-red-500";
    case "balanced":
      return "border-amber-500/30 text-amber-500";
    case "conservative":
      return "border-emerald-500/30 text-emerald-500";
    default:
      return "";
  }
}

// Map trading_mode to a user-friendly risk profile label key
function getRiskProfileLabelKey(mode: TradingMode): string {
  switch (mode) {
    case "aggressive":
      return "aggressive";
    case "balanced":
      return "balanced";
    case "conservative":
    default:
      return "conservative";
  }
}

// Infer time horizon from stored timeframes array
function inferTimeHorizon(timeframes: Timeframe[]): TimeHorizon {
  if (!timeframes || timeframes.length === 0) return "swing";
  const hasShort = timeframes.some((tf) => ["1m", "5m"].includes(tf));
  const hasLong = timeframes.some((tf) => ["4h", "1d"].includes(tf));
  const hasMid = timeframes.some((tf) => ["15m", "30m", "1h"].includes(tf));
  // If the shortest timeframe is 1m/5m and no daily frames -> scalp
  if (hasShort && !hasLong) return "scalp";
  // If the longest is 4h/1d and no very short frames -> position
  if (hasLong && !hasShort && !hasMid) return "position";
  // Default -> swing
  return "swing";
}

function getTimeHorizonColor(horizon: TimeHorizon) {
  switch (horizon) {
    case "scalp":
      return "border-amber-500/30 text-amber-500";
    case "swing":
      return "border-violet-500/30 text-violet-500";
    case "position":
      return "border-cyan-500/30 text-cyan-500";
    default:
      return "";
  }
}

interface AgentCardProps {
  agent: StrategyResponse;
  onStatusChange: (id: string, status: StrategyStatus) => void;
  onDelete: (id: string) => void;
  t: ReturnType<typeof useTranslations>;
}

function AgentCard({ agent, onStatusChange, onDelete, t }: AgentCardProps) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  const handleStatusChange = async (newStatus: StrategyStatus) => {
    setIsUpdating(true);
    try {
      await onStatusChange(agent.id, newStatus);
    } finally {
      setIsUpdating(false);
    }
  };

  const config = agent.config as Record<string, unknown>;
  const riskControls = (config?.risk_controls as Record<string, number>) || {};
  const maxLeverage = riskControls.max_leverage || 1;
  const timeframes = (config?.timeframes as Timeframe[]) || [];
  const timeHorizon = inferTimeHorizon(timeframes);
  const preset = config?.preset as string | undefined;
  const isCustomPreset = preset === "custom";

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors gap-3">
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between overflow-hidden">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  variant="outline"
                  className={cn("text-xs", getStatusColor(agent.status))}
                >
                  {t(`status.${agent.status}`)}
                </Badge>
                {isCustomPreset ? (
                  <Badge variant="outline" className="text-xs">
                    {t("mode.custom")}
                  </Badge>
                ) : (
                  <>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", getRiskProfileColor(agent.trading_mode))}
                    >
                      {t(`mode.${getRiskProfileLabelKey(agent.trading_mode)}`)}
                    </Badge>
                    <Badge
                      variant="outline"
                      className={cn("text-xs", getTimeHorizonColor(timeHorizon))}
                    >
                      {t(`timeHorizon.${timeHorizon}`)}
                    </Badge>
                  </>
                )}
              </div>
              <p className="text-sm text-muted-foreground truncate mt-1">
                {agent.description || t("empty.noDescription")}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link href={`/agents/${agent.id}/edit`} className="flex items-center">
                  <Pencil className="w-4 h-4 mr-2" />
                  {t("actions.edit")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem>{t("actions.duplicate")}</DropdownMenuItem>
              <DropdownMenuItem>{t("actions.viewDecisions")}</DropdownMenuItem>
              <DropdownMenuItem
                className={agent.status === "stopped" ? "text-destructive" : "text-muted-foreground"}
                disabled={agent.status !== "stopped"}
                onClick={() => agent.status === "stopped" && onDelete(agent.id)}
              >
                {t("actions.delete")}
                {agent.status !== "stopped" && (
                  <span className="ml-1 text-xs">({t("actions.deleteRequireStopped")})</span>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 pt-2 border-t border-border/30">
          <div>
            <p className="text-xs text-muted-foreground">{t("stats.totalPL")}</p>
            {agent.total_pnl !== undefined ? (
              <p
                className={cn(
                  "font-mono font-semibold flex items-center gap-1",
                  agent.total_pnl >= 0
                    ? "text-[var(--profit)]"
                    : "text-[var(--loss)]"
                )}
              >
                {agent.total_pnl >= 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                ${Math.abs(agent.total_pnl).toLocaleString()}
              </p>
            ) : (
              <p className="text-muted-foreground">—</p>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("stats.winRate")}</p>
            {agent.win_rate !== undefined ? (
              <p className="font-mono font-semibold">
                {agent.win_rate.toFixed(1)}%
              </p>
            ) : (
              <p className="text-muted-foreground">—</p>
            )}
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("stats.maxLeverage")}</p>
            <p className="font-mono font-semibold">{maxLeverage}x</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {agent.status === "active" ? (
            <Button
              variant="default"
              size="sm"
              className="flex-1 bg-primary/20 text-primary hover:bg-primary/30"
              onClick={() => handleStatusChange("paused")}
              disabled={isUpdating}
            >
              {isUpdating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Pause className="w-4 h-4 mr-2" />
              )}
              {t("actions.pause")}
            </Button>
          ) : agent.status === "paused" || agent.status === "draft" ? (
            <>
              <Button
                variant="default"
                size="sm"
                className="flex-1"
                onClick={() => handleStatusChange("active")}
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                {agent.status === "draft" ? t("actions.start") : t("actions.resume")}
              </Button>
              {agent.status === "paused" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                  onClick={() => setShowStopConfirm(true)}
                  disabled={isUpdating}
                >
                  <Square className="w-4 h-4 mr-2" />
                  {t("actions.stop")}
                </Button>
              )}
            </>
          ) : null}
          <Link href={`/agents/${agent.id}`}>
            <Button variant="ghost" size="sm">
              {t("actions.viewDetails")}
            </Button>
          </Link>

          {/* Stop Confirm Dialog */}
          <Dialog open={showStopConfirm} onOpenChange={setShowStopConfirm}>
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>{t("actions.stopConfirmTitle")}</DialogTitle>
                <DialogDescription>{t("actions.stopConfirmDesc")}</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowStopConfirm(false)}>
                  {t("actions.cancel")}
                </Button>
                <Button
                  variant="destructive"
                  onClick={async () => {
                    setShowStopConfirm(false);
                    await handleStatusChange("stopped");
                  }}
                  disabled={isUpdating}
                >
                  {isUpdating ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  {t("actions.confirmStop")}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AgentsPage() {
  const t = useTranslations("agents");
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { strategies, error, isLoading, refresh } = useStrategies();

  // Toast notifications
  const toast = useToast();

  // Status update handler
  const handleStatusChange = async (id: string, status: StrategyStatus) => {
    try {
      const { strategiesApi } = await import("@/lib/api");
      await strategiesApi.updateStatus(id, status);
      refresh();
      const statusKey = status === 'active' ? 'started' : status;
      toast.success(t(`toast.${statusKey}`));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.updateFailed");
      toast.error(t("toast.updateFailed"), message);
    }
  };

  // Delete handler
  const handleDelete = async (id: string) => {
    if (!confirm(t("confirmDelete"))) return;

    try {
      const { strategiesApi } = await import("@/lib/api");
      await strategiesApi.delete(id);
      refresh();
      toast.success(t("toast.deleteSuccess"));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.deleteFailed");
      toast.error(t("toast.deleteFailed"), message);
    }
  };

  const filteredAgents = strategies.filter((a) => {
    const matchesFilter = filter === "all" || a.status === filter;
    const matchesSearch = a.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const hasNoAgents = !isLoading && !error && strategies.length === 0;

  return (
    <div className="space-y-6">
      {/* Page Header - always show CTA */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link href="/agents/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t("createAgent")}
          </Button>
        </Link>
      </div>

      {/* Info Card */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="flex items-center gap-4 py-4">
          <div className="p-3 rounded-full bg-primary/10">
            <Bot className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{t("info.title")}</h3>
            <p className="text-sm text-muted-foreground">{t("info.description")}</p>
          </div>
        </CardContent>
      </Card>

      {/* Filters - only when has data */}
      {!hasNoAgents && (
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-muted/50"
            />
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 bg-muted/50">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("filter.allStatus")}</SelectItem>
              <SelectItem value="active">{t("filter.active")}</SelectItem>
              <SelectItem value="paused">{t("filter.paused")}</SelectItem>
              <SelectItem value="draft">{t("filter.draft")}</SelectItem>
              <SelectItem value="stopped">{t("filter.stopped")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Loading */}
      {isLoading && <ListPageSkeleton />}

      {/* Error */}
      {error && (
        <ListPageError
          message={error.message || t("error.loadFailed")}
          onRetry={() => refresh()}
          retryLabel={t("retry")}
        />
      )}

      {/* Empty - no agents at all */}
      {hasNoAgents && (
        <ListPageEmpty
          icon={Bot}
          title={t("empty.title")}
          description={t("empty.description")}
          actionLabel={t("empty.createFirst")}
          actionHref="/agents/new"
          actionIcon={Plus}
        />
      )}

      {/* Agent Cards + Add card when has data */}
      {!isLoading && !error && strategies.length > 0 && (
        <>
          {filteredAgents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                  t={t}
                />
              ))}
              <Link href="/agents/new" className="block h-full">
                <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardContent className="flex flex-col items-center justify-center h-full min-h-0 py-8 text-muted-foreground hover:text-foreground transition-colors">
                    <div className="p-3 rounded-full bg-muted/30 mb-3">
                      <Plus className="w-6 h-6" />
                    </div>
                    <p className="font-medium">{t("createAgent")}</p>
                    <p className="text-sm text-center mt-1 text-muted-foreground">
                      {t("empty.description")}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </div>
          ) : (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <div className="p-4 rounded-full bg-muted/50 mb-4">
                  <Bot className="w-8 h-8 text-muted-foreground" />
                </div>
                <h3 className="text-lg font-semibold mb-2">{t("empty.title")}</h3>
                <p className="text-muted-foreground text-center mb-4">
                  {t("empty.searchHint")}
                </p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
