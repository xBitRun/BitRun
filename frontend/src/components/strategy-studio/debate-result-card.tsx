"use client";

import {
  Users,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  Zap,
  AlertCircle,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { DebateParticipant, DebateResultSummary, ConsensusMode } from "@/types";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import { getModelDisplayName } from "@/hooks";
import type { AIModelInfoResponse } from "@/lib/api/endpoints";

interface DebateResultCardProps {
  summary: DebateResultSummary;
  participants: DebateParticipant[];
  consensusReasoning?: string;
  finalDecisions?: {
    symbol: string;
    action: string;
    confidence: number;
  }[];
  /** Models list for resolving display names */
  models?: AIModelInfoResponse[];
}

export function DebateResultCard({
  summary,
  participants,
  consensusReasoning,
  finalDecisions = [],
  models = [],
}: DebateResultCardProps) {
  const t = useTranslations("strategyStudio");

  const getConsensusModeLabel = (mode: ConsensusMode) => {
    const labels: Record<ConsensusMode, string> = {
      majority_vote: t("debate.consensusModes.majorityVote"),
      highest_confidence: t("debate.consensusModes.highestConfidence"),
      weighted_average: t("debate.consensusModes.weightedAverage"),
      unanimous: t("debate.consensusModes.unanimous"),
    };
    return labels[mode] || mode;
  };

  const getActionIcon = (action: string) => {
    if (action.includes("long") || action.includes("buy")) {
      return <TrendingUp className="h-4 w-4 text-profit" />;
    }
    if (action.includes("short") || action.includes("sell")) {
      return <TrendingDown className="h-4 w-4 text-loss" />;
    }
    return <Minus className="h-4 w-4 text-muted-foreground" />;
  };

  const getAgreementColor = (score: number) => {
    if (score >= 0.8) return "text-profit";
    if (score >= 0.5) return "text-warning";
    return "text-loss";
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Users className="h-5 w-5 text-primary" />
            {t("debate.resultTitle")}
          </CardTitle>
          <Badge variant="outline">
            {getConsensusModeLabel(summary.consensusMode)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4">
          <div className="p-3 rounded-lg bg-muted/30 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <CheckCircle className="h-4 w-4 text-profit" />
              <span className="text-2xl font-bold">{summary.successful}</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {t("debate.successfulModels")}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-muted/30 text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              <XCircle className="h-4 w-4 text-loss" />
              <span className="text-2xl font-bold">{summary.failed}</span>
            </div>
            <span className="text-xs text-muted-foreground">
              {t("debate.failedModels")}
            </span>
          </div>
          <div className="p-3 rounded-lg bg-muted/30 text-center">
            <div
              className={cn(
                "flex items-center justify-center gap-1 mb-1",
                getAgreementColor(summary.agreementScore)
              )}
            >
              <Zap className="h-4 w-4" />
              <span className="text-2xl font-bold">
                {Math.round(summary.agreementScore * 100)}%
              </span>
            </div>
            <span className="text-xs text-muted-foreground">
              {t("debate.agreement")}
            </span>
          </div>
        </div>

        {/* Agreement Score Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{t("debate.modelAgreement")}</span>
            <span className={getAgreementColor(summary.agreementScore)}>
              {Math.round(summary.agreementScore * 100)}%
            </span>
          </div>
          <Progress
            value={summary.agreementScore * 100}
            className="h-2"
          />
        </div>

        {/* Final Decisions */}
        {finalDecisions.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary" />
              {t("debate.consensusDecisions")}
            </h4>
            <div className="space-y-2">
              {finalDecisions.map((decision, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 rounded-lg bg-muted/30"
                >
                  <div className="flex items-center gap-2">
                    {getActionIcon(decision.action)}
                    <span className="font-medium">{decision.symbol}</span>
                    <Badge
                      variant={
                        decision.action.includes("long") ||
                        decision.action.includes("buy")
                          ? "default"
                          : decision.action.includes("short") ||
                            decision.action.includes("sell")
                          ? "destructive"
                          : "secondary"
                      }
                    >
                      {decision.action.replace("_", " ")}
                    </Badge>
                  </div>
                  <span className="text-sm text-muted-foreground">
                    {decision.confidence}% {t("debate.confidence")}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Consensus Reasoning */}
        {consensusReasoning && (
          <div className="p-3 rounded-lg bg-muted/20 border border-border/50">
            <p className="text-sm text-muted-foreground whitespace-pre-wrap">
              {consensusReasoning}
            </p>
          </div>
        )}

        {/* Individual Model Responses */}
        <Collapsible>
          <CollapsibleTrigger className="w-full flex items-center justify-between p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
            <span className="text-sm font-medium">
              {t("debate.viewModelResponses")}
            </span>
            <Badge variant="outline">{participants.length}</Badge>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3 space-y-2">
            {participants.map((participant, idx) => (
              <div
                key={idx}
                className={cn(
                  "p-3 rounded-lg border",
                  participant.succeeded
                    ? "border-border/50 bg-background/30"
                    : "border-destructive/30 bg-destructive/5"
                )}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {participant.succeeded ? (
                      <CheckCircle className="h-4 w-4 text-profit" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-loss" />
                    )}
                    <span className="font-medium text-sm">
                      {getModelDisplayName(participant.modelId, models)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {participant.latencyMs}ms
                    </span>
                    {participant.succeeded && (
                      <Badge
                        variant={
                          participant.confidence >= 70 ? "default" : "outline"
                        }
                      >
                        {participant.confidence}%
                      </Badge>
                    )}
                  </div>
                </div>

                {participant.succeeded && participant.decisions.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {participant.decisions.map((d, didx) => (
                      <Badge
                        key={didx}
                        variant="outline"
                        className="text-xs"
                      >
                        {d.symbol}: {d.action.replace("_", " ")} ({d.confidence}
                        %)
                      </Badge>
                    ))}
                  </div>
                )}

                {!participant.succeeded && participant.error && (
                  <p className="text-xs text-loss mt-1">{participant.error}</p>
                )}
              </div>
            ))}
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
    </Card>
  );
}
