import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { generateBrandMetadata } from "@/components/brand";
import { getBrandConfig } from "@/config/brand-loader";
import { getThemePreset } from "@/config/themes";
import { generateThemeCss } from "@/lib/theme-css";
import "./globals.css";

export const metadata: Metadata = generateBrandMetadata();

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Generate theme CSS at SSR time to prevent flash
  const brandConfig = getBrandConfig();
  const themePreset = getThemePreset(brandConfig.theme.preset);
  const finalTheme = brandConfig.theme.overrides
    ? {
        ...themePreset,
        colors: { ...themePreset.colors, ...brandConfig.theme.overrides },
      }
    : themePreset;
  const themeCss = generateThemeCss(finalTheme);

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <style
          id="brand-theme-styles"
          dangerouslySetInnerHTML={{ __html: themeCss }}
        />
      </head>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} antialiased min-h-screen bg-background`}
      >
        {children}
      </body>
    </html>
  );
}
