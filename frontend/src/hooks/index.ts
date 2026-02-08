/**
 * Hooks exports
 */

// Mobile detection
export { useIsMobile } from './use-mobile';

// Data hooks
export {
  useStrategies,
  useStrategy,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useUpdateStrategyStatus,
  useActiveStrategiesCount,
} from './use-strategies';

export {
  useAccounts,
  useAccount,
  useAccountBalance,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useTestAccountConnection,
  useTotalEquity,
} from './use-accounts';

export {
  useRecentDecisions,
  useStrategyDecisions,
  useDecision,
  useDecisionStats,
  useLatestDecision,
} from './use-decisions';
export type { DecisionFilters } from './use-decisions';

export {
  useRunBacktest,
  useQuickBacktest,
  useBacktestSymbols,
} from './use-backtest';

// Dashboard hooks
export {
  useDashboardStats,
  useAllPositions,
  useAccountsWithBalances,
  usePerformanceStats,
  useActivityFeed,
} from './use-dashboard';
export type { DashboardStats, Position } from './use-dashboard';

// WebSocket hook
export { useWebSocket } from './use-websocket';

// AI Models hooks
export {
  useModels,
  useModelProviders,
  useUserModels,
  getModelDisplayName,
  getProviderDisplayName,
  groupModelsByProvider,
} from './use-models';

// AI Provider Config hooks
export {
  usePresetProviders,
  useProviderConfigs,
  useApiFormats,
  getPresetInfo,
  getProviderIcon,
  getProviderConfigDisplayName,
} from './use-providers';

// Strategy Studio hook
export {
  useStrategyStudio,
  apiResponseToConfig,
} from './use-strategy-studio';

// Quant Strategies hooks
export {
  useQuantStrategies,
  useQuantStrategy,
  useCreateQuantStrategy,
  useUpdateQuantStrategy,
  useDeleteQuantStrategy,
  useUpdateQuantStrategyStatus,
} from './use-quant-strategies';
