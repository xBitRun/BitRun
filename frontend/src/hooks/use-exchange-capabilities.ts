/**
 * Exchange Capabilities Hooks
 *
 * SWR hooks for fetching exchange capabilities and filtering by asset type.
 */

import useSWR from "swr";
import { dataApi } from "@/lib/api";
import type {
  AssetType,
  ExchangeCapabilities,
  SettlementCurrency,
} from "@/types";

// Keys
const EXCHANGES_KEY = "/data/exchanges";

/**
 * Fetch all exchange capabilities.
 * Returns information about supported exchanges including asset types,
 * settlement currencies, features, and limits.
 */
export function useExchangeCapabilities() {
  const { data, error, isLoading, mutate } = useSWR(
    EXCHANGES_KEY,
    () => dataApi.getExchanges(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 600000, // Cache for 10 minutes
      onError: (err) => {
        console.error("Failed to fetch exchange capabilities:", err);
      },
    },
  );

  return {
    exchanges: data?.exchanges || [],
    lastUpdated: data?.last_updated,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Fetch capabilities for a specific exchange.
 *
 * @param exchangeId - Exchange identifier (e.g., 'hyperliquid', 'binance')
 * @param enabled - Whether to enable fetching (default: true)
 */
export function useExchangeCapability(
  exchangeId?: string,
  enabled: boolean = true,
) {
  const { exchanges, isLoading, error } = useExchangeCapabilities();

  const exchange = exchangeId
    ? exchanges.find((e) => e.id === exchangeId.toLowerCase())
    : undefined;

  return {
    exchange,
    isLoading,
    error,
    // Derived values
    supportedAssets: exchange?.supported_assets || [],
    defaultSettlement: exchange?.default_settlement || "USDT",
    maxLeverage: exchange?.max_leverage || 100,
  };
}

/**
 * Get exchanges filtered by asset type.
 *
 * @param assetType - Asset type to filter by (optional)
 */
export function useExchangesForAsset(assetType?: AssetType) {
  const { exchanges, isLoading, error, mutate } = useExchangeCapabilities();

  const filtered = assetType
    ? exchanges.filter((e) => e.supported_assets.includes(assetType))
    : exchanges;

  return {
    exchanges: filtered,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Get settlement currency for a specific exchange and asset type.
 *
 * @param exchangeId - Exchange identifier
 * @param assetType - Asset type (default: 'crypto_perp')
 */
export function useSettlementCurrency(
  exchangeId?: string,
  assetType: AssetType = "crypto_perp",
): {
  settlement: SettlementCurrency;
  isLoading: boolean;
} {
  const { exchange, isLoading } = useExchangeCapability(exchangeId);

  if (!exchange) {
    return { settlement: "USDT" as SettlementCurrency, isLoading };
  }

  const settlement =
    exchange.settlement_currencies[assetType] || exchange.default_settlement;

  return { settlement, isLoading };
}

/**
 * Check if an exchange supports a specific asset type.
 *
 * @param exchangeId - Exchange identifier
 * @param assetType - Asset type to check
 */
export function useSupportsAsset(
  exchangeId?: string,
  assetType?: AssetType,
): {
  supports: boolean;
  isLoading: boolean;
} {
  const { exchange, isLoading } = useExchangeCapability(exchangeId);

  if (!exchange || !assetType) {
    return { supports: false, isLoading };
  }

  return {
    supports: exchange.supported_assets.includes(assetType),
    isLoading,
  };
}

/**
 * Validate if a strategy's symbols are compatible with an exchange.
 * This checks if the exchange supports the asset types of the strategy's symbols.
 *
 * @param exchangeId - Exchange identifier
 * @param symbols - Strategy symbols (e.g., ['BTC/USDT:USDT', 'ETH/USDC:USDC'])
 */
export function useStrategyExchangeCompatibility(
  exchangeId?: string,
  symbols?: string[],
): {
  isCompatible: boolean;
  incompatibleSymbols: string[];
  isLoading: boolean;
} {
  const { exchange, isLoading } = useExchangeCapability(exchangeId);

  if (!exchange || !symbols || symbols.length === 0) {
    return {
      isCompatible: true,
      incompatibleSymbols: [],
      isLoading,
    };
  }

  // Get expected settlement currency for this exchange
  const expectedSettlement = exchange.default_settlement;

  // Check each symbol
  const incompatibleSymbols = symbols.filter((symbol) => {
    // Extract settlement from symbol (e.g., 'BTC/USDT:USDT' -> 'USDT')
    const match = symbol.match(/\/(\w+):/);
    const symbolSettlement = match ? match[1] : null;

    // Symbol is incompatible if settlement doesn't match
    return symbolSettlement && symbolSettlement !== expectedSettlement;
  });

  return {
    isCompatible: incompatibleSymbols.length === 0,
    incompatibleSymbols,
    isLoading,
  };
}
