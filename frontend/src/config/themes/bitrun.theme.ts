import type { ThemePreset } from "../brand";

/**
 * BitRun Default Theme - Purple/Blue Arkham-inspired dark theme
 * Uses OKLCH color space for perceptual uniformity
 * Extracted from globals.css
 */
export const bitrunTheme: ThemePreset = {
  id: "bitrun",
  name: "BitRun Purple",
  description: "Default purple theme inspired by Arkham Intel",

  colors: {
    // Base - Deep dark background
    background: "oklch(0.09 0.01 260)",
    foreground: "oklch(0.95 0 0)",

    // Headings - Title colors
    headingForeground: "oklch(0.95 0 0)",
    headingGradient: ["oklch(0.7 0.2 280)", "oklch(0.7 0.18 200)"],

    // Surfaces - Cards with subtle elevation
    card: "oklch(0.12 0.01 260)",
    cardForeground: "oklch(0.95 0 0)",
    popover: "oklch(0.14 0.01 260)",
    popoverForeground: "oklch(0.95 0 0)",

    // Primary - Arkham purple/blue accent
    primary: "oklch(0.65 0.2 280)",
    primaryForeground: "oklch(0.98 0 0)",
    primaryVivid: "oklch(0.50 0.33 280)",
    primaryGlow: "oklch(0.55 0.25 285)",
    primaryGlowSoft: "oklch(0.60 0.22 280)",

    // Semantic
    secondary: "oklch(0.18 0.01 260)",
    secondaryForeground: "oklch(0.9 0 0)",
    muted: "oklch(0.2 0.01 260)",
    mutedForeground: "oklch(0.6 0 0)",
    accent: "oklch(0.22 0.03 280)",
    accentForeground: "oklch(0.95 0 0)",
    destructive: "oklch(0.55 0.22 25)",

    // Trading
    profit: "oklch(0.72 0.2 145)",
    loss: "oklch(0.65 0.22 25)",
    success: "oklch(0.7 0.18 145)",
    warning: "oklch(0.75 0.18 60)",

    // UI - Very subtle borders
    border: "oklch(0.25 0.02 260)",
    input: "oklch(0.18 0.01 260)",
    ring: "oklch(0.65 0.2 280)",

    // Sidebar - Slightly lighter than main bg
    sidebar: "oklch(0.11 0.01 260)",
    sidebarForeground: "oklch(0.9 0 0)",
    sidebarPrimary: "oklch(0.65 0.2 280)",
    sidebarPrimaryForeground: "oklch(0.98 0 0)",
    sidebarAccent: "oklch(0.18 0.02 280)",
    sidebarAccentForeground: "oklch(0.95 0 0)",
    sidebarBorder: "oklch(0.22 0.02 260)",
    sidebarRing: "oklch(0.65 0.2 280)",

    // Charts - Vibrant for data viz
    chart: [
      "oklch(0.7 0.2 280)", // Purple
      "oklch(0.7 0.18 200)", // Cyan
      "oklch(0.75 0.15 140)", // Green
      "oklch(0.75 0.18 60)", // Orange
      "oklch(0.7 0.2 330)", // Pink
    ],

    // Gradients (Landing page)
    gradients: {
      purple1: "oklch(0.62 0.22 280)",
      purple2: "oklch(0.68 0.22 295)",
      purple3: "oklch(0.55 0.28 290)",
    },
  },

  cssVars: {
    "--radius": "0.5rem",
  },

  effects: {
    darkVeilHueShift: 0, // Keep original purple tone
  },
};

export default bitrunTheme;
