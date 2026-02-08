/**
 * Decisions Hooks
 *
 * SWR hooks for AI decision data fetching.
 */

import useSWR from 'swr';
import { decisionsApi } from '@/lib/api';
import type { DecisionResponse, PaginatedDecisionResponse, DecisionStatsResponse } from '@/lib/api';

// Keys
const DECISIONS_RECENT_KEY = '/decisions/recent';
const DECISIONS_STATS_KEY = '/decisions/stats';
const decisionKey = (id: string) => `/decisions/${id}`;
const strategyDecisionsKey = (strategyId: string) => `/decisions/strategy/${strategyId}`;

/**
 * Fetch recent decisions
 */
export function useRecentDecisions(limit: number = 20) {
  return useSWR<DecisionResponse[]>(
    [DECISIONS_RECENT_KEY, limit],
    () => decisionsApi.listRecent(limit),
    {
      refreshInterval: 60000, // Refresh every minute
      revalidateOnFocus: true,
    }
  );
}

/**
 * Fetch decisions for a specific strategy (paginated)
 */
export interface DecisionFilters {
  executionFilter?: "all" | "executed" | "skipped";
  action?: string;
}

export function useStrategyDecisions(
  strategyId: string | null,
  page: number = 1,
  pageSize: number = 10,
  filters: DecisionFilters = {},
) {
  const offset = (page - 1) * pageSize;
  const { executionFilter = "all", action } = filters;
  return useSWR<PaginatedDecisionResponse>(
    strategyId ? [strategyDecisionsKey(strategyId), page, pageSize, executionFilter, action ?? ""] : null,
    () => decisionsApi.listByStrategy(strategyId!, pageSize, offset, executionFilter, action),
    {
      refreshInterval: 60000,
      revalidateOnFocus: true,
      keepPreviousData: true,
    }
  );
}

/**
 * Fetch single decision
 */
export function useDecision(id: string | null) {
  return useSWR<DecisionResponse>(
    id ? decisionKey(id) : null,
    () => decisionsApi.get(id!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * Fetch decision statistics
 */
export function useDecisionStats(strategyId?: string) {
  return useSWR<DecisionStatsResponse>(
    strategyId ? [DECISIONS_STATS_KEY, strategyId] : null,
    () => decisionsApi.getStats(strategyId!),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000,
    }
  );
}

/**
 * Get latest decision for a strategy
 */
export function useLatestDecision(strategyId: string | null) {
  const { data } = useStrategyDecisions(strategyId, 1, 1, {});
  return data?.items?.[0] ?? null;
}
