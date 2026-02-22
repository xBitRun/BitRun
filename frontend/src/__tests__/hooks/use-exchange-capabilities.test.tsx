/**
 * Tests for exchange capabilities hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useExchangeCapabilities,
  useExchangeCapability,
  useExchangesForAsset,
  useSettlementCurrency,
  useSupportsAsset,
  useStrategyExchangeCompatibility,
} from "@/hooks/use-exchange-capabilities";
import { dataApi } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  dataApi: {
    getExchanges: jest.fn(),
  },
}));

const mockDataApi = dataApi as jest.Mocked<typeof dataApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

const mockExchangesResponse = {
  exchanges: [
    {
      id: "hyperliquid",
      name: "Hyperliquid",
      supported_assets: ["crypto_perp", "crypto_spot"],
      default_settlement: "USDT",
      settlement_currencies: {
        crypto_perp: "USDT",
        crypto_spot: "USDT",
      },
      max_leverage: 50,
      features: ["perp", "spot"],
    },
    {
      id: "binance",
      name: "Binance",
      supported_assets: ["crypto_perp", "crypto_spot", "equities"],
      default_settlement: "USDT",
      settlement_currencies: {
        crypto_perp: "USDT",
        crypto_spot: "USDT",
        equities: "USDC",
      },
      max_leverage: 125,
      features: ["perp", "spot", "futures"],
    },
  ],
  last_updated: "2024-01-01T00:00:00Z",
};

describe("useExchangeCapabilities", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch exchange capabilities", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangeCapabilities(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.exchanges).toHaveLength(2));

    expect(mockDataApi.getExchanges).toHaveBeenCalled();
    expect(result.current.exchanges[0].id).toBe("hyperliquid");
    expect(result.current.lastUpdated).toBe("2024-01-01T00:00:00Z");
  });

  it("should handle fetch error", async () => {
    const consoleSpy = jest.spyOn(console, "error").mockImplementation();
    mockDataApi.getExchanges.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useExchangeCapabilities(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.exchanges).toEqual([]);
    consoleSpy.mockRestore();
  });

  it("should return loading state", () => {
    mockDataApi.getExchanges.mockImplementation(() => new Promise(() => {}));

    const { result } = renderHook(() => useExchangeCapabilities(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });
});

describe("useExchangeCapability", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return specific exchange by id", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangeCapability("hyperliquid"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.exchange).toBeDefined());

    expect(result.current.exchange?.name).toBe("Hyperliquid");
    expect(result.current.maxLeverage).toBe(50);
    expect(result.current.defaultSettlement).toBe("USDT");
  });

  it("should return undefined for unknown exchange", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangeCapability("unknown"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.exchange).toBeUndefined();
    expect(result.current.supportedAssets).toEqual([]);
  });

  it("should not fetch when disabled", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useExchangeCapability("hyperliquid", false),
      { wrapper: createWrapper() }
    );

    // When disabled, it should not trigger fetch
    expect(result.current.exchange).toBeUndefined();
  });

  it("should handle case-insensitive exchange id", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangeCapability("HYPERLIQUID"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.exchange).toBeDefined());

    expect(result.current.exchange?.id).toBe("hyperliquid");
  });
});

describe("useExchangesForAsset", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should filter exchanges by asset type", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangesForAsset("equities"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.exchanges).toHaveLength(1));

    expect(result.current.exchanges[0].id).toBe("binance");
  });

  it("should return all exchanges when no asset type specified", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useExchangesForAsset(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.exchanges).toHaveLength(2));
  });
});

describe("useSettlementCurrency", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return settlement currency for exchange and asset", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useSettlementCurrency("binance", "equities"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.settlement).toBe("USDC");
  });

  it("should return default settlement when exchange not found", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useSettlementCurrency("unknown", "crypto_perp"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.settlement).toBe("USDT");
  });

  it("should use default asset type", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useSettlementCurrency("hyperliquid"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.settlement).toBe("USDT");
  });
});

describe("useSupportsAsset", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return true when exchange supports asset", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useSupportsAsset("hyperliquid", "crypto_perp"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.supports).toBe(true);
  });

  it("should return false when exchange does not support asset", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useSupportsAsset("hyperliquid", "equities"),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.supports).toBe(false);
  });

  it("should return false when exchange not specified", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useSupportsAsset(undefined, "crypto_perp"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.supports).toBe(false);
  });

  it("should return false when asset type not specified", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(() => useSupportsAsset("hyperliquid", undefined), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.supports).toBe(false);
  });
});

describe("useStrategyExchangeCompatibility", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return compatible for matching settlements", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const symbols = ["BTC/USDT:USDT", "ETH/USDT:USDT"];
    const { result } = renderHook(
      () => useStrategyExchangeCompatibility("hyperliquid", symbols),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCompatible).toBe(true);
    expect(result.current.incompatibleSymbols).toEqual([]);
  });

  it("should detect incompatible symbols", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const symbols = ["BTC/USDT:USDT", "ETH/USDC:USDC"];
    const { result } = renderHook(
      () => useStrategyExchangeCompatibility("hyperliquid", symbols),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCompatible).toBe(false);
    expect(result.current.incompatibleSymbols).toContain("ETH/USDC:USDC");
  });

  it("should return compatible when no symbols provided", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const { result } = renderHook(
      () => useStrategyExchangeCompatibility("hyperliquid", []),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCompatible).toBe(true);
  });

  it("should return compatible when exchange not found", async () => {
    mockDataApi.getExchanges.mockResolvedValue(mockExchangesResponse);

    const symbols = ["BTC/USDT:USDT"];
    const { result } = renderHook(
      () => useStrategyExchangeCompatibility("unknown", symbols),
      { wrapper: createWrapper() }
    );

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isCompatible).toBe(true);
  });
});
