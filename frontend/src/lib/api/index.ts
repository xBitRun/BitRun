/**
 * API Module exports
 */

export { api, ApiError, AuthError, TokenManager } from "./client";
export {
  authApi,
  strategiesApi,
  agentsApi,
  quantStrategiesApi,
  accountsApi,
  decisionsApi,
  backtestApi,
  dashboardApi,
  systemApi,
  healthApi,
  modelsApi,
  providersApi,
  workersApi,
  dataApi,
} from "./endpoints";

export type {
  // Auth
  LoginRequest,
  RegisterRequest,
  UserResponse,
  TokenResponse,
  ProfileUpdateRequest,
  ChangePasswordRequest,
  // Strategies (v2 - unified)
  CreateStrategyRequest,
  UpdateStrategyRequest,
  StrategyResponse,
  MarketplaceResponse,
  StrategyVersionResponse,
  // Agents (new)
  CreateAgentRequest,
  UpdateAgentRequest,
  AgentStatusRequest,
  AgentResponse,
  AgentPositionResponse,
  AgentAccountStateResponse,
  BoundAccountInfo,
  DeleteAgentResponse,
  // Accounts
  CreateAccountRequest,
  AccountResponse,
  AccountBalanceResponse,
  // Decisions
  DecisionResponse,
  DecisionExecutionResult,
  PaginatedDecisionResponse,
  DecisionStatsResponse,
  // Dashboard
  DashboardStatsResponse,
  DashboardExecutionMode,
  ActivityItem,
  ActivityFeedResponse,
  // Backtest
  BacktestExchange,
  BacktestRequest,
  QuickBacktestRequest,
  BacktestResponse,
  BacktestListItem,
  BacktestListResponse,
  BacktestDetailResponse,
  TradeRecord,
  PnLTradeRecord,
  TradeStatistics,
  SideStats,
  MonthlyReturn,
  SymbolBreakdown,
  // Health
  HealthResponse,
  // AI Models
  AIModelInfoResponse,
  AIProviderResponse,
  TestModelRequest,
  // AI Providers
  PresetProviderInfo,
  ProviderConfigResponse,
  CreateProviderRequest,
  UpdateProviderRequest,
  ApiFormatInfo,
  ProviderModelItem,
  // Quant Strategies (deprecated)
  CreateQuantStrategyRequest,
  UpdateQuantStrategyRequest,
  QuantStrategyApiResponse,
  // Workers
  TriggerExecutionResponse,
  // System
  OutboundIPResponse,
  // Data
  SymbolItem,
  SymbolsResponse,
  PricePrefetchStatsResponse,
} from "./endpoints";
