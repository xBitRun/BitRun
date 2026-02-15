/**
 * Tests for useQuantStrategies hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useQuantStrategies,
  useQuantStrategy,
  useCreateQuantStrategy,
  useUpdateQuantStrategy,
  useDeleteQuantStrategy,
  useUpdateQuantStrategyStatus,
} from "@/hooks/use-quant-strategies";
import { agentsApi } from "@/lib/api";

// Mock the API module - hooks delegate to agentsApi internally
jest.mock("@/lib/api", () => ({
  agentsApi: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    updateStatus: jest.fn(),
  },
}));

const mockedAgentsApi = agentsApi as jest.Mocked<typeof agentsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      SWRConfig,
      { value: { provider: () => new Map(), dedupingInterval: 0 } },
      children
    );
};

// Mock data
const mockQuantStrategies = [
  {
    id: "qs-1",
    name: "BTC Grid Bot",
    description: "Grid trading for BTC",
    strategy_type: "grid",
    symbol: "BTC/USDT",
    config: { grid_levels: 10, upper_price: 70000, lower_price: 60000 },
    runtime_state: {},
    status: "active" as const,
    error_message: null,
    account_id: "account-1",
    total_pnl: 500,
    total_trades: 30,
    winning_trades: 20,
    losing_trades: 10,
    win_rate: 66.7,
    max_drawdown: 3.5,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    last_run_at: "2024-01-10T12:00:00Z",
  },
  {
    id: "qs-2",
    name: "ETH DCA",
    description: "Dollar cost averaging ETH",
    strategy_type: "dca",
    symbol: "ETH/USDT",
    config: { interval_hours: 24, amount_usd: 100 },
    runtime_state: {},
    status: "draft" as const,
    error_message: null,
    account_id: null,
    total_pnl: 0,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    max_drawdown: 0,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
    last_run_at: null,
  },
];

describe("useQuantStrategies", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch quant strategies list", async () => {
    mockedAgentsApi.list.mockResolvedValue(mockQuantStrategies as never);

    const { result } = renderHook(() => useQuantStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAgentsApi.list).toHaveBeenCalled();
    expect(result.current.strategies).toEqual(mockQuantStrategies);
    expect(result.current.strategies.length).toBe(2);
  });

  it("should handle fetch error", async () => {
    mockedAgentsApi.list.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useQuantStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should return loading state initially", () => {
    mockedAgentsApi.list.mockReturnValue(new Promise(() => {}) as never);

    const { result } = renderHook(() => useQuantStrategies(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.strategies).toEqual([]);
  });
});

describe("useQuantStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single quant strategy", async () => {
    mockedAgentsApi.get.mockResolvedValue(mockQuantStrategies[0] as never);

    const { result } = renderHook(() => useQuantStrategy("qs-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAgentsApi.get).toHaveBeenCalledWith("qs-1");
    expect(result.current.data).toEqual(mockQuantStrategies[0]);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useQuantStrategy(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedAgentsApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCreateQuantStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should throw deprecation error on trigger", async () => {
    const { result } = renderHook(() => useCreateQuantStrategy(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        name: "New Grid",
        strategy_type: "grid",
        symbol: "BTC/USDT",
        config: { grid_levels: 5 },
      })
    ).rejects.toThrow("deprecated");
  });
});

describe("useUpdateQuantStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update quant strategy", async () => {
    const updated = { ...mockQuantStrategies[0], name: "Updated Grid" };
    mockedAgentsApi.update.mockResolvedValue(updated as never);

    const { result } = renderHook(() => useUpdateQuantStrategy("qs-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({ name: "Updated Grid" });

    expect(mockedAgentsApi.update).toHaveBeenCalledWith("qs-1", {
      name: "Updated Grid",
    });
  });

  it("should handle update error", async () => {
    mockedAgentsApi.update.mockRejectedValue(
      new Error("Update failed")
    );

    const { result } = renderHook(() => useUpdateQuantStrategy("qs-1"), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({ name: "Updated Grid" })
    ).rejects.toThrow("Update failed");
  });
});

describe("useDeleteQuantStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should delete quant strategy", async () => {
    mockedAgentsApi.delete.mockResolvedValue(undefined as never);

    const { result } = renderHook(() => useDeleteQuantStrategy("qs-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger();

    expect(mockedAgentsApi.delete).toHaveBeenCalledWith("qs-1");
  });

  it("should handle deletion error", async () => {
    mockedAgentsApi.delete.mockRejectedValue(
      new Error("Strategy is active")
    );

    const { result } = renderHook(() => useDeleteQuantStrategy("qs-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger()).rejects.toThrow(
      "Strategy is active"
    );
  });
});

describe("useUpdateQuantStrategyStatus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update status to active", async () => {
    const activated = { ...mockQuantStrategies[1], status: "active" };
    mockedAgentsApi.updateStatus.mockResolvedValue(activated as never);

    const { result } = renderHook(
      () => useUpdateQuantStrategyStatus("qs-2"),
      { wrapper: createWrapper() }
    );

    const response = await result.current.trigger("active");

    expect(mockedAgentsApi.updateStatus).toHaveBeenCalledWith(
      "qs-2",
      "active"
    );
    expect(response?.status).toBe("active");
  });

  it("should handle status update error", async () => {
    mockedAgentsApi.updateStatus.mockRejectedValue(
      new Error("Cannot activate - no account linked")
    );

    const { result } = renderHook(
      () => useUpdateQuantStrategyStatus("qs-2"),
      { wrapper: createWrapper() }
    );

    await expect(result.current.trigger("active")).rejects.toThrow(
      "Cannot activate - no account linked"
    );
  });
});
