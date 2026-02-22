/**
 * Tests for useStrategyStudio hook and apiResponseToConfig helper
 */

import { renderHook, waitFor, act } from "@testing-library/react";
import { SWRConfig } from "swr";
import React from "react";
import { useStrategyStudio, apiResponseToConfig } from "@/hooks/use-strategy-studio";
import { api } from "@/lib/api";

// Mock the API module
jest.mock("@/lib/api", () => ({
  api: {
    post: jest.fn(),
  },
}));

// Mock @/types - provide the real defaults and helper
jest.mock("@/types", () => {
  const DEFAULT_STRATEGY_STUDIO_CONFIG = {
    name: "",
    description: "",
    accountId: "",
    aiModel: "",
    tradingMode: "conservative",
    symbols: ["BTC", "ETH"],
    timeframes: ["15m", "1h", "4h"],
    executionIntervalMinutes: 30,
    autoExecute: true,
    indicators: {
      ema: { enabled: true, periods: [9, 21, 55] },
      rsi: { enabled: true, period: 14 },
      macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
      atr: { enabled: true, period: 14 },
    },
    riskControls: {
      maxLeverage: 5,
      maxPositionRatio: 0.2,
      maxTotalExposure: 0.8,
      minRiskRewardRatio: 2.0,
      maxDrawdownPercent: 0.1,
      minConfidence: 60,
    },
    language: "en",
    promptSections: {
      roleDefinition: "",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
    },
    customPrompt: "",
  };

  const DEFAULT_RISK_CONTROLS = DEFAULT_STRATEGY_STUDIO_CONFIG.riskControls;

  return {
    __esModule: true,
    DEFAULT_STRATEGY_STUDIO_CONFIG,
    DEFAULT_RISK_CONTROLS,
    getDefaultPromptSections: jest.fn(() => ({
      roleDefinition: "",
      tradingFrequency: "",
      entryStandards: "",
      decisionProcess: "",
    })),
    getStrategyPreset: jest.fn((riskProfile: string, timeHorizon: string) => {
      if (riskProfile === "aggressive" && timeHorizon === "scalp") {
        return {
          values: {
            tradingMode: "aggressive",
            symbols: ["BTC", "ETH", "SOL"],
            timeframes: ["1m", "5m", "15m"],
            executionIntervalMinutes: 5,
            indicators: DEFAULT_STRATEGY_STUDIO_CONFIG.indicators,
            riskControls: { ...DEFAULT_STRATEGY_STUDIO_CONFIG.riskControls, maxLeverage: 20 },
          },
        };
      }
      return undefined;
    }),
  };
});

const mockedApi = api as jest.Mocked<typeof api>;

// SWR provider that clears cache between tests
const createWrapper = () => {
  return ({ children }: { children: React.ReactNode }) => (
    <SWRConfig value={{ provider: () => new Map(), dedupingInterval: 0 }}>
      {children}
    </SWRConfig>
  );
};

describe("useStrategyStudio - initial state", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should have default config values", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    expect(result.current.config.name).toBe("");
    expect(result.current.config.symbols).toEqual(["BTC", "ETH"]);
    expect(result.current.config.tradingMode).toBe("conservative");
  });

  it("should apply initialConfig override", () => {
    const { result } = renderHook(
      () => useStrategyStudio({ initialConfig: { name: "My Strategy", symbols: ["SOL"] } }),
      { wrapper: createWrapper() }
    );

    expect(result.current.config.name).toBe("My Strategy");
    expect(result.current.config.symbols).toEqual(["SOL"]);
    // Non-overridden fields stay default
    expect(result.current.config.tradingMode).toBe("conservative");
  });

  it("should default to coins tab", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    expect(result.current.activeTab).toBe("coins");
  });

  it("should start with isValid true and no errors", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isValid).toBe(true);
    expect(Object.keys(result.current.errors)).toHaveLength(0);
  });
});

describe("useStrategyStudio - config updates", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update basic info", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateBasicInfo({ name: "Test Strategy", aiModel: "deepseek:chat" });
    });

    expect(result.current.config.name).toBe("Test Strategy");
    expect(result.current.config.aiModel).toBe("deepseek:chat");
  });

  it("should update symbols", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateSymbols(["BTC", "SOL", "DOGE"]);
    });

    expect(result.current.config.symbols).toEqual(["BTC", "SOL", "DOGE"]);
  });

  it("should update trading config", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateTradingConfig({ tradingMode: "aggressive", executionIntervalMinutes: 5 });
    });

    expect(result.current.config.tradingMode).toBe("aggressive");
    expect(result.current.config.executionIntervalMinutes).toBe(5);
  });

  it("should update custom prompt", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateCustomPrompt("You are a momentum trader");
    });

    expect(result.current.config.customPrompt).toBe("You are a momentum trader");
  });

  it("should change active tab", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.setActiveTab("preview");
    });

    expect(result.current.activeTab).toBe("preview");
  });
});

describe("useStrategyStudio - validation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fail validation when name is empty", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    let valid: boolean;
    act(() => {
      valid = result.current.validate();
    });

    expect(valid!).toBe(false);
    expect(result.current.errors.name).toBe("Name is required");
  });

  it("should fail validation when symbols is empty", () => {
    const { result } = renderHook(
      () => useStrategyStudio({ initialConfig: { name: "Test", symbols: [] } }),
      { wrapper: createWrapper() }
    );

    let valid: boolean;
    act(() => {
      valid = result.current.validate();
    });

    expect(valid!).toBe(false);
    expect(result.current.errors.symbols).toBeDefined();
  });

  it("should pass validation with valid config", () => {
    const { result } = renderHook(
      () => useStrategyStudio({ initialConfig: { name: "Valid Strategy" } }),
      { wrapper: createWrapper() }
    );

    let valid: boolean;
    act(() => {
      valid = result.current.validate();
    });

    expect(valid!).toBe(true);
    expect(Object.keys(result.current.errors)).toHaveLength(0);
  });
});

describe("useStrategyStudio - preset and reset", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should apply preset when found", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.applyPreset("aggressive", "scalp");
    });

    expect(result.current.config.tradingMode).toBe("aggressive");
    expect(result.current.config.symbols).toEqual(["BTC", "ETH", "SOL"]);
    expect(result.current.config.executionIntervalMinutes).toBe(5);
  });

  it("should not change config when preset not found", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.applyPreset("conservative", "position");
    });

    // Should remain default
    expect(result.current.config.tradingMode).toBe("conservative");
    expect(result.current.config.symbols).toEqual(["BTC", "ETH"]);
  });

  it("should reset to initial state", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateBasicInfo({ name: "Changed" });
      result.current.setActiveTab("risk");
    });

    expect(result.current.config.name).toBe("Changed");
    expect(result.current.activeTab).toBe("risk");

    act(() => {
      result.current.reset();
    });

    expect(result.current.config.name).toBe("");
    expect(result.current.activeTab).toBe("coins");
  });
});

describe("useStrategyStudio - preview", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch preview when not on preview tab", async () => {
    renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    // Wait a bit to ensure no fetch happens
    await new Promise((r) => setTimeout(r, 100));

    expect(mockedApi.post).not.toHaveBeenCalled();
  });

  it("should fetch preview when on preview tab", async () => {
    mockedApi.post.mockResolvedValue({
      system_prompt: "You are a trader...",
      estimated_tokens: 500,
      sections: {
        role_definition: "Role section",
        trading_mode: "Mode section",
        trading_frequency: "",
        entry_standards: "",
        decision_process: "",
        custom_prompt: "",
      },
    });

    const { result } = renderHook(
      () => useStrategyStudio({ autoPreview: true }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.setActiveTab("preview");
    });

    await waitFor(() => expect(result.current.promptPreview).not.toBeNull());

    expect(mockedApi.post).toHaveBeenCalledWith(
      "/strategies/preview-prompt",
      expect.objectContaining({ trading_mode: "conservative" })
    );
    expect(result.current.promptPreview?.systemPrompt).toBe("You are a trader...");
    expect(result.current.promptPreview?.estimatedTokens).toBe(500);
  });
});

describe("apiResponseToConfig", () => {
  it("should convert API response to frontend config", () => {
    const response = {
      name: "API Strategy",
      description: "From API",
      account_id: "acc-1",
      ai_model: "openai:gpt-4o",
      trading_mode: "aggressive",
      prompt: "Custom prompt text",
      config: {
        language: "zh",
        symbols: ["BTC", "SOL"],
        timeframes: ["1h", "4h"],
        execution_interval_minutes: 15,
        auto_execute: false,
        indicators: {
          ema_periods: [20, 50],
          rsi_period: 21,
          macd_fast: 12,
          macd_slow: 26,
          macd_signal: 9,
          atr_period: 14,
        },
        risk_controls: {
          max_leverage: 10,
          max_position_ratio: 0.3,
          max_total_exposure: 0.9,
          min_risk_reward_ratio: 1.5,
          max_drawdown_percent: 0.2,
          min_confidence: 70,
        },
        prompt_sections: {
          role_definition: "You are a trader",
          trading_frequency: "Trade often",
          entry_standards: "Enter when...",
          decision_process: "Decide by...",
        },
      },
    };

    const config = apiResponseToConfig(response);

    expect(config.name).toBe("API Strategy");
    expect(config.aiModel).toBe("openai:gpt-4o");
    expect(config.tradingMode).toBe("aggressive");
    expect(config.language).toBe("zh");
    expect(config.symbols).toEqual(["BTC", "SOL"]);
    expect(config.autoExecute).toBe(false);
    expect(config.riskControls?.maxLeverage).toBe(10);
    expect(config.promptSections?.roleDefinition).toBe("You are a trader");
  });

  it("should use defaults for missing fields", () => {
    const config = apiResponseToConfig({});

    expect(config.name).toBe("");
    expect(config.symbols).toEqual(["BTC", "ETH"]);
    expect(config.tradingMode).toBe("conservative");
    expect(config.riskControls?.maxLeverage).toBe(5);
  });

  it("should handle disabled indicators", () => {
    const response = {
      config: {
        indicators: {
          ema_periods: [],
          rsi_period: 0,
          macd_fast: 0,
          macd_slow: 0,
          macd_signal: 0,
          atr_period: 0,
        },
      },
    };

    const config = apiResponseToConfig(response);

    expect(config.indicators?.ema.enabled).toBe(false);
    expect(config.indicators?.rsi.enabled).toBe(false);
    expect(config.indicators?.macd.enabled).toBe(false);
    expect(config.indicators?.atr.enabled).toBe(false);
  });

  it("should handle advanced prompt mode", () => {
    const response = {
      config: {
        prompt_mode: "advanced",
        advanced_prompt: "Full markdown prompt",
      },
    };

    const config = apiResponseToConfig(response);

    expect(config.promptMode).toBe("advanced");
    expect(config.advancedPrompt).toBe("Full markdown prompt");
  });

  it("should handle null account_id", () => {
    const response = {
      account_id: null,
    };

    const config = apiResponseToConfig(response);

    expect(config.accountId).toBe("");
  });
});

describe("useStrategyStudio - update helpers", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update timeframes", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateTimeframes(["1h", "4h", "1d"]);
    });

    expect(result.current.config.timeframes).toEqual(["1h", "4h", "1d"]);
  });

  it("should update indicators", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    const newIndicators = {
      ema: { enabled: false, periods: [5, 10] },
      rsi: { enabled: true, period: 21 },
      macd: { enabled: true, fast: 8, slow: 17, signal: 9 },
      atr: { enabled: false, period: 10 },
    };

    act(() => {
      result.current.updateIndicators(newIndicators);
    });

    expect(result.current.config.indicators).toEqual(newIndicators);
  });

  it("should update risk controls", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    const newRiskControls = {
      maxLeverage: 10,
      maxPositionRatio: 0.3,
      maxTotalExposure: 0.9,
      minRiskRewardRatio: 1.5,
      maxDrawdownPercent: 0.2,
      minConfidence: 70,
      defaultSlAtrMultiplier: 1.5,
      defaultTpAtrMultiplier: 3.0,
      maxSlPercent: 5,
    };

    act(() => {
      result.current.updateRiskControls(newRiskControls);
    });

    expect(result.current.config.riskControls).toEqual(newRiskControls);
  });

  it("should update prompt sections", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    const newSections = {
      roleDefinition: "You are a trader",
      tradingFrequency: "Trade every hour",
      entryStandards: "High confidence only",
      decisionProcess: "Multi-step analysis",
    };

    act(() => {
      result.current.updatePromptSections(newSections);
    });

    expect(result.current.config.promptSections).toEqual(newSections);
  });

  it("should update custom prompt", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.updateCustomPrompt("New custom prompt");
    });

    expect(result.current.config.customPrompt).toBe("New custom prompt");
  });
});

describe("useStrategyStudio - validation edge cases", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should fail validation when timeframes is empty", () => {
    const { result } = renderHook(
      () => useStrategyStudio({ initialConfig: { name: "Test", timeframes: [] } }),
      { wrapper: createWrapper() }
    );

    let valid: boolean;
    act(() => {
      valid = result.current.validate();
    });

    expect(valid!).toBe(false);
    expect(result.current.errors.timeframes).toBe("At least one timeframe is required");
  });
});

describe("useStrategyStudio - toApiFormat", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should convert config to API format", () => {
    const { result } = renderHook(
      () => useStrategyStudio({
        initialConfig: {
          name: "Test Strategy",
          description: "Test Description",
          accountId: "acc-1",
          aiModel: "deepseek:chat",
          tradingMode: "aggressive",
          symbols: ["BTC", "SOL"],
          timeframes: ["1h", "4h"],
          customPrompt: "Custom prompt",
          advancedPrompt: "Advanced prompt",
        },
      }),
      { wrapper: createWrapper() }
    );

    let apiFormat: Record<string, unknown>;
    act(() => {
      apiFormat = result.current.toApiFormat();
    });

    expect(apiFormat!.name).toBe("Test Strategy");
    expect(apiFormat!.description).toBe("Test Description");
    expect(apiFormat!.account_id).toBe("acc-1");
    expect(apiFormat!.ai_model).toBe("deepseek:chat");
    expect(apiFormat!.trading_mode).toBe("aggressive");
    expect((apiFormat!.config as Record<string, unknown>).symbols).toEqual(["BTC", "SOL"]);
  });

  it("should handle disabled indicators in API format", () => {
    const { result } = renderHook(
      () => useStrategyStudio({
        initialConfig: {
          name: "Test",
          indicators: {
            ema: { enabled: false, periods: [9, 21] },
            rsi: { enabled: false, period: 14 },
            macd: { enabled: false, fast: 12, slow: 26, signal: 9 },
            atr: { enabled: false, period: 14 },
          },
        },
      }),
      { wrapper: createWrapper() }
    );

    let apiFormat: Record<string, unknown>;
    act(() => {
      apiFormat = result.current.toApiFormat();
    });

    const indicators = (apiFormat!.config as Record<string, unknown>).indicators as Record<string, unknown>;
    expect(indicators.ema_periods).toEqual([]);
    expect(indicators.rsi_period).toBe(0);
    expect(indicators.macd_fast).toBe(0);
  });

  it("should handle null accountId", () => {
    const { result } = renderHook(
      () => useStrategyStudio({
        initialConfig: {
          name: "Test",
          accountId: "",
        },
      }),
      { wrapper: createWrapper() }
    );

    let apiFormat: Record<string, unknown>;
    act(() => {
      apiFormat = result.current.toApiFormat();
    });

    expect(apiFormat!.account_id).toBe(null);
  });
});

describe("useStrategyStudio - preview edge cases", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should not fetch preview when autoPreview is false", async () => {
    const { result } = renderHook(
      () => useStrategyStudio({ autoPreview: false }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.setActiveTab("preview");
    });

    await new Promise((r) => setTimeout(r, 100));

    expect(mockedApi.post).not.toHaveBeenCalled();
  });

  it("should refresh preview when refreshPreview called", async () => {
    mockedApi.post.mockResolvedValue({
      system_prompt: "Prompt",
      estimated_tokens: 100,
      sections: {},
    });

    const { result } = renderHook(
      () => useStrategyStudio({ autoPreview: true }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.setActiveTab("preview");
    });

    await waitFor(() => expect(result.current.promptPreview).not.toBeNull());

    const callCount = mockedApi.post.mock.calls.length;

    act(() => {
      result.current.refreshPreview();
    });

    await waitFor(() => expect(mockedApi.post.mock.calls.length).toBeGreaterThan(callCount));
  });

  it("should handle preview API error gracefully", async () => {
    mockedApi.post.mockRejectedValue(new Error("API Error"));

    const { result } = renderHook(
      () => useStrategyStudio({ autoPreview: true }),
      { wrapper: createWrapper() }
    );

    act(() => {
      result.current.setActiveTab("preview");
    });

    await waitFor(() => {
      // Should not crash, preview should be null
      expect(result.current.promptPreview).toBeNull();
    });
  });
});

describe("useStrategyStudio - isValid computation", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update isValid when errors change", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isValid).toBe(true);

    act(() => {
      result.current.validate();
    });

    // Should be invalid because name is empty
    expect(result.current.isValid).toBe(false);

    act(() => {
      result.current.updateBasicInfo({ name: "Valid Name" });
    });

    act(() => {
      result.current.validate();
    });

    expect(result.current.isValid).toBe(true);
  });
});

describe("useStrategyStudio - setConfig", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("should update config using setConfig with object", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.setConfig({
        ...result.current.config,
        name: "New Name",
        tradingMode: "aggressive",
      });
    });

    expect(result.current.config.name).toBe("New Name");
    expect(result.current.config.tradingMode).toBe("aggressive");
  });

  it("should update config using setConfig with function", () => {
    const { result } = renderHook(() => useStrategyStudio(), {
      wrapper: createWrapper(),
    });

    act(() => {
      result.current.setConfig((prev) => ({
        ...prev,
        name: "Function Name",
      }));
    });

    expect(result.current.config.name).toBe("Function Name");
  });
});
