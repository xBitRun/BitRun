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
  useBacktests,
  useBacktest,
  useCreateBacktest,
  useDeleteBacktest,
} from "@/hooks/use-backtest";
import { backtestApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  backtestApi: {
    run: jest.fn(),
    quick: jest.fn(),
    getSymbols: jest.fn(),
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    delete: jest.fn(),
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

describe("useBacktests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch paginated backtest list", async () => {
    const mockListResponse = {
      items: [
        { id: "bt-1", strategy_name: "Test 1", status: "completed" },
        { id: "bt-2", strategy_name: "Test 2", status: "running" },
      ],
      total: 2,
    };
    mockedBacktestApi.list.mockResolvedValue(mockListResponse);

    const { result } = renderHook(() => useBacktests(10, 0), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedBacktestApi.list).toHaveBeenCalledWith(10, 0);
    expect(result.current.data?.items).toHaveLength(2);
    expect(result.current.data?.total).toBe(2);
  });

  it("should use default pagination values", async () => {
    mockedBacktestApi.list.mockResolvedValue({ items: [], total: 0 });

    renderHook(() => useBacktests(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockedBacktestApi.list).toHaveBeenCalledWith(20, 0));
  });
});

describe("useBacktest", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch when id is null", () => {
    mockedBacktestApi.get.mockResolvedValue({ id: "bt-1", strategy_name: "Test" });

    renderHook(() => useBacktest(null), {
      wrapper: createWrapper(),
    });

    expect(mockedBacktestApi.get).not.toHaveBeenCalled();
  });

  it("should fetch single backtest by id", async () => {
    const mockDetailResponse = {
      id: "bt-1",
      strategy_name: "Test Strategy",
      status: "completed",
      result: mockBacktestResponse,
    };
    mockedBacktestApi.get.mockResolvedValue(mockDetailResponse);

    const { result } = renderHook(() => useBacktest("bt-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedBacktestApi.get).toHaveBeenCalledWith("bt-1");
    expect(result.current.data?.id).toBe("bt-1");
  });
});

describe("useCreateBacktest", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create and save backtest", async () => {
    const mockDetailResponse = {
      id: "bt-new",
      strategy_name: "New Backtest",
      status: "pending",
    };
    mockedBacktestApi.create.mockResolvedValue(mockDetailResponse);

    const { result } = renderHook(() => useCreateBacktest(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      strategy_id: "strategy-1",
      start_date: "2024-01-01",
      end_date: "2024-06-01",
      initial_balance: 10000,
    });

    expect(mockedBacktestApi.create).toHaveBeenCalled();
    expect(response?.id).toBe("bt-new");
  });

  it("should handle create error", async () => {
    mockedBacktestApi.create.mockRejectedValue(new Error("Create failed"));

    const { result } = renderHook(() => useCreateBacktest(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        strategy_id: "strategy-1",
        start_date: "2024-01-01",
        end_date: "2024-06-01",
        initial_balance: 10000,
      })
    ).rejects.toThrow("Create failed");
  });
});

describe("useDeleteBacktest", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should delete backtest", async () => {
    mockedBacktestApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteBacktest(), {
      wrapper: createWrapper(),
    });

    await result.current.trigger("bt-1");

    expect(mockedBacktestApi.delete).toHaveBeenCalledWith("bt-1");
  });

  it("should track deleting id", async () => {
    mockedBacktestApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteBacktest(), {
      wrapper: createWrapper(),
    });

    expect(result.current.deletingId).toBeNull();

    const deletePromise = result.current.trigger("bt-1");

    // During deletion, deletingId should be set
    // After completion, it should be null again
    await deletePromise;

    expect(result.current.deletingId).toBeNull();
  });

  it("should handle delete error", async () => {
    mockedBacktestApi.delete.mockRejectedValue(new Error("Delete failed"));

    const { result } = renderHook(() => useDeleteBacktest(), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger("bt-1")).rejects.toThrow("Delete failed");

    // deletingId should be cleared even on error
    expect(result.current.deletingId).toBeNull();
  });
});
