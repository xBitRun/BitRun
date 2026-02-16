/**
 * SymbolSelector Constants
 *
 * Preset symbol lists for fallback and quick selection.
 */

import type { MarketType } from "@/types";

/**
 * Popular crypto symbols for quick selection
 */
export const POPULAR_CRYPTO_SYMBOLS = [
  "BTC",
  "ETH",
  "SOL",
  "BNB",
  "XRP",
  "DOGE",
  "ADA",
  "AVAX",
  "LINK",
  "DOT",
  "MATIC",
  "UNI",
  "ATOM",
  "LTC",
  "APT",
  "ARB",
  "OP",
  "INJ",
  "TIA",
  "SEI",
] as const;

/**
 * Forex symbol pairs
 */
export const FOREX_SYMBOLS = [
  "EUR/USD",
  "GBP/USD",
  "USD/JPY",
  "USD/CHF",
  "AUD/USD",
  "NZD/USD",
  "USD/CAD",
  "EUR/GBP",
  "EUR/JPY",
  "GBP/JPY",
] as const;

/**
 * Metals symbols
 */
export const METALS_SYMBOLS = ["XAU/USD", "XAG/USD"] as const;

/**
 * All preset symbols combined
 */
export const ALL_PRESET_SYMBOLS = [
  ...POPULAR_CRYPTO_SYMBOLS,
  ...FOREX_SYMBOLS,
  ...METALS_SYMBOLS,
] as const;

/**
 * Extract base symbol from CCXT format
 * e.g., "BTC/USDT:USDT" -> "BTC"
 */
export function extractBaseSymbol(fullSymbol: string): string {
  const slashIndex = fullSymbol.indexOf("/");
  if (slashIndex !== -1) {
    return fullSymbol.slice(0, slashIndex);
  }
  return fullSymbol;
}

/**
 * Detect market type from symbol
 * Returns simplified market type for UI grouping
 */
export function detectMarketType(symbol: string): MarketType {
  const upper = symbol.toUpperCase();

  // Check forex
  if (FOREX_SYMBOLS.some((s) => s === upper || s.includes(upper))) {
    return "forex";
  }

  // Check metals
  if (
    METALS_SYMBOLS.some((s) => s === upper || s.includes(upper)) ||
    upper.startsWith("XAU") ||
    upper.startsWith("XAG") ||
    upper.startsWith("XPT") ||
    upper.startsWith("XPD")
  ) {
    return "metals";
  }

  return "crypto_perp";
}
