import type { BrandConfig } from "./brand";

// Import the static config (bundled at build time)
import brandConfigJson from "./brand.config.json";

// Cache for loaded config
let cachedConfig: BrandConfig | null = null;

/**
 * Loads brand configuration with environment variable overrides
 * Priority: ENV vars > brand.config.json > defaults
 */
export function getBrandConfig(): BrandConfig {
  if (cachedConfig) {
    return cachedConfig;
  }

  // Start with JSON config
  const config: BrandConfig = { ...brandConfigJson };

  // Apply environment variable overrides
  const envOverrides: Partial<BrandConfig["identity"]> = {};

  if (process.env.NEXT_PUBLIC_APP_NAME) {
    envOverrides.name = process.env.NEXT_PUBLIC_APP_NAME;
    envOverrides.shortName = process.env.NEXT_PUBLIC_APP_NAME;
  }

  if (process.env.NEXT_PUBLIC_APP_DESCRIPTION) {
    envOverrides.description = process.env.NEXT_PUBLIC_APP_DESCRIPTION;
  }

  // Merge overrides
  if (Object.keys(envOverrides).length > 0) {
    config.identity = { ...config.identity, ...envOverrides };
  }

  // Theme preset override
  if (process.env.NEXT_PUBLIC_THEME_PRESET) {
    config.theme.preset = process.env.NEXT_PUBLIC_THEME_PRESET;
  }

  cachedConfig = config;
  return config;
}

/**
 * Get brand config for server-side usage (metadata generation)
 */
export function getBrandConfigServer(): BrandConfig {
  return getBrandConfig();
}

/**
 * Reset cached config (useful for testing)
 */
export function resetBrandConfigCache(): void {
  cachedConfig = null;
}
