/**
 * API Endpoints
 *
 * Type-safe API endpoint definitions for all backend routes.
 */

import { api, ApiError } from "./client";
import type {
  StrategyType,
  StrategyVisibility,
  AgentStatus,
  ExecutionMode,
  TradingMode,
  ExchangeType,
  DashboardStats,
} from "@/types";

// Backward compat
type StrategyStatus = AgentStatus;

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
  name: string; // Backend uses 'name', not 'username'
  invite_code: string; // Required for registration
}

export type UserRole = "user" | "channel_admin" | "platform_admin";

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  is_active: boolean;
  role: UserRole;
  channel_id?: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user?: UserResponse; // Inline user info from login to avoid extra /me call
}

// Login uses OAuth2 form data format, custom fetch needed
async function loginWithForm(data: LoginRequest): Promise<TokenResponse> {
  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const formData = new URLSearchParams();
  formData.append("username", data.email); // OAuth2 uses 'username' field
  formData.append("password", data.password);

  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));

    // Backend returns structured error: { code: "AUTH_...", remaining_attempts?: number, ... }
    const detail = errorData.detail;
    if (detail && typeof detail === "object" && detail.code) {
      const authError: AuthApiError = {
        code: detail.code,
        remaining_attempts: detail.remaining_attempts,
        remaining_minutes: detail.remaining_minutes,
      };
      throw new ApiError(
        detail.code,
        response.status,
        detail.code,
        authError as unknown as Record<string, unknown>,
      );
    }

    // Fallback for unexpected error format
    const message = typeof detail === "string" ? detail : "Login failed";
    throw new ApiError(message, response.status, "LOGIN_FAILED");
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
    api.post<UserResponse>("/auth/register", data, { skipAuth: true }),

  logout: () => api.post<{ message: string }>("/auth/logout"),

  me: () => api.get<UserResponse>("/auth/me"),

  refresh: (refreshToken: string) =>
    api.post<TokenResponse>(
      "/auth/refresh",
      { refresh_token: refreshToken },
      { skipAuth: true },
    ),

  updateProfile: (data: ProfileUpdateRequest) =>
    api.put<UserResponse>("/auth/profile", data),

  changePassword: (data: ChangePasswordRequest) =>
    api.post<{ message: string }>("/auth/change-password", data),
};

// ==================== Strategies (v2 - unified logic templates) ====================

export interface CreateStrategyRequest {
  type: StrategyType;
  name: string;
  description?: string;
  symbols: string[];
  config: Record<string, unknown>;
  visibility?: StrategyVisibility;
  category?: string;
  tags?: string[];
}

export interface UpdateStrategyRequest {
  name?: string;
  description?: string;
  symbols?: string[];
  config?: Record<string, unknown>;
  visibility?: StrategyVisibility;
  category?: string;
  tags?: string[];
}

export interface StrategyResponse {
  id: string;
  user_id: string;
  type: StrategyType;
  name: string;
  description: string;
  symbols: string[];
  config: Record<string, unknown>;

  // Marketplace
  visibility: StrategyVisibility;
  category?: string | null;
  tags: string[];
  forked_from?: string | null;
  fork_count: number;
  author_name?: string | null;

  // Statistics
  agent_count: number;

  // Pricing
  is_paid: boolean;
  price_monthly?: number | null;
  pricing_model: "free" | "one_time" | "monthly";

  // Timestamps
  created_at: string;
  updated_at: string;
}

export interface MarketplaceResponse {
  items: StrategyResponse[];
  total: number;
  limit: number;
  offset: number;
}

export interface StrategyVersionResponse {
  id: string;
  strategy_id: string;
  version: number;
  name: string;
  description: string;
  symbols: string[];
  config: Record<string, unknown>;
  change_note: string;
  created_at: string;
}

export const strategiesApi = {
  list: (params?: {
    type_filter?: StrategyType;
    visibility?: StrategyVisibility;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.type_filter)
      searchParams.set("type_filter", params.type_filter);
    if (params?.visibility) searchParams.set("visibility", params.visibility);
    const query = searchParams.toString();
    return api.get<StrategyResponse[]>(
      `/strategies${query ? `?${query}` : ""}`,
    );
  },

  get: (id: string) => api.get<StrategyResponse>(`/strategies/${id}`),

  create: (data: CreateStrategyRequest) =>
    api.post<StrategyResponse>("/strategies", data),

  update: (id: string, data: UpdateStrategyRequest) =>
    api.patch<StrategyResponse>(`/strategies/${id}`, data),

  delete: (id: string) => api.delete<void>(`/strategies/${id}`),

  fork: (id: string) => api.post<StrategyResponse>(`/strategies/${id}/fork`),

  /** Browse public strategies (marketplace) */
  marketplace: (params?: {
    type_filter?: StrategyType;
    category?: string;
    search?: string;
    sort_by?: "popular" | "recent";
    limit?: number;
    offset?: number;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.type_filter) searchParams.set("type", params.type_filter);
    if (params?.category) searchParams.set("category", params.category);
    if (params?.search) searchParams.set("search", params.search);
    if (params?.sort_by)
      searchParams.set(
        "sort_by",
        params.sort_by === "popular" ? "fork_count" : "newest",
      );
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    const query = searchParams.toString();
    return api.get<MarketplaceResponse>(
      `/strategies/marketplace${query ? `?${query}` : ""}`,
    );
  },

  previewPrompt: (data: Record<string, unknown>) =>
    api.post<{
      system_prompt: string;
      estimated_tokens: number;
      sections: Record<string, string>;
    }>("/strategies/preview-prompt", data),

  /** List version history for a strategy */
  listVersions: (strategyId: string) =>
    api.get<StrategyVersionResponse[]>(`/strategies/${strategyId}/versions`),

  /** Get a specific version snapshot */
  getVersion: (strategyId: string, version: number) =>
    api.get<StrategyVersionResponse>(
      `/strategies/${strategyId}/versions/${version}`,
    ),

  /** Restore a strategy to a previous version */
  restoreVersion: (strategyId: string, version: number) =>
    api.post<StrategyResponse>(
      `/strategies/${strategyId}/versions/${version}/restore`,
    ),

  /** Check subscription status for a paid strategy */
  getSubscription: (strategyId: string) =>
    api.get<{
      strategy_id: string;
      subscribed: boolean;
      status?: string;
      expires_at?: string;
    }>(`/strategies/${strategyId}/subscription`),

  /** Subscribe to a paid strategy */
  subscribe: (strategyId: string) =>
    api.post<{
      strategy_id: string;
      subscribed: boolean;
      status?: string;
      expires_at?: string;
    }>(`/strategies/${strategyId}/subscribe`),
};

// ==================== Agents (execution instances) ====================

export interface CreateAgentRequest {
  name: string;
  strategy_id: string;
  ai_model?: string | null;
  execution_mode: ExecutionMode;
  account_id?: string | null;
  mock_initial_balance?: number | null;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
  execution_interval_minutes?: number;
  auto_execute?: boolean;
  // Trade type (crypto_perp, crypto_spot, etc.)
  trade_type?: string;
  // Multi-model debate configuration
  debate_enabled?: boolean;
  debate_models?: string[];
  debate_consensus_mode?: string;
  debate_min_participants?: number;
}

export interface UpdateAgentRequest {
  name?: string;
  ai_model?: string | null;
  execution_mode?: ExecutionMode;
  account_id?: string | null;
  mock_initial_balance?: number | null;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
  execution_interval_minutes?: number;
  auto_execute?: boolean;
  // Trade type (crypto_perp, crypto_spot, etc.)
  trade_type?: string;
  // Multi-model debate configuration
  debate_enabled?: boolean;
  debate_models?: string[];
  debate_consensus_mode?: string;
  debate_min_participants?: number;
}

export interface AgentStatusRequest {
  status: AgentStatus;
  close_positions?: boolean;
}

export interface AgentResponse {
  id: string;
  user_id: string;
  name: string;

  // Strategy
  strategy_id: string;
  strategy_type?: string | null;
  strategy_name?: string | null;
  strategy_symbols?: string[];

  // AI model
  ai_model?: string | null;

  // Execution mode
  execution_mode: ExecutionMode;
  account_id?: string | null;
  account_name?: string | null;
  account_exchange?: string | null;
  mock_initial_balance?: number | null;

  // Capital allocation
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;

  // Execution config
  execution_interval_minutes: number;
  auto_execute: boolean;

  // Trade type (crypto_perp, crypto_spot, etc.)
  trade_type: string;

  // Multi-model debate configuration
  debate_enabled: boolean;
  debate_models: string[];
  debate_consensus_mode: string;
  debate_min_participants: number;

  // Quant runtime state
  runtime_state?: Record<string, unknown> | null;

  // Strategy config (populated by backend for convenience)
  config?: Record<string, unknown> | null;
  description?: string | null;

  // Status
  status: AgentStatus;
  error_message?: string | null;

  // Worker heartbeat tracking
  worker_heartbeat_at?: string | null;
  worker_instance_id?: string | null;
  is_running: boolean;

  // Performance
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
  next_run_at?: string | null;
}

export interface AgentPositionResponse {
  id: string;
  agent_id: string;
  account_id: string;
  symbol: string;
  side: "long" | "short";
  size: number;
  size_usd: number;
  entry_price: number;
  leverage: number;
  status: string;
  realized_pnl: number;
  close_price?: number | null;
  opened_at?: string | null;
  closed_at?: string | null;
  // Real-time fields (populated in live mode from exchange)
  mark_price?: number | null;
  unrealized_pnl?: number | null;
  unrealized_pnl_percent?: number | null;
}

export interface AgentAccountStateResponse {
  equity: number;
  available_balance: number;
  total_unrealized_pnl: number;
  total_margin_used: number;
}

export interface BoundAccountInfo {
  account_id: string;
  total_percent: number;
  agent_count: number;
  allocation_mode?: "percent" | "fixed" | null;
}

export const agentsApi = {
  list: (params?: {
    status_filter?: AgentStatus;
    strategy_type?: StrategyType;
  }) => {
    const searchParams = new URLSearchParams();
    if (params?.status_filter)
      searchParams.set("status_filter", params.status_filter);
    if (params?.strategy_type)
      searchParams.set("strategy_type", params.strategy_type);
    const query = searchParams.toString();
    return api.get<AgentResponse[]>(`/agents${query ? `?${query}` : ""}`);
  },

  get: (id: string) => api.get<AgentResponse>(`/agents/${id}`),

  create: (data: CreateAgentRequest) =>
    api.post<AgentResponse>("/agents", data),

  update: (id: string, data: UpdateAgentRequest) =>
    api.patch<AgentResponse>(`/agents/${id}`, data),

  delete: (id: string) => api.delete<void>(`/agents/${id}`),

  updateStatus: (id: string, status: AgentStatus, close_positions?: boolean) =>
    api.post<AgentResponse>(`/agents/${id}/status`, {
      status,
      close_positions,
    }),

  activate: (id: string) =>
    api.post<AgentResponse>(`/agents/${id}/status`, { status: "active" }),

  pause: (id: string) =>
    api.post<AgentResponse>(`/agents/${id}/status`, { status: "paused" }),

  stop: (id: string, close_positions?: boolean) =>
    api.post<AgentResponse>(`/agents/${id}/status`, {
      status: "stopped",
      close_positions,
    }),

  getPositions: (id: string) =>
    api.get<AgentPositionResponse[]>(`/agents/${id}/positions`),

  getAccountState: (id: string) =>
    api.get<AgentAccountStateResponse>(`/agents/${id}/account-state`),

  trigger: (id: string) =>
    api.post<TriggerExecutionResponse>(`/agents/${id}/trigger`),

  /** Get allocation info for bound accounts */
  getBoundAccounts: () =>
    api.get<Record<string, BoundAccountInfo>>("/agents/bound-accounts"),
};

// ==================== Quant Strategies (DEPRECATED - use strategiesApi + agentsApi) ====================

/** @deprecated Use CreateStrategyRequest + CreateAgentRequest instead */
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

/** @deprecated Use UpdateStrategyRequest + UpdateAgentRequest instead */
export interface UpdateQuantStrategyRequest {
  name?: string;
  description?: string;
  symbol?: string;
  config?: Record<string, unknown>;
  account_id?: string;
  allocated_capital?: number | null;
  allocated_capital_percent?: number | null;
}

/** @deprecated Use StrategyResponse + AgentResponse instead */
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

/**
 * @deprecated Backend /quant-strategies endpoints have been removed.
 * Use strategiesApi (for strategy templates) and agentsApi (for execution instances) instead.
 */
export const quantStrategiesApi = {
  list: (params?: { status_filter?: string; strategy_type?: string }) => {
    // Redirect to unified agents API filtered by quant types
    return agentsApi.list({
      status_filter: params?.status_filter as AgentStatus,
      strategy_type: params?.strategy_type as StrategyType,
    });
  },

  get: (id: string) => agentsApi.get(id),

  create: (_data: CreateQuantStrategyRequest) => {
    throw new Error(
      "quantStrategiesApi.create is deprecated. Use strategiesApi.create + agentsApi.create instead.",
    );
  },

  update: (id: string, data: UpdateQuantStrategyRequest) =>
    agentsApi.update(id, data),

  delete: (id: string) => agentsApi.delete(id),

  updateStatus: (
    id: string,
    status: StrategyStatus,
    close_positions?: boolean,
  ) => agentsApi.updateStatus(id, status, close_positions),
};

// ==================== Workers ====================

export interface TriggerExecutionResponse {
  message: string;
  success: boolean;
  job_id?: string;
  decision_id?: string;
}

export const workersApi = {
  /** @deprecated Use agentsApi.trigger(agentId) instead */
  triggerExecution: (agentId: string) => agentsApi.trigger(agentId),
};

// ==================== Accounts ====================

export interface CreateAccountRequest {
  name: string;
  exchange: ExchangeType;
  is_testnet: boolean;
  api_key?: string;
  api_secret?: string;
  private_key?: string; // For Hyperliquid (direct private key)
  mnemonic?: string; // For Hyperliquid (12/24 word seed phrase)
  passphrase?: string; // For exchanges that require it
}

export interface AccountResponse {
  id: string;
  name: string;
  exchange: ExchangeType;
  is_testnet: boolean;
  is_connected: boolean;
  connection_error?: string | null;
  created_at: string;
  last_synced_at?: string | null; // Optional: last time balance was fetched
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
    side: "long" | "short";
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
  list: () => api.get<AccountResponse[]>("/accounts"),

  get: (id: string) => api.get<AccountResponse>(`/accounts/${id}`),

  create: (data: CreateAccountRequest) =>
    api.post<AccountResponse>("/accounts", data),

  update: (id: string, data: Partial<CreateAccountRequest>) =>
    api.patch<AccountResponse>(`/accounts/${id}`, data),

  delete: (id: string) => api.delete<void>(`/accounts/${id}`),

  testConnection: (id: string) =>
    api.post<{ success: boolean; message: string }>(`/accounts/${id}/test`),

  getBalance: (id: string) =>
    api.get<AccountBalanceResponse>(`/accounts/${id}/balance`),

  getPositions: (id: string) =>
    api.get<AccountBalanceResponse["positions"]>(`/accounts/${id}/positions`),
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
  indicators: Record<
    string,
    {
      ema: Record<string, number>;
      rsi: number | null;
      rsi_signal: string;
      macd: { macd: number; signal: number; histogram: number };
      macd_signal: string;
      atr: number | null;
      bollinger: { upper: number; middle: number; lower: number };
      ema_trend: string;
    }
  >;
  klines: Record<
    string,
    Array<{
      timestamp: string;
      open: number;
      high: number;
      low: number;
      close: number;
      volume: number;
    }>
  >;
  funding_history: Array<{ timestamp: string; rate: number }>;
  available_timeframes: string[];
}

export interface DecisionResponse {
  id: string;
  agent_id: string;
  /** @deprecated use agent_id */
  strategy_id?: string;
  timestamp: string; // Backend uses timestamp, not created_at
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
  execution_results: unknown[]; // Backend uses execution_results (array)
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
    side: "long" | "short";
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
    api.get<DecisionResponse[]>("/decisions/recent", { params: { limit } }),

  /** List decisions by agent (new primary endpoint) */
  listByAgent: (
    agentId: string,
    limit: number = 10,
    offset: number = 0,
    executionFilter: string = "all",
    action?: string,
  ) =>
    api.get<PaginatedDecisionResponse>(`/decisions/agent/${agentId}`, {
      params: {
        limit,
        offset,
        execution_filter: executionFilter,
        ...(action ? { action } : {}),
      },
    }),

  /** @deprecated Use listByAgent instead */
  listByStrategy: (
    strategyId: string,
    limit: number = 10,
    offset: number = 0,
    executionFilter: string = "all",
    action?: string,
  ) =>
    api.get<PaginatedDecisionResponse>(`/decisions/strategy/${strategyId}`, {
      params: {
        limit,
        offset,
        execution_filter: executionFilter,
        ...(action ? { action } : {}),
      },
    }),

  get: (id: string) => api.get<DecisionResponse>(`/decisions/${id}`),

  /** Get stats by agent (new primary endpoint) */
  getStatsByAgent: (agentId: string) =>
    api.get<DecisionStatsResponse>(`/decisions/agent/${agentId}/stats`),

  /** @deprecated Use getStatsByAgent instead */
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
  ai_model?: string;
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
    api.post<BacktestResponse>("/backtest/run", data),

  quick: (data: QuickBacktestRequest) =>
    api.post<BacktestResponse>("/backtest/quick", data),

  getSymbols: (exchange: string = "binance") =>
    api.get<{ symbols: Array<{ symbol: string; full_symbol: string }> }>(
      "/backtest/symbols",
      {
        params: { exchange },
      },
    ),

  // Persisted backtest records
  list: (limit: number = 20, offset: number = 0) =>
    api.get<BacktestListResponse>("/backtests", {
      params: { limit, offset },
    }),

  get: (id: string) => api.get<BacktestDetailResponse>(`/backtests/${id}`),

  create: (data: BacktestRequest) =>
    api.post<BacktestDetailResponse>("/backtests", data),

  delete: (id: string) => api.delete<void>(`/backtests/${id}`),
};

// Backtest list item
export interface BacktestListItem {
  id: string;
  strategy_name: string;
  symbols: string[];
  exchange: string;
  start_date: string;
  end_date: string;
  initial_balance: number;
  final_balance: number;
  total_return_percent: number;
  total_trades: number;
  win_rate: number;
  max_drawdown_percent: number;
  sharpe_ratio?: number;
  created_at: string;
}

export interface BacktestListResponse {
  items: BacktestListItem[];
  total: number;
  limit: number;
  offset: number;
}

// Full backtest detail (extends BacktestResponse with id and timestamps)
export interface BacktestDetailResponse extends BacktestResponse {
  id: string;
  strategy_id?: string;
  symbols: string[];
  exchange: string;
  use_ai: boolean;
  timeframe: string;
  sortino_ratio?: number;
  calmar_ratio?: number;
  created_at: string;
}

// ==================== Dashboard ====================

export interface AccountBalanceSummary {
  account_id: string;
  account_name: string;
  exchange: string;
  status: "online" | "offline" | "error";
  total_equity: number;
  available_balance: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  open_positions: number;
}

export interface DashboardStatsResponse {
  // Account-level breakdown
  accounts: AccountBalanceSummary[];
  // Aggregated totals
  total_equity: number;
  total_available: number;
  available_balance: number;
  unrealized_pnl: number;
  // Daily P/L
  daily_pnl: number;
  daily_pnl_percent: number;
  // Weekly P/L
  weekly_pnl: number;
  weekly_pnl_percent: number;
  // Monthly P/L
  monthly_pnl: number;
  monthly_pnl_percent: number;
  // Strategies
  active_strategies: number;
  total_strategies: number;
  // Positions
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
    account_id?: string;
  }>;
  // Today's decisions
  today_decisions: number;
  today_executed_decisions: number;
  // Account breakdown (legacy)
  accounts_connected: number;
  accounts_total: number;
}

export interface ActivityItem {
  id: string;
  type: "decision" | "trade" | "strategy_status" | "system";
  timestamp: string;
  title: string;
  description: string;
  data?: Record<string, unknown>;
  status?: "success" | "error" | "info";
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
      const response =
        await api.get<DashboardStatsResponse>("/dashboard/stats");

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
      const [_accounts, agents] = await Promise.all([
        accountsApi.list(),
        agentsApi.list(),
      ]);

      const activeAgents = agents.filter((a) => a.status === "active").length;

      return {
        totalEquity: 0,
        dailyPnl: 0,
        dailyPnlPercent: 0,
        activeStrategies: activeAgents,
        openPositions: 0,
        todayTrades: 0,
      };
    }
  },

  // Direct access to the full stats response
  getFullStats: () => api.get<DashboardStatsResponse>("/dashboard/stats"),

  // Get activity feed
  getActivity: (limit: number = 20, offset: number = 0) =>
    api.get<ActivityFeedResponse>("/dashboard/activity", {
      params: { limit, offset },
    }),
};

// ==================== Health ====================

export interface HealthResponse {
  status: "healthy" | "degraded";
  version: string;
  environment: string;
  components?: {
    redis: { status: string };
    database: { status: string };
  };
}

export const healthApi = {
  check: () => api.get<HealthResponse>("/health", { skipAuth: true }),

  detailed: () => api.get<HealthResponse>("/health/detailed"),
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
  listProviders: () => api.get<AIProviderResponse[]>("/models/providers"),

  list: (provider?: string) =>
    api.get<AIModelInfoResponse[]>("/models", {
      params: provider ? { provider } : {},
    }),

  get: (modelId: string) =>
    api.get<AIModelInfoResponse>(`/models/${encodeURIComponent(modelId)}`),

  test: (data: TestModelRequest) =>
    api.post<{
      model_id: string;
      success: boolean;
      message: string;
      error_code?: string;
    }>("/models/test", data),
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
  listPresets: () => api.get<PresetProviderInfo[]>("/providers/presets"),

  listFormats: () =>
    api.get<{ formats: ApiFormatInfo[] }>("/providers/formats"),

  list: () => api.get<ProviderConfigResponse[]>("/providers"),

  get: (id: string) => api.get<ProviderConfigResponse>(`/providers/${id}`),

  create: (data: CreateProviderRequest) =>
    api.post<ProviderConfigResponse>("/providers", data),

  update: (id: string, data: UpdateProviderRequest) =>
    api.patch<ProviderConfigResponse>(`/providers/${id}`, data),

  delete: (id: string) => api.delete<void>(`/providers/${id}`),

  test: (id: string, apiKey?: string) =>
    api.post<{ success: boolean; message: string }>(`/providers/${id}/test`, {
      api_key: apiKey,
    }),

  // Per-provider model CRUD
  listModels: (providerId: string) =>
    api.get<ProviderModelItem[]>(`/providers/${providerId}/models`),

  addModel: (providerId: string, data: ProviderModelItem) =>
    api.post<ProviderModelItem>(`/providers/${providerId}/models`, data),

  replaceModels: (providerId: string, models: ProviderModelItem[]) =>
    api.put<ProviderModelItem[]>(`/providers/${providerId}/models`, { models }),

  deleteModel: (providerId: string, modelId: string) =>
    api.delete<void>(
      `/providers/${providerId}/models/${encodeURIComponent(modelId)}`,
    ),
};

// ==================== System ====================

export interface OutboundIPResponse {
  ip: string | null;
  source: string;
  cached: boolean;
}

export const systemApi = {
  getOutboundIP: () => api.get<OutboundIPResponse>("/system/outbound-ip"),
};

// ==================== Data (Symbols & Exchanges) ====================

import type {
  AssetType,
  ExchangeCapabilities,
  ExchangeCapabilitiesResponse,
} from "@/types";

export interface SymbolItem {
  symbol: string;
  full_symbol: string;
}

export interface SymbolsResponse {
  exchange: string;
  asset_type?: string | null;
  symbols: SymbolItem[];
  cached: boolean;
}

export interface ExchangesForAssetResponse {
  asset_type: AssetType;
  exchanges: ExchangeCapabilities[];
}

export const dataApi = {
  /**
   * Get available trading symbols for an exchange.
   * Returns both base symbol (e.g., 'BTC') and full CCXT format (e.g., 'BTC/USDT:USDT').
   *
   * @param exchange - Exchange name (binance, okx, hyperliquid, etc.)
   * @param assetType - Optional asset type filter (crypto_perp, crypto_spot, forex, metals)
   */
  getSymbols: (exchange: string = "binance", assetType?: AssetType) =>
    api.get<SymbolsResponse>("/data/symbols", {
      params: { exchange, ...(assetType ? { asset_type: assetType } : {}) },
    }),

  /**
   * Get all exchange capabilities.
   * Returns information about supported exchanges including asset types, settlement currencies, features.
   */
  getExchanges: () => api.get<ExchangeCapabilitiesResponse>("/data/exchanges"),

  /**
   * Get capabilities for a specific exchange.
   *
   * @param exchangeId - Exchange identifier (e.g., 'hyperliquid', 'binance')
   */
  getExchange: (exchangeId: string) =>
    api.get<ExchangeCapabilities>(`/data/exchanges/${exchangeId}`),

  /**
   * Get all exchanges that support a specific asset type.
   *
   * @param assetType - Asset type to filter by
   */
  getExchangesForAsset: (assetType: AssetType) =>
    api.get<ExchangesForAssetResponse>(
      `/data/exchanges/for-asset/${assetType}`,
    ),
};

// ==================== Analytics ====================

export interface PnLTradeRecord {
  id: string;
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number | null;
  size: number;
  size_usd: number;
  leverage: number;
  realized_pnl: number;
  fees: number;
  opened_at: string;
  closed_at: string;
  duration_minutes: number;
  exit_reason: string | null;
}

export interface AgentPnLSummary {
  total_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  total_fees: number;
}

export interface AgentPnLResponse {
  agent_id: string;
  agent_name: string;
  summary: AgentPnLSummary;
  trades: PnLTradeRecord[];
  total: number;
  limit: number;
  offset: number;
}

export interface AgentPerformance {
  agent_id: string;
  agent_name: string;
  strategy_name: string;
  strategy_type: string;
  status: string;
  total_pnl: number;
  daily_pnl: number;
  win_rate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  max_drawdown: number;
  open_positions: number;
}

export interface AccountAgentsResponse {
  account_id: string;
  agents: AgentPerformance[];
  total: number;
}

export interface EquityDataPoint {
  date: string;
  equity: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  cumulative_pnl: number;
  cumulative_pnl_percent: number;
}

export interface EquityCurveResponse {
  account_id: string;
  start_date: string;
  end_date: string;
  granularity: string;
  data_points: EquityDataPoint[];
}

export interface AccountPnLSummary {
  account_id: string;
  account_name: string;
  exchange: string;
  current_equity: number;
  total_pnl: number;
  total_pnl_percent: number;
  daily_pnl: number;
  daily_pnl_percent: number;
  weekly_pnl: number;
  weekly_pnl_percent: number;
  monthly_pnl: number;
  monthly_pnl_percent: number;
  win_rate: number;
  total_trades: number;
  profit_factor: number;
  max_drawdown_percent: number | null;
  sharpe_ratio: number | null;
}

export const analyticsApi = {
  /**
   * Get P&L details for a specific agent.
   */
  getAgentPnL: (
    agentId: string,
    params?: {
      start_date?: string;
      end_date?: string;
      limit?: number;
      offset?: number;
    },
  ) =>
    api.get<AgentPnLResponse>(`/analytics/agents/${agentId}/pnl`, {
      params,
    }),

  /**
   * Get performance metrics for all agents on an account.
   */
  getAccountAgents: (accountId: string) =>
    api.get<AccountAgentsResponse>(`/analytics/accounts/${accountId}/agents`),

  /**
   * Get equity curve data for an account.
   */
  getEquityCurve: (
    accountId: string,
    params?: {
      start_date?: string;
      end_date?: string;
      granularity?: "day" | "week" | "month";
    },
  ) =>
    api.get<EquityCurveResponse>(
      `/analytics/accounts/${accountId}/equity-curve`,
      { params },
    ),

  /**
   * Get P&L summary for an account.
   */
  getAccountPnL: (accountId: string) =>
    api.get<AccountPnLSummary>(`/analytics/accounts/${accountId}/pnl`),

  /**
   * Sync account snapshot with real-time data from exchange.
   * Creates/updates today's snapshot for immediate P&L visibility.
   */
  syncAccount: (accountId: string) =>
    api.post<SyncSnapshotResponse>(`/analytics/accounts/${accountId}/sync`),
};

// ==================== Wallet Types ====================

export interface WalletResponse {
  user_id: string;
  balance: number;
  frozen_balance: number;
  total_balance: number;
  total_recharged: number;
  total_consumed: number;
}

export interface WalletTransactionResponse {
  id: string;
  type: "recharge" | "consume" | "refund" | "gift" | "adjustment";
  amount: number;
  balance_before: number;
  balance_after: number;
  reference_type: string | null;
  reference_id: string | null;
  commission_info: {
    channel_id: string | null;
    channel_amount: number;
    platform_amount: number;
  } | null;
  description: string | null;
  created_at: string;
}

export interface TransactionSummaryResponse {
  recharge: number;
  consume: number;
  refund: number;
  gift: number;
  adjustment: number;
}

export interface InviteInfoResponse {
  invite_code: string | null; // Always null (users don't have codes)
  referrer_id: string | null; // Always null (no referral tracking)
  channel_id: string | null;
  total_invited: number; // Always 0 (users can't invite)
  channel_code: string | null; // Channel's invite code for sharing
}

export const walletsApi = {
  getMyWallet: () => api.get<WalletResponse>("/wallets/me"),

  getMyTransactions: (params?: {
    types?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<WalletTransactionResponse[]>("/wallets/me/transactions", {
      params,
    }),

  getMySummary: (params?: { start_date?: string; end_date?: string }) =>
    api.get<TransactionSummaryResponse>("/wallets/me/summary", { params }),

  getMyInviteInfo: () => api.get<InviteInfoResponse>("/wallets/me/invite"),
};

// ==================== Recharge Types ====================

export interface RechargeOrderResponse {
  id: string;
  user_id: string;
  order_no: string;
  amount: number;
  bonus_amount: number;
  total_amount: number;
  payment_method: string;
  status: "pending" | "paid" | "completed" | "failed" | "refunded";
  paid_at: string | null;
  completed_at: string | null;
  note: string | null;
  created_at: string;
  updated_at: string;
}

export interface RechargeOrderListResponse extends RechargeOrderResponse {
  user_email: string | null;
  user_name: string | null;
}

export const rechargeApi = {
  createOrder: (data: { amount: number; bonus_amount?: number }) =>
    api.post<RechargeOrderResponse>("/recharge/orders", data),

  getMyOrders: (params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) => api.get<RechargeOrderResponse[]>("/recharge/orders", { params }),

  getMyOrder: (orderId: string) =>
    api.get<RechargeOrderResponse>(`/recharge/orders/${orderId}`),

  // Admin
  adminListOrders: (params?: {
    status?: string;
    user_id?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
    offset?: number;
  }) =>
    api.get<RechargeOrderListResponse[]>("/recharge/admin/orders", { params }),

  adminMarkPaid: (orderId: string, note?: string) =>
    api.post<RechargeOrderResponse>(
      `/recharge/admin/orders/${orderId}/mark-paid`,
      { note },
    ),

  adminConfirm: (orderId: string, note?: string) =>
    api.post<RechargeOrderResponse>(
      `/recharge/admin/orders/${orderId}/confirm`,
      { note },
    ),

  adminCancel: (orderId: string, note?: string) =>
    api.post<{ message: string; order_id: string }>(
      `/recharge/admin/orders/${orderId}/cancel`,
      { note },
    ),
};

// ==================== Channel Types ====================

export interface ChannelResponse {
  id: string;
  name: string;
  code: string;
  commission_rate: number;
  status: "active" | "suspended" | "closed";
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  admin_user_id: string | null;
  total_users: number;
  total_revenue: number;
  total_commission: number;
  // Extended statistics
  total_accounts: number;
  total_agents: number;
  active_users: number;
  available_balance: number;
  pending_commission: number;
  created_at: string;
  updated_at: string;
}

export interface ChannelWalletResponse {
  channel_id: string;
  balance: number;
  frozen_balance: number;
  pending_commission: number;
  total_commission: number;
  total_withdrawn: number;
}

export interface ChannelUserResponse {
  id: string;
  email: string;
  name: string;
  created_at: string;
}

export interface ChannelStatisticsResponse {
  total_users: number;
  active_users: number;
  total_revenue: number;
  total_commission: number;
  period_commission: number;
  pending_commission: number;
  available_balance: number;
  frozen_balance: number;
}

// Admin user with channel info
export interface AdminUserResponse {
  id: string;
  email: string;
  name: string;
  role: string;
  channel_id: string | null;
  channel_name: string | null;
  channel_code: string | null;
  is_active: boolean;
  created_at: string;
}

export interface AdminUserListResponse {
  users: AdminUserResponse[];
  total: number;
  limit: number;
  offset: number;
}

export const channelsApi = {
  // Platform Admin
  create: (data: {
    name: string;
    code: string;
    commission_rate?: number;
    contact_name?: string;
    contact_email?: string;
    contact_phone?: string;
    admin_user_id?: string;
  }) => api.post<ChannelResponse>("/channels", data),

  list: (params?: { status?: string; limit?: number; offset?: number }) =>
    api.get<ChannelResponse[]>("/channels", { params }),

  get: (channelId: string) =>
    api.get<ChannelResponse>(`/channels/${channelId}`),

  update: (
    channelId: string,
    data: Partial<{
      name: string;
      commission_rate: number;
      contact_name: string;
      contact_email: string;
      contact_phone: string;
      admin_user_id: string;
    }>,
  ) => api.put<ChannelResponse>(`/channels/${channelId}`, data),

  updateStatus: (
    channelId: string,
    status: "active" | "suspended" | "closed",
  ) => api.put<ChannelResponse>(`/channels/${channelId}/status`, { status }),

  // Channel Admin
  getMyChannel: () => api.get<ChannelResponse>("/channels/me"),

  getMyUsers: (params?: { limit?: number; offset?: number }) =>
    api.get<ChannelUserResponse[]>("/channels/me/users", { params }),

  getMyWallet: () => api.get<ChannelWalletResponse>("/channels/me/wallet"),

  getMyStatistics: (params?: { start_date?: string; end_date?: string }) =>
    api.get<ChannelStatisticsResponse>("/channels/me/statistics", { params }),

  // Platform Admin - User Management
  listAllUsers: (params?: {
    search?: string;
    role?: string;
    channel_id?: string;
    limit?: number;
    offset?: number;
  }) => api.get<AdminUserListResponse>("/channels/admin/users", { params }),

  setUserChannel: (userId: string, channelId: string | null) =>
    api.put<{ message: string; channel_id: string | null }>(
      `/channels/admin/users/${userId}/channel?channel_id=${channelId || ""}`,
    ),
};

// ==================== Accounting Types ====================

export interface UserAccountingOverview {
  balance: number;
  frozen_balance: number;
  total_balance: number;
  total_recharged: number;
  total_consumed: number;
  period_recharged: number;
  period_consumed: number;
}

export interface ChannelAccountingOverview {
  channel_id: string;
  channel_name: string;
  channel_code: string;
  commission_rate: number;
  total_users: number;
  total_revenue: number;
  total_commission: number;
  available_balance: number;
  pending_commission: number;
  period_commission: number;
  active_users: number;
}

export interface PlatformAccountingOverview {
  total_channels: number;
  active_channels: number;
  total_users: number;
  total_revenue: number;
  total_commission: number;
  platform_revenue: number;
}

export interface DailyStats {
  date: string;
  recharge_amount: number;
  consume_amount: number;
  commission_amount: number;
}

export const accountingApi = {
  // User
  getUserOverview: (params?: { start_date?: string; end_date?: string }) =>
    api.get<UserAccountingOverview>("/accounting/overview", { params }),

  // Channel
  getChannelOverview: (
    channelId: string,
    params?: { start_date?: string; end_date?: string },
  ) =>
    api.get<ChannelAccountingOverview>(
      `/accounting/channels/${channelId}/overview`,
      { params },
    ),

  getMyChannelOverview: (params?: { start_date?: string; end_date?: string }) =>
    api.get<ChannelAccountingOverview>("/accounting/channels/me/overview", {
      params,
    }),

  // Platform Admin
  getPlatformOverview: () =>
    api.get<PlatformAccountingOverview>("/accounting/platform/overview"),

  getPlatformDailyStats: (days?: number) =>
    api.get<DailyStats[]>("/accounting/platform/daily", { params: { days } }),
};

export interface SyncSnapshotResponse {
  success: boolean;
  message: string;
  equity?: number;
  daily_pnl?: number;
}
