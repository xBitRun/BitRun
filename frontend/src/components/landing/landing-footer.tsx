"use client";

import { useTranslations } from "next-intl";
import { Heart } from "lucide-react";
import { useBrand } from "@/lib/brand-context";

export function LandingFooter() {
  const t = useTranslations("landing");
  const { shortName } = useBrand();

  return (
    <footer className="landing-footer">
      <div className="flex flex-col items-center gap-4 px-4 sm:flex-row sm:justify-between sm:px-6 lg:px-8">
        <p className="flex items-center gap-1 text-sm text-foreground/40">
          {t("footer.madeWith")}
          <Heart className="inline h-4 w-4 text-red-400" aria-hidden="true" />
          {t("footer.by")}{" "}
          <span className="font-medium text-foreground/60">
            {t("footer.teamName", { brandName: shortName })}
          </span>
        </p>
        <p className="text-xs text-foreground/30">
          {t("footer.copyright", {
            year: new Date().getFullYear(),
            brandName: shortName,
          })}
        </p>
      </div>
    </footer>
  );
}
