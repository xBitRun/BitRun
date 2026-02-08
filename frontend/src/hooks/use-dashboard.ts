/**
 * Dashboard Hooks
 *
 * Aggregates data from multiple sources for the dashboard.
 */

import useSWR from "swr";
import { accountsApi, strategiesApi, dashboardApi } from "@/lib/api";
import type {
  AccountResponse,
  AccountBalanceResponse,
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

// ==================== Dashboard Stats Hook ====================

/**
 * Fetch aggregated dashboard statistics
 *
 * First tries to use the backend aggregation endpoint for efficiency.
 * Falls back to client-side aggregation if the backend endpoint fails.
 */
export function useDashboardStats() {
  return useSWR<DashboardStats>(
    "/dashboard/stats",
    async () => {
      // Try backend endpoint first for efficient aggregation
      try {
        const response = await dashboardApi.getFullStats();

        // Count profitable positions from the response
        const profitablePositions = response.positions.filter(
          (p) => p.unrealized_pnl > 0
        ).length;

        return {
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
      } catch {
        // Fallback to client-side aggregation (backend endpoint may not be available)
      }

      // Client-side fallback: Fetch all required data in parallel
      const [accounts, strategies] = await Promise.all([
        accountsApi.list(),
        strategiesApi.list(),
      ]);

      // Fetch balances for all connected accounts
      const balancePromises = accounts
        .filter((acc) => acc.is_connected)
        .map((acc) =>
          accountsApi.getBalance(acc.id).catch(() => null)
        );
      const balances = await Promise.all(balancePromises);

      // Aggregate balances
      let totalEquity = 0;
      let availableBalance = 0;
      let unrealizedPnl = 0;
      let openPositions = 0;
      let profitablePositions = 0;

      balances.forEach((balance) => {
        if (balance) {
          totalEquity += balance.equity;
          availableBalance += balance.available_balance;
          unrealizedPnl += balance.unrealized_pnl;
          openPositions += balance.positions.length;
          profitablePositions += balance.positions.filter(
            (p) => p.unrealized_pnl > 0
          ).length;
        }
      });

      // Calculate percentages
      const unrealizedPnlPercent =
        totalEquity > 0 ? (unrealizedPnl / (totalEquity - unrealizedPnl)) * 100 : 0;

      // Count strategies
      const activeStrategies = strategies.filter(
        (s) => s.status === "active"
      ).length;

      // Count accounts
      const connectedAccounts = accounts.filter((acc) => acc.is_connected).length;

      return {
        totalEquity,
        availableBalance,
        unrealizedPnl,
        unrealizedPnlPercent,
        dailyPnl: unrealizedPnl, // Use unrealized PnL as daily PnL estimate
        dailyPnlPercent: unrealizedPnlPercent,
        activeStrategies,
        totalStrategies: strategies.length,
        openPositions,
        profitablePositions,
        connectedAccounts,
        totalAccounts: accounts.length,
      };
    },
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
      dedupingInterval: 5000,
    }
  );
}

// ==================== All Positions Hook ====================

/**
 * Fetch all positions across all accounts
 */
export function useAllPositions() {
  return useSWR<Position[]>(
    "/dashboard/positions",
    async () => {
      // Fetch accounts
      const accounts = await accountsApi.list();

      // Fetch balances for connected accounts
      const balancePromises = accounts
        .filter((acc) => acc.is_connected)
        .map(async (acc) => {
          try {
            const balance = await accountsApi.getBalance(acc.id);
            return { account: acc, balance };
          } catch {
            return null;
          }
        });

      const results = await Promise.all(balancePromises);

      // Flatten positions with account info
      const positions: Position[] = [];
      results.forEach((result) => {
        if (result && result.balance) {
          result.balance.positions.forEach((pos) => {
            positions.push({
              accountId: result.account.id,
              accountName: result.account.name,
              exchange: result.account.exchange,
              symbol: pos.symbol,
              side: pos.side as "long" | "short",
              size: pos.size,
              sizeUsd: pos.size_usd,
              entryPrice: pos.entry_price,
              markPrice: pos.mark_price,
              leverage: pos.leverage,
              unrealizedPnl: pos.unrealized_pnl,
              unrealizedPnlPercent: pos.unrealized_pnl_percent,
              liquidationPrice: pos.liquidation_price,
            });
          });
        }
      });

      // Sort by absolute PnL (highest first)
      return positions.sort(
        (a, b) => Math.abs(b.unrealizedPnl) - Math.abs(a.unrealizedPnl)
      );
    },
    {
      refreshInterval: 15000, // Refresh every 15 seconds
      revalidateOnFocus: true,
    }
  );
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
 * Fetch aggregated performance statistics from strategies
 */
export function usePerformanceStats() {
  return useSWR<PerformanceStats>(
    "/dashboard/performance",
    async () => {
      const strategies = await strategiesApi.list();

      let totalPnl = 0;
      let totalTrades = 0;
      let winningTrades = 0;
      let losingTrades = 0;
      let maxDrawdown = 0;

      strategies.forEach((strategy) => {
        totalPnl += strategy.total_pnl;
        totalTrades += strategy.total_trades;
        winningTrades += strategy.winning_trades;
        losingTrades += strategy.losing_trades;
        maxDrawdown = Math.max(maxDrawdown, strategy.max_drawdown);
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
