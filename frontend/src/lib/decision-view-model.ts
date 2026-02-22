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
