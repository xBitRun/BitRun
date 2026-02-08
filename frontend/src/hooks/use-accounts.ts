/**
 * Accounts Hooks
 *
 * SWR hooks for exchange account data fetching and mutations.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { useMemo } from 'react';
import { accountsApi } from '@/lib/api';
import type {
  AccountResponse,
  AccountBalanceResponse,
  CreateAccountRequest,
} from '@/lib/api';

// Keys
const ACCOUNTS_KEY = '/accounts';
const ALL_BALANCES_KEY = '/accounts/balances';
const accountKey = (id: string) => `/accounts/${id}`;
const accountBalanceKey = (id: string) => `/accounts/${id}/balance`;

/**
 * Fetch all accounts.
 * Prefer `accounts` (always array) and `refresh` for consistent list-page usage.
 */
export function useAccounts() {
  const swr = useSWR<AccountResponse[]>(
    ACCOUNTS_KEY,
    () => accountsApi.list(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    }
  );
  return {
    ...swr,
    accounts: swr.data ?? [],
    refresh: swr.mutate,
  };
}

/**
 * Fetch single account
 */
export function useAccount(id: string | null) {
  return useSWR<AccountResponse>(
    id ? accountKey(id) : null,
    () => accountsApi.get(id!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * Fetch account balance and positions
 */
export function useAccountBalance(id: string | null) {
  return useSWR<AccountBalanceResponse>(
    id ? accountBalanceKey(id) : null,
    () => accountsApi.getBalance(id!),
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
    }
  );
}

/**
 * Create account mutation
 */
export function useCreateAccount() {
  return useSWRMutation<AccountResponse, Error, string, CreateAccountRequest>(
    ACCOUNTS_KEY,
    async (_, { arg }) => {
      return accountsApi.create(arg);
    }
  );
}

/**
 * Update account mutation
 */
export function useUpdateAccount(id: string) {
  return useSWRMutation<AccountResponse, Error, string, Partial<CreateAccountRequest>>(
    accountKey(id),
    async (_, { arg }) => {
      return accountsApi.update(id, arg);
    }
  );
}

/**
 * Delete account mutation
 */
export function useDeleteAccount(id: string) {
  return useSWRMutation<void, Error, string>(
    accountKey(id),
    async () => {
      return accountsApi.delete(id);
    }
  );
}

/**
 * Test account connection mutation
 */
export function useTestAccountConnection(id: string) {
  return useSWRMutation<{ success: boolean; message: string }, Error, string>(
    `${accountKey(id)}/test`,
    async () => {
      return accountsApi.testConnection(id);
    }
  );
}

/**
 * Fetch balances for all connected accounts
 */
export function useAllAccountBalances() {
  const { data: accounts } = useAccounts();

  // Get connected account IDs
  const connectedAccountIds = useMemo(() => {
    if (!accounts) return [];
    return accounts.filter(a => a.is_connected).map(a => a.id);
  }, [accounts]);

  // Fetch all balances in parallel
  const { data: balances, isLoading, error, mutate } = useSWR<AccountBalanceResponse[]>(
    connectedAccountIds.length > 0 ? [ALL_BALANCES_KEY, ...connectedAccountIds] : null,
    async () => {
      const results = await Promise.allSettled(
        connectedAccountIds.map(id => accountsApi.getBalance(id))
      );
      return results
        .filter((r): r is PromiseFulfilledResult<AccountBalanceResponse> => r.status === 'fulfilled')
        .map(r => r.value);
    },
    {
      refreshInterval: 30000, // Refresh every 30 seconds
      revalidateOnFocus: true,
      dedupingInterval: 5000,
    }
  );

  return {
    data: balances,
    isLoading,
    error,
    mutate,
    accountCount: accounts?.length ?? 0,
    connectedCount: connectedAccountIds.length,
  };
}

/**
 * Get total equity across all accounts
 */
export function useTotalEquity() {
  const { data: balances, isLoading, accountCount, connectedCount } = useAllAccountBalances();

  const totals = useMemo(() => {
    if (!balances || balances.length === 0) {
      return {
        totalEquity: 0,
        totalAvailableBalance: 0,
        totalUnrealizedPnl: 0,
        totalMarginUsed: 0,
      };
    }

    return balances.reduce((acc, balance) => ({
      totalEquity: acc.totalEquity + (balance.equity || 0),
      totalAvailableBalance: acc.totalAvailableBalance + (balance.available_balance || 0),
      totalUnrealizedPnl: acc.totalUnrealizedPnl + (balance.unrealized_pnl || 0),
      totalMarginUsed: acc.totalMarginUsed + (balance.total_margin_used || 0),
    }), {
      totalEquity: 0,
      totalAvailableBalance: 0,
      totalUnrealizedPnl: 0,
      totalMarginUsed: 0,
    });
  }, [balances]);

  return {
    ...totals,
    isLoading,
    accountCount,
    connectedCount,
  };
}
