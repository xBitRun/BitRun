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
  LineChart,
  Grid3X3,
  ArrowDownUp,
  Activity,
  Filter,
  Loader2,
  Square,
  RotateCcw,
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
import { useQuantStrategies } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { StrategyStatus } from "@/types";
import type { QuantStrategyApiResponse } from "@/lib/api";

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

function getTypeIcon(type: string) {
  switch (type) {
    case "grid":
      return Grid3X3;
    case "dca":
      return ArrowDownUp;
    case "rsi":
      return Activity;
    default:
      return LineChart;
  }
}

function getTypeColor(type: string) {
  switch (type) {
    case "grid":
      return "border-blue-500/30 text-blue-500";
    case "dca":
      return "border-emerald-500/30 text-emerald-500";
    case "rsi":
      return "border-violet-500/30 text-violet-500";
    default:
      return "";
  }
}

interface StrategyCardProps {
  strategy: QuantStrategyApiResponse;
  onStatusChange: (id: string, status: StrategyStatus) => void;
  onDelete: (id: string) => void;
  t: ReturnType<typeof useTranslations>;
}

function StrategyCard({ strategy, onStatusChange, onDelete, t }: StrategyCardProps) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const TypeIcon = getTypeIcon(strategy.strategy_type);

  const handleStatusChange = async (newStatus: StrategyStatus) => {
    setIsUpdating(true);
    try {
      await onStatusChange(strategy.id, newStatus);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors gap-3">
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between overflow-hidden">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 shrink-0">
              <TypeIcon className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-lg">{strategy.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1">
                <Badge
                  variant="outline"
                  className={cn("text-xs", getStatusColor(strategy.status as StrategyStatus))}
                >
                  {t(`status.${strategy.status}`)}
                </Badge>
                <Badge
                  variant="outline"
                  className={cn("text-xs", getTypeColor(strategy.strategy_type))}
                >
                  {t(`types.${strategy.strategy_type}`)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {strategy.symbol}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground truncate mt-1">
                {strategy.description || t("empty.noDescription")}
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
              <DropdownMenuItem
                className={["stopped", "draft"].includes(strategy.status) ? "text-destructive" : "text-muted-foreground"}
                disabled={!["stopped", "draft"].includes(strategy.status)}
                onClick={() => ["stopped", "draft"].includes(strategy.status) && onDelete(strategy.id)}
              >
                {t("actions.delete")}
                {!["stopped", "draft"].includes(strategy.status) && (
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
            <p
              className={cn(
                "font-mono font-semibold flex items-center gap-1",
                strategy.total_pnl >= 0
                  ? "text-[var(--profit)]"
                  : "text-[var(--loss)]"
              )}
            >
              {strategy.total_pnl >= 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              ${Math.abs(strategy.total_pnl).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("stats.winRate")}</p>
            <p className="font-mono font-semibold">
              {strategy.win_rate.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("stats.trades")}</p>
            <p className="font-mono font-semibold">{strategy.total_trades}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {strategy.status === "active" ? (
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
          ) : strategy.status === "paused" || strategy.status === "draft" ? (
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
                {strategy.status === "draft" ? t("actions.start") : t("actions.resume")}
              </Button>
              {strategy.status === "paused" && (
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
          ) : (strategy.status === "error" || strategy.status === "warning") ? (
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
                  <RotateCcw className="w-4 h-4 mr-2" />
                )}
                {t("actions.restart")}
              </Button>
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
            </>
          ) : null}
          <Link href={`/strategies/${strategy.id}`}>
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

export default function QuantStrategiesPage() {
  const t = useTranslations("quantStrategies");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { strategies, error, isLoading, refresh } = useQuantStrategies();
  const toast = useToast();

  const handleStatusChange = async (id: string, status: StrategyStatus) => {
    try {
      const { quantStrategiesApi } = await import("@/lib/api");
      await quantStrategiesApi.updateStatus(id, status);
      refresh();
      const statusKey = status === "active" ? "started" : status;
      toast.success(t(`toast.${statusKey}`));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.updateFailed");
      toast.error(t("toast.updateFailed"), message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("confirmDelete"))) return;
    try {
      const { quantStrategiesApi } = await import("@/lib/api");
      await quantStrategiesApi.delete(id);
      refresh();
      toast.success(t("toast.deleteSuccess"));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.deleteFailed");
      toast.error(t("toast.deleteFailed"), message);
    }
  };

  const filteredStrategies = strategies.filter((s) => {
    const matchesStatus = statusFilter === "all" || s.status === statusFilter;
    const matchesType = typeFilter === "all" || s.strategy_type === typeFilter;
    const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesType && matchesSearch;
  });

  const hasNoStrategies = !isLoading && !error && strategies.length === 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link href="/strategies/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t("createStrategy")}
          </Button>
        </Link>
      </div>

      {/* Info Card */}
      <Card className="bg-primary/5 border-primary/20">
        <CardContent className="flex items-center gap-4 py-4">
          <div className="p-3 rounded-full bg-primary/10">
            <LineChart className="w-6 h-6 text-primary" />
          </div>
          <div>
            <h3 className="font-semibold">{t("info.title")}</h3>
            <p className="text-sm text-muted-foreground">{t("info.description")}</p>
          </div>
        </CardContent>
      </Card>

      {/* Filters */}
      {!hasNoStrategies && (
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-muted/50"
            />
          </div>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
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
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40 bg-muted/50">
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("filter.allTypes")}</SelectItem>
              <SelectItem value="grid">{t("types.grid")}</SelectItem>
              <SelectItem value="dca">{t("types.dca")}</SelectItem>
              <SelectItem value="rsi">{t("types.rsi")}</SelectItem>
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

      {/* Empty */}
      {hasNoStrategies && (
        <ListPageEmpty
          icon={LineChart}
          title={t("empty.title")}
          description={t("empty.description")}
          actionLabel={t("empty.createFirst")}
          actionHref="/strategies/new"
          actionIcon={Plus}
        />
      )}

      {/* Strategy Cards */}
      {!isLoading && !error && strategies.length > 0 && (
        <>
          {filteredStrategies.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredStrategies.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                  t={t}
                />
              ))}
              <Link href="/strategies/new" className="block h-full">
                <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardContent className="flex flex-col items-center justify-center h-full min-h-0 py-8 text-muted-foreground hover:text-foreground transition-colors">
                    <div className="p-3 rounded-full bg-muted/30 mb-3">
                      <Plus className="w-6 h-6" />
                    </div>
                    <p className="font-medium">{t("createStrategy")}</p>
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
                  <LineChart className="w-8 h-8 text-muted-foreground" />
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
