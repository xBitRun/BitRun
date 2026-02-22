"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  Percent,
  BarChart3,
  DollarSign,
  Zap,
  Loader2,
  Trash2,
  AlertCircle,
  Trophy,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useBacktest, useDeleteBacktest } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { BacktestDetailResponse } from "@/lib/api";
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
        <p className={cn("text-xl font-bold font-mono truncate", valueColor)}>
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

const WEEKDAY_KEYS = [
  "sun",
  "mon",
  "tue",
  "wed",
  "thu",
  "fri",
  "sat",
] as const;

// ===================== Tab: Overview =====================

function OverviewTab({ data }: { data: BacktestDetailResponse }) {
  const t = useTranslations("backtest");
  const ts = data.trade_statistics;

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
            data.win_rate >= 50 ? "text-[var(--profit)]" : "text-[var(--loss)]"
          }
        />
        <MetricCard
          icon={BarChart3}
          label={t("metrics.profitFactor")}
          value={
            data.profit_factor === Infinity
              ? "∞"
              : data.profit_factor.toFixed(2)
          }
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
                config={
                  {
                    equity: {
                      label: t("charts.equity"),
                      color: "var(--primary)",
                    },
                    balance: {
                      label: t("charts.balance"),
                      color: "var(--muted-foreground)",
                    },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={equityData}>
                  <defs>
                    <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor="var(--color-equity)"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor="var(--color-equity)"
                        stopOpacity={0}
                      />
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
                  />
                  <ChartTooltip
                    content={
                      <ChartTooltipContent
                        labelFormatter={(v) =>
                          String(v).replace("T", " ").slice(0, 16)
                        }
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
                config={
                  {
                    drawdown_percent: {
                      label: t("charts.drawdown"),
                      color: "var(--loss, #ef4444)",
                    },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={drawdownData}>
                  <defs>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor="var(--color-drawdown_percent)"
                        stopOpacity={0.4}
                      />
                      <stop
                        offset="95%"
                        stopColor="var(--color-drawdown_percent)"
                        stopOpacity={0}
                      />
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
                        labelFormatter={(v) =>
                          String(v).replace("T", " ").slice(0, 16)
                        }
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

function TradeAnalysisTab({ data }: { data: BacktestDetailResponse }) {
  const t = useTranslations("backtest");
  const ts = data.trade_statistics;

  // P&L distribution histogram
  const pnlBins = useMemo(() => {
    if (!data.trades.length) return [];
    const pnls = data.trades.map((tr) => tr.pnl);
    const min = Math.min(...pnls);
    const max = Math.max(...pnls);
    const range = max - min || 1;
    const binCount = Math.min(
      20,
      Math.max(5, Math.ceil(data.trades.length / 3)),
    );
    const binSize = range / binCount;
    const bins: { range: string; count: number; isPositive: boolean }[] = [];
    for (let i = 0; i < binCount; i++) {
      const lo = min + i * binSize;
      const hi = lo + binSize;
      const count = pnls.filter(
        (p) => p >= lo && (i === binCount - 1 ? p <= hi : p < hi),
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
                config={
                  {
                    count: {
                      label: t("charts.tradeCount"),
                      color: "var(--primary)",
                    },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlBins}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="range"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                  />
                  <ChartTooltip content={<ChartTooltipContent />} />
                  <ReferenceLine
                    x="0"
                    stroke="var(--muted-foreground)"
                    strokeDasharray="3 3"
                  />
                  <Bar
                    dataKey="count"
                    name={t("charts.tradeCount")}
                    radius={[4, 4, 0, 0]}
                  >
                    {pnlBins.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={
                          entry.isPositive
                            ? "var(--profit, #22c55e)"
                            : "var(--loss, #ef4444)"
                        }
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
                config={
                  {
                    count: {
                      label: t("tradeAnalysis.trades"),
                      color: "var(--primary)",
                    },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={holdingDist}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                  />
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
                    <span className="text-muted-foreground">
                      {t("metrics.totalTrades")}
                    </span>
                    <span className="font-mono">
                      {longStats?.total_trades ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("metrics.winRate")}
                    </span>
                    <span className="font-mono">
                      {(longStats?.win_rate ?? 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("charts.pnl")}
                    </span>
                    <span
                      className={cn(
                        "font-mono",
                        (longStats?.total_pnl ?? 0) >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]",
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
                    <span className="text-muted-foreground">
                      {t("metrics.totalTrades")}
                    </span>
                    <span className="font-mono">
                      {shortStats?.total_trades ?? 0}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("metrics.winRate")}
                    </span>
                    <span className="font-mono">
                      {(shortStats?.win_rate ?? 0).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">
                      {t("charts.pnl")}
                    </span>
                    <span
                      className={cn(
                        "font-mono",
                        (shortStats?.total_pnl ?? 0) >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]",
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
                <span className="text-muted-foreground">
                  {t("metrics.maxConsecutiveWins")}
                </span>
                <span className="font-mono text-[var(--profit)]">
                  {ts?.max_consecutive_wins ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.maxConsecutiveLosses")}
                </span>
                <span className="font-mono text-[var(--loss)]">
                  {ts?.max_consecutive_losses ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.avgHoldingHours")}
                </span>
                <span className="font-mono">
                  {(ts?.avg_holding_hours ?? 0).toFixed(1)}h
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.largestWin")}
                </span>
                <span className="font-mono text-[var(--profit)]">
                  ${(ts?.largest_win ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.largestLoss")}
                </span>
                <span className="font-mono text-[var(--loss)]">
                  ${(ts?.largest_loss ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.averageWin")}
                </span>
                <span className="font-mono">
                  ${(ts?.average_win ?? 0).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">
                  {t("metrics.averageLoss")}
                </span>
                <span className="font-mono">
                  ${(ts?.average_loss ?? 0).toFixed(2)}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ===================== Tab: Time Analysis =====================

function TimeAnalysisTab({ data }: { data: BacktestDetailResponse }) {
  const t = useTranslations("backtest");

  const monthlyData = useMemo(() => {
    const raw = data.monthly_returns || [];

    // 从 end_date 提取结束月份，生成前 6 个月的月份列表
    const endMonth = data.end_date?.slice(0, 7); // "YYYY-MM"
    if (!endMonth) {
      return raw.map((m) => ({ ...m, isPositive: m.return_percent >= 0 }));
    }

    const [endY, endM] = endMonth.split("-").map(Number);
    const months: string[] = [];
    for (let i = 5; i >= 0; i--) {
      const d = new Date(endY, endM - 1 - i, 1);
      months.push(
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
      );
    }

    // 如果原始数据有比 6 个月范围更早的月份，前面追加
    const rawMap = new Map(raw.map((m) => [m.month, m]));
    const earliest = months[0];
    const earlier = raw.filter((m) => m.month < earliest).map((m) => m.month);
    const allMonths = [...earlier, ...months];

    return allMonths.map((month) => {
      const found = rawMap.get(month);
      return {
        month,
        return_percent: found?.return_percent ?? 0,
        isPositive: (found?.return_percent ?? 0) >= 0,
      };
    });
  }, [data.monthly_returns, data.end_date]);

  // Cumulative returns
  const cumulativeData = useMemo(() => {
    return monthlyData.reduce<Array<{ month: string; cumulative: number }>>(
      (acc, m) => {
        const prev = acc.length > 0 ? acc[acc.length - 1].cumulative : 0;
        const cumulative = parseFloat((prev + m.return_percent).toFixed(2));
        return [...acc, { month: m.month, cumulative }];
      },
      []
    );
  }, [monthlyData]);

  // P&L by day of week (computed from trades)
  const pnlByWeekday = useMemo(() => {
    const buckets = WEEKDAY_KEYS.map(() => 0);
    for (const trade of data.trades) {
      if (!trade.opened_at) continue;
      const day = new Date(trade.opened_at).getDay(); // 0=Sun..6=Sat
      buckets[day] += trade.pnl;
    }
    return WEEKDAY_KEYS.map((key, i) => ({
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
                config={
                  {
                    return_percent: {
                      label: t("charts.returnPercent"),
                      color: "var(--primary)",
                    },
                  } satisfies ChartConfig
                }
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
                  <ReferenceLine
                    y={0}
                    stroke="var(--muted-foreground)"
                    strokeDasharray="3 3"
                  />
                  <Bar
                    dataKey="return_percent"
                    name={t("charts.returnPercent")}
                    radius={[4, 4, 0, 0]}
                  >
                    {monthlyData.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={
                          entry.isPositive
                            ? "var(--profit, #22c55e)"
                            : "var(--loss, #ef4444)"
                        }
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
                config={
                  {
                    cumulative: {
                      label: t("charts.cumulativeReturn"),
                      color: "var(--primary)",
                    },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <AreaChart accessibilityLayer data={cumulativeData}>
                  <defs>
                    <linearGradient id="cumGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop
                        offset="5%"
                        stopColor="var(--color-cumulative)"
                        stopOpacity={0.3}
                      />
                      <stop
                        offset="95%"
                        stopColor="var(--color-cumulative)"
                        stopOpacity={0}
                      />
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
                  <ReferenceLine
                    y={0}
                    stroke="var(--muted-foreground)"
                    strokeDasharray="3 3"
                  />
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
                config={
                  {
                    pnl: { label: t("charts.pnl"), color: "var(--primary)" },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlByWeekday}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => `$${v}`}
                  />
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
                  <ReferenceLine
                    y={0}
                    stroke="var(--muted-foreground)"
                    strokeDasharray="3 3"
                  />
                  <Bar
                    dataKey="pnl"
                    name={t("charts.pnl")}
                    radius={[4, 4, 0, 0]}
                  >
                    {pnlByWeekday.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={
                          entry.isPositive
                            ? "var(--profit, #22c55e)"
                            : "var(--loss, #ef4444)"
                        }
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
                config={
                  {
                    pnl: { label: t("charts.pnl"), color: "var(--primary)" },
                  } satisfies ChartConfig
                }
                className="min-h-[250px] w-full"
              >
                <BarChart accessibilityLayer data={pnlByHour}>
                  <CartesianGrid vertical={false} />
                  <XAxis
                    dataKey="name"
                    tickLine={false}
                    axisLine={false}
                    tickMargin={8}
                    tick={{ fontSize: 10 }}
                    interval={2}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fontSize: 10 }}
                    tickFormatter={(v) => `$${v}`}
                  />
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
                  <ReferenceLine
                    y={0}
                    stroke="var(--muted-foreground)"
                    strokeDasharray="3 3"
                  />
                  <Bar
                    dataKey="pnl"
                    name={t("charts.pnl")}
                    radius={[4, 4, 0, 0]}
                  >
                    {pnlByHour.map((entry, index) => (
                      <Cell
                        key={index}
                        fill={
                          entry.isPositive
                            ? "var(--profit, #22c55e)"
                            : "var(--loss, #ef4444)"
                        }
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
                            : "text-[var(--loss)]",
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

function SymbolBreakdownTab({ data }: { data: BacktestDetailResponse }) {
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
              config={
                {
                  total_pnl: {
                    label: t("charts.pnl"),
                    color: "var(--primary)",
                  },
                } satisfies ChartConfig
              }
              className="min-h-[250px] w-full"
            >
              <BarChart accessibilityLayer data={sb}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="symbol"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tick={{ fontSize: 10 }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `$${v}`}
                />
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
                <ReferenceLine
                  y={0}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="3 3"
                />
                <Bar
                  dataKey="total_pnl"
                  name={t("charts.pnl")}
                  radius={[4, 4, 0, 0]}
                >
                  {sb.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        entry.total_pnl >= 0
                          ? "var(--profit, #22c55e)"
                          : "var(--loss, #ef4444)"
                      }
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
              config={
                {
                  win_rate: {
                    label: t("symbolBreakdown.winRate"),
                    color: "var(--primary)",
                  },
                } satisfies ChartConfig
              }
              className="min-h-[250px] w-full"
            >
              <BarChart accessibilityLayer data={sb}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="symbol"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tick={{ fontSize: 10 }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `${v}%`}
                  domain={[0, 100]}
                />
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
                <ReferenceLine
                  y={50}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="3 3"
                />
                <Bar
                  dataKey="win_rate"
                  name={t("symbolBreakdown.winRate")}
                  radius={[4, 4, 0, 0]}
                >
                  {sb.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={
                        entry.win_rate >= 50
                          ? "var(--profit, #22c55e)"
                          : "var(--loss, #ef4444)"
                      }
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
                    <td className="py-2 px-3 font-mono font-medium">
                      {s.symbol}
                    </td>
                    <td className="py-2 px-3 text-right font-mono">
                      {s.total_trades}
                    </td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.win_rate >= 50
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]",
                      )}
                    >
                      {s.win_rate.toFixed(1)}%
                    </td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.total_pnl >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]",
                      )}
                    >
                      ${s.total_pnl.toFixed(2)}
                    </td>
                    <td
                      className={cn(
                        "py-2 px-3 text-right font-mono",
                        s.average_pnl >= 0
                          ? "text-[var(--profit)]"
                          : "text-[var(--loss)]",
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

// ===================== Tab: Analysis =====================

function AnalysisTab({
  data,
}: {
  data: {
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
  };
}) {
  const t = useTranslations("backtest");

  return (
    <div className="space-y-6">
      {/* Strengths */}
      {data.strengths.length > 0 && (
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Trophy className="w-4 h-4 text-[var(--profit)]" />
              {t("analysis.strengths")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.strengths.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-[var(--profit)] mt-0.5">✓</span>
                  <span className="text-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Weaknesses */}
      {data.weaknesses.length > 0 && (
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <TrendingDown className="w-4 h-4 text-[var(--loss)]" />
              {t("analysis.weaknesses")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.weaknesses.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-[var(--loss)] mt-0.5">⚠</span>
                  <span className="text-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      {data.recommendations.length > 0 && (
        <Card className="bg-card/50 border-border/50">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Target className="w-4 h-4 text-primary" />
              {t("analysis.recommendations")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {data.recommendations.map((item, idx) => (
                <li key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-primary mt-0.5">→</span>
                  <span className="text-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ===================== Tab: Trade List =====================

function TradeListTab({ data }: { data: BacktestDetailResponse }) {
  const t = useTranslations("backtest");

  if (!data.trades.length) {
    return (
      <Card className="bg-card/50 border-border/50">
        <CardContent className="py-12 text-center text-muted-foreground">
          {t("tradeList.noTrades")}
        </CardContent>
      </Card>
    );
  }

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

  const isLimited = data.total_trades > data.trades.length;

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="pt-4">
        {isLimited && (
          <div className="mb-4 p-3 bg-muted/50 border border-border/50 rounded-md text-sm text-muted-foreground">
            {t("tradeList.limited", {
              count: data.trades.length,
              total: data.total_trades,
            })}
          </div>
        )}
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50">
                <th className="py-2 px-2 text-left text-muted-foreground font-medium">
                  {t("tradeList.symbol")}
                </th>
                <th className="py-2 px-2 text-left text-muted-foreground font-medium">
                  {t("tradeList.side")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.leverage")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.entryPrice")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.exitPrice")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.pnl")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.pnlPercent")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.duration")}
                </th>
                <th className="py-2 px-2 text-left text-muted-foreground font-medium">
                  {t("tradeList.exitReason")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.closeTime")}
                </th>
              </tr>
            </thead>
            <tbody>
              {data.trades.map((trade, i) => (
                <tr
                  key={i}
                  className={cn(
                    "border-b border-border/10 hover:bg-muted/30 transition-colors",
                    trade.pnl > 0
                      ? "bg-[var(--profit)]/[0.03]"
                      : trade.pnl < 0
                        ? "bg-[var(--loss)]/[0.03]"
                        : "",
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
                          : "bg-[var(--loss)]/10 text-[var(--loss)]",
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
                        : "text-[var(--loss)]",
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
                        : "text-[var(--loss)]",
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
                            : "bg-muted text-muted-foreground",
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

export default function BacktestDetailPage() {
  const t = useTranslations("backtest");
  const params = useParams();
  const router = useRouter();
  const toast = useToast();
  const id = params.id as string;

  const { data: backtest, isLoading, error } = useBacktest(id);
  const { trigger: deleteBacktest, isMutating: isDeleting } = useDeleteBacktest();

  const [deleteConfirm, setDeleteConfirm] = useState(false);

  const handleDelete = () => {
    setDeleteConfirm(true);
  };

  const confirmDelete = async () => {
    try {
      await deleteBacktest(id);
      toast.success(t("detail.deleteSuccess"));
      router.push("/backtest");
    } catch (error) {
      const message = error instanceof Error ? error.message : t("detail.deleteFailed");
      toast.error(t("detail.deleteFailed"), message);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !backtest) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
        <AlertCircle className="w-12 h-12 text-muted-foreground" />
        <p className="text-muted-foreground">{t("detail.notFound")}</p>
        <Button asChild>
          <Link href="/backtest">{t("detail.backToList")}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild>
            <Link href="/backtest">
              <ArrowLeft className="w-5 h-5" />
            </Link>
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gradient">
              {backtest.strategy_name}
            </h1>
            <p className="text-muted-foreground text-sm">
              {backtest.start_date?.slice(0, 10)} - {backtest.end_date?.slice(0, 10)} •{" "}
              {backtest.exchange} • {backtest.timeframe}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="text-destructive"
            onClick={handleDelete}
            disabled={isDeleting}
          >
            <Trash2 className="w-4 h-4 mr-1" />
            {t("detail.delete")}
          </Button>
        </div>
      </div>

      {/* Results Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="mb-4 flex-wrap h-auto gap-1">
          <TabsTrigger value="overview">{t("tabs.overview")}</TabsTrigger>
          <TabsTrigger value="trade-analysis">{t("tabs.tradeAnalysis")}</TabsTrigger>
          <TabsTrigger value="time-analysis">{t("tabs.timeAnalysis")}</TabsTrigger>
          <TabsTrigger value="symbol-breakdown">{t("tabs.symbolBreakdown")}</TabsTrigger>
          {backtest.analysis && (
            <TabsTrigger value="analysis">{t("tabs.analysis")}</TabsTrigger>
          )}
          <TabsTrigger value="trades">
            {t("tabs.trades")} ({backtest.total_trades})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab data={backtest} />
        </TabsContent>

        <TabsContent value="trade-analysis">
          <TradeAnalysisTab data={backtest} />
        </TabsContent>

        <TabsContent value="time-analysis">
          <TimeAnalysisTab data={backtest} />
        </TabsContent>

        <TabsContent value="symbol-breakdown">
          <SymbolBreakdownTab data={backtest} />
        </TabsContent>

        {backtest.analysis && (
          <TabsContent value="analysis">
            <AnalysisTab data={backtest.analysis} />
          </TabsContent>
        )}

        <TabsContent value="trades">
          <TradeListTab data={backtest} />
        </TabsContent>
      </Tabs>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirm}
        onOpenChange={setDeleteConfirm}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("detail.deleteConfirm.title")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("detail.deleteConfirm.description")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("detail.deleteConfirm.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className="bg-destructive hover:bg-destructive/90"
            >
              {isDeleting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {t("detail.deleteConfirm.confirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
