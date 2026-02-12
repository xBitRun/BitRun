/**
 * Competition Hooks
 *
 * Fetches leaderboard data for the AI competition mode.
 */

import useSWR from "swr";
import { competitionApi } from "@/lib/api";
import type { LeaderboardResponse } from "@/lib/api";

export function useLeaderboard(sortBy?: string, order?: string) {
  const { data, error, isLoading, mutate } = useSWR<LeaderboardResponse>(
    ["competition-leaderboard", sortBy, order],
    () => competitionApi.getLeaderboard(sortBy, order),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
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
