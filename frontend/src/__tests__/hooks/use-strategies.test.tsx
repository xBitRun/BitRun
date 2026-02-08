/**
 * Tests for useStrategies hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useStrategies,
  useStrategy,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useUpdateStrategyStatus,
  useActiveStrategiesCount,
} from "@/hooks/use-strategies";
import { strategiesApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  strategiesApi: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    updateStatus: jest.fn(),
  },
}));

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
const mockStrategies = [
  {
    id: "strategy-1",
    name: "BTC Momentum",
    description: "BTC momentum trading",
    prompt: "Trade BTC based on momentum indicators",
    status: "active" as const,
    trading_mode: "conservative",
    account_id: "account-1",
    config: {
      execution_interval_minutes: 30,
      max_positions: 3,
      symbols: ["BTC"],
    },
    total_pnl: 1000,
    total_trades: 50,
    winning_trades: 30,
    losing_trades: 20,
    win_rate: 60,
    max_drawdown: 5,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "strategy-2",
    name: "ETH Grid",
    description: "ETH grid trading",
    prompt: "Trade ETH with grid strategy",
    status: "draft" as const,
    trading_mode: "aggressive",
    account_id: null,
    config: {
      execution_interval_minutes: 60,
      max_positions: 5,
      symbols: ["ETH"],
    },
    total_pnl: 0,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    max_drawdown: 0,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
  {
    id: "strategy-3",
    name: "Multi Coin",
    description: "Multi coin strategy",
    prompt: "Diversified trading across multiple coins",
    status: "active" as const,
    trading_mode: "balanced",
    account_id: "account-2",
    config: {
      execution_interval_minutes: 15,
      max_positions: 10,
      symbols: ["BTC", "ETH", "SOL"],
    },
    total_pnl: 500,
    total_trades: 100,
    winning_trades: 55,
    losing_trades: 45,
    win_rate: 55,
    max_drawdown: 8,
    created_at: "2024-01-03T00:00:00Z",
    updated_at: "2024-01-03T00:00:00Z",
  },
];

describe("useStrategies", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch strategies list", async () => {
    mockedStrategiesApi.list.mockResolvedValue(mockStrategies);

    const { result } = renderHook(() => useStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedStrategiesApi.list).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockStrategies);
    expect(result.current.data?.length).toBe(3);
  });

  it("should handle fetch error", async () => {
    mockedStrategiesApi.list.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should return loading state initially", () => {
    mockedStrategiesApi.list.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useStrategies(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single strategy", async () => {
    mockedStrategiesApi.get.mockResolvedValue(mockStrategies[0]);

    const { result } = renderHook(() => useStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedStrategiesApi.get).toHaveBeenCalledWith("strategy-1");
    expect(result.current.data).toEqual(mockStrategies[0]);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useStrategy(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedStrategiesApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("should return correct strategy data", async () => {
    mockedStrategiesApi.get.mockResolvedValue(mockStrategies[0]);

    const { result } = renderHook(() => useStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.name).toBe("BTC Momentum");
    expect(result.current.data?.status).toBe("active");
    expect(result.current.data?.total_pnl).toBe(1000);
  });
});

describe("useCreateStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create strategy", async () => {
    const newStrategy = { ...mockStrategies[1], id: "new-strategy" };
    mockedStrategiesApi.create.mockResolvedValue(newStrategy);

    const { result } = renderHook(() => useCreateStrategy(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      name: "New Strategy",
      prompt: "Test prompt for new strategy",
      trading_mode: "conservative",
      symbols: ["BTC"],
      account_id: "account-1",
    });

    expect(mockedStrategiesApi.create).toHaveBeenCalled();
    expect(response).toEqual(newStrategy);
  });

  it("should handle creation error", async () => {
    mockedStrategiesApi.create.mockRejectedValue(new Error("Creation failed"));

    const { result } = renderHook(() => useCreateStrategy(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        name: "New Strategy",
        prompt: "Test prompt",
        trading_mode: "conservative",
        symbols: ["BTC"],
        account_id: "account-1",
      })
    ).rejects.toThrow("Creation failed");
  });

  it("should pass correct data to API", async () => {
    mockedStrategiesApi.create.mockResolvedValue(mockStrategies[0]);

    const { result } = renderHook(() => useCreateStrategy(), {
      wrapper: createWrapper(),
    });

    const createData = {
      name: "Test Strategy",
      prompt: "Test prompt",
      trading_mode: "aggressive" as const,
      symbols: ["BTC", "ETH"],
      account_id: "account-1",
      config: {
        execution_interval_minutes: 45,
      },
    };

    await result.current.trigger(createData);

    expect(mockedStrategiesApi.create).toHaveBeenCalledWith(createData);
  });
});

describe("useUpdateStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update strategy", async () => {
    const updatedStrategy = { ...mockStrategies[0], name: "Updated Name" };
    mockedStrategiesApi.update.mockResolvedValue(updatedStrategy);

    const { result } = renderHook(() => useUpdateStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({ name: "Updated Name" });

    expect(mockedStrategiesApi.update).toHaveBeenCalledWith("strategy-1", {
      name: "Updated Name",
    });
  });

  it("should update multiple fields", async () => {
    const updatedStrategy = {
      ...mockStrategies[0],
      name: "Updated Name",
      prompt: "Updated prompt",
    };
    mockedStrategiesApi.update.mockResolvedValue(updatedStrategy);

    const { result } = renderHook(() => useUpdateStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    const updateData = {
      name: "Updated Name",
      prompt: "Updated prompt",
      trading_mode: "balanced" as const,
    };

    await result.current.trigger(updateData);

    expect(mockedStrategiesApi.update).toHaveBeenCalledWith(
      "strategy-1",
      updateData
    );
  });

  it("should handle update error", async () => {
    mockedStrategiesApi.update.mockRejectedValue(new Error("Update failed"));

    const { result } = renderHook(() => useUpdateStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({ name: "Updated Name" })
    ).rejects.toThrow("Update failed");
  });
});

describe("useDeleteStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should delete strategy", async () => {
    mockedStrategiesApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger();

    expect(mockedStrategiesApi.delete).toHaveBeenCalledWith("strategy-1");
  });

  it("should handle deletion error", async () => {
    mockedStrategiesApi.delete.mockRejectedValue(
      new Error("Strategy has active positions")
    );

    const { result } = renderHook(() => useDeleteStrategy("strategy-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger()).rejects.toThrow(
      "Strategy has active positions"
    );
  });
});

describe("useUpdateStrategyStatus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update status to active", async () => {
    const activatedStrategy = { ...mockStrategies[1], status: "active" };
    mockedStrategiesApi.updateStatus.mockResolvedValue(activatedStrategy);

    const { result } = renderHook(() => useUpdateStrategyStatus("strategy-2"), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger("active");

    expect(mockedStrategiesApi.updateStatus).toHaveBeenCalledWith(
      "strategy-2",
      "active"
    );
    expect(response?.status).toBe("active");
  });

  it("should update status to paused", async () => {
    const pausedStrategy = { ...mockStrategies[0], status: "paused" };
    mockedStrategiesApi.updateStatus.mockResolvedValue(pausedStrategy);

    const { result } = renderHook(() => useUpdateStrategyStatus("strategy-1"), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger("paused");

    expect(mockedStrategiesApi.updateStatus).toHaveBeenCalledWith(
      "strategy-1",
      "paused"
    );
    expect(response?.status).toBe("paused");
  });

  it("should handle status update error", async () => {
    mockedStrategiesApi.updateStatus.mockRejectedValue(
      new Error("Cannot activate - no account linked")
    );

    const { result } = renderHook(() => useUpdateStrategyStatus("strategy-2"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger("active")).rejects.toThrow(
      "Cannot activate - no account linked"
    );
  });
});

describe("useActiveStrategiesCount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return count of active strategies", async () => {
    mockedStrategiesApi.list.mockResolvedValue(mockStrategies);

    const { result } = renderHook(() => useActiveStrategiesCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBe(2));

    // mockStrategies has 2 active strategies
    expect(result.current).toBe(2);
  });

  it("should return 0 when no active strategies", async () => {
    const allDraftStrategies = mockStrategies.map((s) => ({
      ...s,
      status: "draft" as const,
    }));
    mockedStrategiesApi.list.mockResolvedValue(allDraftStrategies);

    const { result } = renderHook(() => useActiveStrategiesCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBe(0));

    expect(result.current).toBe(0);
  });

  it("should return 0 when no strategies", async () => {
    mockedStrategiesApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useActiveStrategiesCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBe(0));

    expect(result.current).toBe(0);
  });
});
