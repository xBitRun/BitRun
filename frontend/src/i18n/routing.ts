import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // A list of all locales that are supported
  locales: ["en", "zh"],

  // Used when no locale matches
  defaultLocale: "en",

  // The `pathnames` option can be used to customize URL paths for specific locales
  localePrefix: "as-needed",
});

export type Locale = (typeof routing.locales)[number];
