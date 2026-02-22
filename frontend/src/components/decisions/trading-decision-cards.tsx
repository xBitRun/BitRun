"use client";

import { useMemo } from "react";
import { Target } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DecisionResponse } from "@/lib/api";
import { aggregateTradingDecisions } from "@/lib/decision-view-model";
import { cn } from "@/lib/utils";

type DecisionItem = DecisionResponse["decisions"][number];

interface TradingDecisionLabels {
  title: string;
  leverage: string;
  size: string;
  stopLoss: string;
  takeProfit: string;
}

interface TradingDecisionCardsProps {
  decisions: DecisionItem[];
  labels: TradingDecisionLabels;
  getActionColor: (action: string) => string;
  resolveDisplay?: (decision: DecisionItem) => {
    leverage: number;
    sizeUsd: number;
  };
}

export function TradingDecisionCards({
  decisions,
  labels,
  getActionColor,
  resolveDisplay,
}: TradingDecisionCardsProps) {
  if (!decisions?.length) return null;

  const aggregated = useMemo(
    () => aggregateTradingDecisions(decisions, resolveDisplay),
    [decisions, resolveDisplay],
  );

  return (
    <div>
      <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
        <Target className="w-4 h-4 text-primary" />
        {labels.title}
      </h4>
      <div className="space-y-3">
        {aggregated.map((d, i) => {
          return (
            <div
              key={i}
              className="p-4 rounded-lg bg-muted/30 border border-border/30"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-3">
                <div className="flex items-center gap-3 flex-wrap">
                  <span className="text-base font-semibold">{d.symbol}</span>
                  <Badge variant="outline" className={cn(getActionColor(d.action))}>
                    {d.action.replace("_", " ").toUpperCase()}
                  </Badge>
                  {d.count > 1 && (
                    <Badge variant="secondary" className="text-xs font-mono">
                      x{d.count}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 sm:justify-end">
                  <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className={cn(
                        "h-full rounded-full",
                        d.confidence >= 80
                          ? "bg-[var(--profit)]"
                          : d.confidence >= 60
                            ? "bg-[var(--warning)]"
                            : "bg-muted-foreground",
                      )}
                      style={{ width: `${d.confidence}%` }}
                    />
                  </div>
                  <span className="text-sm font-medium">{d.confidence}%</span>
                </div>
              </div>

              {d.action !== "hold" && d.action !== "wait" && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-muted-foreground">{labels.leverage}</span>
                    <p className="font-mono font-semibold">
                      {d.leverage != null ? `${d.leverage}x` : "-"}
                    </p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{labels.size}</span>
                    <p className="font-mono font-semibold">
                      ${d.sizeUsd.toLocaleString()}
                    </p>
                  </div>
                  {d.stopLoss && (
                    <div>
                      <span className="text-muted-foreground">{labels.stopLoss}</span>
                      <p className="font-mono font-semibold text-[var(--loss)]">
                        ${d.stopLoss.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {d.takeProfit && (
                    <div>
                      <span className="text-muted-foreground">
                        {labels.takeProfit}
                      </span>
                      <p className="font-mono font-semibold text-[var(--profit)]">
                        ${d.takeProfit.toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              )}

              <p className="text-sm text-muted-foreground mt-3 pt-3 border-t border-border/30 break-words">
                {d.reasoning}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
