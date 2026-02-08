/**
 * Quant Strategies Hooks
 *
 * SWR hooks for quant strategy data fetching and mutations.
 */

import useSWR from 'swr';
import useSWRMutation from 'swr/mutation';
import { quantStrategiesApi } from '@/lib/api';
import type {
  QuantStrategyApiResponse,
  CreateQuantStrategyRequest,
  UpdateQuantStrategyRequest,
} from '@/lib/api';
import type { StrategyStatus } from '@/types';

// Keys
const QUANT_STRATEGIES_KEY = '/quant-strategies';
const quantStrategyKey = (id: string) => `/quant-strategies/${id}`;

/**
 * Fetch all quant strategies.
 */
export function useQuantStrategies() {
  const swr = useSWR<QuantStrategyApiResponse[]>(
    QUANT_STRATEGIES_KEY,
    () => quantStrategiesApi.list(),
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
 * Fetch single quant strategy
 */
export function useQuantStrategy(id: string | null) {
  return useSWR<QuantStrategyApiResponse>(
    id ? quantStrategyKey(id) : null,
    () => quantStrategiesApi.get(id!),
    {
      revalidateOnFocus: false,
    }
  );
}

/**
 * Create quant strategy mutation
 */
export function useCreateQuantStrategy() {
  return useSWRMutation<QuantStrategyApiResponse, Error, string, CreateQuantStrategyRequest>(
    QUANT_STRATEGIES_KEY,
    async (_, { arg }) => {
      return quantStrategiesApi.create(arg);
    }
  );
}

/**
 * Update quant strategy mutation
 */
export function useUpdateQuantStrategy(id: string) {
  return useSWRMutation<QuantStrategyApiResponse, Error, string, UpdateQuantStrategyRequest>(
    quantStrategyKey(id),
    async (_, { arg }) => {
      return quantStrategiesApi.update(id, arg);
    }
  );
}

/**
 * Delete quant strategy mutation
 */
export function useDeleteQuantStrategy(id: string) {
  return useSWRMutation<void, Error, string>(
    quantStrategyKey(id),
    async () => {
      return quantStrategiesApi.delete(id);
    }
  );
}

/**
 * Update quant strategy status mutation
 */
export function useUpdateQuantStrategyStatus(id: string) {
  return useSWRMutation<QuantStrategyApiResponse, Error, string, StrategyStatus>(
    quantStrategyKey(id),
    async (_, { arg }) => {
      return quantStrategiesApi.updateStatus(id, arg);
    }
  );
}
