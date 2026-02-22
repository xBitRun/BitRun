'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import Link from 'next/link';
import {
  Plus,
  MoreHorizontal,
  LineChart,
  Grid3X3,
  ArrowDownUp,
  Activity,
  Filter,
  Bot,
  GitFork,
  Eye,
  Trash2,
  Zap,
  Copy,
  type LucideIcon,
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useStrategies } from '@/hooks';
import { useRouter } from '@/i18n/navigation';
import { useToast } from '@/components/ui/toast';
import type { StrategyResponse } from '@/lib/api';


function getTypeIcon(type: string): LucideIcon {
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
      return 'border-rose-500/30 text-rose-500';
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

function getVisibilityColor(vis: string) {
  return vis === 'public'
    ? 'border-emerald-500/30 text-emerald-500'
    : 'border-muted-foreground/30 text-muted-foreground';
}

interface StrategyCardProps {
  strategy: StrategyResponse;
  typeIcon: LucideIcon;
  onDelete: (id: string) => void;
  onToggleVisibility: (id: string, current: string) => void;
  onDuplicate: (id: string) => void;
  t: ReturnType<typeof useTranslations>;
  tType: ReturnType<typeof useTranslations>;
}

function StrategyCard({
  strategy,
  typeIcon: TypeIcon,
  onDelete,
  onToggleVisibility,
  onDuplicate,
  t,
  tType,
}: StrategyCardProps) {

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors gap-3">
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
                <Badge
                  variant="outline"
                  className={cn(
                    'text-xs',
                    getVisibilityColor(strategy.visibility)
                  )}
                >
                  {t(`visibility.${strategy.visibility}`)}
                </Badge>
                {strategy.symbols.length > 0 && (
                  <Badge
                    variant="outline"
                    className="bg-primary/10 text-primary border-primary/30 font-mono text-xs py-0"
                  >
                    {strategy.symbols.slice(0, 3).join(', ')}
                    {strategy.symbols.length > 3 &&
                      ` +${strategy.symbols.length - 3}`}
                  </Badge>
                )}
              </div>
              <p className="text-sm text-muted-foreground truncate mt-1">
                {strategy.description || t('empty.noDescription')}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link
                  href={`/strategies/${strategy.id}`}
                  className="flex items-center"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  {t('actions.viewDetails')}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link
                  href={`/agents/new?strategyId=${strategy.id}`}
                  className="flex items-center"
                >
                  <Zap className="w-4 h-4 mr-2" />
                  {t('actions.createAgent')}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onDuplicate(strategy.id)}>
                <Copy className="w-4 h-4 mr-2" />
                {t('actions.duplicate')}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() =>
                  onToggleVisibility(strategy.id, strategy.visibility)
                }
              >
                {strategy.visibility === 'public' ? (
                  <>
                    <Eye className="w-4 h-4 mr-2" />
                    {t('actions.makePrivate')}
                  </>
                ) : (
                  <>
                    <GitFork className="w-4 h-4 mr-2" />
                    {t('actions.makePublic')}
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive"
                onClick={() => onDelete(strategy.id)}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                {t('actions.delete')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Tags and metadata */}
        <div className="flex items-center gap-4 pt-2 border-t border-border/30">
          {strategy.tags.length > 0 && (
            <div className="flex items-center gap-1 flex-wrap">
              {strategy.tags.slice(0, 3).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          )}
          <div className="flex items-center gap-3 ml-auto text-xs text-muted-foreground">
            {strategy.fork_count > 0 && (
              <span className="flex items-center gap-1">
                <GitFork className="w-3 h-3" />
                {strategy.fork_count}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          <Link
            href={`/agents/new?strategyId=${strategy.id}`}
            className="flex-1"
          >
            <Button variant="default" size="sm" className="w-full">
              <Zap className="w-4 h-4 mr-2" />
              {t('actions.createAgent')}
            </Button>
          </Link>
          <Link href={`/strategies/${strategy.id}`}>
            <Button variant="ghost" size="sm">
              {t('actions.viewDetails')}
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
}

export default function StrategiesPage() {
  const t = useTranslations('strategies');
  const tType = useTranslations('strategies.type');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [deleteConfirm, setDeleteConfirm] = useState<{
    show: boolean;
    strategyId: string;
  }>({ show: false, strategyId: '' });
  const [isDeleting, setIsDeleting] = useState(false);

  const { strategies, error, isLoading, refresh } = useStrategies();
  const toast = useToast();
  const router = useRouter();

  const handleDelete = (id: string) => {
    setDeleteConfirm({ show: true, strategyId: id });
  };

  const handleDuplicate = async (id: string) => {
    try {
      const { strategiesApi } = await import('@/lib/api');
      const newStrategy = await strategiesApi.duplicate(id);
      toast.success(t('toast.duplicated'));
      router.push(`/strategies/${newStrategy.id}/edit`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('error.duplicateFailed');
      toast.error(t('error.duplicateFailed'), message);
    }
  };

  const confirmDelete = async () => {
    setIsDeleting(true);
    try {
      const { strategiesApi } = await import('@/lib/api');
      await strategiesApi.delete(deleteConfirm.strategyId);
      refresh();
      toast.success(t('toast.deleted'));
      setDeleteConfirm({ show: false, strategyId: '' });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('error.deleteFailed');
      toast.error(t('error.deleteFailed'), message);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleToggleVisibility = async (id: string, current: string) => {
    const newVisibility = current === 'public' ? 'private' : 'public';
    try {
      const { strategiesApi } = await import('@/lib/api');
      await strategiesApi.update(id, {
        visibility: newVisibility as 'private' | 'public',
      });
      refresh();
      toast.success(t('toast.updated'));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t('error.updateFailed');
      toast.error(t('error.updateFailed'), message);
    }
  };

  const filteredStrategies = strategies.filter((s) => {
    const matchesType = typeFilter === 'all' || s.type === typeFilter;
    const matchesSearch = s.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  const hasNoStrategies = !isLoading && !error && strategies.length === 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t('title')}</h1>
          <p className="text-muted-foreground">{t('subtitle')}</p>
        </div>
        <Link href="/strategies/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t('createStrategy')}
          </Button>
        </Link>
      </div>

      {/* Filters */}
      {!hasNoStrategies && (
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Input
              placeholder={t('searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-muted/50"
            />
          </div>
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-40 bg-muted/50">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('filter.allTypes')}</SelectItem>
              <SelectItem value="ai">{tType('ai')}</SelectItem>
              <SelectItem value="grid">{tType('grid')}</SelectItem>
              <SelectItem value="dca">{tType('dca')}</SelectItem>
              <SelectItem value="rsi">{tType('rsi')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

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

      {/* Empty */}
      {hasNoStrategies && (
        <ListPageEmpty
          icon={LineChart}
          title={t('empty.title')}
          description={t('empty.createHint')}
          actionLabel={t('createStrategy')}
          actionHref="/strategies/new"
          actionIcon={Plus}
        />
      )}

      {/* Strategy Cards */}
      {!isLoading && !error && strategies.length > 0 && (
        <>
          {filteredStrategies.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredStrategies.map((strategy) => (
                <StrategyCard
                  key={strategy.id}
                  strategy={strategy}
                  typeIcon={getTypeIcon(strategy.type)}
                  onDelete={handleDelete}
                  onToggleVisibility={handleToggleVisibility}
                  onDuplicate={handleDuplicate}
                  t={t}
                  tType={tType}
                />
              ))}
              <Link href="/strategies/new" className="block h-full">
                <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardContent className="flex flex-col items-center justify-center h-full min-h-0 py-8 text-muted-foreground hover:text-foreground transition-colors">
                    <div className="p-3 rounded-full bg-muted/30 mb-3">
                      <Plus className="w-6 h-6" />
                    </div>
                    <p className="font-medium">{t('createStrategy')}</p>
                  </CardContent>
                </Card>
              </Link>
            </div>
          ) : (
            <ListPageFilterEmpty
              icon={LineChart}
              title={t('empty.title')}
              description={t('empty.searchHint')}
            />
          )}
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirm.show}
        onOpenChange={(open) => {
          if (!open) setDeleteConfirm({ show: false, strategyId: '' });
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('deleteConfirm.title')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('deleteConfirm.description')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t('deleteConfirm.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              disabled={isDeleting}
              className="bg-destructive hover:bg-destructive/90"
            >
              {isDeleting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
              {t('deleteConfirm.confirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
