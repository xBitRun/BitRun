/**
 * Wallet Hooks
 *
 * SWR hooks for wallet and recharge operations.
 */

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import {
  walletsApi,
  rechargeApi,
  WalletResponse,
  WalletTransactionResponse,
  TransactionSummaryResponse,
  InviteInfoResponse,
  RechargeOrderResponse,
  RechargeOrderListResponse,
} from "@/lib/api/endpoints";

// ==================== Wallet Keys ====================

const WALLET_KEY = "/wallets/me";
const WALLET_TRANSACTIONS_KEY = "/wallets/me/transactions";
const WALLET_SUMMARY_KEY = "/wallets/me/summary";
const INVITE_INFO_KEY = "/wallets/me/invite";
const RECHARGE_ORDERS_KEY = "/recharge/orders";

// ==================== Wallet Hooks ====================

/**
 * Get current user's wallet info.
 */
export function useWallet() {
  const swr = useSWR<WalletResponse>(WALLET_KEY, async () => {
    return walletsApi.getMyWallet();
  });

  return {
    ...swr,
    wallet: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Get wallet transaction history.
 */
export function useWalletTransactions(params?: {
  types?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const key = params
    ? [WALLET_TRANSACTIONS_KEY, params]
    : WALLET_TRANSACTIONS_KEY;

  const swr = useSWR<WalletTransactionResponse[]>(key, async () => {
    return walletsApi.getMyTransactions(params);
  });

  return {
    ...swr,
    transactions: swr.data ?? [],
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Get transaction summary by type.
 */
export function useTransactionSummary(params?: {
  start_date?: string;
  end_date?: string;
}) {
  const key = params ? [WALLET_SUMMARY_KEY, params] : WALLET_SUMMARY_KEY;

  const swr = useSWR<TransactionSummaryResponse>(key, async () => {
    return walletsApi.getMySummary(params);
  });

  return {
    ...swr,
    summary: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
  };
}

/**
 * Get user's invitation info.
 */
export function useInviteInfo() {
  const swr = useSWR<InviteInfoResponse>(INVITE_INFO_KEY, async () => {
    return walletsApi.getMyInviteInfo();
  });

  return {
    ...swr,
    inviteInfo: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
  };
}

// ==================== Recharge Hooks ====================

/**
 * Get user's recharge orders.
 */
export function useRechargeOrders(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const key = params ? [RECHARGE_ORDERS_KEY, params] : RECHARGE_ORDERS_KEY;

  const swr = useSWR<RechargeOrderResponse[]>(key, async () => {
    return rechargeApi.getMyOrders(params);
  });

  return {
    ...swr,
    orders: swr.data ?? [],
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Create a new recharge order.
 */
export function useCreateRechargeOrder() {
  return useSWRMutation<
    RechargeOrderResponse,
    Error,
    string,
    { amount: number; bonus_amount?: number }
  >(RECHARGE_ORDERS_KEY, async (_, { arg }) => {
    return rechargeApi.createOrder(arg);
  });
}

// ==================== Admin Recharge Hooks ====================

const ADMIN_RECHARGE_ORDERS_KEY = "/recharge/admin/orders";

/**
 * Get all recharge orders (admin only).
 */
export function useAdminRechargeOrders(params?: {
  status?: string;
  user_id?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}) {
  const key = params
    ? [ADMIN_RECHARGE_ORDERS_KEY, params]
    : ADMIN_RECHARGE_ORDERS_KEY;

  const swr = useSWR<RechargeOrderListResponse[]>(key, async () => {
    return rechargeApi.adminListOrders(params);
  });

  return {
    ...swr,
    orders: swr.data ?? [],
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}
