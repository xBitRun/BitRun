/**
 * Dashboard Hooks
 *
 * Aggregates data from multiple sources for the dashboard.
 *
 * `useDashboardStats` fetches everything once from the backend
 * `/dashboard/stats` endpoint and returns both stats and positions
 * in a single SWR request, eliminating race conditions between hooks.
 */

import useSWR from "swr";
import { accountsApi, agentsApi, dashboardApi } from "@/lib/api";
import type {
  AccountResponse,
  AccountBalanceResponse,
  DashboardStatsResponse,
  ActivityFeedResponse,
} from "@/lib/api";

// ==================== Types ====================

export interface DashboardStats {
  // Equity & PnL
  totalEquity: number;
  availableBalance: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  dailyPnl: number;
  dailyPnlPercent: number;

  // Strategies
  activeStrategies: number;
  totalStrategies: number;

  // Positions
  openPositions: number;
  profitablePositions: number;

  // Accounts
  connectedAccounts: number;
  totalAccounts: number;
}

export interface Position {
  accountId: string;
  accountName: string;
  exchange: string;
  symbol: string;
  side: "long" | "short";
  size: number;
  sizeUsd: number;
  entryPrice: number;
  markPrice: number;
  leverage: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  liquidationPrice?: number;
}

// ==================== Internal Types ====================

/** Combined SWR value returned by the single dashboard fetch. */
interface DashboardData {
  stats: DashboardStats;
  positions: Position[];
}

// ==================== Dashboard Stats Hook ====================

/**
 * Helper: convert backend position summary to frontend Position type.
 */
function mapBackendPositions(
  positions: DashboardStatsResponse["positions"]
): Position[] {
  return positions
    .map((p) => ({
      accountId: "",
      accountName: p.account_name,
      exchange: p.exchange,
      symbol: p.symbol,
      side: p.side as "long" | "short",
      size: p.size,
      sizeUsd: p.size_usd,
      entryPrice: p.entry_price,
      markPrice: p.mark_price,
      leverage: p.leverage,
      unrealizedPnl: p.unrealized_pnl,
      unrealizedPnlPercent: p.unrealized_pnl_percent,
      liquidationPrice: p.liquidation_price ?? undefined,
    }))
    .sort((a, b) => Math.abs(b.unrealizedPnl) - Math.abs(a.unrealizedPnl));
}

/**
 * Fetch aggregated dashboard statistics **and** positions in a single request.
 *
 * Returns `{ data, positions, isLoading, mutate, ... }` where `data` is
 * `DashboardStats` (backward-compatible) and `positions` is `Position[]`.
 *
 * First tries the backend `/dashboard/stats` endpoint.  Falls back to
 * client-side aggregation when the backend is unavailable.
 */
export function useDashboardStats() {
  const { data, ...rest } = useSWR<DashboardData>(
    "/dashboard/stats",
    async () => {
      // Try backend endpoint first for efficient aggregation
      try {
        const response = await dashboardApi.getFullStats();

        // Count profitable positions from the response
        const profitablePositions = response.positions.filter(
          (p) => p.unrealized_pnl > 0
        ).length;

        const positions = mapBackendPositions(response.positions);

        const stats: DashboardStats = {
          totalEquity: response.total_equity,
          availableBalance: response.available_balance,
          unrealizedPnl: response.unrealized_pnl,
          unrealizedPnlPercent: response.total_equity > 0
            ? (response.unrealized_pnl / response.total_equity) * 100
            : 0,
          dailyPnl: response.daily_pnl,
          dailyPnlPercent: response.daily_pnl_percent,
          activeStrategies: response.active_strategies,
          totalStrategies: response.total_strategies,
          openPositions: response.open_positions,
          profitablePositions,
          connectedAccounts: response.accounts_connected,
          totalAccounts: response.accounts_total,
        };

        return { stats, positions };
      } catch {
        // Fallback to client-side aggregation (backend endpoint may not be available)
      }

      // Client-side fallback: Fetch all required data in parallel
      const [accounts, agents] = await Promise.all([
        accountsApi.list(),
        agentsApi.list(),
      ]);

      // Fetch balances for all connected accounts
      const connectedAccts = accounts.filter((acc) => acc.is_connected);
      const balancePromises = connectedAccts.map((acc) =>
        accountsApi
          .getBalance(acc.id)
          .then((balance) => ({ account: acc, balance }))
          .catch(() => ({ account: acc, balance: null as AccountBalanceResponse | null }))
      );
      const balanceResults = await Promise.all(balancePromises);

      // Aggregate balances and build positions
      let totalEquity = 0;
      let availableBalance = 0;
      let unrealizedPnl = 0;
      let openPositions = 0;
      let profitablePositions = 0;
      const allPositions: Position[] = [];

      balanceResults.forEach(({ account, balance }) => {
        if (balance) {
          totalEquity += balance.equity;
          availableBalance += balance.available_balance;
          unrealizedPnl += balance.unrealized_pnl;
          openPositions += balance.positions.length;
          profitablePositions += balance.positions.filter(
            (p) => p.unrealized_pnl > 0
          ).length;

          // Build positions from per-account balances
          for (const p of balance.positions) {
            allPositions.push({
              accountId: account.id,
              accountName: account.name,
              exchange: account.exchange,
              symbol: p.symbol,
              side: p.side as "long" | "short",
              size: p.size,
              sizeUsd: p.size_usd,
              entryPrice: p.entry_price,
              markPrice: p.mark_price,
              leverage: p.leverage,
              unrealizedPnl: p.unrealized_pnl,
              unrealizedPnlPercent: p.unrealized_pnl_percent,
              liquidationPrice: p.liquidation_price ?? undefined,
            });
          }
        }
      });

      // Sort positions by absolute PnL descending
      allPositions.sort(
        (a, b) => Math.abs(b.unrealizedPnl) - Math.abs(a.unrealizedPnl)
      );

      // Calculate percentages
      const unrealizedPnlPercent =
        totalEquity > 0 ? (unrealizedPnl / (totalEquity - unrealizedPnl)) * 100 : 0;

      // Count agents (execution instances)
      const activeStrategies = agents.filter(
        (a) => a.status === "active"
      ).length;

      // Count accounts
      const connectedAccounts = connectedAccts.length;

      const stats: DashboardStats = {
        totalEquity,
        availableBalance,
        unrealizedPnl,
        unrealizedPnlPercent,
        dailyPnl: unrealizedPnl, // Use unrealized PnL as daily PnL estimate
        dailyPnlPercent: unrealizedPnlPercent,
        activeStrategies,
        totalStrategies: agents.length,
        openPositions,
        profitablePositions,
        connectedAccounts,
        totalAccounts: accounts.length,
      };

      return { stats, positions: allPositions };
    },
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
      dedupingInterval: 5000,
    }
  );

  return {
    ...rest,
    data: data?.stats,
    positions: data?.positions ?? [],
  };
}

// ==================== All Positions Hook ====================

/**
 * Read-only accessor for positions.
 *
 * @deprecated Prefer destructuring `positions` directly from
 * `useDashboardStats()`.  This hook is kept for backward compatibility but
 * no longer makes its own API requests – it simply reads whatever
 * `useDashboardStats` last fetched.  If used on a page that does NOT mount
 * `useDashboardStats`, `data` will be `undefined`.
 */
export function useAllPositions() {
  return useSWR<Position[]>("/dashboard/positions", null);
}

// ==================== Account Balances Hook ====================

interface AccountWithBalance {
  account: AccountResponse;
  balance: AccountBalanceResponse | null;
  error?: string;
}

/**
 * Fetch all accounts with their balances
 */
export function useAccountsWithBalances() {
  return useSWR<AccountWithBalance[]>(
    "/dashboard/accounts-with-balances",
    async () => {
      const accounts = await accountsApi.list();

      const results = await Promise.all(
        accounts.map(async (account) => {
          if (!account.is_connected) {
            return { account, balance: null };
          }
          try {
            const balance = await accountsApi.getBalance(account.id);
            return { account, balance };
          } catch (err) {
            return {
              account,
              balance: null,
              error: err instanceof Error ? err.message : "Failed to fetch balance",
            };
          }
        })
      );

      return results;
    },
    {
      refreshInterval: 30000,
      revalidateOnFocus: true,
    }
  );
}

// ==================== Performance Stats Hook ====================

interface PerformanceStats {
  totalPnl: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  winRate: number;
  maxDrawdown: number;
}

/**
 * Fetch aggregated performance statistics from agents
 */
export function usePerformanceStats() {
  return useSWR<PerformanceStats>(
    "/dashboard/performance",
    async () => {
      const agents = await agentsApi.list();

      let totalPnl = 0;
      let totalTrades = 0;
      let winningTrades = 0;
      let losingTrades = 0;
      let maxDrawdown = 0;

      agents.forEach((agent) => {
        totalPnl += agent.total_pnl;
        totalTrades += agent.total_trades;
        winningTrades += agent.winning_trades;
        losingTrades += agent.losing_trades;
        maxDrawdown = Math.max(maxDrawdown, agent.max_drawdown);
      });

      const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;

      return {
        totalPnl,
        totalTrades,
        winningTrades,
        losingTrades,
        winRate,
        maxDrawdown,
      };
    },
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );
}

// ==================== Activity Feed Hook ====================

/**
 * Fetch activity feed for dashboard
 */
export function useActivityFeed(limit: number = 20) {
  return useSWR<ActivityFeedResponse>(
    `/dashboard/activity?limit=${limit}`,
    () => dashboardApi.getActivity(limit, 0),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
      dedupingInterval: 5000,
    }
  );
}
