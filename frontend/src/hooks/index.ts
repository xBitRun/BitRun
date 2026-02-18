/**
 * Hooks exports
 */

// Mobile detection
export { useIsMobile } from "./use-mobile";

// Strategy hooks (v2 - unified templates)
export {
  useStrategies,
  useStrategy,
  useCreateStrategy,
  useUpdateStrategy,
  useDeleteStrategy,
  useForkStrategy,
  useMarketplaceStrategies,
  useStrategyVersions,
  useRestoreStrategyVersion,
} from "./use-strategies";

// Agent hooks (execution instances)
export {
  useAgents,
  useAgent,
  useCreateAgent,
  useUpdateAgent,
  useDeleteAgent,
  useUpdateAgentStatus,
  useTriggerAgent,
  useAgentPositions,
  useActiveAgentsCount,
  useBoundAccounts,
} from "./use-agents";

// Account hooks
export {
  useAccounts,
  useAccount,
  useAccountBalance,
  useCreateAccount,
  useUpdateAccount,
  useDeleteAccount,
  useTestAccountConnection,
  useTotalEquity,
} from "./use-accounts";

// Decision hooks
export {
  useRecentDecisions,
  useAgentDecisions,
  useStrategyDecisions,
  useDecision,
  useAgentDecisionStats,
  useDecisionStats,
  useLatestDecision,
} from "./use-decisions";
export type { DecisionFilters } from "./use-decisions";

// Backtest hooks
export {
  useRunBacktest,
  useQuickBacktest,
  useBacktestSymbols,
  useBacktests,
  useBacktest,
  useCreateBacktest,
  useDeleteBacktest,
} from "./use-backtest";

// Dashboard hooks
export {
  useDashboardStats,
  useAllPositions,
  useAccountsWithBalances,
  usePerformanceStats,
  useActivityFeed,
} from "./use-dashboard";
export type { DashboardStats, Position, AccountSummary } from "./use-dashboard";

// WebSocket hook
export { useWebSocket } from "./use-websocket";

// AI Models hooks
export {
  useModels,
  useModelProviders,
  useUserModels,
  getModelDisplayName,
  getProviderDisplayName,
  groupModelsByProvider,
} from "./use-models";

// AI Provider Config hooks
export {
  usePresetProviders,
  useProviderConfigs,
  useApiFormats,
  getPresetInfo,
  getProviderIcon,
  getProviderConfigDisplayName,
} from "./use-providers";

// Strategy Studio hook
export { useStrategyStudio, apiResponseToConfig } from "./use-strategy-studio";

// System hooks
export { useOutboundIP } from "./use-system";

// Symbols hooks
export { useSymbols, useSymbolsList } from "./use-symbols";
export type { UseSymbolsResult } from "./use-symbols";

// Exchange Capabilities hooks
export {
  useExchangeCapabilities,
  useExchangeCapability,
  useExchangesForAsset,
  useSettlementCurrency,
  useSupportsAsset,
  useStrategyExchangeCompatibility,
} from "./use-exchange-capabilities";

// Quant Strategies hooks (deprecated - use agents + strategies)
export {
  useQuantStrategies,
  useQuantStrategy,
  useCreateQuantStrategy,
  useUpdateQuantStrategy,
  useDeleteQuantStrategy,
  useUpdateQuantStrategyStatus,
} from "./use-quant-strategies";

// Analytics hooks
export {
  useAgentPnL,
  useAccountAgents,
  useEquityCurve,
  useAccountPnL,
  useSyncAccount,
} from "./use-analytics";
export type {
  UseAgentPnLOptions,
  UseEquityCurveOptions,
} from "./use-analytics";

// Wallet hooks
export {
  useWallet,
  useWalletTransactions,
  useTransactionSummary,
  useInviteInfo,
  useRechargeOrders,
  useCreateRechargeOrder,
  useAdminRechargeOrders,
} from "./use-wallet";

// Channel hooks
export {
  useMyChannel,
  useMyChannelUsers,
  useMyChannelWallet,
  useMyChannelStatistics,
  useMyChannelAccounting,
  useChannels,
  useChannel,
  useCreateChannel,
  useUpdateChannel,
  useUpdateChannelStatus,
  useAdminUsers,
  useSetUserChannel,
} from "./use-channel";
