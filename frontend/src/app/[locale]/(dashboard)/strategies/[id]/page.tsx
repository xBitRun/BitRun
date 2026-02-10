"use client";

import { use, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import {
  ArrowLeft,
  Play,
  Pause,
  Square,
  RefreshCw,
  Grid3X3,
  ArrowDownUp,
  Activity,
  LineChart,
  Loader2,
  Trash2,
  Clock,
  RotateCcw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { useQuantStrategy } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import { TradingViewChart } from "@/components/charts/tradingview-chart";
import type { StrategyStatus } from "@/types";
import type { QuantStrategyApiResponse } from "@/lib/api";

function getStatusColor(status: string) {
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

// ============ Quant Trade Section (runtime_state visualization) ============

function QuantTradeSection({
  strategy,
  t,
}: {
  strategy: QuantStrategyApiResponse;
  t: ReturnType<typeof useTranslations>;
}) {
  const runtimeState = strategy.runtime_state as Record<string, unknown>;
  const hasRuntimeState = Object.keys(runtimeState).length > 0;

  if (!hasRuntimeState && strategy.total_trades === 0) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <div className="p-4 rounded-full bg-muted/50 mb-4">
            <LineChart className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">{t("detail.overview.tradeList")}</h3>
          <p className="text-muted-foreground text-center text-sm">
            {t("detail.overview.noTradeDataHint")}
          </p>
        </CardContent>
      </Card>
    );
  }

  // Grid Strategy — show grid levels table
  if (strategy.strategy_type === "grid" && hasRuntimeState) {
    const gridLevels = (runtimeState.grid_levels as number[]) || [];
    const filledBuys = new Set((runtimeState.filled_buys as string[]) || []);
    const filledSells = new Set((runtimeState.filled_sells as string[]) || []);
    const totalInvested = (runtimeState.total_invested as number) || 0;
    const totalReturned = (runtimeState.total_returned as number) || 0;
    const lastPrice = (runtimeState.last_price as number) || 0;
    const lastCheck = runtimeState.last_check as string | undefined;

    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Grid3X3 className="w-5 h-5 text-primary" />
              {t("detail.overview.gridLevels")}
            </CardTitle>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              {lastPrice > 0 && (
                <span>{t("detail.overview.gridLastPrice")}: <span className="font-mono font-medium text-foreground">${lastPrice.toLocaleString()}</span></span>
              )}
              {lastCheck && (
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(lastCheck).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Summary metrics */}
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.gridTotalInvested")}</p>
              <p className="font-mono font-bold">${totalInvested.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.gridTotalReturned")}</p>
              <p className="font-mono font-bold">${totalReturned.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.totalPnl")}</p>
              <p className={cn("font-mono font-bold", (totalReturned - totalInvested) >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]")}>
                {(totalReturned - totalInvested) >= 0 ? "+" : ""}${(totalReturned - totalInvested).toLocaleString()}
              </p>
            </div>
          </div>

          {/* Grid levels table */}
          {gridLevels.length > 0 && (
            <div className="max-h-80 overflow-y-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/50">
                    <TableHead className="text-xs">{t("detail.overview.gridLevel")}</TableHead>
                    <TableHead className="text-xs text-right">{t("detail.overview.gridPrice")}</TableHead>
                    <TableHead className="text-xs text-center">{t("detail.overview.gridBuyStatus")}</TableHead>
                    <TableHead className="text-xs text-center">{t("detail.overview.gridSellStatus")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {gridLevels.map((price, idx) => (
                    <TableRow key={idx} className="border-border/30">
                      <TableCell className="font-mono text-xs">#{idx + 1}</TableCell>
                      <TableCell className="font-mono text-xs text-right">${price.toLocaleString()}</TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            filledBuys.has(String(idx))
                              ? "bg-[var(--profit)]/10 text-[var(--profit)] border-[var(--profit)]/30"
                              : "bg-muted text-muted-foreground"
                          )}
                        >
                          {filledBuys.has(String(idx)) ? t("detail.overview.gridFilled") : t("detail.overview.gridPending")}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            filledSells.has(String(idx))
                              ? "bg-[var(--loss)]/10 text-[var(--loss)] border-[var(--loss)]/30"
                              : "bg-muted text-muted-foreground"
                          )}
                        >
                          {filledSells.has(String(idx)) ? t("detail.overview.gridFilled") : t("detail.overview.gridPending")}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  // DCA Strategy — show DCA state
  if (strategy.strategy_type === "dca" && hasRuntimeState) {
    const ordersPlaced = (runtimeState.orders_placed as number) || 0;
    const totalInvested = (runtimeState.total_invested as number) || 0;
    const totalQuantity = (runtimeState.total_quantity as number) || 0;
    const avgCost = (runtimeState.avg_cost as number) || 0;
    const lastOrderTime = runtimeState.last_order_time as string | undefined;
    const lastCheck = runtimeState.last_check as string | undefined;

    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <ArrowDownUp className="w-5 h-5 text-primary" />
              {t("detail.overview.tradeList")}
            </CardTitle>
            {lastCheck && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t("detail.overview.lastCheck")}: {new Date(lastCheck).toLocaleString()}
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.dcaOrdersPlaced")}</p>
              <p className="text-xl font-mono font-bold">{ordersPlaced}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.dcaTotalInvested")}</p>
              <p className="text-xl font-mono font-bold">${totalInvested.toLocaleString()}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.dcaTotalQuantity")}</p>
              <p className="text-xl font-mono font-bold">{totalQuantity}</p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.dcaAvgCost")}</p>
              <p className="text-xl font-mono font-bold">${avgCost.toLocaleString()}</p>
            </div>
            {lastOrderTime && (
              <div className="p-3 rounded-lg bg-muted/30">
                <p className="text-xs text-muted-foreground">{t("detail.overview.dcaLastOrderTime")}</p>
                <p className="text-sm font-mono">{new Date(lastOrderTime).toLocaleString()}</p>
              </div>
            )}
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.totalPnl")}</p>
              <p className={cn(
                "text-xl font-mono font-bold",
                strategy.total_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"
              )}>
                {strategy.total_pnl >= 0 ? "+" : ""}${strategy.total_pnl.toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // RSI Strategy — show RSI state
  if (strategy.strategy_type === "rsi" && hasRuntimeState) {
    const hasPosition = (runtimeState.has_position as boolean) || false;
    const entryPrice = (runtimeState.entry_price as number) || 0;
    const positionSizeUsd = (runtimeState.position_size_usd as number) || 0;
    const lastRsi = (runtimeState.last_rsi as number) || 0;
    const lastSignal = (runtimeState.last_signal as string) || "";
    const lastPrice = (runtimeState.last_price as number) || 0;
    const lastCheck = runtimeState.last_check as string | undefined;

    return (
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="w-5 h-5 text-primary" />
              {t("detail.overview.tradeList")}
            </CardTitle>
            {lastCheck && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {t("detail.overview.lastCheck")}: {new Date(lastCheck).toLocaleString()}
              </span>
            )}
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.rsiHasPosition")}</p>
              <p className="text-xl font-mono font-bold">
                {hasPosition ? t("detail.overview.rsiYes") : t("detail.overview.rsiNo")}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.rsiLastRsi")}</p>
              <p className={cn(
                "text-xl font-mono font-bold",
                lastRsi >= 70 ? "text-[var(--loss)]" : lastRsi <= 30 ? "text-[var(--profit)]" : ""
              )}>
                {lastRsi.toFixed(1)}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.rsiLastSignal")}</p>
              <Badge
                variant="outline"
                className={cn(
                  "text-xs mt-1",
                  lastSignal === "buy"
                    ? "bg-[var(--profit)]/10 text-[var(--profit)] border-[var(--profit)]/30"
                    : lastSignal === "sell"
                      ? "bg-[var(--loss)]/10 text-[var(--loss)] border-[var(--loss)]/30"
                      : "bg-muted text-muted-foreground"
                )}
              >
                {lastSignal === "buy"
                  ? t("detail.overview.rsiBuySignal")
                  : lastSignal === "sell"
                    ? t("detail.overview.rsiSellSignal")
                    : "-"}
              </Badge>
            </div>
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.rsiLastPrice")}</p>
              <p className="text-xl font-mono font-bold">${lastPrice.toLocaleString()}</p>
            </div>
            {hasPosition && (
              <>
                <div className="p-3 rounded-lg bg-muted/30">
                  <p className="text-xs text-muted-foreground">{t("detail.overview.rsiEntryPrice")}</p>
                  <p className="text-xl font-mono font-bold">${entryPrice.toLocaleString()}</p>
                </div>
                <div className="p-3 rounded-lg bg-muted/30">
                  <p className="text-xs text-muted-foreground">{t("detail.overview.rsiPositionSize")}</p>
                  <p className="text-xl font-mono font-bold">${positionSizeUsd.toLocaleString()}</p>
                </div>
              </>
            )}
            <div className="p-3 rounded-lg bg-muted/30">
              <p className="text-xs text-muted-foreground">{t("detail.overview.totalPnl")}</p>
              <p className={cn(
                "text-xl font-mono font-bold",
                strategy.total_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"
              )}>
                {strategy.total_pnl >= 0 ? "+" : ""}${strategy.total_pnl.toLocaleString()}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Fallback: show raw runtime state
  return (
    <Card className="bg-card/50 border-border/50">
      <CardHeader>
        <CardTitle className="text-base">{t("detail.overview.runtimeState")}</CardTitle>
      </CardHeader>
      <CardContent>
        <pre className="text-xs font-mono bg-muted/50 p-4 rounded-lg overflow-auto max-h-64">
          {JSON.stringify(runtimeState, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}

export default function QuantStrategyDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const t = useTranslations("quantStrategies");
  const router = useRouter();
  const toast = useToast();
  const { data: strategy, error, isLoading, mutate } = useQuantStrategy(id);
  const [isUpdating, setIsUpdating] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  const handleStatusChange = async (newStatus: StrategyStatus) => {
    setIsUpdating(true);
    try {
      const { quantStrategiesApi } = await import("@/lib/api");
      await quantStrategiesApi.updateStatus(id, newStatus);
      mutate();
      const statusKey = newStatus === "active" ? "started" : newStatus;
      toast.success(t(`toast.${statusKey}`));
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.updateFailed");
      toast.error(t("toast.updateFailed"), message);
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(t("detail.settings.deleteConfirm"))) return;
    try {
      const { quantStrategiesApi } = await import("@/lib/api");
      await quantStrategiesApi.delete(id);
      toast.success(t("toast.deleteSuccess"));
      router.push("/strategies");
    } catch (err) {
      const message = err instanceof Error ? err.message : t("toast.deleteFailed");
      toast.error(t("toast.deleteFailed"), message);
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
      <div className="space-y-4">
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

  const TypeIcon = getTypeIcon(strategy.strategy_type);
  const config = strategy.config as Record<string, unknown>;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/strategies")}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <TypeIcon className="w-6 h-6 text-primary" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">{strategy.name}</h1>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className={cn("text-xs", getStatusColor(strategy.status))}>
                  {t(`status.${strategy.status}`)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {t(`types.${strategy.strategy_type}`)}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {strategy.symbol}
                </Badge>
              </div>
            </div>
          </div>
        </div>

        {/* Status Actions */}
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={() => mutate()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
          {strategy.status === "active" && (
            <Button
              variant="default"
              className="bg-primary/20 text-primary hover:bg-primary/30"
              onClick={() => handleStatusChange("paused")}
              disabled={isUpdating}
            >
              {isUpdating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Pause className="w-4 h-4 mr-2" />}
              {t("actions.pause")}
            </Button>
          )}
          {(strategy.status === "paused" || strategy.status === "draft") && (
            <Button
              onClick={() => handleStatusChange("active")}
              disabled={isUpdating}
            >
              {isUpdating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
              {strategy.status === "draft" ? t("actions.start") : t("actions.resume")}
            </Button>
          )}
          {strategy.status === "paused" && (
            <Button
              variant="outline"
              className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
              onClick={() => setShowStopConfirm(true)}
              disabled={isUpdating}
            >
              <Square className="w-4 h-4 mr-2" />
              {t("actions.stop")}
            </Button>
          )}
          {(strategy.status === "error" || strategy.status === "warning") && (
            <>
              <Button
                onClick={() => handleStatusChange("active")}
                disabled={isUpdating}
              >
                {isUpdating ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
                {t("actions.restart")}
              </Button>
              <Button
                variant="outline"
                className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                onClick={() => setShowStopConfirm(true)}
                disabled={isUpdating}
              >
                <Square className="w-4 h-4 mr-2" />
                {t("actions.stop")}
              </Button>
            </>
          )}
        </div>
      </div>

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

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList>
          <TabsTrigger value="overview">{t("detail.tabs.overview")}</TabsTrigger>
          <TabsTrigger value="trades">{t("detail.tabs.trades")}</TabsTrigger>
          <TabsTrigger value="settings">{t("detail.tabs.settings")}</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          {/* Chart + Strategy Info Sidebar */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
            {/* TradingView Chart */}
            <Card className="bg-card/50 border-border/50 overflow-hidden min-h-[500px] flex flex-col">
              {/* Current trading pair display */}
              <div className="flex items-center gap-2 px-4 pt-3 pb-0">
                <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 font-mono text-xs">
                  {strategy.symbol}/USDT
                </Badge>
                <span className="text-xs text-muted-foreground">{t(`types.${strategy.strategy_type}`)}</span>
              </div>
              <CardContent className="p-0 flex-1">
                <TradingViewChart
                  symbol={`BINANCE:${strategy.symbol}USDT`}
                  interval="60"
                />
              </CardContent>
            </Card>

            {/* Strategy Info Sidebar */}
            <div className="space-y-4">
              {/* Strategy Details */}
              <Card className="bg-card/50 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t("detail.overview.strategyInfo")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t("detail.overview.status")}</span>
                    <Badge variant="outline" className={cn("text-xs", getStatusColor(strategy.status))}>
                      {t(`status.${strategy.status}`)}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t("detail.overview.symbol")}</span>
                    <span className="font-mono font-medium">{strategy.symbol}/USDT</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t("detail.overview.strategyType")}</span>
                    <span className="font-medium">{t(`types.${strategy.strategy_type}`)}</span>
                  </div>

                  {/* Strategy-specific config params */}
                  <div className="pt-2 border-t border-border/30 space-y-2">
                    {Object.entries(config).map(([key, value]) => (
                      <div key={key} className="flex items-center justify-between">
                        <span className="text-muted-foreground text-xs">{key.replace(/_/g, " ")}</span>
                        <span className="font-mono text-xs">{String(value)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="pt-2 border-t border-border/30 space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">{t("detail.overview.createdAt")}</span>
                      <span className="text-xs">{new Date(strategy.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">{t("detail.overview.lastRun")}</span>
                      <span className="text-xs">
                        {strategy.last_run_at
                          ? new Date(strategy.last_run_at).toLocaleString()
                          : t("detail.overview.never")}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Profit Summary */}
              <Card className="bg-card/50 border-border/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">{t("detail.overview.profitSummary")}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t("detail.overview.totalPnl")}</span>
                    <span className={cn(
                      "font-mono font-bold",
                      strategy.total_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"
                    )}>
                      {strategy.total_pnl >= 0 ? "+" : ""}{strategy.total_pnl.toLocaleString()} USDT
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t("detail.overview.winRate")}</span>
                    <span className="font-mono font-medium">{strategy.win_rate.toFixed(1)}%</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t("detail.overview.totalTrades")}</span>
                    <span className="font-mono font-medium">{strategy.total_trades}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">{t("detail.overview.maxDrawdown")}</span>
                    <span className="font-mono font-medium text-[var(--loss)]">
                      ${strategy.max_drawdown.toLocaleString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>

          {/* Trade Execution / Runtime State */}
          <QuantTradeSection strategy={strategy} t={t} />
        </TabsContent>

        {/* Trades Tab — same content as overview trade section for dedicated view */}
        <TabsContent value="trades" className="space-y-6">
          <QuantTradeSection strategy={strategy} t={t} />
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-6">
          {/* Danger Zone */}
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="text-destructive">{t("detail.settings.dangerZone")}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">{t("detail.settings.deleteStrategy")}</p>
                  <p className="text-sm text-muted-foreground">
                    {!["stopped", "draft"].includes(strategy.status)
                      ? t("detail.settings.deleteRequireStopped")
                      : t("detail.settings.deleteConfirm")}
                  </p>
                </div>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={!["stopped", "draft"].includes(strategy.status)}
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {t("detail.settings.confirmDelete")}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
