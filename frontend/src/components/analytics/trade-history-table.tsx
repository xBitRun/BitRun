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
import { PnLCell, formatPrice, formatDuration } from "@/components/pnl";
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

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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
                <PnLCell value={trade.realized_pnl} weight="semibold" />
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
