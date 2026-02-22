import { render, screen, fireEvent } from "@testing-library/react";

import DecisionsPage from "@/app/[locale]/(dashboard)/decisions/page";

jest.mock("@/components/decisions/decision-detail-content", () => ({
  DecisionDetailContent: ({ decision }: { decision: { id: string } }) => (
    <div data-testid="decision-detail-content">{decision.id}</div>
  ),
}));

jest.mock("@/hooks", () => ({
  useRecentDecisions: jest.fn(),
}));

const { useRecentDecisions } = jest.requireMock("@/hooks") as {
  useRecentDecisions: jest.Mock;
};

describe("DecisionsPage integration", () => {
  beforeEach(() => {
    useRecentDecisions.mockReset();
    useRecentDecisions.mockReturnValue({
      data: [
        {
          id: "decision-12345678",
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
      error: undefined,
      isLoading: false,
      mutate: jest.fn(),
    });
  });

  it("renders decision detail container after expanding a decision card", () => {
    render(<DecisionsPage />);

    expect(screen.queryByTestId("decision-detail-content")).not.toBeInTheDocument();

    fireEvent.click(screen.getByText(/card\.decision/i));

    expect(screen.getByTestId("decision-detail-content")).toBeInTheDocument();
    expect(screen.getByText("decision-12345678")).toBeInTheDocument();
  });
});
