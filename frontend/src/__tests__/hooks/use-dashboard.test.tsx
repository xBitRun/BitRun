/**
 * Tests for useDashboard hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useDashboardStats,
  useAllPositions,
  useAccountsWithBalances,
  usePerformanceStats,
  useActivityFeed,
} from "@/hooks/use-dashboard";
import { dashboardApi, accountsApi, strategiesApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  dashboardApi: {
    getFullStats: jest.fn(),
    getActivity: jest.fn(),
  },
  accountsApi: {
    list: jest.fn(),
    getBalance: jest.fn(),
  },
  strategiesApi: {
    list: jest.fn(),
  },
}));

const mockedDashboardApi = dashboardApi as jest.Mocked<typeof dashboardApi>;
const mockedAccountsApi = accountsApi as jest.Mocked<typeof accountsApi>;
const mockedStrategiesApi = strategiesApi as jest.Mocked<typeof strategiesApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockFullStatsResponse = {
  total_equity: 50000,
  available_balance: 40000,
  unrealized_pnl: 1500,
  daily_pnl: 800,
  daily_pnl_percent: 1.6,
  active_strategies: 3,
  total_strategies: 5,
  open_positions: 4,
  positions: [
    { symbol: "BTC", side: "long", size_usd: 10000, unrealized_pnl: 500, account_name: "Binance", exchange: "binance" },
    { symbol: "ETH", side: "short", size_usd: 5000, unrealized_pnl: -200, account_name: "Binance", exchange: "binance" },
    { symbol: "SOL", side: "long", size_usd: 3000, unrealized_pnl: 300, account_name: "OKX", exchange: "okx" },
    { symbol: "BNB", side: "long", size_usd: 2000, unrealized_pnl: 100, account_name: "OKX", exchange: "okx" },
  ],
  today_decisions: 10,
  today_executed_decisions: 6,
  accounts_connected: 2,
  accounts_total: 3,
};

const mockAccounts = [
  { id: "acc-1", name: "Binance Main", exchange: "binance", is_testnet: false, is_connected: true, has_api_key: true, has_api_secret: true, has_private_key: false, has_passphrase: false, created_at: "2024-01-01", updated_at: "2024-01-01" },
  { id: "acc-2", name: "OKX Test", exchange: "okx", is_testnet: true, is_connected: false, has_api_key: true, has_api_secret: true, has_private_key: false, has_passphrase: false, created_at: "2024-01-02", updated_at: "2024-01-02" },
];

const mockBalance = {
  account_id: "acc-1",
  equity: 25000,
  available_balance: 20000,
  total_margin_used: 5000,
  unrealized_pnl: 750,
  positions: [
    { symbol: "BTC", side: "long" as const, size: 0.5, size_usd: 15000, entry_price: 30000, mark_price: 31500, leverage: 3, unrealized_pnl: 750, unrealized_pnl_percent: 5.0, liquidation_price: 25000 },
  ],
};

const mockStrategies = [
  { id: "s-1", name: "Strategy 1", description: "", prompt: "", trading_mode: "conservative" as const, status: "active" as const, config: {}, total_pnl: 500, total_trades: 20, winning_trades: 12, losing_trades: 8, win_rate: 60, max_drawdown: 0.05, created_at: "2024-01-01", updated_at: "2024-01-01" },
  { id: "s-2", name: "Strategy 2", description: "", prompt: "", trading_mode: "aggressive" as const, status: "paused" as const, config: {}, total_pnl: -100, total_trades: 10, winning_trades: 4, losing_trades: 6, win_rate: 40, max_drawdown: 0.1, created_at: "2024-01-02", updated_at: "2024-01-02" },
  { id: "s-3", name: "Strategy 3", description: "", prompt: "", trading_mode: "conservative" as const, status: "active" as const, config: {}, total_pnl: 300, total_trades: 15, winning_trades: 10, losing_trades: 5, win_rate: 66, max_drawdown: 0.03, created_at: "2024-01-03", updated_at: "2024-01-03" },
];

const mockActivityFeed = {
  items: [
    { id: "a-1", type: "decision" as const, title: "Buy BTC", description: "Opened long", timestamp: "2024-01-01T00:00:00Z", metadata: {} },
  ],
  total: 1,
  has_more: false,
};

describe("useDashboardStats", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch stats from backend endpoint", async () => {
    mockedDashboardApi.getFullStats.mockResolvedValue(mockFullStatsResponse as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDashboardApi.getFullStats).toHaveBeenCalled();
    expect(result.current.data?.totalEquity).toBe(50000);
    expect(result.current.data?.availableBalance).toBe(40000);
    expect(result.current.data?.activeStrategies).toBe(3);
    expect(result.current.data?.connectedAccounts).toBe(2);
  });

  it("should return positions alongside stats from backend response", async () => {
    mockedDashboardApi.getFullStats.mockResolvedValue(mockFullStatsResponse as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.positions.length).toBeGreaterThan(0));

    expect(result.current.positions.length).toBe(4);
    expect(result.current.positions[0].symbol).toBeDefined();
    expect(result.current.positions[0].exchange).toBeDefined();
  });

  it("should sort positions by absolute PnL descending", async () => {
    mockedDashboardApi.getFullStats.mockResolvedValue({
      ...mockFullStatsResponse,
      positions: [
        { symbol: "BNB", side: "long", size: 1, size_usd: 2000, entry_price: 300, mark_price: 310, leverage: 1, unrealized_pnl: 100, unrealized_pnl_percent: 5, liquidation_price: null, account_name: "Binance", exchange: "binance" },
        { symbol: "ETH", side: "short", size: 10, size_usd: 20000, entry_price: 2000, mark_price: 1800, leverage: 2, unrealized_pnl: 2000, unrealized_pnl_percent: 10, liquidation_price: 2500, account_name: "OKX", exchange: "okx" },
      ],
    } as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.positions.length).toBe(2));

    // ETH has |2000| > BNB |100|, so ETH should come first
    expect(result.current.positions[0].symbol).toBe("ETH");
    expect(result.current.positions[1].symbol).toBe("BNB");
  });

  it("should count profitable positions from backend response", async () => {
    mockedDashboardApi.getFullStats.mockResolvedValue(mockFullStatsResponse as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    // 3 positions have positive PnL (BTC: 500, SOL: 300, BNB: 100)
    expect(result.current.data?.profitablePositions).toBe(3);
  });

  it("should calculate unrealizedPnlPercent correctly", async () => {
    mockedDashboardApi.getFullStats.mockResolvedValue(mockFullStatsResponse as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    // (1500 / 50000) * 100 = 3
    expect(result.current.data?.unrealizedPnlPercent).toBe(3);
  });

  it("should fallback to client-side aggregation when backend fails", async () => {
    mockedDashboardApi.getFullStats.mockRejectedValue(new Error("Server error"));
    mockedAccountsApi.list.mockResolvedValue(mockAccounts as never);
    mockedStrategiesApi.list.mockResolvedValue(mockStrategies as never);
    mockedAccountsApi.getBalance.mockResolvedValue(mockBalance as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountsApi.list).toHaveBeenCalled();
    expect(mockedStrategiesApi.list).toHaveBeenCalled();
    // Only connected accounts get balance fetched
    expect(mockedAccountsApi.getBalance).toHaveBeenCalledWith("acc-1");
    expect(result.current.data?.totalAccounts).toBe(2);
    expect(result.current.data?.activeStrategies).toBe(2);

    // Positions should also be built from per-account balances in fallback
    expect(result.current.positions.length).toBe(1);
    expect(result.current.positions[0].symbol).toBe("BTC");
    expect(result.current.positions[0].accountName).toBe("Binance Main");
  });

  it("should handle zero equity in fallback for pnl percent", async () => {
    mockedDashboardApi.getFullStats.mockRejectedValue(new Error("fail"));
    mockedAccountsApi.list.mockResolvedValue([]);
    mockedStrategiesApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.unrealizedPnlPercent).toBe(0);
    expect(result.current.data?.totalEquity).toBe(0);
    expect(result.current.positions).toEqual([]);
  });

  it("should return loading state initially", () => {
    mockedDashboardApi.getFullStats.mockReturnValue(new Promise(() => {}) as never);

    const { result } = renderHook(() => useDashboardStats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useAllPositions (deprecated cache-only hook)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return undefined when no cache is populated", () => {
    const { result } = renderHook(() => useAllPositions(), {
      wrapper: createWrapper(),
    });

    // No fetcher, no cache → data should be undefined
    expect(result.current.data).toBeUndefined();
  });
});

describe("useAccountsWithBalances", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return accounts with balances for connected ones", async () => {
    mockedAccountsApi.list.mockResolvedValue(mockAccounts as never);
    mockedAccountsApi.getBalance.mockResolvedValue(mockBalance as never);

    const { result } = renderHook(() => useAccountsWithBalances(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.length).toBe(2);
    // Connected account has balance
    const connected = result.current.data?.find((r) => r.account.id === "acc-1");
    expect(connected?.balance?.equity).toBe(25000);
    // Disconnected account has null balance
    const disconnected = result.current.data?.find((r) => r.account.id === "acc-2");
    expect(disconnected?.balance).toBeNull();
  });

  it("should set error when balance fetch fails", async () => {
    const connected = [{ ...mockAccounts[0], is_connected: true }];
    mockedAccountsApi.list.mockResolvedValue(connected as never);
    mockedAccountsApi.getBalance.mockRejectedValue(new Error("Timeout"));

    const { result } = renderHook(() => useAccountsWithBalances(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.data).toBeDefined();
      expect(result.current.data?.[0].error).toBe("Timeout");
    });

    expect(result.current.data?.[0].balance).toBeNull();
  });
});

describe("usePerformanceStats", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should aggregate performance from all strategies", async () => {
    mockedStrategiesApi.list.mockResolvedValue(mockStrategies as never);

    const { result } = renderHook(() => usePerformanceStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.totalPnl).toBe(700); // 500 + (-100) + 300
    expect(result.current.data?.totalTrades).toBe(45); // 20 + 10 + 15
    expect(result.current.data?.winningTrades).toBe(26); // 12 + 4 + 10
    expect(result.current.data?.losingTrades).toBe(19); // 8 + 6 + 5
    expect(result.current.data?.maxDrawdown).toBe(0.1);
  });

  it("should calculate win rate correctly", async () => {
    mockedStrategiesApi.list.mockResolvedValue(mockStrategies as never);

    const { result } = renderHook(() => usePerformanceStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    // winRate = (26 / 45) * 100 ≈ 57.78
    expect(result.current.data?.winRate).toBeCloseTo(57.78, 1);
  });

  it("should return zero win rate when no trades", async () => {
    mockedStrategiesApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => usePerformanceStats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.winRate).toBe(0);
    expect(result.current.data?.totalTrades).toBe(0);
  });
});

describe("useActivityFeed", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch activity feed with default limit", async () => {
    mockedDashboardApi.getActivity.mockResolvedValue(mockActivityFeed as never);

    const { result } = renderHook(() => useActivityFeed(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDashboardApi.getActivity).toHaveBeenCalledWith(20, 0);
    expect(result.current.data?.items.length).toBe(1);
  });

  it("should fetch activity feed with custom limit", async () => {
    mockedDashboardApi.getActivity.mockResolvedValue(mockActivityFeed as never);

    const { result } = renderHook(() => useActivityFeed(5), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDashboardApi.getActivity).toHaveBeenCalledWith(5, 0);
  });
});
