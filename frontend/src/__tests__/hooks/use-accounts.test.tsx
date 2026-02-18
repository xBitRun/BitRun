/**
 * Tests for useAccounts hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useAccounts,
  useAccount,
  useAccountBalance,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useTestAccountConnection,
  useAllAccountBalances,
  useTotalEquity,
} from "@/hooks/use-accounts";
import { accountsApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  accountsApi: {
    list: jest.fn(),
    get: jest.fn(),
    getBalance: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
    delete: jest.fn(),
    testConnection: jest.fn(),
  },
}));

const mockedAccountsApi = accountsApi as jest.Mocked<typeof accountsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockAccounts = [
  {
    id: "account-1",
    name: "Binance Main",
    exchange: "binance" as const,
    is_testnet: false,
    is_connected: true,
    has_api_key: true,
    has_api_secret: true,
    has_private_key: false,
    has_passphrase: false,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "account-2",
    name: "OKX Test",
    exchange: "okx" as const,
    is_testnet: true,
    is_connected: false,
    has_api_key: true,
    has_api_secret: true,
    has_private_key: false,
    has_passphrase: false,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
];

const mockBalance = {
  account_id: "account-1",
  equity: 10000,
  available_balance: 8000,
  total_margin_used: 2000,
  unrealized_pnl: 500,
  positions: [],
};

describe("useAccounts", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch accounts list", async () => {
    mockedAccountsApi.list.mockResolvedValue(mockAccounts);

    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountsApi.list).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockAccounts);
  });

  it("should handle fetch error", async () => {
    mockedAccountsApi.list.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });

  it("should return loading state initially", () => {
    mockedAccountsApi.list.mockReturnValue(new Promise(() => {})); // Never resolves

    const { result } = renderHook(() => useAccounts(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useAccount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch single account", async () => {
    mockedAccountsApi.get.mockResolvedValue(mockAccounts[0]);

    const { result } = renderHook(() => useAccount("account-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountsApi.get).toHaveBeenCalledWith("account-1");
    expect(result.current.data).toEqual(mockAccounts[0]);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useAccount(null), {
      wrapper: createWrapper(),
    });

    // Wait a bit to ensure no fetch happens
    await new Promise((r) => setTimeout(r, 100));

    expect(mockedAccountsApi.get).not.toHaveBeenCalled();
    expect(result.current.data).toBeUndefined();
  });
});

describe("useAccountBalance", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch account balance", async () => {
    mockedAccountsApi.getBalance.mockResolvedValue(mockBalance);

    const { result } = renderHook(() => useAccountBalance("account-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.data).toBeDefined());

    expect(mockedAccountsApi.getBalance).toHaveBeenCalledWith("account-1");
    expect(result.current.data?.equity).toBe(10000);
  });

  it("should not fetch when id is null", async () => {
    const { result } = renderHook(() => useAccountBalance(null), {
      wrapper: createWrapper(),
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedAccountsApi.getBalance).not.toHaveBeenCalled();
  });
});

describe("useCreateAccount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should create account", async () => {
    const newAccount = { ...mockAccounts[0], id: "new-account" };
    mockedAccountsApi.create.mockResolvedValue(newAccount);

    const { result } = renderHook(() => useCreateAccount(), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({
      name: "New Account",
      exchange: "binance",
      is_testnet: false,
      api_key: "key",
      api_secret: "secret",
    });

    expect(mockedAccountsApi.create).toHaveBeenCalled();
  });

  it("should handle creation error", async () => {
    mockedAccountsApi.create.mockRejectedValue(new Error("Creation failed"));

    const { result } = renderHook(() => useCreateAccount(), {
      wrapper: createWrapper(),
    });

    await expect(
      result.current.trigger({
        name: "New Account",
        exchange: "binance",
        is_testnet: false,
        api_key: "key",
        api_secret: "secret",
      })
    ).rejects.toThrow("Creation failed");
  });
});

describe("useUpdateAccount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update account", async () => {
    const updatedAccount = { ...mockAccounts[0], name: "Updated Name" };
    mockedAccountsApi.update.mockResolvedValue(updatedAccount);

    const { result } = renderHook(() => useUpdateAccount("account-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger({ name: "Updated Name" });

    expect(mockedAccountsApi.update).toHaveBeenCalledWith("account-1", {
      name: "Updated Name",
    });
  });
});

describe("useDeleteAccount", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should delete account", async () => {
    mockedAccountsApi.delete.mockResolvedValue(undefined);

    const { result } = renderHook(() => useDeleteAccount("account-1"), {
      wrapper: createWrapper(),
    });

    await result.current.trigger();

    expect(mockedAccountsApi.delete).toHaveBeenCalledWith("account-1");
  });
});

describe("useTestAccountConnection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should test connection successfully", async () => {
    mockedAccountsApi.testConnection.mockResolvedValue({
      success: true,
      message: "Connected",
    });

    const { result } = renderHook(() => useTestAccountConnection("account-1"), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger();

    expect(mockedAccountsApi.testConnection).toHaveBeenCalledWith("account-1");
    expect(response?.success).toBe(true);
  });

  it("should handle connection failure", async () => {
    mockedAccountsApi.testConnection.mockResolvedValue({
      success: false,
      message: "Invalid credentials",
    });

    const { result } = renderHook(() => useTestAccountConnection("account-1"), {
      wrapper: createWrapper(),
    });

    const response = await result.current.trigger();

    expect(response?.success).toBe(false);
    expect(response?.message).toBe("Invalid credentials");
  });
});

describe("useAllAccountBalances", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch balances for connected accounts", async () => {
    mockedAccountsApi.list.mockResolvedValue(mockAccounts);
    mockedAccountsApi.getBalance.mockResolvedValue(mockBalance);

    const { result } = renderHook(() => useAllAccountBalances(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.accountCount).toBe(2));

    expect(result.current.connectedCount).toBe(1);
  });

  it("should return empty when no accounts", async () => {
    mockedAccountsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useAllAccountBalances(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.accountCount).toBe(0);
    expect(result.current.connectedCount).toBe(0);
  });
});

describe("useTotalEquity", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should calculate total equity", async () => {
    const connectedAccounts = [
      { ...mockAccounts[0], is_connected: true },
      { ...mockAccounts[1], id: "account-2", is_connected: true },
    ];
    mockedAccountsApi.list.mockResolvedValue(connectedAccounts);
    mockedAccountsApi.getBalance.mockResolvedValue(mockBalance);

    const { result } = renderHook(() => useTotalEquity(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    // Total equity should be calculated from balances
    expect(result.current.accountCount).toBe(2);
  });

  it("should return zero totals when no balances", async () => {
    mockedAccountsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useTotalEquity(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.totalEquity).toBe(0);
    expect(result.current.totalAvailableBalance).toBe(0);
    expect(result.current.totalUnrealizedPnl).toBe(0);
    expect(result.current.totalMarginUsed).toBe(0);
  });
});
