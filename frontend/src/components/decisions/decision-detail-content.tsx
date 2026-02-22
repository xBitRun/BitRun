"use client";

import type { ReactNode } from "react";
import { BarChart3 } from "lucide-react";

import {
  AccountSnapshotSection,
  MarketSnapshotSection,
} from "@/components/decisions/snapshot-sections";
import { ChainOfThought } from "@/components/decisions/chain-of-thought";
import { DecisionMetaInfo } from "@/components/decisions/decision-meta-info";
import { ExecutionRecords } from "@/components/decisions/execution-records";
import { TradingDecisionCards } from "@/components/decisions/trading-decision-cards";
import type { DecisionResponse } from "@/lib/api";

type DecisionItem = DecisionResponse["decisions"][number];

interface TradingLabels {
  title: string;
  leverage: string;
  size: string;
  stopLoss: string;
  takeProfit: string;
}

interface ExecutionLabels {
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

interface MetaLabels {
  strategyType: string;
  model: string;
  tokens: string;
  latency: string;
}

interface DecisionDetailContentProps {
  decision: DecisionResponse;
  snapshotT: (
    key: string,
    values?: Record<string, string | number | Date>,
  ) => string;
  getActionColor: (action: string) => string;

  marketAssessmentTitle: string;
  chainTitleKey: "executionReasoning" | "chainOfThought";

  tradingLabels: TradingLabels;
  executionLabels: ExecutionLabels;
  metaLabels: MetaLabels;
  metaMode?: "ai" | "auto";
  formatModelName?: (model: string) => string;

  resolveDisplay?: (d: DecisionItem) => { leverage: number; sizeUsd: number };
  renderMarketAssessmentContent?: (text: string) => ReactNode;
  renderChainSection?: (decision: DecisionResponse) => ReactNode;
  rawSection?: ReactNode;
}

export function DecisionDetailContent({
  decision,
  snapshotT,
  getActionColor,
  marketAssessmentTitle,
  chainTitleKey,
  tradingLabels,
  executionLabels,
  metaLabels,
  metaMode = "auto",
  formatModelName,
  resolveDisplay,
  renderMarketAssessmentContent,
  renderChainSection,
  rawSection,
}: DecisionDetailContentProps) {
  return (
    <>
      {decision.account_snapshot && (
        <AccountSnapshotSection snapshot={decision.account_snapshot} t={snapshotT} />
      )}

      {decision.market_snapshot && decision.market_snapshot.length > 0 && (
        <MarketSnapshotSection snapshot={decision.market_snapshot} t={snapshotT} />
      )}

      <div className="p-4 rounded-lg bg-muted/30 border border-border/30">
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <BarChart3 className="w-4 h-4 text-primary" />
          {marketAssessmentTitle}
        </h4>
        {renderMarketAssessmentContent ? (
          renderMarketAssessmentContent(decision.market_assessment)
        ) : (
          <p className="text-sm text-muted-foreground">
            {decision.market_assessment}
          </p>
        )}
      </div>

      {renderChainSection ? (
        renderChainSection(decision)
      ) : (
        <ChainOfThought content={decision.chain_of_thought} titleKey={chainTitleKey} />
      )}

      <TradingDecisionCards
        decisions={decision.decisions}
        getActionColor={getActionColor}
        resolveDisplay={resolveDisplay}
        labels={tradingLabels}
      />

      <ExecutionRecords
        records={decision.execution_results}
        getActionColor={getActionColor}
        labels={executionLabels}
      />

      {rawSection}

      <DecisionMetaInfo
        aiModel={decision.ai_model}
        tokensUsed={decision.tokens_used}
        latencyMs={decision.latency_ms}
        labels={metaLabels}
        mode={metaMode}
        formatModelName={formatModelName}
      />
    </>
  );
}
