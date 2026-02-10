"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { format } from "date-fns";
import {
  FlaskConical,
  Play,
  TrendingUp,
  TrendingDown,
  Loader2,
  BarChart3,
  Target,
  Activity,
  Percent,
  ChevronsUpDown,
  Check,
  X,
  DollarSign,
  Clock,
  ArrowUpDown,
  Trophy,
  Zap,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { DatePicker } from "@/components/ui/date-picker";
import { cn } from "@/lib/utils";
import { useStrategies, useRunBacktest, useBacktestSymbols } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type {
  BacktestExchange,
  BacktestResponse,
  TradeRecord,
} from "@/lib/api";
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  ReferenceLine,
} from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
  type ChartConfig,
} from "@/components/ui/chart";

// Supported exchanges for backtesting
const EXCHANGE_OPTIONS: {
  value: BacktestExchange;
  label: string;
  icon: string;
}[] = [
  { value: "binance", label: "Binance", icon: "🟡" },
  { value: "bybit", label: "Bybit", icon: "🟠" },
  { value: "okx", label: "OKX", icon: "⬛" },
  { value: "hyperliquid", label: "Hyperliquid", icon: "🔷" },
];

// ===================== Helper Components =====================

function MetricCard({
  icon: Icon,
  label,
  value,
  valueColor,
  prefix,
  suffix,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  valueColor?: string;
  prefix?: string;
  suffix?: string;
}) {
  return (
    <Card className="bg-muted/30 border-0">
      <CardContent className="pt-4 pb-3">
        <div className="flex items-center gap-2 text-muted-foreground mb-1">
          <Icon className="w-4 h-4" />
          <span className="text-xs">{label}</span>
        </div>
        <p
          className={cn(
            "text-xl font-bold font-mono truncate",
            valueColor
          )}
        >
          {prefix}
          {value}
          {suffix}
        </p>
      </CardContent>
    </Card>
  );
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${Math.round(minutes)}m`;
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)}h`;
  return `${(minutes / 1440).toFixed(1)}d`;
}

function formatPrice(v: number): string {
  if (Math.abs(v) >= 1000) return `$${v.toFixed(0)}`;
  if (Math.abs(v) >= 1) return `$${v.toFixed(2)}`;
  return `$${v.toFixed(4)}`;
}

// ===================== Tab: Overview =====================

function OverviewTab({ data }: { data: BacktestResponse }) {
  const t = useTranslations("backtest");
  const ts = data.trade_statistics;

  // Down-sample equity/drawdown curves for performance
  const equityData = useMemo(() => {
    const ec = data.equity_curve;
    if (ec.length <= 300) return ec;
    const step = Math.ceil(ec.length / 300);
    return ec.filter((_, i) => i % step === 0 || i === ec.length - 1);
  }, [data.equity_curve]);

  const drawdownData = useMemo(() => {
    const dc = data.drawdown_curve;
    if (dc.length <= 300) return dc;
    const step = Math.ceil(dc.length / 300);
    return dc.filter((_, i) => i % step === 0 || i === dc.length - 1);
  }, [data.drawdown_curve]);

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        <MetricCard
          icon={data.total_return_percent >= 0 ? TrendingUp : TrendingDown}
          label={t("metrics.totalReturn")}
          value={`${data.total_return_percent >= 0 ? "+" : ""}${data.total_return_percent.toFixed(2)}%`}
          valueColor={
            data.total_return_percent >= 0
              ? "text-[var(--profit)]"
              : "text-[var(--loss)]"
          }
        />
        <MetricCard
          icon={TrendingDown}
          label={t("metrics.maxDrawdown")}
          value={`-${Math.abs(data.max_drawdown_percent).toFixed(2)}%`}
          valueColor="text-[var(--loss)]"
        />
        <MetricCard
          icon={Target}
          label={t("metrics.sharpeRatio")}
          value={(data.sharpe_ratio ?? 0).toFixed(2)}
        />
        <MetricCard
          icon={Activity}
          label={t("metrics.totalTrades")}
          value={data.total_trades}
        />
        <MetricCard
          icon={Percent}
          label={t("metrics.winRate")}
          value={`${data.win_rate.toFixed(1)}%`}
          valueColor={
            data.win_rate >= 50
              ? "text-[var(--profit)]"
              : "text-[var(--loss)]"
          }
        />
        <MetricCard
          icon={BarChart3}
          label={t("metrics.profitFactor")}
          value={data.profit_factor === Infinity ? "∞" : data.profit_factor.toFixed(2)}
          valueColor={
            data.profit_factor >= 1
              ? "text-[var(--profit)]"
              : "text-[var(--loss)]"
          }
        />
        <MetricCard
          icon={Target}
          label={t("metrics.sortinoRatio")}
          value={(ts?.sortino_ratio ?? 0).toFixed(2)}
        />
        <MetricCard
          icon={DollarSign}
          label={t("metrics.finalBalance")}
          value={`$${data.final_balance.toFixed(0)}`}
          valueColor={
            data.final_balance >= data.initial_balance
              ? "text-[var(--profit)]"
              : "text-[var(--loss)]"
          }
        />
        <MetricCard
          icon={DollarSign}
          label={t("metrics.totalFees")}
          value={`$${data.total_fees.toFixed(2)}`}
        />
        <MetricCard
          icon={Zap}
          label={t("metrics.expectancy")}
          value={`$${(ts?.expectancy ?? 0).toFixed(2)}`}
          valueColor={
            (ts?.expectancy ?? 0) >= 0
              ? "text-[var(--profit)]"
              : "text-[var(--loss)]"
          }
        />
      </div>

      {/* Equity Curve + Drawdown Curve side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {equityData.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.equityCurve")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  equity: { label: t("charts.equity"), color: "var(--primary)" },
                  balance: { label: t("charts.balance"), color: "var(--muted-foreground)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={equityData}>
                  <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-equity)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-equity)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="timestamp"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => v?.slice(5, 10) ?? ""}
                  />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(v) => String(v).replace("T", " ").slice(0, 16)}
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            ${Number(value).toFixed(2)}
                          </span>
                        )}
                      />
                    }
                  />
                  <ChartLegend content={<ChartLegendContent />} />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="var(--color-equity)"
                    fill="url(#eqGrad)"
                    strokeWidth={2}
                  />
                  <Area
                    type="monotone"
                    dataKey="balance"
                    stroke="var(--color-balance)"
                    fill="none"
                    strokeWidth={1}
                    strokeDasharray="4 2"
                  />
                </AreaChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}

        {drawdownData.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.drawdownCurve")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  drawdown_percent: { label: t("charts.drawdown"), color: "var(--loss, #ef4444)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={drawdownData}>
                  <defs>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-drawdown_percent)" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="var(--color-drawdown_percent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="timestamp"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => v?.slice(5, 10) ?? ""}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => `-${v}%`}
                    reversed
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(v) => String(v).replace("T", " ").slice(0, 16)}
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            -{Number(value).toFixed(2)}%
                          </span>
                        )}
                      />
                    }
                  />
                  <Area
                    type="monotone"
                    dataKey="drawdown_percent"
                    stroke="var(--color-drawdown_percent)"
                    fill="url(#ddGrad)"
                    strokeWidth={1.5}
                  />
                </AreaChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

// ===================== Tab: Trade Analysis =====================

function TradeAnalysisTab({ data }: { data: BacktestResponse }) {
  const t = useTranslations("backtest");
  const ts = data.trade_statistics;

  // P&L distribution histogram
  const pnlBins = useMemo(() => {
    if (!data.trades.length) return [];
    const pnls = data.trades.map((t) => t.pnl);
    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const range = max - min || 1;
    const binCount = Math.min(20, Math.max(5, Math.ceil(data.trades.length / 3)));
    const binSize = range / binCount;
    const bins: { range: string; count: number; isPositive: boolean }[] = [];
    for (let i = 0; i < binCount; i++) {
      const lo = min + i * binSize;
      const hi = lo + binSize;
      const count = pnls.filter(
        (p) => p >= lo && (i === binCount - 1 ? p <= hi : p < hi)
      ).length;
      bins.push({
        range: `${lo >= 0 ? "+" : ""}${lo.toFixed(0)}`,
        count,
        isPositive: lo + binSize / 2 >= 0,
      });
    }
    return bins;
  }, [data.trades]);

  // Holding time distribution
  const holdingDist = useMemo(() => {
    const buckets = [
      { key: "lessThan1h", max: 60, count: 0 },
      { key: "1hTo4h", max: 240, count: 0 },
      { key: "4hTo24h", max: 1440, count: 0 },
      { key: "1dTo7d", max: 10080, count: 0 },
      { key: "moreThan7d", max: Infinity, count: 0 },
    ];
    for (const trade of data.trades) {
      for (const b of buckets) {
        if (trade.duration_minutes < b.max) {
          b.count++;
          break;
        }
      }
    }
    return buckets.map((b) => ({
      name: t(`tradeAnalysis.${b.key}`),
      count: b.count,
    }));
  }, [data.trades, t]);

  const longStats = ts?.long_stats;
  const shortStats = ts?.short_stats;

  return (
    <div className="space-y-6">
      {/* P&L Distribution + Holding Time Distribution side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {pnlBins.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.pnlDistribution")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  count: { label: t("charts.tradeCount"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlBins}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="range" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ReferenceLine x="0" stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                  <Bar dataKey="count" name={t("charts.tradeCount")} radius={[4, 4, 0, 0]}>
                    {pnlBins.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={entry.isPositive ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                        fillOpacity={0.8}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}

        {holdingDist.some((b) => b.count > 0) && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("tradeAnalysis.holdingTimeDistribution")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  count: { label: t("tradeAnalysis.trades"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={holdingDist}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <Bar
                    dataKey="count"
                    fill="var(--color-count)"
                    fillOpacity={0.7}
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Long vs Short + Consecutive Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Long vs Short */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("tradeAnalysis.longVsShort")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              {/* Long */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-[var(--profit)]">
                  {t("tradeAnalysis.longTrades")}
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("metrics.totalTrades")}</span>
                    <span className="font-mono">{longStats?.total_trades ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("metrics.winRate")}</span>
                    <span className="font-mono">{(longStats?.win_rate ?? 0).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("charts.pnl")}</span>
                    <span
                      className={cn(
                        "font-mono",
                        (longStats?.total_pnl ?? 0) >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]"
                      )}
                    >
                      ${(longStats?.total_pnl ?? 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
              {/* Short */}
              <div className="space-y-2">
                <div className="text-xs font-medium text-[var(--loss)]">
                  {t("tradeAnalysis.shortTrades")}
                </div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("metrics.totalTrades")}</span>
                    <span className="font-mono">{shortStats?.total_trades ?? 0}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("metrics.winRate")}</span>
                    <span className="font-mono">{(shortStats?.win_rate ?? 0).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">{t("charts.pnl")}</span>
                    <span
                      className={cn(
                        "font-mono",
                        (shortStats?.total_pnl ?? 0) >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]"
                      )}
                    >
                      ${(shortStats?.total_pnl ?? 0).toFixed(2)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Consecutive + Extended Stats */}
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("tradeAnalysis.consecutiveAnalysis")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.maxConsecutiveWins")}</span>
                <span className="font-mono text-[var(--profit)]">
                  {ts?.max_consecutive_wins ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.maxConsecutiveLosses")}</span>
                <span className="font-mono text-[var(--loss)]">
                  {ts?.max_consecutive_losses ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.avgHoldingHours")}</span>
                <span className="font-mono">{(ts?.avg_holding_hours ?? 0).toFixed(1)}h</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.largestWin")}</span>
                <span className="font-mono text-[var(--profit)]">
                  ${(ts?.largest_win ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.largestLoss")}</span>
                <span className="font-mono text-[var(--loss)]">
                  ${(ts?.largest_loss ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.averageWin")}</span>
                <span className="font-mono">${(ts?.average_win ?? 0).toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">{t("metrics.averageLoss")}</span>
                <span className="font-mono">${(ts?.average_loss ?? 0).toFixed(2)}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ===================== Tab: Time Analysis =====================

function TimeAnalysisTab({ data }: { data: BacktestResponse }) {
  const t = useTranslations("backtest");

  const weekdayKeys = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] as const;

  const monthlyData = useMemo(() => {
    return (data.monthly_returns || []).map((m) => ({
      ...m,
      isPositive: m.return_percent >= 0,
    }));
  }, [data.monthly_returns]);

  // Cumulative returns
  const cumulativeData = useMemo(() => {
    let cum = 0;
    return monthlyData.map((m) => {
      cum += m.return_percent;
      return { month: m.month, cumulative: parseFloat(cum.toFixed(2)) };
    });
  }, [monthlyData]);

  // P&L by day of week (computed from trades)
  const pnlByWeekday = useMemo(() => {
    const buckets = weekdayKeys.map(() => 0);
    for (const trade of data.trades) {
      if (!trade.opened_at) continue;
      const day = new Date(trade.opened_at).getDay(); // 0=Sun..6=Sat
      buckets[day] += trade.pnl;
    }
    return weekdayKeys.map((key, i) => ({
      name: t(`timeAnalysis.${key}`),
      pnl: parseFloat(buckets[i].toFixed(2)),
      isPositive: buckets[i] >= 0,
    }));
  }, [data.trades, t]);

  // P&L by hour of day (computed from trades)
  const pnlByHour = useMemo(() => {
    const buckets = Array.from({ length: 24 }, () => 0);
    for (const trade of data.trades) {
      if (!trade.opened_at) continue;
      const hour = new Date(trade.opened_at).getHours();
      buckets[hour] += trade.pnl;
    }
    return buckets.map((pnl, h) => ({
      name: `${String(h).padStart(2, "0")}:00`,
      pnl: parseFloat(pnl.toFixed(2)),
      isPositive: pnl >= 0,
    }));
  }, [data.trades]);

  return (
    <div className="space-y-6">
      {/* Monthly Returns + Cumulative Return side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {monthlyData.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.monthlyReturns")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  return_percent: { label: t("charts.returnPercent"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={monthlyData}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => v?.slice(2) ?? ""}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => `${v}%`}
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            {Number(value).toFixed(2)}%
                          </span>
                        )}
                      />
                    }
                  />
                  <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                  <Bar dataKey="return_percent" name={t("charts.returnPercent")} radius={[4, 4, 0, 0]}>
                    {monthlyData.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={entry.isPositive ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                        fillOpacity={0.8}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}

        {cumulativeData.length > 0 && (
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.cumulativeReturn")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  cumulative: { label: t("charts.cumulativeReturn"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={cumulativeData}>
                  <defs>
                    <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--color-cumulative)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--color-cumulative)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="month"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => v?.slice(2) ?? ""}
                  />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            {Number(value).toFixed(2)}%
                          </span>
                        )}
                      />
                    }
                  />
                  <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                  <Area
                    type="monotone"
                    dataKey="cumulative"
                    stroke="var(--color-cumulative)"
                    fill="url(#cumGrad)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ChartContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {/* P&L by Weekday + P&L by Hour side by side */}
      {data.trades.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.pnlByWeekday")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  pnl: { label: t("charts.pnl"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlByWeekday}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            ${Number(value).toFixed(2)}
                          </span>
                        )}
                      />
                    }
                  />
                  <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                  <Bar dataKey="pnl" name={t("charts.pnl")} radius={[4, 4, 0, 0]}>
                    {pnlByWeekday.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={entry.isPositive ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                        fillOpacity={0.8}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>

          <Card className="bg-card/50 border-border/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">
                {t("charts.pnlByHour")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ChartContainer
                config={{
                  pnl: { label: t("charts.pnl"), color: "var(--primary)" },
                } satisfies ChartConfig}
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlByHour}>
                  <CartesianGrid vertical={false} />
                  <XAxis dataKey="name" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} interval={2} />
                  <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        formatter={(value) => (
                          <span className="font-mono font-medium text-foreground">
                            ${Number(value).toFixed(2)}
                          </span>
                        )}
                      />
                    }
                  />
                  <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                  <Bar dataKey="pnl" name={t("charts.pnl")} radius={[4, 4, 0, 0]}>
                    {pnlByHour.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={entry.isPositive ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                        fillOpacity={0.8}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ChartContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Monthly Returns Table */}
      {monthlyData.length > 0 && (
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("charts.monthlyReturns")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="text-left py-2 px-3 text-muted-foreground font-medium">
                      {t("history.period")}
                    </th>
                    <th className="text-right py-2 px-3 text-muted-foreground font-medium">
                      {t("charts.returnPercent")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {monthlyData.map((m) => (
                    <tr key={m.month} className="border-b border-border/20">
                      <td className="py-2 px-3 font-mono text-xs">{m.month}</td>
                      <td
                        className={cn(
                          "py-2 px-3 text-right font-mono text-xs",
                          m.isPositive
                            ? "text-[var(--profit)]"
                            : "text-[var(--loss)]"
                        )}
                      >
                        {m.isPositive ? "+" : ""}
                        {m.return_percent.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ===================== Tab: Symbol Breakdown =====================

function SymbolBreakdownTab({ data }: { data: BacktestResponse }) {
  const t = useTranslations("backtest");
  const sb = data.symbol_breakdown || [];

  if (sb.length === 0) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="py-12 text-center text-muted-foreground">
          {t("symbolBreakdown.noData")}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Symbol P&L + Win Rate side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("charts.symbolComparison")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{
                total_pnl: { label: t("charts.pnl"), color: "var(--primary)" },
              } satisfies ChartConfig}
              className="min-h-[250px] w-full"
            >
              <BarChart accessibilityLayer data={sb}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="symbol" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(value) => (
                        <span className="font-mono font-medium text-foreground">
                          ${Number(value).toFixed(2)}
                        </span>
                      )}
                    />
                  }
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                <Bar dataKey="total_pnl" name={t("charts.pnl")} radius={[4, 4, 0, 0]}>
                  {sb.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.total_pnl >= 0 ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                      fillOpacity={0.8}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              {t("charts.symbolWinRate")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer
              config={{
                win_rate: { label: t("symbolBreakdown.winRate"), color: "var(--primary)" },
              } satisfies ChartConfig}
              className="min-h-[250px] w-full"
            >
              <BarChart accessibilityLayer data={sb}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="symbol" tickLine={false} axisLine={false} tickMargin={8} tick={{ fontSize: 10 }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} tickFormatter={(v) => `${v}%`} domain={[0, 100]} />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(value) => (
                        <span className="font-mono font-medium text-foreground">
                          {Number(value).toFixed(1)}%
                        </span>
                      )}
                    />
                  }
                />
                <ReferenceLine y={50} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                <Bar dataKey="win_rate" name={t("symbolBreakdown.winRate")} radius={[4, 4, 0, 0]}>
                  {sb.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.win_rate >= 50 ? "var(--profit, #22c55e)" : "var(--loss, #ef4444)"}
                      fillOpacity={0.8}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      </div>

      {/* Symbol Table */}
      <Card className="bg-card/50 border-border/50">
        <CardContent className="pt-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50">
                  <th className="text-left py-2 px-3 text-muted-foreground font-medium">
                    {t("symbolBreakdown.symbol")}
                  </th>
                  <th className="text-right py-2 px-3 text-muted-foreground font-medium">
                    {t("symbolBreakdown.trades")}
                  </th>
                  <th className="text-right py-2 px-3 text-muted-foreground font-medium">
                    {t("symbolBreakdown.winRate")}
                  </th>
                  <th className="text-right py-2 px-3 text-muted-foreground font-medium">
                    {t("symbolBreakdown.totalPnl")}
                  </th>
                  <th className="text-right py-2 px-3 text-muted-foreground font-medium">
                    {t("symbolBreakdown.avgPnl")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sb.map((s) => (
                  <tr key={s.symbol} className="border-b border-border/20">
                    <td className="py-2 px-3 font-mono font-medium">{s.symbol}</td>
                    <td className="py-2 px-3 text-right font-mono">{s.total_trades}</td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.win_rate >= 50
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]"
                      )}
                    >
                      {s.win_rate.toFixed(1)}%
                    </td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.total_pnl >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]"
                      )}
                    >
                      ${s.total_pnl.toFixed(2)}
                    </td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.average_pnl >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]"
                      )}
                    >
                      ${s.average_pnl.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// ===================== Tab: Trade List =====================

function TradeListTab({ data }: { data: BacktestResponse }) {
  const t = useTranslations("backtest");
  const [sortKey, setSortKey] = useState<keyof TradeRecord>("closed_at");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    const trades = [...data.trades];
    trades.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (typeof av === "number" && typeof bv === "number") {
        return sortAsc ? av - bv : bv - av;
      }
      return sortAsc
        ? String(av).localeCompare(String(bv))
        : String(bv).localeCompare(String(av));
    });
    return trades;
  }, [data.trades, sortKey, sortAsc]);

  const handleSort = (key: keyof TradeRecord) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  const exitReasonLabel = (reason: string) => {
    const map: Record<string, string> = {
      manual: t("tradeList.manual"),
      stop_loss: t("tradeList.stopLoss"),
      take_profit: t("tradeList.takeProfit"),
      liquidation: t("tradeList.liquidation"),
      signal: t("tradeList.signal"),
      reverse: t("tradeList.reverse"),
    };
    return map[reason] || reason;
  };

  if (!data.trades.length) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="py-12 text-center text-muted-foreground">
          {t("tradeList.noTrades")}
        </CardContent>
      </Card>
    );
  }

  const SortHeader = ({
    children,
    field,
    className: cls,
  }: {
    children: React.ReactNode;
    field: keyof TradeRecord;
    className?: string;
  }) => (
    <th
      className={cn(
        "py-2 px-2 text-muted-foreground font-medium cursor-pointer hover:text-foreground select-none",
        cls
      )}
      onClick={() => handleSort(field)}
    >
      <span className="inline-flex items-center gap-1">
        {children}
        {sortKey === field && (
          <ArrowUpDown className="w-3 h-3" />
        )}
      </span>
    </th>
  );

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="pt-4">
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50">
                <SortHeader field="symbol" className="text-left">
                  {t("tradeList.symbol")}
                </SortHeader>
                <SortHeader field="side" className="text-left">
                  {t("tradeList.side")}
                </SortHeader>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.leverage")}
                </th>
                <SortHeader field="entry_price" className="text-right">
                  {t("tradeList.entryPrice")}
                </SortHeader>
                <SortHeader field="exit_price" className="text-right">
                  {t("tradeList.exitPrice")}
                </SortHeader>
                <SortHeader field="pnl" className="text-right">
                  {t("tradeList.pnl")}
                </SortHeader>
                <SortHeader field="pnl_percent" className="text-right">
                  {t("tradeList.pnlPercent")}
                </SortHeader>
                <SortHeader field="duration_minutes" className="text-right">
                  {t("tradeList.duration")}
                </SortHeader>
                <SortHeader field="exit_reason" className="text-left">
                  {t("tradeList.exitReason")}
                </SortHeader>
                <SortHeader field="closed_at" className="text-right">
                  {t("tradeList.closeTime")}
                </SortHeader>
              </tr>
            </thead>
            <tbody>
              {sorted.map((trade, i) => (
                <tr
                  key={i}
                  className={cn(
                    "border-b border-border/10 hover:bg-muted/30 transition-colors",
                    trade.pnl > 0
                      ? "bg-[var(--profit)]/[0.03]"
                      : trade.pnl < 0
                        ? "bg-[var(--loss)]/[0.03]"
                        : ""
                  )}
                >
                  <td className="py-1.5 px-2 font-mono font-medium">
                    {trade.symbol}
                  </td>
                  <td className="py-1.5 px-2">
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-xs font-medium",
                        trade.side === "long"
                          ? "bg-[var(--profit)]/10 text-[var(--profit)]"
                          : "bg-[var(--loss)]/10 text-[var(--loss)]"
                      )}
                    >
                      {trade.side === "long"
                        ? t("tradeList.long")
                        : t("tradeList.short")}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono">
                    {trade.leverage}x
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono">
                    {formatPrice(trade.entry_price)}
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono">
                    {formatPrice(trade.exit_price)}
                  </td>
                  <td
                    className={cn(
                      "py-1.5 px-2 text-right font-mono font-medium",
                      trade.pnl >= 0
                        ? "text-[var(--profit)]"
                        : "text-[var(--loss)]"
                    )}
                  >
                    {trade.pnl >= 0 ? "+" : ""}
                    {trade.pnl.toFixed(2)}
                  </td>
                  <td
                    className={cn(
                      "py-1.5 px-2 text-right font-mono",
                      trade.pnl_percent >= 0
                        ? "text-[var(--profit)]"
                        : "text-[var(--loss)]"
                    )}
                  >
                    {trade.pnl_percent >= 0 ? "+" : ""}
                    {trade.pnl_percent.toFixed(2)}%
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono">
                    {formatDuration(trade.duration_minutes)}
                  </td>
                  <td className="py-1.5 px-2">
                    <span
                      className={cn(
                        "px-1.5 py-0.5 rounded text-xs",
                        trade.exit_reason === "take_profit"
                          ? "bg-[var(--profit)]/10 text-[var(--profit)]"
                          : trade.exit_reason === "stop_loss"
                            ? "bg-[var(--loss)]/10 text-[var(--loss)]"
                            : "bg-muted text-muted-foreground"
                      )}
                    >
                      {exitReasonLabel(trade.exit_reason)}
                    </span>
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono text-muted-foreground">
                    {trade.closed_at?.replace("T", " ").slice(0, 16)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

// ===================== Main Page =====================

export default function BacktestPage() {
  const t = useTranslations("backtest");
  const toast = useToast();
  const { data: agents } = useStrategies();
  const { trigger: runBacktest, isMutating: isRunning } = useRunBacktest();

  // Exchange state
  const [selectedExchange, setSelectedExchange] =
    useState<BacktestExchange>("hyperliquid");
  const { data: symbolsData, isLoading: isLoadingSymbols } =
    useBacktestSymbols(selectedExchange);

  const symbolsList = useMemo(
    () => symbolsData?.symbols ?? [],
    [symbolsData]
  );

  // Form state
  const [selectedAgent, setSelectedAgent] = useState<string>("");
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([]);
  const [pairOpen, setPairOpen] = useState(false);
  const [startDate, setStartDate] = useState<Date | undefined>();
  const [endDate, setEndDate] = useState<Date | undefined>();
  const [initialBalance, setInitialBalance] = useState<string>("10000");

  // Results state
  const [results, setResults] = useState<BacktestResponse | null>(null);

  const handleExchangeChange = (value: string) => {
    setSelectedExchange(value as BacktestExchange);
    setSelectedSymbols([]);
  };

  const toggleSymbol = (symbol: string) => {
    setSelectedSymbols((prev) =>
      prev.includes(symbol)
        ? prev.filter((s) => s !== symbol)
        : [...prev, symbol]
    );
  };

  const removeSymbol = (symbol: string) => {
    setSelectedSymbols((prev) => prev.filter((s) => s !== symbol));
  };

  const handleRunBacktest = async () => {
    if (!selectedAgent || selectedSymbols.length === 0 || !startDate || !endDate) return;

    try {
      const result = await runBacktest({
        strategy_id: selectedAgent,
        start_date: format(startDate, "yyyy-MM-dd"),
        end_date: format(endDate, "yyyy-MM-dd"),
        initial_balance: parseFloat(initialBalance),
        symbols: selectedSymbols,
        exchange: selectedExchange,
      });

      if (result) {
        setResults(result);
        toast.success(
          t("toast.completed"),
          `Total return: ${result.total_return_percent?.toFixed(2)}%`
        );
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : t("toast.failed");
      toast.error(t("toast.failed"), message);
    }
  };

  const canRun =
    selectedAgent && selectedSymbols.length > 0 && startDate && endDate && !isRunning;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
        <p className="text-muted-foreground">{t("subtitle")}</p>
      </div>

      <div className="space-y-6">
        {/* Configuration Panel */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <FlaskConical className="w-5 h-5 text-primary" />
              {t("configuration")}
            </CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4 items-end">
            {/* Exchange Selection */}
            <div className="space-y-2">
              <Label>{t("dataSource")}</Label>
              <Select
                value={selectedExchange}
                onValueChange={handleExchangeChange}
              >
                <SelectTrigger className="bg-muted/50">
                  <SelectValue placeholder={t("selectExchange")} />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGE_OPTIONS.map((ex) => (
                    <SelectItem key={ex.value} value={ex.value}>
                      <span className="flex items-center gap-2">
                        <span>{ex.icon}</span>
                        <span>{ex.label}</span>
                      </span>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Agent Selection */}
            <div className="space-y-2">
              <Label>{t("selectAgent")}</Label>
              <Select value={selectedAgent} onValueChange={setSelectedAgent}>
                <SelectTrigger className="bg-muted/50">
                  <SelectValue placeholder={t("selectAgentPlaceholder")} />
                </SelectTrigger>
                <SelectContent>
                  {(agents || []).map((agent) => (
                    <SelectItem key={agent.id} value={agent.id}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Trading Pairs (Multi-select) */}
            <div className="space-y-2 lg:col-span-2">
              <Label>{t("tradingPair")}</Label>
              <Popover open={pairOpen} onOpenChange={setPairOpen}>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    role="combobox"
                    aria-expanded={pairOpen}
                    className="w-full justify-between bg-muted/50 font-normal h-auto min-h-9"
                    disabled={isLoadingSymbols}
                  >
                    {isLoadingSymbols ? (
                      <span className="flex items-center gap-2 text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        {t("loadingPairs")}
                      </span>
                    ) : selectedSymbols.length > 0 ? (
                      <span className="flex flex-wrap gap-1">
                        {selectedSymbols.map((sym) => (
                          <Badge
                            key={sym}
                            variant="secondary"
                            className="text-xs px-1.5 py-0"
                          >
                            {sym}
                            <button
                              type="button"
                              className="ml-1 hover:text-foreground"
                              onClick={(e) => {
                                e.stopPropagation();
                                removeSymbol(sym);
                              }}
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </Badge>
                        ))}
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        {t("selectPair")}
                      </span>
                    )}
                    <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className="w-[--radix-popover-trigger-width] p-0"
                  align="start"
                >
                  <Command>
                    <CommandInput placeholder={t("searchPair")} />
                    <CommandList>
                      <CommandEmpty>{t("noMatch")}</CommandEmpty>
                      <CommandGroup>
                        {symbolsList.map((item) => (
                          <CommandItem
                            key={item.symbol}
                            value={item.full_symbol || item.symbol}
                            onSelect={() => toggleSymbol(item.symbol)}
                          >
                            <Check
                              className={cn(
                                "mr-2 h-4 w-4",
                                selectedSymbols.includes(item.symbol)
                                  ? "opacity-100"
                                  : "opacity-0"
                              )}
                            />
                            {item.full_symbol || item.symbol}
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </CommandList>
                  </Command>
                </PopoverContent>
              </Popover>
            </div>

            {/* Time Range */}
            <div className="space-y-2 lg:col-span-2">
              <Label>{t("timeRange")}</Label>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <Label className="text-xs text-muted-foreground">
                    {t("startDate")}
                  </Label>
                  <DatePicker
                    value={startDate}
                    onChange={setStartDate}
                    placeholder={t("startDate")}
                    toDate={endDate}
                  />
                </div>
                <div>
                  <Label className="text-xs text-muted-foreground">
                    {t("endDate")}
                  </Label>
                  <DatePicker
                    value={endDate}
                    onChange={setEndDate}
                    placeholder={t("endDate")}
                    fromDate={startDate}
                    toDate={new Date()}
                  />
                </div>
              </div>
            </div>

            {/* Initial Balance */}
            <div className="space-y-2">
              <Label>{t("initialBalance")}</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  $
                </span>
                <Input
                  type="number"
                  value={initialBalance}
                  onChange={(e) => setInitialBalance(e.target.value)}
                  className="bg-muted/50 pl-8"
                  min="100"
                />
              </div>
            </div>

            {/* Run Button */}
            <div className="flex items-end">
              <Button
                className="w-full glow-primary"
                onClick={handleRunBacktest}
                disabled={!canRun}
              >
                {isRunning ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {t("running")}
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    {t("runBacktest")}
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Results Panel */}
        <div>
          {results ? (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  {t("results")}
                </CardTitle>
                <CardDescription>
                  {results.strategy_name} &bull;{" "}
                  {selectedExchange.toUpperCase()} &bull; {startDate} ~{" "}
                  {endDate}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Tabs defaultValue="overview" className="w-full">
                  <TabsList className="w-full mb-4">
                    <TabsTrigger value="overview">
                      {t("tabs.overview")}
                    </TabsTrigger>
                    <TabsTrigger value="trade-analysis">
                      {t("tabs.tradeAnalysis")}
                    </TabsTrigger>
                    <TabsTrigger value="time-analysis">
                      {t("tabs.timeAnalysis")}
                    </TabsTrigger>
                    <TabsTrigger value="symbol-breakdown">
                      {t("tabs.symbolBreakdown")}
                    </TabsTrigger>
                    <TabsTrigger value="trade-list">
                      {t("tabs.tradeList")}
                    </TabsTrigger>
                  </TabsList>

                  <TabsContent value="overview">
                    <OverviewTab data={results} />
                  </TabsContent>
                  <TabsContent value="trade-analysis">
                    <TradeAnalysisTab data={results} />
                  </TabsContent>
                  <TabsContent value="time-analysis">
                    <TimeAnalysisTab data={results} />
                  </TabsContent>
                  <TabsContent value="symbol-breakdown">
                    <SymbolBreakdownTab data={results} />
                  </TabsContent>
                  <TabsContent value="trade-list">
                    <TradeListTab data={results} />
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          ) : (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-primary" />
                  {t("results")}
                </CardTitle>
                <CardDescription>{t("noResultsHint")}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <div className="p-4 rounded-full bg-muted/50 mb-4">
                    <FlaskConical className="w-8 h-8 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-semibold mb-2">
                    {t("noResults")}
                  </h3>
                  <p className="text-muted-foreground max-w-sm">
                    {t("noResultsHint")}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
