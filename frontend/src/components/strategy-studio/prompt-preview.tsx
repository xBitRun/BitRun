"use client";

import { useState } from "react";
import { Eye, Copy, Check, RefreshCw, Zap, FileCode } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { PromptPreviewResponse } from "@/types";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";

interface PromptPreviewProps {
  preview: PromptPreviewResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
  onTest?: () => void;
  isTestLoading?: boolean;
}

export function PromptPreview({
  preview,
  isLoading,
  onRefresh,
  onTest,
  isTestLoading,
}: PromptPreviewProps) {
  const t = useTranslations("strategyStudio");
  const [copied, setCopied] = useState(false);
  const [activeSection, setActiveSection] = useState<string>("full");

  const handleCopy = async () => {
    if (preview?.systemPrompt) {
      await navigator.clipboard.writeText(preview.systemPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const sections = [
    { key: "full", label: t("preview.fullPrompt"), icon: FileCode },
    { key: "roleDefinition", label: t("preview.role"), icon: null },
    { key: "tradingMode", label: t("preview.mode"), icon: null },
    { key: "tradingFrequency", label: t("preview.frequency"), icon: null },
    { key: "entryStandards", label: t("preview.entry"), icon: null },
    { key: "decisionProcess", label: t("preview.process"), icon: null },
    { key: "customPrompt", label: t("preview.custom"), icon: null },
  ];

  const getSectionContent = (key: string): string => {
    if (!preview) return "";
    if (key === "full") return preview.systemPrompt;
    return preview.sections[key as keyof typeof preview.sections] || "";
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Eye className="h-5 w-5 text-primary" />
            {t("preview.title")}
          </CardTitle>
          <div className="flex items-center gap-2">
            {preview && (
              <Badge variant="outline" className="text-xs">
                ~{preview.estimatedTokens.toLocaleString()} tokens
              </Badge>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              className="h-8"
            >
              <RefreshCw
                className={cn("h-4 w-4", isLoading && "animate-spin")}
              />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleCopy}
              disabled={!preview}
              className="h-8"
            >
              {copied ? (
                <Check className="h-4 w-4 text-green-500" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          {t("preview.description")}
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Section Tabs */}
        <Tabs value={activeSection} onValueChange={setActiveSection}>
          <TabsList className="w-full flex-wrap h-auto gap-1 bg-transparent p-0">
            {sections.map((section) => (
              <TabsTrigger
                key={section.key}
                value={section.key}
                className="text-xs data-[state=active]:bg-primary/20"
              >
                {section.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {sections.map((section) => (
            <TabsContent key={section.key} value={section.key} className="mt-4">
              <ScrollArea className="h-[400px] rounded-lg border border-border/50 bg-background/50">
                {isLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                  </div>
                ) : preview ? (
                  <pre className="p-4 text-sm whitespace-pre-wrap font-mono text-muted-foreground">
                    {getSectionContent(section.key) || (
                      <span className="italic text-muted-foreground/50">
                        {t("preview.usingDefault")}
                      </span>
                    )}
                  </pre>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                    <FileCode className="h-8 w-8 mb-2 opacity-50" />
                    <p className="text-sm">{t("preview.noPreview")}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onRefresh}
                      className="mt-2"
                    >
                      {t("preview.generate")}
                    </Button>
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          ))}
        </Tabs>

        {/* Test AI Button */}
        {onTest && (
          <div className="pt-4 border-t border-border/50">
            <Button
              onClick={onTest}
              disabled={!preview || isTestLoading}
              className="w-full"
            >
              {isTestLoading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  {t("preview.testing")}
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4 mr-2" />
                  {t("preview.testAI")}
                </>
              )}
            </Button>
            <p className="text-xs text-muted-foreground text-center mt-2">
              {t("preview.testHint")}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
