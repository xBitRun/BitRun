"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Plus,
  FlaskConical,
  TrendingUp,
  TrendingDown,
  Target,
  Calendar,
  BarChart3,
  Clock,
  ExternalLink,
  Loader2,
  Trash2,
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { useBacktests, useDeleteBacktest } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { BacktestListItem } from "@/lib/api";

// ===================== Backtest Card =====================

function BacktestCard({
  item,
  onDelete,
  isDeleting,
}: {
  item: BacktestListItem;
  onDelete: () => void;
  isDeleting: boolean;
}) {
  const t = useTranslations("backtest");

  const isPositive = item.total_return_percent >= 0;
  const formatDate = (dateStr: string) => dateStr?.slice(0, 10) || "-";

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-border transition-colors group">
      <CardContent className="pt-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-semibold text-foreground group-hover:text-primary transition-colors">
              {item.strategy_name}
            </h3>
            <div className="flex items-center gap-2 text-xs text-muted-foreground mt-1">
              <Badge variant="outline" className="text-[10px]">
                {item.exchange}
              </Badge>
              <span>•</span>
              <span>
                {formatDate(item.start_date)} - {formatDate(item.end_date)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  disabled={isDeleting}
                >
                  {isDeleting ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Trash2 className="w-4 h-4" />
                  )}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>{t("list.confirmDelete")}</AlertDialogTitle>
                  <AlertDialogDescription>
                    {t("list.confirmDeleteDescription")}
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>{t("list.cancel")}</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={onDelete}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                  >
                    {t("list.delete")}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <div className="bg-muted/30 rounded-lg p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs mb-1">
              {isPositive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span>{t("list.return")}</span>
            </div>
            <p
              className={cn(
                "text-lg font-bold font-mono",
                isPositive ? "text-[var(--profit)]" : "text-[var(--loss)]",
              )}
            >
              {isPositive ? "+" : ""}
              {item.total_return_percent.toFixed(2)}%
            </p>
          </div>

          <div className="bg-muted/30 rounded-lg p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs mb-1">
              <Target className="w-3 h-3" />
              <span>{t("list.winRate")}</span>
            </div>
            <p
              className={cn(
                "text-lg font-bold font-mono",
                item.win_rate >= 50
                  ? "text-[var(--profit)]"
                  : "text-[var(--loss)]",
              )}
            >
              {item.win_rate.toFixed(1)}%
            </p>
          </div>

          <div className="bg-muted/30 rounded-lg p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs mb-1">
              <TrendingDown className="w-3 h-3" />
              <span>{t("list.maxDrawdown")}</span>
            </div>
            <p className="text-lg font-bold font-mono text-[var(--loss)]">
              -{Math.abs(item.max_drawdown_percent).toFixed(2)}%
            </p>
          </div>

          <div className="bg-muted/30 rounded-lg p-2.5">
            <div className="flex items-center gap-1.5 text-muted-foreground text-xs mb-1">
              <BarChart3 className="w-3 h-3" />
              <span>{t("list.trades")}</span>
            </div>
            <p className="text-lg font-bold font-mono">{item.total_trades}</p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="w-3 h-3" />
            <span>{new Date(item.created_at).toLocaleString()}</span>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href={`/backtest/${item.id}`}>
              {t("list.viewDetails")}
              <ExternalLink className="w-3 h-3 ml-1" />
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

// ===================== Main Page =====================

export default function BacktestListPage() {
  const t = useTranslations("backtest");
  const toast = useToast();
  const { data: backtestsData, isLoading, mutate } = useBacktests(50, 0);
  const { trigger: deleteBacktest, deletingId } = useDeleteBacktest();

  const backtests = backtestsData?.items || [];
  const total = backtestsData?.total || 0;

  const handleDelete = async (id: string) => {
    try {
      await deleteBacktest(id);
      toast.success(t("list.deleteSuccess"));
      mutate();
    } catch (error) {
      const message =
        error instanceof Error ? error.message : t("list.deleteFailed");
      toast.error(t("list.deleteFailed"), message);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">
            {t("list.title")}
          </h1>
          <p className="text-muted-foreground">{t("list.subtitle")}</p>
        </div>
        <Button asChild>
          <Link href="/backtest/run">
            <Plus className="w-4 h-4 mr-2" />
            {t("list.runNew")}
          </Link>
        </Button>
      </div>

      {/* Backtest List */}
      {isLoading ? (
        <div className="flex items-center justify-center min-h-[400px]">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : backtests.length === 0 ? (
        <Card className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardContent className="flex flex-col items-center justify-center py-16 text-center">
            <div className="p-4 rounded-full bg-muted/50 mb-4">
              <FlaskConical className="w-8 h-8 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-semibold mb-2">{t("list.empty")}</h3>
            <p className="text-muted-foreground max-w-sm mb-4">
              {t("list.emptyHint")}
            </p>
            <Button asChild>
              <Link href="/backtest/run">
                <Plus className="w-4 h-4 mr-2" />
                {t("list.runNew")}
              </Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {t("list.totalRecords", { count: total })}
            </p>
          </div>
          <div className="grid gap-4">
            {backtests.map((item) => (
              <BacktestCard
                key={item.id}
                item={item}
                onDelete={() => handleDelete(item.id)}
                isDeleting={deletingId === item.id}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
