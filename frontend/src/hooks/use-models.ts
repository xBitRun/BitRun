'use client';

import useSWR from 'swr';
import { modelsApi, AIModelInfoResponse } from '@/lib/api/endpoints';

/**
 * Hook to fetch and manage AI models.
 * Models are now sourced from user-configured providers in the DB.
 */
export function useModels(provider?: string) {
  const { data, error, isLoading, mutate } = useSWR(
    ['models', provider],
    () => modelsApi.list(provider),
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000, // Cache for 1 minute
    }
  );

  return {
    models: data || [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * Hook to fetch AI providers
 */
export function useModelProviders() {
  const { data, error, isLoading, mutate } = useSWR(
    'model-providers',
    () => modelsApi.listProviders(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 60000,
    }
  );

  return {
    providers: data || [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * Hook to get models from user-configured providers.
 * The backend /models API already filters by enabled providers,
 * so no additional client-side filtering is needed.
 */
export function useUserModels() {
  const { models, isLoading, error, refresh } = useModels();

  return {
    models,
    hasConfiguredProviders: models.length > 0,
    isLoading,
    error,
    refresh,
  };
}

/**
 * Get display name for a model ID
 */
export function getModelDisplayName(modelId: string | null | undefined, models: AIModelInfoResponse[]): string {
  if (!modelId) return '';

  const model = models.find(m => m.id === modelId);
  if (model) return model.name;

  // Parse provider:model format
  const parts = modelId.split(':');
  if (parts.length === 2) {
    return `${parts[0].charAt(0).toUpperCase() + parts[0].slice(1)} - ${parts[1]}`;
  }

  return modelId;
}

/**
 * Get provider display name
 */
export function getProviderDisplayName(providerId: string): string {
  const names: Record<string, string> = {
    deepseek: 'DeepSeek',
    qwen: 'Alibaba Qwen',
    zhipu: 'Zhipu GLM',
    minimax: 'MiniMax',
    kimi: 'Moonshot Kimi',
    openai: 'OpenAI',
    gemini: 'Google Gemini',
    grok: 'xAI Grok',
    custom: 'Custom',
  };
  return names[providerId] || providerId;
}

/**
 * Group models by provider
 */
export function groupModelsByProvider(models: AIModelInfoResponse[]): Record<string, AIModelInfoResponse[]> {
  return models.reduce((acc, model) => {
    const provider = model.provider;
    if (!acc[provider]) {
      acc[provider] = [];
    }
    acc[provider].push(model);
    return acc;
  }, {} as Record<string, AIModelInfoResponse[]>);
}
