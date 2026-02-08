/**
 * Tests for useProviders hooks
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  usePresetProviders,
  useProviderConfigs,
  useApiFormats,
  getPresetInfo,
  getProviderIcon,
  getProviderConfigDisplayName,
} from "@/hooks/use-providers";
import { providersApi } from "@/lib/api/endpoints";

// Mock the API module (must match the import path used by the hook)
jest.mock("@/lib/api/endpoints", () => ({
  providersApi: {
    listPresets: jest.fn(),
    list: jest.fn(),
    listFormats: jest.fn(),
  },
}));

const mockedProvidersApi = providersApi as jest.Mocked<typeof providersApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      SWRConfig,
      { value: { provider: () => new Map(), dedupingInterval: 0 } },
      children
    );
};

// Mock data
const mockPresets = [
  {
    id: "deepseek",
    name: "DeepSeek",
    base_url: "https://api.deepseek.com/v1",
    api_format: "openai",
    website_url: "https://deepseek.com",
  },
  {
    id: "openai",
    name: "OpenAI",
    base_url: "https://api.openai.com/v1",
    api_format: "openai",
    website_url: "https://openai.com",
  },
];

const mockProviderConfigs = [
  {
    id: "config-1",
    provider_type: "deepseek",
    name: "My DeepSeek",
    note: null,
    website_url: null,
    base_url: "https://api.deepseek.com/v1",
    api_format: "openai",
    is_enabled: true,
    has_api_key: true,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "config-2",
    provider_type: "openai",
    name: "OpenAI Config",
    note: "Production key",
    website_url: null,
    base_url: null,
    api_format: "openai",
    is_enabled: false,
    has_api_key: true,
    created_at: "2024-01-02T00:00:00Z",
    updated_at: "2024-01-02T00:00:00Z",
  },
];

const mockFormats = {
  formats: [
    { id: "openai", name: "OpenAI Compatible" },
    { id: "anthropic", name: "Anthropic" },
  ],
};

describe("usePresetProviders", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch preset providers", async () => {
    mockedProvidersApi.listPresets.mockResolvedValue(mockPresets);

    const { result } = renderHook(() => usePresetProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.presets.length).toBeGreaterThan(0));

    expect(mockedProvidersApi.listPresets).toHaveBeenCalled();
    expect(result.current.presets).toEqual(mockPresets);
  });

  it("should return loading state initially", () => {
    mockedProvidersApi.listPresets.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => usePresetProviders(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.presets).toEqual([]);
  });

  it("should handle fetch error", async () => {
    mockedProvidersApi.listPresets.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => usePresetProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useProviderConfigs", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch provider configs", async () => {
    mockedProvidersApi.list.mockResolvedValue(mockProviderConfigs);

    const { result } = renderHook(() => useProviderConfigs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.providers.length).toBeGreaterThan(0));

    expect(mockedProvidersApi.list).toHaveBeenCalled();
    expect(result.current.providers).toEqual(mockProviderConfigs);
  });

  it("should return empty array when loading", () => {
    mockedProvidersApi.list.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useProviderConfigs(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.providers).toEqual([]);
  });

  it("should handle fetch error", async () => {
    mockedProvidersApi.list.mockRejectedValue(new Error("API error"));

    const { result } = renderHook(() => useProviderConfigs(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useApiFormats", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch API formats", async () => {
    mockedProvidersApi.listFormats.mockResolvedValue(mockFormats);

    const { result } = renderHook(() => useApiFormats(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.formats.length).toBeGreaterThan(0));

    expect(mockedProvidersApi.listFormats).toHaveBeenCalled();
    expect(result.current.formats).toEqual(mockFormats.formats);
  });

  it("should return empty array when loading", () => {
    mockedProvidersApi.listFormats.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useApiFormats(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.formats).toEqual([]);
  });
});

describe("getPresetInfo", () => {
  it("should find preset by id", () => {
    const result = getPresetInfo("deepseek", mockPresets);
    expect(result).toEqual(mockPresets[0]);
  });

  it("should return undefined for unknown preset", () => {
    const result = getPresetInfo("unknown", mockPresets);
    expect(result).toBeUndefined();
  });
});

describe("getProviderIcon", () => {
  it("should return correct icon for known providers", () => {
    expect(getProviderIcon("deepseek")).toBe("🔍");
    expect(getProviderIcon("openai")).toBe("🤖");
    expect(getProviderIcon("gemini")).toBe("💎");
    expect(getProviderIcon("kimi")).toBe("🌙");
  });

  it("should return default icon for unknown provider", () => {
    expect(getProviderIcon("unknown_provider")).toBe("🤖");
  });
});

describe("getProviderConfigDisplayName", () => {
  it("should return correct display name for known providers", () => {
    expect(getProviderConfigDisplayName("deepseek")).toBe("DeepSeek");
    expect(getProviderConfigDisplayName("openai")).toBe("OpenAI");
    expect(getProviderConfigDisplayName("qwen")).toBe("Alibaba Qwen");
    expect(getProviderConfigDisplayName("grok")).toBe("xAI Grok");
  });

  it("should return provider type string for unknown provider", () => {
    expect(getProviderConfigDisplayName("unknown_type")).toBe("unknown_type");
  });
});
