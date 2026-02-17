"use client";

import { createContext, useContext, useMemo, ReactNode } from "react";
import type {
  BrandConfig,
  BrandContextValue,
  ThemePreset,
} from "@/config/brand";
import { getBrandConfig } from "@/config/brand-loader";
import { getThemePreset } from "@/config/themes";
import { generateThemeCss } from "./theme-css";

const BrandContext = createContext<BrandContextValue | null>(null);

export interface BrandProviderProps {
  children: ReactNode;
  config?: BrandConfig;
  theme?: ThemePreset;
}

export function BrandProvider({ children, config, theme }: BrandProviderProps) {
  const value = useMemo<BrandContextValue>(() => {
    const brandConfig = config ?? getBrandConfig();
    const themePreset = theme ?? getThemePreset(brandConfig.theme.preset);

    // Apply theme overrides if specified
    const finalTheme: ThemePreset = brandConfig.theme.overrides
      ? {
          ...themePreset,
          colors: { ...themePreset.colors, ...brandConfig.theme.overrides },
        }
      : themePreset;

    return {
      config: brandConfig,
      theme: finalTheme,

      // Convenience accessors
      name: brandConfig.identity.name,
      shortName: brandConfig.identity.shortName,
      logo: brandConfig.assets.logo,

      // Helper functions
      getLogoSrc: (variant = "default"): string | null => {
        const logoAsset = brandConfig.assets.logo;
        switch (variant) {
          case "compact":
            return logoAsset.compact || logoAsset.default || null;
          case "icon":
            return (
              logoAsset.icon || logoAsset.compact || logoAsset.default || null
            );
          default:
            return logoAsset.default || null;
        }
      },
      getLogoAlt: () =>
        brandConfig.assets.logo.alt ?? brandConfig.identity.name,
    };
  }, [config, theme]);

  // Inject theme CSS at runtime (only on client)
  useMemo(() => {
    if (typeof document !== "undefined") {
      const styleId = "brand-theme-styles";
      let styleEl = document.getElementById(styleId);
      if (!styleEl) {
        styleEl = document.createElement("style");
        styleEl.id = styleId;
        document.head.appendChild(styleEl);
      }
      styleEl.textContent = generateThemeCss(value.theme);
    }
  }, [value.theme]);

  return (
    <BrandContext.Provider value={value}>{children}</BrandContext.Provider>
  );
}

export function useBrand(): BrandContextValue {
  const context = useContext(BrandContext);
  if (!context) {
    throw new Error("useBrand must be used within a BrandProvider");
  }
  return context;
}

// Hook for accessing just the theme
export function useTheme(): ThemePreset {
  return useBrand().theme;
}

// Hook for accessing just the brand name
export function useBrandName(): string {
  return useBrand().name;
}
