"use client";

import { useTranslations } from "next-intl";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  Pause,
  Square,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { AgentPerformance } from "@/lib/api/endpoints";

interface AgentPerformanceTableProps {
  agents: AgentPerformance[];
  isLoading?: boolean;
  onRowClick?: (agentId: string) => void;
  className?: string;
}

function formatCurrency(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)}`;
}

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

const statusIcons: Record<string, React.ReactNode> = {
  active: <Activity className="w-3 h-3" />,
  paused: <Pause className="w-3 h-3" />,
  stopped: <Square className="w-3 h-3" />,
  error: <AlertTriangle className="w-3 h-3" />,
  warning: <AlertTriangle className="w-3 h-3" />,
  draft: null,
};

const statusColors: Record<string, string> = {
  active: "bg-green-500/10 text-green-500 border-green-500/20",
  paused: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  stopped: "bg-gray-500/10 text-gray-500 border-gray-500/20",
  error: "bg-red-500/10 text-red-500 border-red-500/20",
  warning: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  draft: "bg-blue-500/10 text-blue-500 border-blue-500/20",
};

const strategyTypeColors: Record<string, string> = {
  ai: "bg-purple-500/10 text-purple-500",
  grid: "bg-blue-500/10 text-blue-500",
  dca: "bg-cyan-500/10 text-cyan-500",
  rsi: "bg-orange-500/10 text-orange-500",
};

export function AgentPerformanceTable({
  agents,
  isLoading,
  onRowClick,
  className,
}: AgentPerformanceTableProps) {
  const t = useTranslations("analytics");
  const tStatus = useTranslations("agents.status");

  if (isLoading) {
    return (
      <div className={cn("space-y-3", className)}>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    );
  }

  if (agents.length === 0) {
    return (
      <div className={cn("text-center py-8 text-muted-foreground", className)}>
        {t("agents.noData")}
      </div>
    );
  }

  return (
    <Table className={className}>
      <TableHeader>
        <TableRow>
          <TableHead>{t("agents.columns.name")}</TableHead>
          <TableHead>{t("agents.columns.status")}</TableHead>
          <TableHead className="text-right">{t("agents.columns.totalPnl")}</TableHead>
          <TableHead className="text-right">{t("agents.columns.dailyPnl")}</TableHead>
          <TableHead className="text-right">{t("agents.columns.winRate")}</TableHead>
          <TableHead className="text-right">{t("agents.columns.trades")}</TableHead>
          <TableHead className="text-right">{t("agents.columns.positions")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {agents.map((agent) => {
          const pnlColor =
            agent.total_pnl > 0
              ? "text-[var(--profit)]"
              : agent.total_pnl < 0
                ? "text-[var(--loss)]"
                : "text-muted-foreground";

          const TrendIcon = agent.daily_pnl > 0 ? TrendingUp : TrendingDown;

          return (
            <TableRow
              key={agent.agent_id}
              onClick={() => onRowClick?.(agent.agent_id)}
              className={cn(onRowClick && "cursor-pointer hover:bg-muted/50")}
            >
              <TableCell>
                <div className="flex flex-col gap-1">
                  <span className="font-medium">{agent.agent_name}</span>
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "text-xs px-1.5 py-0.5 rounded",
                        strategyTypeColors[agent.strategy_type] ?? "bg-muted"
                      )}
                    >
                      {agent.strategy_type.toUpperCase()}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {agent.strategy_name}
                    </span>
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge
                  variant="outline"
                  className={cn("gap-1", statusColors[agent.status] ?? "")}
                >
                  {statusIcons[agent.status]}
                  {tStatus(agent.status)}
                </Badge>
              </TableCell>
              <TableCell className="text-right font-mono font-medium">
                <span className={pnlColor}>
                  {formatCurrency(agent.total_pnl)}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono">
                <span
                  className={cn(
                    "flex items-center justify-end gap-1",
                    agent.daily_pnl > 0
                      ? "text-[var(--profit)]"
                      : agent.daily_pnl < 0
                        ? "text-[var(--loss)]"
                        : "text-muted-foreground"
                  )}
                >
                  <TrendIcon className="w-3 h-3" />
                  {formatCurrency(agent.daily_pnl)}
                </span>
              </TableCell>
              <TableCell className="text-right font-mono">
                {formatPercent(agent.win_rate)}
              </TableCell>
              <TableCell className="text-right font-mono">
                {agent.total_trades}
              </TableCell>
              <TableCell className="text-right font-mono">
                {agent.open_positions}
              </TableCell>
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
