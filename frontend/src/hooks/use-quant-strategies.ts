/**
 * Quant Strategies Hooks
 *
 * @deprecated MIGRATION GUIDE - Replace with unified agent/strategy hooks:
 *
 * | Old (deprecated)              | New                                  |
 * |-------------------------------|--------------------------------------|
 * | useQuantStrategies()          | useAgents()                          |
 * | useQuantStrategy(id)          | useAgent(id)                         |
 * | useCreateQuantStrategy()      | useCreateStrategy() + useCreateAgent()|
 * | useUpdateQuantStrategy(id)    | useUpdateAgent(id)                   |
 * | useDeleteQuantStrategy(id)    | useDeleteAgent(id)                   |
 * | useUpdateQuantStrategyStatus()| useUpdateAgentStatus(id)             |
 *
 * All hooks above are re-exported from '@/hooks/index.ts'.
 * The quantStrategies i18n namespace is retained for grid/dca/rsi
 * parameter labels; full removal is planned for Phase 2.
 *
 * This backward-compat layer delegates to the agents API.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { agentsApi } from '@/lib/api';
import type {
  AgentResponse,
  UpdateAgentRequest,
} from '@/lib/api';
import type { AgentStatus, StrategyType } from '@/types';

// Re-export for backward compat
export type QuantStrategyApiResponse = AgentResponse;
export type CreateQuantStrategyRequest = never;
export type UpdateQuantStrategyRequest = UpdateAgentRequest;

// Keys
const QUANT_STRATEGIES_KEY = '/agents?quant';
const quantStrategyKey = (id: string) => `/agents/${id}`;

/**
 * @deprecated Use useAgents instead.
 */
export function useQuantStrategies() {
  const swr = useSWR<AgentResponse[]>(
    QUANT_STRATEGIES_KEY,
    () => agentsApi.list({ strategy_type: 'grid' as StrategyType }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    }
  );
  return {
    ...swr,
    strategies: swr.data ?? [],
    refresh: swr.mutate,
  };
}

/**
 * @deprecated Use useAgent instead.
 */
export function useQuantStrategy(id: string | null) {
  return useSWR<AgentResponse>(
    id ? quantStrategyKey(id) : null,
    () => agentsApi.get(id!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * @deprecated Use useCreateAgent + useCreateStrategy instead.
 */
export function useCreateQuantStrategy() {
  return useSWRMutation<AgentResponse, Error, string, Record<string, unknown>>(
    QUANT_STRATEGIES_KEY,
    async () => {
      throw new Error('useCreateQuantStrategy is deprecated. Use useCreateAgent + useCreateStrategy instead.');
    }
  );
}

/**
 * @deprecated Use useUpdateAgent instead.
 */
export function useUpdateQuantStrategy(id: string) {
  return useSWRMutation<AgentResponse, Error, string, UpdateAgentRequest>(
    quantStrategyKey(id),
    async (_, { arg }) => {
      return agentsApi.update(id, arg);
    }
  );
}

/**
 * @deprecated Use useDeleteAgent instead.
 */
export function useDeleteQuantStrategy(id: string) {
  return useSWRMutation<void, Error, string>(
    quantStrategyKey(id),
    async () => {
      return agentsApi.delete(id);
    }
  );
}

/**
 * @deprecated Use useUpdateAgentStatus instead.
 */
export function useUpdateQuantStrategyStatus(id: string) {
  return useSWRMutation<AgentResponse, Error, string, AgentStatus>(
    quantStrategyKey(id),
    async (_, { arg }) => {
      return agentsApi.updateStatus(id, arg);
    }
  );
}
