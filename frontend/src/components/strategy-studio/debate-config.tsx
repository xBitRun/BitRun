"use client";

import { useState, useCallback } from "react";
import {
  Users,
  Bot,
  AlertCircle,
  CheckCircle,
  Loader2,
  Info,
  Zap,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";
import {
  ConsensusMode,
  CONSENSUS_MODE_OPTIONS,
  DebateModelValidation,
} from "@/types";
import { useTranslations } from "next-intl";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useUserModels, getProviderDisplayName } from "@/hooks";
import type { AIModelInfoResponse } from "@/lib/api/endpoints";

/** Derive cost level from API cost per 1k tokens (avg of input/output). */
function getCostLevel(model: AIModelInfoResponse): "low" | "medium" {
  const avg = (model.cost_per_1k_input + model.cost_per_1k_output) / 2;
  return avg <= 0.15 ? "low" : "medium";
}

interface DebateConfigProps {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  modelIds: string[];
  onModelIdsChange: (modelIds: string[]) => void;
  consensusMode: ConsensusMode;
  onConsensusModeChange: (mode: ConsensusMode) => void;
  minParticipants: number;
  onMinParticipantsChange: (min: number) => void;
}

export function DebateConfig({
  enabled,
  onEnabledChange,
  modelIds,
  onModelIdsChange,
  consensusMode,
  onConsensusModeChange,
  minParticipants,
  onMinParticipantsChange,
}: DebateConfigProps) {
  const t = useTranslations("strategyStudio");
  const { models, isLoading: modelsLoading, error: modelsError, refresh: refreshModels } = useUserModels();
  const [validationResults, setValidationResults] = useState<
    DebateModelValidation[] | null
  >(null);
  const [isValidating, setIsValidating] = useState(false);

  const toggleModel = (modelId: string) => {
    if (modelIds.includes(modelId)) {
      onModelIdsChange(modelIds.filter((id) => id !== modelId));
    } else if (modelIds.length < 5) {
      onModelIdsChange([...modelIds, modelId]);
    }
    // Clear validation when models change
    setValidationResults(null);
  };

  const validateModels = useCallback(async () => {
    if (modelIds.length < 2) return;

    setIsValidating(true);
    try {
      const response = await fetch("/api/strategies/validate-debate-models", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model_ids: modelIds }),
      });

      if (response.ok) {
        const data = await response.json();
        setValidationResults(data.models);
      }
    } catch (error) {
      console.error("Failed to validate models:", error);
    } finally {
      setIsValidating(false);
    }
  }, [modelIds]);

  const getModelValidationStatus = (modelId: string) => {
    if (!validationResults) return null;
    return validationResults.find((r) => r.modelId === modelId);
  };

  const estimatedCost = modelIds.length * 0.1; // Rough estimate per call

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Users className="h-5 w-5 text-primary" />
          {t("debate.title")}
        </CardTitle>
        <p className="text-sm text-muted-foreground">{t("debate.description")}</p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Enable/Disable Toggle */}
        <div className="flex items-center justify-between p-4 rounded-lg border border-border/50 bg-background/30">
          <div className="space-y-1">
            <Label className="text-sm font-medium">{t("debate.enable")}</Label>
            <p className="text-xs text-muted-foreground">
              {t("debate.enableDescription")}
            </p>
          </div>
          <Switch checked={enabled} onCheckedChange={onEnabledChange} />
        </div>

        {enabled && (
          <>
            {/* Model Selection */}
            <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="h-4 w-4 text-blue-500" />
                  <Label className="text-sm font-medium">
                    {t("debate.selectModels")}
                  </Label>
                  <Badge variant="outline" className="text-xs">
                    {modelIds.length}/5
                  </Badge>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={validateModels}
                  disabled={modelIds.length < 2 || isValidating}
                >
                  {isValidating ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <CheckCircle className="h-4 w-4 mr-1" />
                  )}
                  {t("debate.validate")}
                </Button>
              </div>

              <p className="text-xs text-muted-foreground">
                {t("debate.selectModelsDescription")}
              </p>

              <div className="grid grid-cols-1 gap-2">
                {modelsLoading ? (
                  <>
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-14 w-full rounded-lg" />
                    ))}
                  </>
                ) : modelsError ? (
                  <Card className="bg-destructive/10 border-destructive/30">
                    <CardContent className="flex items-center gap-3 py-4">
                      <AlertCircle className="w-5 h-5 shrink-0 text-destructive" />
                      <p className="text-destructive flex-1 text-sm">
                        {t("debate.modelsLoadFailed")}
                      </p>
                      <Button variant="outline" size="sm" onClick={() => refreshModels()}>
                        {t("debate.retry")}
                      </Button>
                    </CardContent>
                  </Card>
                ) : models.length === 0 ? (
                  <div className="text-center py-4 space-y-2">
                    <p className="text-sm text-muted-foreground">
                      {t("debate.noModels")}
                    </p>
                    <p className="text-sm">
                      <Link href="/models" className="text-primary hover:underline">
                        {t("debate.addModelLink")}
                      </Link>
                    </p>
                  </div>
                ) : (
                  models.map((model) => {
                    const isSelected = modelIds.includes(model.id);
                    const validation = getModelValidationStatus(model.id);
                    const costLevel = getCostLevel(model);

                    return (
                      <div
                        key={model.id}
                        className={cn(
                          "flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-colors",
                          isSelected
                            ? "border-primary bg-primary/5"
                            : "border-border/50 hover:border-border"
                        )}
                        onClick={() => toggleModel(model.id)}
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              "w-4 h-4 rounded-full border-2 flex items-center justify-center",
                              isSelected
                                ? "border-primary bg-primary"
                                : "border-muted-foreground"
                            )}
                          >
                            {isSelected && (
                              <CheckCircle className="h-3 w-3 text-primary-foreground" />
                            )}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium">
                                {model.name}
                              </span>
                              <Badge variant="secondary" className="text-xs">
                                {getProviderDisplayName(model.provider)}
                              </Badge>
                            </div>
                            <span className="text-xs text-muted-foreground">
                              {model.id}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {validation && (
                            <>
                              {validation.valid ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <TooltipProvider>
                                  <Tooltip>
                                    <TooltipTrigger>
                                      <AlertCircle className="h-4 w-4 text-destructive" />
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p>{validation.error}</p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TooltipProvider>
                              )}
                            </>
                          )}
                          <Badge
                            variant={costLevel === "low" ? "outline" : "secondary"}
                            className="text-xs"
                          >
                            {costLevel === "low" ? "$" : "$$"}
                          </Badge>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {modelIds.length < 2 && (
                <div className="flex items-center gap-2 p-2 rounded-md bg-warning/10 text-warning text-xs">
                  <AlertCircle className="h-4 w-4" />
                  {t("debate.minModelsWarning")}
                </div>
              )}
            </div>

            {/* Consensus Mode */}
            <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-yellow-500" />
                <Label className="text-sm font-medium">
                  {t("debate.consensusMode")}
                </Label>
              </div>

              <Select
                value={consensusMode}
                onValueChange={(value) =>
                  onConsensusModeChange(value as ConsensusMode)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CONSENSUS_MODE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <div className="flex flex-col">
                        <span>{option.label}</span>
                        <span className="text-xs text-muted-foreground">
                          {option.description}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Min Participants */}
            <div className="space-y-4 p-4 rounded-lg border border-border/50 bg-background/30">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Info className="h-4 w-4 text-blue-500" />
                  <Label className="text-sm font-medium">
                    {t("debate.minParticipants")}
                  </Label>
                </div>
                <Select
                  value={minParticipants.toString()}
                  onValueChange={(value) =>
                    onMinParticipantsChange(parseInt(value))
                  }
                >
                  <SelectTrigger className="w-24">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2, 3, 4, 5]
                      .filter((n) => n <= modelIds.length || modelIds.length === 0)
                      .map((n) => (
                        <SelectItem key={n} value={n.toString()}>
                          {n} {t("debate.models")}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>
              <p className="text-xs text-muted-foreground">
                {t("debate.minParticipantsDescription")}
              </p>
            </div>

            {/* Estimated Cost */}
            <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
              <span className="text-sm text-muted-foreground">
                {t("debate.estimatedCost")}
              </span>
              <Badge variant="outline">
                ~${estimatedCost.toFixed(2)} / {t("debate.perCycle")}
              </Badge>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
