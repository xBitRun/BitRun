/**
 * Channel Hooks
 *
 * SWR hooks for channel management operations.
 */

import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import {
  channelsApi,
  accountingApi,
  ChannelResponse,
  ChannelWalletResponse,
  ChannelUserResponse,
  ChannelStatisticsResponse,
  ChannelAccountingOverview,
} from "@/lib/api/endpoints";

// ==================== Channel Keys ====================

const CHANNELS_KEY = "/channels";
const MY_CHANNEL_KEY = "/channels/me";
const MY_CHANNEL_USERS_KEY = "/channels/me/users";
const MY_CHANNEL_WALLET_KEY = "/channels/me/wallet";
const MY_CHANNEL_STATS_KEY = "/channels/me/statistics";
const MY_CHANNEL_ACCOUNTING_KEY = "/accounting/channels/me/overview";

// ==================== Channel Admin Hooks ====================

/**
 * Get current user's channel (for channel admins).
 */
export function useMyChannel() {
  const swr = useSWR<ChannelResponse>(MY_CHANNEL_KEY, async () => {
    return channelsApi.getMyChannel();
  });

  return {
    ...swr,
    channel: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Get users in current channel.
 */
export function useMyChannelUsers(params?: {
  limit?: number;
  offset?: number;
}) {
  const key = params ? [MY_CHANNEL_USERS_KEY, params] : MY_CHANNEL_USERS_KEY;

  const swr = useSWR<ChannelUserResponse[]>(key, async () => {
    return channelsApi.getMyUsers(params);
  });

  return {
    ...swr,
    users: swr.data ?? [],
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Get current channel's wallet.
 */
export function useMyChannelWallet() {
  const swr = useSWR<ChannelWalletResponse>(MY_CHANNEL_WALLET_KEY, async () => {
    return channelsApi.getMyWallet();
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
 * Get current channel's statistics.
 */
export function useMyChannelStatistics(params?: {
  start_date?: string;
  end_date?: string;
}) {
  const key = params ? [MY_CHANNEL_STATS_KEY, params] : MY_CHANNEL_STATS_KEY;

  const swr = useSWR<ChannelStatisticsResponse>(key, async () => {
    return channelsApi.getMyStatistics(params);
  });

  return {
    ...swr,
    statistics: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
  };
}

/**
 * Get current channel's accounting overview.
 */
export function useMyChannelAccounting(params?: {
  start_date?: string;
  end_date?: string;
}) {
  const key = params
    ? [MY_CHANNEL_ACCOUNTING_KEY, params]
    : MY_CHANNEL_ACCOUNTING_KEY;

  const swr = useSWR<ChannelAccountingOverview>(key, async () => {
    return accountingApi.getMyChannelOverview(params);
  });

  return {
    ...swr,
    overview: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
  };
}

// ==================== Platform Admin Hooks ====================

/**
 * List all channels (platform admin only).
 */
export function useChannels(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  const key = params ? [CHANNELS_KEY, params] : CHANNELS_KEY;

  const swr = useSWR<ChannelResponse[]>(key, async () => {
    return channelsApi.list(params);
  });

  return {
    ...swr,
    channels: swr.data ?? [],
    isLoading: swr.isLoading,
    error: swr.error,
    refresh: swr.mutate,
  };
}

/**
 * Get a specific channel.
 */
export function useChannel(channelId: string | null) {
  const swr = useSWR<ChannelResponse | null>(
    channelId ? `${CHANNELS_KEY}/${channelId}` : null,
    () => {
      if (!channelId) return null;
      return channelsApi.get(channelId);
    },
  );

  return {
    ...swr,
    channel: swr.data,
    isLoading: swr.isLoading,
    error: swr.error,
  };
}

/**
 * Create a new channel (platform admin only).
 */
export function useCreateChannel() {
  return useSWRMutation<
    ChannelResponse,
    Error,
    string,
    {
      name: string;
      code: string;
      commission_rate?: number;
      contact_name?: string;
      contact_email?: string;
      contact_phone?: string;
      admin_user_id?: string;
    }
  >(CHANNELS_KEY, async (_, { arg }) => {
    return channelsApi.create(arg);
  });
}

/**
 * Update a channel (platform admin only).
 */
export function useUpdateChannel() {
  return useSWRMutation<
    ChannelResponse,
    Error,
    string,
    { channelId: string; data: Parameters<typeof channelsApi.update>[1] }
  >(CHANNELS_KEY, async (_, { arg }) => {
    return channelsApi.update(arg.channelId, arg.data);
  });
}

/**
 * Update channel status (platform admin only).
 */
export function useUpdateChannelStatus() {
  return useSWRMutation<
    ChannelResponse,
    Error,
    string,
    { channelId: string; status: "active" | "suspended" | "closed" }
  >(CHANNELS_KEY, async (_, { arg }) => {
    return channelsApi.updateStatus(arg.channelId, arg.status);
  });
}
