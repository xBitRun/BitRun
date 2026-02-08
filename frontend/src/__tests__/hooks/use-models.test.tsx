/**
 * Tests for useModels hooks and utility functions
 */

import { renderHook, waitFor } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import {
  useModels,
  useModelProviders,
  useUserModels,
  getModelDisplayName,
  getProviderDisplayName,
  groupModelsByProvider,
} from "@/hooks/use-models";
import { modelsApi } from "@/lib/api/endpoints";
import type { AIModelInfoResponse } from "@/lib/api/endpoints";

// Mock the API module
jest.mock("@/lib/api/endpoints", () => ({
  modelsApi: {
    list: jest.fn(),
    listProviders: jest.fn(),
    get: jest.fn(),
    test: jest.fn(),
  },
}));

const mockedModelsApi = modelsApi as jest.Mocked<typeof modelsApi>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

// Mock data
const mockModels: AIModelInfoResponse[] = [
  {
    id: "deepseek:deepseek-chat",
    provider: "deepseek",
    name: "DeepSeek Chat",
    description: "DeepSeek general chat model",
    context_window: 32768,
    max_output_tokens: 4096,
    supports_json_mode: true,
    supports_vision: false,
    cost_per_1k_input: 0.14,
    cost_per_1k_output: 0.28,
  },
  {
    id: "deepseek:deepseek-reasoner",
    provider: "deepseek",
    name: "DeepSeek Reasoner",
    description: "DeepSeek reasoning model",
    context_window: 32768,
    max_output_tokens: 8192,
    supports_json_mode: true,
    supports_vision: false,
    cost_per_1k_input: 0.55,
    cost_per_1k_output: 2.19,
  },
  {
    id: "openai:gpt-4o",
    provider: "openai",
    name: "GPT-4o",
    description: "OpenAI GPT-4o",
    context_window: 128000,
    max_output_tokens: 4096,
    supports_json_mode: true,
    supports_vision: true,
    cost_per_1k_input: 2.5,
    cost_per_1k_output: 10,
  },
];

const mockProviders = [
  { id: "deepseek", name: "DeepSeek", configured: true },
  { id: "openai", name: "OpenAI", configured: true },
  { id: "gemini", name: "Google Gemini", configured: false },
];

describe("useModels", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch models list", async () => {
    mockedModelsApi.list.mockResolvedValue(mockModels);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.models.length).toBeGreaterThan(0));

    expect(mockedModelsApi.list).toHaveBeenCalledWith(undefined);
    expect(result.current.models).toEqual(mockModels);
    expect(result.current.models.length).toBe(3);
  });

  it("should fetch models filtered by provider", async () => {
    const deepseekModels = mockModels.filter((m) => m.provider === "deepseek");
    mockedModelsApi.list.mockResolvedValue(deepseekModels);

    const { result } = renderHook(() => useModels("deepseek"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.models.length).toBeGreaterThan(0));

    expect(mockedModelsApi.list).toHaveBeenCalledWith("deepseek");
    expect(result.current.models.length).toBe(2);
  });

  it("should return empty array when no models", async () => {
    mockedModelsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.models).toEqual([]);
  });

  it("should handle fetch error", async () => {
    mockedModelsApi.list.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useModelProviders", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fetch providers list", async () => {
    mockedModelsApi.listProviders.mockResolvedValue(mockProviders);

    const { result } = renderHook(() => useModelProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() =>
      expect(result.current.providers.length).toBeGreaterThan(0)
    );

    expect(mockedModelsApi.listProviders).toHaveBeenCalled();
    expect(result.current.providers).toEqual(mockProviders);
    expect(result.current.providers.length).toBe(3);
  });

  it("should return empty array initially", async () => {
    mockedModelsApi.listProviders.mockResolvedValue([]);

    const { result } = renderHook(() => useModelProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.providers).toEqual([]);
  });

  it("should handle provider fetch error", async () => {
    mockedModelsApi.listProviders.mockRejectedValue(
      new Error("Network error")
    );

    const { result } = renderHook(() => useModelProviders(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.error).toBeDefined());

    expect(result.current.error).toBeTruthy();
  });
});

describe("useUserModels", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should return models and hasConfiguredProviders=true when models exist", async () => {
    mockedModelsApi.list.mockResolvedValue(mockModels);

    const { result } = renderHook(() => useUserModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.models.length).toBeGreaterThan(0));

    expect(result.current.models).toEqual(mockModels);
    expect(result.current.hasConfiguredProviders).toBe(true);
  });

  it("should return hasConfiguredProviders=false when no models", async () => {
    mockedModelsApi.list.mockResolvedValue([]);

    const { result } = renderHook(() => useUserModels(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.models).toEqual([]);
    expect(result.current.hasConfiguredProviders).toBe(false);
  });
});

describe("getModelDisplayName", () => {
  it("should return model name when found in list", () => {
    expect(getModelDisplayName("deepseek:deepseek-chat", mockModels)).toBe(
      "DeepSeek Chat"
    );
  });

  it("should return formatted name for provider:model format not in list", () => {
    expect(getModelDisplayName("anthropic:claude-3", mockModels)).toBe(
      "Anthropic - claude-3"
    );
  });

  it("should return raw modelId when not in provider:model format", () => {
    expect(getModelDisplayName("some-model", mockModels)).toBe("some-model");
  });

  it("should return empty string for null modelId", () => {
    expect(getModelDisplayName(null, mockModels)).toBe("");
  });

  it("should return empty string for undefined modelId", () => {
    expect(getModelDisplayName(undefined, mockModels)).toBe("");
  });
});

describe("getProviderDisplayName", () => {
  it("should return display name for known provider", () => {
    expect(getProviderDisplayName("deepseek")).toBe("DeepSeek");
    expect(getProviderDisplayName("openai")).toBe("OpenAI");
    expect(getProviderDisplayName("gemini")).toBe("Google Gemini");
    expect(getProviderDisplayName("qwen")).toBe("Alibaba Qwen");
    expect(getProviderDisplayName("grok")).toBe("xAI Grok");
  });

  it("should return raw id for unknown provider", () => {
    expect(getProviderDisplayName("unknown-provider")).toBe("unknown-provider");
  });
});

describe("groupModelsByProvider", () => {
  it("should group models by provider", () => {
    const grouped = groupModelsByProvider(mockModels);

    expect(Object.keys(grouped)).toEqual(["deepseek", "openai"]);
    expect(grouped["deepseek"]).toHaveLength(2);
    expect(grouped["openai"]).toHaveLength(1);
  });

  it("should return empty object for empty array", () => {
    const grouped = groupModelsByProvider([]);

    expect(grouped).toEqual({});
    expect(Object.keys(grouped)).toHaveLength(0);
  });

  it("should handle single provider", () => {
    const singleProvider = mockModels.filter((m) => m.provider === "openai");
    const grouped = groupModelsByProvider(singleProvider);

    expect(Object.keys(grouped)).toEqual(["openai"]);
    expect(grouped["openai"]).toHaveLength(1);
    expect(grouped["openai"][0].name).toBe("GPT-4o");
  });
});
