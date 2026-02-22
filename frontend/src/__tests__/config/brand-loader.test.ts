/**
 * Tests for brand-loader configuration
 */

import {
  getBrandConfig,
  getBrandConfigServer,
  resetBrandConfigCache,
} from "@/config/brand-loader";

// Mock the brand config JSON
jest.mock("@/config/brand.config.json", () => ({
  identity: {
    name: "DefaultBrand",
    shortName: "DB",
    tagline: "Default Tagline",
    description: "Default Description",
  },
  assets: {
    logo: {
      default: "/logo.svg",
      compact: null,
      icon: null,
      alt: "DefaultBrand",
    },
    favicon: "/favicon.ico",
  },
  theme: {
    preset: "default",
    overrides: null,
  },
  legal: {
    copyrightHolder: "DefaultBrand Inc",
    termsUrl: "/terms",
    privacyUrl: "/privacy",
  },
  links: {
    homepage: "https://default.com",
    documentation: null,
    support: null,
    github: null,
  },
}));

describe("brand-loader", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    // Reset cache before each test
    resetBrandConfigCache();
    // Clear all NEXT_PUBLIC_BRAND env vars
    Object.keys(process.env).forEach((key) => {
      if (key.startsWith("NEXT_PUBLIC_BRAND")) {
        delete process.env[key];
      }
    });
  });

  afterAll(() => {
    // Restore original env
    Object.keys(process.env).forEach((key) => {
      if (key.startsWith("NEXT_PUBLIC_BRAND")) {
        delete process.env[key];
      }
    });
    Object.assign(process.env, originalEnv);
  });

  describe("getBrandConfig", () => {
    it("returns default config from JSON", () => {
      const config = getBrandConfig();

      expect(config.identity.name).toBe("DefaultBrand");
      expect(config.identity.shortName).toBe("DB");
      expect(config.theme.preset).toBe("default");
    });

    it("caches config after first load", () => {
      const config1 = getBrandConfig();
      const config2 = getBrandConfig();

      expect(config1).toBe(config2);
    });

    it("overrides name from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_NAME = "CustomBrand";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.identity.name).toBe("CustomBrand");
    });

    it("overrides shortName from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_SHORT_NAME = "CB";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.identity.shortName).toBe("CB");
    });

    it("uses name as shortName when only name is set", () => {
      process.env.NEXT_PUBLIC_BRAND_NAME = "NewBrand";
      delete process.env.NEXT_PUBLIC_BRAND_SHORT_NAME;

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.identity.name).toBe("NewBrand");
      expect(config.identity.shortName).toBe("NewBrand");
    });

    it("overrides tagline from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_TAGLINE = "Custom Tagline";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.identity.tagline).toBe("Custom Tagline");
    });

    it("overrides description from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_DESCRIPTION = "Custom Description";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.identity.description).toBe("Custom Description");
    });

    it("overrides logo default from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_LOGO_DEFAULT = "/custom-logo.svg";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.assets.logo.default).toBe("/custom-logo.svg");
    });

    it("overrides logo compact from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_LOGO_COMPACT = "/compact-logo.svg";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.assets.logo.compact).toBe("/compact-logo.svg");
    });

    it("overrides logo icon from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_LOGO_ICON = "/icon-logo.svg";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.assets.logo.icon).toBe("/icon-logo.svg");
    });

    it("overrides favicon from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_FAVICON = "/custom-favicon.ico";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.assets.favicon).toBe("/custom-favicon.ico");
    });

    it("overrides theme preset from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_THEME_PRESET = "dark";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.theme.preset).toBe("dark");
    });

    it("overrides theme colors from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE = '{"primary":"#ff0000"}';

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.theme.overrides?.primary).toBe("#ff0000");
    });

    it("handles invalid theme colors JSON gracefully", () => {
      const warnSpy = jest.spyOn(console, "warn").mockImplementation();
      process.env.NEXT_PUBLIC_BRAND_THEME_COLORS_OVERRIDE = "invalid json";

      resetBrandConfigCache();
      const config = getBrandConfig();

      // Should not crash - invalid JSON means empty object fallback, so no override
      // The important thing is it doesn't throw
      expect(config.theme).toBeDefined();
      expect(warnSpy).toHaveBeenCalled();
      warnSpy.mockRestore();
    });

    it("overrides copyright holder from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_COPYRIGHT_HOLDER = "Custom Inc";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.legal.copyrightHolder).toBe("Custom Inc");
    });

    it("overrides terms URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_TERMS_URL = "https://custom.com/terms";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.legal.termsUrl).toBe("https://custom.com/terms");
    });

    it("overrides privacy URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_PRIVACY_URL = "https://custom.com/privacy";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.legal.privacyUrl).toBe("https://custom.com/privacy");
    });

    it("overrides homepage URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_HOMEPAGE_URL = "https://custom.com";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.links.homepage).toBe("https://custom.com");
    });

    it("overrides docs URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_DOCS_URL = "https://docs.custom.com";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.links.documentation).toBe("https://docs.custom.com");
    });

    it("overrides support URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_SUPPORT_URL = "https://support.custom.com";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.links.support).toBe("https://support.custom.com");
    });

    it("overrides github URL from env var", () => {
      process.env.NEXT_PUBLIC_BRAND_GITHUB_URL = "https://github.com/custom";

      resetBrandConfigCache();
      const config = getBrandConfig();

      expect(config.links.github).toBe("https://github.com/custom");
    });
  });

  describe("getBrandConfigServer", () => {
    it("returns same config as getBrandConfig", () => {
      const config1 = getBrandConfig();
      const config2 = getBrandConfigServer();

      expect(config1).toEqual(config2);
    });
  });

  describe("resetBrandConfigCache", () => {
    it("clears cached config", () => {
      const config1 = getBrandConfig();
      resetBrandConfigCache();
      const config2 = getBrandConfig();

      // They should be equal but not the same reference
      expect(config1).toEqual(config2);
      expect(config1).not.toBe(config2);
    });
  });
});
