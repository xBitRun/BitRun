"use client";

import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Wallet,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  RefreshCw,
  Bot,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import {
  useWebSocket,
  useDashboardStats,
  useAccounts,
  useActivityFeed,
} from "@/hooks";
import type { AccountSummary, Position } from "@/hooks";
import { useEffect, useState, useMemo } from "react";
import type { ActivityItem } from "@/lib/api";
import { PnLValue, formatPnL, formatPnLPercent } from "@/components/pnl";

function formatTimeAgo(
  dateString: string,
  t: ReturnType<typeof useTranslations<"time">>,
): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return t("justNow");
  if (diffMins < 60) return t("m_ago", { count: diffMins });

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return t("h_ago", { count: diffHours });

  const diffDays = Math.floor(diffHours / 24);
  return t("d_ago", { count: diffDays });
}

// ==================== Skeleton Components ====================

function AccountsOverviewSkeleton() {
  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <Skeleton className="h-6 w-28" />
          <Skeleton className="h-5 w-16" />
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex gap-4 overflow-x-auto pb-2">
          {[...Array(3)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-52 flex-shrink-0 rounded-lg" />
          ))}
        </div>
        <div className="mt-4 pt-4 border-t border-border/50">
          <Skeleton className="h-5 w-96 mx-auto" />
        </div>
      </CardContent>
    </Card>
  );
}

function OperationalCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {[...Array(3)].map((_, i) => (
        <Card key={i} className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <Skeleton className="h-5 w-16" />
            </div>
            <div className="mt-4 space-y-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-4 w-20" />
            </div>
            <div className="mt-3 pt-3 border-t border-border/30 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ActivityFeedSkeleton() {
  return (
    <div className="space-y-3">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className="flex items-start gap-3 p-3 rounded-lg bg-muted/30"
        >
          <Skeleton className="w-8 h-8 rounded-full flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <Skeleton className="h-2 w-2 rounded-full" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-12" />
            </div>
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-16" />
          </div>
          <Skeleton className="h-5 w-8" />
        </div>
      ))}
    </div>
  );
}

function PositionsSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(2)].map((_, i) => (
        <div key={i} className="space-y-2">
          <Skeleton className="h-10 w-full rounded-lg" />
          <div className="pl-4 space-y-2">
            {[...Array(2)].map((_, j) => (
              <Skeleton key={j} className="h-28 w-full rounded-lg" />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ==================== Account Overview Section ====================

function AccountsOverviewSection({
  accounts,
  isLoading,
}: {
  accounts: AccountSummary[];
  isLoading: boolean;
}) {
  const t = useTranslations("dashboard.accountsOverview");

  // Calculate totals
  const totals = useMemo(() => {
    const onlineAccounts = accounts.filter((a) => a.status === "online");
    return {
      totalEquity: onlineAccounts.reduce((sum, a) => sum + a.totalEquity, 0),
      totalAvailable: onlineAccounts.reduce(
        (sum, a) => sum + a.availableBalance,
        0,
      ),
      dailyPnl: onlineAccounts.reduce((sum, a) => sum + a.dailyPnl, 0),
    };
  }, [accounts]);

  if (isLoading) {
    return <AccountsOverviewSkeleton />;
  }

  if (accounts.length === 0) {
    return (
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Wallet className="w-5 h-5 text-primary" />
              {t("title")}
            </CardTitle>
            <Link
              href="/accounts"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              {t("viewAll")}
              <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6 text-muted-foreground">
            <p>{t("noAccounts")}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Wallet className="w-5 h-5 text-primary" />
            {t("title")}
          </CardTitle>
          <Link
            href="/accounts"
            className="text-sm text-primary hover:underline flex items-center gap-1"
          >
            {t("viewAll")}
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {/* Account cards - horizontal scroll */}
        <div className="flex gap-4 overflow-x-auto pb-2 -mx-2 px-2">
          {accounts.map((account) => (
            <AccountCard key={account.accountId} account={account} t={t} />
          ))}
        </div>

        {/* Totals summary */}
        <div className="mt-4 pt-4 border-t border-border/50 flex items-center justify-between text-sm">
          <span className="text-muted-foreground">{t("total")}:</span>
          <div className="flex items-center gap-4 flex-wrap">
            <span>
              <span className="text-muted-foreground">
                {t("totalEquity")}:{" "}
              </span>
              <span className="font-semibold">
                {formatPnL(totals.totalEquity, false)}
              </span>
            </span>
            <span>
              <span className="text-muted-foreground">{t("available")}: </span>
              <span className="font-semibold">
                {formatPnL(totals.totalAvailable, false)}
              </span>
            </span>
            <span className="flex items-center gap-1">
              <span className="text-muted-foreground">{t("todayPL")}: </span>
              <PnLValue value={totals.dailyPnl} size="sm" weight="semibold" />
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AccountCard({
  account,
  t,
}: {
  account: AccountSummary;
  t: ReturnType<typeof useTranslations<"dashboard.accountsOverview">>;
}) {
  const isOnline = account.status === "online";

  return (
    <div
      className={cn(
        "flex-shrink-0 w-52 p-4 rounded-lg border transition-colors",
        isOnline
          ? "bg-muted/30 border-border/30 hover:bg-muted/50"
          : "bg-muted/20 border-border/20 opacity-60",
      )}
    >
      {/* Header: Status + Name */}
      <div className="flex items-center gap-2 mb-3">
        <div
          className={cn(
            "w-2 h-2 rounded-full",
            isOnline ? "bg-green-500" : "bg-red-500",
          )}
        />
        <span className="font-medium text-sm truncate">
          {account.accountName}
        </span>
      </div>

      {/* Exchange */}
      <div className="text-xs text-muted-foreground mb-2">
        {account.exchange}
      </div>

      {isOnline ? (
        <>
          {/* Total Equity */}
          <div className="text-lg font-bold">
            {formatPnL(account.totalEquity, false)}
          </div>

          {/* Available */}
          <div className="text-sm text-muted-foreground">
            {t("available")}: {formatPnL(account.availableBalance, false)}
          </div>

          {/* Daily P/L */}
          <div className="text-sm mt-1">
            <span className="text-muted-foreground">{t("todayPL")}: </span>
            <PnLValue value={account.dailyPnl} size="sm" />
          </div>
        </>
      ) : (
        <div className="text-sm text-red-500 flex items-center gap-1">
          <AlertTriangle className="w-4 h-4" />
          {t("offline")}
        </div>
      )}
    </div>
  );
}

// ==================== Operational Cards ====================

function OperationalCardsSection({
  stats,
  isLoading,
}: {
  stats: ReturnType<typeof useDashboardStats>["data"];
  isLoading: boolean;
}) {
  const t = useTranslations("dashboard.stats");

  if (isLoading || !stats) {
    return <OperationalCardsSkeleton />;
  }

  const cards = [
    {
      // P/L Trend Card
      titleKey: "plTrend",
      icon: stats.dailyPnl >= 0 ? TrendingUp : TrendingDown,
      mainValue: formatPnL(stats.dailyPnl),
      mainLabel: t("dailyPL"),
      trend: stats.dailyPnl >= 0 ? "up" : "down",
      subItems: [
        { label: t("weeklyPL"), value: formatPnL(stats.weeklyPnl) },
        {
          label: t("monthlyPL"),
          value: formatPnL(stats.monthlyPnl),
        },
      ],
    },
    {
      // Agents Status Card
      titleKey: "agentsStatus",
      icon: Zap,
      mainValue: `${stats.activeStrategies}/${stats.totalStrategies}`,
      mainLabel: t("running"),
      trend: "neutral",
      subItems: [
        {
          label: t("decisions"),
          value: String(stats.todayDecisions),
        },
      ],
    },
    {
      // Today's Activity Card
      titleKey: "todayActivity",
      icon: Activity,
      mainValue: `${stats.todayExecutedDecisions}/${stats.todayDecisions}`,
      mainLabel: t("trades"),
      trend: "neutral",
      subItems: [
        {
          label: t("executionRate"),
          value:
            stats.todayDecisions > 0
              ? `${Math.round((stats.todayExecutedDecisions / stats.todayDecisions) * 100)}%`
              : "0%",
        },
      ],
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 shrink-0">
      {cards.map((card) => (
        <Card
          key={card.titleKey}
          className="bg-card/50 backdrop-blur-sm border-border/50"
        >
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="p-2 rounded-lg bg-primary/10">
                <card.icon
                  className={cn(
                    "w-5 h-5",
                    card.trend === "up"
                      ? "text-[var(--profit)]"
                      : card.trend === "down"
                        ? "text-[var(--loss)]"
                        : "text-primary",
                  )}
                />
              </div>
              {card.trend !== "neutral" && (
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    card.trend === "up"
                      ? "text-[var(--profit)] border-[var(--profit)]/30"
                      : "text-[var(--loss)] border-[var(--loss)]/30",
                  )}
                >
                  {card.trend === "up" ? (
                    <ArrowUpRight className="w-3 h-3 mr-1" />
                  ) : (
                    <ArrowDownRight className="w-3 h-3 mr-1" />
                  )}
                  {formatPnLPercent(stats.dailyPnlPercent)}
                </Badge>
              )}
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold">{card.mainValue}</p>
              <p className="text-sm text-muted-foreground">{card.mainLabel}</p>
            </div>
            <div className="mt-3 pt-3 border-t border-border/30 space-y-1">
              {card.subItems.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-muted-foreground">{item.label}</span>
                  <span className="font-mono">{item.value}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== Positions Grouped by Agent ====================

interface AgentGroup {
  agentId: string;
  agentName: string;
  executionMode: "mock" | "live" | "unknown";
  positions: Position[];
}

function PositionsGroupedByAgent({
  positions,
  isLoading,
  tPositions,
}: {
  positions: Position[];
  isLoading: boolean;
  tPositions: ReturnType<typeof useTranslations<"dashboard.positions">>;
}) {
  const [expandedAgents, setExpandedAgents] = useState<Set<string>>(new Set());

  // Group positions by Agent
  const positionsByAgent = useMemo(() => {
    const grouped = new Map<string, AgentGroup>();

    for (const position of positions) {
      // Use agentId if available, otherwise fall back to accountId
      const groupId = position.agentId || position.accountId || "unknown";
      const groupName = position.agentName || position.accountName || "Unknown";
      const executionMode =
        position.executionMode ||
        (position.exchange === "mock" ? "mock" : "live");

      const existing = grouped.get(groupId);
      if (existing) {
        existing.positions.push(position);
      } else {
        grouped.set(groupId, {
          agentId: groupId,
          agentName: groupName,
          executionMode: executionMode as "mock" | "live" | "unknown",
          positions: [position],
        });
      }
    }

    // Convert to array and sort: live agents first, then mock
    return Array.from(grouped.values()).sort((a, b) => {
      if (a.executionMode === "live" && b.executionMode !== "live") return -1;
      if (a.executionMode !== "live" && b.executionMode === "live") return 1;
      return a.agentName.localeCompare(b.agentName);
    });
  }, [positions]);

  const toggleAgent = (agentId: string) => {
    setExpandedAgents((prev) => {
      const next = new Set(prev);
      if (next.has(agentId)) {
        next.delete(agentId);
      } else {
        next.add(agentId);
      }
      return next;
    });
  };

  if (isLoading) {
    return <PositionsSkeleton />;
  }

  if (positionsByAgent.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>{tPositions("empty")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {positionsByAgent.map((group) => {
        const isExpanded =
          expandedAgents.has(group.agentId) || expandedAgents.size === 0;
        const isMock = group.executionMode === "mock";

        return (
          <div key={group.agentId} className="space-y-2">
            {/* Agent Header */}
            <button
              onClick={() => toggleAgent(group.agentId)}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2 flex-wrap">
                <div
                  className={cn(
                    "w-2 h-2 rounded-full",
                    isMock ? "bg-orange-500" : "bg-green-500",
                  )}
                />
                <span className="font-medium text-sm">{group.agentName}</span>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    isMock
                      ? "bg-orange-500/10 text-orange-500 border-orange-500/30"
                      : "bg-green-500/10 text-green-500 border-green-500/30",
                  )}
                >
                  {isMock ? "Mock" : "Live"}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {tPositions("positionsCount", {
                    count: group.positions.length,
                  })}
                </Badge>
              </div>
              {isExpanded ? (
                <ChevronUp className="w-4 h-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="w-4 h-4 text-muted-foreground" />
              )}
            </button>

            {/* Positions List */}
            {isExpanded && (
              <div className="space-y-2 pl-4">
                {group.positions.map((position, index) => (
                  <div
                    key={`${position.agentId || position.accountId}-${position.symbol}-${index}`}
                    className="p-4 rounded-lg bg-muted/20 border border-border/30"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="font-bold">{position.symbol}</span>
                        <Badge
                          variant={
                            position.side === "long" ? "default" : "secondary"
                          }
                          className="text-xs"
                        >
                          {tPositions(position.side)}
                        </Badge>
                      </div>
                      <PnLValue
                        value={position.unrealizedPnl}
                        percent={position.unrealizedPnlPercent}
                        mode="percent"
                        weight="semibold"
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions("sizeValue")}
                        </span>
                        <p className="font-mono">
                          ${position.sizeUsd.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions("sizeQty")}
                        </span>
                        <p className="font-mono">{position.size}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions("entry")}
                        </span>
                        <p className="font-mono">
                          ${position.entryPrice.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions("pnl")}
                        </span>
                        <PnLValue
                          value={position.unrealizedPnl}
                          size="sm"
                          className="mt-0.5"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ==================== Main Page ====================

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const tPositions = useTranslations("dashboard.positions");
  const tTime = useTranslations("time");

  // Data fetching - using aggregated hooks
  const {
    data: stats,
    positions,
    isLoading: statsLoading,
    mutate: refreshStats,
  } = useDashboardStats();
  const { isLoading: accountsLoading } = useAccounts();

  // Real-time updates via WebSocket
  const { isConnected, subscribe } = useWebSocket({
    onPositionUpdate: () => {
      refreshStats();
    },
  });

  // Subscribe to user notifications
  useEffect(() => {
    subscribe("system");
  }, [subscribe]);

  const isLoading = statsLoading || accountsLoading;

  return (
    <div className="flex flex-col gap-6 min-h-[calc(100vh-6rem)] md:min-h-[calc(100vh-7rem)]">
      {/* Page Header */}
      <div className="flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">
            {t("subtitle")}
            {isConnected && (
              <span className="ml-2 inline-flex items-center">
                <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-1" />
                <span className="text-xs text-green-500">{tTime("live")}</span>
              </span>
            )}
          </p>
        </div>
        <Link href="/agents">
          <Button className="glow-primary">
            <Bot className="w-4 h-4 mr-2" />
            {t("newAgent")}
          </Button>
        </Link>
      </div>

      {/* Accounts Overview Section */}
      <AccountsOverviewSection
        accounts={stats?.accounts ?? []}
        isLoading={isLoading}
      />

      {/* Operational Cards (3 cards) */}
      <OperationalCardsSection stats={stats} isLoading={isLoading} />

      {/* Main Content Grid - Activity Feed & Positions side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
        {/* Activity Feed - Left */}
        <ActivityFeed t={t} tTime={tTime} isLoading={isLoading} />

        {/* Open Positions - Right (Grouped by Account) */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50 flex flex-col min-h-0">
          <CardHeader className="flex flex-row items-center justify-between pb-4">
            <CardTitle className="text-lg font-semibold">
              {tPositions("title")}
            </CardTitle>
            <Badge variant="outline" className="text-muted-foreground">
              {positions?.length ?? 0} {tPositions("active")}
            </Badge>
          </CardHeader>
          <CardContent className="flex-1 overflow-y-auto">
            <PositionsGroupedByAgent
              positions={positions ?? []}
              isLoading={statsLoading}
              tPositions={tPositions}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ==================== Activity Feed Component ====================

function ActivityFeed({
  t,
  tTime,
  isLoading: parentLoading,
  className,
}: {
  t: ReturnType<typeof useTranslations>;
  tTime: ReturnType<typeof useTranslations<"time">>;
  isLoading: boolean;
  className?: string;
}) {
  const { data: activityData, isLoading, mutate } = useActivityFeed(5);

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case "success":
        return <div className="w-2 h-2 rounded-full bg-[var(--profit)]" />;
      case "error":
        return <div className="w-2 h-2 rounded-full bg-[var(--loss)]" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-primary" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case "decision":
        return <Bot className="w-4 h-4 text-primary" />;
      case "trade":
        return <TrendingUp className="w-4 h-4 text-[var(--profit)]" />;
      default:
        return <Activity className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <Card
      className={cn(
        "bg-card/50 backdrop-blur-sm border-border/50 flex flex-col",
        className,
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          {t("activity.title")}
        </CardTitle>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => mutate()}
          className="h-8 w-8"
        >
          <RefreshCw className="w-4 h-4" />
        </Button>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {isLoading || parentLoading ? (
          <ActivityFeedSkeleton />
        ) : activityData && activityData.items.length > 0 ? (
          <div className="space-y-3">
            {activityData.items.map((item: ActivityItem) => {
              const agentId = (item.data?.agent_id ||
                item.data?.strategy_id) as string | undefined;
              const isClickable = !!agentId;
              const executionMode = item.data?.execution_mode as
                | string
                | undefined;
              const isLive = executionMode === "live";

              const content = (
                <>
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 flex-shrink-0">
                    {getTypeIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getStatusIcon(item.status)}
                      <span className="font-medium text-sm truncate">
                        {item.title.includes(": ")
                          ? item.title.split(": ")[0]
                          : item.title}
                      </span>
                      {item.title.includes(": ") && (
                        <Badge
                          variant="outline"
                          className="text-xs bg-primary/10 text-primary border-primary/30 shrink-0"
                        >
                          {item.title.split(": ").slice(1).join(": ")}
                        </Badge>
                      )}
                      {executionMode && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs shrink-0",
                            isLive
                              ? "bg-green-500/10 text-green-500 border-green-500/30"
                              : "bg-orange-500/10 text-orange-500 border-orange-500/30",
                          )}
                        >
                          {t(`activity.${isLive ? "live" : "mock"}`)}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {item.description}
                    </p>
                    <p className="text-xs text-muted-foreground/70 mt-1">
                      {formatTimeAgo(item.timestamp, tTime)}
                    </p>
                  </div>
                  {item.data?.confidence !== undefined && (
                    <Badge variant="outline" className="text-xs shrink-0">
                      {Number(item.data.confidence)}%
                    </Badge>
                  )}
                  {isClickable && (
                    <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-foreground/70 transition-colors shrink-0 mt-1" />
                  )}
                </>
              );

              const sharedClassName = cn(
                "flex items-start gap-3 p-3 rounded-lg bg-muted/30 transition-colors group hover:bg-muted/50",
                isClickable && "cursor-pointer",
              );

              return isClickable ? (
                <Link
                  key={item.id}
                  href={`/agents/${agentId}?tab=decisions&decision=${item.id}`}
                  className={sharedClassName}
                  title={t("activity.viewDetail")}
                >
                  {content}
                </Link>
              ) : (
                <div key={item.id} className={sharedClassName}>
                  {content}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <div className="text-center">
              <div className="relative mx-auto w-12 h-12 mb-4">
                <span className="absolute inset-0 rounded-full bg-primary/20 animate-ping" />
                <span className="relative flex items-center justify-center w-12 h-12 rounded-full bg-primary/10">
                  <Activity className="w-6 h-6 text-primary" />
                </span>
              </div>
              <p>{t("activity.monitoring")}</p>
              <p className="text-sm">{t("activity.analyzing")}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
