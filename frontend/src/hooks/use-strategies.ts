/**
 * Strategies Hooks (v2 - unified strategy templates)
 * 
 * SWR hooks for strategy data fetching and mutations.
 * Strategy is a pure logic template - no runtime bindings.
 * For execution instances, see use-agents.ts.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { strategiesApi, ApiError } from '@/lib/api';
import type { 
  StrategyResponse, 
  MarketplaceResponse,
  StrategyVersionResponse,
  CreateStrategyRequest, 
  UpdateStrategyRequest 
} from '@/lib/api';
import type { StrategyType, StrategyVisibility } from '@/types';

// Keys
const STRATEGIES_KEY = '/strategies';
const strategyKey = (id: string) => `/strategies/${id}`;
const MARKETPLACE_KEY = '/strategies/marketplace';

/**
 * Fetch all user strategies (templates).
 */
export function useStrategies(params?: { type_filter?: StrategyType; visibility?: StrategyVisibility }) {
  const key = params ? [STRATEGIES_KEY, params] : STRATEGIES_KEY;
  const swr = useSWR<StrategyResponse[]>(
    key,
    () => strategiesApi.list(params),
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
 * Fetch single strategy
 */
export function useStrategy(id: string | null) {
  return useSWR<StrategyResponse>(
    id ? strategyKey(id) : null,
    () => strategiesApi.get(id!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * Create strategy mutation
 */
export function useCreateStrategy() {
  return useSWRMutation<StrategyResponse, Error, string, CreateStrategyRequest>(
    STRATEGIES_KEY,
    async (_, { arg }) => {
      return strategiesApi.create(arg);
    }
  );
}

/**
 * Update strategy mutation
 */
export function useUpdateStrategy(id: string) {
  return useSWRMutation<StrategyResponse, Error, string, UpdateStrategyRequest>(
    strategyKey(id),
    async (_, { arg }) => {
      return strategiesApi.update(id, arg);
    }
  );
}

/**
 * Delete strategy mutation
 */
export function useDeleteStrategy(id: string) {
  return useSWRMutation<void, Error, string>(
    strategyKey(id),
    async () => {
      return strategiesApi.delete(id);
    }
  );
}

/**
 * Fork strategy mutation
 */
export function useForkStrategy() {
  return useSWRMutation<StrategyResponse, Error, string, string>(
    STRATEGIES_KEY,
    async (_, { arg: strategyId }) => {
      return strategiesApi.fork(strategyId);
    }
  );
}

/**
 * Browse marketplace strategies (public).
 * Treats 404 as empty list (graceful degradation when backend route is unavailable).
 */
export function useMarketplaceStrategies(params?: {
  type_filter?: StrategyType;
  category?: string;
  search?: string;
  sort_by?: 'popular' | 'recent';
  limit?: number;
  offset?: number;
}) {
  const key = params ? [MARKETPLACE_KEY, params] : MARKETPLACE_KEY;
  const swr = useSWR<MarketplaceResponse>(
    key,
    async () => {
      try {
        return await strategiesApi.marketplace(params);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return { items: [], total: 0, limit: params?.limit ?? 50, offset: params?.offset ?? 0 };
        }
        throw err;
      }
    },
    {
      revalidateOnFocus: false,
      dedupingInterval: 10000,
    }
  );
  return {
    ...swr,
    strategies: swr.data?.items ?? [],
    total: swr.data?.total ?? 0,
    refresh: swr.mutate,
  };
}

/**
 * Fetch version history for a strategy
 */
export function useStrategyVersions(strategyId: string | null) {
  return useSWR<StrategyVersionResponse[]>(
    strategyId ? `/strategies/${strategyId}/versions` : null,
    () => strategiesApi.listVersions(strategyId!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * Restore strategy to a previous version
 */
export function useRestoreStrategyVersion(strategyId: string) {
  return useSWRMutation<StrategyResponse, Error, string, number>(
    `/strategies/${strategyId}`,
    async (_, { arg: version }) => {
      return strategiesApi.restoreVersion(strategyId, version);
    }
  );
}
