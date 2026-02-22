"use client";

import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  formatPnL,
  formatPnLPercent,
  getPnLTrend,
  type PnLTrend,
} from "@/lib/pnl-utils";

// ==================== PnLValue 组件 ====================

interface PnLValueProps {
  /** 盈亏金额 */
  value: number;
  /** 盈亏百分比 (可选) */
  percent?: number;
  /** 显示模式 */
  mode?: "amount" | "percent" | "both";
  /** 显示 +/- 符号 */
  showSign?: boolean;
  /** 金额小数位 */
  decimals?: number;
  /** 百分比小数位 */
  percentDecimals?: number;
  /** 自定义类名 */
  className?: string;
  /** 金额类名 */
  amountClassName?: string;
  /** 百分比类名 */
  percentClassName?: string;
  /** 显示趋势图标 */
  showTrendIcon?: boolean;
  /** 图标位置 */
  iconPosition?: "left" | "right";
  /** 字体大小 */
  size?: "xs" | "sm" | "md" | "lg" | "xl";
  /** 字重 */
  weight?: "normal" | "medium" | "semibold" | "bold";
}

const sizeClasses: Record<NonNullable<PnLValueProps["size"]>, string> = {
  xs: "text-xs",
  sm: "text-sm",
  md: "text-base",
  lg: "text-lg",
  xl: "text-xl",
};

const weightClasses: Record<NonNullable<PnLValueProps["weight"]>, string> = {
  normal: "font-normal",
  medium: "font-medium",
  semibold: "font-semibold",
  bold: "font-bold",
};

const iconSizes: Record<NonNullable<PnLValueProps["size"]>, string> = {
  xs: "w-2.5 h-2.5",
  sm: "w-3 h-3",
  md: "w-3.5 h-3.5",
  lg: "w-4 h-4",
  xl: "w-5 h-5",
};

/**
 * 统一盈亏数值显示组件
 * 自动处理颜色、图标、格式化
 */
export function PnLValue({
  value,
  percent,
  mode = "amount",
  showSign = true,
  decimals = 2,
  percentDecimals = 2,
  className,
  amountClassName,
  percentClassName,
  showTrendIcon = false,
  iconPosition = "left",
  size = "md",
  weight = "medium",
}: PnLValueProps) {
  const trend = getPnLTrend(value);

  const TrendIcon =
    trend === "profit" ? TrendingUp : trend === "loss" ? TrendingDown : Minus;

  const trendColor =
    trend === "profit"
      ? "text-[var(--profit)]"
      : trend === "loss"
        ? "text-[var(--loss)]"
        : "text-muted-foreground";

  const renderAmount = () => (
    <span className={cn("font-mono", trendColor, amountClassName)}>
      {formatPnL(value, showSign, decimals)}
    </span>
  );

  const renderPercent = () =>
    percent !== undefined && (
      <span className={cn("font-mono", trendColor, percentClassName)}>
        {formatPnLPercent(percent, showSign, percentDecimals)}
      </span>
    );

  const renderIcon = () =>
    showTrendIcon && (
      <TrendIcon className={cn(trendColor, iconSizes[size])} />
    );

  if (mode === "percent") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1",
          sizeClasses[size],
          weightClasses[weight],
          className
        )}
      >
        {iconPosition === "left" && renderIcon()}
        {renderPercent()}
        {iconPosition === "right" && renderIcon()}
      </span>
    );
  }

  if (mode === "both") {
    return (
      <span
        className={cn(
          "inline-flex items-center gap-1.5",
          sizeClasses[size],
          weightClasses[weight],
          className
        )}
      >
        {iconPosition === "left" && renderIcon()}
        {renderAmount()}
        {percent !== undefined && (
          <span className="text-muted-foreground text-xs">
            ({renderPercent()})
          </span>
        )}
        {iconPosition === "right" && renderIcon()}
      </span>
    );
  }

  // mode === "amount"
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1",
        sizeClasses[size],
        weightClasses[weight],
        className
      )}
    >
      {iconPosition === "left" && renderIcon()}
      {renderAmount()}
      {iconPosition === "right" && renderIcon()}
    </span>
  );
}

// ==================== PnLCell 组件 (表格单元格用) ====================

interface PnLCellProps extends Omit<PnLValueProps, "className"> {
  /** 表格对齐 */
  align?: "left" | "right";
  /** 自定义类名 */
  className?: string;
}

/**
 * 表格单元格专用盈亏组件
 * 预设右对齐 + mono 字体
 */
export function PnLCell({ align = "right", className, ...props }: PnLCellProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1",
        align === "right" && "justify-end",
        className
      )}
    >
      <PnLValue {...props} />
    </div>
  );
}

// ==================== PnLBadge 组件 ====================

interface PnLBadgeProps {
  /** 盈亏金额 */
  value: number;
  /** 标签文本 */
  label?: string;
  /** 显示 +/- 符号 */
  showSign?: boolean;
  /** 小数位 */
  decimals?: number;
  /** 自定义类名 */
  className?: string;
  /** 尺寸 */
  size?: "sm" | "md";
}

/**
 * 盈亏徽章组件 (带背景色)
 */
export function PnLBadge({
  value,
  label,
  showSign = true,
  decimals = 2,
  className,
  size = "md",
}: PnLBadgeProps) {
  const trend = getPnLTrend(value);

  const bgClass =
    trend === "profit"
      ? "bg-profit/10 text-[var(--profit)] border-profit/20"
      : trend === "loss"
        ? "bg-loss/10 text-[var(--loss)] border-loss/20"
        : "bg-muted/50 text-muted-foreground border-muted/20";

  const sizeClass = size === "sm" ? "px-1.5 py-0.5 text-xs" : "px-2 py-1 text-sm";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded border font-mono",
        bgClass,
        sizeClass,
        className
      )}
    >
      {label && <span className="opacity-70">{label}</span>}
      {formatPnL(value, showSign, decimals)}
    </span>
  );
}

// ==================== PnLSummary 组件 ====================

interface PnLSummaryProps {
  /** 主要数值 */
  value: number;
  /** 百分比 */
  percent?: number;
  /** 标题 */
  title?: string;
  /** 副标题 */
  subtitle?: string;
  /** 图标 */
  icon?: React.ReactNode;
  /** 显示模式 */
  mode?: "amount" | "percent" | "both";
  /** 显示符号 */
  showSign?: boolean;
  /** 自定义类名 */
  className?: string;
}

/**
 * 盈亏汇总显示组件
 * 适用于卡片式汇总显示
 */
export function PnLSummary({
  value,
  percent,
  title,
  subtitle,
  icon,
  mode = "amount",
  showSign = true,
  className,
}: PnLSummaryProps) {
  const trend = getPnLTrend(value);
  const trendColor =
    trend === "profit"
      ? "text-[var(--profit)]"
      : trend === "loss"
        ? "text-[var(--loss)]"
        : "text-muted-foreground";

  const TrendIcon =
    trend === "profit" ? TrendingUp : trend === "loss" ? TrendingDown : Minus;

  return (
    <div className={cn("flex flex-col", className)}>
      {title && (
        <span className="text-sm text-muted-foreground flex items-center gap-2 mb-1">
          {icon}
          {title}
        </span>
      )}
      <div className="flex items-center gap-2">
        <TrendIcon className={cn("w-5 h-5", trendColor)} />
        {mode === "percent" && percent !== undefined ? (
          <span className={cn("text-2xl font-bold font-mono", trendColor)}>
            {formatPnLPercent(percent, showSign)}
          </span>
        ) : mode === "both" && percent !== undefined ? (
          <div className="flex flex-col">
            <span className={cn("text-2xl font-bold font-mono", trendColor)}>
              {formatPnL(value, showSign)}
            </span>
            <span className={cn("text-sm font-mono", trendColor)}>
              {formatPnLPercent(percent, showSign)}
            </span>
          </div>
        ) : (
          <span className={cn("text-2xl font-bold font-mono", trendColor)}>
            {formatPnL(value, showSign)}
          </span>
        )}
      </div>
      {subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
    </div>
  );
}

// ==================== Helper Hook ====================

/**
 * 获取盈亏相关的样式类名
 */
export function usePnLStyles(value: number) {
  const trend = getPnLTrend(value);
  const color =
    trend === "profit"
      ? "text-[var(--profit)]"
      : trend === "loss"
        ? "text-[var(--loss)]"
        : "text-muted-foreground";

  const bgColor =
    trend === "profit"
      ? "bg-profit/10"
      : trend === "loss"
        ? "bg-loss/10"
        : "bg-muted/50";

  const borderColor =
    trend === "profit"
      ? "border-profit/20"
      : trend === "loss"
        ? "border-loss/20"
        : "border-muted/20";

  const IconComponent =
    trend === "profit" ? TrendingUp : trend === "loss" ? TrendingDown : Minus;

  return {
    trend,
    color,
    bgColor,
    borderColor,
    IconComponent,
    isProfit: trend === "profit",
    isLoss: trend === "loss",
    isNeutral: trend === "neutral",
  };
}
