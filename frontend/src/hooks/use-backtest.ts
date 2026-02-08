/**
 * Backtest Hooks
 * 
 * SWR hooks for backtesting functionality.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { backtestApi } from '@/lib/api';
import type { 
  BacktestRequest, 
  BacktestExchange,
  QuickBacktestRequest, 
  BacktestResponse 
} from '@/lib/api';

// Keys
const BACKTEST_SYMBOLS_KEY = '/backtest/symbols';

/**
 * Run backtest mutation
 */
export function useRunBacktest() {
  return useSWRMutation<BacktestResponse, Error, string, BacktestRequest>(
    '/backtest/run',
    async (_, { arg }) => {
      return backtestApi.run(arg);
    }
  );
}

/**
 * Run quick backtest mutation
 */
export function useQuickBacktest() {
  return useSWRMutation<BacktestResponse, Error, string, QuickBacktestRequest>(
    '/backtest/quick',
    async (_, { arg }) => {
      return backtestApi.quick(arg);
    }
  );
}

/**
 * Fetch available symbols for backtesting
 */
export function useBacktestSymbols(exchange: string = 'hyperliquid') {
  return useSWR<{ symbols: Array<{ symbol: string; full_symbol: string }> }>(
    [BACKTEST_SYMBOLS_KEY, exchange],
    () => backtestApi.getSymbols(exchange),
    {
      revalidateOnFocus: false,
      dedupingInterval: 300000, // Cache for 5 minutes
    }
  );
}
