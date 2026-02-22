/**
 * 盈亏(PnL)组件模块
 * 提供统一的盈亏显示组件和工具函数
 */

// 组件
export { PnLValue, PnLCell, PnLBadge, PnLSummary, usePnLStyles } from "./pnl-display";

// 工具函数
export {
  formatPnL,
  formatPnLPercent,
  getPnLTrend,
  getPnLColor,
  getPnLIconType,
  formatPnLDisplay,
  formatPrice,
  formatDuration,
  type PnLTrend,
  type PnLValue as PnLValueType,
  type PnLDisplayOptions,
} from "@/lib/pnl-utils";
