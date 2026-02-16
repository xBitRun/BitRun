"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import Link from "next/link";
import {
  Plus,
  Play,
  Pause,
  MoreHorizontal,
  TrendingUp,
  TrendingDown,
  Bot,
  Filter,
  Loader2,
  Square,
  Pencil,
  RotateCcw,
  Zap,
  Eye,
} from "lucide-react";
import {
  ListPageSkeleton,
  ListPageError,
  ListPageEmpty,
  ListPageFilterEmpty,
} from "@/components/list-page";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { useAgents } from "@/hooks/use-agents";
import { useToast } from "@/components/ui/toast";
import type { AgentResponse } from "@/lib/api";
import type { AgentStatus } from "@/types";

function getStatusColor(status: AgentStatus) {
  switch (status) {
    case "active":
      return "bg-[var(--profit)]/20 text-[var(--profit)]";
    case "paused":
      return "bg-[var(--warning)]/20 text-[var(--warning)]";
    case "stopped":
      return "bg-muted text-muted-foreground";
    case "error":
      return "bg-[var(--loss)]/20 text-[var(--loss)]";
    case "warning":
      return "bg-[var(--warning)]/20 text-[var(--warning)]";
    default:
      return "bg-muted text-muted-foreground";
  }
}

function getExecutionModeColor(mode: string) {
  return mode === "live"
    ? "border-emerald-500/30 text-emerald-500"
    : "border-amber-500/30 text-amber-500";
}

function getStrategyTypeColor(type: string | null | undefined) {
  switch (type) {
    case "ai":
      return "border-violet-500/30 text-violet-500";
    case "grid":
      return "border-blue-500/30 text-blue-500";
    case "dca":
      return "border-emerald-500/30 text-emerald-500";
    case "rsi":
      return "border-amber-500/30 text-amber-500";
    default:
      return "border-muted-foreground/30 text-muted-foreground";
  }
}

interface AgentCardProps {
  agent: AgentResponse;
  onStatusChange: (id: string, status: AgentStatus) => void;
  onDelete: (id: string) => void;
  t: ReturnType<typeof useTranslations>;
}

function AgentCard({ agent, onStatusChange, onDelete, t }: AgentCardProps) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  const handleStatusChange = async (newStatus: AgentStatus) => {
    setIsUpdating(true);
    try {
      await onStatusChange(agent.id, newStatus);
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur-sm border-border/50 hover:border-primary/30 transition-colors gap-3">
      <CardHeader className="pb-0">
        <div className="flex items-start justify-between overflow-hidden">
          <div className="flex items-center gap-3 min-w-0">
            <div className="p-2 rounded-lg bg-primary/10 shrink-0">
              <Bot className="w-5 h-5 text-primary" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-lg">{agent.name}</CardTitle>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <Badge
                  variant="outline"
                  className={cn("text-xs", getStatusColor(agent.status))}
                >
                  {t(`status.${agent.status}`)}
                </Badge>
                {agent.strategy_type && (
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      getStrategyTypeColor(agent.strategy_type),
                    )}
                  >
                    {agent.strategy_type.toUpperCase()}
                  </Badge>
                )}
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    getExecutionModeColor(agent.execution_mode),
                  )}
                >
                  {t(`executionMode.${agent.execution_mode}`)}
                </Badge>
              </div>
              {agent.strategy_name && (
                <p className="text-xs text-muted-foreground mt-1">
                  {agent.strategy_name}
                </p>
              )}
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem asChild>
                <Link
                  href={`/agents/${agent.id}`}
                  className="flex items-center"
                >
                  <Eye className="w-4 h-4 mr-2" />
                  {t("actions.viewDetails")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link
                  href={`/agents/${agent.id}/edit`}
                  className="flex items-center"
                >
                  <Pencil className="w-4 h-4 mr-2" />
                  {t("actions.edit")}
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem
                className={
                  ["stopped", "draft"].includes(agent.status)
                    ? "text-destructive"
                    : "text-muted-foreground"
                }
                disabled={!["stopped", "draft"].includes(agent.status)}
                onClick={() =>
                  ["stopped", "draft"].includes(agent.status) &&
                  onDelete(agent.id)
                }
              >
                {t("actions.delete")}
                {!["stopped", "draft"].includes(agent.status) && (
                  <span className="ml-1 text-xs">
                    ({t("actions.deleteRequireStopped")})
                  </span>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 pt-2 border-t border-border/30">
          <div>
            <p className="text-xs text-muted-foreground">
              {t("stats.totalPL")}
            </p>
            <p
              className={cn(
                "font-mono font-semibold flex items-center gap-1",
                agent.total_pnl >= 0
                  ? "text-[var(--profit)]"
                  : "text-[var(--loss)]",
              )}
            >
              {agent.total_pnl >= 0 ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              ${Math.abs(agent.total_pnl).toLocaleString()}
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">
              {t("stats.winRate")}
            </p>
            <p className="font-mono font-semibold">
              {agent.win_rate.toFixed(1)}%
            </p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">
              {t("stats.totalTrades")}
            </p>
            <p className="font-mono font-semibold">{agent.total_trades}</p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 pt-2">
          {agent.status === "active" ? (
            <Button
              variant="default"
              size="sm"
              className="flex-1 bg-primary/20 text-primary hover:bg-primary/30"
              onClick={() => handleStatusChange("paused")}
              disabled={isUpdating}
            >
              {isUpdating ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Pause className="w-4 h-4 mr-2" />
              )}
              {t("actions.pause")}
            </Button>
          ) : agent.status === "paused" || agent.status === "draft" ? (
            <>
              <Button
                variant="default"
                size="sm"
                className="flex-1"
                onClick={() => handleStatusChange("active")}
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                {agent.status === "draft"
                  ? t("actions.start")
                  : t("actions.resume")}
              </Button>
              {agent.status === "paused" && (
                <Button
                  variant="outline"
                  size="sm"
                  className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                  onClick={() => setShowStopConfirm(true)}
                  disabled={isUpdating}
                >
                  <Square className="w-4 h-4 mr-2" />
                  {t("actions.stop")}
                </Button>
              )}
            </>
          ) : agent.status === "error" || agent.status === "warning" ? (
            <>
              <Button
                variant="default"
                size="sm"
                className="flex-1"
                onClick={() => handleStatusChange("active")}
                disabled={isUpdating}
              >
                {isUpdating ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4 mr-2" />
                )}
                {t("actions.restart")}
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="border-[var(--loss)]/50 text-[var(--loss)] hover:bg-[var(--loss)]/10"
                onClick={() => setShowStopConfirm(true)}
                disabled={isUpdating}
              >
                <Square className="w-4 h-4 mr-2" />
                {t("actions.stop")}
              </Button>
            </>
          ) : null}
          <Link href={`/agents/${agent.id}`}>
            <Button variant="ghost" size="sm">
              {t("actions.viewDetails")}
            </Button>
          </Link>

          {/* Stop Confirm Dialog */}
          <Dialog open={showStopConfirm} onOpenChange={setShowStopConfirm}>
            <DialogContent showCloseButton={false}>
              <DialogHeader>
                <DialogTitle>{t("actions.stopConfirmTitle")}</DialogTitle>
                <DialogDescription>
                  {t("actions.stopConfirmDesc")}
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowStopConfirm(false)}
                >
                  {t("actions.cancel")}
                </Button>
                <Button
                  variant="destructive"
                  onClick={async () => {
                    setShowStopConfirm(false);
                    await handleStatusChange("stopped");
                  }}
                  disabled={isUpdating}
                >
                  {isUpdating ? (
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="w-4 h-4 mr-2" />
                  )}
                  {t("actions.confirmStop")}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
}

export default function AgentsPage() {
  const t = useTranslations("agents");
  const [filter, setFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");

  const { agents, error, isLoading, refresh } = useAgents();
  const toast = useToast();

  // Status update handler
  const handleStatusChange = async (id: string, status: AgentStatus) => {
    try {
      const { agentsApi } = await import("@/lib/api");
      await agentsApi.updateStatus(id, status);
      refresh();
      const statusKey = status === "active" ? "started" : status;
      toast.success(t(`toast.${statusKey}`));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.updateFailed");
      toast.error(t("toast.updateFailed"), message);
    }
  };

  // Delete handler
  const handleDelete = async (id: string) => {
    try {
      const { agentsApi } = await import("@/lib/api");
      await agentsApi.delete(id);
      refresh();
      toast.success(t("toast.deleteSuccess"));
    } catch (err) {
      const message =
        err instanceof Error ? err.message : t("toast.deleteFailed");
      toast.error(t("toast.deleteFailed"), message);
    }
  };

  const filteredAgents = agents.filter((a) => {
    const matchesFilter = filter === "all" || a.status === filter;
    const matchesSearch = a.name
      .toLowerCase()
      .includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const hasNoAgents = !isLoading && !error && agents.length === 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gradient">{t("title")}</h1>
          <p className="text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Link href="/agents/new">
          <Button className="glow-primary">
            <Plus className="w-4 h-4 mr-2" />
            {t("createAgent")}
          </Button>
        </Link>
      </div>

      {/* Filters */}
      {!hasNoAgents && (
        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Input
              placeholder={t("searchPlaceholder")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-muted/50"
            />
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-40 bg-muted/50">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("filter.allStatus")}</SelectItem>
              <SelectItem value="active">{t("filter.active")}</SelectItem>
              <SelectItem value="paused">{t("filter.paused")}</SelectItem>
              <SelectItem value="draft">{t("filter.draft")}</SelectItem>
              <SelectItem value="stopped">{t("filter.stopped")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      )}

      {/* Loading */}
      {isLoading && <ListPageSkeleton />}

      {/* Error */}
      {error && (
        <ListPageError
          message={error.message || t("error.loadFailed")}
          onRetry={() => refresh()}
          retryLabel={t("retry")}
        />
      )}

      {/* Empty */}
      {hasNoAgents && (
        <ListPageEmpty
          icon={Bot}
          title={t("empty.title")}
          description={t("empty.description")}
          actionLabel={t("empty.createFirst")}
          actionHref="/agents/new"
          actionIcon={Plus}
        />
      )}

      {/* Agent Cards */}
      {!isLoading && !error && agents.length > 0 && (
        <>
          {filteredAgents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  onStatusChange={handleStatusChange}
                  onDelete={handleDelete}
                  t={t}
                />
              ))}
              <Link href="/agents/new" className="block h-full">
                <Card className="bg-card/30 backdrop-blur-sm border-dashed border-2 border-border/50 hover:border-primary/50 transition-colors cursor-pointer h-full">
                  <CardContent className="flex flex-col items-center justify-center h-full min-h-0 py-8 text-muted-foreground hover:text-foreground transition-colors">
                    <div className="p-3 rounded-full bg-muted/30 mb-3">
                      <Plus className="w-6 h-6" />
                    </div>
                    <p className="font-medium">{t("createAgent")}</p>
                    <p className="text-sm text-center mt-1 text-muted-foreground">
                      {t("empty.description")}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            </div>
          ) : (
            <ListPageFilterEmpty
              icon={Bot}
              title={t("empty.title")}
              description={t("empty.searchHint")}
            />
          )}
        </>
      )}
    </div>
  );
}
