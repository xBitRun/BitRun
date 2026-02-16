/**
 * Symbols Hooks
 *
 * SWR hooks for fetching trading symbols from exchanges.
 */

import useSWR from "swr";
import { dataApi, type SymbolsResponse, type SymbolItem } from "@/lib/api";
import type { AssetType, ExchangeType } from "@/types";

// Keys
const SYMBOLS_KEY = "/data/symbols";

/**
 * Fetch available trading symbols for an exchange.
 * Returns both base symbol (e.g., 'BTC') and full CCXT format.
 *
 * @param exchange - Exchange name (default: 'binance')
 * @param assetType - Optional asset type filter (crypto_perp, crypto_spot, forex, metals)
 * @param enabled - Whether to enable fetching (default: true)
 */
export function useSymbols(
  exchange?: ExchangeType | string,
  assetType?: AssetType,
  enabled: boolean = true,
) {
  const exchangeValue = exchange || "binance";

  return useSWR<SymbolsResponse>(
    enabled ? [SYMBOLS_KEY, exchangeValue, assetType] : null,
    () => dataApi.getSymbols(exchangeValue, assetType),
    {
      revalidateOnFocus: false,
      dedupingInterval: 300000, // Cache for 5 minutes
      onError: (err) => {
        console.error(`Failed to fetch symbols for ${exchangeValue}:`, err);
      },
    },
  );
}

/**
 * Hook result type for components
 */
export interface UseSymbolsResult {
  symbols: SymbolItem[];
  isLoading: boolean;
  error: Error | undefined;
  mutate: () => void;
}

/**
 * Convenience hook that returns a simpler interface
 *
 * @param exchange - Exchange name (default: 'binance')
 * @param assetType - Optional asset type filter
 */
export function useSymbolsList(
  exchange?: ExchangeType | string,
  assetType?: AssetType,
): UseSymbolsResult {
  const { data, isLoading, error, mutate } = useSymbols(exchange, assetType);

  return {
    symbols: data?.symbols || [],
    isLoading,
    error,
    mutate,
  };
}
