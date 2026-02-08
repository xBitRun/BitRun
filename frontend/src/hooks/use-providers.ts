'use client';

import useSWR from 'swr';
import { providersApi, PresetProviderInfo } from '@/lib/api/endpoints';

/**
 * Hook to fetch preset provider configurations
 */
export function usePresetProviders() {
  const { data, error, isLoading, mutate } = useSWR(
    'preset-providers',
    () => providersApi.listPresets(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 300000, // Cache for 5 minutes (presets don't change)
    }
  );

  return {
    presets: data || [],
    isLoading,
    error,
    refresh: mutate,
  };
}

/**
 * Hook to fetch user's configured providers
 */
export function useProviderConfigs() {
  const { data, error, isLoading, mutate } = useSWR(
    'provider-configs',
    () => providersApi.list(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30000, // Cache for 30 seconds
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
 * Hook to fetch API formats
 */
export function useApiFormats() {
  const { data, error, isLoading } = useSWR(
    'api-formats',
    () => providersApi.listFormats(),
    {
      revalidateOnFocus: false,
      dedupingInterval: 300000, // Cache for 5 minutes
    }
  );

  return {
    formats: data?.formats || [],
    isLoading,
    error,
  };
}

/**
 * Get provider display info from preset
 */
export function getPresetInfo(presetId: string, presets: PresetProviderInfo[]): PresetProviderInfo | undefined {
  return presets.find(p => p.id === presetId);
}

/**
 * Get provider icon/emoji based on type
 */
export function getProviderIcon(providerType: string): string {
  const icons: Record<string, string> = {
    deepseek: '🔍',
    qwen: '☁️',
    zhipu: '🧠',
    minimax: '⚡',
    kimi: '🌙',
    openai: '🤖',
    gemini: '💎',
    grok: '🦅',
    custom: '⚙️',
  };
  return icons[providerType] || '🤖';
}

/**
 * Get provider config display name
 */
export function getProviderConfigDisplayName(providerType: string): string {
  const names: Record<string, string> = {
    deepseek: 'DeepSeek',
    qwen: 'Alibaba Qwen',
    zhipu: 'Zhipu GLM',
    minimax: 'MiniMax',
    kimi: 'Moonshot Kimi',
    openai: 'OpenAI',
    gemini: 'Google Gemini',
    grok: 'xAI Grok',
    custom: 'Custom Provider',
  };
  return names[providerType] || providerType;
}
