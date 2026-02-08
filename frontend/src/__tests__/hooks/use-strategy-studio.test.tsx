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
    debateEnabled: false,
    debateModels: [],
    debateConsensusMode: "majority_vote",
    debateMinParticipants: 2,
  };

  return {
    __esModule: true,
    DEFAULT_STRATEGY_STUDIO_CONFIG,
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
    expect(result.current.config.debateEnabled).toBe(false);
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

  it("should fail validation when debate enabled with < 2 models", () => {
    const { result } = renderHook(
      () => useStrategyStudio({ initialConfig: { name: "Test", debateEnabled: true, debateModels: ["model-1"] } }),
      { wrapper: createWrapper() }
    );

    let valid: boolean;
    act(() => {
      valid = result.current.validate();
    });

    expect(valid!).toBe(false);
    expect(result.current.errors.debate).toBeDefined();
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
        debate_enabled: true,
        debate_models: ["model-a", "model-b"],
        debate_consensus_mode: "weighted_average",
        debate_min_participants: 3,
      },
    };

    const config = apiResponseToConfig(response);

    expect(config.name).toBe("API Strategy");
    expect(config.aiModel).toBe("openai:gpt-4o");
    expect(config.tradingMode).toBe("aggressive");
    expect(config.language).toBe("zh");
    expect(config.symbols).toEqual(["BTC", "SOL"]);
    expect(config.autoExecute).toBe(false);
    expect(config.debateEnabled).toBe(true);
    expect(config.debateModels).toEqual(["model-a", "model-b"]);
    expect(config.riskControls?.maxLeverage).toBe(10);
    expect(config.promptSections?.roleDefinition).toBe("You are a trader");
  });

  it("should use defaults for missing fields", () => {
    const config = apiResponseToConfig({});

    expect(config.name).toBe("");
    expect(config.symbols).toEqual(["BTC", "ETH"]);
    expect(config.tradingMode).toBe("conservative");
    expect(config.debateEnabled).toBe(false);
    expect(config.riskControls?.maxLeverage).toBe(5);
  });
});
