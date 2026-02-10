"use client";

import { useState } from "react";
import { FileText, ChevronDown, ChevronUp, AlertTriangle, Code2, Layers } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { MonacoMarkdownEditor } from "@/components/ui/monaco-markdown-editor";
import { PromptSections, DEFAULT_PROMPT_SECTIONS } from "@/types";
import type { TradingMode } from "@/types";
import { useTranslations } from "next-intl";

interface PromptTemplateEditorProps {
  promptMode: "simple" | "advanced";
  onPromptModeChange: (mode: "simple" | "advanced") => void;
  value: PromptSections;
  onChange: (sections: PromptSections) => void;
  customPrompt: string;
  onCustomPromptChange: (prompt: string) => void;
  advancedPrompt: string;
  onAdvancedPromptChange: (prompt: string) => void;
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

export function PromptTemplateEditor({
  promptMode,
  onPromptModeChange,
  value,
  onChange,
  customPrompt,
  onCustomPromptChange,
  advancedPrompt,
  onAdvancedPromptChange,
  tradingMode,
}: PromptTemplateEditorProps) {
  const t = useTranslations("strategyStudio");
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set()
  );

  const handleModeChange = (checked: boolean) => {
    const newMode = checked ? "advanced" : "simple";
    onPromptModeChange(newMode);
    // When switching from advanced to simple, clear advanced prompt
    if (newMode === "simple" && advancedPrompt) {
      onAdvancedPromptChange("");
    }
  };

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

  // Check if a section has been customized (differs from default)
  const isCustomized = (key: keyof PromptSections): boolean => {
    const currentValue = value[key]?.trim() || "";
    const defaultValue = DEFAULT_PROMPT_SECTIONS[key]?.trim() || "";
    return currentValue !== defaultValue && currentValue !== "";
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FileText className="h-5 w-5 text-primary" />
              {t("promptEditor.title")}
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {t("promptEditor.description")}
            </p>
          </div>
          {/* Mode Toggle */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {t("promptEditor.modeSimple")}
              </span>
            </div>
            <Switch
              checked={promptMode === "advanced"}
              onCheckedChange={handleModeChange}
            />
            <div className="flex items-center gap-2">
              <Code2 className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {t("promptEditor.modeAdvanced")}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {promptMode === "simple" ? (
          <>
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
                      {isCustomized(config.key) && (
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
          </>
        ) : (
          <>
            {/* Advanced Mode: Markdown Editor */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">
                {t("promptEditor.advancedModeTitle")}
              </Label>
              <MonacoMarkdownEditor
                value={advancedPrompt}
                onChange={onAdvancedPromptChange}
                placeholder={t("promptEditor.advancedModePlaceholder")}
                minHeight={500}
                className="mt-2"
              />
              <p className="text-xs text-muted-foreground mt-2">
                {t("promptEditor.advancedModeHint")}
              </p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
