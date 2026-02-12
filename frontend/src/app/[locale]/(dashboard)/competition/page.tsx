'use client';

import { useTranslations } from 'next-intl';
import Link from 'next/link';
import { useMemo, useState } from 'react';
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  ArrowUpDown,
  RefreshCw,
  Bot,
  Loader2,
  Zap,
  Target,
  BarChart3,
  Medal,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useLeaderboard } from '@/hooks';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Cell,
  ReferenceLine,
} from 'recharts';
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from '@/components/ui/chart';

type SortField = 'total_pnl' | 'win_rate' | 'total_trades' | 'max_drawdown';
type StatusFilter = 'all' | 'active' | 'paused';

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

function formatPercent(value: number, showSign = false): string {
  const formatted = `${Math.abs(value).toFixed(2)}%`;
  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return formatted;
}

function getRankBadge(rank: number) {
  if (rank === 1) return <Medal className="w-5 h-5 text-yellow-500" />;
  if (rank === 2) return <Medal className="w-5 h-5 text-gray-400" />;
  if (rank === 3) return <Medal className="w-5 h-5 text-amber-600" />;
  return <span className="text-sm text-muted-foreground font-mono">{rank}</span>;
}

export default function CompetitionPage() {
  const t = useTranslations('competition');
  const [sortBy, setSortBy] = useState<SortField>('total_pnl');
  const [order, setOrder] = useState<'desc' | 'asc'>('desc');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const { leaderboard, stats, isLoading, mutate } = useLeaderboard(sortBy, order);

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      setOrder(order === 'desc' ? 'asc' : 'desc');
    } else {
      setSortBy(field);
      setOrder('desc');
    }
  };

  // Apply status filter
  const filteredLeaderboard = useMemo(() => {
    if (statusFilter === 'all') return leaderboard;
    return leaderboard.filter((entry) => {
      if (statusFilter === 'active') return entry.status === 'active';
      return entry.status !== 'active'; // paused / draft / stopped
    });
  }, [leaderboard, statusFilter]);

  // Chart data — sorted by P&L descending, max 15 entries
  const chartData = useMemo(() => {
    return [...filteredLeaderboard]
      .sort((a, b) => b.total_pnl - a.total_pnl)
      .slice(0, 15)
      .map((entry) => ({
        name: entry.name.length > 12 ? entry.name.slice(0, 12) + '…' : entry.name,
        pnl: entry.total_pnl,
      }));
  }, [filteredLeaderboard]);

  const chartConfig = {
    pnl: { label: t('table.totalPnl') },
  } satisfies ChartConfig;

  const statsConfig = [
    {
      key: 'totalStrategies',
      value: stats?.total_strategies ?? 0,
      icon: BarChart3,
    },
    {
      key: 'activeStrategies',
      value: stats?.active_strategies ?? 0,
      icon: Zap,
    },
    {
      key: 'avgWinRate',
      value: formatPercent(stats?.avg_win_rate ?? 0),
      icon: Target,
    },
    {
      key: 'totalTrades',
      value: stats?.total_trades ?? 0,
      icon: TrendingUp,
    },
  ];

  const filterOptions: { key: StatusFilter; label: string }[] = [
    { key: 'all', label: t('filter.all') },
    { key: 'active', label: t('filter.active') },
    { key: 'paused', label: t('filter.paused') },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient flex items-center gap-2">
            <Trophy className="w-7 h-7 text-primary" />
            {t('title')}
          </h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => mutate()}
          disabled={isLoading}
        >
          <RefreshCw className={cn('w-4 h-4 mr-2', isLoading && 'animate-spin')} />
          {t('refresh')}
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statsConfig.map((stat) => (
          <Card key={stat.key} className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 mb-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <stat.icon className="w-4 h-4 text-primary" />
                </div>
                <span className="text-xs text-muted-foreground">
                  {t(`stats.${stat.key}`)}
                </span>
              </div>
              <p className="text-xl font-bold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Best / Worst P&L */}
      {stats && (stats.best_pnl !== 0 || stats.worst_pnl !== 0) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--profit)]/10">
                <TrendingUp className="w-5 h-5 text-[var(--profit)]" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('stats.bestPnl')}</p>
                <p className="text-lg font-bold text-[var(--profit)]">
                  {formatCurrency(stats.best_pnl, true)}
                </p>
                {stats.best_performer && (
                  <p className="text-xs text-muted-foreground">{stats.best_performer}</p>
                )}
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card/50 backdrop-blur-sm border-border/50">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-[var(--loss)]/10">
                <TrendingDown className="w-5 h-5 text-[var(--loss)]" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t('stats.worstPnl')}</p>
                <p className="text-lg font-bold text-[var(--loss)]">
                  {formatCurrency(stats.worst_pnl, true)}
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* P&L Comparison Chart */}
      {!isLoading && chartData.length > 0 && (
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              {t('chart.title')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ChartContainer config={chartConfig} className="min-h-[220px] w-full">
              <BarChart accessibilityLayer data={chartData}>
                <CartesianGrid vertical={false} />
                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: number) => `$${v}`}
                />
                <ChartTooltip
                  content={
                    <ChartTooltipContent
                      formatter={(value) => formatCurrency(Number(value), true)}
                    />
                  }
                />
                <ReferenceLine y={0} stroke="var(--muted-foreground)" strokeDasharray="3 3" />
                <Bar dataKey="pnl" name={t('table.totalPnl')} radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.pnl >= 0 ? 'var(--profit)' : 'var(--loss)'}
                      fillOpacity={0.8}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ChartContainer>
          </CardContent>
        </Card>
      )}

      {/* Leaderboard Table */}
      <Card className="bg-card/50 backdrop-blur-sm border-border/50">
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <Trophy className="w-5 h-5 text-primary" />
              {t('leaderboard')}
            </CardTitle>
            {/* Status Filter */}
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-0.5">
              {filterOptions.map((opt) => (
                <Button
                  key={opt.key}
                  variant={statusFilter === opt.key ? 'default' : 'ghost'}
                  size="sm"
                  className={cn(
                    'h-7 text-xs px-3',
                    statusFilter === opt.key
                      ? ''
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                  onClick={() => setStatusFilter(opt.key)}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
            </div>
          ) : filteredLeaderboard.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50">
                    <th className="text-left py-3 px-2 text-muted-foreground font-medium w-10">
                      {t('table.rank')}
                    </th>
                    <th className="text-left py-3 px-2 text-muted-foreground font-medium">
                      {t('table.name')}
                    </th>
                    <th className="text-left py-3 px-2 text-muted-foreground font-medium hidden md:table-cell">
                      {t('table.status')}
                    </th>
                    <th className="text-left py-3 px-2 text-muted-foreground font-medium hidden lg:table-cell">
                      {t('table.model')}
                    </th>
                    <th className="text-right py-3 px-2">
                      <button
                        onClick={() => handleSort('total_pnl')}
                        className="inline-flex items-center gap-1 text-muted-foreground font-medium hover:text-foreground transition-colors"
                      >
                        {t('table.totalPnl')}
                        <ArrowUpDown className="w-3 h-3" />
                      </button>
                    </th>
                    <th className="text-right py-3 px-2">
                      <button
                        onClick={() => handleSort('win_rate')}
                        className="inline-flex items-center gap-1 text-muted-foreground font-medium hover:text-foreground transition-colors"
                      >
                        {t('table.winRate')}
                        <ArrowUpDown className="w-3 h-3" />
                      </button>
                    </th>
                    <th className="text-right py-3 px-2 hidden md:table-cell">
                      <button
                        onClick={() => handleSort('total_trades')}
                        className="inline-flex items-center gap-1 text-muted-foreground font-medium hover:text-foreground transition-colors"
                      >
                        {t('table.trades')}
                        <ArrowUpDown className="w-3 h-3" />
                      </button>
                    </th>
                    <th className="text-right py-3 px-2 hidden lg:table-cell">
                      <button
                        onClick={() => handleSort('max_drawdown')}
                        className="inline-flex items-center gap-1 text-muted-foreground font-medium hover:text-foreground transition-colors"
                      >
                        {t('table.maxDrawdown')}
                        <ArrowUpDown className="w-3 h-3" />
                      </button>
                    </th>
                    <th className="text-right py-3 px-2 w-20">
                      {t('table.actions')}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeaderboard.map((entry) => (
                    <tr
                      key={entry.strategy_id}
                      className="border-b border-border/30 hover:bg-muted/30 transition-colors"
                    >
                      <td className="py-3 px-2">
                        <div className="flex items-center justify-center">
                          {getRankBadge(entry.rank)}
                        </div>
                      </td>
                      <td className="py-3 px-2">
                        <div className="flex items-center gap-2">
                          <Bot className="w-4 h-4 text-primary shrink-0" />
                          <span className="font-medium truncate max-w-[150px]">
                            {entry.name}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-2 hidden md:table-cell">
                        <Badge
                          variant={entry.status === 'active' ? 'default' : 'secondary'}
                          className="text-xs"
                        >
                          {entry.status}
                        </Badge>
                      </td>
                      <td className="py-3 px-2 hidden lg:table-cell">
                        <span className="text-xs text-muted-foreground truncate max-w-[120px] inline-block">
                          {entry.ai_model?.split(':').pop() || '—'}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right">
                        <span
                          className={cn(
                            'font-mono font-semibold',
                            entry.total_pnl >= 0
                              ? 'text-[var(--profit)]'
                              : 'text-[var(--loss)]'
                          )}
                        >
                          {formatCurrency(entry.total_pnl, true)}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right font-mono">
                        {formatPercent(entry.win_rate)}
                      </td>
                      <td className="py-3 px-2 text-right font-mono hidden md:table-cell">
                        {entry.total_trades}
                      </td>
                      <td className="py-3 px-2 text-right font-mono hidden lg:table-cell">
                        <span className="text-[var(--loss)]">
                          {formatPercent(entry.max_drawdown)}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right">
                        <Link href={`/agents/${entry.strategy_id}`}>
                          <Button variant="ghost" size="sm" className="text-xs">
                            {t('viewDetails')}
                          </Button>
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="text-center py-12">
              <Trophy className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
              <h3 className="text-lg font-medium mb-2">{t('empty.title')}</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {t('empty.description')}
              </p>
              <Link href="/agents/new">
                <Button>{t('empty.createFirst')}</Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
