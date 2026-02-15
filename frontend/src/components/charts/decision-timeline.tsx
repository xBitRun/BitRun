"use client";

import { cn } from "@/lib/utils";
import { Brain, TrendingUp, TrendingDown, Minus, Clock } from "lucide-react";
import { useTranslations } from "next-intl";

interface Decision {
  id: string;
  timestamp: string;
  action: string;
  symbol: string;
  confidence: number;
  executed: boolean;
}

interface DecisionTimelineProps {
  decisions: Decision[];
  maxItems?: number;
  className?: string;
}

function getActionIcon(action: string) {
  switch (action) {
    case "open_long":
      return <TrendingUp className="w-4 h-4 text-[var(--profit)]" />;
    case "open_short":
      return <TrendingDown className="w-4 h-4 text-[var(--loss)]" />;
    case "close_long":
    case "close_short":
      return <Minus className="w-4 h-4 text-muted-foreground" />;
    default:
      return <Clock className="w-4 h-4 text-[var(--warning)]" />;
  }
}

function getActionColor(action: string) {
  switch (action) {
    case "open_long":
      return "border-[var(--profit)] bg-[var(--profit)]/10";
    case "open_short":
      return "border-[var(--loss)] bg-[var(--loss)]/10";
    case "close_long":
    case "close_short":
      return "border-muted bg-muted/30";
    default:
      return "border-[var(--warning)] bg-[var(--warning)]/10";
  }
}

function formatTimeAgo(
  timestamp: string,
  t: (key: string, values?: Record<string, string | number | Date>) => string,
): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return t("justNow");
  if (diffMins < 60) return t("minutesAgo", { count: diffMins });
  if (diffHours < 24) return t("hoursAgo", { count: diffHours });
  if (diffDays < 7) return t("daysAgo", { count: diffDays });

  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DecisionTimeline({
  decisions,
  maxItems = 10,
  className,
}: DecisionTimelineProps) {
  const tTime = useTranslations("time");
  const tCharts = useTranslations("charts.decisionTimeline");

  const displayedDecisions = decisions.slice(0, maxItems);

  if (displayedDecisions.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-8",
          className,
        )}
      >
        <Brain className="w-8 h-8 text-muted-foreground mb-2" />
        <p className="text-sm text-muted-foreground">
          {tCharts("noDecisions")}
        </p>
      </div>
    );
  }

  return (
    <div className={cn("relative", className)}>
      {/* Timeline line */}
      <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />

      {/* Timeline items */}
      <div className="space-y-4">
        {displayedDecisions.map((decision) => (
          <div
            key={decision.id}
            className="relative flex items-start gap-4 pl-2"
          >
            {/* Timeline dot */}
            <div
              className={cn(
                "relative z-10 flex items-center justify-center w-5 h-5 rounded-full border-2",
                getActionColor(decision.action),
              )}
            >
              {getActionIcon(decision.action)}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0 pb-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">
                    {decision.action.replace("_", " ").toUpperCase()}
                  </span>
                  <span className="text-sm text-muted-foreground">
                    {decision.symbol}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground shrink-0">
                  {formatTimeAgo(decision.timestamp, tTime)}
                </span>
              </div>

              <div className="flex items-center gap-2 mt-1">
                <div className="flex items-center gap-1">
                  <div
                    className={cn(
                      "w-12 h-1.5 rounded-full bg-muted overflow-hidden",
                    )}
                  >
                    <div
                      className={cn(
                        "h-full rounded-full",
                        decision.confidence >= 70
                          ? "bg-[var(--profit)]"
                          : decision.confidence >= 50
                            ? "bg-[var(--warning)]"
                            : "bg-muted-foreground",
                      )}
                      style={{ width: `${decision.confidence}%` }}
                    />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {decision.confidence}%
                  </span>
                </div>

                {decision.executed ? (
                  <span className="text-xs text-[var(--profit)]">
                    {tCharts("executed")}
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    {tCharts("skipped")}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Show more indicator */}
      {decisions.length > maxItems && (
        <div className="relative flex items-center gap-4 pl-2 text-sm text-muted-foreground">
          <div className="w-5 flex justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-muted-foreground" />
          </div>
          <span>
            {tCharts("moreDecisions", { count: decisions.length - maxItems })}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Compact decision stats bar
 */
interface DecisionStatsBarProps {
  total: number;
  executed: number;
  actions: Record<string, number>;
  className?: string;
}

export function DecisionStatsBar({
  total,
  executed,
  actions,
  className,
}: DecisionStatsBarProps) {
  const tCharts = useTranslations("charts.decisionTimeline");
  const executionRate = total > 0 ? (executed / total) * 100 : 0;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Execution rate */}
      <div>
        <div className="flex items-center justify-between text-sm mb-1">
          <span className="text-muted-foreground">
            {tCharts("executionRate")}
          </span>
          <span className="font-mono">{executionRate.toFixed(1)}%</span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-primary rounded-full"
            style={{ width: `${executionRate}%` }}
          />
        </div>
      </div>

      {/* Action distribution */}
      <div>
        <div className="text-sm text-muted-foreground mb-2">
          {tCharts("actionDistribution")}
        </div>
        <div className="flex gap-1 h-4 rounded overflow-hidden">
          {Object.entries(actions).map(([action, count]) => {
            const percentage = total > 0 ? (count / total) * 100 : 0;
            if (percentage === 0) return null;

            const bgColor =
              action === "open_long"
                ? "bg-[var(--profit)]"
                : action === "open_short"
                  ? "bg-[var(--loss)]"
                  : action.includes("close")
                    ? "bg-muted-foreground"
                    : "bg-[var(--warning)]";

            return (
              <div
                key={action}
                className={cn("h-full", bgColor)}
                style={{ width: `${percentage}%` }}
                title={`${action}: ${count} (${percentage.toFixed(1)}%)`}
              />
            );
          })}
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {Object.entries(actions).map(([action, count]) => (
            <div key={action} className="flex items-center gap-1 text-xs">
              <div
                className={cn(
                  "w-2 h-2 rounded-full",
                  action === "open_long"
                    ? "bg-[var(--profit)]"
                    : action === "open_short"
                      ? "bg-[var(--loss)]"
                      : action.includes("close")
                        ? "bg-muted-foreground"
                        : "bg-[var(--warning)]",
                )}
              />
              <span className="text-muted-foreground capitalize">
                {action.replace("_", " ")}: {count}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
