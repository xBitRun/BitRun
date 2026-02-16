/**
 * SymbolSelector Types
 *
 * Type definitions for the unified symbol selector component.
 */

import type { AssetType, MarketType, ExchangeType } from "@/types";

/**
 * Selection mode for the symbol selector
 */
export type SymbolSelectorMode = "single" | "multiple";

/**
 * Individual symbol option
 */
export interface SymbolOption {
  /** Base symbol (e.g., 'BTC') */
  symbol: string;
  /** Full CCXT symbol (e.g., 'BTC/USDT:USDT') */
  fullSymbol: string;
  /** Market type (crypto/forex/metals) */
  marketType?: MarketType;
}

/**
 * Props for the SymbolSelector component
 */
export interface SymbolSelectorProps {
  // ===== Core Value Control =====
  /** Selected symbol(s) - base symbols like "BTC", "ETH" */
  value: string | string[];
  /** Change handler - receives base symbols */
  onChange: (value: string | string[]) => void;

  // ===== Selection Mode =====
  /** Single or multi-select mode */
  mode?: SymbolSelectorMode;
  /** Maximum selections in multiple mode (default: 10) */
  maxSelections?: number;

  // ===== Exchange Awareness =====
  /**
   * Exchange filter - when provided, shows only symbols from this exchange.
   * If not provided, shows symbols from preset list.
   */
  exchange?: ExchangeType | string;

  /**
   * Asset type filter - when provided with exchange, filters symbols by asset type.
   * Also determines the settlement currency (USDT vs USDC).
   * Default: 'crypto_perp'
   */
  assetType?: AssetType;

  // ===== UI Customization =====
  /** Show market type tabs (crypto/forex/metals) - default: true */
  showMarketTypeTabs?: boolean;
  /** Placeholder text for the trigger button */
  placeholder?: string;
  /** Disable the selector */
  disabled?: boolean;
  /** Size variant */
  size?: "sm" | "md" | "lg";
  /** Additional class names */
  className?: string;

  // ===== Behavior =====
  /** Allow custom symbol input - default: true */
  allowCustomInput?: boolean;
  /** Show "popular" quick-select buttons - default: false (use search instead) */
  showPopularSymbols?: boolean;
}
