"use client";

import { useTranslations } from "next-intl";
import {
  TrendingUp,
  TrendingDown,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { PnLTradeRecord } from "@/lib/api/endpoints";

interface TradeHistoryTableProps {
  trades: PnLTradeRecord[];
  isLoading?: boolean;
  total: number;
  limit: number;
  offset: number;
  onPageChange: (offset: number) => void;
  className?: string;
}

function formatCurrency(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)}`;
}

function formatPrice(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours < 24) {
    return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`;
}

const exitReasonLabels: Record<string, string> = {
  take_profit: "TP",
  stop_loss: "SL",
  signal: "Signal",
  manual: "Manual",
};

export function TradeHistoryTable({
  trades,
  isLoading,
  total,
  limit,
  offset,
  onPageChange,
  className,
}: TradeHistoryTableProps) {
  const t = useTranslations("analytics.trades");

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  if (isLoading) {
    return (
      <div className={cn("space-y-3", className)}>
        {[1, 2, 3, 4, 5].map((i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    );
  }

  if (trades.length === 0) {
    return (
      <div className={cn("text-center py-8 text-muted-foreground", className)}>
        {t("noData")}
      </div>
    );
  }

  return (
    <div className={cn("space-y-4", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("columns.symbol")}</TableHead>
            <TableHead>{t("columns.side")}</TableHead>
            <TableHead className="text-right">{t("columns.entry")}</TableHead>
            <TableHead className="text-right">{t("columns.exit")}</TableHead>
            <TableHead className="text-right">{t("columns.size")}</TableHead>
            <TableHead className="text-right">{t("columns.pnl")}</TableHead>
            <TableHead className="text-right">
              {t("columns.duration")}
            </TableHead>
            <TableHead>{t("columns.exitReason")}</TableHead>
            <TableHead>{t("columns.time")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade) => {
            const isProfit = trade.realized_pnl > 0;
            const isLoss = trade.realized_pnl < 0;
            const pnlColor = isProfit
              ? "text-[var(--profit)]"
              : isLoss
                ? "text-[var(--loss)]"
                : "text-muted-foreground";

            const SideIcon = trade.side === "long" ? TrendingUp : TrendingDown;
            const sideColor =
              trade.side === "long"
                ? "bg-green-500/10 text-green-500"
                : "bg-red-500/10 text-red-500";

            return (
              <TableRow key={trade.id}>
                <TableCell>
                  <span className="font-medium">{trade.symbol}</span>
                </TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={cn("gap-1 uppercase", sideColor)}
                  >
                    <SideIcon className="w-3 h-3" />
                    {trade.side}
                  </Badge>
                </TableCell>
                <TableCell className="text-right font-mono">
                  {formatPrice(trade.entry_price)}
                </TableCell>
                <TableCell className="text-right font-mono">
                  {trade.exit_price ? formatPrice(trade.exit_price) : "-"}
                </TableCell>
                <TableCell className="text-right font-mono">
                  ${formatPrice(trade.size_usd)}
                </TableCell>
                <TableCell className="text-right font-mono font-medium">
                  <span className={pnlColor}>
                    {formatCurrency(trade.realized_pnl)}
                  </span>
                </TableCell>
                <TableCell className="text-right font-mono text-muted-foreground">
                  {formatDuration(trade.duration_minutes)}
                </TableCell>
                <TableCell>
                  {trade.exit_reason && (
                    <Badge variant="secondary" className="text-xs">
                      {exitReasonLabels[trade.exit_reason] ?? trade.exit_reason}
                    </Badge>
                  )}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatDateTime(trade.closed_at)}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {t("pagination", {
              total,
              current: currentPage,
              pages: totalPages,
            })}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={offset === 0}
              onClick={() => onPageChange(offset - limit)}
            >
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={currentPage >= totalPages}
              onClick={() => onPageChange(offset + limit)}
            >
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
