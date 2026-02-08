"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import {
  Brain,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  XCircle,
  Activity,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { useRecentDecisions } from "@/hooks";
import { MarketSnapshotSection, AccountSnapshotSection } from "@/components/decisions/snapshot-sections";

function getActionColor(action: string) {
  switch (action) {
    case "open_long":
      return "bg-[var(--profit)]/20 text-[var(--profit)] border-[var(--profit)]/30";
    case "open_short":
      return "bg-[var(--loss)]/20 text-[var(--loss)] border-[var(--loss)]/30";
    case "close_long":
    case "close_short":
      return "bg-muted text-foreground border-border";
    case "hold":
    case "wait":
      return "bg-[var(--warning)]/20 text-[var(--warning)] border-[var(--warning)]/30";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function DecisionsSkeleton() {
  return (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <Card key={i} className="bg-card/50 backdrop-blur-sm border-border/50">
          <CardHeader>
            <div className="flex items-center gap-4">
              <Skeleton className="w-10 h-10 rounded-lg" />
              <div className="space-y-2 flex-1">
                <Skeleton className="h-5 w-40" />
                <Skeleton className="h-4 w-60" />
              </div>
              <Skeleton className="h-6 w-24" />
            </div>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}

export default function DecisionsPage() {
  const t = useTranslations("decisions");
  const tAgent = useTranslations("agentDetail");
  const [filter, setFilter] = useState<string>("all");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // Fetch real decisions from API
  const { data: decisions, error, isLoading, mutate } = useRecentDecisions(50);

  const toggleExpanded = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Filter decisions based on executed status
  const filteredDecisions = (decisions || []).filter((d) => {
    if (filter === "all") return true;
    if (filter === "executed") return d.executed;
    if (filter === "skipped") return !d.executed;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => mutate()}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Input
            placeholder={t("searchPlaceholder")}
            className="bg-muted/50"
          />
        </div>
        <Select value={filter} onValueChange={setFilter}>
          <SelectTrigger className="w-40 bg-muted/50">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t("filter.allDecisions")}</SelectItem>
            <SelectItem value="executed">{t("filter.executed")}</SelectItem>
            <SelectItem value="skipped">{t("filter.skipped")}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Loading State */}
      {isLoading && <DecisionsSkeleton />}

      {/* Error State */}
      {error && (
        <Card className="bg-destructive/10 border-destructive/30">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="w-5 h-5 text-destructive" />
            <p className="text-destructive">
              {error.message || "Failed to load decisions"}
            </p>
            <Button variant="outline" size="sm" onClick={() => mutate()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Decision Cards */}
      {!isLoading && !error && (
        <div className="space-y-4">
          {filteredDecisions.length === 0 ? (
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <Brain className="w-12 h-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No Decisions Yet</h3>
                <p className="text-muted-foreground text-center">
                  AI decisions will appear here once your strategies start running.
                </p>
              </CardContent>
            </Card>
          ) : (
            filteredDecisions.map((decision) => (
          <Collapsible
            key={decision.id}
            open={expandedIds.has(decision.id)}
            onOpenChange={() => toggleExpanded(decision.id)}
          >
            <Card className="bg-card/50 backdrop-blur-sm border-border/50">
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Brain className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <CardTitle className="text-base">
                            {t("card.decision")} #{decision.id.slice(0, 8)}
                          </CardTitle>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-xs",
                              decision.executed
                                ? "bg-[var(--profit)]/20 text-[var(--profit)]"
                                : "bg-muted text-muted-foreground"
                            )}
                          >
                            {decision.executed ? (
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                            ) : (
                              <AlertCircle className="w-3 h-3 mr-1" />
                            )}
                            {decision.executed
                              ? t("card.executed")
                              : t("card.skipped")}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                          <Clock className="w-3 h-3" />
                          {new Date(decision.timestamp).toLocaleString()}
                          <span className="mx-1">•</span>
                          {t("card.confidence")}: {decision.overall_confidence}%
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {/* Action Badges */}
                      <div className="flex gap-2">
                        {decision.decisions.map((d, i) => (
                          <Badge
                            key={i}
                            variant="outline"
                            className={cn("text-xs", getActionColor(d.action))}
                          >
                            {d.symbol} {d.action.replace("_", " ").toUpperCase()}
                          </Badge>
                        ))}
                      </div>
                      {expandedIds.has(decision.id) ? (
                        <ChevronDown className="w-5 h-5 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="pt-0 space-y-6">
                  {/* Market Assessment */}
                  <div className="p-4 rounded-lg bg-muted/30 border border-border/30">
                    <h4 className="text-sm font-semibold mb-2">
                      {t("details.marketAssessment")}
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      {decision.market_assessment}
                    </p>
                  </div>

                  {/* Account Snapshot */}
                  {decision.account_snapshot && (
                    <AccountSnapshotSection snapshot={decision.account_snapshot} t={tAgent} />
                  )}

                  {/* Market Data Snapshot */}
                  {decision.market_snapshot && decision.market_snapshot.length > 0 && (
                    <MarketSnapshotSection snapshot={decision.market_snapshot} t={tAgent} />
                  )}

                  {/* Chain of Thought */}
                  <div>
                    <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <Brain className="w-4 h-4 text-primary" />
                      {t("details.chainOfThought")}
                    </h4>
                    <div className="p-4 rounded-lg bg-muted/20 border border-border/30 font-mono text-sm whitespace-pre-wrap text-muted-foreground">
                      {decision.chain_of_thought}
                    </div>
                  </div>

                  {/* Trading Decisions */}
                  <div>
                    <h4 className="text-sm font-semibold mb-3">
                      {t("details.tradingDecisions")}
                    </h4>
                    <div className="space-y-3">
                      {decision.decisions.map((d, i) => (
                        <div
                          key={i}
                          className="p-4 rounded-lg bg-muted/30 border border-border/30"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-3">
                              <span className="text-lg font-bold">
                                {d.symbol}
                              </span>
                              <Badge
                                variant="outline"
                                className={cn(getActionColor(d.action))}
                              >
                                {d.action.replace("_", " ").toUpperCase()}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-2">
                              <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                                <div
                                  className={cn(
                                    "h-full rounded-full",
                                    d.confidence >= 80
                                      ? "bg-[var(--profit)]"
                                      : d.confidence >= 60
                                      ? "bg-[var(--warning)]"
                                      : "bg-muted-foreground"
                                  )}
                                  style={{ width: `${d.confidence}%` }}
                                />
                              </div>
                              <span className="text-sm font-medium">
                                {d.confidence}%
                              </span>
                            </div>
                          </div>
                          {d.action !== "hold" && d.action !== "wait" && (
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">
                                  {t("details.leverage")}
                                </span>
                                <p className="font-mono font-semibold">
                                  {d.leverage}x
                                </p>
                              </div>
                              <div>
                                <span className="text-muted-foreground">
                                  {t("details.size")}
                                </span>
                                <p className="font-mono font-semibold">
                                  ${d.position_size_usd.toLocaleString()}
                                </p>
                              </div>
                              {d.stop_loss && (
                                <div>
                                  <span className="text-muted-foreground">
                                    {t("details.stopLoss")}
                                  </span>
                                  <p className="font-mono font-semibold text-[var(--loss)]">
                                    ${d.stop_loss.toLocaleString()}
                                  </p>
                                </div>
                              )}
                              {d.take_profit && (
                                <div>
                                  <span className="text-muted-foreground">
                                    {t("details.takeProfit")}
                                  </span>
                                  <p className="font-mono font-semibold text-[var(--profit)]">
                                    ${d.take_profit.toLocaleString()}
                                  </p>
                                </div>
                              )}
                            </div>
                          )}
                          <p className="text-sm text-muted-foreground mt-3 pt-3 border-t border-border/30">
                            {d.reasoning}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Execution Records */}
                  {decision.execution_results && decision.execution_results.length > 0 && (
                    <div>
                      <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-primary" />
                        {t("executionRecords")}
                      </h4>
                      <div className="space-y-2">
                        {(decision.execution_results as Array<Record<string, unknown>>).map((er, i) => {
                          const wasExecuted = er.executed === true;
                          const orderResult = er.order_result as Record<string, unknown> | null;
                          const hasFailed = wasExecuted === false && orderResult?.error != null;
                          return (
                            <div
                              key={i}
                              className={cn(
                                "p-3 rounded-lg border",
                                wasExecuted
                                  ? "bg-[var(--profit)]/5 border-[var(--profit)]/20"
                                  : hasFailed
                                  ? "bg-[var(--loss)]/5 border-[var(--loss)]/20"
                                  : "bg-muted/30 border-border/30"
                              )}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-sm">{String(er.symbol)}</span>
                                  <Badge variant="outline" className={cn("text-xs", getActionColor(String(er.action)))}>
                                    {String(er.action)?.replace("_", " ").toUpperCase()}
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-1.5">
                                  {wasExecuted ? (
                                    <>
                                      <CheckCircle2 className="w-3.5 h-3.5 text-[var(--profit)]" />
                                      <span className="text-xs font-medium text-[var(--profit)]">
                                        {t("execution.success")}
                                      </span>
                                    </>
                                  ) : hasFailed ? (
                                    <>
                                      <XCircle className="w-3.5 h-3.5 text-[var(--loss)]" />
                                      <span className="text-xs font-medium text-[var(--loss)]">
                                        {t("execution.failed")}
                                      </span>
                                    </>
                                  ) : (
                                    <>
                                      <AlertCircle className="w-3.5 h-3.5 text-muted-foreground" />
                                      <span className="text-xs font-medium text-muted-foreground">
                                        {t("execution.skipped")}
                                      </span>
                                    </>
                                  )}
                                </div>
                              </div>
                              {wasExecuted && orderResult && (
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                                  {orderResult.order_id != null && (
                                    <div>
                                      <span className="text-muted-foreground">{t("execution.orderId")}</span>
                                      <p className="font-mono font-medium truncate">{String(orderResult.order_id)}</p>
                                    </div>
                                  )}
                                  {orderResult.filled_size != null && (
                                    <div>
                                      <span className="text-muted-foreground">{t("execution.filledSize")}</span>
                                      <p className="font-mono font-medium">{Number(orderResult.filled_size)}</p>
                                    </div>
                                  )}
                                  {orderResult.filled_price != null && (
                                    <div>
                                      <span className="text-muted-foreground">{t("execution.filledPrice")}</span>
                                      <p className="font-mono font-medium">${Number(orderResult.filled_price).toLocaleString()}</p>
                                    </div>
                                  )}
                                  {orderResult.status != null && (
                                    <div>
                                      <span className="text-muted-foreground">{t("execution.status")}</span>
                                      <p className="font-mono font-medium">{String(orderResult.status)}</p>
                                    </div>
                                  )}
                                </div>
                              )}
                              {wasExecuted && er.requested_size_usd != null && er.actual_size_usd != null && (
                                <div className="flex gap-4 mt-2 text-xs">
                                  <div>
                                    <span className="text-muted-foreground">{t("execution.requestedSize")}</span>
                                    <span className="font-mono font-medium ml-1">${Number(er.requested_size_usd).toLocaleString()}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">{t("execution.actualSize")}</span>
                                    <span className="font-mono font-medium ml-1">${Number(er.actual_size_usd).toLocaleString()}</span>
                                  </div>
                                </div>
                              )}
                              {!wasExecuted && er.reason != null && (
                                <div className="text-xs mt-1">
                                  <span className="text-muted-foreground">{t("execution.reason")}: </span>
                                  <span className="text-muted-foreground/80">{String(er.reason)}</span>
                                </div>
                              )}
                              {hasFailed && orderResult?.error != null && (
                                <div className="text-xs mt-1">
                                  <span className="text-[var(--loss)]">{t("execution.reason")}: </span>
                                  <span className="text-[var(--loss)]/80">{String(orderResult.error)}</span>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* AI Info */}
                  <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/30">
                    <span>Model: {decision.ai_model}</span>
                    <span>Tokens: {decision.tokens_used}</span>
                    <span>Latency: {decision.latency_ms}ms</span>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        ))
          )}
        </div>
      )}
    </div>
  );
}
