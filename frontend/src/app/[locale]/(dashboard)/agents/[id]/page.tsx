"use client";

import { useState, useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { useParams, useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  BarChart3,
  Bot,
  Brain,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Clock,
  Play,
  Pause,
  Square,
  Settings,
  TrendingUp,
  TrendingDown,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
  Target,
  Activity,
  Trash2,
  XCircle,
  Zap,
  ExternalLink,
  RotateCcw,
  Code,
  Copy,
  Check,
  Wallet,
  CircleDot,
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import {
  useUserModels,
  groupModelsByProvider,
  getProviderDisplayName,
} from "@/hooks";
import {
  useAgent,
  useUpdateAgentStatus,
  useAgentPositions,
  useAgentAccountState,
} from "@/hooks/use-agents";
import {
  useAgentDecisions,
  useAgentDecisionStats,
} from "@/hooks/use-decisions";
import { agentsApi } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import type { AgentStatus } from "@/types";

// Backward compat alias used throughout this file
type StrategyStatus = AgentStatus;
import {
  MarketSnapshotSection,
  AccountSnapshotSection,
} from "@/components/decisions/snapshot-sections";
import { MarkdownToggle } from "@/components/ui/markdown-toggle";
import { ChainOfThought as ChainOfThoughtView } from "@/components/decisions/chain-of-thought";
import { DetailPageHeader } from "@/components/layout";

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

function getActionColor(action: string) {
  switch (action) {
    case "open_long":
      return "bg-[var(--profit)]/20 text-[var(--profit)] border-[var(--profit)]/30";
    case "open_short":
      return "bg-[var(--loss)]/20 text-[var(--loss)] border-[var(--loss)]/30";
    case "close_long":
    case "close_short":
      return "bg-muted text-foreground border-border";
    case "hold":
    case "wait":
      return "bg-[var(--warning)]/20 text-[var(--warning)] border-[var(--warning)]/30";
    default:
      return "bg-muted text-muted-foreground";
  }
}

// Positions Tab
function PositionsTab({
  agentId,
  t,
}: {
  agentId: string;
  t: ReturnType<typeof useTranslations>;
}) {
  const { data: positions, isLoading, error } = useAgentPositions(agentId);
  const { data: accountState } = useAgentAccountState(agentId);

  // Filter to show only open and pending positions
  const activePositions = positions?.filter(
    (p) => p.status === "open" || p.status === "pending",
  );

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "open":
        return (
          <Badge
            variant="outline"
            className="bg-[var(--profit)]/10 text-[var(--profit)] border-[var(--profit)]/30"
          >
            {t("positions.status.open")}
          </Badge>
        );
      case "pending":
        return (
          <Badge
            variant="outline"
            className="bg-[var(--warning)]/10 text-[var(--warning)] border-[var(--warning)]/30"
          >
            {t("positions.status.pending")}
          </Badge>
        );
      case "closed":
        return (
          <Badge variant="outline" className="bg-muted text-muted-foreground">
            {t("positions.status.closed")}
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getSideBadge = (side: string) => {
    if (side === "long") {
      return (
        <Badge className="bg-[var(--profit)]/20 text-[var(--profit)]">
          {t("positions.side.long")}
        </Badge>
      );
    }
    return (
      <Badge className="bg-[var(--loss)]/20 text-[var(--loss)]">
        {t("positions.side.short")}
      </Badge>
    );
  };

  const formatPrice = (price: number) => {
    if (price >= 1000)
      return `$${price.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    if (price >= 1) return `$${price.toFixed(2)}`;
    return `$${price.toFixed(6)}`;
  };

  const formatPnl = (pnl: number) => {
    const isPositive = pnl >= 0;
    return (
      <span
        className={isPositive ? "text-[var(--profit)]" : "text-[var(--loss)]"}
      >
        {isPositive ? "+" : ""}${pnl.toFixed(2)}
      </span>
    );
  };

  const formatTime = (dateStr: string | null | undefined) => {
    if (!dateStr) return "-";
    const date = new Date(dateStr);
    return date.toLocaleString();
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <AlertCircle className="w-10 h-10 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">{t("positions.empty")}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Account Summary Cards */}
      {accountState && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">
                {t("positions.accountSummary.equity")}
              </div>
              <div className="text-2xl font-bold">
                $
                {accountState.equity.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">
                {t("positions.accountSummary.availableBalance")}
              </div>
              <div className="text-2xl font-bold">
                $
                {accountState.available_balance.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">
                {t("positions.accountSummary.unrealizedPnl")}
              </div>
              <div
                className={`text-2xl font-bold ${accountState.total_unrealized_pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]"}`}
              >
                {accountState.total_unrealized_pnl >= 0 ? "+" : ""}$
                {accountState.total_unrealized_pnl.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-muted-foreground mb-1">
                {t("positions.accountSummary.marginUsed")}
              </div>
              <div className="text-2xl font-bold">
                $
                {accountState.total_margin_used.toLocaleString(undefined, {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t("positions.title")}</CardTitle>
        </CardHeader>
        <CardContent>
          {!activePositions || activePositions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Target className="w-10 h-10 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{t("positions.empty")}</p>
              <p className="text-sm text-muted-foreground mt-1">
                {t("positions.emptyDesc")}
              </p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("positions.columns.symbol")}</TableHead>
                    <TableHead>{t("positions.columns.side")}</TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.size")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.sizeUsd")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.entryPrice")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.leverage")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.margin")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.unrealizedPnl")}
                    </TableHead>
                    <TableHead className="text-right">
                      {t("positions.columns.realizedPnl")}
                    </TableHead>
                    <TableHead>{t("positions.columns.status")}</TableHead>
                    <TableHead>{t("positions.columns.openedAt")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activePositions.map((position) => (
                    <TableRow key={position.id}>
                      <TableCell className="font-medium">
                        {position.symbol}
                      </TableCell>
                      <TableCell>{getSideBadge(position.side)}</TableCell>
                      <TableCell className="text-right">
                        {position.size.toFixed(4)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPrice(position.size_usd)}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPrice(position.entry_price)}
                      </TableCell>
                      <TableCell className="text-right">
                        {position.leverage}x
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPrice(position.size_usd / position.leverage)}
                      </TableCell>
                      <TableCell className="text-right">
                        {position.unrealized_pnl != null
                          ? formatPnl(position.unrealized_pnl)
                          : "-"}
                      </TableCell>
                      <TableCell className="text-right">
                        {formatPnl(position.realized_pnl)}
                      </TableCell>
                      <TableCell>{getStatusBadge(position.status)}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {formatTime(position.opened_at)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Overview Tab
function OverviewTab({
  agent,
  agentId,
  t,
}: {
  agent: NonNullable<ReturnType<typeof useAgent>["data"]>;
  agentId: string;
  t: ReturnType<typeof useTranslations>;
}) {
  const hasTradeData = (agent.total_trades ?? 0) > 0;
  const symbols = agent.strategy_symbols || [];

  // --- Trade execution list: state, data fetching, pagination ---
  const TRADES_PAGE_SIZE = 10;
  const [tradePage, setTradePage] = useState(1);
  const [tradeActionFilter, setTradeActionFilter] = useState<string>("");
  const tradeListTopRef = useRef<HTMLDivElement>(null);

  const tradeFilters = {
    executionFilter: "executed" as const,
    action: tradeActionFilter || undefined,
  };
  const {
    data: tradePageData,
    isValidating: isTradeValidating,
    mutate: mutateTrades,
  } = useAgentDecisions(agentId, tradePage, TRADES_PAGE_SIZE, tradeFilters);
  const tradeDecisions = tradePageData?.items ?? [];
  const tradeTotalItems = tradePageData?.total ?? 0;
  const tradeTotalPages = Math.max(
    1,
    Math.ceil(tradeTotalItems / TRADES_PAGE_SIZE),
  );

  // Build trade rows from execution_results, matched with decision data and account snapshot
  const tradeRows = tradeDecisions.flatMap((decision) => {
    const snapshotPositions = (
      decision.account_snapshot as Record<string, unknown> | null
    )?.positions as
      | Array<{
          symbol: string;
          side: string;
          size: number;
          size_usd: number;
          entry_price: number;
          mark_price: number;
          leverage: number;
          unrealized_pnl: number;
          unrealized_pnl_percent: number;
          liquidation_price?: number | null;
        }>
      | undefined;
    const execResults =
      (decision.execution_results as Array<Record<string, unknown>>) ?? [];

    return execResults
      .filter((er) => er.executed === true)
      .map((er, idx) => {
        const symbol = er.symbol as string;
        const action = er.action as string;
        const orderResult = er.order_result as Record<string, unknown> | null;
        const aiDecision = decision.decisions.find(
          (d) => d.symbol === symbol && d.action === action,
        );
        const position = snapshotPositions?.find((p) => p.symbol === symbol);
        const side = action.includes("long") ? "long" : "short";
        const isClose = action.startsWith("close");

        return {
          key: `${decision.id}-exec-${idx}`,
          symbol,
          action,
          side: side as "long" | "short",
          isClose,
          // For close actions: prefer position_leverage from exec_result (backend enriched),
          // then fallback to account_snapshot position, then AI decision
          leverage: isClose
            ? ((er.position_leverage as number) ??
              position?.leverage ??
              aiDecision?.leverage ??
              0)
            : (aiDecision?.leverage ?? position?.leverage ?? 0),
          entryPrice: isClose
            ? (position?.entry_price ?? aiDecision?.entry_price)
            : (aiDecision?.entry_price ?? position?.entry_price),
          filledPrice: orderResult?.filled_price as number | undefined,
          filledSize: orderResult?.filled_size as number | undefined,
          sizeUsd: isClose
            ? ((er.position_size_usd as number) ?? position?.size_usd)
            : (er.actual_size_usd as number | undefined),
          markPrice: position?.mark_price,
          unrealizedPnl: position?.unrealized_pnl,
          unrealizedPnlPercent: position?.unrealized_pnl_percent,
          realizedPnl: er.realized_pnl as number | undefined,
          timestamp: decision.timestamp,
        };
      });
  });

  const handleTradeActionFilterChange = (value: string) => {
    setTradeActionFilter(value);
    setTradePage(1);
  };

  const goToTradePage = (newPage: number) => {
    setTradePage(newPage);
    tradeListTopRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  };

  // Helper to format price
  const fmtPrice = (v: number | undefined | null) =>
    v != null
      ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : t("overview.tradeNA");

  // Helper to format PnL
  const fmtPnl = (v: number | undefined | null) =>
    v != null
      ? `$${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : t("overview.tradeNA");

  return (
    <div className="space-y-6">
      {/* Strategy Info + Profit Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Strategy Details */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">
                {t("overview.strategyInfo")}
              </CardTitle>
              {agent.strategy_id && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1 text-xs text-muted-foreground hover:text-foreground"
                  asChild
                >
                  <Link href={`/strategies/${agent.strategy_id}`}>
                    {t("overview.viewStrategy")}
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                {t("overview.symbols")}
              </span>
              <div className="flex gap-1 flex-wrap justify-end">
                {symbols.map((s) => (
                  <Badge
                    key={s}
                    variant="outline"
                    className="bg-primary/10 text-primary border-primary/30 font-mono text-xs py-0"
                  >
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                {t("overview.tradingMode")}
              </span>
              <span className="font-medium">
                {t(
                  `tradingModeValue.${(agent.config as Record<string, unknown>)?.trading_mode || "balanced"}`,
                )}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                {t("overview.aiModel")}
              </span>
              <span
                className="font-medium text-xs truncate max-w-[150px]"
                title={agent.ai_model || ""}
              >
                {agent.ai_model
                  ? agent.ai_model.includes(":")
                    ? agent.ai_model.split(":").slice(1).join(":")
                    : agent.ai_model
                  : "-"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">
                {t("overview.executionInterval")}
              </span>
              <span className="font-mono text-xs">
                {t("overview.everyMinutes", {
                  minutes: agent.execution_interval_minutes,
                })}
              </span>
            </div>
            <div className="pt-2 border-t border-border/30 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">
                  {t("overview.createdAt")}
                </span>
                <span className="text-xs">
                  {agent.created_at
                    ? new Date(agent.created_at).toLocaleDateString()
                    : "-"}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">
                  {t("overview.lastRun")}
                </span>
                <span className="text-xs">
                  {agent.last_run_at
                    ? new Date(agent.last_run_at).toLocaleString()
                    : t("overview.never")}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Profit Summary */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">
              {t("overview.profitSummary")}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {t("overview.totalPnl")}
              </span>
              {hasTradeData ? (
                <span
                  className={cn(
                    "font-mono font-bold",
                    (agent.total_pnl ?? 0) >= 0
                      ? "text-[var(--profit)]"
                      : "text-[var(--loss)]",
                  )}
                >
                  {(agent.total_pnl ?? 0) >= 0 ? "+" : ""}$
                  {Math.abs(agent.total_pnl ?? 0).toLocaleString()}
                </span>
              ) : (
                <span className="font-mono text-muted-foreground">
                  {t("overview.noData")}
                </span>
              )}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {t("overview.winRate")}
              </span>
              <span className="font-mono font-medium">
                {hasTradeData ? `${(agent.win_rate ?? 0).toFixed(1)}%` : "-"}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {t("overview.totalTrades")}
              </span>
              <span className="font-mono font-medium">
                {agent.total_trades ?? 0}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                {t("overview.maxDrawdown")}
              </span>
              <span className="font-mono font-medium text-[var(--loss)]">
                {hasTradeData
                  ? `-${(agent.max_drawdown ?? 0).toFixed(2)}%`
                  : "-"}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Trade Execution List */}
      <div ref={tradeListTopRef} />
      <Card className="bg-card/50 border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            {t("overview.recentTrades")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Toolbar: filters + refresh */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <Select
                value={tradeActionFilter || "__all__"}
                onValueChange={(v) =>
                  handleTradeActionFilterChange(v === "__all__" ? "" : v)
                }
              >
                <SelectTrigger className="w-[160px] h-8 text-xs">
                  <SelectValue placeholder={t("overview.tradeFilterAll")} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">
                    {t("overview.tradeFilterAll")}
                  </SelectItem>
                  {["open_long", "open_short", "close_long", "close_short"].map(
                    (action) => (
                      <SelectItem key={action} value={action}>
                        {action.replace("_", " ").toUpperCase()}
                      </SelectItem>
                    ),
                  )}
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => mutateTrades()}
              disabled={isTradeValidating}
            >
              <RefreshCw
                className={cn(
                  "w-4 h-4 mr-2",
                  isTradeValidating && "animate-spin",
                )}
              />
              {t("refresh")}
            </Button>
          </div>

          {/* Table or empty state */}
          {tradeTotalItems === 0 && tradeRows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8">
              <Brain className="w-8 h-8 text-muted-foreground mb-3" />
              <p className="text-sm text-muted-foreground">
                {t("overview.noRecentTrades")}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {t("overview.noRecentTradesHint")}
              </p>
            </div>
          ) : (
            <div className="relative">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/50">
                      <TableHead className="text-xs">
                        {t("overview.tradeTime")}
                      </TableHead>
                      <TableHead className="text-xs">
                        {t("overview.tradeSymbol")}
                      </TableHead>
                      <TableHead className="text-xs">
                        {t("overview.tradeAction")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradeLeverage")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradeEntryPrice")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradeClosePrice")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradeSize")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradeSizeUsd")}
                      </TableHead>
                      <TableHead className="text-xs text-right">
                        {t("overview.tradePnl")}
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {tradeRows.map((row) => {
                      const pnlValue = row.isClose
                        ? row.realizedPnl
                        : row.unrealizedPnl;
                      const pnlPct = row.isClose
                        ? undefined
                        : row.unrealizedPnlPercent;

                      return (
                        <TableRow key={row.key} className="border-border/30">
                          <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(row.timestamp).toLocaleString()}
                          </TableCell>
                          <TableCell className="font-mono text-xs font-medium">
                            {row.symbol}/USDT
                          </TableCell>
                          <TableCell>
                            <Badge
                              variant="outline"
                              className={cn(
                                "text-xs",
                                row.isClose
                                  ? "bg-muted text-foreground border-border"
                                  : getActionColor(row.action),
                              )}
                            >
                              {row.isClose
                                ? row.side === "long"
                                  ? t("overview.tradeCloseLong")
                                  : t("overview.tradeCloseShort")
                                : row.side === "long"
                                  ? t("overview.tradeLong")
                                  : t("overview.tradeShort")}
                            </Badge>
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right">
                            {row.leverage}x
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right">
                            {fmtPrice(
                              row.isClose ? row.entryPrice : row.filledPrice,
                            )}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right">
                            {row.isClose
                              ? fmtPrice(row.filledPrice)
                              : t("overview.tradeNA")}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right">
                            {row.filledSize != null
                              ? row.filledSize
                              : t("overview.tradeNA")}
                          </TableCell>
                          <TableCell className="font-mono text-xs text-right">
                            {row.sizeUsd != null
                              ? `$${row.sizeUsd.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
                              : t("overview.tradeNA")}
                          </TableCell>
                          <TableCell className="text-right">
                            {pnlValue != null ? (
                              <span
                                className={cn(
                                  "font-mono text-xs font-semibold",
                                  pnlValue >= 0
                                    ? "text-[var(--profit)]"
                                    : "text-[var(--loss)]",
                                )}
                              >
                                {fmtPnl(pnlValue)}
                                {pnlPct != null && (
                                  <span className="ml-1 font-normal text-muted-foreground">
                                    ({pnlPct >= 0 ? "+" : ""}
                                    {pnlPct.toFixed(2)}%)
                                  </span>
                                )}
                              </span>
                            ) : (
                              <span className="font-mono text-xs text-muted-foreground">
                                {t("overview.tradeNA")}
                              </span>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            </div>
          )}

          {/* Pagination */}
          {tradeTotalPages > 1 && (
            <div className="flex items-center justify-center gap-1.5 pt-2">
              <Button
                variant="outline"
                size="icon"
                className="w-8 h-8"
                onClick={() => goToTradePage(tradePage - 1)}
                disabled={tradePage <= 1}
              >
                <ChevronLeft className="w-4 h-4" />
              </Button>
              {(() => {
                const pages: (number | "ellipsis-start" | "ellipsis-end")[] =
                  [];
                if (tradeTotalPages <= 7) {
                  for (let i = 1; i <= tradeTotalPages; i++) pages.push(i);
                } else {
                  pages.push(1);
                  if (tradePage > 3) pages.push("ellipsis-start");
                  const start = Math.max(2, tradePage - 1);
                  const end = Math.min(tradeTotalPages - 1, tradePage + 1);
                  for (let i = start; i <= end; i++) pages.push(i);
                  if (tradePage < tradeTotalPages - 2)
                    pages.push("ellipsis-end");
                  pages.push(tradeTotalPages);
                }
                return pages.map((p) =>
                  typeof p === "string" ? (
                    <span
                      key={p}
                      className="w-8 h-8 flex items-center justify-center text-sm text-muted-foreground"
                    >
                      ...
                    </span>
                  ) : (
                    <Button
                      key={p}
                      variant={p === tradePage ? "default" : "outline"}
                      size="icon"
                      className="w-8 h-8 text-xs"
                      onClick={() => goToTradePage(p)}
                    >
                      {p}
                    </Button>
                  ),
                );
              })()}
              <Button
                variant="outline"
                size="icon"
                className="w-8 h-8"
                onClick={() => goToTradePage(tradePage + 1)}
                disabled={tradePage >= tradeTotalPages}
              >
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// Raw AI Response Viewer
function RawResponseViewer({
  rawResponse,
  t,
  isQuant = false,
}: {
  rawResponse: string;
  t: ReturnType<typeof useTranslations>;
  isQuant?: boolean;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const formattedResponse = (() => {
    try {
      const parsed = JSON.parse(rawResponse);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return rawResponse;
    }
  })();

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(rawResponse);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback: ignore
    }
  };

  // Use different labels for Quant strategies
  const titleLabel = isQuant
    ? t("decisions.executionLog")
    : t("decisions.rawResponse");
  const hintLabel = isQuant
    ? t("decisions.executionLogHint")
    : t("decisions.rawResponseHint");

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button className="flex items-center justify-between w-full px-4 py-2.5 rounded-lg bg-muted/20 border border-border/30 hover:bg-muted/40 transition-colors text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Code className="w-4 h-4" />
            <span className="font-medium">{titleLabel}</span>
            <span className="text-xs opacity-70">({hintLabel})</span>
          </div>
          <ChevronDown
            className={cn(
              "w-4 h-4 text-muted-foreground transition-transform",
              isOpen && "rotate-180",
            )}
          />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="relative mt-2 rounded-lg border border-border/30 bg-muted/10">
          <div className="absolute top-2 right-2 z-10">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleCopy}
            >
              {copied ? (
                <>
                  <Check className="w-3.5 h-3.5 mr-1" />
                  {t("decisions.copied")}
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 mr-1" />
                  {t("decisions.copyRaw")}
                </>
              )}
            </Button>
          </div>
          <pre className="p-4 pr-20 text-xs font-mono leading-relaxed overflow-auto max-h-[400px] whitespace-pre-wrap break-words text-muted-foreground">
            {formattedResponse}
          </pre>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// Decisions Tab (merged with Performance analytics)
const DECISIONS_PAGE_SIZE = 10;

function DecisionsTab({
  agentId,
  agentName,
  t,
  onRunNow,
  isRunningNow,
  agentStatus,
  highlightDecisionId,
}: {
  agentId: string;
  agentName: string;
  t: ReturnType<typeof useTranslations>;
  onRunNow?: () => void;
  isRunningNow?: boolean;
  agentStatus?: string;
  highlightDecisionId?: string;
}) {
  const [page, setPage] = useState(1);
  const [executionFilter, setExecutionFilter] = useState<
    "all" | "executed" | "skipped"
  >("all");
  const [actionFilter, setActionFilter] = useState<string>("");

  const filters = { executionFilter, action: actionFilter || undefined };
  const {
    data: pageData,
    isLoading,
    isValidating,
    mutate,
  } = useAgentDecisions(agentId, page, DECISIONS_PAGE_SIZE, filters);
  const { data: stats } = useAgentDecisionStats(agentId);

  const decisions = pageData?.items ?? [];
  const totalItems = pageData?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / DECISIONS_PAGE_SIZE));

  const [expandedIds, setExpandedIds] = useState<Set<string>>(() =>
    highlightDecisionId ? new Set([highlightDecisionId]) : new Set(),
  );
  const highlightRef = useRef<HTMLDivElement>(null);
  const hasScrolled = useRef(false);
  const listTopRef = useRef<HTMLDivElement>(null);

  // Scroll to the highlighted decision once it's loaded and expanded
  useEffect(() => {
    if (highlightDecisionId && decisions.length > 0 && !hasScrolled.current) {
      setExpandedIds((prev) => {
        if (prev.has(highlightDecisionId)) return prev;
        return new Set(prev).add(highlightDecisionId);
      });
      const timer = setTimeout(() => {
        highlightRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
        hasScrolled.current = true;
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [highlightDecisionId, decisions]);

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const goToPage = (newPage: number) => {
    setPage(newPage);
    setExpandedIds(new Set());
    listTopRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const handleExecutionFilterChange = (
    value: "all" | "executed" | "skipped",
  ) => {
    setExecutionFilter(value);
    setPage(1);
    setExpandedIds(new Set());
  };

  const handleActionFilterChange = (value: string) => {
    setActionFilter(value);
    setPage(1);
    setExpandedIds(new Set());
  };

  // Stats-driven metrics
  const executionRate =
    stats && stats.total_decisions > 0
      ? Math.round((stats.executed_decisions / stats.total_decisions) * 100)
      : 0;
  const actionCounts = stats?.action_counts ?? {};

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const toolbar = (
    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Execution status filter */}
        <div className="flex rounded-md border border-border overflow-hidden">
          {(["all", "executed", "skipped"] as const).map((value) => (
            <button
              key={value}
              onClick={() => handleExecutionFilterChange(value)}
              className={cn(
                "px-3 py-1.5 text-xs font-medium transition-colors",
                executionFilter === value
                  ? "bg-primary text-primary-foreground"
                  : "bg-background hover:bg-muted text-muted-foreground",
              )}
            >
              {t(
                `decisions.filter${value.charAt(0).toUpperCase() + value.slice(1)}`,
              )}
            </button>
          ))}
        </div>
        {/* Action type filter */}
        <Select
          value={actionFilter || "__all__"}
          onValueChange={(v) =>
            handleActionFilterChange(v === "__all__" ? "" : v)
          }
        >
          <SelectTrigger className="w-[140px] h-8 text-xs">
            <SelectValue placeholder={t("decisions.filterActionAll")} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">
              {t("decisions.filterActionAll")}
            </SelectItem>
            {[
              "open_long",
              "open_short",
              "close_long",
              "close_short",
              "hold",
              "wait",
            ].map((action) => (
              <SelectItem key={action} value={action}>
                {action.replace("_", " ").toUpperCase()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {/* Actions */}
      <div className="flex items-center gap-2">
        {agentStatus === "active" && onRunNow && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRunNow}
            disabled={isRunningNow}
          >
            {isRunningNow ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Zap className="w-4 h-4 mr-2" />
            )}
            {t("actions.runNow")}
          </Button>
        )}
        <Button
          variant="outline"
          size="sm"
          onClick={() => mutate()}
          disabled={isValidating}
        >
          <RefreshCw
            className={cn("w-4 h-4 mr-2", isValidating && "animate-spin")}
          />
          {t("refresh")}
        </Button>
      </div>
    </div>
  );

  if (totalItems === 0 && decisions.length === 0) {
    return (
      <div className="space-y-4">
        {toolbar}
        <Card className="bg-card/50 border-border/50">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Brain className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              {t("decisions.empty")}
            </h3>
            <p className="text-muted-foreground text-center">
              {t("decisions.emptyHint")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* AI Decision Analytics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Brain className="w-4 h-4" />
              <span className="text-xs">{t("decisions.totalDecisions")}</span>
            </div>
            <p className="text-2xl font-bold font-mono">
              {stats?.total_decisions ?? 0}
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Zap className="w-4 h-4" />
              <span className="text-xs">{t("decisions.executionRate")}</span>
            </div>
            <p className="text-2xl font-bold font-mono">{executionRate}%</p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Target className="w-4 h-4" />
              <span className="text-xs">{t("decisions.avgConfidence")}</span>
            </div>
            <p className="text-2xl font-bold font-mono">
              {Math.round(stats?.average_confidence ?? 0)}%
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Clock className="w-4 h-4" />
              <span className="text-xs">{t("decisions.avgLatency")}</span>
            </div>
            <p className="text-2xl font-bold font-mono">
              {Math.round(stats?.average_latency_ms ?? 0)}ms
            </p>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-muted-foreground mb-1">
              <Activity className="w-4 h-4" />
              <span className="text-xs">{t("decisions.totalTokens")}</span>
            </div>
            <p className="text-2xl font-bold font-mono">
              {(stats?.total_tokens ?? 0).toLocaleString()}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Action Distribution (compact) */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="pt-4 pb-3">
          <div className="flex items-center gap-2 text-muted-foreground mb-2">
            <BarChart3 className="w-4 h-4" />
            <span className="text-xs">{t("decisions.actionDistribution")}</span>
          </div>
          <div className="flex flex-wrap gap-3">
            {[
              "open_long",
              "open_short",
              "close_long",
              "close_short",
              "hold",
              "wait",
            ].map((action) => (
              <div key={action} className="flex items-center gap-1.5">
                <Badge
                  variant="outline"
                  className={cn("text-xs py-0", getActionColor(action))}
                >
                  {action.replace("_", " ").toUpperCase()}
                </Badge>
                <span className="text-sm font-bold font-mono">
                  {actionCounts[action] || 0}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {toolbar}

      <div ref={listTopRef} />

      <div className="relative">
        {decisions.map((decision) => {
          const isHighlighted = highlightDecisionId === decision.id;
          return (
            <Collapsible
              key={decision.id}
              open={expandedIds.has(decision.id)}
              onOpenChange={() => toggleExpanded(decision.id)}
            >
              <div ref={isHighlighted ? highlightRef : undefined}>
                <Card
                  className={cn(
                    "bg-card/50 border-border/50 transition-all duration-500",
                    isHighlighted && "ring-2 ring-primary/50 border-primary/30",
                  )}
                >
                  <CollapsibleTrigger asChild>
                    <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="p-2 rounded-lg bg-primary/10">
                            <Brain className="w-5 h-5 text-primary" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <CardTitle className="text-base">
                                {agentName} {t("decisions.decision")} #
                                {decision.id.slice(0, 8)}
                              </CardTitle>
                              <Badge
                                variant="outline"
                                className={cn(
                                  "text-xs",
                                  decision.executed
                                    ? "bg-[var(--profit)]/20 text-[var(--profit)]"
                                    : "bg-muted text-muted-foreground",
                                )}
                              >
                                {decision.executed ? (
                                  <CheckCircle2 className="w-3 h-3 mr-1" />
                                ) : (
                                  <AlertCircle className="w-3 h-3 mr-1" />
                                )}
                                {decision.executed
                                  ? t("decisions.executed")
                                  : t("decisions.skipped")}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                              <Clock className="w-3 h-3" />
                              {new Date(decision.timestamp).toLocaleString()}
                              <span className="mx-1">•</span>
                              {t("decisions.confidence")}:{" "}
                              {decision.overall_confidence}%
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="flex gap-2">
                            {decision.decisions.slice(0, 3).map((d, i) => (
                              <Badge
                                key={i}
                                variant="outline"
                                className={cn(
                                  "text-xs",
                                  getActionColor(d.action),
                                )}
                              >
                                {d.symbol}{" "}
                                {d.action.replace("_", " ").toUpperCase()}
                              </Badge>
                            ))}
                          </div>
                          {expandedIds.has(decision.id) ? (
                            <ChevronDown className="w-5 h-5 text-muted-foreground" />
                          ) : (
                            <ChevronRight className="w-5 h-5 text-muted-foreground" />
                          )}
                        </div>
                      </div>
                    </CardHeader>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <CardContent className="pt-0 space-y-6">
                      {/* Market Assessment */}
                      <div className="p-4 rounded-lg bg-muted/30 border border-border/30">
                        <h4 className="text-sm font-semibold mb-2">
                          {t("decisions.marketAssessment")}
                        </h4>
                        <p className="text-sm text-muted-foreground">
                          {decision.market_assessment}
                        </p>
                      </div>

                      {/* Account Snapshot */}
                      {decision.account_snapshot && (
                        <AccountSnapshotSection
                          snapshot={decision.account_snapshot}
                          t={t}
                        />
                      )}

                      {/* Market Data Snapshot */}
                      {decision.market_snapshot &&
                        decision.market_snapshot.length > 0 && (
                          <MarketSnapshotSection
                            snapshot={decision.market_snapshot}
                            t={t}
                          />
                        )}

                      {/* Chain of Thought - Enhanced Timeline View */}
                      <ChainOfThoughtView
                        content={decision.chain_of_thought}
                        titleKey={
                          decision.ai_model?.startsWith("quant:")
                            ? "executionReasoning"
                            : "chainOfThought"
                        }
                      />

                      {/* Trading Decisions */}
                      <div>
                        <h4 className="text-sm font-semibold mb-3">
                          {t("decisions.tradingDecisions")}
                        </h4>
                        <div className="space-y-3">
                          {decision.decisions.map((d, i) => {
                            // For close actions, resolve real leverage/size from account_snapshot or execution_results
                            const isCloseAction =
                              d.action === "close_long" ||
                              d.action === "close_short";
                            const snapshotPos = isCloseAction
                              ? (
                                  (
                                    decision.account_snapshot as Record<
                                      string,
                                      unknown
                                    > | null
                                  )?.positions as
                                    | Array<{
                                        symbol: string;
                                        leverage: number;
                                        size_usd: number;
                                      }>
                                    | undefined
                                )?.find((p) => p.symbol === d.symbol)
                              : undefined;
                            const execRes = isCloseAction
                              ? (
                                  decision.execution_results as
                                    | Array<Record<string, unknown>>
                                    | undefined
                                )?.find(
                                  (er) =>
                                    er.symbol === d.symbol &&
                                    er.action === d.action,
                                )
                              : undefined;
                            const displayLeverage = isCloseAction
                              ? ((execRes?.position_leverage as number) ??
                                snapshotPos?.leverage ??
                                d.leverage)
                              : d.leverage;
                            const displaySize = isCloseAction
                              ? ((execRes?.position_size_usd as number) ??
                                snapshotPos?.size_usd ??
                                d.position_size_usd)
                              : d.position_size_usd;

                            return (
                              <div
                                key={i}
                                className="p-4 rounded-lg bg-muted/30 border border-border/30"
                              >
                                <div className="flex items-center justify-between mb-3">
                                  <div className="flex items-center gap-3">
                                    <span className="text-lg font-bold">
                                      {d.symbol}
                                    </span>
                                    <Badge
                                      variant="outline"
                                      className={cn(getActionColor(d.action))}
                                    >
                                      {d.action.replace("_", " ").toUpperCase()}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                      <div
                                        className={cn(
                                          "h-full rounded-full",
                                          d.confidence >= 80
                                            ? "bg-[var(--profit)]"
                                            : d.confidence >= 60
                                              ? "bg-[var(--warning)]"
                                              : "bg-muted-foreground",
                                        )}
                                        style={{ width: `${d.confidence}%` }}
                                      />
                                    </div>
                                    <span className="text-sm font-medium">
                                      {d.confidence}%
                                    </span>
                                  </div>
                                </div>
                                {d.action !== "hold" && d.action !== "wait" && (
                                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                                    <div>
                                      <span className="text-muted-foreground">
                                        {t("decisions.leverage")}
                                      </span>
                                      <p className="font-mono font-semibold">
                                        {displayLeverage}x
                                      </p>
                                    </div>
                                    <div>
                                      <span className="text-muted-foreground">
                                        {t("decisions.size")}
                                      </span>
                                      <p className="font-mono font-semibold">
                                        ${displaySize.toLocaleString()}
                                      </p>
                                    </div>
                                    {d.stop_loss && (
                                      <div>
                                        <span className="text-muted-foreground">
                                          {t("decisions.stopLoss")}
                                        </span>
                                        <p className="font-mono font-semibold text-[var(--loss)]">
                                          ${d.stop_loss.toLocaleString()}
                                        </p>
                                      </div>
                                    )}
                                    {d.take_profit && (
                                      <div>
                                        <span className="text-muted-foreground">
                                          {t("decisions.takeProfit")}
                                        </span>
                                        <p className="font-mono font-semibold text-[var(--profit)]">
                                          ${d.take_profit.toLocaleString()}
                                        </p>
                                      </div>
                                    )}
                                  </div>
                                )}
                                <p className="text-sm text-muted-foreground mt-3 pt-3 border-t border-border/30">
                                  {d.reasoning}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Execution Records */}
                      {decision.execution_results &&
                        decision.execution_results.length > 0 && (
                          <div>
                            <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                              <Activity className="w-4 h-4 text-primary" />
                              {t("decisions.executionRecords")}
                            </h4>
                            <div className="space-y-2">
                              {(
                                decision.execution_results as Array<
                                  Record<string, unknown>
                                >
                              ).map((er, i) => {
                                const wasExecuted = er.executed === true;
                                const orderResult = er.order_result as Record<
                                  string,
                                  unknown
                                > | null;
                                const hasFailed =
                                  wasExecuted === false &&
                                  orderResult?.error != null;
                                return (
                                  <div
                                    key={i}
                                    className={`p-3 rounded-lg border ${
                                      wasExecuted
                                        ? "bg-[var(--profit)]/5 border-[var(--profit)]/20"
                                        : hasFailed
                                          ? "bg-[var(--loss)]/5 border-[var(--loss)]/20"
                                          : "bg-muted/30 border-border/30"
                                    }`}
                                  >
                                    <div className="flex items-center justify-between mb-2">
                                      <div className="flex items-center gap-2">
                                        <span className="font-semibold text-sm">
                                          {er.symbol as string}
                                        </span>
                                        <Badge
                                          variant="outline"
                                          className={cn(
                                            "text-xs",
                                            getActionColor(er.action as string),
                                          )}
                                        >
                                          {(er.action as string)
                                            ?.replace("_", " ")
                                            .toUpperCase()}
                                        </Badge>
                                      </div>
                                      <div className="flex items-center gap-1.5">
                                        {wasExecuted ? (
                                          <>
                                            <CheckCircle2 className="w-3.5 h-3.5 text-[var(--profit)]" />
                                            <span className="text-xs font-medium text-[var(--profit)]">
                                              {t("decisions.execution.success")}
                                            </span>
                                          </>
                                        ) : hasFailed ? (
                                          <>
                                            <XCircle className="w-3.5 h-3.5 text-[var(--loss)]" />
                                            <span className="text-xs font-medium text-[var(--loss)]">
                                              {t("decisions.execution.failed")}
                                            </span>
                                          </>
                                        ) : (
                                          <>
                                            <AlertCircle className="w-3.5 h-3.5 text-muted-foreground" />
                                            <span className="text-xs font-medium text-muted-foreground">
                                              {t("decisions.execution.skipped")}
                                            </span>
                                          </>
                                        )}
                                      </div>
                                    </div>
                                    {wasExecuted && orderResult && (
                                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                        {orderResult.order_id != null && (
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t("decisions.execution.orderId")}
                                            </span>
                                            <p className="font-mono font-medium truncate">
                                              {String(orderResult.order_id)}
                                            </p>
                                          </div>
                                        )}
                                        {orderResult.filled_size != null && (
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t(
                                                "decisions.execution.filledSize",
                                              )}
                                            </span>
                                            <p className="font-mono font-medium">
                                              {Number(orderResult.filled_size)}
                                            </p>
                                          </div>
                                        )}
                                        {orderResult.filled_price != null && (
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t(
                                                "decisions.execution.filledPrice",
                                              )}
                                            </span>
                                            <p className="font-mono font-medium">
                                              $
                                              {Number(
                                                orderResult.filled_price,
                                              ).toLocaleString()}
                                            </p>
                                          </div>
                                        )}
                                        {orderResult.status != null && (
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t("decisions.execution.status")}
                                            </span>
                                            <p className="font-mono font-medium">
                                              {String(orderResult.status)}
                                            </p>
                                          </div>
                                        )}
                                      </div>
                                    )}
                                    {wasExecuted &&
                                      er.requested_size_usd != null &&
                                      er.actual_size_usd != null && (
                                        <div className="flex gap-4 mt-2 text-xs">
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t(
                                                "decisions.execution.requestedSize",
                                              )}
                                            </span>
                                            <span className="font-mono font-medium ml-1">
                                              $
                                              {Number(
                                                er.requested_size_usd,
                                              ).toLocaleString()}
                                            </span>
                                          </div>
                                          <div>
                                            <span className="text-muted-foreground">
                                              {t(
                                                "decisions.execution.actualSize",
                                              )}
                                            </span>
                                            <span className="font-mono font-medium ml-1">
                                              $
                                              {Number(
                                                er.actual_size_usd,
                                              ).toLocaleString()}
                                            </span>
                                          </div>
                                        </div>
                                      )}
                                    {!wasExecuted && er.reason != null && (
                                      <div className="text-xs mt-1">
                                        <span className="text-muted-foreground">
                                          {t("decisions.execution.reason")}
                                          :{" "}
                                        </span>
                                        <span className="text-muted-foreground/80">
                                          {String(er.reason)}
                                        </span>
                                      </div>
                                    )}
                                    {hasFailed &&
                                      orderResult?.error != null && (
                                        <div className="text-xs mt-1">
                                          <span className="text-[var(--loss)]">
                                            {t("decisions.execution.reason")}
                                            :{" "}
                                          </span>
                                          <span className="text-[var(--loss)]/80">
                                            {String(orderResult.error)}
                                          </span>
                                        </div>
                                      )}
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        )}

                      {/* Raw AI Response / Execution Log */}
                      {decision.raw_response && (
                        <RawResponseViewer
                          rawResponse={decision.raw_response}
                          t={t}
                          isQuant={decision.ai_model?.startsWith("quant:")}
                        />
                      )}

                      {/* AI Info / Strategy Info */}
                      {decision.ai_model?.startsWith("quant:") ? (
                        // Quant strategy: only show strategy type
                        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/30">
                          <span>
                            {t("decisions.strategyType")}:{" "}
                            {decision.ai_model
                              .replace("quant:", "")
                              .toUpperCase()}
                          </span>
                        </div>
                      ) : (
                        // AI strategy: show full info
                        <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/30">
                          <span>
                            {t("decisions.model")}: {decision.ai_model}
                          </span>
                          <span>
                            {t("decisions.tokens")}: {decision.tokens_used}
                          </span>
                          <span>
                            {t("decisions.latency")}: {decision.latency_ms}ms
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </CollapsibleContent>
                </Card>
              </div>
            </Collapsible>
          );
        })}
      </div>
      {/* end loading overlay wrapper */}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1.5 pt-2">
          <Button
            variant="outline"
            size="icon"
            className="w-8 h-8"
            onClick={() => goToPage(page - 1)}
            disabled={page <= 1}
          >
            <ChevronLeft className="w-4 h-4" />
          </Button>
          {(() => {
            const pages: (number | "ellipsis-start" | "ellipsis-end")[] = [];
            if (totalPages <= 7) {
              for (let i = 1; i <= totalPages; i++) pages.push(i);
            } else {
              pages.push(1);
              if (page > 3) pages.push("ellipsis-start");
              const start = Math.max(2, page - 1);
              const end = Math.min(totalPages - 1, page + 1);
              for (let i = start; i <= end; i++) pages.push(i);
              if (page < totalPages - 2) pages.push("ellipsis-end");
              pages.push(totalPages);
            }
            return pages.map((p) =>
              typeof p === "string" ? (
                <span
                  key={p}
                  className="w-8 h-8 flex items-center justify-center text-sm text-muted-foreground"
                >
                  ...
                </span>
              ) : (
                <Button
                  key={p}
                  variant={p === page ? "default" : "outline"}
                  size="icon"
                  className="w-8 h-8 text-xs"
                  onClick={() => goToPage(p)}
                >
                  {p}
                </Button>
              ),
            );
          })()}
          <Button
            variant="outline"
            size="icon"
            className="w-8 h-8"
            onClick={() => goToPage(page + 1)}
            disabled={page >= totalPages}
          >
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      )}
    </div>
  );
}

// Settings Tab (Quick settings + Read-only strategy config)
function SettingsTab({
  agent,
  agentId,
  t,
  onUpdate,
}: {
  agent: NonNullable<ReturnType<typeof useAgent>["data"]>;
  agentId: string;
  t: ReturnType<typeof useTranslations>;
  onUpdate: () => void;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const { models } = useUserModels();
  const groupedModels = groupModelsByProvider(models);

  const config = agent.config as Record<string, unknown>;

  // Quick settings form (only editable fields)
  const [formData, setFormData] = useState({
    name: agent.name,
    description: agent.description || "",
    ai_model: agent.ai_model || "",
    execution_interval_minutes: agent.execution_interval_minutes,
    auto_execute: (config?.auto_execute as boolean) ?? true,
  });

  const updateForm = (patch: Partial<typeof formData>) =>
    setFormData((prev) => ({ ...prev, ...patch }));

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);

    try {
      await agentsApi.update(agentId, {
        name: formData.name,
        ai_model: formData.ai_model || undefined,
        execution_interval_minutes: formData.execution_interval_minutes,
        auto_execute: formData.auto_execute,
      });
      setSaveSuccess(true);
      onUpdate();
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.failedToUpdateSettings");
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await agentsApi.delete(agentId);
      window.location.href = "/agents";
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.failedToDeleteAgent");
      setSaveError(message);
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  const inputClass =
    "w-full px-3 py-2 rounded-md bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50";
  const smallInputClass =
    "w-24 px-3 py-2 rounded-md bg-background border border-border focus:outline-none focus:ring-2 focus:ring-primary/50";

  return (
    <div className="space-y-6">
      {/* Quick Settings (Editable) */}
      <Card className="bg-card/50 border-border/50">
        <CardHeader>
          <CardTitle className="text-lg">
            {t("settings.quickSettings")}
          </CardTitle>
          <CardDescription>{t("settings.quickSettingsDesc")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.agentName")}
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => updateForm({ name: e.target.value })}
                className={inputClass}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.aiModel")}
              </label>
              <Select
                value={formData.ai_model}
                onValueChange={(v) => updateForm({ ai_model: v })}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t("settings.aiModelPlaceholder")} />
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
                      {t("settings.noModels")}
                    </div>
                  )}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              {t("settings.description")}
            </label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => updateForm({ description: e.target.value })}
              className={inputClass}
              placeholder={t("settings.descriptionPlaceholder")}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">
                {t("settings.executionInterval")}
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  min={5}
                  max={1440}
                  value={formData.execution_interval_minutes}
                  onChange={(e) =>
                    updateForm({
                      execution_interval_minutes:
                        parseInt(e.target.value) || 30,
                    })
                  }
                  className={smallInputClass}
                />
                <span className="text-sm text-muted-foreground">
                  {t("settings.minutes")}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
              <div>
                <p className="text-sm font-medium">
                  {t("settings.autoExecute")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("settings.autoExecuteDesc")}
                </p>
              </div>
              <Switch
                checked={formData.auto_execute}
                onCheckedChange={(checked) =>
                  updateForm({ auto_execute: checked })
                }
              />
            </div>
          </div>

          {/* Save Button */}
          <div className="flex items-center gap-4 pt-2">
            <Button onClick={handleSave} disabled={isSaving}>
              {isSaving ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4 mr-2" />
              )}
              {t("settings.saveChanges")}
            </Button>

            {saveSuccess && (
              <span className="text-sm text-[var(--profit)] flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" />
                {t("settings.saved")}
              </span>
            )}

            {saveError && (
              <span className="text-sm text-[var(--loss)]">{saveError}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="bg-card/50 border-[var(--loss)]/30">
        <CardHeader>
          <CardTitle className="text-lg text-[var(--loss)]">
            {t("settings.dangerZone")}
          </CardTitle>
          <CardDescription>{t("settings.dangerZoneDesc")}</CardDescription>
        </CardHeader>
        <CardContent>
          {!["stopped", "draft"].includes(agent.status) ? (
            <div className="space-y-2">
              <Button
                variant="outline"
                className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                disabled
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t("settings.deleteAgent")}
              </Button>
              <p className="text-sm text-muted-foreground">
                {t("settings.deleteRequireStopped")}
              </p>
            </div>
          ) : !showDeleteConfirm ? (
            <Button
              variant="outline"
              className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
              onClick={() => setShowDeleteConfirm(true)}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              {t("settings.deleteAgent")}
            </Button>
          ) : (
            <div className="p-4 rounded-lg bg-[var(--loss)]/10 border border-[var(--loss)]/30 space-y-4">
              <p className="text-sm">{t("settings.deleteConfirm")}</p>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                >
                  {t("settings.cancel")}
                </Button>
                <Button
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4 mr-2" />
                  )}
                  {t("settings.confirmDelete")}
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function AgentDetailPage() {
  const t = useTranslations("agentDetail");
  const params = useParams();
  const searchParams = useSearchParams();
  const agentId = params.id as string;
  const toast = useToast();

  // URL query params for deep linking: ?tab=decisions&decision=<id>
  const tabParam = searchParams.get("tab");
  const decisionParam = searchParams.get("decision");
  const validTabs = ["overview", "decisions", "positions", "settings"];
  const initialTab =
    tabParam && validTabs.includes(tabParam) ? tabParam : "overview";
  const [activeTab, setActiveTab] = useState(initialTab);

  const { data: agent, isLoading, error, mutate } = useAgent(agentId);
  const { trigger: updateStatus, isMutating: isUpdating } =
    useUpdateAgentStatus(agentId);
  const [isRunningNow, setIsRunningNow] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  const handleRunNow = async () => {
    setIsRunningNow(true);
    try {
      await agentsApi.trigger(agentId);
      toast.success(t("toast.runNowSuccess"));
      mutate(); // refresh agent data
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.runNowFailed");
      toast.error(t("toast.runNowFailed"), message);
    } finally {
      setIsRunningNow(false);
    }
  };

  const handleStatusChange = async (status: StrategyStatus) => {
    try {
      await updateStatus(status);
      mutate();
      const statusKey = status === "active" ? "started" : status;
      toast.success(t(`toast.${statusKey}`));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.updateFailed");
      toast.error(t("toast.updateFailed"), message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !agent) {
    return (
      <div className="space-y-6">
        <Link href="/agents">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="w-4 h-4 mr-2" />
            {t("backToAgents")}
          </Button>
        </Link>
        <Card className="bg-destructive/10 border-destructive/30">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <p className="text-destructive">
              {error?.message || t("notFound")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <DetailPageHeader
        backHref="/agents"
        icon={<Bot className="w-6 h-6 text-primary" />}
        title={agent.name}
        description={agent.description ?? undefined}
        badges={[
          {
            label: t(`status.${agent.status}`),
            className: getStatusColor(agent.status),
          },
          {
            label: t(`executionMode.${agent.execution_mode}`),
            className:
              agent.execution_mode === "live"
                ? "bg-[var(--profit)]/15 text-[var(--profit)] border-[var(--profit)]/30"
                : "bg-muted/50 text-muted-foreground border-border/50",
          },
          ...(agent.execution_mode === "live" && agent.account_name
            ? [
                {
                  label: agent.account_name,
                  className:
                    "bg-muted/30 text-muted-foreground border-border/30",
                },
              ]
            : []),
        ]}
        primaryActions={
          <div className="flex items-center gap-2">
            {agent.status === "active" ? (
              <Button
                variant="default"
                className="bg-primary/20 text-primary hover:bg-primary/30"
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
                  onClick={() => handleStatusChange("active")}
                  disabled={isUpdating}
                >
                  {isUpdating ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  {agent.status === "draft"
                    ? t("actions.start")
                    : t("actions.resume")}
                </Button>
                {agent.status === "paused" && (
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
              </>
            ) : agent.status === "error" || agent.status === "warning" ? (
              <>
                <Button
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
                  className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                  onClick={() => setShowStopConfirm(true)}
                  disabled={isUpdating}
                >
                  <Square className="w-4 h-4 mr-2" />
                  {t("actions.stop")}
                </Button>
              </>
            ) : null}
          </div>
        }
      />

      {/* Stop Confirm Dialog */}
      <Dialog open={showStopConfirm} onOpenChange={setShowStopConfirm}>
        <DialogContent showCloseButton={false}>
          <DialogHeader>
            <DialogTitle>{t("actions.stopConfirmTitle")}</DialogTitle>
            <DialogDescription>
              {t("actions.stopConfirmDesc")}
            </DialogDescription>
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
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-muted/50">
          <TabsTrigger value="overview">{t("tabs.overview")}</TabsTrigger>
          <TabsTrigger value="decisions">{t("tabs.decisions")}</TabsTrigger>
          <TabsTrigger value="positions">{t("tabs.positions")}</TabsTrigger>
          <TabsTrigger value="settings">{t("tabs.settings")}</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <OverviewTab agent={agent} agentId={agentId} t={t} />
        </TabsContent>

        <TabsContent value="decisions" className="mt-6">
          <DecisionsTab
            agentId={agentId}
            agentName={agent.name}
            t={t}
            onRunNow={handleRunNow}
            isRunningNow={isRunningNow}
            agentStatus={agent.status}
            highlightDecisionId={decisionParam ?? undefined}
          />
        </TabsContent>

        <TabsContent value="positions" className="mt-6">
          <PositionsTab agentId={agentId} t={t} />
        </TabsContent>

        <TabsContent value="settings" className="mt-6">
          <SettingsTab
            agent={agent}
            agentId={agentId}
            t={t}
            onUpdate={mutate}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
