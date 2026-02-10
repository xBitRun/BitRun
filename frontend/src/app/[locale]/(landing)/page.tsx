"use client";

import { useTranslations } from "next-intl";
import { Link } from "@/i18n/navigation";
import { Header } from "@/components/layout/header";
import { DarkVeil } from "@/components/landing/dark-veil";
import { FeatureCards } from "@/components/landing/feature-cards";
import { CoreCapabilities } from "@/components/landing/core-capabilities";
import { CapabilityShowcase } from "@/components/landing/capability-showcase";
import { LandingFooter } from "@/components/landing/landing-footer";

export default function LandingPage() {
  const t = useTranslations("landing");

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

      {/* ── Core Capabilities ── */}
      <CoreCapabilities />

      {/* ── Core Capabilities Showcase ── */}
      <CapabilityShowcase />

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
