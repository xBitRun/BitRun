"use client";

import { useState } from "react";
import { FileText, ChevronDown, ChevronUp, Sparkles, AlertTriangle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { PromptSections } from "@/types";
import type { TradingMode } from "@/types";
import { useTranslations } from "next-intl";
import { useToast } from "@/components/ui/toast";

// Keywords that may conflict with the selected trading mode (custom prompt vs mode)
const CONFLICT_KEYWORDS: Record<
  TradingMode,
  { pattern: RegExp; labelKey: string }[]
> = {
  conservative: [
    { pattern: /aggressive|high\s*leverage|大胆|激进|高杠杆|频繁交易|重仓|满仓/i, labelKey: "promptEditor.conflictWithConservative" },
  ],
  aggressive: [
    { pattern: /conservative|low\s*risk|保守|谨慎|少交易|轻仓|小仓位/i, labelKey: "promptEditor.conflictWithAggressive" },
  ],
  balanced: [
    { pattern: /all[- ]?in|满仓|梭哈|max\s*leverage/i, labelKey: "promptEditor.conflictWithBalanced" },
  ],
};

function detectPromptModeConflict(
  customPrompt: string,
  tradingMode: TradingMode
): string | null {
  if (!customPrompt.trim()) return null;
  const keywords = CONFLICT_KEYWORDS[tradingMode];
  if (!keywords) return null;
  for (const { pattern, labelKey } of keywords) {
    if (pattern.test(customPrompt)) return labelKey;
  }
  return null;
}

interface PromptTemplateEditorProps {
  value: PromptSections;
  onChange: (sections: PromptSections) => void;
  customPrompt: string;
  onCustomPromptChange: (prompt: string) => void;
  tradingMode: TradingMode;
}

interface PromptSectionConfig {
  key: keyof PromptSections;
  icon: string;
  rows: number;
}

const SECTION_CONFIGS: PromptSectionConfig[] = [
  { key: "roleDefinition", icon: "👤", rows: 4 },
  { key: "tradingFrequency", icon: "⏰", rows: 3 },
  { key: "entryStandards", icon: "🎯", rows: 4 },
  { key: "decisionProcess", icon: "🧠", rows: 5 },
];

// Preset templates
const PROMPT_TEMPLATES = {
  momentum: {
    roleDefinition:
      "You are a momentum trader who specializes in identifying and riding strong price trends. You focus on breakouts, volume surges, and momentum indicators.",
    tradingFrequency:
      "Trade when clear momentum signals appear. Avoid choppy, ranging markets. Quality setups over quantity.",
    entryStandards:
      "Enter when:\n- Price breaks key resistance/support with volume\n- RSI shows momentum (above 50 for longs, below 50 for shorts)\n- Multiple timeframes align",
    decisionProcess:
      "1. Identify trend direction on higher timeframes\n2. Wait for pullback to key levels\n3. Confirm with volume and momentum\n4. Set tight stop loss below/above recent swing\n5. Target 2-3x risk for reward",
  },
  meanReversion: {
    roleDefinition:
      "You are a mean reversion trader who profits from price returning to average levels. You specialize in identifying overextended moves and fading extremes.",
    tradingFrequency:
      "Trade only when price deviates significantly from moving averages. Patient approach, waiting for extreme readings.",
    entryStandards:
      "Enter when:\n- Price deviates >2-3% from 20 EMA\n- RSI at extreme levels (>70 or <30)\n- Volume shows exhaustion\n- Support/resistance nearby",
    decisionProcess:
      "1. Calculate distance from moving average\n2. Check RSI for overbought/oversold\n3. Identify nearest support/resistance\n4. Enter with stop beyond recent extreme\n5. Target return to mean",
  },
  conservative: {
    roleDefinition:
      "You are a conservative trader focused on capital preservation. You only take the highest probability setups with excellent risk/reward.",
    tradingFrequency:
      "Trade sparingly - only when all conditions align perfectly. Missing a trade is better than taking a bad one.",
    entryStandards:
      "Enter only when:\n- Minimum 3:1 risk/reward ratio\n- Multiple indicator confirmation\n- Clear invalidation level\n- Reasonable position size within limits",
    decisionProcess:
      "1. Assess overall market risk\n2. Identify highest probability setups only\n3. Calculate exact risk before entry\n4. Use conservative position sizing\n5. Set hard stop loss, no exceptions",
  },
};

export function PromptTemplateEditor({
  value,
  onChange,
  customPrompt,
  onCustomPromptChange,
  tradingMode,
}: PromptTemplateEditorProps) {
  const t = useTranslations("strategyStudio");
  const toast = useToast();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["customPrompt"])
  );
  const conflictKey = detectPromptModeConflict(customPrompt, tradingMode);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const updateSection = (key: keyof PromptSections, newValue: string) => {
    onChange({ ...value, [key]: newValue });
  };

  const applyTemplate = (templateKey: keyof typeof PROMPT_TEMPLATES) => {
    const template = PROMPT_TEMPLATES[templateKey];
    onChange(template);
    // Suggest syncing trading mode when applying a style-specific template
    if (templateKey === "conservative" && tradingMode !== "conservative") {
      toast.info(
        t("promptEditor.suggestTradingModeConservativeTitle"),
        t("promptEditor.suggestTradingModeConservative")
      );
    }
    if (templateKey === "momentum" && tradingMode === "conservative") {
      toast.info(
        t("promptEditor.suggestTradingModeMomentumTitle"),
        t("promptEditor.suggestTradingModeMomentum")
      );
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <FileText className="h-5 w-5 text-primary" />
          {t("promptEditor.title")}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          {t("promptEditor.description")}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Template Presets */}
        <div className="space-y-2">
          <Label className="text-sm font-medium">
            {t("promptEditor.templates")}
          </Label>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyTemplate("momentum")}
              className="text-xs"
            >
              <Sparkles className="h-3 w-3 mr-1" />
              {t("promptEditor.templateMomentum")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyTemplate("meanReversion")}
              className="text-xs"
            >
              <Sparkles className="h-3 w-3 mr-1" />
              {t("promptEditor.templateMeanReversion")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => applyTemplate("conservative")}
              className="text-xs"
            >
              <Sparkles className="h-3 w-3 mr-1" />
              {t("promptEditor.templateConservative")}
            </Button>
          </div>
        </div>

        {/* Custom Prompt (Main) */}
        <Collapsible
          open={expandedSections.has("customPrompt")}
          onOpenChange={() => toggleSection("customPrompt")}
        >
          <CollapsibleTrigger className="flex items-center justify-between w-full p-3 rounded-lg border border-border/50 bg-primary/5 hover:bg-primary/10 transition-colors">
            <div className="flex items-center gap-2">
              <span>✨</span>
              <span className="font-medium">
                {t("promptEditor.customPrompt")}
              </span>
              {customPrompt && (
                <span className="text-xs text-muted-foreground">
                  ({customPrompt.length} chars)
                </span>
              )}
            </div>
            {expandedSections.has("customPrompt") ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </CollapsibleTrigger>
          <CollapsibleContent className="pt-2">
            <Textarea
              value={customPrompt}
              onChange={(e) => onCustomPromptChange(e.target.value)}
              placeholder={t("promptEditor.customPromptPlaceholder")}
              rows={6}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t("promptEditor.customPromptHint")}
            </p>
            {conflictKey && (
              <div className="flex items-start gap-2 p-3 mt-2 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-500 mt-0.5 shrink-0" />
                <p className="text-xs text-yellow-700 dark:text-yellow-400">
                  {t(conflictKey)}
                </p>
              </div>
            )}
          </CollapsibleContent>
        </Collapsible>

        {/* Section Editors */}
        <div className="space-y-2">
          <Label className="text-sm font-medium text-muted-foreground">
            {t("promptEditor.advancedSections")}
          </Label>

          {SECTION_CONFIGS.map((config) => (
            <Collapsible
              key={config.key}
              open={expandedSections.has(config.key)}
              onOpenChange={() => toggleSection(config.key)}
            >
              <CollapsibleTrigger className="flex items-center justify-between w-full p-3 rounded-lg border border-border/50 bg-background/50 hover:bg-background/80 transition-colors">
                <div className="flex items-center gap-2">
                  <span>{config.icon}</span>
                  <span className="text-sm">
                    {t(`promptEditor.sections.${config.key}`)}
                  </span>
                  {value[config.key] && (
                    <span className="text-xs text-primary">
                      ({t("promptEditor.customized")})
                    </span>
                  )}
                </div>
                {expandedSections.has(config.key) ? (
                  <ChevronUp className="h-4 w-4" />
                ) : (
                  <ChevronDown className="h-4 w-4" />
                )}
              </CollapsibleTrigger>
              <CollapsibleContent className="pt-2">
                <Textarea
                  value={value[config.key]}
                  onChange={(e) => updateSection(config.key, e.target.value)}
                  placeholder={t(
                    `promptEditor.placeholders.${config.key}`
                  )}
                  rows={config.rows}
                  className="resize-none text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  {t(`promptEditor.hints.${config.key}`)}
                </p>
              </CollapsibleContent>
            </Collapsible>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
