"use client";

import { useState, useMemo, useCallback } from "react";
import { useTranslations } from "next-intl";
import { ChevronLeft, ChevronRight, TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeRangeSelector, type TimeRange } from "./time-range-selector";
import type { EquityDataPoint } from "@/lib/api/endpoints";

interface EquityCurveTableProps {
  data: EquityDataPoint[];
  isLoading?: boolean;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
  title?: string;
  className?: string;
  pageSize?: number;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
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

function formatPercent(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

export function EquityCurveTable({
  data,
  isLoading,
  timeRange,
  onTimeRangeChange,
  title,
  className,
  pageSize = 15,
}: EquityCurveTableProps) {
  const t = useTranslations("analytics.equityCurve");
  const [currentPage, setCurrentPage] = useState(1);

  // Handle time range change and reset pagination in event handler
  const handleTimeRangeChange = useCallback((newRange: TimeRange) => {
    setCurrentPage(1); // Reset to first page when time range changes
    onTimeRangeChange(newRange);
  }, [onTimeRangeChange]);

  // Sort data by date descending (newest first)
  const sortedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    return [...data].sort(
      (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
    );
  }, [data]);

  // Pagination
  const totalPages = Math.ceil(sortedData.length / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return sortedData.slice(start, start + pageSize);
  }, [sortedData, currentPage, pageSize]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="flex flex-row items-center justify-between">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg">{title ?? t("title")}</CardTitle>
        <TimeRangeSelector
          value={timeRange}
          onChange={handleTimeRangeChange}
        />
      </CardHeader>
      <CardContent>
        {sortedData.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t("noData")}
          </div>
        ) : (
          <>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("columns.date")}</TableHead>
                  <TableHead className="text-right">{t("columns.equity")}</TableHead>
                  <TableHead className="text-right">{t("columns.dailyPnl")}</TableHead>
                  <TableHead className="text-right">{t("columns.dailyPnlPercent")}</TableHead>
                  <TableHead className="text-right">{t("columns.cumulativePnl")}</TableHead>
                  <TableHead className="text-right">{t("columns.cumulativePnlPercent")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedData.map((point, index) => {
                  const isPositive = point.daily_pnl >= 0;
                  const TrendIcon = isPositive ? TrendingUp : TrendingDown;

                  return (
                    <TableRow key={point.date}>
                      <TableCell className="font-medium">
                        {formatDate(point.date)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {formatCurrency(point.equity)}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        <span
                          className={cn(
                            "flex items-center justify-end gap-1",
                            isPositive
                              ? "text-[var(--profit)]"
                              : "text-[var(--loss)]",
                          )}
                        >
                          <TrendIcon className="w-3 h-3" />
                          {formatCurrency(point.daily_pnl)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        <span
                          className={cn(
                            isPositive
                              ? "text-[var(--profit)]"
                              : "text-[var(--loss)]",
                          )}
                        >
                          {formatPercent(point.daily_pnl_percent)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        <span
                          className={cn(
                            point.cumulative_pnl >= 0
                              ? "text-[var(--profit)]"
                              : "text-[var(--loss)]",
                          )}
                        >
                          {formatCurrency(point.cumulative_pnl)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        <span
                          className={cn(
                            point.cumulative_pnl_percent >= 0
                              ? "text-[var(--profit)]"
                              : "text-[var(--loss)]",
                          )}
                        >
                          {formatPercent(point.cumulative_pnl_percent)}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4 border-t mt-4">
                <p className="text-sm text-muted-foreground">
                  {t("pagination.info", {
                    start: (currentPage - 1) * pageSize + 1,
                    end: Math.min(currentPage * pageSize, sortedData.length),
                    total: sortedData.length,
                  })}
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </Button>
                  <span className="text-sm text-muted-foreground px-2">
                    {currentPage} / {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                    disabled={currentPage === totalPages}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
