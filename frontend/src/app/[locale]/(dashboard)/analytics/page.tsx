"use client";

import { useState, useMemo } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  Wallet,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  RefreshCw,
  CloudDownload,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import {
  useAccounts,
  useAccountPnL,
  useEquityCurve,
  useAccountAgents,
  useSyncAccount,
} from "@/hooks";
import {
  EquityCurveTable,
  PnLSummaryCard,
  AgentPerformanceTable,
  TimeRangeSelector,
  TradeHistoryTable,
} from "@/components/analytics";
import type { TimeRange } from "@/components/analytics";

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export default function AnalyticsPage() {
  const t = useTranslations("analytics");
  const router = useRouter();
  const { success, error } = useToast();

  const [timeRange, setTimeRange] = useState<TimeRange>("30d");
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(
    null,
  );

  const {
    accounts,
    isLoading: isLoadingAccounts,
    refresh: refreshAccounts,
  } = useAccounts();

  // Auto-select first connected account
  const activeAccountId = useMemo(() => {
    if (selectedAccountId) return selectedAccountId;
    const connectedAccount = accounts.find((a) => a.is_connected);
    return connectedAccount?.id ?? null;
  }, [accounts, selectedAccountId]);

  const {
    data: accountPnL,
    isLoading: isLoadingPnL,
    mutate: mutatePnL,
  } = useAccountPnL(activeAccountId);
  const {
    dataPoints,
    isLoading: isLoadingCurve,
    mutate: mutateCurve,
  } = useEquityCurve(activeAccountId, {
    granularity: "day",
  });
  const {
    agents,
    isLoading: isLoadingAgents,
    mutate: mutateAgents,
  } = useAccountAgents(activeAccountId);

  const { sync: syncAccount, isSyncing } = useSyncAccount(activeAccountId);

  const isLoading =
    isLoadingAccounts || isLoadingPnL || isLoadingCurve || isLoadingAgents;

  // Sync real-time data from exchange
  const handleSync = async () => {
    if (!activeAccountId) return;

    const result = await syncAccount();
    if (result?.success) {
      success(t("sync.success"));
      // Refresh all data after sync
      mutatePnL();
      mutateCurve();
      mutateAgents();
    } else {
      error(t("sync.error"));
    }
  };

  // Calculate total equity across all accounts
  const totalEquity = useMemo(() => {
    // This would need to be calculated from account balances
    // For now, use accountPnL data if available
    return accountPnL?.current_equity ?? 0;
  }, [accountPnL]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isLoading || isSyncing || !activeAccountId}
          >
            <CloudDownload
              className={cn("w-4 h-4 mr-2", isSyncing && "animate-pulse")}
            />
            {t("sync.button")}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => refreshAccounts()}
            disabled={isLoading}
          >
            <RefreshCw className={cn("w-4 h-4", isLoading && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Account Selector */}
      {accounts.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-2">
          {accounts
            .filter((a) => a.is_connected)
            .map((account) => (
              <Button
                key={account.id}
                variant={activeAccountId === account.id ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedAccountId(account.id)}
              >
                <Wallet className="w-4 h-4 mr-2" />
                {account.name}
              </Button>
            ))}
        </div>
      )}

      {/* Loading State */}
      {isLoadingAccounts && accounts.length === 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      )}

      {/* No Connected Accounts */}
      {!isLoadingAccounts &&
        accounts.filter((a) => a.is_connected).length === 0 && (
          <Card className="bg-card/50">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Wallet className="w-12 h-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium mb-2">暂无已连接的账户</p>
              <p className="text-muted-foreground text-sm mb-4">
                请先连接一个交易所账户以查看收益分析
              </p>
              <Button onClick={() => router.push("/accounts/new")}>
                添加账户
              </Button>
            </CardContent>
          </Card>
        )}

      {/* Analytics Content */}
      {activeAccountId && (
        <>
          {/* P&L Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <PnLSummaryCard
              title={t("pnl.total")}
              value={accountPnL?.total_pnl ?? 0}
              percent={accountPnL?.total_pnl_percent}
              icon={<BarChart3 className="w-4 h-4" />}
            />
            <PnLSummaryCard
              title={t("pnl.daily")}
              value={accountPnL?.daily_pnl ?? 0}
              percent={accountPnL?.daily_pnl_percent}
              icon={<TrendingUp className="w-4 h-4" />}
            />
            <PnLSummaryCard
              title={t("pnl.weekly")}
              value={accountPnL?.weekly_pnl ?? 0}
              percent={accountPnL?.weekly_pnl_percent}
              icon={<Activity className="w-4 h-4" />}
            />
            <PnLSummaryCard
              title={t("pnl.monthly")}
              value={accountPnL?.monthly_pnl ?? 0}
              percent={accountPnL?.monthly_pnl_percent}
              icon={<TrendingDown className="w-4 h-4" />}
            />
          </div>

          {/* Metrics Grid */}
          {accountPnL && (
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <Card className="bg-card/50">
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground">
                    {t("metrics.winRate")}
                  </p>
                  <p className="text-xl font-bold font-mono">
                    {accountPnL.win_rate.toFixed(1)}%
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50">
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground">
                    {t("metrics.profitFactor")}
                  </p>
                  <p className="text-xl font-bold font-mono">
                    {accountPnL.profit_factor.toFixed(2)}
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50">
                <CardContent className="pt-4">
                  <p className="text-xs text-muted-foreground">
                    {t("metrics.totalTrades")}
                  </p>
                  <p className="text-xl font-bold font-mono">
                    {accountPnL.total_trades}
                  </p>
                </CardContent>
              </Card>
              {accountPnL.max_drawdown_percent !== null && (
                <Card className="bg-card/50">
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">
                      {t("metrics.maxDrawdown")}
                    </p>
                    <p className="text-xl font-bold font-mono text-[var(--loss)]">
                      -{accountPnL.max_drawdown_percent.toFixed(1)}%
                    </p>
                  </CardContent>
                </Card>
              )}
              {accountPnL.sharpe_ratio !== null && (
                <Card className="bg-card/50">
                  <CardContent className="pt-4">
                    <p className="text-xs text-muted-foreground">
                      {t("metrics.sharpeRatio")}
                    </p>
                    <p className="text-xl font-bold font-mono">
                      {accountPnL.sharpe_ratio.toFixed(2)}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          )}

          {/* Equity Curve */}
          <EquityCurveTable
            data={dataPoints}
            isLoading={isLoadingCurve}
            timeRange={timeRange}
            onTimeRangeChange={setTimeRange}
            pageSize={15}
          />

          {/* Agent Performance */}
          <Card className="bg-card/50">
            <CardHeader>
              <CardTitle className="text-lg">{t("agents.title")}</CardTitle>
            </CardHeader>
            <CardContent>
              <AgentPerformanceTable
                agents={agents}
                isLoading={isLoadingAgents}
                onRowClick={(agentId) => router.push(`/agents/${agentId}`)}
              />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
