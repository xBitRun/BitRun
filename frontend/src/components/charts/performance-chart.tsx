"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface DataPoint {
  timestamp: string;
  value: number;
  label?: string;
}

interface PerformanceChartProps {
  data: DataPoint[];
  height?: number;
  showGrid?: boolean;
  showLabels?: boolean;
  positiveColor?: string;
  negativeColor?: string;
  className?: string;
}

/**
 * Simple performance chart using SVG
 * Displays a line chart with gradient fill
 */
export function PerformanceChart({
  data,
  height = 200,
  showGrid = true,
  showLabels = true,
  positiveColor = "var(--profit)",
  negativeColor = "var(--loss)",
  className,
}: PerformanceChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return null;

    const values = data.map((d) => d.value);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue || 1;

    // Determine if overall performance is positive
    const isPositive = data[data.length - 1]?.value >= data[0]?.value;

    // Calculate chart dimensions
    const width = 100; // Percentage width
    const padding = { top: 10, bottom: 30, left: 10, right: 10 };
    const chartHeight = height - padding.top - padding.bottom;
    const chartWidth = width - padding.left - padding.right;

    // Generate path points
    const points = data.map((d, i) => {
      const x = padding.left + (i / (data.length - 1)) * chartWidth;
      const y =
        padding.top +
        chartHeight -
        ((d.value - minValue) / valueRange) * chartHeight;
      return { x, y, ...d };
    });

    // Create SVG path
    const linePath =
      points
        .map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`))
        .join(" ");

    // Create area path (for gradient fill)
    const areaPath =
      linePath +
      ` L ${points[points.length - 1].x} ${height - padding.bottom}` +
      ` L ${points[0].x} ${height - padding.bottom}` +
      " Z";

    return {
      points,
      linePath,
      areaPath,
      minValue,
      maxValue,
      isPositive,
      padding,
      chartHeight,
      chartWidth,
    };
  }, [data, height]);

  if (!chartData || !data || data.length === 0) {
    return (
      <div
        className={cn(
          "flex items-center justify-center text-muted-foreground",
          className
        )}
        style={{ height }}
      >
        No data available
      </div>
    );
  }

  const { points, linePath, areaPath, minValue, maxValue, isPositive, padding } =
    chartData;
  const color = isPositive ? positiveColor : negativeColor;

  return (
    <div className={cn("relative", className)}>
      <svg
        viewBox={`0 0 100 ${height}`}
        preserveAspectRatio="none"
        className="w-full"
        style={{ height }}
      >
        {/* Definitions */}
        <defs>
          <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* Grid lines */}
        {showGrid && (
          <g className="stroke-muted/30" strokeWidth="0.1">
            {[0.25, 0.5, 0.75].map((ratio) => (
              <line
                key={ratio}
                x1={padding.left}
                y1={padding.top + chartData.chartHeight * ratio}
                x2={100 - padding.right}
                y2={padding.top + chartData.chartHeight * ratio}
              />
            ))}
          </g>
        )}

        {/* Area fill */}
        <path d={areaPath} fill="url(#areaGradient)" />

        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke={color}
          strokeWidth="0.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {points.length <= 30 &&
          points.map((point, i) => (
            <circle
              key={i}
              cx={point.x}
              cy={point.y}
              r="0.8"
              fill={color}
              className="opacity-0 hover:opacity-100 transition-opacity"
            />
          ))}
      </svg>

      {/* Y-axis labels */}
      {showLabels && (
        <>
          <div className="absolute top-2 left-2 text-xs text-muted-foreground font-mono">
            {maxValue >= 0 ? "+" : ""}
            {maxValue.toFixed(1)}%
          </div>
          <div className="absolute bottom-8 left-2 text-xs text-muted-foreground font-mono">
            {minValue >= 0 ? "+" : ""}
            {minValue.toFixed(1)}%
          </div>
        </>
      )}

      {/* X-axis labels */}
      {showLabels && data.length > 0 && (
        <div className="absolute bottom-1 left-0 right-0 flex justify-between px-2">
          <span className="text-xs text-muted-foreground">
            {formatDate(data[0].timestamp)}
          </span>
          <span className="text-xs text-muted-foreground">
            {formatDate(data[data.length - 1].timestamp)}
          </span>
        </div>
      )}
    </div>
  );
}

function formatDate(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/**
 * Mini sparkline chart for inline display
 */
interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  positive?: boolean;
  className?: string;
}

export function Sparkline({
  data,
  width = 80,
  height = 24,
  positive,
  className,
}: SparklineProps) {
  const path = useMemo(() => {
    if (!data || data.length < 2) return "";

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((value, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((value - min) / range) * height * 0.8 - height * 0.1;
      return `${x},${y}`;
    });

    return `M ${points.join(" L ")}`;
  }, [data, width, height]);

  if (!data || data.length < 2) {
    return <div className={cn("bg-muted/30 rounded", className)} style={{ width, height }} />;
  }

  const isPositive = positive ?? data[data.length - 1] >= data[0];
  const color = isPositive ? "var(--profit)" : "var(--loss)";

  return (
    <svg width={width} height={height} className={className}>
      <path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
