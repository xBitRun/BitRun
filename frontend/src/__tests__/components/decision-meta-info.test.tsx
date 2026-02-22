import { render, screen } from "@testing-library/react";

import { DecisionMetaInfo } from "@/components/decisions/decision-meta-info";

const labels = {
  strategyType: "Strategy Type",
  model: "Model",
  tokens: "Tokens",
  latency: "Latency",
};

describe("DecisionMetaInfo", () => {
  it("shows quant strategy type in auto mode", () => {
    render(
      <DecisionMetaInfo
        aiModel="quant:grid"
        tokensUsed={0}
        latencyMs={0}
        labels={labels}
        mode="auto"
      />,
    );

    expect(screen.getByText("Strategy Type: GRID")).toBeInTheDocument();
    expect(screen.queryByText(/Model:/)).not.toBeInTheDocument();
  });

  it("shows model/tokens/latency for ai model in auto mode", () => {
    render(
      <DecisionMetaInfo
        aiModel="openai:gpt-4.1"
        tokensUsed={234}
        latencyMs={789}
        labels={labels}
        mode="auto"
      />,
    );

    expect(screen.getByText("Model: openai:gpt-4.1")).toBeInTheDocument();
    expect(screen.getByText("Tokens: 234")).toBeInTheDocument();
    expect(screen.getByText("Latency: 789ms")).toBeInTheDocument();
  });

  it("respects model formatter in ai mode", () => {
    render(
      <DecisionMetaInfo
        aiModel="quant:rsi"
        tokensUsed={12}
        latencyMs={34}
        labels={labels}
        mode="ai"
        formatModelName={(m) => `MODEL(${m})`}
      />,
    );

    expect(screen.getByText("Model: MODEL(quant:rsi)")).toBeInTheDocument();
    expect(screen.getByText("Tokens: 12")).toBeInTheDocument();
    expect(screen.getByText("Latency: 34ms")).toBeInTheDocument();
  });
});

