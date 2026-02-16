"use client";

import { useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Brain,
  ArrowRight,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { MarkdownToggle } from "@/components/ui/markdown-toggle";
import { Button } from "@/components/ui/button";

interface ChainOfThoughtProps {
  content: string;
  className?: string;
  /** Number of steps to show before collapsing (default: 3) */
  initialVisibleSteps?: number;
  /** Custom title translation key (default: 'chainOfThought') */
  titleKey?: string;
}

interface ThoughtStep {
  text: string;
  type: "bullish" | "bearish" | "neutral" | "warning" | "conclusion";
}

// Heuristic patterns to classify thought steps
const BULLISH_PATTERNS = [
  /\bbullish\b/i,
  /\buptrend\b/i,
  /\bbreakout\b/i,
  /\bstrong\s+support\b/i,
  /\babove\b.*\bma\b/i,
  /\bopen\s*long\b/i,
  /\bbuy\b/i,
  /看多|做多|突破|上涨|支撑强|多头/,
];

const BEARISH_PATTERNS = [
  /\bbearish\b/i,
  /\bdowntrend\b/i,
  /\bbreakdown\b/i,
  /\bstrong\s+resistance\b/i,
  /\bbelow\b.*\bma\b/i,
  /\bopen\s*short\b/i,
  /\bsell\b/i,
  /看空|做空|跌破|下跌|阻力强|空头/,
];

const WARNING_PATTERNS = [
  /\brisk\b/i,
  /\bcaution\b/i,
  /\bwarning\b/i,
  /\bvolatil/i,
  /\bdrawdown\b/i,
  /风险|注意|警告|波动|回撤/,
];

const CONCLUSION_PATTERNS = [
  /\bconclusion\b/i,
  /\bdecision\b/i,
  /\brecommend\b/i,
  /\bfinal\b/i,
  /\btherefore\b/i,
  /\boverall\b/i,
  /结论|决策|建议|总结|综上|因此/,
];

export function classifyStep(text: string): ThoughtStep["type"] {
  if (CONCLUSION_PATTERNS.some((p) => p.test(text))) return "conclusion";
  if (WARNING_PATTERNS.some((p) => p.test(text))) return "warning";
  if (BULLISH_PATTERNS.some((p) => p.test(text))) return "bullish";
  if (BEARISH_PATTERNS.some((p) => p.test(text))) return "bearish";
  return "neutral";
}

export function parseSteps(content: string): ThoughtStep[] {
  if (!content) return [];

  // Split by numbered steps, markdown headers, or double newlines
  const lines = content
    .split(new RegExp("(?:\\n\\s*\\n|\\n(?=\\d+[.)]\\s)|(?=^#{1,3}\\s))", "m"))
    .map((s) => s.trim())
    .filter((s) => s.length > 0);

  return lines.map((text) => ({
    text,
    type: classifyStep(text),
  }));
}

const stepConfig = {
  bullish: {
    icon: TrendingUp,
    color: "text-[var(--profit)]",
    bg: "bg-[var(--profit)]/10",
    border: "border-[var(--profit)]/30",
    dot: "bg-[var(--profit)]",
  },
  bearish: {
    icon: TrendingDown,
    color: "text-[var(--loss)]",
    bg: "bg-[var(--loss)]/10",
    border: "border-[var(--loss)]/30",
    dot: "bg-[var(--loss)]",
  },
  warning: {
    icon: AlertTriangle,
    color: "text-amber-500",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    dot: "bg-amber-500",
  },
  conclusion: {
    icon: CheckCircle2,
    color: "text-primary",
    bg: "bg-primary/10",
    border: "border-primary/30",
    dot: "bg-primary",
  },
  neutral: {
    icon: Activity,
    color: "text-muted-foreground",
    bg: "bg-muted/30",
    border: "border-border/50",
    dot: "bg-muted-foreground",
  },
};

// Highlight key signals in text
export function highlightSignals(text: string): string {
  // Highlight signal keywords
  let highlighted = text;
  const signalPatterns: Array<[RegExp, string]> = [
    [/\b(RSI|MACD|EMA|ATR|SMA|BB)\b/gi, "**$1**"],
    [/\b(\d+\.?\d*%)/g, "`$1`"],
    [/\$([\d,]+\.?\d*)/g, "`$$$1`"],
  ];

  for (const [pattern, replacement] of signalPatterns) {
    highlighted = highlighted.replace(pattern, replacement);
  }
  return highlighted;
}

export function ChainOfThought({
  content,
  className,
  initialVisibleSteps = 3,
  titleKey = "chainOfThought",
}: ChainOfThoughtProps) {
  const t = useTranslations("decisions.details");
  const [isExpanded, setIsExpanded] = useState(false);
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const steps = useMemo(() => parseSteps(content), [content]);

  const toggleStep = (index: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  // If content is too short or doesn't split well, fallback to markdown view
  if (steps.length <= 1) {
    return (
      <div className={className}>
        <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          {t(titleKey)}
        </h4>
        <div className="p-4 rounded-lg bg-muted/20 border border-border/30">
          <MarkdownToggle content={content} />
        </div>
      </div>
    );
  }

  const needsCollapse = steps.length > initialVisibleSteps;
  const visibleSteps = isExpanded ? steps : steps.slice(0, initialVisibleSteps);
  const hiddenCount = steps.length - initialVisibleSteps;

  return (
    <div className={className}>
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold flex items-center gap-2">
          <Brain className="w-4 h-4 text-primary" />
          {t(titleKey)}
          <span className="text-xs font-normal text-muted-foreground">
            ({steps.length} {t("steps")})
          </span>
        </h4>
        {needsCollapse && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs text-muted-foreground"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5 mr-1" />
                {t("collapseAll")}
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5 mr-1" />
                {t("expandAll", { count: hiddenCount })}
              </>
            )}
          </Button>
        )}
      </div>

      {/* Timeline view */}
      <div className="relative pl-6">
        {/* Timeline line */}
        <div className="absolute left-[9px] top-2 bottom-2 w-px bg-border/50" />

        <div className="space-y-3">
          {visibleSteps.map((step, index) => {
            const config = stepConfig[step.type];
            const Icon = config.icon;
            const isLast = index === steps.length - 1;
            const isConclusion = step.type === "conclusion";
            const isStepExpanded = expandedSteps.has(index);

            // For long steps, truncate unless expanded
            const isLongStep = step.text.length > 200;
            const shouldTruncate = isLongStep && !isStepExpanded;

            return (
              <div key={index} className="relative flex gap-3">
                {/* Timeline dot */}
                <div
                  className={cn(
                    "absolute -left-6 top-1.5 w-[18px] h-[18px] rounded-full flex items-center justify-center border-2 border-background z-10",
                    config.dot,
                  )}
                >
                  {isLast ? (
                    <ArrowRight className="w-2.5 h-2.5 text-background" />
                  ) : (
                    <div className="w-1.5 h-1.5 rounded-full bg-background" />
                  )}
                </div>

                {/* Content */}
                <div
                  className={cn(
                    "flex-1 p-3 rounded-lg border text-sm transition-all",
                    config.bg,
                    config.border,
                    isConclusion && "ring-1 ring-primary/20 border-primary/40",
                    isLast && !isConclusion && "ring-1 ring-primary/10",
                    isLongStep &&
                      "cursor-pointer hover:ring-1 hover:ring-primary/20",
                  )}
                  onClick={isLongStep ? () => toggleStep(index) : undefined}
                >
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <Icon className={cn("w-3.5 h-3.5", config.color)} />
                    <span
                      className={cn(
                        "text-xs font-semibold uppercase",
                        config.color,
                      )}
                    >
                      {step.type}
                    </span>
                    {isLongStep && (
                      <span className="ml-auto">
                        {isStepExpanded ? (
                          <ChevronUp className="w-3 h-3 text-muted-foreground" />
                        ) : (
                          <ChevronDown className="w-3 h-3 text-muted-foreground" />
                        )}
                      </span>
                    )}
                  </div>
                  <div
                    className={cn(
                      "text-foreground/80 whitespace-pre-wrap text-xs leading-relaxed",
                      shouldTruncate &&
                        "max-h-[4.5rem] overflow-hidden relative",
                    )}
                  >
                    <MarkdownToggle content={highlightSignals(step.text)} />
                    {shouldTruncate && (
                      <div className="absolute bottom-0 left-0 right-0 h-6 bg-gradient-to-t from-background/80 to-transparent pointer-events-none" />
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Collapsed indicator */}
        {needsCollapse && !isExpanded && (
          <button
            onClick={() => setIsExpanded(true)}
            className="relative flex items-center gap-2 mt-3 ml-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            <div className="w-3 h-3 rounded-full border-2 border-muted-foreground/30 flex items-center justify-center">
              <ChevronDown className="w-2 h-2" />
            </div>
            {t("expandAll", { count: hiddenCount })}
          </button>
        )}
      </div>
    </div>
  );
}
