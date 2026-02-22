/**
 * Backtest Hooks
 *
 * SWR hooks for backtesting functionality.
 */

import * as React from "react";
import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { backtestApi } from "@/lib/api";
import type {
  BacktestRequest,
  QuickBacktestRequest,
  BacktestResponse,
  BacktestListResponse,
  BacktestDetailResponse,
} from "@/lib/api";

// Keys
const BACKTEST_SYMBOLS_KEY = "/backtest/symbols";
const BACKTESTS_KEY = "/backtests";

/**
 * Run backtest mutation
 */
export function useRunBacktest() {
  return useSWRMutation<BacktestResponse, Error, string, BacktestRequest>(
    "/backtest/run",
    async (_, { arg }) => {
      return backtestApi.run(arg);
    },
  );
}

/**
 * Run quick backtest mutation
 */
export function useQuickBacktest() {
  return useSWRMutation<BacktestResponse, Error, string, QuickBacktestRequest>(
    "/backtest/quick",
    async (_, { arg }) => {
      return backtestApi.quick(arg);
    },
  );
}

/**
 * Fetch available symbols for backtesting
 */
export function useBacktestSymbols(exchange: string = "hyperliquid") {
  return useSWR<{ symbols: Array<{ symbol: string; full_symbol: string }> }>(
    [BACKTEST_SYMBOLS_KEY, exchange],
    () => backtestApi.getSymbols(exchange),
    {
      revalidateOnFocus: false,
      dedupingInterval: 300000, // Cache for 5 minutes
    },
  );
}

// =============================================================================
// Persisted Backtest Records
// =============================================================================

/**
 * Fetch paginated list of backtest records
 */
export function useBacktests(limit: number = 20, offset: number = 0) {
  return useSWR<BacktestListResponse>(
    [BACKTESTS_KEY, limit, offset],
    () => backtestApi.list(limit, offset),
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000, // Cache for 10 seconds
    },
  );
}

/**
 * Fetch a single backtest record by ID
 */
export function useBacktest(id: string | null) {
  return useSWR<BacktestDetailResponse>(
    id ? `${BACKTESTS_KEY}/${id}` : null,
    () => backtestApi.get(id!),
    {
      revalidateOnFocus: false,
    },
  );
}

/**
 * Create backtest and save mutation
 */
export function useCreateBacktest() {
  return useSWRMutation<BacktestDetailResponse, Error, string, BacktestRequest>(
    BACKTESTS_KEY,
    async (_, { arg }) => {
      return backtestApi.create(arg);
    },
  );
}

/**
 * Delete backtest record mutation
 * Returns deletingId to track which specific item is being deleted
 */
export function useDeleteBacktest() {
  const [deletingId, setDeletingId] = React.useState<string | null>(null);

  const mutation = useSWRMutation<void, Error, string, string>(
    BACKTESTS_KEY,
    async (_, { arg }) => {
      return backtestApi.delete(arg);
    },
  );

  const trigger = async (id: string) => {
    setDeletingId(id);
    try {
      await mutation.trigger(id);
    } finally {
      setDeletingId(null);
    }
  };

  return {
    trigger,
    deletingId,
    isMutating: mutation.isMutating,
  };
}
