/**
 * Tests for use-competition hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useLeaderboard, useStrategyRanking } from "@/hooks/use-competition";
import { competitionApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  competitionApi: {
    getLeaderboard: jest.fn(),
    getStrategyRanking: jest.fn(),
  },
}));

const mockedCompetitionApi = competitionApi as jest.Mocked<typeof competitionApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockLeaderboardResponse = {
  leaderboard: [
    {
      agent_id: "agent-1",
      agent_name: "Top Trader",
      strategy_id: "strategy-1",
      strategy_name: "Momentum Strategy",
      strategy_type: "momentum",
      status: "active",
      execution_mode: "live",
      ai_model: "deepseek:chat",
      total_pnl: 10000,
      total_pnl_percent: 50.5,
      win_rate: 75,
      total_trades: 100,
      max_drawdown: 5,
      rank: 1,
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      agent_id: "agent-2",
      agent_name: "Second Best",
      strategy_id: "strategy-2",
      strategy_name: "Grid Strategy",
      strategy_type: "grid",
      status: "active",
      execution_mode: "live",
      ai_model: "gpt-4",
      total_pnl: 8000,
      total_pnl_percent: 40,
      win_rate: 65,
      total_trades: 80,
      max_drawdown: 8,
      rank: 2,
      created_at: "2024-01-02T00:00:00Z",
    },
    {
      agent_id: "agent-3",
      agent_name: "Third Place",
      strategy_id: "strategy-3",
      strategy_name: "DCA Strategy",
      strategy_type: "dca",
      status: "paused",
      execution_mode: "mock",
      ai_model: null,
      total_pnl: 5000,
      total_pnl_percent: 25,
      win_rate: 55,
      total_trades: 50,
      max_drawdown: 10,
      rank: 3,
      created_at: "2024-01-03T00:00:00Z",
    },
  ],
  stats: {
    total_agents: 50,
    active_agents: 30,
    best_performer: "Top Trader",
    best_pnl: 10000,
    worst_pnl: -500,
    avg_win_rate: 55,
    total_trades: 1000,
  },
};

const mockStrategyRankingResponse = {
  rankings: [
    {
      strategy_id: "strategy-1",
      strategy_name: "Momentum Master",
      strategy_type: "momentum",
      author_name: "ProTrader",
      description: "High momentum trading",
      symbols: ["BTC", "ETH"],
      fork_count: 100,
      agent_count: 50,
      avg_pnl: 5000,
      total_pnl: 250000,
      avg_win_rate: 70,
      best_pnl: 20000,
      total_trades: 5000,
      rank: 1,
    },
    {
      strategy_id: "strategy-2",
      strategy_name: "Grid Bot",
      strategy_type: "grid",
      author_name: "GridMaster",
      description: "Automated grid trading",
      symbols: ["SOL", "AVAX"],
      fork_count: 80,
      agent_count: 40,
      avg_pnl: 3000,
      total_pnl: 120000,
      avg_win_rate: 60,
      best_pnl: 15000,
      total_trades: 4000,
      rank: 2,
    },
  ],
  total: 100,
};

describe("useLeaderboard", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch leaderboard data", async () => {
    mockedCompetitionApi.getLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.leaderboard).toBeDefined());

    expect(mockedCompetitionApi.getLeaderboard).toHaveBeenCalledWith(undefined, undefined);
    expect(result.current.leaderboard).toEqual(mockLeaderboardResponse.leaderboard);
    expect(result.current.leaderboard.length).toBe(3);
  });

  it("should pass sort params to API", async () => {
    mockedCompetitionApi.getLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    const { result } = renderHook(() => useLeaderboard("total_pnl", "desc"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.leaderboard).toBeDefined());

    expect(mockedCompetitionApi.getLeaderboard).toHaveBeenCalledWith("total_pnl", "desc");
  });

  it("should return stats data", async () => {
    mockedCompetitionApi.getLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.stats).toBeDefined());

    expect(result.current.stats).toEqual(mockLeaderboardResponse.stats);
    expect(result.current.stats?.total_agents).toBe(50);
    expect(result.current.stats?.active_agents).toBe(30);
    expect(result.current.stats?.best_performer).toBe("Top Trader");
  });

  it("should return empty leaderboard on error", async () => {
    mockedCompetitionApi.getLeaderboard.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.leaderboard).toEqual([]);
    expect(result.current.stats).toBeNull();
  });

  it("should expose isLoading state", async () => {
    mockedCompetitionApi.getLeaderboard.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("should expose mutate function", async () => {
    mockedCompetitionApi.getLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.leaderboard).toBeDefined());

    expect(result.current.mutate).toBeInstanceOf(Function);
  });

  it("should return first ranked agent correctly", async () => {
    mockedCompetitionApi.getLeaderboard.mockResolvedValue(mockLeaderboardResponse);

    const { result } = renderHook(() => useLeaderboard(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.leaderboard).toBeDefined());

    expect(result.current.leaderboard[0].rank).toBe(1);
    expect(result.current.leaderboard[0].agent_name).toBe("Top Trader");
    expect(result.current.leaderboard[0].total_pnl).toBe(10000);
  });
});

describe("useStrategyRanking", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch strategy ranking data", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue(mockStrategyRankingResponse);

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(mockedCompetitionApi.getStrategyRanking).toHaveBeenCalledWith(undefined);
    expect(result.current.rankings).toEqual(mockStrategyRankingResponse.rankings);
    expect(result.current.rankings.length).toBe(2);
  });

  it("should pass filter params to API", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue(mockStrategyRankingResponse);

    const params = {
      sort_by: "avg_pnl",
      type_filter: "momentum",
      limit: 10,
      offset: 20,
    };

    const { result } = renderHook(() => useStrategyRanking(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(mockedCompetitionApi.getStrategyRanking).toHaveBeenCalledWith(params);
  });

  it("should return total count", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue(mockStrategyRankingResponse);

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(result.current.total).toBe(100);
  });

  it("should return empty rankings on error", async () => {
    mockedCompetitionApi.getStrategyRanking.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.rankings).toEqual([]);
    expect(result.current.total).toBe(0);
  });

  it("should expose isLoading state", async () => {
    mockedCompetitionApi.getStrategyRanking.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("should expose mutate function", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue(mockStrategyRankingResponse);

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(result.current.mutate).toBeInstanceOf(Function);
  });

  it("should return first ranked strategy correctly", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue(mockStrategyRankingResponse);

    const { result } = renderHook(() => useStrategyRanking(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(result.current.rankings[0].rank).toBe(1);
    expect(result.current.rankings[0].strategy_name).toBe("Momentum Master");
    expect(result.current.rankings[0].fork_count).toBe(100);
    expect(result.current.rankings[0].avg_pnl).toBe(5000);
  });

  it("should handle pagination params", async () => {
    mockedCompetitionApi.getStrategyRanking.mockResolvedValue({
      rankings: mockStrategyRankingResponse.rankings.slice(0, 1),
      total: 100,
    });

    const { result } = renderHook(() => useStrategyRanking({ limit: 1, offset: 0 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.rankings).toBeDefined());

    expect(mockedCompetitionApi.getStrategyRanking).toHaveBeenCalledWith({
      limit: 1,
      offset: 0,
    });
    expect(result.current.rankings.length).toBe(1);
    expect(result.current.total).toBe(100);
  });
});
