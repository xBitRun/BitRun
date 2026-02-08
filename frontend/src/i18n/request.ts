import { getRequestConfig } from "next-intl/server";
import { routing, type Locale } from "./routing";
import en from "../messages/en.json";
import zh from "../messages/zh.json";

// Pre-loaded messages to avoid dynamic import issues with Webpack in Docker
const messages: Record<Locale, typeof en> = {
  en,
  zh,
};

export default getRequestConfig(async ({ requestLocale }) => {
  // This typically corresponds to the `[locale]` segment
  let locale = await requestLocale;

  // Ensure that a valid locale is used
  if (!locale || !routing.locales.includes(locale as Locale)) {
    locale = routing.defaultLocale;
  }

  return {
    locale,
    messages: messages[locale as Locale],
  };
});
