import type { Metadata } from "next";
import { getBrandConfigServer } from "@/config/brand-loader";

/**
 * Generates Next.js metadata from brand configuration
 * Use in layout.tsx or page.tsx for dynamic SEO
 */
export function generateBrandMetadata(
  overrides?: Partial<Metadata>
): Metadata {
  const config = getBrandConfigServer();

  return {
    title: {
      default: config.identity.name,
      template: `%s | ${config.identity.name}`,
    },
    description: config.identity.description,

    icons: {
      icon: config.assets.favicon,
      shortcut: config.assets.favicon,
      apple: config.assets.logo.icon,
    },

    openGraph: {
      title: config.identity.name,
      description: config.identity.tagline,
      siteName: config.identity.name,
    },

    twitter: {
      card: "summary_large_image",
      title: config.identity.name,
      description: config.identity.tagline,
    },

    ...overrides,
  };
}

/**
 * Generates metadata for a specific page with custom title/description
 */
export function generatePageMetadata(
  title: string,
  description?: string,
  overrides?: Partial<Metadata>
): Metadata {
  const config = getBrandConfigServer();

  return generateBrandMetadata({
    title,
    description: description ?? config.identity.description,
    ...overrides,
  });
}
