"use client";

interface DecisionMetaLabels {
  strategyType: string;
  model: string;
  tokens: string;
  latency: string;
}

interface DecisionMetaInfoProps {
  aiModel: string;
  tokensUsed: number;
  latencyMs: number;
  labels: DecisionMetaLabels;
  mode?: "ai" | "auto";
  formatModelName?: (model: string) => string;
}

export function DecisionMetaInfo({
  aiModel,
  tokensUsed,
  latencyMs,
  labels,
  mode = "auto",
  formatModelName,
}: DecisionMetaInfoProps) {
  const isQuant = aiModel?.startsWith("quant:");
  const showQuantStrategyOnly = mode === "auto" && isQuant;
  const modelText = formatModelName ? formatModelName(aiModel) : aiModel;

  if (showQuantStrategyOnly) {
    return (
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground pt-3 border-t border-border/30">
        <span>
          {labels.strategyType}: {aiModel.replace("quant:", "").toUpperCase()}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground pt-3 border-t border-border/30">
      <span>
        {labels.model}: {modelText}
      </span>
      <span>
        {labels.tokens}: {tokensUsed}
      </span>
      <span>
        {labels.latency}: {latencyMs}ms
      </span>
    </div>
  );
}
