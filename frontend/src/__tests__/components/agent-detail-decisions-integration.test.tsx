import { render, screen, fireEvent } from "@testing-library/react";

import AgentDetailPage from "@/app/[locale]/(dashboard)/agents/[id]/page";

jest.mock("@/components/ui/markdown-toggle", () => ({
  MarkdownToggle: ({ content }: { content: string }) => <div>{content}</div>,
}));

jest.mock("@/components/ui/toast", () => ({
  useToast: () => ({
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  }),
}));

jest.mock("next/navigation", () => ({
  useParams: () => ({ id: "agent-1" }),
  useSearchParams: () => ({
    get: (key: string) => (key === "tab" ? "decisions" : null),
  }),
}));

jest.mock("@/components/decisions/decision-detail-content", () => ({
  DecisionDetailContent: ({ decision }: { decision: { id: string } }) => (
    <div data-testid="decision-detail-content">{decision.id}</div>
  ),
}));

jest.mock("@/hooks", () => ({
  useUserModels: jest.fn(() => ({ models: [] })),
  groupModelsByProvider: jest.fn(() => ({})),
  getProviderDisplayName: jest.fn((v: string) => v),
}));

jest.mock("@/hooks/use-agents", () => ({
  useAgent: jest.fn(() => ({
    data: {
      id: "agent-1",
      name: "Test Agent",
      description: "desc",
      status: "active",
      execution_mode: "mock",
      trade_type: "crypto_perp",
      strategy_type: "ai",
      account_name: null,
      total_trades: 0,
      total_pnl: 0,
      total_pnl_percent: 0,
      max_drawdown_percent: 0,
      win_rate: 0,
      strategy_symbols: [],
      config: {},
    },
    isLoading: false,
    error: undefined,
    mutate: jest.fn(),
  })),
  useUpdateAgentStatus: jest.fn(() => ({
    trigger: jest.fn(),
    isMutating: false,
  })),
  useAgentPositions: jest.fn(() => ({
    data: [],
    isLoading: false,
    error: undefined,
    mutate: jest.fn(),
  })),
  useAgentAccountState: jest.fn(() => ({ data: undefined })),
}));

jest.mock("@/hooks/use-decisions", () => ({
  useAgentDecisions: jest.fn(() => ({
    data: {
      items: [
        {
          id: "decision-87654321",
          agent_id: "agent-1",
          timestamp: new Date().toISOString(),
          chain_of_thought: "reasoning",
          market_assessment: "assessment",
          decisions: [
            {
              symbol: "BTC",
              action: "open_long",
              leverage: 2,
              position_size_usd: 100,
              confidence: 80,
              risk_usd: 10,
              reasoning: "breakout",
            },
          ],
          overall_confidence: 80,
          executed: true,
          execution_results: [],
          ai_model: "openai:gpt-4.1",
          tokens_used: 10,
          latency_ms: 20,
          account_snapshot: null,
          market_snapshot: null,
        },
      ],
      total: 1,
      limit: 10,
      offset: 0,
    },
    isLoading: false,
    isValidating: false,
    mutate: jest.fn(),
  })),
  useAgentDecisionStats: jest.fn(() => ({
    data: {
      total_decisions: 1,
      executed_decisions: 1,
      average_confidence: 80,
      average_latency_ms: 20,
      total_tokens: 10,
      action_counts: { open_long: 1 },
    },
    isLoading: false,
  })),
}));

jest.mock("@/lib/api", () => ({
  agentsApi: {
    trigger: jest.fn(),
  },
}));

describe("AgentDetailPage decisions integration", () => {
  it("renders decision detail container in decisions tab", () => {
    render(<AgentDetailPage />);

    expect(screen.queryByTestId("decision-detail-content")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/#decision/i));

    expect(screen.getByTestId("decision-detail-content")).toBeInTheDocument();
    expect(screen.getByText("decision-87654321")).toBeInTheDocument();
  });
});
