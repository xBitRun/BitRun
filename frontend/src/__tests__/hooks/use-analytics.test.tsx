/**
 * Tests for analytics hooks
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useAgentPnL,
  useAccountAgents,
  useEquityCurve,
  useAccountPnL,
  useSyncAccount,
} from "@/hooks/use-analytics";
import { analyticsApi } from "@/lib/api/endpoints";

// Mock the API module
jest.mock("@/lib/api/endpoints", () => ({
  analyticsApi: {
    getAgentPnL: jest.fn(),
    getAccountAgents: jest.fn(),
    getEquityCurve: jest.fn(),
    getAccountPnL: jest.fn(),
    syncAccount: jest.fn(),
  },
}));

const mockAnalyticsApi = analyticsApi as jest.Mocked<typeof analyticsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockAgentPnLData = {
  summary: {
    total_pnl: 1000.0,
    win_rate: 0.75,
    total_trades: 10,
  },
  trades: [
    {
      id: "trade-1",
      symbol: "BTC/USDT",
      side: "buy" as const,
      pnl: 100.0,
      timestamp: "2024-01-01T00:00:00Z",
    },
  ],
  total: 1,
};

const mockAccountAgentsData = {
  agents: [
    {
      id: "agent-1",
      name: "Test Agent",
      pnl: 500.0,
      trades: 5,
    },
  ],
  total: 1,
};

const mockEquityCurveData = {
  data_points: [
    { date: "2024-01-01", equity: 10000 },
    { date: "2024-01-02", equity: 10500 },
  ],
  start_date: "2024-01-01",
  end_date: "2024-01-02",
  granularity: "day" as const,
};

const mockAccountPnLData = {
  total_pnl: 2000.0,
  daily_pnl: 100.0,
  weekly_pnl: 500.0,
};

describe("useAgentPnL", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch when agentId is null", () => {
    mockAnalyticsApi.getAgentPnL.mockResolvedValue(mockAgentPnLData);

    renderHook(() => useAgentPnL(null), { wrapper: createWrapper() });

    expect(mockAnalyticsApi.getAgentPnL).not.toHaveBeenCalled();
  });

  it("should fetch agent P&L data", async () => {
    mockAnalyticsApi.getAgentPnL.mockResolvedValue(mockAgentPnLData);

    const { result } = renderHook(() => useAgentPnL("agent-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockAnalyticsApi.getAgentPnL).toHaveBeenCalledWith("agent-1", undefined);
    expect(result.current.summary).toEqual(mockAgentPnLData.summary);
    expect(result.current.trades).toEqual(mockAgentPnLData.trades);
    expect(result.current.total).toBe(1);
  });

  it("should pass options to API", async () => {
    mockAnalyticsApi.getAgentPnL.mockResolvedValue(mockAgentPnLData);

    const options = { startDate: "2024-01-01", limit: 10 };
    renderHook(() => useAgentPnL("agent-1", options), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockAnalyticsApi.getAgentPnL).toHaveBeenCalled());

    expect(mockAnalyticsApi.getAgentPnL).toHaveBeenCalledWith("agent-1", options);
  });

  it("should return empty array for trades when no data", async () => {
    mockAnalyticsApi.getAgentPnL.mockResolvedValue({ summary: null, trades: [], total: 0 });

    const { result } = renderHook(() => useAgentPnL("agent-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.trades).toEqual([]);
    expect(result.current.total).toBe(0);
  });
});

describe("useAccountAgents", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch when accountId is null", () => {
    mockAnalyticsApi.getAccountAgents.mockResolvedValue(mockAccountAgentsData);

    renderHook(() => useAccountAgents(null), { wrapper: createWrapper() });

    expect(mockAnalyticsApi.getAccountAgents).not.toHaveBeenCalled();
  });

  it("should fetch account agents", async () => {
    mockAnalyticsApi.getAccountAgents.mockResolvedValue(mockAccountAgentsData);

    const { result } = renderHook(() => useAccountAgents("account-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.agents).toHaveLength(1));

    expect(mockAnalyticsApi.getAccountAgents).toHaveBeenCalledWith("account-1");
    expect(result.current.agents[0].name).toBe("Test Agent");
    expect(result.current.total).toBe(1);
  });
});

describe("useEquityCurve", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch when accountId is null", () => {
    mockAnalyticsApi.getEquityCurve.mockResolvedValue(mockEquityCurveData);

    renderHook(() => useEquityCurve(null), { wrapper: createWrapper() });

    expect(mockAnalyticsApi.getEquityCurve).not.toHaveBeenCalled();
  });

  it("should fetch equity curve data", async () => {
    mockAnalyticsApi.getEquityCurve.mockResolvedValue(mockEquityCurveData);

    const { result } = renderHook(() => useEquityCurve("account-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.dataPoints).toHaveLength(2));

    expect(mockAnalyticsApi.getEquityCurve).toHaveBeenCalledWith("account-1", undefined);
    expect(result.current.startDate).toBe("2024-01-01");
    expect(result.current.granularity).toBe("day");
  });

  it("should pass options to API", async () => {
    mockAnalyticsApi.getEquityCurve.mockResolvedValue(mockEquityCurveData);

    const options = { granularity: "week" as const };
    renderHook(() => useEquityCurve("account-1", options), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(mockAnalyticsApi.getEquityCurve).toHaveBeenCalled());

    expect(mockAnalyticsApi.getEquityCurve).toHaveBeenCalledWith("account-1", options);
  });
});

describe("useAccountPnL", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch when accountId is null", () => {
    mockAnalyticsApi.getAccountPnL.mockResolvedValue(mockAccountPnLData);

    renderHook(() => useAccountPnL(null), { wrapper: createWrapper() });

    expect(mockAnalyticsApi.getAccountPnL).not.toHaveBeenCalled();
  });

  it("should fetch account P&L", async () => {
    mockAnalyticsApi.getAccountPnL.mockResolvedValue(mockAccountPnLData);

    const { result } = renderHook(() => useAccountPnL("account-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockAnalyticsApi.getAccountPnL).toHaveBeenCalledWith("account-1");
    expect(result.current.data?.total_pnl).toBe(2000.0);
  });
});

describe("useSyncAccount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return null when accountId is null", async () => {
    const { result } = renderHook(() => useSyncAccount(null), {
      wrapper: createWrapper(),
    });

    let syncResult: unknown;
    await act(async () => {
      syncResult = await result.current.sync();
    });

    expect(syncResult).toBeNull();
    expect(mockAnalyticsApi.syncAccount).not.toHaveBeenCalled();
  });

  it("should sync account successfully", async () => {
    const mockSyncResponse = { status: "completed", timestamp: "2024-01-01T00:00:00Z" };
    mockAnalyticsApi.syncAccount.mockResolvedValue(mockSyncResponse);

    const { result } = renderHook(() => useSyncAccount("account-1"), {
      wrapper: createWrapper(),
    });

    let syncResult: unknown;
    await act(async () => {
      syncResult = await result.current.sync();
    });

    expect(mockAnalyticsApi.syncAccount).toHaveBeenCalledWith("account-1");
    expect(syncResult).toEqual(mockSyncResponse);
    expect(result.current.isSyncing).toBe(false);
    expect(result.current.syncError).toBe(null);
  });

  it("should handle sync error", async () => {
    mockAnalyticsApi.syncAccount.mockRejectedValue(new Error("Sync failed"));

    const { result } = renderHook(() => useSyncAccount("account-1"), {
      wrapper: createWrapper(),
    });

    let syncResult: unknown;
    await act(async () => {
      syncResult = await result.current.sync();
    });

    expect(syncResult).toBeNull();
    expect(result.current.isSyncing).toBe(false);
    expect(result.current.syncError).toBeInstanceOf(Error);
    expect(result.current.syncError?.message).toBe("Sync failed");
  });

  it("should handle non-Error sync errors", async () => {
    mockAnalyticsApi.syncAccount.mockRejectedValue("String error");

    const { result } = renderHook(() => useSyncAccount("account-1"), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await result.current.sync();
    });

    expect(result.current.syncError).toBeInstanceOf(Error);
    expect(result.current.syncError?.message).toBe("Sync failed");
  });
});
