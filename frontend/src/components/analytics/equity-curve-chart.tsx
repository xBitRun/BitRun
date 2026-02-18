"use client";

import { useMemo } from "react";
import { useTranslations } from "next-intl";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { TimeRangeSelector, type TimeRange } from "./time-range-selector";
import type { EquityDataPoint } from "@/lib/api/endpoints";

interface EquityCurveChartProps {
  data: EquityDataPoint[];
  isLoading?: boolean;
  timeRange: TimeRange;
  onTimeRangeChange: (range: TimeRange) => void;
  title?: string;
  className?: string;
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function EquityCurveChart({
  data,
  isLoading,
  timeRange,
  onTimeRangeChange,
  title,
  className,
}: EquityCurveChartProps) {
  const t = useTranslations("analytics.equityCurve");

  // Sample data if too many points
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];

    // If more than 300 points, sample
    if (data.length <= 300) return data;

    const step = Math.ceil(data.length / 300);
    return data.filter((_, i) => i % step === 0 || i === data.length - 1);
  }, [data]);

  // Calculate min/max for Y axis
  const { minValue, maxValue } = useMemo(() => {
    if (chartData.length === 0) {
      return { minValue: 0, maxValue: 10000 };
    }
    const values = chartData.map((d) => d.equity);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = (max - min) * 0.1;
    return {
      minValue: Math.max(0, min - padding),
      maxValue: max + padding,
    };
  }, [chartData]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader className="flex flex-row items-center justify-between">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-8 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[300px] w-full" />
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
          onChange={onTimeRangeChange}
        />
      </CardHeader>
      <CardContent>
        {chartData.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">
            {t("noData")}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <defs>
                <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[minValue, maxValue]}
                tickFormatter={formatCurrency}
                stroke="hsl(var(--muted-foreground))"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                labelStyle={{ color: "hsl(var(--foreground))", fontWeight: 600 }}
                formatter={(value: number) => [formatCurrency(value), "Equity"]}
                labelFormatter={formatDate}
              />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="hsl(var(--primary))"
                strokeWidth={2}
                fill="url(#equityGradient)"
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
