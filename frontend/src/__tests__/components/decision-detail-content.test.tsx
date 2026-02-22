import { render, screen } from "@testing-library/react";

jest.mock("@/components/ui/markdown-toggle", () => ({
  MarkdownToggle: ({ content }: { content: string }) => (
    <div data-testid="markdown-toggle">{content}</div>
  ),
}));

import { DecisionDetailContent } from "@/components/decisions/decision-detail-content";
import type { DecisionResponse } from "@/lib/api";

const baseDecision: DecisionResponse = {
  id: "d1",
  agent_id: "a1",
  timestamp: new Date().toISOString(),
  chain_of_thought: "Step 1\nStep 2",
  market_assessment: "Market is neutral",
  decisions: [
    {
      symbol: "BTC",
      action: "open_long",
      leverage: 2,
      position_size_usd: 100,
      confidence: 80,
      risk_usd: 10,
      reasoning: "Breakout setup",
    },
  ],
  overall_confidence: 80,
  executed: false,
  execution_results: [
    {
      symbol: "BTC",
      action: "open_long",
      executed: false,
      reason: "filtered_by_risk_control",
      reasoning: "filtered_by_risk_control",
      position_size_usd: 0,
      size_usd: 0,
    },
  ],
  ai_model: "openai:gpt-4.1",
  tokens_used: 123,
  latency_ms: 456,
  raw_response: null,
  market_snapshot: null,
  account_snapshot: null,
};

const labels = {
  trading: {
    title: "Trading Decisions",
    leverage: "Leverage",
    size: "Size",
    stopLoss: "Stop Loss",
    takeProfit: "Take Profit",
  },
  execution: {
    title: "Execution Records",
    success: "Success",
    failed: "Failed",
    skipped: "Skipped",
    reason: "Reason",
    orderId: "Order ID",
    filledSize: "Filled Size",
    filledPrice: "Filled Price",
    status: "Status",
    requestedSize: "Requested Size",
    actualSize: "Actual Size",
  },
  meta: {
    strategyType: "Strategy Type",
    model: "Model",
    tokens: "Tokens",
    latency: "Latency",
  },
};

const getActionColor = () => "bg-muted";
const t = (key: string) => key;

describe("DecisionDetailContent", () => {
  it("renders default sections with ai meta mode", () => {
    render(
      <DecisionDetailContent
        decision={baseDecision}
        snapshotT={t}
        getActionColor={getActionColor}
        marketAssessmentTitle="Market Assessment"
        chainTitleKey="chainOfThought"
        tradingLabels={labels.trading}
        executionLabels={labels.execution}
        metaLabels={labels.meta}
        metaMode="ai"
      />,
    );

    expect(screen.getByText("Market Assessment")).toBeInTheDocument();
    expect(screen.getByText("Market is neutral")).toBeInTheDocument();
    expect(screen.getByText("Trading Decisions")).toBeInTheDocument();
    expect(screen.getAllByText("BTC").length).toBeGreaterThan(0);
    expect(screen.getAllByText("OPEN LONG").length).toBeGreaterThan(0);
    expect(screen.getByText("Breakout setup")).toBeInTheDocument();
    expect(screen.getByText("Execution Records")).toBeInTheDocument();
    expect(screen.getByText("Skipped")).toBeInTheDocument();
    expect(screen.getAllByText("Reason:")[0]).toBeInTheDocument();
    expect(screen.getByText("Model: openai:gpt-4.1")).toBeInTheDocument();
    expect(screen.getByText("Tokens: 123")).toBeInTheDocument();
    expect(screen.getByText("Latency: 456ms")).toBeInTheDocument();
  });

  it("uses custom renderers and quant auto meta", () => {
    const quantDecision: DecisionResponse = {
      ...baseDecision,
      ai_model: "quant:grid",
      market_assessment: "custom markdown",
    };

    render(
      <DecisionDetailContent
        decision={quantDecision}
        snapshotT={t}
        getActionColor={getActionColor}
        marketAssessmentTitle="Market Assessment"
        chainTitleKey="executionReasoning"
        tradingLabels={labels.trading}
        executionLabels={labels.execution}
        metaLabels={labels.meta}
        metaMode="auto"
        renderMarketAssessmentContent={(text) => (
          <div data-testid="custom-market">{text}</div>
        )}
        renderChainSection={() => <div data-testid="custom-chain">COT</div>}
        rawSection={<div data-testid="raw-section">RAW</div>}
      />,
    );

    expect(screen.getByTestId("custom-market")).toHaveTextContent(
      "custom markdown",
    );
    expect(screen.getByTestId("custom-chain")).toHaveTextContent("COT");
    expect(screen.getByTestId("raw-section")).toHaveTextContent("RAW");
    expect(screen.getByText("Strategy Type: GRID")).toBeInTheDocument();
    expect(screen.queryByText(/Model:/)).not.toBeInTheDocument();
  });

  it("applies resolveDisplay values for trading cards", () => {
    render(
      <DecisionDetailContent
        decision={baseDecision}
        snapshotT={t}
        getActionColor={getActionColor}
        marketAssessmentTitle="Market Assessment"
        chainTitleKey="chainOfThought"
        tradingLabels={labels.trading}
        executionLabels={labels.execution}
        metaLabels={labels.meta}
        resolveDisplay={() => ({ leverage: 9, sizeUsd: 999 })}
      />,
    );

    expect(screen.getByText("9x")).toBeInTheDocument();
    expect(screen.getByText("$999")).toBeInTheDocument();
  });
});
