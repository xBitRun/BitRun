"use client";

import { useMemo } from "react";
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
} from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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

      {/* Equity Curve */}
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
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 10 }} />
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
                <Area
                  type="monotone"
                  dataKey="equity"
                  stroke="var(--color-equity)"
                  fill="url(#eqGrad)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ChartContainer>
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

  return (
    <Card className="bg-card/50 border-border/50">
      <CardContent className="pt-4">
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
                  {t("tradeList.pnl")}
                </th>
                <th className="py-2 px-2 text-right text-muted-foreground font-medium">
                  {t("tradeList.pnlPercent")}
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
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px] font-mono",
                        trade.side === "long"
                          ? "text-[var(--profit)] border-[var(--profit)]/50"
                          : "text-[var(--loss)] border-[var(--loss)]/50",
                      )}
                    >
                      {trade.side.toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-1.5 px-2 text-right font-mono">
                    {trade.leverage}x
                  </td>
                  <td
                    className={cn(
                      "py-1.5 px-2 text-right font-mono",
                      trade.pnl >= 0 ? "text-[var(--profit)]" : "text-[var(--loss)]",
                    )}
                  >
                    {trade.pnl >= 0 ? "+" : ""}${trade.pnl.toFixed(2)}
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
                  <td className="py-1.5 px-2">
                    <Badge
                      variant="outline"
                      className={cn(
                        "text-[10px]",
                        trade.exit_reason === "take_profit"
                          ? "bg-[var(--profit)]/10 text-[var(--profit)]"
                          : trade.exit_reason === "stop_loss"
                            ? "bg-[var(--loss)]/10 text-[var(--loss)]"
                            : "bg-muted text-muted-foreground",
                      )}
                    >
                      {trade.exit_reason}
                    </Badge>
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

  const handleDelete = async () => {
    if (!confirm(t("detail.confirmDelete"))) return;

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
        <TabsList className="mb-4">
          <TabsTrigger value="overview">{t("tabs.overview")}</TabsTrigger>
          <TabsTrigger value="trades">
            {t("tabs.trades")} ({backtest.total_trades})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <OverviewTab data={backtest} />
        </TabsContent>

        <TabsContent value="trades">
          <TradeListTab data={backtest} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
