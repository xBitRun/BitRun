/**
 * Tests for useBacktest hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useRunBacktest,
  useQuickBacktest,
  useBacktestSymbols,
} from "@/hooks/use-backtest";
import { backtestApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  backtestApi: {
    run: jest.fn(),
    quick: jest.fn(),
    getSymbols: jest.fn(),
  },
}));

const mockedBacktestApi = backtestApi as jest.Mocked<typeof backtestApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockBacktestResponse = {
  strategy_name: "BTC Momentum",
  start_date: "2024-01-01",
  end_date: "2024-06-01",
  initial_balance: 10000,
  final_balance: 12500,
  total_return_percent: 25,
  total_trades: 42,
  winning_trades: 28,
  losing_trades: 14,
  win_rate: 66.7,
  profit_factor: 2.1,
  max_drawdown_percent: 8.5,
  sharpe_ratio: 1.8,
  total_fees: 120,
  equity_curve: [],
  trades: [],
  drawdown_curve: [],
  monthly_returns: [],
  symbol_breakdown: [],
};

const mockSymbolsResponse = {
  symbols: [
    { symbol: "BTC", full_symbol: "BTCUSDT" },
    { symbol: "ETH", full_symbol: "ETHUSDT" },
    { symbol: "SOL", full_symbol: "SOLUSDT" },
  ],
};

describe("useRunBacktest", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should trigger backtest run", async () => {
    mockedBacktestApi.run.mockResolvedValue(mockBacktestResponse);

    const { result } = renderHook(() => useRunBacktest(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      strategy_id: "strategy-1",
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
      symbols: ["BTC"],
    });

    expect(mockedBacktestApi.run).toHaveBeenCalledWith({
      strategy_id: "strategy-1",
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
      symbols: ["BTC"],
    });
    expect(response?.total_return_percent).toBe(25);
  });

  it("should handle backtest run error", async () => {
    mockedBacktestApi.run.mockRejectedValue(new Error("Backtest failed"));

    const { result } = renderHook(() => useRunBacktest(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        strategy_id: "strategy-1",
        start_date: "2024-01-01",
        end_date: "2024-06-01",
        initial_balance: 10000,
      })
    ).rejects.toThrow("Backtest failed");
  });

  it("should return backtest result with correct fields", async () => {
    mockedBacktestApi.run.mockResolvedValue(mockBacktestResponse);

    const { result } = renderHook(() => useRunBacktest(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      strategy_id: "strategy-1",
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
    });

    expect(response?.win_rate).toBe(66.7);
    expect(response?.final_balance).toBe(12500);
    expect(response?.total_trades).toBe(42);
  });
});

describe("useQuickBacktest", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should trigger quick backtest", async () => {
    mockedBacktestApi.quick.mockResolvedValue(mockBacktestResponse);

    const { result } = renderHook(() => useQuickBacktest(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      symbols: ["BTC", "ETH"],
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
      max_leverage: 5,
    });

    expect(mockedBacktestApi.quick).toHaveBeenCalledWith({
      symbols: ["BTC", "ETH"],
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
      max_leverage: 5,
    });
    expect(response?.total_return_percent).toBe(25);
  });

  it("should handle quick backtest error", async () => {
    mockedBacktestApi.quick.mockRejectedValue(
      new Error("Insufficient data for backtest")
    );

    const { result } = renderHook(() => useQuickBacktest(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        symbols: ["BTC"],
        start_date: "2024-01-01",
        end_date: "2024-06-01",
        initial_balance: 10000,
      })
    ).rejects.toThrow("Insufficient data for backtest");
  });
});

describe("useBacktestSymbols", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch symbols with default exchange", async () => {
    mockedBacktestApi.getSymbols.mockResolvedValue(mockSymbolsResponse);

    const { result } = renderHook(() => useBacktestSymbols(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedBacktestApi.getSymbols).toHaveBeenCalledWith("hyperliquid");
    expect(result.current.data?.symbols).toHaveLength(3);
  });

  it("should fetch symbols with specified exchange", async () => {
    mockedBacktestApi.getSymbols.mockResolvedValue(mockSymbolsResponse);

    const { result } = renderHook(() => useBacktestSymbols("binance"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedBacktestApi.getSymbols).toHaveBeenCalledWith("binance");
  });

  it("should handle symbols fetch error", async () => {
    mockedBacktestApi.getSymbols.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useBacktestSymbols(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});
