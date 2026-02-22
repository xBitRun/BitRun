"use client";

import { useMemo } from "react";
import { Activity, AlertCircle, CheckCircle2, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DecisionExecutionResult } from "@/lib/api";
import {
  aggregateExecutionResults,
  executionReason,
} from "@/lib/decision-view-model";
import { cn } from "@/lib/utils";

interface ExecutionRecordLabels {
  title: string;
  success: string;
  failed: string;
  skipped: string;
  reason: string;
  orderId: string;
  filledSize: string;
  filledPrice: string;
  status: string;
  requestedSize: string;
  actualSize: string;
}

interface ExecutionRecordsProps {
  records: DecisionExecutionResult[];
  labels: ExecutionRecordLabels;
  getActionColor: (action: string) => string;
}

export function ExecutionRecords({
  records,
  labels,
  getActionColor,
}: ExecutionRecordsProps) {
  if (!records?.length) return null;

  const aggregated = useMemo(() => aggregateExecutionResults(records), [records]);

  return (
    <div>
      <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
        <Activity className="w-4 h-4 text-primary" />
        {labels.title}
      </h4>
      <div className="space-y-3">
        {aggregated.map((er, i) => {
          const wasExecuted = er.executed === true;
          const orderResult = er.order_result ?? null;
          const hasFailed = wasExecuted === false && orderResult?.error != null;
          return (
            <div
              key={i}
              className={cn(
                "p-4 rounded-lg border",
                wasExecuted
                  ? "bg-[var(--profit)]/5 border-[var(--profit)]/20"
                  : hasFailed
                    ? "bg-[var(--loss)]/5 border-[var(--loss)]/20"
                    : "bg-muted/30 border-border/30",
              )}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between mb-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-base font-semibold">{er.symbol}</span>
                  <Badge
                    variant="outline"
                    className={cn("text-xs", getActionColor(er.action))}
                  >
                    {er.action?.replace("_", " ").toUpperCase()}
                  </Badge>
                  {er.count > 1 && (
                    <Badge variant="secondary" className="text-xs font-mono">
                      x{er.count}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-1.5 sm:justify-end">
                  {wasExecuted ? (
                    <>
                      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--profit)]" />
                      <span className="text-sm font-medium text-[var(--profit)]">
                        {labels.success}
                      </span>
                    </>
                  ) : hasFailed ? (
                    <>
                      <XCircle className="w-3.5 h-3.5 text-[var(--loss)]" />
                      <span className="text-sm font-medium text-[var(--loss)]">
                        {labels.failed}
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertCircle className="w-3.5 h-3.5 text-muted-foreground" />
                      <span className="text-sm font-medium text-muted-foreground">
                        {labels.skipped}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {wasExecuted && orderResult && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-sm">
                  {orderResult.order_id != null && (
                    <div>
                      <span className="text-muted-foreground">
                        {labels.orderId}
                      </span>
                      <p className="font-mono font-medium break-all">
                        {String(orderResult.order_id)}
                      </p>
                    </div>
                  )}
                  {orderResult.filled_size != null && (
                    <div>
                      <span className="text-muted-foreground">
                        {labels.filledSize}
                      </span>
                      <p className="font-mono font-medium">
                        {Number(orderResult.filled_size)}
                      </p>
                    </div>
                  )}
                  {orderResult.filled_price != null && (
                    <div>
                      <span className="text-muted-foreground">
                        {labels.filledPrice}
                      </span>
                      <p className="font-mono font-medium">
                        ${Number(orderResult.filled_price).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {orderResult.status != null && (
                    <div>
                      <span className="text-muted-foreground">{labels.status}</span>
                      <p className="font-mono font-medium">
                        {String(orderResult.status)}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {wasExecuted &&
                er.requested_size_usd != null &&
                er.actual_size_usd != null && (
                  <div className="flex flex-col gap-1 sm:flex-row sm:gap-4 mt-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">
                        {labels.requestedSize}
                      </span>
                      <span className="font-mono font-medium ml-1">
                        ${Number(er.requested_size_usd).toLocaleString()}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">
                        {labels.actualSize}
                      </span>
                      <span className="font-mono font-medium ml-1">
                        ${Number(er.actual_size_usd).toLocaleString()}
                      </span>
                    </div>
                  </div>
                )}

              {!wasExecuted && executionReason(er) && (
                <div className="text-sm mt-1 break-words">
                  <span className="text-muted-foreground">{labels.reason}: </span>
                  <span className="text-muted-foreground/80">
                    {executionReason(er)}
                  </span>
                </div>
              )}

              {hasFailed && orderResult?.error != null && (
                <div className="text-sm mt-1 break-words">
                  <span className="text-[var(--loss)]">{labels.reason}: </span>
                  <span className="text-[var(--loss)]/80">
                    {String(orderResult.error)}
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
