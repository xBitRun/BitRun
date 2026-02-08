"use client";

import { useTranslations } from "next-intl";
import { Heart } from "lucide-react";

export function LandingFooter() {
  const t = useTranslations("landing");

  return (
    <footer className="landing-footer">
      <div className="mx-auto flex max-w-[1200px] flex-col items-center gap-4 px-5 sm:flex-row sm:justify-between">
        <p className="flex items-center gap-1 text-sm text-foreground/40">
          {t("footer.madeWith")}
          <Heart className="inline h-4 w-4 text-red-400" aria-hidden="true" />
          {t("footer.by")}{" "}
          <span className="font-medium text-foreground/60">{t("footer.teamName")}</span>
        </p>
        <p className="text-xs text-foreground/30">
          {t("footer.copyright", { year: new Date().getFullYear() })}
        </p>
      </div>
    </footer>
  );
}
