/**
 * Competition Hooks
 *
 * Fetches leaderboard data for the agent competition and strategy ranking.
 */

import useSWR from "swr";
import { competitionApi } from "@/lib/api";
import type { LeaderboardResponse, StrategyRankingResponse } from "@/lib/api";

export function useLeaderboard(sortBy?: string, order?: string) {
  const { data, error, isLoading, mutate } = useSWR<LeaderboardResponse>(
    ["competition-leaderboard", sortBy, order],
    () => competitionApi.getLeaderboard(sortBy, order),
    {
      refreshInterval: 30000,
      revalidateOnFocus: true,
    }
  );

  return {
    leaderboard: data?.leaderboard ?? [],
    stats: data?.stats ?? null,
    isLoading,
    error,
    mutate,
  };
}

/**
 * Fetch aggregated strategy performance ranking (cross-user public strategies).
 */
export function useStrategyRanking(params?: {
  sort_by?: string;
  type_filter?: string;
  limit?: number;
  offset?: number;
}) {
  const key = params
    ? ["strategy-ranking", params]
    : "strategy-ranking";

  const { data, error, isLoading, mutate } = useSWR<StrategyRankingResponse>(
    key,
    () => competitionApi.getStrategyRanking(params),
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000,
    }
  );

  return {
    rankings: data?.rankings ?? [],
    total: data?.total ?? 0,
    isLoading,
    error,
    mutate,
  };
}
