import { render, screen } from "@testing-library/react";

import { TradingDecisionCards } from "@/components/decisions/trading-decision-cards";
import type { DecisionResponse } from "@/lib/api";

const labels = {
  title: "Trading Decisions",
  leverage: "Leverage",
  size: "Size",
  stopLoss: "Stop Loss",
  takeProfit: "Take Profit",
};

const getActionColor = () => "bg-muted";

const decisions: DecisionResponse["decisions"] = [
  {
    symbol: "BTC",
    action: "open_long",
    leverage: 3,
    position_size_usd: 150,
    confidence: 82,
    risk_usd: 10,
    reasoning: "Momentum breakout",
    stop_loss: 49000,
    take_profit: 53000,
  },
];

describe("TradingDecisionCards", () => {
  it("renders nothing for empty decisions", () => {
    const { container } = render(
      <TradingDecisionCards
        decisions={[]}
        labels={labels}
        getActionColor={getActionColor}
      />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders decision card with default display values", () => {
    render(
      <TradingDecisionCards
        decisions={decisions}
        labels={labels}
        getActionColor={getActionColor}
      />,
    );

    expect(screen.getByText("Trading Decisions")).toBeInTheDocument();
    expect(screen.getByText("BTC")).toBeInTheDocument();
    expect(screen.getByText("OPEN LONG")).toBeInTheDocument();
    expect(screen.getByText("3x")).toBeInTheDocument();
    expect(screen.getByText("$150")).toBeInTheDocument();
    expect(screen.getByText("$49,000")).toBeInTheDocument();
    expect(screen.getByText("$53,000")).toBeInTheDocument();
    expect(screen.getByText("Momentum breakout")).toBeInTheDocument();
  });

  it("uses resolveDisplay override", () => {
    render(
      <TradingDecisionCards
        decisions={decisions}
        labels={labels}
        getActionColor={getActionColor}
        resolveDisplay={() => ({ leverage: 9, sizeUsd: 999 })}
      />,
    );

    expect(screen.getByText("9x")).toBeInTheDocument();
    expect(screen.getByText("$999")).toBeInTheDocument();
  });

  it("hides leverage/size grid for hold action", () => {
    render(
      <TradingDecisionCards
        decisions={[
          {
            symbol: "ETH",
            action: "hold",
            leverage: 1,
            position_size_usd: 0,
            confidence: 70,
            risk_usd: 0,
            reasoning: "No setup",
          },
        ]}
        labels={labels}
        getActionColor={getActionColor}
      />,
    );

    expect(screen.getByText("HOLD")).toBeInTheDocument();
    expect(screen.queryByText("Leverage")).not.toBeInTheDocument();
    expect(screen.queryByText("Size")).not.toBeInTheDocument();
  });

  it("aggregates repeated decisions with same symbol/action", () => {
    render(
      <TradingDecisionCards
        decisions={[
          {
            symbol: "BTC",
            action: "open_long",
            leverage: 3,
            position_size_usd: 100,
            confidence: 80,
            risk_usd: 0,
            reasoning: "grid_buy_signal",
          },
          {
            symbol: "BTC",
            action: "open_long",
            leverage: 3,
            position_size_usd: 120,
            confidence: 90,
            risk_usd: 0,
            reasoning: "grid_buy_signal",
          },
        ]}
        labels={labels}
        getActionColor={getActionColor}
      />,
    );

    expect(screen.getByText("x2")).toBeInTheDocument();
    expect(screen.getByText("$220")).toBeInTheDocument();
    expect(screen.getByText("85%")).toBeInTheDocument();
  });
});
