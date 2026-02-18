/**
 * Tests for use-agents hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useAgents,
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useUpdateAgentStatus,
  useTriggerAgent,
  useAgentPositions,
  useActiveAgentsCount,
} from "@/hooks/use-agents";
import { agentsApi, ApiError } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  agentsApi: {
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    updateStatus: jest.fn(),
    trigger: jest.fn(),
    getPositions: jest.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

const mockedAgentsApi = agentsApi as jest.Mocked<typeof agentsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockAgents = [
  {
    id: "agent-1",
    user_id: "user-1",
    name: "BTC Agent",
    strategy_id: "strategy-1",
    strategy_type: "dca" as const,
    strategy_name: "BTC DCA",
    ai_model: "deepseek:chat",
    execution_mode: "live" as const,
    account_id: "account-1",
    mock_initial_balance: null,
    allocated_capital: 1000,
    allocated_capital_percent: null,
    execution_interval_minutes: 30,
    auto_execute: true,
    runtime_state: null,
    config: null,
    description: null,
    status: "active" as const,
    error_message: null,
    total_pnl: 500,
    total_trades: 20,
    winning_trades: 12,
    losing_trades: 8,
    win_rate: 60,
    max_drawdown: 5,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    last_run_at: "2024-01-02T00:00:00Z",
    next_run_at: "2024-01-03T00:00:00Z",
  },
  {
    id: "agent-2",
    user_id: "user-1",
    name: "ETH Agent",
    strategy_id: "strategy-2",
    strategy_type: "grid",
    strategy_name: "ETH Grid",
    ai_model: "gpt-4",
    execution_mode: "mock" as const,
    account_id: null,
    mock_initial_balance: 10000,
    allocated_capital: null,
    allocated_capital_percent: 50,
    execution_interval_minutes: 60,
    auto_execute: false,
    runtime_state: { lastPrice: 2000 },
    config: { gridLevels: 10 },
    description: "Grid trading",
    status: "paused" as const,
    error_message: null,
    total_pnl: -100,
    total_trades: 10,
    winning_trades: 4,
    losing_trades: 6,
    win_rate: 40,
    max_drawdown: 10,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
    last_run_at: null,
    next_run_at: null,
  },
  {
    id: "agent-3",
    user_id: "user-1",
    name: "SOL Agent",
    strategy_id: "strategy-3",
    strategy_type: "dca" as const,
    strategy_name: "SOL DCA",
    ai_model: null,
    execution_mode: "live" as const,
    account_id: "account-2",
    mock_initial_balance: null,
    allocated_capital: 2000,
    allocated_capital_percent: null,
    execution_interval_minutes: 15,
    auto_execute: true,
    runtime_state: null,
    config: null,
    description: null,
    status: "stopped" as const,
    error_message: "Connection lost",
    total_pnl: 0,
    total_trades: 0,
    winning_trades: 0,
    losing_trades: 0,
    win_rate: 0,
    max_drawdown: 0,
    created_at: "2024-01-03T00:00:00Z",
    updated_at: "2024-01-03T00:00:00Z",
    last_run_at: null,
    next_run_at: null,
  },
];

const mockPositions = [
  {
    id: "pos-1",
    agent_id: "agent-1",
    account_id: "account-1",
    symbol: "BTCUSDT",
    side: "long" as const,
    size: 0.1,
    size_usd: 5000,
    entry_price: 50000,
    leverage: 5,
    status: "open",
    realized_pnl: 0,
    close_price: null,
    opened_at: "2024-01-01T00:00:00Z",
    closed_at: null,
  },
];

describe("useAgents", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch agents list", async () => {
    mockedAgentsApi.list.mockResolvedValue(mockAgents);

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.agents).toBeDefined());

    expect(mockedAgentsApi.list).toHaveBeenCalledWith(undefined);
    expect(result.current.agents).toEqual(mockAgents);
    expect(result.current.agents.length).toBe(3);
  });

  it("should pass filter params to API", async () => {
    mockedAgentsApi.list.mockResolvedValue(mockAgents);

    const { result } = renderHook(
      () => useAgents({ status_filter: "active", strategy_type: "dca" as const }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.agents).toBeDefined());

    expect(mockedAgentsApi.list).toHaveBeenCalledWith({
      status_filter: "active",
      strategy_type: "dca",
    });
  });

  it("should treat 404 as empty list (graceful degradation)", async () => {
    const apiError = new ApiError("Not found", 404);
    mockedAgentsApi.list.mockRejectedValue(apiError);

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.agents).toBeDefined());

    expect(result.current.agents).toEqual([]);
    expect(result.current.error).toBeUndefined();
  });

  it("should throw non-404 errors", async () => {
    const apiError = new ApiError("Server error", 500);
    mockedAgentsApi.list.mockRejectedValue(apiError);

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should expose refresh method", async () => {
    mockedAgentsApi.list.mockResolvedValue(mockAgents);

    const { result } = renderHook(() => useAgents(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.agents).toBeDefined());

    expect(result.current.refresh).toBeInstanceOf(Function);
  });
});

describe("useAgent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single agent", async () => {
    mockedAgentsApi.get.mockResolvedValue(mockAgents[0]);

    const { result } = renderHook(() => useAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAgentsApi.get).toHaveBeenCalledWith("agent-1");
    expect(result.current.data).toEqual(mockAgents[0]);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useAgent(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedAgentsApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("should return correct agent data", async () => {
    mockedAgentsApi.get.mockResolvedValue(mockAgents[0]);

    const { result } = renderHook(() => useAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.data?.name).toBe("BTC Agent");
    expect(result.current.data?.status).toBe("active");
    expect(result.current.data?.execution_mode).toBe("live");
  });
});

describe("useCreateAgent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create agent", async () => {
    const newAgent = { ...mockAgents[0], id: "new-agent", name: "New Agent" };
    mockedAgentsApi.create.mockResolvedValue(newAgent);

    const { result } = renderHook(() => useCreateAgent(), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger({
      name: "New Agent",
      strategy_id: "strategy-1",
      execution_mode: "live",
      account_id: "account-1",
    });

    expect(mockedAgentsApi.create).toHaveBeenCalled();
    expect(response).toEqual(newAgent);
  });

  it("should handle creation error", async () => {
    mockedAgentsApi.create.mockRejectedValue(new Error("Creation failed"));

    const { result } = renderHook(() => useCreateAgent(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        name: "New Agent",
        strategy_id: "strategy-1",
        execution_mode: "live",
      })
    ).rejects.toThrow("Creation failed");
  });
});

describe("useUpdateAgent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update agent", async () => {
    const updatedAgent = { ...mockAgents[0], name: "Updated Agent" };
    mockedAgentsApi.update.mockResolvedValue(updatedAgent);

    const { result } = renderHook(() => useUpdateAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({ name: "Updated Agent" });

    expect(mockedAgentsApi.update).toHaveBeenCalledWith("agent-1", {
      name: "Updated Agent",
    });
  });

  it("should update multiple fields", async () => {
    const updatedAgent = {
      ...mockAgents[0],
      name: "Updated Agent",
      ai_model: "gpt-4",
    };
    mockedAgentsApi.update.mockResolvedValue(updatedAgent);

    const { result } = renderHook(() => useUpdateAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({ name: "Updated Agent", ai_model: "gpt-4" });

    expect(mockedAgentsApi.update).toHaveBeenCalledWith("agent-1", {
      name: "Updated Agent",
      ai_model: "gpt-4",
    });
  });

  it("should handle update error", async () => {
    mockedAgentsApi.update.mockRejectedValue(new Error("Update failed"));

    const { result } = renderHook(() => useUpdateAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({ name: "Updated Name" })
    ).rejects.toThrow("Update failed");
  });
});

describe("useDeleteAgent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should delete agent", async () => {
    mockedAgentsApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger();

    expect(mockedAgentsApi.delete).toHaveBeenCalledWith("agent-1");
  });

  it("should handle deletion error", async () => {
    mockedAgentsApi.delete.mockRejectedValue(
      new Error("Agent has active positions")
    );

    const { result } = renderHook(() => useDeleteAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger()).rejects.toThrow(
      "Agent has active positions"
    );
  });
});

describe("useUpdateAgentStatus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update status to active", async () => {
    const updatedAgent = { ...mockAgents[1], status: "active" as const };
    mockedAgentsApi.updateStatus.mockResolvedValue(updatedAgent);

    const { result } = renderHook(() => useUpdateAgentStatus("agent-2"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger("active");

    expect(mockedAgentsApi.updateStatus).toHaveBeenCalledWith(
      "agent-2",
      "active"
    );
  });

  it("should update status to paused", async () => {
    const updatedAgent = { ...mockAgents[0], status: "paused" as const };
    mockedAgentsApi.updateStatus.mockResolvedValue(updatedAgent);

    const { result } = renderHook(() => useUpdateAgentStatus("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger("paused");

    expect(mockedAgentsApi.updateStatus).toHaveBeenCalledWith(
      "agent-1",
      "paused"
    );
  });

  it("should update status to stopped", async () => {
    const updatedAgent = { ...mockAgents[0], status: "stopped" as const };
    mockedAgentsApi.updateStatus.mockResolvedValue(updatedAgent);

    const { result } = renderHook(() => useUpdateAgentStatus("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger("stopped");

    expect(mockedAgentsApi.updateStatus).toHaveBeenCalledWith(
      "agent-1",
      "stopped"
    );
  });

  it("should handle status update error", async () => {
    mockedAgentsApi.updateStatus.mockRejectedValue(
      new Error("Status update failed")
    );

    const { result } = renderHook(() => useUpdateAgentStatus("agent-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger("paused")).rejects.toThrow(
      "Status update failed"
    );
  });
});

describe("useTriggerAgent", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should trigger agent execution", async () => {
    mockedAgentsApi.trigger.mockResolvedValue({
      message: "Triggered",
      success: true,
    });

    const { result } = renderHook(() => useTriggerAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger();

    expect(mockedAgentsApi.trigger).toHaveBeenCalledWith("agent-1");
  });

  it("should handle trigger error", async () => {
    mockedAgentsApi.trigger.mockRejectedValue(new Error("Trigger failed"));

    const { result } = renderHook(() => useTriggerAgent("agent-1"), {
      wrapper: createWrapper(),
    });

    await expect(result.current.trigger()).rejects.toThrow("Trigger failed");
  });
});

describe("useAgentPositions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch agent positions", async () => {
    mockedAgentsApi.getPositions.mockResolvedValue(mockPositions);

    const { result } = renderHook(() => useAgentPositions("agent-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAgentsApi.getPositions).toHaveBeenCalledWith("agent-1");
    expect(result.current.data).toEqual(mockPositions);
  });

  it("should not fetch when agentId is null", async () => {
    const { result } = renderHook(() => useAgentPositions(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedAgentsApi.getPositions).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useActiveAgentsCount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should count active agents", async () => {
    mockedAgentsApi.list.mockResolvedValue(mockAgents);

    const { result } = renderHook(() => useActiveAgentsCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    // mockAgents has 1 active agent (agent-1)
    expect(result.current).toBe(1);
  });

  it("should return 0 when no agents", async () => {
    mockedAgentsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useActiveAgentsCount(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    expect(result.current).toBe(0);
  });
});
