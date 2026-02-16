'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation';
import {
  Search,
  Filter,
  GitFork,
  Bot,
  Grid3X3,
  ArrowDownUp,
  Activity,
  LineChart,
  Store,
  ArrowUpDown,
  User,
  Zap,
  Loader2,
} from 'lucide-react';
import {
  ListPageSkeleton,
  ListPageError,
  ListPageEmpty,
  ListPageFilterEmpty,
} from '@/components/list-page';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import { useMarketplaceStrategies, useForkStrategy } from '@/hooks';
import { useToast } from '@/components/ui/toast';
import type { StrategyResponse } from '@/lib/api';
import type { StrategyType } from '@/types';

// ==================== Helper Functions ====================

function getTypeIcon(type: string) {
  switch (type) {
    case 'ai':
      return Bot;
    case 'grid':
      return Grid3X3;
    case 'dca':
      return ArrowDownUp;
    case 'rsi':
      return Activity;
    default:
      return LineChart;
  }
}

function getTypeColor(type: string) {
  switch (type) {
    case 'ai':
      return 'border-violet-500/30 text-violet-500';
    case 'grid':
      return 'border-blue-500/30 text-blue-500';
    case 'dca':
      return 'border-emerald-500/30 text-emerald-500';
    case 'rsi':
      return 'border-amber-500/30 text-amber-500';
    default:
      return '';
  }
}

// ==================== Marketplace Strategy Card ====================

interface MarketplaceCardProps {
  strategy: StrategyResponse;
  onFork: (id: string) => void;
  forking: boolean;
  t: ReturnType<typeof useTranslations>;
  tType: ReturnType<typeof useTranslations>;
}

function MarketplaceCard({
  strategy,
  onFork,
  forking,
  t,
  tType,
}: MarketplaceCardProps) {
  const TypeIcon = getTypeIcon(strategy.type);

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors gap-3 group">
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between overflow-hidden">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 shrink-0">
              <TypeIcon className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-lg">{strategy.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <Badge
                  variant="outline"
                  className={cn('text-xs', getTypeColor(strategy.type))}
                >
                  {tType(strategy.type)}
                </Badge>
                {strategy.symbols.length > 0 && (
                  <Badge variant="outline" className="text-xs">
                    {strategy.symbols.slice(0, 3).join(', ')}
                    {strategy.symbols.length > 3 &&
                      ` +${strategy.symbols.length - 3}`}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Description */}
        <p className="text-sm text-muted-foreground line-clamp-2">
          {strategy.description || t('empty.noDescription')}
        </p>

        {/* Tags */}
        {strategy.tags.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            {strategy.tags.slice(0, 4).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
            {strategy.tags.length > 4 && (
              <span className="text-xs text-muted-foreground">
                +{strategy.tags.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Metadata row */}
        <div className="flex items-center gap-4 pt-2 border-t border-border/30 text-xs text-muted-foreground">
          {strategy.author_name && (
            <span className="flex items-center gap-1">
              <User className="w-3 h-3" />
              {strategy.author_name}
            </span>
          )}
          <span className="flex items-center gap-1">
            <GitFork className="w-3 h-3" />
            {strategy.fork_count} {t('marketplace.forks')}
          </span>
          {strategy.is_paid && strategy.price_monthly && (
            <Badge
              variant="outline"
              className="text-xs border-amber-500/30 text-amber-500 ml-auto"
            >
              ${strategy.price_monthly}/mo
            </Badge>
          )}
          {!strategy.is_paid && (
            <Badge
              variant="outline"
              className="text-xs border-emerald-500/30 text-emerald-500 ml-auto"
            >
              Free
            </Badge>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          <Button
            variant="default"
            size="sm"
            className="flex-1"
            onClick={() => onFork(strategy.id)}
            disabled={forking}
          >
            {forking ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <GitFork className="w-4 h-4 mr-2" />
            )}
            {t('marketplace.forkAndUse')}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ==================== Main Marketplace Page ====================

export default function MarketplacePage() {
  const t = useTranslations('strategies');
  const tType = useTranslations('strategies.type');
  const router = useRouter();
  const toast = useToast();

  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [sortBy, setSortBy] = useState<'popular' | 'recent'>('popular');
  const [forkingId, setForkingId] = useState<string | null>(null);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchQuery);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { strategies, total, error, isLoading, refresh } =
    useMarketplaceStrategies({
      type_filter:
        typeFilter !== 'all' ? (typeFilter as StrategyType) : undefined,
      search: debouncedSearch || undefined,
      sort_by: sortBy,
      limit: 50,
    });

  const { trigger: forkTrigger } = useForkStrategy();

  const handleFork = async (strategyId: string) => {
    setForkingId(strategyId);
    try {
      const forked = await forkTrigger(strategyId);
      toast.success(t('marketplace.forkSuccess'));
      refresh(); // revalidate marketplace data to update fork counts
      // Redirect to agent creation wizard with the forked strategy pre-selected
      router.push(`/agents/new?strategyId=${forked.id}`);
    } catch (err) {
      const description = err instanceof Error ? err.message : undefined;
      toast.error(t('marketplace.forkError'), description);
    } finally {
      setForkingId(null);
    }
  };

  const hasNoStrategies = !isLoading && !error && strategies.length === 0;
  const isSearching = debouncedSearch.length > 0 || typeFilter !== 'all';

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">
            {t('marketplace.title')}
          </h1>
          <p className="text-muted-foreground">{t('marketplace.subtitle')}</p>
        </div>
        {total > 0 && (
          <Badge variant="secondary" className="text-sm">
            {t('marketplace.totalStrategies', { count: total })}
          </Badge>
        )}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder={t('marketplace.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-muted/50 pl-9"
          />
        </div>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40 bg-muted/50">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('filter.allTypes')}</SelectItem>
            <SelectItem value="ai">{tType('ai')}</SelectItem>
            <SelectItem value="grid">{tType('grid')}</SelectItem>
            <SelectItem value="dca">{tType('dca')}</SelectItem>
            <SelectItem value="rsi">{tType('rsi')}</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={sortBy}
          onValueChange={(v) => setSortBy(v as 'popular' | 'recent')}
        >
          <SelectTrigger className="w-40 bg-muted/50">
            <ArrowUpDown className="w-4 h-4 mr-2" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="popular">
              {t('marketplace.sortPopular')}
            </SelectItem>
            <SelectItem value="recent">
              {t('marketplace.sortRecent')}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Loading */}
      {isLoading && <ListPageSkeleton />}

      {/* Error */}
      {error && (
        <ListPageError
          message={error.message || t('error.loadFailed')}
          onRetry={() => refresh()}
          retryLabel={t('retry')}
        />
      )}

      {/* Empty state */}
      {hasNoStrategies && !isSearching && (
        <ListPageEmpty
          icon={Store}
          title={t('marketplace.emptyTitle')}
          description={t('marketplace.emptyDescription')}
        />
      )}

      {/* Empty search state */}
      {hasNoStrategies && isSearching && (
        <ListPageFilterEmpty
          icon={Search}
          title={t('marketplace.emptySearchTitle')}
          description={t('marketplace.emptySearchDescription')}
        />
      )}

      {/* Strategy Cards Grid */}
      {!isLoading && !error && strategies.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {strategies.map((strategy) => (
            <MarketplaceCard
              key={strategy.id}
              strategy={strategy}
              onFork={handleFork}
              forking={forkingId === strategy.id}
              t={t}
              tType={tType}
            />
          ))}
        </div>
      )}
    </div>
  );
}
