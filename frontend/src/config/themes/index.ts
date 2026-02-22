import type { ThemePreset } from "../brand";
import { binanceTheme } from "./binance.theme";
import { bitrunTheme } from "./bitrun.theme";

/**
 * Theme Registry
 * Add new themes here to make them available
 */
export const themes: Record<string, ThemePreset> = {
  bitrun: bitrunTheme,
  binance: binanceTheme,
};

/**
 * Get a theme preset by ID
 * Falls back to bitrun theme if not found
 */
export function getThemePreset(themeId: string): ThemePreset {
  return themes[themeId] ?? bitrunTheme;
}

/**
 * Get all available theme IDs
 */
export function getAvailableThemes(): string[] {
  return Object.keys(themes);
}

// Re-export individual themes
export { binanceTheme, bitrunTheme };
