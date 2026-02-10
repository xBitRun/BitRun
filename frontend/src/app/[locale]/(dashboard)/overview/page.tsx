'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Wallet,
  Target,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  Loader2,
  RefreshCw,
  Bot,
  LineChart,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import {
  useWebSocket,
  useDashboardStats,
  useAccounts,
  useStrategies,
  useQuantStrategies,
  useActivityFeed,
} from '@/hooks';
import { useEffect } from 'react';
import type { ActivityItem } from '@/lib/api';

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

function StatsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i} className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <Skeleton className="h-9 w-9 rounded-lg" />
              <Skeleton className="h-5 w-16" />
            </div>
            <div className="mt-4 space-y-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-4 w-32" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Format currency values
function formatCurrency(value: number, showSign = false): string {
  const formatted = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Math.abs(value));

  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return formatted;
}

// Format percentage values
function formatPercent(value: number, showSign = false): string {
  const formatted = `${Math.abs(value).toFixed(2)}%`;
  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return formatted;
}

export default function DashboardPage() {
  const t = useTranslations('dashboard');
  const tPositions = useTranslations('dashboard.positions');

  // Data fetching - using aggregated hooks
  const {
    data: stats,
    positions,
    isLoading: statsLoading,
    mutate: refreshStats,
  } = useDashboardStats();
  const { isLoading: accountsLoading } = useAccounts();
  const { data: strategies, isLoading: agentsLoading } = useStrategies();
  const { data: quantStrategies } = useQuantStrategies();

  // Real-time updates via WebSocket
  const { isConnected, subscribe } = useWebSocket({
    onPositionUpdate: () => {
      refreshStats();
    },
  });

  // Subscribe to user notifications
  useEffect(() => {
    subscribe('system');
  }, [subscribe]);

  const isLoading = statsLoading || accountsLoading || agentsLoading;

  // Stats configuration - using real data
  const statsConfig = [
    {
      titleKey: 'totalEquity',
      value: stats ? formatCurrency(stats.totalEquity) : '$0.00',
      change: stats ? formatPercent(stats.unrealizedPnlPercent, true) : '0%',
      trend:
        (stats?.unrealizedPnl ?? 0) >= 0 ? ('up' as const) : ('down' as const),
      icon: Wallet,
    },
    {
      titleKey: 'dailyPL',
      value: stats ? formatCurrency(stats.unrealizedPnl, true) : '$0.00',
      change: stats ? formatPercent(stats.unrealizedPnlPercent, true) : '0%',
      trend:
        (stats?.unrealizedPnl ?? 0) >= 0 ? ('up' as const) : ('down' as const),
      icon: (stats?.unrealizedPnl ?? 0) >= 0 ? TrendingUp : TrendingDown,
    },
    {
      titleKey: 'activeStrategies',
      value: String(stats?.activeStrategies ?? 0),
      changeKey: 'executing',
      changeCount: stats?.totalStrategies ?? 0,
      trend: 'neutral' as const,
      icon: Zap,
    },
    {
      titleKey: 'openPositions',
      value: String(stats?.openPositions ?? 0),
      changeKey: 'inProfit',
      changeCount: stats?.profitablePositions ?? 0,
      trend: 'neutral' as const,
      icon: Target,
    },
  ];

  return (
    <div className="flex flex-col gap-6 min-h-[calc(100vh-6rem)] md:min-h-[calc(100vh-7rem)]">
        {/* Page Header */}
        <div className="flex items-center justify-between shrink-0">
          <div>
            <h1 className="text-2xl font-bold text-gradient">{t('title')}</h1>
            <p className="text-muted-foreground">
              {t('subtitle')}
              {isConnected && (
                <span className="ml-2 inline-flex items-center">
                  <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-1" />
                  <span className="text-xs text-green-500">Live</span>
                </span>
              )}
            </p>
          </div>
          <Link href="/agents">
            <Button className="glow-primary">
              <Bot className="w-4 h-4 mr-2" />
              {t('newAgent')}
            </Button>
          </Link>
        </div>

        {/* Stats Grid */}
        {isLoading ? (
          <StatsSkeleton />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 shrink-0">
            {statsConfig.map((stat) => (
              <Card
                key={stat.titleKey}
                className="bg-card/50 backdrop-blur-sm border-border/50"
              >
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="p-2 rounded-lg bg-primary/10">
                      <stat.icon className="w-5 h-5 text-primary" />
                    </div>
                    {stat.trend !== 'neutral' && (
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs',
                          stat.trend === 'up'
                            ? 'text-[var(--profit)] border-[var(--profit)]/30'
                            : 'text-[var(--loss)] border-[var(--loss)]/30'
                        )}
                      >
                        {stat.trend === 'up' ? (
                          <ArrowUpRight className="w-3 h-3 mr-1" />
                        ) : (
                          <ArrowDownRight className="w-3 h-3 mr-1" />
                        )}
                        {stat.change}
                      </Badge>
                    )}
                  </div>
                  <div className="mt-4">
                    <p className="text-2xl font-bold">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">
                      {t(`stats.${stat.titleKey}`)}
                      {stat.changeKey && (
                        <span className="ml-1 text-muted-foreground/70">
                          ({stat.changeCount} {t(`stats.${stat.changeKey}`)})
                        </span>
                      )}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Agent strategies P&L and win rate */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50 shrink-0">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary" />
              {t('agentStrategies.title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {strategies && strategies.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {strategies.map((s) => (
                  <Link
                    key={s.id}
                    href={`/agents/${s.id}`}
                    className="p-4 rounded-lg bg-muted/30 border border-border/30 hover:bg-muted/50 transition-colors"
                  >
                    <p className="font-medium truncate">{s.name}</p>
                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                      <span className="text-muted-foreground">{t('agentStrategies.totalPnl')}</span>
                      <span
                        className={cn(
                          'font-mono font-semibold text-right',
                          (s.total_pnl ?? 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'
                        )}
                      >
                        {s.total_pnl !== undefined && s.total_pnl !== null
                          ? `$${Math.abs(s.total_pnl).toLocaleString()}`
                          : '—'}
                      </span>
                      <span className="text-muted-foreground">{t('agentStrategies.winRate')}</span>
                      <span className="font-mono text-right">
                        {s.win_rate !== undefined && s.win_rate !== null
                          ? `${s.win_rate.toFixed(1)}%`
                          : '—'}
                      </span>
                      <span className="text-muted-foreground">{t('agentStrategies.trades')}</span>
                      <span className="font-mono text-right">{s.total_trades ?? 0}</span>
                    </div>
                    <p className="text-xs text-primary mt-2">{t('agentStrategies.viewAgent')}</p>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">{t('agentStrategies.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Quant strategies P&L and win rate */}
        <Card className="bg-card/50 backdrop-blur-sm border-border/50 shrink-0">
          <CardHeader>
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <LineChart className="w-5 h-5 text-primary" />
              {t('quantStrategies.title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {quantStrategies && quantStrategies.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {quantStrategies.map((s) => (
                  <Link
                    key={s.id}
                    href={`/strategies/${s.id}`}
                    className="p-4 rounded-lg bg-muted/30 border border-border/30 hover:bg-muted/50 transition-colors"
                  >
                    <p className="font-medium truncate">{s.name}</p>
                    <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                      <span className="text-muted-foreground">{t('quantStrategies.totalPnl')}</span>
                      <span
                        className={cn(
                          'font-mono font-semibold text-right',
                          (s.total_pnl ?? 0) >= 0 ? 'text-[var(--profit)]' : 'text-[var(--loss)]'
                        )}
                      >
                        {s.total_pnl !== undefined && s.total_pnl !== null
                          ? `$${Math.abs(s.total_pnl).toLocaleString()}`
                          : '—'}
                      </span>
                      <span className="text-muted-foreground">{t('quantStrategies.winRate')}</span>
                      <span className="font-mono text-right">
                        {s.win_rate !== undefined && s.win_rate !== null
                          ? `${s.win_rate.toFixed(1)}%`
                          : '—'}
                      </span>
                      <span className="text-muted-foreground">{t('quantStrategies.trades')}</span>
                      <span className="font-mono text-right">{s.total_trades ?? 0}</span>
                    </div>
                    <p className="text-xs text-primary mt-2">{t('quantStrategies.viewStrategy')}</p>
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground py-6 text-center">{t('quantStrategies.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Main Content Grid - Activity Feed & Positions side by side, fill remaining height */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 flex-1 min-h-0">
          {/* Activity Feed - Left */}
          <ActivityFeed t={t} className="min-h-0" />

          {/* Open Positions - Right */}
          <Card className="bg-card/50 backdrop-blur-sm border-border/50 flex flex-col min-h-0">
            <CardHeader className="flex flex-row items-center justify-between pb-4">
              <CardTitle className="text-lg font-semibold">
                {tPositions('title')}
              </CardTitle>
              <div className="flex items-center gap-2">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => refreshStats()}
                  className="h-8 w-8"
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
                <Badge variant="outline" className="text-muted-foreground">
                  {positions?.length ?? 0} {tPositions('active')}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 flex-1 overflow-y-auto">
              {statsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : positions && positions.length > 0 ? (
                positions.map((position, index) => (
                  <div
                    key={`${position.accountId}-${position.symbol}-${index}`}
                    className="p-4 rounded-lg bg-muted/30 border border-border/30"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="font-bold">{position.symbol}</span>
                        <Badge
                          variant={
                            position.side === 'long' ? 'default' : 'secondary'
                          }
                          className="text-xs"
                        >
                          {tPositions(position.side)}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {position.exchange}
                        </span>
                      </div>
                      <span
                        className={cn(
                          'font-mono font-semibold',
                          position.unrealizedPnl >= 0
                            ? 'text-[var(--profit)]'
                            : 'text-[var(--loss)]'
                        )}
                      >
                        {formatPercent(position.unrealizedPnlPercent, true)}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions('entry')}
                        </span>
                        <p className="font-mono">
                          ${position.entryPrice.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions('mark')}
                        </span>
                        <p className="font-mono">
                          ${position.markPrice.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions('size')}
                        </span>
                        <p className="font-mono">{position.size}</p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">
                          {tPositions('pnl')}
                        </span>
                        <p
                          className={cn(
                            'font-mono font-medium',
                            position.unrealizedPnl >= 0
                              ? 'text-[var(--profit)]'
                              : 'text-[var(--loss)]'
                          )}
                        >
                          {formatCurrency(position.unrealizedPnl, true)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <p>{tPositions('empty')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
    </div>
  );
}

// Activity Feed Component
function ActivityFeed({
  t,
  className,
}: {
  t: ReturnType<typeof useTranslations>;
  className?: string;
}) {
  const { data: activityData, isLoading, mutate } = useActivityFeed(10);

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'success':
        return <div className="w-2 h-2 rounded-full bg-[var(--profit)]" />;
      case 'error':
        return <div className="w-2 h-2 rounded-full bg-[var(--loss)]" />;
      default:
        return <div className="w-2 h-2 rounded-full bg-primary" />;
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'decision':
        return <Bot className="w-4 h-4 text-primary" />;
      case 'trade':
        return <TrendingUp className="w-4 h-4 text-[var(--profit)]" />;
      default:
        return <Activity className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <Card
      className={cn(
        'bg-card/50 backdrop-blur-sm border-border/50 flex flex-col',
        className
      )}
    >
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <CardTitle className="text-lg font-semibold flex items-center gap-2">
          <Activity className="w-5 h-5 text-primary" />
          {t('activity.title')}
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
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : activityData && activityData.items.length > 0 ? (
          <div className="space-y-3">
            {activityData.items.map((item: ActivityItem) => {
              const strategyId = item.data?.strategy_id as string | undefined;
              const isClickable = !!strategyId;

              const content = (
                <>
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 flex-shrink-0">
                    {getTypeIcon(item.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(item.status)}
                      <span className="font-medium text-sm truncate">
                        {item.title.includes(": ") ? item.title.split(": ")[0] : item.title}
                      </span>
                      {item.title.includes(": ") && (
                        <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/30 shrink-0">
                          {item.title.split(": ").slice(1).join(": ")}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {item.description}
                    </p>
                    <p className="text-xs text-muted-foreground/70 mt-1">
                      {formatTimeAgo(item.timestamp)}
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
                'flex items-start gap-3 p-3 rounded-lg bg-muted/30 transition-colors group hover:bg-muted/50',
                isClickable && 'cursor-pointer'
              );

              return isClickable ? (
                <Link
                  key={item.id}
                  href={`/agents/${strategyId}?tab=decisions&decision=${item.id}`}
                  className={sharedClassName}
                  title={t('activity.viewDetail')}
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
              <p>{t('activity.monitoring')}</p>
              <p className="text-sm">{t('activity.analyzing')}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
