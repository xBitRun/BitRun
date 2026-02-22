import {
  aggregateExecutionResults,
  aggregateTradingDecisions,
  buildDecisionTradeRows,
} from "@/lib/decision-view-model";

describe("buildDecisionTradeRows", () => {
  it("calculates realized pnl percent for close executions", () => {
    const rows = buildDecisionTradeRows({
      id: "decision-1",
      agent_id: "agent-1",
      timestamp: "2026-02-22T00:00:00.000Z",
      chain_of_thought: "",
      market_assessment: "",
      decisions: [
        {
          symbol: "BTC",
          action: "close_long",
          leverage: 2,
          position_size_usd: 1000,
          confidence: 90,
          risk_usd: 0,
          reasoning: "",
        },
      ],
      overall_confidence: 90,
      executed: true,
      execution_results: [
        {
          symbol: "BTC",
          action: "close_long",
          executed: true,
          reason: "",
          reasoning: "",
          position_size_usd: 1000,
          size_usd: 1000,
          position_leverage: 2,
          realized_pnl: 50,
          order_result: {
            filled_price: 101000,
            filled_size: 0.01,
          },
        },
      ],
      ai_model: "openai:gpt-4.1",
      tokens_used: 1,
      latency_ms: 1,
      raw_response: null,
      market_snapshot: null,
      account_snapshot: null,
    });

    expect(rows).toHaveLength(1);
    expect(rows[0].realizedPnl).toBe(50);
    expect(rows[0].realizedPnlPercent).toBeCloseTo(10, 6);
  });

  it("does not set realized pnl percent when leverage is missing", () => {
    const rows = buildDecisionTradeRows({
      id: "decision-2",
      agent_id: "agent-1",
      timestamp: "2026-02-22T00:00:00.000Z",
      chain_of_thought: "",
      market_assessment: "",
      decisions: [
        {
          symbol: "ETH",
          action: "close_short",
          leverage: 0,
          position_size_usd: 1000,
          confidence: 90,
          risk_usd: 0,
          reasoning: "",
        },
      ],
      overall_confidence: 90,
      executed: true,
      execution_results: [
        {
          symbol: "ETH",
          action: "close_short",
          executed: true,
          reason: "",
          reasoning: "",
          position_size_usd: 1000,
          size_usd: 1000,
          position_leverage: 0,
          realized_pnl: -40,
          order_result: {
            filled_price: 2900,
            filled_size: 0.2,
          },
        },
      ],
      ai_model: "openai:gpt-4.1",
      tokens_used: 1,
      latency_ms: 1,
      raw_response: null,
      market_snapshot: null,
      account_snapshot: null,
    });

    expect(rows).toHaveLength(1);
    expect(rows[0].realizedPnl).toBe(-40);
    expect(rows[0].realizedPnlPercent).toBeUndefined();
  });
});

describe("aggregateTradingDecisions", () => {
  it("aggregates same symbol/action decisions", () => {
    const rows = aggregateTradingDecisions([
      {
        symbol: "BTC",
        action: "open_long",
        leverage: 2,
        position_size_usd: 100,
        confidence: 80,
        risk_usd: 0,
        reasoning: "grid_buy_signal",
      },
      {
        symbol: "BTC",
        action: "open_long",
        leverage: 2,
        position_size_usd: 120,
        confidence: 90,
        risk_usd: 0,
        reasoning: "grid_buy_signal",
      },
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0].count).toBe(2);
    expect(rows[0].sizeUsd).toBe(220);
    expect(rows[0].confidence).toBe(85);
    expect(rows[0].reasoning).toBe("grid_buy_signal");
  });
});

describe("aggregateExecutionResults", () => {
  it("aggregates executed records by symbol/action/reason", () => {
    const rows = aggregateExecutionResults([
      {
        symbol: "BTC",
        action: "open_long",
        executed: true,
        reason: "grid_buy_signal",
        reasoning: "grid_buy_signal",
        requested_size_usd: 100,
        actual_size_usd: 100,
        position_size_usd: 100,
        size_usd: 100,
        order_result: {
          order_id: "o-1",
          filled_size: 0.001,
          filled_price: 50000,
          status: "filled",
        },
      },
      {
        symbol: "BTC",
        action: "open_long",
        executed: true,
        reason: "grid_buy_signal",
        reasoning: "grid_buy_signal",
        requested_size_usd: 120,
        actual_size_usd: 120,
        position_size_usd: 120,
        size_usd: 120,
        order_result: {
          order_id: "o-2",
          filled_size: 0.002,
          filled_price: 51000,
          status: "filled",
        },
      },
    ]);

    expect(rows).toHaveLength(1);
    expect(rows[0].count).toBe(2);
    expect(rows[0].requested_size_usd).toBe(220);
    expect(rows[0].actual_size_usd).toBe(220);
    expect(rows[0].order_result?.filled_size).toBeCloseTo(0.003, 8);
    expect(rows[0].order_result?.filled_price).toBeCloseTo(50666.6666, 3);
    expect(rows[0].order_result?.order_id).toBeNull();
  });
});
