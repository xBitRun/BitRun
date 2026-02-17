import type { ThemeColors, ThemePreset } from "@/config/brand";

/**
 * Generates CSS custom properties from theme colors
 * Maps theme color values to CSS variable names
 */
export function generateCssVars(colors: ThemeColors): string {
  const vars: Record<string, string> = {
    // Base
    "--background": colors.background,
    "--foreground": colors.foreground,

    // Headings
    "--heading-foreground": colors.headingForeground ?? colors.foreground,
    "--heading-gradient-1": colors.headingGradient?.[0] ?? colors.primary,
    "--heading-gradient-2": colors.headingGradient?.[1] ?? colors.primaryVivid,

    // Surfaces
    "--card": colors.card,
    "--card-foreground": colors.cardForeground ?? colors.foreground,
    "--popover": colors.popover,
    "--popover-foreground": colors.popoverForeground ?? colors.foreground,

    // Primary
    "--primary": colors.primary,
    "--primary-foreground": colors.primaryForeground,
    "--primary-vivid": colors.primaryVivid,
    "--primary-glow": colors.primaryGlow,
    "--primary-glow-soft": colors.primaryGlowSoft ?? colors.primaryGlow,

    // Semantic
    "--secondary": colors.secondary,
    "--secondary-foreground": colors.secondaryForeground ?? "oklch(0.9 0 0)",
    "--muted": colors.muted,
    "--muted-foreground": colors.mutedForeground ?? "oklch(0.6 0 0)",
    "--accent": colors.accent,
    "--accent-foreground": colors.accentForeground ?? colors.foreground,
    "--destructive": colors.destructive,

    // Trading
    "--profit": colors.profit,
    "--loss": colors.loss,
    "--success": colors.success,
    "--warning": colors.warning,

    // UI
    "--border": colors.border,
    "--input": colors.input ?? colors.secondary,
    "--ring": colors.ring,

    // Sidebar
    "--sidebar": colors.sidebar,
    "--sidebar-foreground": colors.sidebarForeground ?? "oklch(0.9 0 0)",
    "--sidebar-primary": colors.sidebarPrimary ?? colors.primary,
    "--sidebar-primary-foreground":
      colors.sidebarPrimaryForeground ?? "oklch(0.98 0 0)",
    "--sidebar-accent": colors.sidebarAccent,
    "--sidebar-accent-foreground":
      colors.sidebarAccentForeground ?? colors.foreground,
    "--sidebar-border": colors.sidebarBorder ?? colors.border,
    "--sidebar-ring": colors.sidebarRing ?? colors.ring,

    // Charts
    "--chart-1": colors.chart[0],
    "--chart-2": colors.chart[1],
    "--chart-3": colors.chart[2],
    "--chart-4": colors.chart[3],
    "--chart-5": colors.chart[4],

    // Gradients
    "--gradient-purple-1": colors.gradients.purple1,
    "--gradient-purple-2": colors.gradients.purple2,
    "--gradient-purple-3": colors.gradients.purple3,
  };

  return Object.entries(vars)
    .map(([key, value]) => `  ${key}: ${value};`)
    .join("\n");
}

/**
 * Generates complete CSS for a theme
 */
export function generateThemeCss(theme: ThemePreset): string {
  const colorVars = generateCssVars(theme.colors);
  const customVars = theme.cssVars
    ? Object.entries(theme.cssVars)
        .map(([key, value]) => `  ${key}: ${value};`)
        .join("\n")
    : "";

  return `/* Generated theme: ${theme.name} */
:root {
${colorVars}
${customVars}
}

/* Keep .dark class for compatibility */
.dark {
${colorVars}
${customVars}
}
`;
}
