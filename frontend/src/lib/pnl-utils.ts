/**
 * 盈亏(PnL)统一格式化工具
 * 用于所有盈亏相关的显示，确保视觉一致性
 */



// ==================== 类型定义 ====================

export type PnLTrend = "profit" | "loss" | "neutral";

export interface PnLValue {
  /** 盈亏金额 */
  amount: number;
  /** 盈亏百分比 (可选) */
  percent?: number;
}

export interface PnLDisplayOptions {
  /** 显示正负符号 */
  showSign?: boolean;
  /** 显示百分比 */
  showPercent?: boolean;
  /** 货币小数位 */
  decimals?: number;
  /** 百分比小数位 */
  percentDecimals?: number;
}

// ==================== 格式化函数 ====================

/**
 * 格式化盈亏金额
 * @param value - 盈亏金额
 * @param showSign - 是否显示 +/- 符号，默认 true
 * @param decimals - 小数位数，默认 2
 */
export function formatPnL(value: number, showSign = true, decimals = 2): string {
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(Math.abs(value));

  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return formatted;
}

/**
 * 格式化盈亏百分比
 * @param value - 百分比值 (如 5.5 表示 5.5%)
 * @param showSign - 是否显示 +/- 符号，默认 true
 * @param decimals - 小数位数，默认 2
 */
export function formatPnLPercent(value: number, showSign = true, decimals = 2): string {
  const formatted = `${Math.abs(value).toFixed(decimals)}%`;
  if (showSign && value !== 0) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return formatted;
}

// ==================== 趋势与颜色工具 ====================

/**
 * 获取盈亏趋势
 * @param value - 盈亏金额
 * @param threshold - 阈值，默认 0
 */
export function getPnLTrend(value: number, threshold = 0): PnLTrend {
  if (value > threshold) return "profit";
  if (value < -threshold) return "loss";
  return "neutral";
}

/**
 * 获取盈亏颜色类名
 * @param value - 盈亏金额
 * @param threshold - 阈值，默认 0
 */
export function getPnLColor(value: number, threshold = 0): string {
  const trend = getPnLTrend(value, threshold);
  switch (trend) {
    case "profit":
      return "text-[var(--profit)]";
    case "loss":
      return "text-[var(--loss)]";
    default:
      return "text-muted-foreground";
  }
}

/**
 * 获取盈亏趋势图标类型
 * @param value - 盈亏金额
 */
export function getPnLIconType(value: number): "up" | "down" | "neutral" {
  const trend = getPnLTrend(value);
  switch (trend) {
    case "profit":
      return "up";
    case "loss":
      return "down";
    default:
      return "neutral";
  }
}

// ==================== 组合格式化 ====================

/**
 * 格式化盈亏显示对象 (金额 + 百分比)
 */
export function formatPnLDisplay(
  value: PnLValue,
  options: PnLDisplayOptions = {}
): { amount: string; percent?: string; color: string; trend: PnLTrend } {
  const { showSign = true, showPercent = false, decimals = 2, percentDecimals = 2 } = options;

  const trend = getPnLTrend(value.amount);

  return {
    amount: formatPnL(value.amount, showSign, decimals),
    percent:
      showPercent && value.percent !== undefined
        ? formatPnLPercent(value.percent, showSign, percentDecimals)
        : undefined,
    color: getPnLColor(value.amount),
    trend,
  };
}

/**
 * 格式化价格（不带货币符号）
 * @param value - 价格
 * @param decimals - 小数位数，默认 2
 */
export function formatPrice(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * 格式化持续时间
 * @param minutes - 分钟数
 */
export function formatDuration(minutes: number): string {
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
