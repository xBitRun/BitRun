/**
 * Tests for useDecisions hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useRecentDecisions,
  useStrategyDecisions,
  useDecision,
  useDecisionStats,
  useLatestDecision,
} from "@/hooks/use-decisions";
import { decisionsApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  decisionsApi: {
    listRecent: jest.fn(),
    listByStrategy: jest.fn(),
    listByAgent: jest.fn(),
    get: jest.fn(),
    getStats: jest.fn(),
    getStatsByAgent: jest.fn(),
  },
}));

const mockedDecisionsApi = decisionsApi as jest.Mocked<typeof decisionsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockDecision = {
  id: "decision-1",
  strategy_id: "strategy-1",
  timestamp: "2024-01-15T10:00:00Z",
  chain_of_thought: "BTC showing strong momentum...",
  market_assessment: "Bullish trend",
  decisions: [
    {
      symbol: "BTC",
      action: "open_long",
      leverage: 3,
      position_size_usd: 1000,
      entry_price: 42000,
      stop_loss: 40000,
      take_profit: 46000,
      confidence: 85,
      risk_usd: 50,
      reasoning: "Strong upward momentum",
    },
  ],
  overall_confidence: 85,
  executed: true,
  execution_results: [],
  ai_model: "deepseek:deepseek-chat",
  tokens_used: 1500,
  latency_ms: 2300,
  market_snapshot: null,
  account_snapshot: null,
};

const mockDecisions = [
  mockDecision,
  {
    ...mockDecision,
    id: "decision-2",
    timestamp: "2024-01-15T08:00:00Z",
    overall_confidence: 70,
    executed: false,
    decisions: [
      {
        symbol: "ETH",
        action: "hold",
        leverage: 1,
        position_size_usd: 0,
        confidence: 70,
        risk_usd: 0,
        reasoning: "No clear signal",
      },
    ],
  },
  {
    ...mockDecision,
    id: "decision-3",
    strategy_id: "strategy-2",
    timestamp: "2024-01-15T06:00:00Z",
    overall_confidence: 90,
  },
];

const mockStats = {
  total_decisions: 100,
  executed_decisions: 75,
  average_confidence: 78.5,
  average_latency_ms: 2100,
};

describe("useRecentDecisions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch recent decisions", async () => {
    mockedDecisionsApi.listRecent.mockResolvedValue(mockDecisions);

    const { result } = renderHook(() => useRecentDecisions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDecisionsApi.listRecent).toHaveBeenCalledWith(20);
    expect(result.current.data).toEqual(mockDecisions);
    expect(result.current.data?.length).toBe(3);
  });

  it("should fetch with custom limit", async () => {
    mockedDecisionsApi.listRecent.mockResolvedValue([mockDecisions[0]]);

    const { result } = renderHook(() => useRecentDecisions(5), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDecisionsApi.listRecent).toHaveBeenCalledWith(5);
  });

  it("should handle fetch error", async () => {
    mockedDecisionsApi.listRecent.mockRejectedValue(
      new Error("Network error")
    );

    const { result } = renderHook(() => useRecentDecisions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useStrategyDecisions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch decisions for a strategy", async () => {
    const strategyDecisions = mockDecisions.filter(
      (d) => d.strategy_id === "strategy-1"
    );
    mockedDecisionsApi.listByStrategy.mockResolvedValue({
      items: strategyDecisions,
      total: strategyDecisions.length,
      limit: 10,
      offset: 0,
    });

    const { result } = renderHook(
      () => useStrategyDecisions("strategy-1"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDecisionsApi.listByStrategy).toHaveBeenCalledWith(
      "strategy-1",
      10,
      0,
      "all",
      undefined
    );
    expect(result.current.data?.items?.length).toBe(2);
  });

  it("should not fetch when strategyId is null", async () => {
    const { result } = renderHook(() => useStrategyDecisions(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedDecisionsApi.listByStrategy).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });

  it("should return loading state initially", () => {
    mockedDecisionsApi.listByStrategy.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(
      () => useStrategyDecisions("strategy-1"),
      { wrapper: createWrapper() }
    );

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useDecision", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single decision", async () => {
    mockedDecisionsApi.get.mockResolvedValue(mockDecision);

    const { result } = renderHook(() => useDecision("decision-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDecisionsApi.get).toHaveBeenCalledWith("decision-1");
    expect(result.current.data).toEqual(mockDecision);
    expect(result.current.data?.overall_confidence).toBe(85);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useDecision(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedDecisionsApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useDecisionStats", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch decision stats", async () => {
    mockedDecisionsApi.getStats.mockResolvedValue(mockStats);

    const { result } = renderHook(() => useDecisionStats("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedDecisionsApi.getStats).toHaveBeenCalledWith("strategy-1");
    expect(result.current.data?.total_decisions).toBe(100);
    expect(result.current.data?.executed_decisions).toBe(75);
    expect(result.current.data?.average_confidence).toBe(78.5);
  });

  it("should not fetch when strategyId is undefined", async () => {
    const { result } = renderHook(() => useDecisionStats(), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedDecisionsApi.getStats).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useLatestDecision", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return the latest decision for an agent", async () => {
    mockedDecisionsApi.listByAgent.mockResolvedValue({
      items: [mockDecision],
      total: 1,
      limit: 1,
      offset: 0,
    });

    const { result } = renderHook(() => useLatestDecision("strategy-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current).not.toBeNull());

    expect(mockedDecisionsApi.listByAgent).toHaveBeenCalledWith(
      "strategy-1",
      1,
      0,
      "all",
      undefined
    );
    expect(result.current?.id).toBe("decision-1");
  });

  it("should return null when no decisions", async () => {
    mockedDecisionsApi.listByAgent.mockResolvedValue({
      items: [],
      total: 0,
      limit: 1,
      offset: 0,
    });

    const { result } = renderHook(() => useLatestDecision("strategy-1"), {
      wrapper: createWrapper(),
    });

    // Initially null, remains null after empty response
    await waitFor(() =>
      expect(mockedDecisionsApi.listByAgent).toHaveBeenCalled()
    );

    expect(result.current).toBeNull();
  });

  it("should return null when strategyId is null", async () => {
    const { result } = renderHook(() => useLatestDecision(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedDecisionsApi.listByAgent).not.toHaveBeenCalled();
    expect(result.current).toBeNull();
  });
});
