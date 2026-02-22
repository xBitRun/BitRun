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
import { DecisionDetailContent } from "@/components/decisions/decision-detail-content";

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
          {t("refresh")}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Input placeholder={t("searchPlaceholder")} className="bg-muted/50" />
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
              {error.message || t("error.loadFailed")}
            </p>
            <Button variant="outline" size="sm" onClick={() => mutate()}>
              {t("retry")}
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
                <h3 className="text-lg font-semibold mb-2">
                  {t("emptyTitle")}
                </h3>
                <p className="text-muted-foreground text-center">
                  {t("emptyDescription")}
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
                                    : "bg-muted text-muted-foreground",
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
                              {t("card.confidence")}:{" "}
                              {decision.overall_confidence}%
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
                                className={cn(
                                  "text-xs",
                                  getActionColor(d.action),
                                )}
                              >
                                {d.symbol}{" "}
                                {d.action.replace("_", " ").toUpperCase()}
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
                      <DecisionDetailContent
                        decision={decision}
                        snapshotT={tAgent}
                        getActionColor={getActionColor}
                        marketAssessmentTitle={t("details.marketAssessment")}
                        chainTitleKey={
                          decision.ai_model?.startsWith("quant:")
                            ? "executionReasoning"
                            : "chainOfThought"
                        }
                        tradingLabels={{
                          title: t("details.tradingDecisions"),
                          leverage: t("details.leverage"),
                          size: t("details.size"),
                          stopLoss: t("details.stopLoss"),
                          takeProfit: t("details.takeProfit"),
                        }}
                        executionLabels={{
                          title: t("executionRecords"),
                          success: t("execution.success"),
                          failed: t("execution.failed"),
                          skipped: t("execution.skipped"),
                          reason: t("execution.reason"),
                          orderId: t("execution.orderId"),
                          filledSize: t("execution.filledSize"),
                          filledPrice: t("execution.filledPrice"),
                          status: t("execution.status"),
                          requestedSize: t("execution.requestedSize"),
                          actualSize: t("execution.actualSize"),
                        }}
                        metaLabels={{
                          strategyType: "",
                          model: tAgent("decisions.model"),
                          tokens: tAgent("decisions.tokens"),
                          latency: tAgent("decisions.latency"),
                        }}
                        metaMode="ai"
                      />
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
