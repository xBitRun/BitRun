/**
 * API Endpoints
 *
 * Type-safe API endpoint definitions for all backend routes.
 */

import { api, ApiError } from './client';
import type {
  StrategyStatus,
  TradingMode,
  ExchangeType,
  DashboardStats,
} from '@/types';

// ==================== Auth Error Types ====================

/**
 * Structured auth error from backend.
 * Contains error code for frontend i18n lookup.
 */
export interface AuthApiError {
  code: string;
  remaining_attempts?: number;
  remaining_minutes?: number;
}

// ==================== Auth ====================

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;  // Backend uses 'name', not 'username'
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user?: UserResponse;  // Inline user info from login to avoid extra /me call
}

// Login uses OAuth2 form data format, custom fetch needed
async function loginWithForm(data: LoginRequest): Promise<TokenResponse> {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  const formData = new URLSearchParams();
  formData.append('username', data.email);  // OAuth2 uses 'username' field
  formData.append('password', data.password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    
    // Backend returns structured error: { code: "AUTH_...", remaining_attempts?: number, ... }
    const detail = errorData.detail;
    if (detail && typeof detail === 'object' && detail.code) {
      const authError: AuthApiError = {
        code: detail.code,
        remaining_attempts: detail.remaining_attempts,
        remaining_minutes: detail.remaining_minutes,
      };
      throw new ApiError(
        detail.code,
        response.status,
        detail.code,
        authError as unknown as Record<string, unknown>
      );
    }
    
    // Fallback for unexpected error format
    const message = typeof detail === 'string' ? detail : 'Login failed';
    throw new ApiError(message, response.status, 'LOGIN_FAILED');
  }

  return response.json();
}

export interface ProfileUpdateRequest {
  name?: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export const authApi = {
  login: (data: LoginRequest) => loginWithForm(data),

  register: (data: RegisterRequest) =>
    api.post<UserResponse>('/auth/register', data, { skipAuth: true }),

  logout: () =>
    api.post<{ message: string }>('/auth/logout'),

  me: () =>
    api.get<UserResponse>('/auth/me'),

  refresh: (refreshToken: string) =>
    api.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }, { skipAuth: true }),

  updateProfile: (data: ProfileUpdateRequest) =>
    api.put<UserResponse>('/auth/profile', data),

  changePassword: (data: ChangePasswordRequest) =>
    api.post<{ message: string }>('/auth/change-password', data),
};

// ==================== Strategies ====================

export interface CreateStrategyRequest {
  name: string;
  description?: string;
  prompt: string;
  trading_mode: TradingMode;
  symbols: string[];
  account_id: string;
  ai_model?: string; // AI model in format 'provider:model_id'
  config?: Record<string, unknown>;
  // Capital allocation (pick one)
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
}

export interface UpdateStrategyRequest {
  name?: string;
  description?: string;
  prompt?: string;
  trading_mode?: TradingMode;
  symbols?: string[];
  ai_model?: string; // AI model in format 'provider:model_id'
  config?: Record<string, unknown>;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
}

export interface StrategyResponse {
  id: string;
  name: string;
  description: string;
  prompt: string;
  trading_mode: TradingMode;
  status: StrategyStatus;
  error_message?: string | null;
  account_id?: string | null;
  ai_model?: string | null; // AI model in format 'provider:model_id'
  config: Record<string, unknown>;
  // Capital allocation
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
  // Performance metrics
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  max_drawdown: number;
  // Timestamps
  created_at: string;
  updated_at: string;
  last_run_at?: string | null;
}

export const strategiesApi = {
  list: () =>
    api.get<StrategyResponse[]>('/strategies'),

  get: (id: string) =>
    api.get<StrategyResponse>(`/strategies/${id}`),

  create: (data: CreateStrategyRequest) =>
    api.post<StrategyResponse>('/strategies', data),

  update: (id: string, data: UpdateStrategyRequest) =>
    api.patch<StrategyResponse>(`/strategies/${id}`, data),

  delete: (id: string) =>
    api.delete<void>(`/strategies/${id}`),

  updateStatus: (id: string, status: StrategyStatus, close_positions?: boolean) =>
    api.post<StrategyResponse>(`/strategies/${id}/status`, { status, close_positions }),

  activate: (id: string) =>
    api.post<StrategyResponse>(`/strategies/${id}/status`, { status: 'active' }),

  pause: (id: string) =>
    api.post<StrategyResponse>(`/strategies/${id}/status`, { status: 'paused' }),

  stop: (id: string, close_positions?: boolean) =>
    api.post<StrategyResponse>(`/strategies/${id}/status`, { status: 'stopped', close_positions }),

  previewPrompt: (data: Record<string, unknown>) =>
    api.post<{
      system_prompt: string;
      estimated_tokens: number;
      sections: Record<string, string>;
    }>('/strategies/preview-prompt', data),
};

// ==================== Quant Strategies ====================

export interface CreateQuantStrategyRequest {
  name: string;
  description?: string;
  strategy_type: string;
  symbol: string;
  account_id?: string;
  config: Record<string, unknown>;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
}

export interface UpdateQuantStrategyRequest {
  name?: string;
  description?: string;
  symbol?: string;
  config?: Record<string, unknown>;
  account_id?: string;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
}

export interface QuantStrategyApiResponse {
  id: string;
  name: string;
  description: string;
  strategy_type: string;
  symbol: string;
  config: Record<string, unknown>;
  runtime_state: Record<string, unknown>;
  status: StrategyStatus;
  error_message?: string | null;
  account_id?: string | null;
  // Capital allocation
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
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

export const quantStrategiesApi = {
  list: (params?: { status_filter?: string; strategy_type?: string }) => {
    const searchParams = new URLSearchParams();
    if (params?.status_filter) searchParams.set('status_filter', params.status_filter);
    if (params?.strategy_type) searchParams.set('strategy_type', params.strategy_type);
    const query = searchParams.toString();
    return api.get<QuantStrategyApiResponse[]>(`/quant-strategies${query ? `?${query}` : ''}`);
  },

  get: (id: string) =>
    api.get<QuantStrategyApiResponse>(`/quant-strategies/${id}`),

  create: (data: CreateQuantStrategyRequest) =>
    api.post<QuantStrategyApiResponse>('/quant-strategies', data),

  update: (id: string, data: UpdateQuantStrategyRequest) =>
    api.patch<QuantStrategyApiResponse>(`/quant-strategies/${id}`, data),

  delete: (id: string) =>
    api.delete<void>(`/quant-strategies/${id}`),

  updateStatus: (id: string, status: StrategyStatus, close_positions?: boolean) =>
    api.post<QuantStrategyApiResponse>(`/quant-strategies/${id}/status`, { status, close_positions }),
};

// ==================== Workers ====================

export interface TriggerExecutionResponse {
  message: string;
  success: boolean;
  job_id?: string;
  decision_id?: string;
}

export const workersApi = {
  triggerExecution: (strategyId: string) =>
    api.post<TriggerExecutionResponse>(`/workers/${strategyId}/trigger`),
};

// ==================== Accounts ====================

export interface CreateAccountRequest {
  name: string;
  exchange: ExchangeType;
  is_testnet: boolean;
  api_key?: string;
  api_secret?: string;
  private_key?: string;  // For Hyperliquid (direct private key)
  mnemonic?: string;     // For Hyperliquid (12/24 word seed phrase)
  passphrase?: string;   // For exchanges that require it
}

export interface AccountResponse {
  id: string;
  name: string;
  exchange: ExchangeType;
  is_testnet: boolean;
  is_connected: boolean;
  connection_error?: string | null;
  created_at: string;
  last_synced_at?: string | null;  // Optional: last time balance was fetched
  // Credential status flags
  has_api_key: boolean;
  has_api_secret: boolean;
  has_private_key: boolean;
  has_passphrase: boolean;
}

export interface AccountBalanceResponse {
  account_id: string;
  equity: number;
  available_balance: number;
  total_margin_used: number;
  unrealized_pnl: number;
  positions: Array<{
    symbol: string;
    side: 'long' | 'short';
    size: number;
    size_usd: number;
    entry_price: number;
    mark_price: number;
    leverage: number;
    unrealized_pnl: number;
    unrealized_pnl_percent: number;
    liquidation_price?: number;
  }>;
}

export const accountsApi = {
  list: () =>
    api.get<AccountResponse[]>('/accounts'),

  get: (id: string) =>
    api.get<AccountResponse>(`/accounts/${id}`),

  create: (data: CreateAccountRequest) =>
    api.post<AccountResponse>('/accounts', data),

  update: (id: string, data: Partial<CreateAccountRequest>) =>
    api.patch<AccountResponse>(`/accounts/${id}`, data),

  delete: (id: string) =>
    api.delete<void>(`/accounts/${id}`),

  testConnection: (id: string) =>
    api.post<{ success: boolean; message: string }>(`/accounts/${id}/test`),

  getBalance: (id: string) =>
    api.get<AccountBalanceResponse>(`/accounts/${id}/balance`),

  getPositions: (id: string) =>
    api.get<AccountBalanceResponse['positions']>(`/accounts/${id}/positions`),
};

// ==================== Decisions ====================

export interface MarketSnapshotItem {
  symbol: string;
  exchange_name: string;
  current: {
    mid_price: number;
    bid_price: number;
    ask_price: number;
    volume_24h: number;
    funding_rate: number | null;
  };
  indicators: Record<string, {
    ema: Record<string, number>;
    rsi: number | null;
    rsi_signal: string;
    macd: { macd: number; signal: number; histogram: number };
    macd_signal: string;
    atr: number | null;
    bollinger: { upper: number; middle: number; lower: number };
    ema_trend: string;
  }>;
  klines: Record<string, Array<{
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>>;
  funding_history: Array<{ timestamp: string; rate: number }>;
  available_timeframes: string[];
}

export interface DecisionResponse {
  id: string;
  strategy_id: string;
  timestamp: string;  // Backend uses timestamp, not created_at
  chain_of_thought: string;
  market_assessment: string;
  decisions: Array<{
    symbol: string;
    action: string;
    leverage: number;
    position_size_usd: number;
    entry_price?: number;
    stop_loss?: number;
    take_profit?: number;
    confidence: number;
    risk_usd: number;
    reasoning: string;
  }>;
  overall_confidence: number;
  executed: boolean;
  execution_results: unknown[];  // Backend uses execution_results (array)
  ai_model: string;
  tokens_used: number;
  latency_ms: number;
  raw_response?: string | null;
  market_snapshot?: MarketSnapshotItem[] | null;
  account_snapshot?: AccountSnapshotItem | null;
}

export interface AccountSnapshotItem {
  equity: number;
  available_balance: number;
  total_margin_used: number;
  unrealized_pnl: number;
  margin_usage_percent: number;
  position_count: number;
  positions: Array<{
    symbol: string;
    side: 'long' | 'short';
    size: number;
    size_usd: number;
    entry_price: number;
    mark_price: number;
    leverage: number;
    unrealized_pnl: number;
    unrealized_pnl_percent: number;
    liquidation_price?: number | null;
  }>;
}

export interface PaginatedDecisionResponse {
  items: DecisionResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface DecisionStatsResponse {
  total_decisions: number;
  executed_decisions: number;
  average_confidence: number;
  average_latency_ms: number;
  total_tokens: number;
  action_counts: Record<string, number>;
}

export const decisionsApi = {
  listRecent: (limit: number = 20) =>
    api.get<DecisionResponse[]>('/decisions/recent', { params: { limit } }),

  listByStrategy: (strategyId: string, limit: number = 10, offset: number = 0, executionFilter: string = "all", action?: string) =>
    api.get<PaginatedDecisionResponse>(`/decisions/strategy/${strategyId}`, {
      params: { limit, offset, execution_filter: executionFilter, ...(action ? { action } : {}) }
    }),

  get: (id: string) =>
    api.get<DecisionResponse>(`/decisions/${id}`),

  getStats: (strategyId: string) =>
    api.get<DecisionStatsResponse>(`/decisions/strategy/${strategyId}/stats`),
};

// ==================== Backtest ====================

export type BacktestExchange = "binance" | "bybit" | "okx" | "hyperliquid";

export interface BacktestRequest {
  strategy_id: string;
  start_date: string;
  end_date: string;
  initial_balance: number;
  symbols?: string[];
  use_ai?: boolean;
  timeframe?: string;
  exchange?: BacktestExchange;
}

export interface QuickBacktestRequest {
  symbols: string[];
  start_date: string;
  end_date: string;
  initial_balance: number;
  max_leverage?: number;
  max_position_ratio?: number;
  timeframe?: string;
  exchange?: BacktestExchange;
}

export interface TradeRecord {
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  exit_price: number;
  leverage: number;
  pnl: number;
  pnl_percent: number;
  opened_at: string;
  closed_at: string;
  duration_minutes: number;
  exit_reason: string;
}

export interface SideStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  gross_profit: number;
  gross_loss: number;
  average_win: number;
  average_loss: number;
}

export interface TradeStatistics {
  average_win: number;
  average_loss: number;
  largest_win: number;
  largest_loss: number;
  gross_profit: number;
  gross_loss: number;
  avg_holding_hours: number;
  max_consecutive_wins: number;
  max_consecutive_losses: number;
  expectancy: number;
  recovery_factor?: number;
  sortino_ratio?: number;
  calmar_ratio?: number;
  long_stats: SideStats;
  short_stats: SideStats;
}

export interface MonthlyReturn {
  month: string;
  return_percent: number;
}

export interface SymbolBreakdown {
  symbol: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  total_pnl: number;
  average_pnl: number;
}

export interface BacktestResponse {
  strategy_name: string;
  start_date: string;
  end_date: string;
  initial_balance: number;
  final_balance: number;
  total_return_percent: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  max_drawdown_percent: number;
  sharpe_ratio?: number;
  total_fees: number;
  equity_curve: Array<{
    timestamp: string;
    equity: number;
    balance: number;
    positions: number;
  }>;
  trades: TradeRecord[];
  drawdown_curve: Array<{
    timestamp: string;
    drawdown_percent: number;
  }>;
  monthly_returns: MonthlyReturn[];
  trade_statistics?: TradeStatistics;
  symbol_breakdown: SymbolBreakdown[];
  analysis?: {
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
  };
}

export const backtestApi = {
  run: (data: BacktestRequest) =>
    api.post<BacktestResponse>('/backtest/run', data),

  quick: (data: QuickBacktestRequest) =>
    api.post<BacktestResponse>('/backtest/quick', data),

  getSymbols: (exchange: string = 'binance') =>
    api.get<{ symbols: Array<{ symbol: string; full_symbol: string }> }>('/backtest/symbols', {
      params: { exchange },
    }),
};

// ==================== Dashboard ====================

export interface DashboardStatsResponse {
  total_equity: number;
  available_balance: number;
  unrealized_pnl: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  active_strategies: number;
  total_strategies: number;
  open_positions: number;
  positions: Array<{
    symbol: string;
    side: string;
    size: number;
    size_usd: number;
    entry_price: number;
    mark_price: number;
    leverage: number;
    unrealized_pnl: number;
    unrealized_pnl_percent: number;
    liquidation_price?: number | null;
    account_name: string;
    exchange: string;
  }>;
  today_decisions: number;
  today_executed_decisions: number;
  accounts_connected: number;
  accounts_total: number;
}

export interface ActivityItem {
  id: string;
  type: 'decision' | 'trade' | 'strategy_status' | 'system';
  timestamp: string;
  title: string;
  description: string;
  data?: Record<string, unknown>;
  status?: 'success' | 'error' | 'info';
}

export interface ActivityFeedResponse {
  items: ActivityItem[];
  total: number;
  has_more: boolean;
}

export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    try {
      // Try to fetch from the new backend endpoint
      const response = await api.get<DashboardStatsResponse>('/dashboard/stats');

      return {
        totalEquity: response.total_equity,
        dailyPnl: response.daily_pnl,
        dailyPnlPercent: response.daily_pnl_percent,
        activeStrategies: response.active_strategies,
        openPositions: response.open_positions,
        todayTrades: response.today_executed_decisions,
      };
    } catch (_error) {
      // Fallback to local aggregation if backend endpoint fails
      const [accounts, strategies] = await Promise.all([
        accountsApi.list(),
        strategiesApi.list(),
      ]);

      const activeStrategies = strategies.filter(s => s.status === 'active').length;

      return {
        totalEquity: 0,
        dailyPnl: 0,
        dailyPnlPercent: 0,
        activeStrategies,
        openPositions: 0,
        todayTrades: 0,
      };
    }
  },

  // Direct access to the full stats response
  getFullStats: () => api.get<DashboardStatsResponse>('/dashboard/stats'),

  // Get activity feed
  getActivity: (limit: number = 20, offset: number = 0) =>
    api.get<ActivityFeedResponse>('/dashboard/activity', { params: { limit, offset } }),
};

// ==================== Health ====================

export interface HealthResponse {
  status: 'healthy' | 'degraded';
  version: string;
  environment: string;
  components?: {
    redis: { status: string };
    database: { status: string };
  };
}

export const healthApi = {
  check: () =>
    api.get<HealthResponse>('/health', { skipAuth: true }),

  detailed: () =>
    api.get<HealthResponse>('/health/detailed'),
};

// ==================== AI Models ====================

export interface AIModelInfoResponse {
  id: string; // Full ID (provider:model_id)
  provider: string;
  name: string;
  description: string;
  context_window: number;
  max_output_tokens: number;
  supports_json_mode: boolean;
  supports_vision: boolean;
  cost_per_1k_input: number;
  cost_per_1k_output: number;
}

export interface AIProviderResponse {
  id: string;
  name: string;
  configured: boolean;
}

export interface TestModelRequest {
  model_id: string;
  api_key?: string;
}

export const modelsApi = {
  listProviders: () =>
    api.get<AIProviderResponse[]>('/models/providers'),

  list: (provider?: string) =>
    api.get<AIModelInfoResponse[]>('/models', { params: provider ? { provider } : {} }),

  get: (modelId: string) =>
    api.get<AIModelInfoResponse>(`/models/${encodeURIComponent(modelId)}`),

  test: (data: TestModelRequest) =>
    api.post<{
      model_id: string;
      success: boolean;
      message: string;
      error_code?: string;
    }>('/models/test', data),
};

// ==================== AI Provider Configs ====================

export interface PresetProviderInfo {
  id: string;
  name: string;
  base_url: string;
  api_format: string;
  website_url: string;
}

export interface ProviderConfigResponse {
  id: string;
  provider_type: string;
  name: string;
  note: string | null;
  website_url: string | null;
  base_url: string | null;
  api_format: string;
  is_enabled: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateProviderRequest {
  provider_type: string;
  name: string;
  note?: string;
  website_url?: string;
  api_key: string;
  base_url?: string;
  api_format?: string;
}

export interface UpdateProviderRequest {
  name?: string;
  note?: string;
  website_url?: string;
  api_key?: string;
  base_url?: string;
  api_format?: string;
  is_enabled?: boolean;
}

export interface ApiFormatInfo {
  id: string;
  name: string;
}

// Provider model item (per-provider model config)
export interface ProviderModelItem {
  id: string;
  name: string;
  description?: string;
  context_window?: number;
  max_output_tokens?: number;
  supports_json_mode?: boolean;
  supports_vision?: boolean;
  cost_per_1k_input?: number;
  cost_per_1k_output?: number;
}

export const providersApi = {
  listPresets: () =>
    api.get<PresetProviderInfo[]>('/providers/presets'),

  listFormats: () =>
    api.get<{ formats: ApiFormatInfo[] }>('/providers/formats'),

  list: () =>
    api.get<ProviderConfigResponse[]>('/providers'),

  get: (id: string) =>
    api.get<ProviderConfigResponse>(`/providers/${id}`),

  create: (data: CreateProviderRequest) =>
    api.post<ProviderConfigResponse>('/providers', data),

  update: (id: string, data: UpdateProviderRequest) =>
    api.patch<ProviderConfigResponse>(`/providers/${id}`, data),

  delete: (id: string) =>
    api.delete<void>(`/providers/${id}`),

  test: (id: string, apiKey?: string) =>
    api.post<{ success: boolean; message: string }>(`/providers/${id}/test`, { api_key: apiKey }),

  // Per-provider model CRUD
  listModels: (providerId: string) =>
    api.get<ProviderModelItem[]>(`/providers/${providerId}/models`),

  addModel: (providerId: string, data: ProviderModelItem) =>
    api.post<ProviderModelItem>(`/providers/${providerId}/models`, data),

  replaceModels: (providerId: string, models: ProviderModelItem[]) =>
    api.put<ProviderModelItem[]>(`/providers/${providerId}/models`, { models }),

  deleteModel: (providerId: string, modelId: string) =>
    api.delete<void>(`/providers/${providerId}/models/${encodeURIComponent(modelId)}`),
};
