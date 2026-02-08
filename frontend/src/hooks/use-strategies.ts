/**
 * Strategies Hooks
 * 
 * SWR hooks for strategy data fetching and mutations.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { strategiesApi } from '@/lib/api';
import type { 
  StrategyResponse, 
  CreateStrategyRequest, 
  UpdateStrategyRequest 
} from '@/lib/api';
import type { StrategyStatus } from '@/types';

// Keys
const STRATEGIES_KEY = '/strategies';
const strategyKey = (id: string) => `/strategies/${id}`;

/**
 * Fetch all strategies.
 * Prefer `strategies` (always array) and `refresh` for consistent list-page usage.
 */
export function useStrategies() {
  const swr = useSWR<StrategyResponse[]>(
    STRATEGIES_KEY,
    () => strategiesApi.list(),
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
 * Update strategy status mutation
 */
export function useUpdateStrategyStatus(id: string) {
  return useSWRMutation<StrategyResponse, Error, string, StrategyStatus>(
    strategyKey(id),
    async (_, { arg }) => {
      return strategiesApi.updateStatus(id, arg);
    }
  );
}

/**
 * Get active strategies count
 */
export function useActiveStrategiesCount() {
  const { data } = useStrategies();
  return data?.filter(s => s.status === 'active').length ?? 0;
}
