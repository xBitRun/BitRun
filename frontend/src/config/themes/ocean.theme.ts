import type { ThemePreset } from "../brand";

/**
 * Ocean Theme - Blue/Cyan dark theme
 * Example alternative theme for white-label deployment
 */
export const oceanTheme: ThemePreset = {
  id: "ocean",
  name: "Ocean Blue",
  description: "Calm blue theme with cyan accents",

  colors: {
    // Base - Slightly warmer dark
    background: "oklch(0.08 0.01 240)",
    foreground: "oklch(0.96 0 0)",

    // Surfaces
    card: "oklch(0.11 0.01 240)",
    cardForeground: "oklch(0.96 0 0)",
    popover: "oklch(0.13 0.01 240)",
    popoverForeground: "oklch(0.96 0 0)",

    // Primary - Ocean blue
    primary: "oklch(0.65 0.18 220)",
    primaryForeground: "oklch(0.98 0 0)",
    primaryVivid: "oklch(0.50 0.28 220)",
    primaryGlow: "oklch(0.55 0.22 215)",
    primaryGlowSoft: "oklch(0.60 0.20 220)",

    // Semantic
    secondary: "oklch(0.17 0.01 240)",
    secondaryForeground: "oklch(0.9 0 0)",
    muted: "oklch(0.19 0.01 240)",
    mutedForeground: "oklch(0.6 0 0)",
    accent: "oklch(0.21 0.03 220)",
    accentForeground: "oklch(0.95 0 0)",
    destructive: "oklch(0.55 0.22 25)",

    // Trading
    profit: "oklch(0.72 0.2 145)",
    loss: "oklch(0.65 0.22 25)",
    success: "oklch(0.7 0.18 145)",
    warning: "oklch(0.75 0.18 60)",

    // UI
    border: "oklch(0.24 0.02 240)",
    input: "oklch(0.17 0.01 240)",
    ring: "oklch(0.65 0.18 220)",

    // Sidebar
    sidebar: "oklch(0.10 0.01 240)",
    sidebarForeground: "oklch(0.9 0 0)",
    sidebarPrimary: "oklch(0.65 0.18 220)",
    sidebarPrimaryForeground: "oklch(0.98 0 0)",
    sidebarAccent: "oklch(0.17 0.02 220)",
    sidebarAccentForeground: "oklch(0.95 0 0)",
    sidebarBorder: "oklch(0.21 0.02 240)",
    sidebarRing: "oklch(0.65 0.18 220)",

    // Charts - Ocean palette
    chart: [
      "oklch(0.7 0.18 220)", // Blue
      "oklch(0.7 0.16 190)", // Teal
      "oklch(0.75 0.14 160)", // Sea green
      "oklch(0.7 0.18 250)", // Indigo
      "oklch(0.7 0.16 180)", // Cyan
    ],

    // Gradients (renamed for compatibility but using blue tones)
    gradients: {
      purple1: "oklch(0.62 0.18 220)",
      purple2: "oklch(0.68 0.16 200)",
      purple3: "oklch(0.55 0.2 210)",
    },
  },

  cssVars: {
    "--radius": "0.5rem",
  },

  effects: {
    darkVeilHueShift: -80, // Shift purple to ocean blue
  },
};

export default oceanTheme;
