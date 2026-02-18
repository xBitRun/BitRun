/**
 * Tests for useChannel hooks
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useMyChannel,
  useMyChannelUsers,
  useMyChannelWallet,
  useMyChannelStatistics,
  useMyChannelAccounting,
  useChannels,
  useChannel,
  useCreateChannel,
  useUpdateChannel,
  useUpdateChannelStatus,
} from "@/hooks/use-channel";
import { channelsApi, accountingApi } from "@/lib/api/endpoints";

// Mock the API module
jest.mock("@/lib/api/endpoints", () => ({
  channelsApi: {
    getMyChannel: jest.fn(),
    getMyUsers: jest.fn(),
    getMyWallet: jest.fn(),
    getMyStatistics: jest.fn(),
    list: jest.fn(),
    get: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    updateStatus: jest.fn(),
  },
  accountingApi: {
    getMyChannelOverview: jest.fn(),
  },
}));

const mockedChannelsApi = channelsApi as jest.Mocked<typeof channelsApi>;
const mockedAccountingApi = accountingApi as jest.Mocked<typeof accountingApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockChannel = {
  id: "channel-1",
  name: "Test Channel",
  code: "TEST01",
  commission_rate: 0.1,
  status: "active" as const,
  contact_name: "John Doe",
  contact_email: "john@test.com",
  contact_phone: null,
  admin_user_id: null,
  total_users: 10,
  total_revenue: 1000.0,
  total_commission: 100.0,
  total_accounts: 5,
  total_agents: 8,
  active_users: 5,
  available_balance: 500.0,
  pending_commission: 100.0,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const mockChannelUsers = [
  {
    id: "user-1",
    email: "user1@test.com",
    name: "User One",
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "user-2",
    email: "user2@test.com",
    name: "User Two",
    created_at: "2024-01-02T00:00:00Z",
  },
];

const mockChannelWallet = {
  channel_id: "channel-1",
  balance: 500.0,
  frozen_balance: 50.0,
  pending_commission: 100.0,
  total_commission: 600.0,
  total_withdrawn: 0.0,
};

const mockStatistics = {
  total_users: 10,
  active_users: 5,
  total_revenue: 1000.0,
  total_commission: 100.0,
  period_commission: 50.0,
  available_balance: 500.0,
  pending_commission: 100.0,
  frozen_balance: 50.0,
};

const mockAccountingOverview = {
  channel_id: "channel-1",
  channel_name: "Test Channel",
  channel_code: "TEST01",
  commission_rate: 0.1,
  total_users: 10,
  total_revenue: 1000.0,
  total_commission: 100.0,
  available_balance: 500.0,
  pending_commission: 100.0,
  period_commission: 50.0,
  active_users: 5,
};

describe("useMyChannel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch current user's channel", async () => {
    mockedChannelsApi.getMyChannel.mockResolvedValue(mockChannel);

    const { result } = renderHook(() => useMyChannel(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyChannel).toHaveBeenCalled();
    expect(result.current.channel).toEqual(mockChannel);
    expect(result.current.channel?.name).toBe("Test Channel");
  });

  it("should handle no channel", async () => {
    mockedChannelsApi.getMyChannel.mockResolvedValue(null as any);

    const { result } = renderHook(() => useMyChannel(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.channel).toBeNull();
  });

  it("should handle fetch error", async () => {
    mockedChannelsApi.getMyChannel.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useMyChannel(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());
  });

  it("should provide refresh function", async () => {
    mockedChannelsApi.getMyChannel.mockResolvedValue(mockChannel);

    const { result } = renderHook(() => useMyChannel(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.refresh).toBeDefined();
    expect(typeof result.current.refresh).toBe("function");
  });
});

describe("useMyChannelUsers", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch channel users", async () => {
    mockedChannelsApi.getMyUsers.mockResolvedValue(mockChannelUsers);

    const { result } = renderHook(() => useMyChannelUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyUsers).toHaveBeenCalled();
    expect(result.current.users).toEqual(mockChannelUsers);
    expect(result.current.users.length).toBe(2);
  });

  it("should pass params to API", async () => {
    mockedChannelsApi.getMyUsers.mockResolvedValue(mockChannelUsers);

    const params = { limit: 50, offset: 10 };
    const { result } = renderHook(() => useMyChannelUsers(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyUsers).toHaveBeenCalledWith(params);
  });

  it("should return empty array when no users", async () => {
    mockedChannelsApi.getMyUsers.mockResolvedValue([]);

    const { result } = renderHook(() => useMyChannelUsers(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.users).toEqual([]);
  });
});

describe("useMyChannelWallet", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch channel wallet", async () => {
    mockedChannelsApi.getMyWallet.mockResolvedValue(mockChannelWallet);

    const { result } = renderHook(() => useMyChannelWallet(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyWallet).toHaveBeenCalled();
    expect(result.current.wallet).toEqual(mockChannelWallet);
    expect(result.current.wallet?.balance).toBe(500.0);
  });

  it("should handle no wallet", async () => {
    mockedChannelsApi.getMyWallet.mockResolvedValue(null as any);

    const { result } = renderHook(() => useMyChannelWallet(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
  });
});

describe("useMyChannelStatistics", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch channel statistics", async () => {
    mockedChannelsApi.getMyStatistics.mockResolvedValue(mockStatistics);

    const { result } = renderHook(() => useMyChannelStatistics(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyStatistics).toHaveBeenCalled();
    expect(result.current.statistics).toEqual(mockStatistics);
    expect(result.current.statistics?.total_users).toBe(10);
    expect(result.current.statistics?.active_users).toBe(5);
  });

  it("should pass date params", async () => {
    mockedChannelsApi.getMyStatistics.mockResolvedValue(mockStatistics);

    const params = { start_date: "2024-01-01", end_date: "2024-01-31" };
    const { result } = renderHook(() => useMyChannelStatistics(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.getMyStatistics).toHaveBeenCalledWith(params);
  });
});

describe("useMyChannelAccounting", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch accounting overview", async () => {
    mockedAccountingApi.getMyChannelOverview.mockResolvedValue(mockAccountingOverview);

    const { result } = renderHook(() => useMyChannelAccounting(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountingApi.getMyChannelOverview).toHaveBeenCalled();
    expect(result.current.overview).toEqual(mockAccountingOverview);
    expect(result.current.overview?.total_revenue).toBe(1000.0);
  });

  it("should pass date params", async () => {
    mockedAccountingApi.getMyChannelOverview.mockResolvedValue(mockAccountingOverview);

    const params = { start_date: "2024-01-01", end_date: "2024-01-31" };
    const { result } = renderHook(() => useMyChannelAccounting(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountingApi.getMyChannelOverview).toHaveBeenCalledWith(params);
  });
});

describe("useChannels (Platform Admin)", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should list all channels", async () => {
    mockedChannelsApi.list.mockResolvedValue([mockChannel]);

    const { result } = renderHook(() => useChannels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.list).toHaveBeenCalled();
    expect(result.current.channels).toEqual([mockChannel]);
  });

  it("should pass filter params", async () => {
    mockedChannelsApi.list.mockResolvedValue([mockChannel]);

    const params = { status: "active", limit: 20 };
    const { result } = renderHook(() => useChannels(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.list).toHaveBeenCalledWith(params);
  });

  it("should return empty array when no channels", async () => {
    mockedChannelsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useChannels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.channels).toEqual([]);
  });
});

describe("useChannel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single channel by ID", async () => {
    mockedChannelsApi.get.mockResolvedValue(mockChannel);

    const { result } = renderHook(() => useChannel("channel-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedChannelsApi.get).toHaveBeenCalledWith("channel-1");
    expect(result.current.channel).toEqual(mockChannel);
  });

  it("should not fetch when ID is null", async () => {
    const { result } = renderHook(() => useChannel(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedChannelsApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useCreateChannel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create a new channel", async () => {
    mockedChannelsApi.create.mockResolvedValue(mockChannel);

    const { result } = renderHook(() => useCreateChannel(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      const response = await result.current.trigger({
        name: "Test Channel",
        code: "TEST01",
        commission_rate: 0.1,
      });
      expect(response).toEqual(mockChannel);
    });

    expect(mockedChannelsApi.create).toHaveBeenCalledWith({
      name: "Test Channel",
      code: "TEST01",
      commission_rate: 0.1,
    });
  });

  it("should handle creation error", async () => {
    mockedChannelsApi.create.mockRejectedValue(new Error("Duplicate code"));

    const { result } = renderHook(() => useCreateChannel(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await expect(
        result.current.trigger({
          name: "Test Channel",
          code: "TEST01",
        })
      ).rejects.toThrow("Duplicate code");
    });
  });
});

describe("useUpdateChannel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update a channel", async () => {
    const updatedChannel = { ...mockChannel, name: "Updated Channel" };
    mockedChannelsApi.update.mockResolvedValue(updatedChannel);

    const { result } = renderHook(() => useUpdateChannel(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      const response = await result.current.trigger({
        channelId: "channel-1",
        data: { name: "Updated Channel" },
      });
      expect(response).toEqual(updatedChannel);
    });

    expect(mockedChannelsApi.update).toHaveBeenCalledWith("channel-1", {
      name: "Updated Channel",
    });
  });
});

describe("useUpdateChannelStatus", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update channel status", async () => {
    const suspendedChannel = { ...mockChannel, status: "suspended" as const };
    mockedChannelsApi.updateStatus.mockResolvedValue(suspendedChannel);

    const { result } = renderHook(() => useUpdateChannelStatus(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      const response = await result.current.trigger({
        channelId: "channel-1",
        status: "suspended",
      });
      expect(response).toEqual(suspendedChannel);
    });

    expect(mockedChannelsApi.updateStatus).toHaveBeenCalledWith(
      "channel-1",
      "suspended"
    );
  });

  it("should handle all status types", async () => {
    const statuses: Array<"active" | "suspended" | "closed"> = [
      "active",
      "suspended",
      "closed",
    ];

    for (const status of statuses) {
      mockedChannelsApi.updateStatus.mockResolvedValue({
        ...mockChannel,
        status,
      });

      const { result } = renderHook(() => useUpdateChannelStatus(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        const response = await result.current.trigger({
          channelId: "channel-1",
          status,
        });
        expect(response.status).toBe(status);
      });
    }
  });
});
