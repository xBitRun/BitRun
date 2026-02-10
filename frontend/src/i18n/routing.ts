import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // A list of all locales that are supported
  locales: ["en", "zh"],

  // Used when no locale matches
  defaultLocale: "en",

  // No locale prefix in URL; language preference is persisted via NEXT_LOCALE cookie
  localePrefix: "never",
});

export type Locale = (typeof routing.locales)[number];
