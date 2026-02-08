"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Header } from "@/components/layout/header";
import { DarkVeil } from "@/components/landing/dark-veil";
import { FeatureCards } from "@/components/landing/feature-cards";
import { Marquee } from "@/components/landing/marquee";
import { LandingFooter } from "@/components/landing/landing-footer";
import { useRef, useState, useEffect } from "react";

/* ── Feature marquee card data ── */
const featureCards = [
  { titleKey: "features.items.0.title", descKey: "features.items.0.description" },
  { titleKey: "features.items.1.title", descKey: "features.items.1.description" },
  { titleKey: "features.items.2.title", descKey: "features.items.2.description" },
  { titleKey: "features.items.3.title", descKey: "features.items.3.description" },
  { titleKey: "features.items.4.title", descKey: "features.items.4.description" },
  { titleKey: "features.items.5.title", descKey: "features.items.5.description" },
];

export default function LandingPage() {
  const t = useTranslations("landing");

  /* ── Intersection observer for section headers ── */
  const featuresHeaderRef = useRef<HTMLDivElement>(null);
  const [featuresVisible, setFeaturesVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) setFeaturesVisible(true);
      },
      { threshold: 0.3 }
    );
    if (featuresHeaderRef.current) observer.observe(featuresHeaderRef.current);
    return () => observer.disconnect();
  }, []);

  /* ── Split features into marquee rows ── */
  const row1 = featureCards.slice(0, 3);
  const row2 = featureCards.slice(3, 6);

  return (
    <div className="landing-wrapper bg-background text-foreground">
      {/* ── Navbar ── */}
      <Header variant="landing" />

      {/* ── Hero Section ── */}
      <section className="relative">
        {/* WebGL DarkVeil background */}
        <div className="dark-veil-container">
          <DarkVeil
            hueShift={0}
            noiseIntensity={0}
            scanlineIntensity={0}
            speed={0.5}
            scanlineFrequency={0}
            warpAmount={0}
            resolutionScale={1}
          />
        </div>

        {/* Gradient blur overlay */}
        <div className="landing-gradient-blur" aria-hidden="true" />

        <div className="landing-hero-content">
          {/* Title */}
          <h1 className="hero-animate hero-animate-delay-1 landing-title">
            <span className="text-gradient-animated">{t("hero.titleLine1")}</span>
            <br />
            {t("hero.titleLine2")}
          </h1>

          {/* Subtitle */}
          <p className="hero-animate hero-animate-delay-2 landing-subtitle">
            {t("hero.subtitle")}
          </p>

          {/* CTA Button */}
          <Link
            href="/login"
            className="hero-animate hero-animate-delay-3 landing-cta-button"
          >
            <span>{t("hero.cta")}</span>
          </Link>
        </div>
      </section>

      {/* ── Feature Cards (Bento Grid) ── */}
      <FeatureCards />

      {/* ── Features Marquee (Testimonials-style) ── */}
      <section className="relative z-22 w-full overflow-hidden py-20">
        <div className="mx-auto max-w-[1400px] px-5">
          {/* Header */}
          <div
            ref={featuresHeaderRef}
            className={`mb-20 text-center fade-in-section ${featuresVisible ? "visible" : ""}`}
          >
            <h2 className="section-title-rb text-gradient-animated inline-block">
              {t("features.title")}
            </h2>
            <p className="section-subtitle-rb mt-1 text-center px-4">
              {t("features.subtitle")}
            </p>
          </div>

          {/* Marquee rows */}
          <div className="space-y-5">
            <Marquee direction="left" duration={40}>
              {row1.map((card, i) => (
                <div key={i} className="marquee-card">
                  <p className="text-[0.95rem] leading-relaxed text-foreground">
                    {t(card.descKey)}
                  </p>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-foreground/10 bg-primary-vivid/20 text-sm font-bold text-gradient-purple-2">
                      {String(i + 1).padStart(2, "0")}
                    </div>
                    <span className="text-sm font-medium text-foreground/80">
                      {t(card.titleKey)}
                    </span>
                  </div>
                </div>
              ))}
            </Marquee>

            <Marquee direction="right" duration={45}>
              {row2.map((card, i) => (
                <div key={i} className="marquee-card">
                  <p className="text-[0.95rem] leading-relaxed text-foreground">
                    {t(card.descKey)}
                  </p>
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full border-2 border-foreground/10 bg-primary-vivid/20 text-sm font-bold text-gradient-purple-2">
                      {String(i + 4).padStart(2, "0")}
                    </div>
                    <span className="text-sm font-medium text-foreground/80">
                      {t(card.titleKey)}
                    </span>
                  </div>
                </div>
              ))}
            </Marquee>
          </div>
        </div>
      </section>

      {/* ── CTA Gradient Card ── */}
      <section className="relative z-22 w-full px-4 py-20 sm:px-8">
        <div className="mx-auto max-w-[1200px]">
          <div className="cta-gradient-card">
            <h2 className="text-3xl font-medium leading-none text-foreground sm:text-4xl lg:text-5xl">
              {t("cta.title")}
            </h2>
            <p className="text-base font-medium leading-none text-foreground/60 sm:text-lg">
              {t("cta.subtitle")}
            </p>
            <Link href="/login" className="cta-gradient-button">
              {t("cta.button")}
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <LandingFooter />
    </div>
  );
}
