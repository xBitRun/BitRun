import type { DecisionExecutionResult, DecisionResponse } from "@/lib/api";

type SnapshotPosition = {
  symbol: string;
  side: string;
  size: number;
  size_usd: number;
  entry_price: number;
  mark_price: number;
  leverage: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  liquidation_price?: number | null;
};

export interface DecisionTradeRow {
  key: string;
  symbol: string;
  action: string;
  side: "long" | "short";
  isClose: boolean;
  leverage: number;
  entryPrice?: number;
  filledPrice?: number;
  filledSize?: number;
  sizeUsd?: number;
  markPrice?: number;
  unrealizedPnl?: number;
  unrealizedPnlPercent?: number;
  realizedPnl?: number | null;
  realizedPnlPercent?: number;
  timestamp: string;
}

type DecisionItem = DecisionResponse["decisions"][number];

export interface AggregatedDecisionDisplayItem {
  symbol: string;
  action: string;
  confidence: number;
  leverage: number | null;
  sizeUsd: number;
  stopLoss?: number;
  takeProfit?: number;
  reasoning: string;
  count: number;
}

export interface AggregatedExecutionResult extends DecisionExecutionResult {
  count: number;
}

function calculateRealizedPnlPercent(params: {
  realizedPnl?: number | null;
  sizeUsd?: number;
  leverage?: number;
}): number | undefined {
  const { realizedPnl, sizeUsd, leverage } = params;
  if (realizedPnl == null) return undefined;
  if (sizeUsd == null || sizeUsd <= 0) return undefined;
  if (leverage == null || leverage <= 0) return undefined;

  const marginUsed = sizeUsd / leverage;
  if (marginUsed <= 0) return undefined;

  return (realizedPnl / marginUsed) * 100;
}

export function executionReason(er: DecisionExecutionResult): string {
  if (er.order_result?.error) return er.order_result.error;
  return er.reasoning || er.reason || "";
}

export function resolveDecisionDisplay(
  decision: DecisionResponse,
  d: DecisionResponse["decisions"][number],
): { leverage: number; sizeUsd: number } {
  const isCloseAction = d.action === "close_long" || d.action === "close_short";
  if (!isCloseAction) {
    return {
      leverage: d.leverage ?? 1,
      sizeUsd: d.position_size_usd ?? 0,
    };
  }

  const snapshotPositions = (decision.account_snapshot?.positions ??
    []) as SnapshotPosition[];
  const snapshotPos = snapshotPositions.find((p) => p.symbol === d.symbol);
  const execRes = decision.execution_results.find(
    (er) => er.symbol === d.symbol && er.action === d.action,
  );

  return {
    leverage: execRes?.position_leverage ?? snapshotPos?.leverage ?? d.leverage ?? 1,
    sizeUsd:
      execRes?.position_size_usd ??
      snapshotPos?.size_usd ??
      d.position_size_usd ??
      0,
  };
}

export function buildDecisionTradeRows(
  decision: DecisionResponse,
): DecisionTradeRow[] {
  const snapshotPositions = (decision.account_snapshot?.positions ??
    []) as SnapshotPosition[];

  return decision.execution_results
    .filter((er) => er.executed === true)
    .map((er, idx) => {
      const symbol = er.symbol;
      const action = er.action;
      const aiDecision = decision.decisions.find(
        (d) => d.symbol === symbol && d.action === action,
      );
      const position = snapshotPositions.find((p) => p.symbol === symbol);
      const side = action.includes("long") ? "long" : "short";
      const isClose = action.startsWith("close");
      const leverage = isClose
        ? (er.position_leverage ?? position?.leverage ?? aiDecision?.leverage ?? 0)
        : (aiDecision?.leverage ?? position?.leverage ?? 0);
      const sizeUsd = isClose
        ? (er.position_size_usd ?? position?.size_usd)
        : (er.actual_size_usd ?? undefined);

      return {
        key: `${decision.id}-exec-${idx}`,
        symbol,
        action,
        side: side as "long" | "short",
        isClose,
        leverage,
        entryPrice: isClose
          ? (position?.entry_price ?? aiDecision?.entry_price)
          : (aiDecision?.entry_price ?? position?.entry_price),
        filledPrice: er.order_result?.filled_price ?? undefined,
        filledSize: er.order_result?.filled_size ?? undefined,
        sizeUsd,
        markPrice: position?.mark_price,
        unrealizedPnl: position?.unrealized_pnl,
        unrealizedPnlPercent: position?.unrealized_pnl_percent,
        realizedPnl: er.realized_pnl,
        realizedPnlPercent: isClose
          ? calculateRealizedPnlPercent({
              realizedPnl: er.realized_pnl,
              sizeUsd,
              leverage,
            })
          : undefined,
        timestamp: decision.timestamp,
      };
    });
}

function summarizeText(values: Set<string>): string {
  const list = [...values].filter(Boolean);
  if (list.length === 0) return "";
  if (list.length === 1) return list[0];
  return `${list[0]} (+${list.length - 1} more)`;
}

export function aggregateTradingDecisions(
  decisions: DecisionItem[],
  resolveDisplay?: (decision: DecisionItem) => { leverage: number; sizeUsd: number },
): AggregatedDecisionDisplayItem[] {
  const groups = new Map<
    string,
    {
      symbol: string;
      action: string;
      count: number;
      confidenceSum: number;
      sizeUsdSum: number;
      leverages: Set<number>;
      stopLosses: Set<number>;
      takeProfits: Set<number>;
      reasons: Set<string>;
    }
  >();

  for (const d of decisions) {
    const key = `${d.symbol}::${d.action}`;
    const display = resolveDisplay
      ? resolveDisplay(d)
      : { leverage: d.leverage ?? 1, sizeUsd: d.position_size_usd ?? 0 };

    if (!groups.has(key)) {
      groups.set(key, {
        symbol: d.symbol,
        action: d.action,
        count: 0,
        confidenceSum: 0,
        sizeUsdSum: 0,
        leverages: new Set<number>(),
        stopLosses: new Set<number>(),
        takeProfits: new Set<number>(),
        reasons: new Set<string>(),
      });
    }

    const g = groups.get(key)!;
    g.count += 1;
    g.confidenceSum += d.confidence ?? 0;
    g.sizeUsdSum += display.sizeUsd ?? 0;
    g.leverages.add(display.leverage ?? 1);
    if (d.stop_loss != null) g.stopLosses.add(d.stop_loss);
    if (d.take_profit != null) g.takeProfits.add(d.take_profit);
    if (d.reasoning) g.reasons.add(d.reasoning);
  }

  return [...groups.values()].map((g) => ({
    symbol: g.symbol,
    action: g.action,
    confidence: Math.round(g.confidenceSum / Math.max(g.count, 1)),
    leverage: g.leverages.size === 1 ? [...g.leverages][0] : null,
    sizeUsd: g.sizeUsdSum,
    stopLoss: g.stopLosses.size === 1 ? [...g.stopLosses][0] : undefined,
    takeProfit: g.takeProfits.size === 1 ? [...g.takeProfits][0] : undefined,
    reasoning: summarizeText(g.reasons),
    count: g.count,
  }));
}

export function aggregateExecutionResults(
  records: DecisionExecutionResult[],
): AggregatedExecutionResult[] {
  const groups = new Map<
    string,
    {
      count: number;
      symbol: string;
      action: string;
      executed: boolean;
      reason: string;
      reasoning: string;
      confidenceSum: number;
      confidenceCount: number;
      requestedSizeSum: number;
      requestedSizeCount: number;
      actualSizeSum: number;
      actualSizeCount: number;
      positionSizeSum: number;
      sizeUsdSum: number;
      leverageSum: number;
      leverageCount: number;
      realizedPnlSum: number;
      realizedPnlCount: number;
      orderIds: Set<string>;
      statuses: Set<string>;
      errors: Set<string>;
      filledSizeSum: number;
      filledValueSum: number;
    }
  >();

  for (const er of records) {
    const key = `${er.symbol}::${er.action}::${er.executed}::${executionReason(er)}`;
    if (!groups.has(key)) {
      groups.set(key, {
        count: 0,
        symbol: er.symbol,
        action: er.action,
        executed: er.executed,
        reason: er.reason,
        reasoning: er.reasoning,
        confidenceSum: 0,
        confidenceCount: 0,
        requestedSizeSum: 0,
        requestedSizeCount: 0,
        actualSizeSum: 0,
        actualSizeCount: 0,
        positionSizeSum: 0,
        sizeUsdSum: 0,
        leverageSum: 0,
        leverageCount: 0,
        realizedPnlSum: 0,
        realizedPnlCount: 0,
        orderIds: new Set<string>(),
        statuses: new Set<string>(),
        errors: new Set<string>(),
        filledSizeSum: 0,
        filledValueSum: 0,
      });
    }

    const g = groups.get(key)!;
    g.count += 1;
    if (er.confidence != null) {
      g.confidenceSum += er.confidence;
      g.confidenceCount += 1;
    }
    if (er.requested_size_usd != null) {
      g.requestedSizeSum += er.requested_size_usd;
      g.requestedSizeCount += 1;
    }
    if (er.actual_size_usd != null) {
      g.actualSizeSum += er.actual_size_usd;
      g.actualSizeCount += 1;
    }
    g.positionSizeSum += er.position_size_usd ?? 0;
    g.sizeUsdSum += er.size_usd ?? 0;
    if (er.position_leverage != null) {
      g.leverageSum += er.position_leverage;
      g.leverageCount += 1;
    }
    if (er.realized_pnl != null) {
      g.realizedPnlSum += er.realized_pnl;
      g.realizedPnlCount += 1;
    }

    const orderResult = er.order_result;
    if (orderResult?.order_id) g.orderIds.add(orderResult.order_id);
    if (orderResult?.status) g.statuses.add(orderResult.status);
    if (orderResult?.error) g.errors.add(orderResult.error);
    if (orderResult?.filled_size != null) {
      g.filledSizeSum += orderResult.filled_size;
      if (orderResult.filled_price != null) {
        g.filledValueSum += orderResult.filled_size * orderResult.filled_price;
      }
    }
  }

  return [...groups.values()].map((g) => {
    const filledPrice =
      g.filledSizeSum > 0 ? g.filledValueSum / g.filledSizeSum : null;
    const status =
      g.statuses.size === 0
        ? null
        : g.statuses.size === 1
          ? [...g.statuses][0]
          : "mixed";
    const error =
      g.errors.size === 0
        ? null
        : g.errors.size === 1
          ? [...g.errors][0]
          : "multiple_errors";
    const orderId = g.orderIds.size === 1 ? [...g.orderIds][0] : null;

    return {
      symbol: g.symbol,
      action: g.action,
      confidence:
        g.confidenceCount > 0 ? g.confidenceSum / g.confidenceCount : undefined,
      executed: g.executed,
      reason: g.reason,
      reasoning: g.reasoning,
      requested_size_usd:
        g.requestedSizeCount > 0 ? g.requestedSizeSum : undefined,
      actual_size_usd: g.actualSizeCount > 0 ? g.actualSizeSum : undefined,
      position_size_usd: g.positionSizeSum,
      size_usd: g.sizeUsdSum,
      position_leverage:
        g.leverageCount > 0 ? g.leverageSum / g.leverageCount : undefined,
      realized_pnl: g.realizedPnlCount > 0 ? g.realizedPnlSum : undefined,
      order_result: {
        order_id: orderId,
        filled_size: g.filledSizeSum > 0 ? g.filledSizeSum : null,
        filled_price: filledPrice,
        status,
        error,
      },
      count: g.count,
    };
  });
}
