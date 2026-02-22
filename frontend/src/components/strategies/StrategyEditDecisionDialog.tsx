"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "@/i18n/navigation";
import {
  Pause,
  Copy,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useDuplicateStrategy } from "@/hooks";
import { useToast } from "@/components/ui/toast";
import type { AgentResponse } from "@/lib/api";

interface StrategyEditDecisionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  strategyId: string;
  strategyName: string;
  activeAgents: AgentResponse[];
  onPauseAndEdit: () => void;
}

export function StrategyEditDecisionDialog({
  open,
  onOpenChange,
  strategyId,
  strategyName,
  activeAgents,
  onPauseAndEdit,
}: StrategyEditDecisionDialogProps) {
  const t = useTranslations("strategies.editDecision");
  const router = useRouter();
  const toast = useToast();

  const { trigger: duplicateStrategy, isMutating: isDuplicating } =
    useDuplicateStrategy();

  const handlePauseAndEdit = () => {
    onOpenChange(false);
    onPauseAndEdit();
  };

  const handleDuplicateAndEdit = async () => {
    try {
      const newStrategy = await duplicateStrategy({
        strategyId,
      });
      toast.success(t("duplicateSuccess"));
      onOpenChange(false);
      // Navigate to the new strategy's edit page
      router.push(`/strategies/${newStrategy.id}/edit`);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("duplicateError");
      toast.error(t("duplicateError"), message);
    }
  };

  const agentCount = activeAgents.length;
  const agentNames = activeAgents.slice(0, 3).map((a) => a.name);
  const agentNamesText =
    agentCount === 1
      ? agentNames[0]
      : agentCount <= 3
        ? agentNames.join(", ")
        : `${agentNames.slice(0, 2).join(", ")}...`;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-xl">
            <AlertTriangle className="w-5 h-5 text-orange-500" />
            {t("title")}
          </DialogTitle>
          <DialogDescription className="text-base pt-2">
            {t("description", {
              strategy: strategyName,
              count: agentCount,
              agents: agentNamesText,
            })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-4">
          {/* Option 1: Pause and Edit */}
          <button
            onClick={handlePauseAndEdit}
            className={cn(
              "w-full p-4 rounded-lg border-2 transition-all text-left",
              "border-border hover:border-primary/50 hover:bg-muted/30",
              "focus:outline-none focus:ring-2 focus:ring-primary/30"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-orange-500/10 shrink-0">
                <Pause className="w-5 h-5 text-orange-500" />
              </div>
              <div className="space-y-1">
                <p className="font-medium">{t("pauseOption.title")}</p>
                <p className="text-sm text-muted-foreground">
                  {t("pauseOption.description")}
                </p>
              </div>
            </div>
          </button>

          {/* Option 2: Duplicate and Edit (Recommended) */}
          <button
            onClick={handleDuplicateAndEdit}
            disabled={isDuplicating}
            className={cn(
              "w-full p-4 rounded-lg border-2 transition-all text-left",
              "border-primary/50 bg-primary/5",
              "hover:border-primary hover:bg-primary/10",
              "focus:outline-none focus:ring-2 focus:ring-primary/30",
              isDuplicating && "opacity-50 cursor-not-allowed"
            )}
          >
            <div className="flex items-start gap-3">
              <div className="p-2 rounded-lg bg-primary/10 shrink-0">
                {isDuplicating ? (
                  <Loader2 className="w-5 h-5 text-primary animate-spin" />
                ) : (
                  <Copy className="w-5 h-5 text-primary" />
                )}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{t("duplicateOption.title")}</p>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-primary/20 text-primary font-medium">
                    {t("recommended")}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  {t("duplicateOption.description")}
                </p>
              </div>
            </div>
          </button>
        </div>

        <div className="flex justify-end pt-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            {t("cancel")}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
