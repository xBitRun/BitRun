"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Wallet,
  Bot,
  Cpu,
  Lightbulb,
  Check,
  ChevronDown,
  ChevronUp,
  X,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useAccounts, useModels, useStrategies } from "@/hooks";
import { useAgents } from "@/hooks/use-agents";

const STORAGE_KEY = "bitrun-setup-guide-dismissed";

interface SetupStep {
  id: string;
  titleKey: string;
  descKey: string;
  href: string;
  icon: React.ElementType;
  isComplete: boolean;
  isOptional?: boolean;
}

interface FloatingSetupGuideProps {
  className?: string;
}

export function FloatingSetupGuide({ className }: FloatingSetupGuideProps) {
  const t = useTranslations("setupGuide");
  const { accounts, isLoading: accountsLoading } = useAccounts();
  const { agents, isLoading: agentsLoading } = useAgents();
  const { models, isLoading: modelsLoading } = useModels();
  const { strategies, isLoading: strategiesLoading } = useStrategies();

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isDismissed, setIsDismissed] = useState(true); // Default to true to prevent flash

  // Check localStorage on mount (SSR-safe: must read localStorage in effect)
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    setIsDismissed(dismissed === "true");
  }, []);

  const isLoading = accountsLoading || agentsLoading || modelsLoading || strategiesLoading;

  const hasAccounts = accounts.length > 0;
  const hasAgents = agents.length > 0;
  const hasModels = models.length > 0;
  const hasStrategies = (strategies ?? []).length > 0;

  // New flow: Models -> Strategy -> Agent, Account is optional (for live trading)
  const steps: SetupStep[] = [
    {
      id: "models",
      titleKey: "steps.models.title",
      descKey: "steps.models.desc",
      href: "/models",
      icon: Cpu,
      isComplete: hasModels,
    },
    {
      id: "strategy",
      titleKey: "steps.strategy.title",
      descKey: "steps.strategy.desc",
      href: "/strategies/new",
      icon: Lightbulb,
      isComplete: hasStrategies,
    },
    {
      id: "agent",
      titleKey: "steps.agent.title",
      descKey: "steps.agent.desc",
      href: "/agents/new",
      icon: Bot,
      isComplete: hasAgents,
    },
    {
      id: "account",
      titleKey: "steps.account.title",
      descKey: "steps.account.desc",
      href: "/accounts/new",
      icon: Wallet,
      isComplete: hasAccounts,
      isOptional: true,
    },
  ];

  const completedCount = steps.filter((s) => s.isComplete).length;
  const requiredSteps = steps.filter((s) => !s.isOptional);
  const allRequiredComplete = requiredSteps.every((s) => s.isComplete);

  // Don't show if dismissed or all required steps complete
  if (isDismissed || isLoading || allRequiredComplete) {
    return null;
  }

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setIsDismissed(true);
  };

  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-50 w-80 shadow-2xl",
        className
      )}
    >
      <Card className="bg-card/95 backdrop-blur-md border-primary/20 overflow-hidden">
        {/* Header */}
        <CardHeader className="pb-2 pt-4 px-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-md bg-primary/10">
                <Sparkles className="w-4 h-4 text-primary" />
              </div>
              <CardTitle className="text-sm font-semibold">
                {t("title")}
              </CardTitle>
            </div>
            <div className="flex items-center gap-1">
              <Badge variant="outline" className="text-xs px-2 py-0.5">
                {completedCount}/{steps.length}
              </Badge>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setIsCollapsed(!isCollapsed)}
              >
                {isCollapsed ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
                onClick={handleDismiss}
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          </div>
          {!isCollapsed && (
            <p className="text-xs text-muted-foreground mt-1">
              {t("subtitle")}
            </p>
          )}
        </CardHeader>

        {/* Steps List */}
        {!isCollapsed && (
          <CardContent className="px-4 pb-4 pt-2">
            <div className="space-y-2">
              {steps.map((step, index) => {
                const Icon = step.icon;
                const isNext =
                  !step.isComplete &&
                  steps.slice(0, index).every((s) => s.isComplete || s.isOptional);

                return (
                  <div
                    key={step.id}
                    className={cn(
                      "flex items-center gap-3 p-2.5 rounded-lg transition-all",
                      step.isComplete
                        ? "bg-primary/5"
                        : isNext
                        ? "bg-muted/50 ring-1 ring-primary/30"
                        : "bg-muted/30"
                    )}
                  >
                    {/* Status Icon */}
                    <div
                      className={cn(
                        "flex items-center justify-center w-8 h-8 rounded-full shrink-0",
                        step.isComplete
                          ? "bg-primary/20 text-primary"
                          : "bg-muted text-muted-foreground"
                      )}
                    >
                      {step.isComplete ? (
                        <Check className="w-4 h-4" />
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            "text-sm font-medium",
                            step.isComplete && "text-muted-foreground line-through"
                          )}
                        >
                          {t(step.titleKey)}
                        </span>
                        {step.isOptional && (
                          <Badge variant="outline" className="text-[10px] px-1 py-0">
                            {t("optional")}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {t(step.descKey)}
                      </p>
                    </div>

                    {/* Action */}
                    {!step.isComplete && (
                      <Link href={step.href}>
                        <Button
                          size="sm"
                          variant={isNext ? "default" : "ghost"}
                          className={cn(
                            "h-7 px-2 text-xs",
                            isNext && "glow-primary"
                          )}
                        >
                          {t("go")}
                          <ArrowRight className="w-3 h-3 ml-1" />
                        </Button>
                      </Link>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Progress indicator */}
            <div className="mt-3 pt-3 border-t border-border/50">
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-500"
                    style={{ width: `${(completedCount / steps.length) * 100}%` }}
                  />
                </div>
                <span className="text-xs text-muted-foreground">
                  {Math.round((completedCount / steps.length) * 100)}%
                </span>
              </div>
            </div>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
