/**
 * SymbolSelector Component Exports
 */

export { SymbolSelector } from "./symbol-selector";
export type {
  SymbolSelectorProps,
  SymbolSelectorMode,
  SymbolOption,
} from "./types";

// Re-export utilities
export {
  POPULAR_CRYPTO_SYMBOLS,
  FOREX_SYMBOLS,
  METALS_SYMBOLS,
  extractBaseSymbol,
  detectMarketType,
} from "./constants";
