/**
 * API Module exports
 */

export { api, ApiError, AuthError, TokenManager } from './client';
export {
  authApi,
  strategiesApi,
  quantStrategiesApi,
  accountsApi,
  decisionsApi,
  backtestApi,
  dashboardApi,
  competitionApi,
  systemApi,
  healthApi,
  modelsApi,
  providersApi,
  workersApi,
} from './endpoints';

export type {
  // Auth
  LoginRequest,
  RegisterRequest,
  UserResponse,
  TokenResponse,
  ProfileUpdateRequest,
  ChangePasswordRequest,
  // Strategies
  CreateStrategyRequest,
  UpdateStrategyRequest,
  StrategyResponse,
  // Accounts
  CreateAccountRequest,
  AccountResponse,
  AccountBalanceResponse,
  // Decisions
  DecisionResponse,
  PaginatedDecisionResponse,
  DecisionStatsResponse,
  // Dashboard
  DashboardStatsResponse,
  ActivityItem,
  ActivityFeedResponse,
  // Backtest
  BacktestExchange,
  BacktestRequest,
  QuickBacktestRequest,
  BacktestResponse,
  TradeRecord,
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
  // Quant Strategies
  CreateQuantStrategyRequest,
  UpdateQuantStrategyRequest,
  QuantStrategyApiResponse,
  // Workers
  TriggerExecutionResponse,
  // Competition
  LeaderboardEntry,
  CompetitionStats,
  LeaderboardResponse,
  // System
  OutboundIPResponse,
} from './endpoints';
