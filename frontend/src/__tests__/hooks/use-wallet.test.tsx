/**
 * Tests for useWallet hooks
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useWallet,
  useWalletTransactions,
  useTransactionSummary,
  useInviteInfo,
  useRechargeOrders,
  useCreateRechargeOrder,
} from "@/hooks/use-wallet";
import { walletsApi, rechargeApi } from "@/lib/api/endpoints";

// Mock the API module
jest.mock("@/lib/api/endpoints", () => ({
  walletsApi: {
    getMyWallet: jest.fn(),
    getMyTransactions: jest.fn(),
    getMySummary: jest.fn(),
    getMyInviteInfo: jest.fn(),
  },
  rechargeApi: {
    getMyOrders: jest.fn(),
    createOrder: jest.fn(),
  },
}));

const mockedWalletsApi = walletsApi as jest.Mocked<typeof walletsApi>;
const mockedRechargeApi = rechargeApi as jest.Mocked<typeof rechargeApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockWallet = {
  balance: 1000.0,
  frozen_balance: 100.0,
  total_recharged: 2000.0,
  total_consumed: 900.0,
};

const mockTransactions = [
  {
    id: "tx-1",
    type: "recharge",
    amount: 100.0,
    balance_before: 0.0,
    balance_after: 100.0,
    reference_type: "recharge_order",
    description: "Recharge",
    created_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "tx-2",
    type: "consume",
    amount: 50.0,
    balance_before: 100.0,
    balance_after: 50.0,
    reference_type: "strategy_subscription",
    description: "Consumption",
    created_at: "2024-01-02T00:00:00Z",
  },
];

const mockSummary = {
  recharge: 100.0,
  consume: 50.0,
  gift: 10.0,
};

const mockInviteInfo = {
  invite_code: "ABC123XYZ",
  referrer_id: null,
  channel_id: null,
  total_invited: 5,
};

const mockOrders = [
  {
    id: "order-1",
    order_no: "R202401010001",
    amount: 100.0,
    bonus_amount: 10.0,
    status: "completed",
    created_at: "2024-01-01T00:00:00Z",
  },
];

describe("useWallet", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch wallet info", async () => {
    mockedWalletsApi.getMyWallet.mockResolvedValue(mockWallet);

    const { result } = renderHook(() => useWallet(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMyWallet).toHaveBeenCalled();
    expect(result.current.wallet).toEqual(mockWallet);
    expect(result.current.wallet?.balance).toBe(1000.0);
  });

  it("should handle fetch error", async () => {
    mockedWalletsApi.getMyWallet.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useWallet(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should return loading state initially", () => {
    mockedWalletsApi.getMyWallet.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useWallet(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("should provide refresh function", async () => {
    mockedWalletsApi.getMyWallet.mockResolvedValue(mockWallet);

    const { result } = renderHook(() => useWallet(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.refresh).toBeDefined();
    expect(typeof result.current.refresh).toBe("function");
  });
});

describe("useWalletTransactions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch transactions", async () => {
    mockedWalletsApi.getMyTransactions.mockResolvedValue(mockTransactions);

    const { result } = renderHook(() => useWalletTransactions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMyTransactions).toHaveBeenCalled();
    expect(result.current.transactions).toEqual(mockTransactions);
    expect(result.current.transactions.length).toBe(2);
  });

  it("should pass params to API", async () => {
    mockedWalletsApi.getMyTransactions.mockResolvedValue(mockTransactions);

    const params = { types: "consume", limit: 10 };
    const { result } = renderHook(() => useWalletTransactions(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMyTransactions).toHaveBeenCalledWith(params);
  });

  it("should return empty array when no data", async () => {
    mockedWalletsApi.getMyTransactions.mockResolvedValue([]);

    const { result } = renderHook(() => useWalletTransactions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.transactions).toEqual([]);
  });

  it("should handle fetch error", async () => {
    mockedWalletsApi.getMyTransactions.mockRejectedValue(new Error("API error"));

    const { result } = renderHook(() => useWalletTransactions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());
  });
});

describe("useTransactionSummary", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch transaction summary", async () => {
    mockedWalletsApi.getMySummary.mockResolvedValue(mockSummary);

    const { result } = renderHook(() => useTransactionSummary(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMySummary).toHaveBeenCalled();
    expect(result.current.summary).toEqual(mockSummary);
    expect(result.current.summary?.recharge).toBe(100.0);
    expect(result.current.summary?.consume).toBe(50.0);
  });

  it("should pass date params", async () => {
    mockedWalletsApi.getMySummary.mockResolvedValue(mockSummary);

    const params = { start_date: "2024-01-01", end_date: "2024-01-31" };
    const { result } = renderHook(() => useTransactionSummary(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMySummary).toHaveBeenCalledWith(params);
  });
});

describe("useInviteInfo", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch invite info", async () => {
    mockedWalletsApi.getMyInviteInfo.mockResolvedValue(mockInviteInfo);

    const { result } = renderHook(() => useInviteInfo(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedWalletsApi.getMyInviteInfo).toHaveBeenCalled();
    expect(result.current.inviteInfo).toEqual(mockInviteInfo);
    expect(result.current.inviteInfo?.invite_code).toBe("ABC123XYZ");
    expect(result.current.inviteInfo?.total_invited).toBe(5);
  });

  it("should handle fetch error", async () => {
    mockedWalletsApi.getMyInviteInfo.mockRejectedValue(new Error("Not found"));

    const { result } = renderHook(() => useInviteInfo(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());
  });
});

describe("useRechargeOrders", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch recharge orders", async () => {
    mockedRechargeApi.getMyOrders.mockResolvedValue(mockOrders);

    const { result } = renderHook(() => useRechargeOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedRechargeApi.getMyOrders).toHaveBeenCalled();
    expect(result.current.orders).toEqual(mockOrders);
    expect(result.current.orders[0].status).toBe("completed");
  });

  it("should pass filter params", async () => {
    mockedRechargeApi.getMyOrders.mockResolvedValue(mockOrders);

    const params = { status: "pending", limit: 20 };
    const { result } = renderHook(() => useRechargeOrders(params), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedRechargeApi.getMyOrders).toHaveBeenCalledWith(params);
  });

  it("should return empty array when no orders", async () => {
    mockedRechargeApi.getMyOrders.mockResolvedValue([]);

    const { result } = renderHook(() => useRechargeOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.orders).toEqual([]);
  });

  it("should provide refresh function", async () => {
    mockedRechargeApi.getMyOrders.mockResolvedValue(mockOrders);

    const { result } = renderHook(() => useRechargeOrders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(result.current.refresh).toBeDefined();
  });
});

describe("useCreateRechargeOrder", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create recharge order", async () => {
    const newOrder = {
      id: "new-order",
      order_no: "R202401010002",
      amount: 200.0,
      bonus_amount: 20.0,
      status: "pending",
      created_at: "2024-01-03T00:00:00Z",
    };
    mockedRechargeApi.createOrder.mockResolvedValue(newOrder);

    const { result } = renderHook(() => useCreateRechargeOrder(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      const response = await result.current.trigger({
        amount: 200.0,
        bonus_amount: 20.0,
      });
      expect(response).toEqual(newOrder);
    });

    expect(mockedRechargeApi.createOrder).toHaveBeenCalledWith({
      amount: 200.0,
      bonus_amount: 20.0,
    });
  });

  it("should create order without bonus", async () => {
    const newOrder = {
      id: "new-order",
      order_no: "R202401010003",
      amount: 100.0,
      bonus_amount: 0.0,
      status: "pending",
      created_at: "2024-01-03T00:00:00Z",
    };
    mockedRechargeApi.createOrder.mockResolvedValue(newOrder);

    const { result } = renderHook(() => useCreateRechargeOrder(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      const response = await result.current.trigger({ amount: 100.0 });
      expect(response).toEqual(newOrder);
    });

    expect(mockedRechargeApi.createOrder).toHaveBeenCalledWith({ amount: 100.0 });
  });

  it("should handle creation error", async () => {
    mockedRechargeApi.createOrder.mockRejectedValue(new Error("Creation failed"));

    const { result } = renderHook(() => useCreateRechargeOrder(), {
      wrapper: createWrapper(),
    });

    await act(async () => {
      await expect(
        result.current.trigger({ amount: 100.0 })
      ).rejects.toThrow("Creation failed");
    });
  });

  it("should track isMutating state", async () => {
    let resolvePromise: (value: typeof newOrder) => void;
    const newOrder = {
      id: "new-order",
      order_no: "R202401010004",
      amount: 100.0,
      bonus_amount: 0.0,
      status: "pending",
      created_at: "2024-01-03T00:00:00Z",
    };
    mockedRechargeApi.createOrder.mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      })
    );

    const { result } = renderHook(() => useCreateRechargeOrder(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isMutating).toBe(false);

    const triggerPromise = act(async () => {
      await result.current.trigger({ amount: 100.0 });
    });

    // Check isMutating during mutation
    await waitFor(() => expect(result.current.isMutating).toBe(true));

    // Resolve the promise
    resolvePromise!(newOrder);
    await triggerPromise;

    // Check isMutating after completion
    await waitFor(() => expect(result.current.isMutating).toBe(false));
  });
});
