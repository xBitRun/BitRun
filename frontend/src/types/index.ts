// Strategy Types
export type StrategyStatus = "draft" | "active" | "paused" | "stopped" | "error" | "warning";
export type TradingMode = "aggressive" | "balanced" | "conservative";
export type ActionType = "open_long" | "open_short" | "close_long" | "close_short" | "hold" | "wait";

export interface RiskControls {
  maxLeverage: number;
  maxPositionRatio: number;
  maxTotalExposure: number;
  minRiskRewardRatio: number;
  maxDrawdownPercent: number;
}

export interface Strategy {
  id: string;
  name: string;
  prompt: string;
  tradingMode: TradingMode;
  riskControls: RiskControls;
  status: StrategyStatus;
  accountId: string;
  aiModel?: string; // AI model in format 'provider:model_id'
  // Capital allocation (pick one mode)
  allocatedCapital?: number | null; // Fixed USD amount
  allocatedCapitalPercent?: number | null; // Fraction of equity (e.g. 0.3 = 30%)
  createdAt: string;
  updatedAt: string;
  totalPnl?: number;
  winRate?: number;
}

// AI Model Types
export type AIProvider = "deepseek" | "qwen" | "zhipu" | "minimax" | "kimi" | "custom";

export interface AIModelInfo {
  id: string; // Full ID (provider:model_id)
  provider: AIProvider;
  name: string;
  description: string;
  contextWindow: number;
  maxOutputTokens: number;
  supportsJsonMode: boolean;
  supportsVision: boolean;
  costPer1kInput: number;
  costPer1kOutput: number;
}

export interface AIProviderInfo {
  id: AIProvider;
  name: string;
  configured: boolean;
}

// Decision Types
export interface TradingDecision {
  symbol: string;
  action: ActionType;
  leverage: number;
  positionSizeUsd: number;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  confidence: number;
  riskUsd: number;
  reasoning: string;
}

export interface DecisionRecord {
  id: string;
  strategyId: string;
  timestamp: string;
  chainOfThought: string;
  marketAssessment: string;
  decisions: TradingDecision[];
  overallConfidence: number;
  executed: boolean;
  executionResult?: string;
}

// Account Types
export type ExchangeType = "hyperliquid" | "binance" | "bybit" | "okx";

export interface ExchangeAccount {
  id: string;
  name: string;
  exchange: ExchangeType;
  isTestnet: boolean;
  createdAt: string;
  // Credentials are encrypted, not returned to frontend
}

// Position Types
export interface Position {
  symbol: string;
  side: "long" | "short";
  size: number;
  entryPrice: number;
  markPrice: number;
  leverage: number;
  unrealizedPnl: number;
  unrealizedPnlPercent: number;
  liquidationPrice?: number;
}

export interface AccountState {
  equity: number;
  availableBalance: number;
  totalMarginUsed: number;
  unrealizedPnl: number;
  positions: Position[];
}

// Dashboard Stats
export interface DashboardStats {
  totalEquity: number;
  dailyPnl: number;
  dailyPnlPercent: number;
  activeStrategies: number;
  openPositions: number;
  todayTrades: number;
}

// ==================== Strategy Studio Types ====================

export type Timeframe = "1m" | "5m" | "15m" | "30m" | "1h" | "4h" | "1d";

export type StudioTab = "coins" | "indicators" | "risk" | "prompt" | "debate" | "preview";

// Indicator Settings
export interface IndicatorSettings {
  ema: {
    enabled: boolean;
    periods: number[];
  };
  rsi: {
    enabled: boolean;
    period: number;
  };
  macd: {
    enabled: boolean;
    fast: number;
    slow: number;
    signal: number;
  };
  atr: {
    enabled: boolean;
    period: number;
  };
}

// Risk Controls Config (extended for Strategy Studio)
export interface RiskControlsConfig {
  maxLeverage: number;
  maxPositionRatio: number;
  maxTotalExposure: number;
  minRiskRewardRatio: number;
  maxDrawdownPercent: number;
  minConfidence: number;
}

// Prompt Sections
export interface PromptSections {
  roleDefinition: string;
  tradingFrequency: string;
  entryStandards: string;
  decisionProcess: string;
}

// Complete Strategy Studio Config
export interface StrategyStudioConfig {
  // Basic info
  name: string;
  description: string;
  accountId: string;
  aiModel: string;

  // Trading config
  tradingMode: TradingMode;
  symbols: string[];
  timeframes: Timeframe[];
  executionIntervalMinutes: number;
  autoExecute: boolean;

  // Technical indicators
  indicators: IndicatorSettings;

  // Risk controls
  riskControls: RiskControlsConfig;

  // Prompt configuration
  language: string; // Prompt language: "en" | "zh" (auto-set from locale)
  promptSections: PromptSections;
  customPrompt: string;

  // Debate configuration
  debateEnabled: boolean;
  debateModels: string[];
  debateConsensusMode: ConsensusMode;
  debateMinParticipants: number;
}

// Default values
export const DEFAULT_INDICATOR_SETTINGS: IndicatorSettings = {
  ema: { enabled: true, periods: [9, 21, 55] },
  rsi: { enabled: true, period: 14 },
  macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
  atr: { enabled: true, period: 14 },
};

export const DEFAULT_RISK_CONTROLS: RiskControlsConfig = {
  maxLeverage: 5,
  maxPositionRatio: 0.2,
  maxTotalExposure: 0.8,
  minRiskRewardRatio: 2.0,
  maxDrawdownPercent: 0.1,
  minConfidence: 60,
};

export const DEFAULT_PROMPT_SECTIONS: PromptSections = {
  roleDefinition: "",
  tradingFrequency: "",
  entryStandards: "",
  decisionProcess: "",
};

export const DEFAULT_STRATEGY_STUDIO_CONFIG: StrategyStudioConfig = {
  name: "",
  description: "",
  accountId: "",
  aiModel: "",
  tradingMode: "conservative",
  symbols: ["BTC", "ETH"],
  timeframes: ["15m", "1h", "4h"],
  executionIntervalMinutes: 30,
  autoExecute: true,
  indicators: DEFAULT_INDICATOR_SETTINGS,
  riskControls: DEFAULT_RISK_CONTROLS,
  language: "en",
  promptSections: DEFAULT_PROMPT_SECTIONS,
  customPrompt: "",
  // Debate defaults
  debateEnabled: false,
  debateModels: [],
  debateConsensusMode: "majority_vote",
  debateMinParticipants: 2,
};

// Prompt Preview Response
export interface PromptPreviewResponse {
  systemPrompt: string;
  estimatedTokens: number;
  sections: {
    roleDefinition: string;
    tradingMode: string;
    tradingFrequency: string;
    entryStandards: string;
    decisionProcess: string;
    customPrompt: string;
  };
}

// Popular trading pairs for quick selection
export const POPULAR_SYMBOLS = [
  "BTC",
  "ETH",
  "SOL",
  "BNB",
  "XRP",
  "DOGE",
  "ADA",
  "AVAX",
  "LINK",
  "DOT",
] as const;

export const TIMEFRAME_OPTIONS: { value: Timeframe; label: string }[] = [
  { value: "1m", label: "1 minute" },
  { value: "5m", label: "5 minutes" },
  { value: "15m", label: "15 minutes" },
  { value: "30m", label: "30 minutes" },
  { value: "1h", label: "1 hour" },
  { value: "4h", label: "4 hours" },
  { value: "1d", label: "1 day" },
];

export const EXECUTION_INTERVAL_OPTIONS = [
  { value: 15, label: "15 minutes" },
  { value: 30, label: "30 minutes" },
  { value: 60, label: "1 hour" },
  { value: 120, label: "2 hours" },
  { value: 240, label: "4 hours" },
  { value: 480, label: "8 hours" },
  { value: 1440, label: "24 hours" },
];

// ==================== Quant Strategy Types ====================

export type QuantStrategyType = "grid" | "dca" | "rsi";

export interface GridConfig {
  upper_price: number;
  lower_price: number;
  grid_count: number;
  total_investment: number;
  leverage: number;
}

export interface DCAConfig {
  order_amount: number;
  interval_minutes: number;
  take_profit_percent: number;
  total_budget: number;
  max_orders: number;
}

export interface RSIConfig {
  rsi_period: number;
  overbought_threshold: number;
  oversold_threshold: number;
  order_amount: number;
  timeframe: string;
  leverage: number;
}

export type QuantStrategyConfig = GridConfig | DCAConfig | RSIConfig;

export interface QuantStrategyResponse {
  id: string;
  name: string;
  description: string;
  strategy_type: QuantStrategyType;
  symbol: string;
  config: Record<string, unknown>;
  runtime_state: Record<string, unknown>;
  status: StrategyStatus;
  error_message?: string | null;
  account_id?: string | null;
  // Capital allocation (pick one mode)
  allocatedCapital?: number | null;
  allocatedCapitalPercent?: number | null;
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  max_drawdown: number;
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
}

// ==================== Strategy Preset Types ====================

export type RiskProfile = "conservative" | "balanced" | "aggressive";
export type TimeHorizon = "scalp" | "swing" | "position";

export interface StrategyPresetValues {
  tradingMode: TradingMode;
  symbols: string[];
  timeframes: Timeframe[];
  executionIntervalMinutes: number;
  indicators: IndicatorSettings;
  riskControls: RiskControlsConfig;
}

export interface StrategyPreset {
  riskProfile: RiskProfile;
  timeHorizon: TimeHorizon;
  values: StrategyPresetValues;
}

// Helper to build a preset key
export function presetKey(riskProfile: RiskProfile, timeHorizon: TimeHorizon): string {
  return `${riskProfile}_${timeHorizon}`;
}

// 3x3 preset matrix: RiskProfile x TimeHorizon = 9 presets
export const STRATEGY_PRESETS: Record<string, StrategyPreset> = {
  // ── Conservative ──────────────────────────────────────
  conservative_scalp: {
    riskProfile: "conservative",
    timeHorizon: "scalp",
    values: {
      tradingMode: "conservative",
      symbols: ["BTC", "ETH"],
      timeframes: ["1m", "5m", "15m"],
      executionIntervalMinutes: 5,
      indicators: {
        ema: { enabled: true, periods: [5, 13, 34] },
        rsi: { enabled: true, period: 9 },
        macd: { enabled: true, fast: 8, slow: 17, signal: 9 },
        atr: { enabled: true, period: 10 },
      },
      riskControls: {
        maxLeverage: 3,
        maxPositionRatio: 0.05,
        maxTotalExposure: 0.3,
        minRiskRewardRatio: 2.0,
        maxDrawdownPercent: 0.05,
        minConfidence: 75,
      },
    },
  },
  conservative_swing: {
    riskProfile: "conservative",
    timeHorizon: "swing",
    values: {
      tradingMode: "conservative",
      symbols: ["BTC", "ETH"],
      timeframes: ["15m", "1h", "4h"],
      executionIntervalMinutes: 60,
      indicators: {
        ema: { enabled: true, periods: [9, 21, 55] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 3,
        maxPositionRatio: 0.1,
        maxTotalExposure: 0.5,
        minRiskRewardRatio: 2.5,
        maxDrawdownPercent: 0.08,
        minConfidence: 75,
      },
    },
  },
  conservative_position: {
    riskProfile: "conservative",
    timeHorizon: "position",
    values: {
      tradingMode: "conservative",
      symbols: ["BTC", "ETH"],
      timeframes: ["4h", "1d"],
      executionIntervalMinutes: 240,
      indicators: {
        ema: { enabled: true, periods: [21, 55, 200] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 2,
        maxPositionRatio: 0.1,
        maxTotalExposure: 0.4,
        minRiskRewardRatio: 3.0,
        maxDrawdownPercent: 0.08,
        minConfidence: 80,
      },
    },
  },

  // ── Balanced ──────────────────────────────────────────
  balanced_scalp: {
    riskProfile: "balanced",
    timeHorizon: "scalp",
    values: {
      tradingMode: "balanced",
      symbols: ["BTC", "ETH", "SOL"],
      timeframes: ["1m", "5m", "15m"],
      executionIntervalMinutes: 5,
      indicators: {
        ema: { enabled: true, periods: [5, 9, 21] },
        rsi: { enabled: true, period: 7 },
        macd: { enabled: true, fast: 8, slow: 17, signal: 9 },
        atr: { enabled: true, period: 10 },
      },
      riskControls: {
        maxLeverage: 8,
        maxPositionRatio: 0.08,
        maxTotalExposure: 0.45,
        minRiskRewardRatio: 1.5,
        maxDrawdownPercent: 0.1,
        minConfidence: 65,
      },
    },
  },
  balanced_swing: {
    riskProfile: "balanced",
    timeHorizon: "swing",
    values: {
      tradingMode: "balanced",
      symbols: ["BTC", "ETH", "SOL"],
      timeframes: ["15m", "1h", "4h"],
      executionIntervalMinutes: 30,
      indicators: {
        ema: { enabled: true, periods: [9, 21, 55] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 5,
        maxPositionRatio: 0.15,
        maxTotalExposure: 0.6,
        minRiskRewardRatio: 2.0,
        maxDrawdownPercent: 0.12,
        minConfidence: 65,
      },
    },
  },
  balanced_position: {
    riskProfile: "balanced",
    timeHorizon: "position",
    values: {
      tradingMode: "balanced",
      symbols: ["BTC", "ETH"],
      timeframes: ["4h", "1d"],
      executionIntervalMinutes: 240,
      indicators: {
        ema: { enabled: true, periods: [21, 55, 200] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 3,
        maxPositionRatio: 0.15,
        maxTotalExposure: 0.6,
        minRiskRewardRatio: 2.5,
        maxDrawdownPercent: 0.12,
        minConfidence: 65,
      },
    },
  },

  // ── Aggressive ────────────────────────────────────────
  aggressive_scalp: {
    riskProfile: "aggressive",
    timeHorizon: "scalp",
    values: {
      tradingMode: "aggressive",
      symbols: ["BTC", "ETH", "SOL"],
      timeframes: ["1m", "5m", "15m"],
      executionIntervalMinutes: 5,
      indicators: {
        ema: { enabled: true, periods: [5, 9, 21] },
        rsi: { enabled: true, period: 7 },
        macd: { enabled: true, fast: 8, slow: 17, signal: 9 },
        atr: { enabled: true, period: 10 },
      },
      riskControls: {
        maxLeverage: 15,
        maxPositionRatio: 0.25,
        maxTotalExposure: 0.8,
        minRiskRewardRatio: 1.5,
        maxDrawdownPercent: 0.2,
        minConfidence: 50,
      },
    },
  },
  aggressive_swing: {
    riskProfile: "aggressive",
    timeHorizon: "swing",
    values: {
      tradingMode: "aggressive",
      symbols: ["BTC", "ETH", "SOL", "BNB"],
      timeframes: ["15m", "1h", "4h"],
      executionIntervalMinutes: 15,
      indicators: {
        ema: { enabled: true, periods: [9, 21, 55] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 10,
        maxPositionRatio: 0.25,
        maxTotalExposure: 0.85,
        minRiskRewardRatio: 1.5,
        maxDrawdownPercent: 0.18,
        minConfidence: 55,
      },
    },
  },
  aggressive_position: {
    riskProfile: "aggressive",
    timeHorizon: "position",
    values: {
      tradingMode: "aggressive",
      symbols: ["BTC", "ETH", "SOL"],
      timeframes: ["4h", "1d"],
      executionIntervalMinutes: 120,
      indicators: {
        ema: { enabled: true, periods: [21, 55, 200] },
        rsi: { enabled: true, period: 14 },
        macd: { enabled: true, fast: 12, slow: 26, signal: 9 },
        atr: { enabled: true, period: 14 },
      },
      riskControls: {
        maxLeverage: 8,
        maxPositionRatio: 0.2,
        maxTotalExposure: 0.8,
        minRiskRewardRatio: 2.0,
        maxDrawdownPercent: 0.15,
        minConfidence: 55,
      },
    },
  },
};

/**
 * Look up a preset by risk profile + time horizon.
 * Returns undefined when no match (should never happen for valid inputs).
 */
export function getStrategyPreset(
  riskProfile: RiskProfile,
  timeHorizon: TimeHorizon,
): StrategyPreset | undefined {
  return STRATEGY_PRESETS[presetKey(riskProfile, timeHorizon)];
}

// ==================== Debate Types ====================

export type ConsensusMode = "majority_vote" | "highest_confidence" | "weighted_average" | "unanimous";

export interface DebateConfig {
  enabled: boolean;
  modelIds: string[];
  consensusMode: ConsensusMode;
  minParticipants: number;
}

export interface DebateParticipant {
  modelId: string;
  succeeded: boolean;
  confidence: number;
  latencyMs: number;
  tokensUsed: number;
  error?: string;
  decisions: {
    symbol: string;
    action: string;
    confidence: number;
  }[];
}

export interface DebateResultSummary {
  models: string[];
  successful: number;
  failed: number;
  agreementScore: number;
  consensusMode: ConsensusMode;
}

export interface DebateModelValidation {
  modelId: string;
  valid: boolean;
  error?: string;
}

export interface DebateValidationResponse {
  valid: boolean;
  models: DebateModelValidation[];
  message: string;
}

export const DEFAULT_DEBATE_CONFIG: DebateConfig = {
  enabled: false,
  modelIds: [],
  consensusMode: "majority_vote",
  minParticipants: 2,
};

export const CONSENSUS_MODE_OPTIONS: { value: ConsensusMode; label: string; description: string }[] = [
  {
    value: "majority_vote",
    label: "Majority Vote",
    description: "Most common action for each symbol wins",
  },
  {
    value: "highest_confidence",
    label: "Highest Confidence",
    description: "Model with highest overall confidence wins",
  },
  {
    value: "weighted_average",
    label: "Weighted Average",
    description: "Decisions weighted by confidence scores",
  },
  {
    value: "unanimous",
    label: "Unanimous",
    description: "All models must agree, otherwise hold",
  },
];
