"use client";

import { useState, useCallback, SetStateAction } from "react";
import useSWR from "swr";
import {
  StrategyStudioConfig,
  StudioTab,
  PromptPreviewResponse,
  DEFAULT_STRATEGY_STUDIO_CONFIG,
  TradingMode,
  Timeframe,
  IndicatorSettings,
  RiskControlsConfig,
  PromptSections,
  ConsensusMode,
  RiskProfile,
  TimeHorizon,
  getStrategyPreset,
} from "@/types";
import { api } from "@/lib/api";

interface UseStrategyStudioOptions {
  initialConfig?: Partial<StrategyStudioConfig>;
  autoPreview?: boolean;
}

interface UseStrategyStudioReturn {
  // Config state
  config: StrategyStudioConfig;
  setConfig: (config: SetStateAction<StrategyStudioConfig>) => void;

  // Tab state
  activeTab: StudioTab;
  setActiveTab: (tab: StudioTab) => void;

  // Preset helpers
  applyPreset: (riskProfile: RiskProfile, timeHorizon: TimeHorizon) => void;

  // Update helpers
  updateBasicInfo: (updates: Partial<Pick<StrategyStudioConfig, "name" | "description" | "accountId" | "aiModel">>) => void;
  updateTradingConfig: (updates: Partial<Pick<StrategyStudioConfig, "tradingMode" | "executionIntervalMinutes" | "autoExecute">>) => void;
  updateSymbols: (symbols: string[]) => void;
  updateTimeframes: (timeframes: Timeframe[]) => void;
  updateIndicators: (indicators: IndicatorSettings) => void;
  updateRiskControls: (controls: RiskControlsConfig) => void;
  updatePromptSections: (sections: PromptSections) => void;
  updateCustomPrompt: (prompt: string) => void;

  // Preview
  promptPreview: PromptPreviewResponse | null;
  isPreviewLoading: boolean;
  refreshPreview: () => void;

  // Validation
  errors: Record<string, string>;
  validate: () => boolean;
  isValid: boolean;

  // Reset
  reset: () => void;

  // Convert to API format
  toApiFormat: () => Record<string, unknown>;
}

// Convert frontend config to backend API format
function configToApiFormat(config: StrategyStudioConfig): Record<string, unknown> {
  return {
    name: config.name,
    description: config.description,
    prompt: config.customPrompt,
    trading_mode: config.tradingMode,
    account_id: config.accountId || null,
    ai_model: config.aiModel,
    config: {
      language: config.language,
      symbols: config.symbols,
      timeframes: config.timeframes,
      indicators: {
        ema_periods: config.indicators.ema.enabled ? config.indicators.ema.periods : [],
        rsi_period: config.indicators.rsi.enabled ? config.indicators.rsi.period : 0,
        macd_fast: config.indicators.macd.enabled ? config.indicators.macd.fast : 0,
        macd_slow: config.indicators.macd.enabled ? config.indicators.macd.slow : 0,
        macd_signal: config.indicators.macd.enabled ? config.indicators.macd.signal : 0,
        atr_period: config.indicators.atr.enabled ? config.indicators.atr.period : 0,
      },
      risk_controls: {
        max_leverage: config.riskControls.maxLeverage,
        max_position_ratio: config.riskControls.maxPositionRatio,
        max_total_exposure: config.riskControls.maxTotalExposure,
        min_risk_reward_ratio: config.riskControls.minRiskRewardRatio,
        max_drawdown_percent: config.riskControls.maxDrawdownPercent,
        min_confidence: config.riskControls.minConfidence,
      },
      prompt_mode: config.promptMode || "simple",
      prompt_sections: {
        role_definition: config.promptSections.roleDefinition,
        trading_frequency: config.promptSections.tradingFrequency,
        entry_standards: config.promptSections.entryStandards,
        decision_process: config.promptSections.decisionProcess,
      },
      advanced_prompt: config.advancedPrompt || "",
      execution_interval_minutes: config.executionIntervalMinutes,
      auto_execute: config.autoExecute,
      // Debate configuration
      debate_enabled: config.debateEnabled,
      debate_models: config.debateModels,
      debate_consensus_mode: config.debateConsensusMode,
      debate_min_participants: config.debateMinParticipants,
    },
  };
}

// Convert API response to frontend config
export function apiResponseToConfig(response: Record<string, unknown>): Partial<StrategyStudioConfig> {
  const config = response.config as Record<string, unknown> || {};
  const riskControls = config.risk_controls as Record<string, number> || {};
  const promptSections = config.prompt_sections as Record<string, string> || {};
  const indicators = config.indicators as Record<string, unknown> || {};

  return {
    name: response.name as string || "",
    description: response.description as string || "",
    accountId: response.account_id as string || "",
    aiModel: response.ai_model as string || "",
    tradingMode: (response.trading_mode as TradingMode) || "conservative",
    language: (config.language as string) || "en",
    symbols: (config.symbols as string[]) || ["BTC", "ETH"],
    timeframes: (config.timeframes as Timeframe[]) || ["15m", "1h", "4h"],
    executionIntervalMinutes: (config.execution_interval_minutes as number) || 30,
    autoExecute: (config.auto_execute as boolean) ?? true,
    promptMode: (config.prompt_mode as "simple" | "advanced") || "simple",
    customPrompt: response.prompt as string || "",
    advancedPrompt: (config.advanced_prompt as string) || "",
    indicators: {
      ema: {
        enabled: Array.isArray(indicators.ema_periods) && (indicators.ema_periods as number[]).length > 0,
        periods: (indicators.ema_periods as number[]) || [9, 21, 55],
      },
      rsi: {
        enabled: (indicators.rsi_period as number) > 0,
        period: (indicators.rsi_period as number) || 14,
      },
      macd: {
        enabled: (indicators.macd_fast as number) > 0,
        fast: (indicators.macd_fast as number) || 12,
        slow: (indicators.macd_slow as number) || 26,
        signal: (indicators.macd_signal as number) || 9,
      },
      atr: {
        enabled: (indicators.atr_period as number) > 0,
        period: (indicators.atr_period as number) || 14,
      },
    },
    riskControls: {
      maxLeverage: riskControls.max_leverage || 5,
      maxPositionRatio: riskControls.max_position_ratio || 0.2,
      maxTotalExposure: riskControls.max_total_exposure || 0.8,
      minRiskRewardRatio: riskControls.min_risk_reward_ratio || 2.0,
      maxDrawdownPercent: riskControls.max_drawdown_percent || 0.1,
      minConfidence: riskControls.min_confidence || 60,
    },
    promptSections: {
      roleDefinition: promptSections.role_definition || "",
      tradingFrequency: promptSections.trading_frequency || "",
      entryStandards: promptSections.entry_standards || "",
      decisionProcess: promptSections.decision_process || "",
    },
    // Debate configuration
    debateEnabled: (config.debate_enabled as boolean) ?? false,
    debateModels: (config.debate_models as string[]) || [],
    debateConsensusMode: (config.debate_consensus_mode as ConsensusMode) || "majority_vote",
    debateMinParticipants: (config.debate_min_participants as number) || 2,
  };
}

export function useStrategyStudio(
  options: UseStrategyStudioOptions = {}
): UseStrategyStudioReturn {
  const { initialConfig, autoPreview = true } = options;

  // Config state
  const [config, setConfig] = useState<StrategyStudioConfig>({
    ...DEFAULT_STRATEGY_STUDIO_CONFIG,
    ...initialConfig,
  });

  // Tab state
  const [activeTab, setActiveTab] = useState<StudioTab>("coins");

  // Errors state
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Preview fetcher
  const previewFetcher = useCallback(async () => {
    const response = await api.post<{
      system_prompt: string;
      estimated_tokens: number;
      sections: Record<string, string>;
    }>("/strategies/preview-prompt", {
      prompt: config.customPrompt,
      trading_mode: config.tradingMode,
      language: config.language,
      prompt_mode: config.promptMode || "simple",
      advanced_prompt: config.advancedPrompt || "",
      symbols: config.symbols,
      timeframes: config.timeframes,
      indicators: {
        ema_periods: config.indicators.ema.enabled ? config.indicators.ema.periods : [],
        rsi_period: config.indicators.rsi.enabled ? config.indicators.rsi.period : 0,
        macd_fast: config.indicators.macd.enabled ? config.indicators.macd.fast : 0,
        macd_slow: config.indicators.macd.enabled ? config.indicators.macd.slow : 0,
        macd_signal: config.indicators.macd.enabled ? config.indicators.macd.signal : 0,
        atr_period: config.indicators.atr.enabled ? config.indicators.atr.period : 0,
      },
      risk_controls: {
        max_leverage: config.riskControls.maxLeverage,
        max_position_ratio: config.riskControls.maxPositionRatio,
        max_total_exposure: config.riskControls.maxTotalExposure,
        min_risk_reward_ratio: config.riskControls.minRiskRewardRatio,
        max_drawdown_percent: config.riskControls.maxDrawdownPercent,
        min_confidence: config.riskControls.minConfidence,
      },
      prompt_sections: {
        role_definition: config.promptSections.roleDefinition,
        trading_frequency: config.promptSections.tradingFrequency,
        entry_standards: config.promptSections.entryStandards,
        decision_process: config.promptSections.decisionProcess,
      },
    });

    return {
      systemPrompt: response.system_prompt,
      estimatedTokens: response.estimated_tokens,
      sections: {
        roleDefinition: response.sections.role_definition || "",
        tradingMode: response.sections.trading_mode || "",
        tradingFrequency: response.sections.trading_frequency || "",
        entryStandards: response.sections.entry_standards || "",
        decisionProcess: response.sections.decision_process || "",
        customPrompt: response.sections.custom_prompt || "",
      },
    } as PromptPreviewResponse;
  }, [config]);

  // Preview SWR - only fetch when on preview tab
  const {
    data: promptPreview,
    isLoading: isPreviewLoading,
    mutate: refreshPreview,
  } = useSWR(
    autoPreview && activeTab === "preview" ? ["preview-prompt", config] : null,
    previewFetcher,
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    }
  );

  // Apply a strategy preset (riskProfile + timeHorizon)
  const applyPreset = useCallback(
    (riskProfile: RiskProfile, timeHorizon: TimeHorizon) => {
      const preset = getStrategyPreset(riskProfile, timeHorizon);
      if (!preset) return;
      const { values } = preset;
      setConfig((prev) => ({
        ...prev,
        tradingMode: values.tradingMode,
        symbols: values.symbols,
        timeframes: values.timeframes,
        executionIntervalMinutes: values.executionIntervalMinutes,
        indicators: values.indicators,
        riskControls: values.riskControls,
      }));
    },
    []
  );

  // Update helpers
  const updateBasicInfo = useCallback(
    (updates: Partial<Pick<StrategyStudioConfig, "name" | "description" | "accountId" | "aiModel">>) => {
      setConfig((prev) => ({ ...prev, ...updates }));
    },
    []
  );

  const updateTradingConfig = useCallback(
    (updates: Partial<Pick<StrategyStudioConfig, "tradingMode" | "executionIntervalMinutes" | "autoExecute">>) => {
      setConfig((prev) => ({ ...prev, ...updates }));
    },
    []
  );

  const updateSymbols = useCallback((symbols: string[]) => {
    setConfig((prev) => ({ ...prev, symbols }));
  }, []);

  const updateTimeframes = useCallback((timeframes: Timeframe[]) => {
    setConfig((prev) => ({ ...prev, timeframes }));
  }, []);

  const updateIndicators = useCallback((indicators: IndicatorSettings) => {
    setConfig((prev) => ({ ...prev, indicators }));
  }, []);

  const updateRiskControls = useCallback((riskControls: RiskControlsConfig) => {
    setConfig((prev) => ({ ...prev, riskControls }));
  }, []);

  const updatePromptSections = useCallback((promptSections: PromptSections) => {
    setConfig((prev) => ({ ...prev, promptSections }));
  }, []);

  const updateCustomPrompt = useCallback((customPrompt: string) => {
    setConfig((prev) => ({ ...prev, customPrompt }));
  }, []);

  // Validation
  const validate = useCallback((): boolean => {
    const newErrors: Record<string, string> = {};

    if (!config.name.trim()) {
      newErrors.name = "Name is required";
    }

    if (config.symbols.length === 0) {
      newErrors.symbols = "At least one symbol is required";
    }

    if (config.timeframes.length === 0) {
      newErrors.timeframes = "At least one timeframe is required";
    }

    // Debate validation
    if (config.debateEnabled && config.debateModels.length < 2) {
      newErrors.debate = "At least 2 models required for debate mode";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [config]);

  // Reset
  const reset = useCallback(() => {
    setConfig({ ...DEFAULT_STRATEGY_STUDIO_CONFIG, ...initialConfig });
    setActiveTab("coins");
    setErrors({});
  }, [initialConfig]);

  // Convert to API format
  const toApiFormat = useCallback(() => {
    return configToApiFormat(config);
  }, [config]);

  return {
    config,
    setConfig,
    activeTab,
    setActiveTab,
    applyPreset,
    updateBasicInfo,
    updateTradingConfig,
    updateSymbols,
    updateTimeframes,
    updateIndicators,
    updateRiskControls,
    updatePromptSections,
    updateCustomPrompt,
    promptPreview: promptPreview || null,
    isPreviewLoading,
    refreshPreview: () => refreshPreview(),
    errors,
    validate,
    isValid: Object.keys(errors).length === 0,
    reset,
    toApiFormat,
  };
}
