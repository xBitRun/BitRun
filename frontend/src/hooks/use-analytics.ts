/**
 * Analytics Hooks
 *
 * SWR hooks for P&L and performance analytics data.
 */

import { useState, useCallback } from "react";
import useSWR from "swr";
import { analyticsApi, type SyncSnapshotResponse } from "@/lib/api/endpoints";

// ==================== Agent P&L ====================

export interface UseAgentPnLOptions {
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
}

export function useAgentPnL(
  agentId: string | null | undefined,
  options?: UseAgentPnLOptions,
) {
  const { data, error, isLoading, mutate } = useSWR(
    agentId ? [`/analytics/agents/${agentId}/pnl`, options] : null,
    () => analyticsApi.getAgentPnL(agentId!, options),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    },
  );

  return {
    data,
    summary: data?.summary,
    trades: data?.trades ?? [],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}

// ==================== Account Agents Performance ====================

export function useAccountAgents(accountId: string | null | undefined) {
  const { data, error, isLoading, mutate } = useSWR(
    accountId ? `/analytics/accounts/${accountId}/agents` : null,
    () => analyticsApi.getAccountAgents(accountId!),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    },
  );

  return {
    agents: data?.agents ?? [],
    total: data?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}

// ==================== Equity Curve ====================

export interface UseEquityCurveOptions {
  startDate?: string;
  endDate?: string;
  granularity?: "day" | "week" | "month";
}

export function useEquityCurve(
  accountId: string | null | undefined,
  options?: UseEquityCurveOptions,
) {
  const { data, error, isLoading, mutate } = useSWR(
    accountId
      ? [`/analytics/accounts/${accountId}/equity-curve`, options]
      : null,
    () => analyticsApi.getEquityCurve(accountId!, options),
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000,
    },
  );

  return {
    dataPoints: data?.data_points ?? [],
    startDate: data?.start_date,
    endDate: data?.end_date,
    granularity: data?.granularity,
    error,
    isLoading,
    mutate,
  };
}

// ==================== Account P&L Summary ====================

export function useAccountPnL(accountId: string | null | undefined) {
  const { data, error, isLoading, mutate } = useSWR(
    accountId ? `/analytics/accounts/${accountId}/pnl` : null,
    () => analyticsApi.getAccountPnL(accountId!),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    },
  );

  return {
    data,
    error,
    isLoading,
    mutate,
  };
}

// ==================== Sync Account Snapshot ====================

export function useSyncAccount(accountId: string | null | undefined) {
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncError, setSyncError] = useState<Error | null>(null);

  const sync = useCallback(async (): Promise<SyncSnapshotResponse | null> => {
    if (!accountId) return null;

    setIsSyncing(true);
    setSyncError(null);

    try {
      const result = await analyticsApi.syncAccount(accountId);
      return result;
    } catch (err) {
      setSyncError(err instanceof Error ? err : new Error("Sync failed"));
      return null;
    } finally {
      setIsSyncing(false);
    }
  }, [accountId]);

  return {
    sync,
    isSyncing,
    syncError,
  };
}
