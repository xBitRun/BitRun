import type { BrandConfig, ThemeColors } from "./brand";

// Import the static config (bundled at build time)
import brandConfigJson from "./brand.config.json";

// Cache for loaded config
let cachedConfig: BrandConfig | null = null;

/**
 * Safely parse JSON with error handling
 */
function safeParseJson<T>(json: string | undefined, fallback: T): T {
  if (!json) return fallback;
  try {
    return JSON.parse(json) as T;
  } catch {
    console.warn("Failed to parse JSON config:", json);
    return fallback;
  }
}

/**
 * Loads brand configuration with environment variable overrides
 * Priority: ENV vars > brand.config.json
 */
export function getBrandConfig(): BrandConfig {
  if (cachedConfig) {
    return cachedConfig;
  }

  // Start with JSON config
  const config: BrandConfig = { ...brandConfigJson };

  // ===== Identity Overrides =====
  if (process.env.NEXT_PUBLIC_BRAND_NAME) {
    config.identity.name = process.env.NEXT_PUBLIC_BRAND_NAME;
    // Only override shortName if not explicitly set
    if (!process.env.NEXT_PUBLIC_BRAND_SHORT_NAME) {
      config.identity.shortName = process.env.NEXT_PUBLIC_BRAND_NAME;
    }
  }
  if (process.env.NEXT_PUBLIC_BRAND_SHORT_NAME) {
    config.identity.shortName = process.env.NEXT_PUBLIC_BRAND_SHORT_NAME;
  }
  if (process.env.NEXT_PUBLIC_BRAND_TAGLINE) {
    config.identity.tagline = process.env.NEXT_PUBLIC_BRAND_TAGLINE;
  }
  if (process.env.NEXT_PUBLIC_BRAND_DESCRIPTION) {
    config.identity.description = process.env.NEXT_PUBLIC_BRAND_DESCRIPTION;
  }

  // ===== Assets Overrides =====
  if (process.env.NEXT_PUBLIC_BRAND_LOGO_DEFAULT) {
    config.assets.logo.default = process.env.NEXT_PUBLIC_BRAND_LOGO_DEFAULT;
  }
  if (process.env.NEXT_PUBLIC_BRAND_LOGO_COMPACT) {
    config.assets.logo.compact = process.env.NEXT_PUBLIC_BRAND_LOGO_COMPACT;
  }
  if (process.env.NEXT_PUBLIC_BRAND_LOGO_ICON) {
    config.assets.logo.icon = process.env.NEXT_PUBLIC_BRAND_LOGO_ICON;
  }
  if (process.env.NEXT_PUBLIC_BRAND_FAVICON) {
    config.assets.favicon = process.env.NEXT_PUBLIC_BRAND_FAVICON;
  }

  // ===== Theme Overrides =====
  if (process.env.NEXT_PUBLIC_BRAND_THEME_PRESET) {
    config.theme.preset = process.env.NEXT_PUBLIC_BRAND_THEME_PRESET;
  }
  if (process.env.NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE) {
    const colorOverrides = safeParseJson<Partial<ThemeColors>>(
      process.env.NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE,
      {},
    );
    if (Object.keys(colorOverrides).length > 0) {
      config.theme.overrides = {
        ...config.theme.overrides,
        ...colorOverrides,
      };
    }
  }

  // ===== Legal Overrides =====
  if (process.env.NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER) {
    config.legal.copyrightHolder =
      process.env.NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER;
  }
  if (process.env.NEXT_PUBLIC_BRAND_TERMS_URL) {
    config.legal.termsUrl = process.env.NEXT_PUBLIC_BRAND_TERMS_URL;
  }
  if (process.env.NEXT_PUBLIC_BRAND_PRIVACY_URL) {
    config.legal.privacyUrl = process.env.NEXT_PUBLIC_BRAND_PRIVACY_URL;
  }

  // ===== Links Overrides =====
  if (process.env.NEXT_PUBLIC_BRAND_HOMEPAGE_URL) {
    config.links.homepage = process.env.NEXT_PUBLIC_BRAND_HOMEPAGE_URL;
  }
  if (process.env.NEXT_PUBLIC_BRAND_DOCS_URL) {
    config.links.documentation = process.env.NEXT_PUBLIC_BRAND_DOCS_URL;
  }
  if (process.env.NEXT_PUBLIC_BRAND_SUPPORT_URL) {
    config.links.support = process.env.NEXT_PUBLIC_BRAND_SUPPORT_URL;
  }
  if (process.env.NEXT_PUBLIC_BRAND_GITHUB_URL) {
    config.links.github = process.env.NEXT_PUBLIC_BRAND_GITHUB_URL;
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
