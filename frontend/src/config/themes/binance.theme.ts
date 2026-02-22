import type { ThemePreset } from "../brand";

/**
 * Binance Theme - Yellow/Gold dark theme
 * Inspired by Binance exchange design
 * Primary: #FFB800 (Gold/Yellow)
 * Background: #121212 (Deep black)
 */
export const binanceTheme: ThemePreset = {
  id: "binance",
  name: "Binance Gold",
  description: "Binance-inspired dark theme with gold accents",

  colors: {
    // Base - Deep black background
    background: "oklch(0.13 0 0)",
    foreground: "oklch(0.98 0 0)",

    // Headings - Gold gradient
    headingForeground: "oklch(0.98 0 0)",
    headingGradient: ["oklch(0.82 0.16 85)", "oklch(0.75 0.14 75)"],

    // Surfaces
    card: "oklch(0.16 0 0)",
    cardForeground: "oklch(0.98 0 0)",
    popover: "oklch(0.18 0 0)",
    popoverForeground: "oklch(0.98 0 0)",

    // Primary - Binance Gold (#FFB800)
    primary: "oklch(0.82 0.16 85)",
    primaryForeground: "oklch(0.13 0 0)",
    primaryVivid: "oklch(0.85 0.18 85)",
    primaryGlow: "oklch(0.78 0.15 80)",
    primaryGlowSoft: "oklch(0.75 0.12 85)",

    // Semantic
    secondary: "oklch(0.22 0 0)",
    secondaryForeground: "oklch(0.9 0 0)",
    muted: "oklch(0.24 0 0)",
    mutedForeground: "oklch(0.65 0 0)",
    accent: "oklch(0.26 0.02 85)",
    accentForeground: "oklch(0.98 0 0)",
    destructive: "oklch(0.55 0.22 25)",

    // Trading - Green for profit (Binance style)
    profit: "oklch(0.7 0.18 145)",
    loss: "oklch(0.65 0.22 25)",
    success: "oklch(0.7 0.18 145)",
    warning: "oklch(0.82 0.16 85)",

    // UI
    border: "oklch(0.28 0 0)",
    input: "oklch(0.22 0 0)",
    ring: "oklch(0.82 0.16 85)",

    // Sidebar
    sidebar: "oklch(0.11 0 0)",
    sidebarForeground: "oklch(0.9 0 0)",
    sidebarPrimary: "oklch(0.82 0.16 85)",
    sidebarPrimaryForeground: "oklch(0.13 0 0)",
    sidebarAccent: "oklch(0.2 0.02 85)",
    sidebarAccentForeground: "oklch(0.98 0 0)",
    sidebarBorder: "oklch(0.25 0 0)",
    sidebarRing: "oklch(0.82 0.16 85)",

    // Charts - Binance palette
    chart: [
      "oklch(0.82 0.16 85)", // Gold
      "oklch(0.7 0.18 145)", // Green
      "oklch(0.7 0.15 220)", // Blue
      "oklch(0.75 0.18 60)", // Orange
      "oklch(0.7 0.2 330)", // Pink
    ],

    // Gradients (Gold theme)
    gradients: {
      purple1: "oklch(0.82 0.16 85)",
      purple2: "oklch(0.78 0.14 75)",
      purple3: "oklch(0.85 0.18 85)",
    },
  },

  cssVars: {
    "--radius": "0.375rem", // Slightly smaller radius for Binance feel
  },

  effects: {
    darkVeilHueShift: 195, // Shift purple (280°) to gold (85°)
  },
};

export default binanceTheme;
