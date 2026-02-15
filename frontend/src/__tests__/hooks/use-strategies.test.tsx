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
  useForkStrategy,
  useMarketplaceStrategies,
  useStrategyVersions,
  useRestoreStrategyVersion,
} from "@/hooks/use-strategies";
import { strategiesApi, ApiError } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  strategiesApi: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    fork: jest.fn(),
    marketplace: jest.fn(),
    listVersions: jest.fn(),
    getVersion: jest.fn(),
    restoreVersion: jest.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const mockedStrategiesApi = strategiesApi as jest.Mocked<typeof strategiesApi>;
const MockedApiError = ApiError as jest.MockedClass<typeof ApiError>;

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

describe("useForkStrategy", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fork strategy", async () => {
    const forkedStrategy = { ...mockStrategies[0], id: "forked-strategy", forked_from: "strategy-1" };
    mockedStrategiesApi.fork.mockResolvedValue(forkedStrategy);

    const { result } = renderHook(() => useForkStrategy(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger("strategy-1");

    expect(mockedStrategiesApi.fork).toHaveBeenCalledWith("strategy-1");
    expect(response).toEqual(forkedStrategy);
    expect(response.forked_from).toBe("strategy-1");
  });

  it("should handle fork error", async () => {
    mockedStrategiesApi.fork.mockRejectedValue(new Error("Fork failed"));

    const { result } = renderHook(() => useForkStrategy(), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger("strategy-1")).rejects.toThrow(
      "Fork failed"
    );
  });
});

describe("useMarketplaceStrategies", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockMarketplaceResponse = {
    items: mockStrategies,
    total: 100,
    limit: 50,
    offset: 0,
  };

  it("should fetch marketplace strategies", async () => {
    mockedStrategiesApi.marketplace.mockResolvedValue(mockMarketplaceResponse);

    const { result } = renderHook(() => useMarketplaceStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.strategies).toBeDefined());

    expect(mockedStrategiesApi.marketplace).toHaveBeenCalledWith(undefined);
    expect(result.current.strategies).toEqual(mockStrategies);
    expect(result.current.total).toBe(100);
  });

  it("should pass filter params to API", async () => {
    mockedStrategiesApi.marketplace.mockResolvedValue(mockMarketplaceResponse);

    const params = {
      type_filter: "momentum" as const,
      category: "trend",
      search: "btc",
      sort_by: "popular" as const,
      limit: 10,
      offset: 20,
    };

    const { result } = renderHook(() => useMarketplaceStrategies(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.strategies).toBeDefined());

    expect(mockedStrategiesApi.marketplace).toHaveBeenCalledWith(params);
  });

  it("should treat 404 as empty list (graceful degradation)", async () => {
    const apiError = new MockedApiError("Not found", 404);
    mockedStrategiesApi.marketplace.mockRejectedValue(apiError);

    const { result } = renderHook(() => useMarketplaceStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.strategies).toBeDefined());

    expect(result.current.strategies).toEqual([]);
    expect(result.current.total).toBe(0);
    expect(result.current.error).toBeUndefined();
  });

  it("should throw non-404 errors", async () => {
    const apiError = new MockedApiError("Server error", 500);
    mockedStrategiesApi.marketplace.mockRejectedValue(apiError);

    const { result } = renderHook(() => useMarketplaceStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should expose refresh method", async () => {
    mockedStrategiesApi.marketplace.mockResolvedValue(mockMarketplaceResponse);

    const { result } = renderHook(() => useMarketplaceStrategies(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.strategies).toBeDefined());

    expect(result.current.refresh).toBeInstanceOf(Function);
  });
});

describe("useStrategyVersions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const mockVersions = [
    {
      id: "version-1",
      strategy_id: "strategy-1",
      version: 1,
      name: "Initial version",
      description: "First version",
      symbols: ["BTC"],
      config: {},
      change_note: "Initial",
      created_at: "2024-01-01T00:00:00Z",
    },
    {
      id: "version-2",
      strategy_id: "strategy-1",
      version: 2,
      name: "Updated version",
      description: "Second version",
      symbols: ["BTC", "ETH"],
      config: {},
      change_note: "Added ETH",
      created_at: "2024-01-02T00:00:00Z",
    },
  ];

  it("should fetch version history", async () => {
    mockedStrategiesApi.listVersions.mockResolvedValue(mockVersions);

    const { result } = renderHook(() => useStrategyVersions("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedStrategiesApi.listVersions).toHaveBeenCalledWith("strategy-1");
    expect(result.current.data).toEqual(mockVersions);
    expect(result.current.data?.length).toBe(2);
  });

  it("should not fetch when strategyId is null", async () => {
    const { result } = renderHook(() => useStrategyVersions(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedStrategiesApi.listVersions).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("should handle fetch error", async () => {
    mockedStrategiesApi.listVersions.mockRejectedValue(new Error("Fetch failed"));

    const { result } = renderHook(() => useStrategyVersions("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useRestoreStrategyVersion", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should restore strategy to previous version", async () => {
    const restoredStrategy = { ...mockStrategies[0], name: "Restored version" };
    mockedStrategiesApi.restoreVersion.mockResolvedValue(restoredStrategy);

    const { result } = renderHook(() => useRestoreStrategyVersion("strategy-1"), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger(1);

    expect(mockedStrategiesApi.restoreVersion).toHaveBeenCalledWith("strategy-1", 1);
    expect(response).toEqual(restoredStrategy);
  });

  it("should handle restore error", async () => {
    mockedStrategiesApi.restoreVersion.mockRejectedValue(new Error("Restore failed"));

    const { result } = renderHook(() => useRestoreStrategyVersion("strategy-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger(1)).rejects.toThrow("Restore failed");
  });

  it("should pass correct version number", async () => {
    mockedStrategiesApi.restoreVersion.mockResolvedValue(mockStrategies[0]);

    const { result } = renderHook(() => useRestoreStrategyVersion("strategy-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger(5);

    expect(mockedStrategiesApi.restoreVersion).toHaveBeenCalledWith("strategy-1", 5);
  });
});

