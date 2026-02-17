/**
 * Brand Configuration Types
 * Single source of truth for brand identity and theming
 */

// ===== Theme Types =====

export interface ThemeColors {
  // Base
  background: string;
  foreground: string;

  // Headings (titles)
  headingForeground?: string; // Title foreground color (defaults to foreground)
  headingGradient?: [string, string]; // Gradient colors for .text-gradient

  // Surfaces
  card: string;
  cardForeground?: string;
  popover: string;
  popoverForeground?: string;

  // Primary
  primary: string;
  primaryForeground: string;
  primaryVivid: string;
  primaryGlow: string;
  primaryGlowSoft?: string;

  // Semantic
  secondary: string;
  secondaryForeground?: string;
  muted: string;
  mutedForeground?: string;
  accent: string;
  accentForeground?: string;
  destructive: string;

  // Trading
  profit: string;
  loss: string;
  success: string;
  warning: string;

  // UI
  border: string;
  input?: string;
  ring: string;

  // Sidebar
  sidebar: string;
  sidebarForeground?: string;
  sidebarPrimary?: string;
  sidebarPrimaryForeground?: string;
  sidebarAccent: string;
  sidebarAccentForeground?: string;
  sidebarBorder?: string;
  sidebarRing?: string;

  // Charts
  chart: [string, string, string, string, string];

  // Gradients
  gradients: {
    purple1: string;
    purple2: string;
    purple3: string;
  };
}

export interface ThemeEffects {
  /** DarkVeil background hue shift in degrees (0-360) */
  darkVeilHueShift?: number;
}

export interface ThemePreset {
  id: string;
  name: string;
  description: string;
  colors: ThemeColors;
  cssVars?: Record<string, string>;
  effects?: ThemeEffects;
}

// ===== Brand Asset Types =====

export interface BrandLogo {
  default?: string;
  compact?: string;
  icon?: string;
  alt?: string;
}

export interface BrandAssets {
  logo: BrandLogo;
  favicon: string;
  manifest?: {
    icons: Array<{
      src: string;
      sizes: string;
      type: string;
    }>;
  };
}

// ===== Brand Identity Types =====

export interface BrandIdentity {
  name: string;
  shortName: string;
  tagline: string;
  description: string;
}

export interface BrandLegal {
  copyrightHolder: string;
  termsUrl?: string;
  privacyUrl?: string;
}

export interface BrandLinks {
  homepage?: string;
  documentation?: string;
  support?: string;
  github?: string;
}

// ===== Main Configuration Type =====

export interface BrandConfig {
  $schema?: string;
  id: string;
  version: string;

  identity: BrandIdentity;
  assets: BrandAssets;
  theme: {
    preset: string;
    overrides?: Partial<ThemeColors>;
  };
  legal: BrandLegal;
  links: BrandLinks;
}

// ===== Runtime Brand Context Type =====

export interface BrandContextValue {
  config: BrandConfig;
  theme: ThemePreset;

  // Convenience accessors
  name: string;
  shortName: string;
  logo: BrandLogo;

  // Helper functions
  getLogoSrc: (variant?: "default" | "compact" | "icon") => string | null;
  getLogoAlt: () => string;
}
